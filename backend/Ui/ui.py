import inquirer
import os

from Logger.log import logger

class MenuUI:
    def __init__(self):
        self.data = None
        self.ensure_load_files_dir()

    def ensure_load_files_dir(self):
        os.makedirs("load_files", exist_ok=True)

    def show_main_menu(self):
        questions = [
            inquirer.List('action',
                message="StreamShop service [MAIN MENU]",
                choices=[
                    "Аккаунты",
                    "Прокси",
                    "Задачи",
                    "Логи",
                    "Выход"
                ]),
        ]
        answers = inquirer.prompt(questions)
        return answers['action']

    def show_sub_menu(self, title, items):
        questions = [
            inquirer.List('action', message=title, choices=items),
        ]
        answers = inquirer.prompt(questions)
        return answers['action']

    def display_message(self, message):
        logger.info(message)

    def show_exit_message(self):
        logger.info("Выход из программы...")

    def list_files_in_load_dir(self):
        files = os.listdir("load_files")
        return [f for f in files if os.path.isfile(os.path.join("load_files", f))]

    def select_file_from_load_dir(self, title="Выберите файл для загрузки"):
        files = self.list_files_in_load_dir()
        if not files:
            self.display_message("Нет доступных файлов в папке 'load_files'.")
            return None

        selected = self.show_sub_menu(title, files)
        return os.path.join("load_files", selected)

    @staticmethod
    def clear_screen():
        import platform
        if platform.system() == "Windows":
            os.system('cls')
        else:
            os.system('clear')
