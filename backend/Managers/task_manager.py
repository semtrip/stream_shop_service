from typing import Dict, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
from datetime import time, timedelta

from Logger.log import logger, log_color
#from Service.Twitch.service import TwitchService
from Service.test.service import TwitchService
from Models.task import BotTask, TaskStatus
from Data.Repositories.task_repository import TaskRepository
import datetime
class TaskManager():
    _instance = None

    def __new__(cls, db: AsyncSession):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__initialized = False
        return cls._instance

    def __init__(self, db: AsyncSession):
        if not self.__initialized:
            self.db = db
            self.repo = TaskRepository(db)
            self.lock = asyncio.Lock()
            self.tasks: List[BotTask] = []
            self.running_tasks: Dict[int, asyncio.Task] = {}
            self.__initialized = True

    @classmethod
    async def get_instance(cls, db: AsyncSession = None):
        if cls._instance is None:
            cls._instance = cls(db)
            if db is not None:
                await cls._instance.load_all_tasks()
                await cls._instance.reset_running_tasks()
        return cls._instance

    async def load_all_tasks(self):
        tasks = await self.repo.get_all()
        self.tasks = {task.id: task for task in tasks}
        logger.info(f"Загружено {log_color.CYAN}{len(self.tasks)}{log_color.RESET} задач в память")

    
    async def reset_running_tasks(self):
        async with self.lock:
            logger.info("Сброс выполняющихся и ошибочных задач в статус Pending...")

            # Получаем из БД все задачи со статусом Running или Error
            tasks_to_reset = await self.repo.get_tasks_by_statuses([TaskStatus.Running, TaskStatus.Error])
            
            for task in tasks_to_reset:
                task.status = TaskStatus.Pending
                await self.repo.update_task(task)
                
                # Обновляем кэш (self.tasks) — если уже загружен
                if task.id in self.tasks:
                    self.tasks[task.id].status = TaskStatus.Pending
                else:
                    self.tasks[task.id] = task

            logger.info(f"Сброшено {log_color.YELLOW}{len(tasks_to_reset)}{log_color.RESET} задач.")
        

    async def get_all_tasks(self):
        return list(self.tasks.values())

    async def add_task(self, task: BotTask):
        task.elapsedTime = task.time
        await self.repo.add_task(task)
        self.tasks[task.id] = task
        
        print(f"{log_color.RESET}")
        print(f"{log_color.GREEN}НОВАЯ ЗАДАЧА УСПЕШНО ДОБАВЛЕНА")
        print(f"{log_color.GREEN}ID: {log_color.BLUE}{task.id} ")
        print(f"{log_color.GREEN}Платформа: {log_color.BLUE}{task.platform} ")
        print(f"{log_color.GREEN}Активность: {log_color.BLUE}{task.activity} ")
        print(f"{log_color.GREEN}URL: {log_color.BLUE}{task.url} ")
        print(f"{log_color.GREEN}Всего ботов: {log_color.BLUE}{task.countBot:} ")
        print(f"{log_color.GREEN}Авторизованных ботов: {log_color.BLUE}{task.authBot} ")
        print(f"{log_color.GREEN}Время работы: {log_color.BLUE}{task.time} ")
        print(f"{log_color.GREEN}Время взлета: {log_color.BLUE}{task.rampUpTime} ")
        print(f"{log_color.GREEN}Статус: {log_color.BLUE}{task.status.name} ")
        print(f"{log_color.RESET}")

    async def pause_task(self, task_id: int):
        task = self.tasks.get(task_id)
        if task:
            task.status = TaskStatus.Paused
            await self.repo.update_task(task)
            await task.service.stop()
            logger.info(f"Задача {task_id} приостановлена")

            if task_id in self.running_tasks:
                self.running_tasks[task_id].cancel()
                del self.running_tasks[task_id]

    async def cancel_task(self, task_id: int):
        task = self.tasks.get(task_id)
        if task:
            task.status = TaskStatus.Cancelled
            await self.repo.update_task(task)
            await task.service.stop()
            logger.info(f"Задача {task_id} отменена")

            if task_id in self.running_tasks:
                self.running_tasks[task_id].cancel()
                del self.running_tasks[task_id]

    
    async def run_task(self, task_id: int):
        task:BotTask = self.tasks.get(task_id)
        if not task:
            logger.info(f"Ошибка: задача {task_id} не найдена")
            return
        if task.status == "Running":
            logger.info(f"Задача {task_id} уже запущена")
            return
        if task.status in [TaskStatus.Completed, TaskStatus.Cancelled]:
            logger.info(f"Задача {task_id} не может быть запущена (статус: {task.status})")
            return
        if task.elapsedTime and task.elapsedTime < datetime.time(hour=0, minute=1, second=0):
            logger.info(f"Задача {task_id} осталось меньше 1 минуты. Запуск не возможен")
            return
        try:
            task.status = TaskStatus.Running
            await self.repo.update_task(task)

            async def task_runner():
                try:
                    if task.platform.lower() == "twitch" and task.activity == "Зрители в эфир":
                        service: TwitchService = await TwitchService.create(self.db,
                            url=task.url,
                            count_bots=task.countBot,
                            auth_bots=task.authBot,
                            ramp_up_time=task.rampUpTime.minute
                        )
                        task.service = service
                        await self._wait_for_stream_online(task, service)
                        await self._run_task_timer(task, service)

                except asyncio.CancelledError:
                    task.status = TaskStatus.Paused
                    await self.repo.update_task(task)
                    logger.info(f"Задача {task.id} ПРИОСТАНОВЛЕНА! Осталось: {task.elapsedTime}")

                except Exception as e:
                    task.status = TaskStatus.Error
                    await self.repo.update_task(task)
                    logger.error(f"ОШИБКА в задаче {task.id}: {str(e)}")


            self.running_tasks[task_id] = asyncio.create_task(task_runner())
            
        except Exception as e:
            logger.error(f"ФАТАЛЬНАЯ ОШИБКА при запуске задачи {task_id}: {str(e)}")
            task.status = TaskStatus.Error
            await self.repo.update_task(task)
    
    async def _wait_for_stream_online(self, task: BotTask, service):

        count_check = 0

        logger.info(f"Запускается Twitch-сервис для задачи {task.id} (URL: {task.url})")


        check_interval = 10  # 2 минуты

        while True:
            count_check+=1
            try:
                is_online = await service.is_stream_live()
                if is_online:
                    logger.info(f"Стрим {task.url} в эфире. Начинаем выполнение задачи {task.id}.")
                    await service.start()
                    break
                else:
                    logger.info(f"Стрим {task.url} оффлайн. Повторная проверка через {check_interval} сек.")
                    await asyncio.sleep(check_interval)
            except asyncio.CancelledError:
                task.status = TaskStatus.Paused
                await self.repo.update_task(task)
                logger.info(f"Задача {task.id} ПРИОСТАНОВЛЕНА во время ожидания начала стрима.")
                raise # Важно — пробрасываем отмену дальше

    async def _run_task_timer(self, task: BotTask, service):
        def timedelta_to_time(td: timedelta) -> time:
            return time(
                hour=td.seconds // 3600,
                minute=(td.seconds % 3600) // 60,
                second=td.seconds % 60
            )

        total_seconds = (
            task.elapsedTime.hour * 3600 +
            task.elapsedTime.minute * 60 +
            task.elapsedTime.second
        )
        logger.info(f"Задача {task.id} запущена на {task.elapsedTime} ({total_seconds} секунд)")

        while total_seconds > 0:
            wait_time = min(60, total_seconds)
            logger.info(f"Задача {task.id}: следующий чек через {wait_time} сек...")
            await asyncio.sleep(wait_time)

            total_seconds -= wait_time
            task.elapsedTime = timedelta_to_time(timedelta(seconds=total_seconds))
            await self.repo.update_task(task)

            logger.info(f"Задача {task.id}: осталось {task.elapsedTime} ({total_seconds} сек)")

        task.status = TaskStatus.Completed
        await self.repo.update_task(task)
        await service.stop()
        logger.info(f"Задача {task.id} ВЫПОЛНЕНА!")
