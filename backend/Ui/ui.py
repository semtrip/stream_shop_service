import inquirer
from log import logger

class MenuUI:
    def __init__(self):
        self.data = None

    def show_main_menu(self):
        """Показывает главное меню и возвращает выбранный пункт."""
        questions = [
            inquirer.List('action',
                    message="StreamShop service [MAIN MENU]",
                    choices=[
                        "Загрузить аккаунты",
                        "Загрузить прокси",
                        "Проверить аккаунты",
                        "Проверить прокси",
                        "Создать задачу",
                        "Посмотреть задачи",
                        "Работа с задачами",
                        "Работа с логами",
                        "Выход"
                    ]
                ),
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
        """Отображает сообщение в консоль."""
        logger.info(message)
        
    def show_exit_message(self):
        """Сообщение перед выходом из программы."""
        logger.info("Выход из программы...")

    @staticmethod
    def clear_screen():
        """Очищает экран консоли"""
        import os
        import platform
        if platform.system() == "Windows":
            os.system('cls')
        else:
            os.system('clear')
