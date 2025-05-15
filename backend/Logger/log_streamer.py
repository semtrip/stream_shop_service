import asyncio
import os
import logging
from pathlib import Path
from datetime import datetime

try:
    import keyboard  # для обработки Esc
except ImportError:
    keyboard = None


class LogStreamer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LogStreamer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, logs_dir="logs", lines=25, interval=1):
        if self._initialized:
            return

        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        self.interval = interval
        self.lines = lines
        self.running = True

        now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = self.logs_dir / f"{now_str}_log.log"
        self.error_file = self.logs_dir / f"{now_str}_error.log"

        self._configure_logging()
        self._initialized = True

    def _configure_logging(self):
        formatter = logging.Formatter(
            "[{asctime}] [{levelname}] {message}",
            datefmt="%Y-%m-%d %H:%M:%S",
            style="{"
        )

        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)

        error_handler = logging.FileHandler(self.error_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger = logging.getLogger("main")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        logger.addHandler(file_handler)
        logger.addHandler(error_handler)
        logger.addHandler(console_handler)
        logger.propagate = False

        self._logger = logger  # Приватный атрибут

    @property
    def logger(self):
        return self._logger 

    def get_log_files(self):
        return sorted(self.logs_dir.glob("*.log"), key=lambda f: f.stat().st_mtime)

    def tail(self, path):
        if not path.exists():
            return ["[Файл логов не найден]"]
        with open(path, 'r', encoding="utf-8", errors="ignore") as f:
            try:
                return f.readlines()[-self.lines:]
            except Exception as e:
                return [f"[Ошибка чтения: {e}]"]

    async def esc_listener(self):
        """Асинхронная задача для слушания клавиши ESC."""
        while self.running:
            if keyboard.is_pressed("esc"):
                print("\n[Выход из режима просмотра логов]")
                self.running = False
                break
            await asyncio.sleep(0.1)

    async def stream_logs(self, path):
        if keyboard is None:
            raise RuntimeError("Модуль 'keyboard' не установлен. Установите его с помощью 'pip install keyboard'.")

        print(f"[Лог-файл: {path.name}] Нажмите ESC для выхода.\n")
        self.running = True

        # Не будем сразу сбрасывать вывод
        while self.running:
            if keyboard.is_pressed("esc"):
                print("\n[Выход из режима просмотра логов]")
                break

            os.system('cls' if os.name == 'nt' else 'clear')  # Очистка экрана
            print(f"[{path.name}] (ESC - выход)\n")
            
            # Получаем последние строки лога
            for line in self.tail(path):
                print(line.rstrip())

            # Пауза, чтобы не было излишней нагрузки на систему
            await asyncio.sleep(self.interval)

        # Завершаем вывод
        print("\n[Завершено отображение логов]")


    def clear_old_logs(self):
        log_files = list(self.logs_dir.glob("*.log"))
        current_files = {self.log_file.name, self.error_file.name}
        files_to_delete = [f for f in log_files if f.name not in current_files]

        if not files_to_delete:
            print("Нет файлов для удаления.")
            return

        print(f"Будет удалено {len(files_to_delete)} файлов. Уверены? (y/n): ", end="")
        if input().lower() != "y":
            print("Очистка отменена.")
            return

        # Закрываем все хендлеры логгера
        loggers = [logging.getLogger(), logging.getLogger("error")]
        for logger in loggers:
            handlers = logger.handlers[:]
            for handler in handlers:
                handler.close()
                logger.removeHandler(handler)

        # Теперь можно удалить
        deleted_count = 0
        for f in files_to_delete:
            try:
                f.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"Не удалось удалить {f.name}: {e}")

        print(f"Удалено {deleted_count} файлов.")
        # Повторная инициализация логгера (перезапись хендлеров)
        self._configure_logging()
