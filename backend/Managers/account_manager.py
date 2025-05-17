import asyncio
from typing import Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from Data.Repositories.account_repository import AccountRepository
from Models.account import Account
from Logger.log import logger, log_color
from Models.proxy import Proxy
import os


class AccountManager:
    _instance = None

    def __new__(cls, db: AsyncSession):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__initialized = False
        return cls._instance
    
    def __init__(self, db: AsyncSession):
        if not self.__initialized:
            self.db = db
            self.repo = AccountRepository(db)
            self.lock = asyncio.Lock()
            self.accounts: List[Account] = []
            self.busy_accounts: Dict[int, bool] = {}
            self.__initialized = True

    @classmethod
    async def get_instance(cls, db: AsyncSession = None):
        if cls._instance is None:
            if db is None:
                raise ValueError("Database session is required for first initialization")
            cls._instance = cls(db)
            await cls._instance.load_accounts()
        return cls._instance
    
    async def load_accounts(self):
        """Загружает все аккаунты из базы в память"""
        async with self.lock:
            self.accounts = await self.repo.get_all()
            logger.info(f"Загружено {log_color.CYAN}{len(self.accounts)}{log_color.RESET} аккаунтов в память")

    async def get_free_account(self, platform: str) -> Optional[Account]:
        """
        Получает свободный валидный аккаунт для указанной платформы
        :param platform: 'twitch', 'youtube' или 'kick'
        :return: Account или None, если нет свободных
        """
        async with self.lock:
            for account in self.accounts:
                if (account.platform.lower() == platform.lower() 
                    and account.isValid 
                    and account.id not in self.busy_accounts):
                    
                    self.busy_accounts[account.id] = True
                    return account
            return None

    async def release_account_with_proxy(self, account_id: int):
        """Освобождает аккаунт и уменьшает счетчик активных аккаунтов на прокси"""
        async with self.lock:
            account = await self.get_account_by_id(account_id)
            if account and account.proxy_id:
                proxy = await self.proxy_manager.get_proxy_by_id(account.proxy_id)
                if proxy and proxy.active_accounts_count > 0:
                    proxy.active_accounts_count -= 1
                    await self.db.commit()
            self.busy_accounts.pop(account_id, None)

    async def get_multiple_free_accounts(self, platform: str, count: int) -> List[Account]:
        """
        Получает несколько свободных валидных аккаунтов
        :param platform: платформа
        :param count: сколько нужно аккаунтов
        :return: список аккаунтов (может быть меньше count)
        """
        async with self.lock:
            result = []
            for account in self.accounts:
                if len(result) >= count:
                    break
                    
                if (account.platform.lower() == platform.lower() 
                    and account.isValid 
                    and account.id not in self.busy_accounts):
                    
                    self.busy_accounts[account.id] = True
                    result.append(account)
            
            return result

    async def release_account(self, account_id: int):
        """Освобождает аккаунт по ID"""
        async with self.lock:
            self.busy_accounts.pop(account_id, None)

    async def release_all_accounts(self):
        """Освобождает все занятые аккаунты"""
        async with self.lock:
            self.busy_accounts.clear()

    async def is_account_busy(self, account_id: int) -> bool:
        """Проверяет, занят ли аккаунт"""
        async with self.lock:
            return account_id in self.busy_accounts

    async def add_account(self, account_data: dict) -> Account:
        """Добавляет новый аккаунт"""
        async with self.lock:
            account = Account(**account_data)
            self.accounts.append(account)
            await self.repo.add(account)
            await self.db.commit()
            return account

    async def update_account(self, account_id: int, update_data: dict) -> Optional[Account]:
        """Обновляет данные аккаунта"""
        async with self.lock:
            account = next((a for a in self.accounts if a.id == account_id), None)
            if account:
                for key, value in update_data.items():
                    setattr(account, key, value)
                await self.repo.update(account)
                await self.db.commit()
            return account

    async def delete_account(self, account_id: int) -> bool:
        """Удаляет аккаунт"""
        async with self.lock:
            account = next((a for a in self.accounts if a.id == account_id), None)
            if account:
                self.accounts.remove(account)
                await self.repo.delete(account_id)
                await self.db.commit()
                return True
            return False

    async def refresh_accounts(self):
        """Обновляет список аккаунтов из базы"""
        async with self.lock:
            self.accounts = await self.repo.get_all()
            logger.info(f"Аккаунты обновлены. Теперь в памяти {log_color.CYAN}{len(self.accounts)}{log_color.RESET} аккаунтов")

    async def get_account_by_id(self, account_id: int) -> Optional[Account]:
        """Возвращает аккаунт по ID"""
        async with self.lock:
            return next((a for a in self.accounts if a.id == account_id), None)
    
    async def get_account_by_proxy_id(self, proxy_id: int) -> Optional[Account]:
        """Возвращает аккаунт по ID"""
        async with self.lock:
            for accuont in self.accounts:
                if(accuont.proxy_id == proxy_id):
                    return accuont
        return None
    
    def get_account_by_proxy_id_sync(self, proxy_id: int) -> Optional[Account]:
        """Возвращает аккаунт по ID"""
        with self.lock:
            for accuont in self.accounts:
                if(accuont.proxy_id == proxy_id):
                    return accuont
        return None

    async def get_valid_accounts_count(self, platform: str) -> int:
        """Возвращает количество валидных аккаунтов для платформы"""
        async with self.lock:
            return sum(1 for a in self.accounts 
                     if a.platform.lower() == platform.lower() and a.isValid)
    def parse_account(self, line: str, platform: str) -> Account:
        """Парсинг строки аккаунта с различными форматами"""
        # Очистка строки от пробелов
        line = line.strip()
        
        # Форматы:
        # 1. login:auth-token
        # 2. login auth-token
        
        # Проверяем, есть ли разделитель
        if ':' in line:
            parts = line.split(':', 1)
        else:
            parts = line.split(None, 1)
        
        if len(parts) != 2:
            raise ValueError(f"Неверный формат аккаунта: {line}")
        
        user, token = parts
        
        return Account(
            user=user,
            token=token,
            platform=platform,
            cookies="",  # Если нужны куки, их можно будет добавить позже
            isValid=False
        )

    async def load_from_file(self, path: str, platform: str) -> int:
        """Загрузка аккаунтов из файла с указанием платформы"""
        if not os.path.exists(path):
            print(f"Файл не найден: {path}")
            return 0

        accounts: List[Account] = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    account = self.parse_account(line, platform)
                    accounts.append(account)
                except Exception as e:
                    print(f"Ошибка парсинга строки '{line}': {e}")
        
        await self.repo.add_accounts(accounts)
        return len(accounts)