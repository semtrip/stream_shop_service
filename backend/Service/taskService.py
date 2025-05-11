from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from Models.task import BotTask, TaskStatus
from Data.Repositories.taskRepository import TaskRepository
import asyncio
from datetime import time, timedelta
from log import logger

class TaskService:
    _instance: Optional['TaskService'] = None
    _initialized: bool = False

    def __new__(cls, db: AsyncSession = None):
        if cls._instance is None:
            cls._instance = super(TaskService, cls).__new__(cls)
        return cls._instance

    def __init__(self, db: AsyncSession = None):
        if not self._initialized and db is not None:
            self.db = db
            self.repo = TaskRepository(db)
            self.tasks: Dict[int, BotTask] = {}
            self.running_tasks: Dict[int, asyncio.Task] = {}
            self._initialized = True

    @classmethod
    async def get_instance(cls, db: AsyncSession = None):
        if cls._instance is None:
            cls._instance = cls(db)
            if db is not None:
                await cls._instance.load_all_tasks()
        return cls._instance

    async def get_all_tasks(self):
        return list(self.tasks.values())

    async def load_all_tasks(self):
        tasks = await self.repo.get_all()
        self.tasks = {task.id: task for task in tasks}
        logger.info(f"Загружено {len(self.tasks)} задач в память")

    async def add_task(self, task: BotTask):
        task.elapsedTime = task.time
        await self.repo.add_task(task)
        self.tasks[task.id] = task
        
        # Цвета для терминала
        class Colors:
            HEADER = '\033[95m'
            OKBLUE = '\033[94m'
            OKGREEN = '\033[92m'
            WARNING = '\033[93m'
            FAIL = '\033[91m'
            ENDC = '\033[0m'
            BOLD = '\033[1m'
            UNDERLINE = '\033[4m'
        
        # Выводим подробную информацию о задаче
        print(f"{Colors.ENDC}")
        print(f"{Colors.OKGREEN}НОВАЯ ЗАДАЧА УСПЕШНО ДОБАВЛЕНА")
        print(f"{Colors.OKGREEN}ID: {Colors.OKBLUE}{task.id} ")
        print(f"{Colors.OKGREEN}Платформа: {Colors.OKBLUE}{task.platform} ")
        print(f"{Colors.OKGREEN}Активность: {Colors.OKBLUE}{task.activity} ")
        print(f"{Colors.OKGREEN}URL: {Colors.OKBLUE}{task.url} ")
        print(f"{Colors.OKGREEN}Всего ботов: {Colors.OKBLUE}{task.countBot:} ")
        print(f"{Colors.OKGREEN}Авторизованных ботов: {Colors.OKBLUE}{task.authBot} ")
        print(f"{Colors.OKGREEN}Время работы: {Colors.OKBLUE}{task.time} ")
        print(f"{Colors.OKGREEN}Время взлета: {Colors.OKBLUE}{task.rampUpTime} ")
        print(f"{Colors.OKGREEN}Статус: {Colors.OKBLUE}{task.status.name} ")
        print(f"{Colors.ENDC}")

    async def pause_task(self, task_id: int):
        task = self.tasks.get(task_id)
        if task:
            task.status = TaskStatus.Paused
            await self.repo.update_task(task)
            logger.info(f"Задача {task_id} приостановлена")

            if task_id in self.running_tasks:
                self.running_tasks[task_id].cancel()
                del self.running_tasks[task_id]

    async def cancel_task(self, task_id: int):
        task = self.tasks.get(task_id)
        if task:
            task.status = TaskStatus.Cancelled
            await self.repo.update_task(task)
            logger.info(f"Задача {task_id} отменена")

            if task_id in self.running_tasks:
                self.running_tasks[task_id].cancel()
                del self.running_tasks[task_id]

    

    async def run_task(self, task_id: int):
        task = self.tasks.get(task_id)
        if not task:
            logger.info(f"Ошибка: задача {task_id} не найдена")
            return
        if task.status == "Running":
            logger.info(f"Задача {task_id} уже запущена")
            return
        if task.status in ["Cancelled", "Completed"]:
            logger.info(f"Задача {task_id} не может быть запущена (статус: {task.status})")
            return
        try:
            task.status = TaskStatus.Running
            await self.repo.update_task(task)

            def timedelta_to_str(td):
                total_seconds = int(td.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                return f"{hours:02}:{minutes:02}:{seconds:02}"

            def str_to_time(time_str):
                hours, minutes, seconds = map(int, time_str.split(":"))
                return time(hour=hours, minute=minutes, second=seconds)
    
            async def task_runner():
                try:
                    total_seconds = task.elapsedTime.hour * 3600 + task.elapsedTime.minute * 60 + task.elapsedTime.second
                    logger.info(f"Задача {task.id} запущена на {task.elapsedTime} ({total_seconds} секунд)")
                    
                    while total_seconds > 0:
                        wait_time = min(60, total_seconds)
                        logger.info(f"Задача {task.id}: следующий чек через {wait_time} сек...")
                        
                        await asyncio.sleep(wait_time)
                        
                        total_seconds -= wait_time
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        time_str = timedelta_to_str(timedelta(hours=int(hours), minutes=int(minutes), seconds=int(seconds)))
            
                        # Преобразуем строку в datetime.time
                        task.elapsedTime = str_to_time(time_str)
                        
                        await self.repo.update_task(task)
                        logger.info(f"Задача {task.id}: осталось {task.elapsedTime} ({total_seconds} сек)")
                    
                    task.status = TaskStatus.Completed
                    await self.repo.update_task(task)
                    logger.info(f"Задача {task.id} ВЫПОЛНЕНА!")
                    
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