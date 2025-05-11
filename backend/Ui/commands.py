from prettytable import PrettyTable
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import random

from Data.Repositories.accountRepository import AccountRepository
from Data.Repositories.proxyRepository import ProxyRepository
from Service.taskService import TaskService
from Models.task import BotTask, TaskStatus
from log_streamer import LogStreamer

class Commands():
    def __init__(self, db: AsyncSession, menu_ui):
        self.db = db
        self.menu_ui = menu_ui
        self.task_service = None
        self.log_streamer = LogStreamer()
        self.logger = self.log_streamer.logger
        

    async def initialize(self):
        """Асинхронная инициализация сервиса задач"""
        self.task_service = await TaskService.get_instance(self.db)
        return self

    async def load_accounts(self):
        repo = AccountRepository(self.db)
        accounts = await repo.get_all()
        print(f"Загружено {len(accounts)} аккаунтов")


    async def load_proxies(self):
        repo = ProxyRepository(self.db)
        proxies = await repo.get_all()
        print(f"Загружено {len(proxies)} прокси")


    async def check_accounts(self):
        repo = AccountRepository(self.db)
        valid_accounts = await repo.get_valid_accounts()
        print(f"Проверено {len(valid_accounts)} аккаунтов")


    async def check_proxies(self):
        repo = ProxyRepository(self.db)
        valid_proxies = await repo.get_valid_proxies()
        print(f"Проверено {len(valid_proxies)} прокси")

    @staticmethod
    def get_valid_time():
        """
        Функция для получения времени от пользователя в формате часов.
        Время должно быть от 1 до 8 часов.
        Возвращает объект типа time.
        """
        while True:
            try:
                time_in_hours = int(input("Введите время выполнения задачи (в часах, от 1 до 8): "))
                if 1 <= time_in_hours <= 8:
                    # Преобразуем в формат HH:MM:SS
                    time_str = f"{time_in_hours:02}:00:00"
                    return datetime.strptime(time_str, '%H:%M:%S').time()  # Преобразуем в объект time
                else:
                    print("Введите значение от 1 до 8.")
            except ValueError:
                print("Пожалуйста, введите целое число.")

    @staticmethod
    def get_valid_rump_time():
        """
        Функция для получения времени от пользователя в формате минут.
        Время должно быть от 1 до 30 минут.
        Возвращает объект типа time.
        """
        while True:
            try:
                time_in_minutes = int(input("Введите время взлета (в минутах, от 1 до 30): "))
                if 1 <= time_in_minutes <= 30:
                    # Преобразуем в формат HH:MM:SS
                    time_str = f"00:{time_in_minutes:02}:00"
                    return datetime.strptime(time_str, '%H:%M:%S').time()  # Преобразуем в объект time
                else:
                    print("Введите значение от 1 до 30.")
            except ValueError:
                print("Пожалуйста, введите целое число.")

    @staticmethod
    def set_count_bot():
        """
        Функция для получения количесвта ботов.
        Количесвто должно быть от 10 до 1000 шт.
        Возвращает объект типа int.
        """
        while True:
            try:
                countBots = int(input("Введите количество ботов (от 10 до 1000): "))
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
            ["YouTube", "Twitch", "Kick"]
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
                url = input(f"[Создание задачи] [{platform}] [{activity}] Введите URL трансляции: ")
            elif activity == 'Просмотры видео/shorts':
                url = input(f"[Создание задачи] [{platform}] [{activity}] Введите URL видео/shorts: ")
            elif activity == 'Подписчики':
                url = input(f"[Создание задачи] [{platform}] [{activity}] Введите URL канала: ")
            elif activity == 'Лайки':
                url = input(f"[Создание задачи] [{platform}] [{activity}] Введите URL видео/shorts: ")
        elif platform in ('Twitch', 'Kick'):
            if activity == 'Зрители в эфир':
                url = input(f"[Создание задачи] [{platform}] [{activity}] Введите URL канала: ")
            elif activity == 'Просмотр видео/клипов':
                url = input(f"[Создание задачи] [{platform}] [{activity}] Введите URL видео/клипа: ")
            elif activity == 'Фолловеры':
                url = input(f"[Создание задачи] [{platform}] [{activity}] Введите URL канала: ")
        
        countBot = self.set_count_bot()
        # Создание задачи
        task = BotTask(
            status=TaskStatus.Pending,
            platform=platform,
            activity=activity,
            url=url,
            countBot=countBot,
            activeBot=0,
            authBot=self.calculate_authorized_bots(countBot),
            time=self.get_valid_time(),
            rampUpTime=self.get_valid_rump_time()
        )
        self.menu_ui.clear_screen()
        await self.task_service.add_task(task)


    async def task_menu(self):
        while True:
            choice = self.menu_ui.show_sub_menu("[Меню задач] Выберите действие", ["Запустить задачу", "Поставить на паузу", "Отменить задачу", "Назад"])
            if choice == "Запустить задачу":
                task_id = int(input("Введите ID задачи для запуска: "))
                await self.task_service.run_task(task_id)
                break
            elif choice == "Поставить на паузу":
                task_id = int(input("Введите ID задачи для паузы: "))
                await self.task_service.pause_task(task_id)
                break
            elif choice == "Отменить задачу":
                task_id = int(input("Введите ID задачи для отмены: "))
                await self.task_service.cancel_task(task_id)
                break
            elif choice == "Назад":
                break


    async def view_tasks(self):
        if self.task_service is None:
            print("Ошибка: TaskService не инициализирован")
            return
        table = PrettyTable()
        table.field_names = ["ID", "Платформа", "Статус", "Ботов", "Ботов в работе", "Оставшееся время работы"]

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
            tasks = await self.task_service.get_all_tasks()
            for task in tasks:
                table.add_row([
                    task.id,
                    task.platform,
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
                log_files = self.log_streamer.get_log_files()
                if not log_files:
                    print("Логи отсутствуют.")
                    continue

                file_names = [f.name for f in log_files]
                selected = self.menu_ui.show_sub_menu("Выберите лог-файл для просмотра", file_names + ["Назад"])
                if selected == "Назад":
                    continue

                selected_file = self.log_streamer.logs_dir / selected
                try:
                    await self.log_streamer.stream_logs(selected_file)
                except RuntimeError as e:
                    print(str(e))

            elif choice == "Логи в реальном времени":
                try:
                    await self.log_streamer.stream_logs(self.log_streamer.log_file)
                except RuntimeError as e:
                    print(str(e))

            elif choice == "Очистить логи":
                self.log_streamer.clear_old_logs()

            elif choice == "Назад":
                break



    async def showMenu(self):
        while True:
            action = self.menu_ui.show_main_menu()
            if action == "Загрузить аккаунты":
                await self.load_accounts()
            elif action == "Загрузить прокси":
                await self.load_proxies()
            elif action == "Проверить аккаунты":
                await self.check_accounts()
            elif action == "Проверить прокси":
                await self.check_proxies()
            elif action == "Создать задачу":
                await self.create_task()
            elif action == "Посмотреть задачи":
                await self.view_tasks()
            elif action == "Работа с задачами":
                await self.task_menu()
            elif action == "Работа с логами":
                await self.showLogsMenu()
            elif action == "Выход":
                self.menu_ui.show_exit_message()
                return
        