from prettytable import PrettyTable
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import random
import aioconsole
import asyncio
from typing import List

from Managers.task_manager import TaskManager
from Managers.proxy_manager import ProxyManager
from Managers.account_manager import AccountManager
from Models.task import BotTask, TaskStatus
from Service.proxy_validator import ProxyValidator
from Service.account_validator import AccountValidator
from Logger.log import logger, log_streamer
from Ui.ui import MenuUI

class Commands():
    def __init__(self, db: AsyncSession, task_manager, account_manager, proxy_manager):
        self.db = db
        self.menu_ui:MenuUI = MenuUI()
        self.task_manager:TaskManager = task_manager
        self.account_manager:AccountManager = account_manager
        self.proxy_manager:ProxyManager = proxy_manager

    @classmethod
    async def create(cls, db: AsyncSession):
        task_manager = await TaskManager.get_instance(db)
        account_manager = await AccountManager.get_instance(db)
        proxy_manager = await ProxyManager.get_instance(db)
        return cls(db, task_manager, account_manager, proxy_manager)

    async def load_proxies(self):
        # Выбор типа прокси
        proxy_type = self.menu_ui.show_sub_menu(
            "Выберите тип прокси:", 
            ["http", "socks4", "socks5"]
        )
        
        # Выбор файла с прокси
        file_path = self.menu_ui.select_file_from_load_dir("Выберите файл с прокси")
        if not file_path:
            return

        try:
            loaded_count = await self.proxy_manager.load_from_file(file_path, proxy_type)
            self.menu_ui.display_message(f"Загружено прокси: {loaded_count}")
        except Exception as e:
            self.menu_ui.display_message(f"Ошибка при загрузке прокси: {e}")

    async def load_accounts(self):
        # Выбор платформы
        platform = self.menu_ui.show_sub_menu(
            "Выберите платформу:", 
            ["YouTube", "Twitch", "Kick"]
        )
        
        # Выбор файла с аккаунтами
        file_path = self.menu_ui.select_file_from_load_dir("Выберите файл с аккаунтами")
        if not file_path:
            return

        try:
            loaded_count = await self.account_manager.load_from_file(file_path, platform)
            self.menu_ui.display_message(f"Загружено аккаунтов: {loaded_count}")
        except Exception as e:
            self.menu_ui.display_message(f"Ошибка при загрузке аккаунтов: {e}")

    async def check_accounts(self):
        """Запуск валидации всех аккаунтов"""
        try:
            account_validator = AccountValidator(self.db)
            await account_validator.validate_all_accounts()
        except Exception as e:
            logger.error(f"Ошибка при валидации аккаунтов: {e}")


    async def check_proxies(self):
        """Запуск валидации всех прокси"""
        try:
            proxy_validator = ProxyValidator(self.db)
            await proxy_validator.validate_all_proxies()
        except Exception as e:
            self.menu_ui.display_message(f"Ошибка при валидации прокси: {e}")

    @staticmethod
    async def get_valid_time():
        """
        Функция для получения времени от пользователя в формате часов.
        Время должно быть от 1 до 8 часов.
        Возвращает объект типа time.
        """
        while True:
            try:
                time_in_hours = int(await aioconsole.ainput("Введите время выполнения задачи (в часах, от 1 до 8): "))
                if 1 <= time_in_hours <= 8:
                    # Преобразуем в формат HH:MM:SS
                    time_str = f"{time_in_hours:02}:00:00"
                    return datetime.strptime(time_str, '%H:%M:%S').time()  # Преобразуем в объект time
                else:
                    print("Введите значение от 1 до 8.")
            except ValueError:
                print("Пожалуйста, введите целое число.")

    @staticmethod
    async def get_valid_rump_time():
        """
        Функция для получения времени от пользователя в формате минут.
        Время должно быть от 1 до 30 минут.
        Возвращает объект типа time.
        """
        while True:
            try:
                time_in_minutes = int(await aioconsole.ainput("Введите время взлета (в минутах, от 1 до 30): "))
                if 1 <= time_in_minutes <= 30:
                    # Преобразуем в формат HH:MM:SS
                    time_str = f"00:{time_in_minutes:02}:00"
                    return datetime.strptime(time_str, '%H:%M:%S').time()  # Преобразуем в объект time
                else:
                    print("Введите значение от 1 до 30.")
            except ValueError:
                print("Пожалуйста, введите целое число.")

    @staticmethod
    async def set_count_bot():
        """
        Функция для получения количесвта ботов.
        Количесвто должно быть от 10 до 1000 шт.
        Возвращает объект типа int.
        """
        while True:
            try:
                countBots = int(await aioconsole.ainput("Введите количество ботов (от 10 до 1000): "))
                if 10 <= countBots <= 1000:
                    return countBots
                else:
                    print("Введите значение от 10 до 1000.")
            except ValueError:
                print("Пожалуйста, введите целое число.")

    @staticmethod
    def calculate_authorized_bots(countBot):
        """
        Функция для расчета количества авторизованных ботов.
        Количество авторизованных ботов должно быть в пределах от 40% до 60% от общего количества ботов.
        """
        min_auth_bots = int(countBot * 0.4)
        max_auth_bots = int(countBot * 0.6)
        return random.randint(min_auth_bots, max_auth_bots)


    async def create_task(self):
        """Функция для создания задачи с запросом всех данных"""
        platform = self.menu_ui.show_sub_menu(
            "[Создание задачи] Выберите платформу:", 
            ["YouTube", "Twitch", "Kick", "Отмена"]
        )
        
        # Выбор активности в зависимости от платформы
        if platform == 'YouTube':
            activity = self.menu_ui.show_sub_menu(
                f"[Создание задачи] [{platform}] Выберите активность:",
                ["Зрители в эфир", "Просмотры видео/shorts", "Подписчики", "Лайки"]
            )
        elif platform in ('Twitch', 'Kick'):
            activity = self.menu_ui.show_sub_menu(
                f"[Создание задачи] [{platform}] Выберите активность:",
                ["Зрители в эфир", "Просмотр видео/клипов", "Фолловеры"]
            )
        
        # Ввод URL в зависимости от платформы и активности
        if platform == 'YouTube':
            if activity == 'Зрители в эфир':
                url = await aioconsole.ainput(f"[Создание задачи] [{platform}] [{activity}] Введите URL трансляции: ")
            elif activity == 'Просмотры видео/shorts':
                url = await aioconsole.ainput(f"[Создание задачи] [{platform}] [{activity}] Введите URL видео/shorts: ")
            elif activity == 'Подписчики':
                url = await aioconsole.ainput(f"[Создание задачи] [{platform}] [{activity}] Введите URL канала: ")
            elif activity == 'Лайки':
                url = await aioconsole.ainput(f"[Создание задачи] [{platform}] [{activity}] Введите URL видео/shorts: ")
        elif platform in ('Twitch', 'Kick'):
            if activity == 'Зрители в эфир':
                url = await aioconsole.ainput(f"[Создание задачи] [{platform}] [{activity}] Введите URL канала: ")
            elif activity == 'Просмотр видео/клипов':
                url = await aioconsole.ainput(f"[Создание задачи] [{platform}] [{activity}] Введите URL видео/клипа: ")
            elif activity == 'Фолловеры':
                url = await aioconsole.ainput(f"[Создание задачи] [{platform}] [{activity}] Введите URL канала: ")
        elif platform == 'Отмена':
            self.menu_ui.clear_screen()
            return
        
        countBot = await self.set_count_bot()
        # Создание задачи
        task = BotTask(
            status=TaskStatus.Pending,
            platform=platform,
            activity=activity,
            url=url,
            countBot=countBot,
            activeBot=0,
            authBot=self.calculate_authorized_bots(countBot),
            time= await self.get_valid_time(),
            rampUpTime= await self.get_valid_rump_time()
        )
        self.menu_ui.clear_screen()
        await self.task_manager.add_task(task)


    async def task_menu(self):
        while True:
            choice = self.menu_ui.show_sub_menu("[Меню задач] Выберите действие", ["Запустить задачу", "Поставить на паузу", "Отменить задачу", "Назад"])
            if choice == "Запустить задачу":
                task_id = int(await aioconsole.ainput("Введите ID задачи для запуска: "))
                await self.task_manager.run_task(task_id)
                break
            elif choice == "Поставить на паузу":
                task_id = int(await aioconsole.ainput("Введите ID задачи для паузы: "))
                await self.task_manager.pause_task(task_id)
                break
            elif choice == "Отменить задачу":
                task_id = int(await aioconsole.ainput("Введите ID задачи для отмены: "))
                await self.task_manager.cancel_task(task_id)
                break
            elif choice == "Назад":
                break


    async def view_tasks(self):
        if self.task_manager is None:
            print("Ошибка: TaskService не инициализирован")
            return
        table = PrettyTable()
        table.field_names = ["ID", "Платформа", "Активность", "URL","Статус", "Ботов", "Ботов в работе", "Оставшееся время работы"]

        def getStatusTask(status):
            status_map = {
                TaskStatus.Pending: 'Ожидание запуска',
                TaskStatus.Running: 'Работает',
                TaskStatus.Cancelled: 'Отменена', 
                TaskStatus.Completed: 'Выполнена',
                TaskStatus.Error: 'Ошибка в работе',
                TaskStatus.Paused: 'Пауза'
            }
            return status_map.get(status, "Неизвестно")

        try:
            tasks:List[BotTask] = await self.task_manager.get_all_tasks()
            for task in tasks:
                table.add_row([
                    task.id,
                    task.platform,
                    task.activity,
                    task.url[:50],
                    getStatusTask(task.status),
                    task.countBot,
                    task.activeBot,
                    str(task.elapsedTime) if task.elapsedTime else "N/A"
                ])
            print(table)
        except Exception as e:
            print(f"Ошибка при получении задач: {e}")


    async def showLogsMenu(self):
        while True:
            choice = self.menu_ui.show_sub_menu("[Меню логов]", ["Исторические логи", "Логи в реальном времени", "Очистить логи", "Назад"])

            if choice == "Исторические логи":
                log_files = log_streamer.get_log_files()
                if not log_files:
                    print("Логи отсутствуют.")
                    continue

                file_names = [f.name for f in log_files]
                selected = self.menu_ui.show_sub_menu("Выберите лог-файл для просмотра", file_names + ["Назад"])
                if selected == "Назад":
                    continue

                selected_file = log_streamer.logs_dir / selected
                try:
                    await log_streamer.stream_logs(selected_file)
                except RuntimeError as e:
                    print(str(e))

            elif choice == "Логи в реальном времени":
                try:
                    await log_streamer.stream_logs(log_streamer.log_file)
                except RuntimeError as e:
                    print(str(e))

            elif choice == "Очистить логи":
                log_streamer.clear_old_logs()

            elif choice == "Назад":
                break

    async def showAccountsMenu(self):
        while True:
            choice = self.menu_ui.show_sub_menu("[Меню аккаунтов]", ["Загрузка аккаутов", "Проверка аккаунтов", "Назад"])

            if choice == "Загрузка аккаутов":
                await self.load_accounts()
            elif choice == "Проверка аккаунтов":
                await self.check_accounts()
            elif choice == "Назад":
                break

    async def showProxyMenu(self):
            while True:
                choice = self.menu_ui.show_sub_menu("[Меню прокси]", ["Загрузка прокси", "Проверка прокси", "Назад"])

                if choice == "Загрузка прокси":
                    await self.load_proxies()
                elif choice == "Проверка прокси":
                    await self.check_proxies()
                elif choice == "Назад":
                    break

    async def showTaskMenu(self):
            while True:
                choice = self.menu_ui.show_sub_menu("[Меню задач]", ["Создать задачу", "Список задач", "Управление задачами", "Назад"])

                if choice == "Создать задачу":
                    await self.create_task()
                elif choice == "Список задач":
                    await self.view_tasks()
                elif choice == "Управление задачами":
                    await self.task_menu()
                elif choice == "Назад":
                    break

    async def showMenu(self):
        while True:
            action = self.menu_ui.show_main_menu()
            if action == "Аккаунты":
                await self.showAccountsMenu()
            elif action == "Прокси":
                await self.showProxyMenu()
            elif action == "Задачи":
                await self.showTaskMenu()
            elif action == "Логи":
                await self.showLogsMenu()
            elif action == "Выход":
                self.menu_ui.show_exit_message()
                return
        