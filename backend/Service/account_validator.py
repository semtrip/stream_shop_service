import asyncio
import aiohttp
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from Data.Repositories.account_repository import AccountRepository
from Models.account import Account
from Models.proxy import Proxy
from Logger.log import logger
from aiohttp_socks import ProxyConnector
from datetime import datetime


class AccountValidator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AccountRepository(db)
        self.proxy_manager = None

    @classmethod
    async def create(cls, db: AsyncSession):
        self = cls(db)
        from Managers.proxy_manager import ProxyManager
        self.proxy_manager = await ProxyManager.get_instance(db)
        return self

    def _format_proxy_url(self, proxy: Proxy) -> Optional[str]:
        """Форматирует прокси в URL для подключения"""
        if not proxy:
            return None
            
        proxy_type = proxy.type.lower()
        if proxy_type in ('http', 'https'):
            if proxy.username and proxy.password:
                return f"http://{proxy.username}:{proxy.password}@{proxy.ip}:{proxy.port}"
            return f"http://{proxy.ip}:{proxy.port}"
        elif proxy_type in ('socks', 'socks5'):
            if proxy.username and proxy.password:
                return f"socks5://{proxy.username}:{proxy.password}@{proxy.ip}:{proxy.port}"
            return f"socks5://{proxy.ip}:{proxy.port}"
        return None

    async def validate_account_twitch(self, account: Account, proxy: Proxy) -> Tuple[bool, Optional[str]]:
        """Валидация Twitch аккаунта через прокси"""
        url = "https://id.twitch.tv/oauth2/validate"
        headers = {"Authorization": f"OAuth {account.token}"}

        try:
            proxy_url = self._format_proxy_url(proxy)
            if not proxy_url:
                return False, "Invalid proxy configuration"

            connector = None
            if proxy.type.lower() in ('socks', 'socks5'):
                connector = ProxyConnector.from_url(proxy_url)

            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                    ssl=False
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return bool(data.get("login")), None
                    return False, f"HTTP error {resp.status}"

        except Exception as e:
            error_msg = str(e)
            if "Expected HTTP/" in error_msg:
                error_msg = "SOCKS proxy connection failed"
            return False, error_msg

    async def validate_account_youtube(self, account: Account, proxy: Proxy) -> Tuple[bool, Optional[str]]:
        """Валидация YouTube аккаунта через прокси"""
        # TODO: Реализовать валидацию YouTube аккаунтов
        return False, "YouTube validation not implemented"

    async def validate_account_kick(self, account: Account, proxy: Proxy) -> Tuple[bool, Optional[str]]:
        """Валидация Kick аккаунта через прокси"""
        # TODO: Реализовать валидацию Kick аккаунтов
        return False, "Kick validation not implemented"

    async def validate_account(self, account: Account) -> Account:
        """Основной метод валидации аккаунта"""
        try:
            if self.proxy_manager is None:
                from Managers.proxy_manager import ProxyManager
                self.proxy_manager = await ProxyManager.get_instance(self.db)

            platform = account.platform.lower()

            # Получаем свободный прокси для этой платформы
            proxy = await self.proxy_manager.get_free_proxy_not_account(platform)
            if not proxy:
                account.isValid = False
                await self.repo.update_account(account)
                return account

            # Выбираем метод валидации в зависимости от платформы
            if platform == 'twitch':
                is_valid, error = await self.validate_account_twitch(account, proxy)
            elif platform == 'youtube':
                is_valid, error = await self.validate_account_youtube(account, proxy)
            elif platform == 'kick':
                is_valid, error = await self.validate_account_kick(account, proxy)
            else:
                is_valid, error = False, f"Unsupported platform: {platform}"

            account.isValid = is_valid
            account.lastChecked = datetime.utcnow()

            # Если аккаунт валиден, привязываем к нему прокси
            if is_valid:
                account.proxy_id = proxy.id
                proxy.active_accounts_count += 1
                await self.db.commit()
                logger.info(f"[{platform.capitalize()}] Account {account.user} - VALID (Proxy: {proxy.ip}:{proxy.port})")
            else:
                account.last_error = error
                logger.info(f"[{platform.capitalize()}] Account {account.user} - INVALID ({error})")

            await self.repo.update_account(account)
            await self.proxy_manager.release_proxy(proxy.id)
            return account

        except Exception as e:
            logger.error(f"Error validating account {account.user}: {str(e)}")
            account.isValid = False
            await self.repo.update_account(account)
            return account

    async def validate_accounts(self, accounts: List[Account], max_concurrent: int = 10) -> List[Account]:
        """Валидация списка аккаунтов с ограничением одновременных запросов"""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def validate_one(account: Account):
            async with semaphore:
                return await self.validate_account(account)

        tasks = [asyncio.create_task(validate_one(account)) for account in accounts]
        results = await asyncio.gather(*tasks)
        return results

    async def validate_all_accounts(self, max_concurrent: int = 10) -> List[Account]:
        """Валидация всех аккаунтов в базе данных"""
        async with self.db.begin():
            accounts = await self.repo.get_all()
            logger.info(f"Starting validation of {len(accounts)} accounts")
            validated_accounts = await self.validate_accounts(accounts, max_concurrent)
            await self.db.commit()
            logger.info(f"Completed validation of {len(validated_accounts)} accounts")
            return validated_accounts