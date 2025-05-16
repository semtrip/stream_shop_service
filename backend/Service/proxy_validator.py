import asyncio
import aiohttp
import socket
from typing import List, Optional, Tuple, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from Models.proxy import Proxy
import ssl
from Logger.log import logger, log_color
from aiohttp_socks import ProxyType
from fake_useragent import UserAgent
import urllib.parse
import socks
import socket
from aiohttp_socks import ProxyConnector
from Data.Repositories.proxy_repository import ProxyRepository


ua = UserAgent()


class ProxyValidator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        self.repo = ProxyRepository(db)

    async def test_tcp_connection(self, proxy: Proxy, timeout: float = 5.0) -> bool:
        try:
            proxy_type = self.get_socks_type(proxy.type)
            sock = socks.socksocket()
            sock.set_proxy(
                proxy_type,
                proxy.ip,
                proxy.port,
                username=proxy.username if proxy.username else None,
                password=proxy.password if proxy.password else None
            )
            sock.settimeout(timeout)
            sock.connect(('8.8.8.8', 53))
            sock.close()
            logger.info(f"Прокси {proxy.ip}:{proxy.port} TCP - OK")
            return True
        except Exception as e:
            logger.warning(f"Прокси {proxy.ip}:{proxy.port} TCP - FAIL: {e}")
            return False

    def get_socks_type(self, proxy_type: str) -> int:
        proxy_type = proxy_type.lower()
        if proxy_type == 'socks4':
            return socks.SOCKS4
        elif proxy_type == 'socks5':
            return socks.SOCKS5
        elif proxy_type in ['http', 'https']:
            return socks.HTTP
        else:
            return socks.SOCKS5

    def prepare_proxy_url(self, proxy: Proxy) -> str:
        proxy_type = proxy.type.lower()
        if proxy_type not in ['http', 'https', 'socks4', 'socks5']:
            proxy_type = 'socks5'

        if proxy.username and proxy.password:
            username = urllib.parse.quote(proxy.username)
            password = urllib.parse.quote(proxy.password)
            proxy_url = f"{proxy_type}://{username}:{password}@{proxy.ip}:{proxy.port}"
        else:
            proxy_url = f"{proxy_type}://{proxy.ip}:{proxy.port}"

        return proxy_url

    async def test_http_connection(self, proxy: Proxy, url: str, timeout: float = 10.0) -> bool:
        try:
            from aiohttp_socks import ProxyConnector, ProxyType

            typeProxy = {
                "socks5": ProxyType.SOCKS5,
                "socks4": ProxyType.SOCKS4
            }

            headers = {
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "DNT": "1",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": ua.random,
                "Client-ID": "ewvlchtxgqq88ru9gmfp1gmyt6h2b93",
                "Referer": "https://www.google.com/"
            }

            if proxy.type in typeProxy:
                # SOCKS proxies — use aiohttp_socks
                connector = ProxyConnector(
                    proxy_type=typeProxy[proxy.type],
                    host=proxy.ip,
                    port=proxy.port,
                    username=proxy.username,
                    password=proxy.password
                )
                session_args = {"connector": connector}
            elif proxy.type == "http":
                # HTTP proxy — use regular aiohttp
                proxy_url = f"http://{proxy.username}:{proxy.password}@{proxy.ip}:{proxy.port}" \
                            if proxy.username else f"http://{proxy.ip}:{proxy.port}"
                session_args = {}
            else:
                logger.error(f"Неподдерживаемый тип прокси: {proxy.type}")
                return False

            async with aiohttp.ClientSession(**session_args) as session:
                try:
                    request_args = {
                        "url": url,
                        "timeout": aiohttp.ClientTimeout(total=timeout),
                        "headers": headers
                    }
                    if proxy.type == "http":
                        request_args["proxy"] = proxy_url

                    async with session.get(**request_args) as response:
                        if response.status in [200, 204, 206, 301, 302, 303, 307, 308]:
                            try:
                                content = await response.text(encoding='utf-8', errors='ignore')
                                return len(content.strip()) > 10
                            except Exception as e:
                                logger.warning(f"Proxy {proxy.ip}:{proxy.port} ошибка чтения контента: {e}")
                                return True
                        logger.warning(f"Proxy {proxy.ip}:{proxy.port} вернул статус {response.status}")
                        return False
                except Exception as e:
                    logger.error(f"Proxy {proxy.ip}:{proxy.port} ошибка в запросе: {type(e).__name__}: {e}")
                    return False

        except Exception as e:
            logger.error(f"Proxy {proxy.ip}:{proxy.port} неизвестная ошибка: {e}")
            return False


    async def validate_proxy(self, proxy: Proxy) -> Dict[str, bool]:
        results = {
            'twitchValid': False,
            'youtubeValid': False,
            'kickValid': False
        }

        # tcp_valid = await self.test_tcp_connection(proxy)
        # if not tcp_valid:
        #     logger.info(f"Proxy {proxy.ip}:{proxy.port} не прошел TCP-тест")
        #     return results

        platforms = [
            ('twitchValid', 'https://www.twitch.tv/'),
            #('youtubeValid', 'https://www.youtube.com/'),
            #('kickValid', 'https://kick.com/')
        ]

        for platform_key, url in platforms:
            try:
                results[platform_key] = await self.test_http_connection(proxy, url)
            except Exception as e:
                logger.error(f"Ошибка валидации для {url}: {e}")
                results[platform_key] = False
        
        return results

    async def validate_proxies(self, proxies: List[Proxy], max_concurrent: int = 10):
        semaphore = asyncio.Semaphore(max_concurrent)

        async def validate_with_semaphore(proxy):
            async with semaphore:
                try:
                    validation_results = await self.validate_proxy(proxy)
                    proxy.twitchValid = validation_results['twitchValid']
                    proxy.youtubeValid = validation_results['youtubeValid']
                    proxy.kickValid = validation_results['kickValid']
                    proxy.lastChecked = datetime.now()
                    logger.info(f"Прокси {proxy.ip}:{proxy.port} для twitch - {"OK" if proxy.twitchValid  else "Invalid"} youtube - {"OK" if proxy.youtubeValid  else "Invalid"} kick - {"OK" if proxy.kickValid  else "Invalid"} ")
                    return proxy
                except Exception as e:
                    logger.error(f"Ошибка при валидации прокси {proxy.ip}:{proxy.port}: {e}")
                    return None

        validation_tasks = [validate_with_semaphore(proxy) for proxy in proxies]
        results = await asyncio.gather(*validation_tasks)
        return [r for r in results if r is not None]

    async def validate_all_proxies(self, isNew, max_concurrent: int = 10):
        try:
            proxies = []
            if(isNew) :
                proxies = await self.repo.get_all_invalid()
            else:
                proxies = await self.repo.get_all()    
            logger.info(f"Начало валидации {len(proxies)} прокси")
            validated_proxies = await self.validate_proxies(proxies, max_concurrent)
            await self.db.commit()
            logger.info(f"Завершена валидация {len(validated_proxies)} прокси")
            return validated_proxies
        except Exception as e:
            logger.error(f"Ошибка запуска валидации прокси: {e}")
