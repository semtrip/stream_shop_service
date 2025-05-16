import asyncio, re, os
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from Models.proxy import Proxy
from Models.account import Account
from Data.Repositories.proxy_repository import ProxyRepository
from Logger.log import logger, log_color
from datetime import datetime
class ProxyManager:
    _instance = None

    def __new__(cls, db: AsyncSession):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__initialized = False
        return cls._instance

    def __init__(self, db: AsyncSession):
        if not self.__initialized:
            self.db = db
            self.repo = ProxyRepository(db)
            self.lock = asyncio.Lock()
            self.proxies: List[Proxy] = []
            self.busy_proxies: Dict[int, bool] = {}
            self.__initialized = True

    @classmethod
    async def get_instance(cls, db: AsyncSession = None):
        if cls._instance is None:
            cls._instance = cls(db)
            if db is not None:
                await cls._instance.load_proxies()
        return cls._instance

    async def load_proxies(self):
        """Загружает все прокси из базы в память"""
        async with self.lock:
            self.proxies = await self.repo.get_all()
            logger.info(F"Загружено {log_color.CYAN}{len(self.proxies)}{log_color.RESET} прокси в память")

    async def get_free_proxy(self, platform: str) -> Optional[Proxy]:
        """
        Получает свободную прокси для указанной платформы.
        
        :param platform: 'twitch', 'youtube' или 'kick'
        :return: Proxy или None, если нет свободных
        """
        async with self.lock:
            for proxy in self.proxies:
                if not self._is_proxy_valid_for_platform(proxy, platform):
                    continue
                    
                if proxy.id not in self.busy_proxies:
                    self.busy_proxies[proxy.id] = True
                    proxy.useds += 1
                    await self.db.commit()
                    return proxy
            return None
    

    async def get_free_proxy_and_account(self, platform: str) -> Optional[Proxy]:
        """
        Получает свободную прокси для указанной платформы с аккаунтом.
        
        :param platform: 'twitch', 'youtube' или 'kick'
        :return: Proxy или None, если нет свободных
        """
        async with self.lock:
            for proxy in self.proxies:
                if not self._is_proxy_valid_for_platform_and_account(proxy, platform):
                    continue
                if proxy.id not in self.busy_proxies:
                    self.busy_proxies[proxy.id] = True
                    proxy.useds += 1
                    await self.db.commit()
                    return proxy
            return None
        
    async def get_free_proxy_not_account(self, platform: str) -> Optional[Proxy]:
        """
        Получает свободную прокси для указанной платформы с аккаунтом.
        
        :param platform: 'twitch', 'youtube' или 'kick'
        :return: Proxy или None, если нет свободных
        """
        async with self.lock:
            for proxy in self.proxies:
                if not self._is_proxy_valid_for_platform(proxy, platform):
                    continue

                if proxy.active_accounts_count > 0:
                    continue
                    
                if proxy.id not in self.busy_proxies:
                    self.busy_proxies[proxy.id] = True
                    proxy.useds += 1
                    await self.db.commit()
                    return proxy
            return None

    async def bind_proxy_to_account(self, proxy: Proxy, account: Account):
        """
        Привязывает аккаунт к прокси:
        - обновляет объект в памяти
        - увеличивает счётчик активных аккаунтов
        - сохраняет в БД
        """
        async with self.lock:
            for current_proxy in self.proxies:
                if(current_proxy.id == proxy.id):
                    current_proxy.active_accounts_count += 1


    async def get_multiple_free_proxies(self, platform: str, count: int) -> List[Proxy]:
        """
        Получает несколько свободных прокси для платформы.
        
        :param platform: 'twitch', 'youtube' или 'kick'
        :param count: сколько нужно прокси
        :return: список прокси (может быть меньше count)
        """
        async with self.lock:
            result = []
            for proxy in self.proxies:
                if len(result) >= count:
                    break
                    
                if (self._is_proxy_valid_for_platform(proxy, platform) 
                    and proxy.id not in self.busy_proxies):
                    self.busy_proxies[proxy.id] = True
                    proxy.useds += 1
                    result.append(proxy)
            
            if result:
                await self.db.commit()
            return result

    def _is_proxy_valid_for_platform(self, proxy: Proxy, platform: str) -> bool:
        """Проверяет валидность прокси для платформы"""
        if platform == 'twitch':
            return proxy.twitchValid
        elif platform == 'youtube':
            return proxy.youtubeValid
        elif platform == 'kick':
            return proxy.kickValid
        return False

    def _is_proxy_valid_for_platform_and_account(self, proxy: Proxy, platform: str) -> bool:
        """Проверяет, валидна ли прокси и есть ли аккаунт для платформы"""
        valid_flag = getattr(proxy, f"{platform}Valid", False)
        has_account = any(acc.platform == platform for acc in proxy.accounts)
        return valid_flag and has_account


    def _is_proxy_valid_for_platform_not_account(self, proxy: Proxy, platform: str) -> bool:
        """Проверяет, валидна ли прокси и нет аккаунта по платформе"""
        valid_flag = getattr(proxy, f"{platform}Valid", False)
        has_account = any(acc.platform == platform for acc in proxy.accounts)
        return valid_flag and not has_account


    async def release_proxy(self, proxy_id: int):
        """Освобождает прокси по ID"""
        async with self.lock:
            self.busy_proxies.pop(proxy_id, None)

    async def release_all_proxies(self):
        """Освобождает все занятые прокси"""
        async with self.lock:
            self.busy_proxies.clear()

    async def is_proxy_busy(self, proxy_id: int) -> bool:
        """Проверяет, занята ли прокси"""
        async with self.lock:
            return proxy_id in self.busy_proxies

    async def get_proxy_by_id(self, proxy_id: int) -> Optional[Proxy]:
        """Возвращает прокси по ID (если есть в памяти)"""
        async with self.lock:
            for proxy in self.proxies:
                if proxy.id == proxy_id:
                    return proxy
            return None
    def parse_proxy(self, line: str, proxy_type: str) -> Proxy:
        """Парсинг строки прокси с различными форматами"""
        # Очистка строки от пробелов
        line = line.strip()
        
        # Форматы:
        # 1. ip:port
        # 2. ip:port:username:password
        # 3. username:password@ip:port
        
        # Разбор username:password@ip:port
        at_match = re.match(r'^(.+?)@(.+):(\d+)$', line)
        if at_match:
            username, ip, port = at_match.groups()
            if ':' in username:
                username, password = username.split(':')
            else:
                password = None
            return Proxy(
                ip=ip, 
                port=int(port), 
                username=username, 
                password=password, 
                type=proxy_type, 
                twitchValid=False,
                youtubeValid=False,
                kickValid=False,
                lastChecked = datetime.now()
            )
        
        # Разбор ip:port:username:password
        parts = line.split(':')
        if len(parts) == 2:
            ip, port = parts
            username, password = None, None
        elif len(parts) == 4:
            ip, port, username, password = parts
        else:
            raise ValueError(f"Неверный формат прокси: {line}")
        
        return Proxy(
            ip=ip, 
            port=int(port), 
            username=username, 
            password=password, 
            type=proxy_type, 
            twitchValid=False,
            youtubeValid=False,
            kickValid=False,
            lastChecked = datetime.now()
        )

    async def load_from_file(self, path: str, proxy_type: str) -> int:
        """Загрузка прокси из файла с указанием типа"""
        if not os.path.exists(path):
            print(f"Файл не найден: {path}")
            return 0

        proxies: List[Proxy] = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    proxy = self.parse_proxy(line, proxy_type)
                    proxies.append(proxy)
                except Exception as e:
                    print(f"Ошибка парсинга строки '{line}': {e}")
        
        return await self.repo.bulk_insert_proxies(proxies)