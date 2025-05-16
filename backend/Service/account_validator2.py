from typing import Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
import aiohttp
from Data.Repositories.account_repository import AccountRepository
from Logger.log import logger, log_color
from Models.account import Account
from Models.proxy import Proxy
import asyncio
from Managers.proxy_manager import ProxyManager


class AccountValidator():
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AccountRepository(db)
        self.proxy_manager = ProxyManager(db)

    async def validate_account_twitch(self, account: Account, proxy: Proxy) -> Tuple[bool, Optional[str]]:
        url = "https://id.twitch.tv/oauth2/validate"
        headers = {"Authorization": f"OAuth {account.token}"}
        
        try:
            proxy_url = self._format_proxy_url(proxy)
            if not proxy_url:
                return False, "Invalid proxy configuration"

            connector = None
            if proxy.type.lower() in ('socks', 'socks5'):
                from aiohttp_socks import ProxyConnector
                connector = ProxyConnector.from_url(proxy_url)

            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                    ssl=False
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json() #return client_id:Str, login:Str, scopes:List, user_id:Str, expires_in:Int
                        return bool(data.get("login")), None
                    return False, f"HTTP error {resp.status}"
                    
        except Exception as e:
            error_msg = str(e)
            # Упрощаем сообщение об ошибке для логов
            if "Expected HTTP/" in error_msg:
                error_msg = "SOCKS proxy connection failed"
            return False, error_msg
        finally:
            await self.proxy_manager.release_proxy(proxy.id)

    def _format_proxy_url(self, proxy: Proxy) -> Optional[str]:
        """Форматирует URL прокси для aiohttp с учетом особенностей SOCKS"""
        if not proxy:
            return None
            
        if proxy.type.lower() in ('http', 'https'):
            return f"http://{proxy.ip}:{proxy.port}"
            
        elif proxy.type.lower() in ('socks', 'socks5'):
            if proxy.username and proxy.password:
                return f"socks5://{proxy.username}:{proxy.password}@{proxy.ip}:{proxy.port}"
            return f"socks5://{proxy.ip}:{proxy.port}"
        
        return None
    
    async def validate_accounts(self, accounts: List[Account], max_concurrent: int = 10):
        semaphore = asyncio.Semaphore(max_concurrent)

        async def validate_with_semaphore(account: Account):
            async with semaphore:
                try:
                    match account.platform.lower():
                        case 'twitch':
                            proxy = await self.proxy_manager.get_free_proxy_not_account('twitch')
                            if not proxy:
                                logger.warning(f"[Twitch] Нет свободных прокси для аккаунта {account.user}")
                                account.isValid = False
                                account.last_error = "No available proxies"
                                return account
                            
                            is_valid, error = await self.validate_account_twitch(account, proxy)
                            account.isValid = is_valid
                            account.proxy_id = proxy.id if is_valid else None
                            
                            if is_valid:
                                await self.proxy_manager.bind_proxy_to_account(proxy, account)
                                logger.info(f"[Twitch] [{account.id}] Аккаунт {log_color.BLUE}{account.user}{log_color.RESET} - {log_color.GREEN}OK{log_color.RESET})")
                            else:
                                logger.info(f"[Twitch] [{account.id}] Аккаунт {log_color.BLUE}{account.user}{log_color.RESET} - {log_color.RED}Invalid{log_color.RESET} ({log_color.YELLOW}{error}{log_color.RESET})")
                            
                        case 'youtube':
                            account.isValid = False
                            account.last_error = "Platform not supported yet"
                        case 'kick':
                            account.isValid = False
                            account.last_error = "Platform not supported yet"
                        case _:
                            account.isValid = False
                            account.last_error = "Unknown platform"
                    
                    return account
                
                except Exception as e:
                    logger.error(f"\033[31m[ERROR]\033[0m Ошибка при валидации аккаунта {account.user}: {str(e)}")
                    account.isValid = False
                    account.last_error = str(e)
                    return account

        validation_tasks = [validate_with_semaphore(account) for account in accounts]
        results = await asyncio.gather(*validation_tasks)
        
        try:
            await self.db.commit()
        except Exception as e:
            logger.error(f"\033[31m[DB ERROR]\033[0m Ошибка при сохранении результатов: {str(e)}")
            await self.db.rollback()
            raise
        
        return [r for r in results if r is not None]

    async def validate_all_accounts(self, max_concurrent: int = 10):
        accounts = await self.repo.get_all_twitch()
        logger.info(f"\033[34m[INFO]\033[0m Начало валидации {len(accounts)} аккаунтов")
        validated_accounts = await self.validate_accounts(accounts, max_concurrent)
        return validated_accounts