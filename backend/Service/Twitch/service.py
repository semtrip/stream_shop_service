import threading
from streamlink import Streamlink
from fake_useragent import UserAgent
from typing import List
import random
import asyncio

from Managers.proxy_manager import ProxyManager
from Managers.account_manager import AccountManager
from sqlalchemy.ext.asyncio import AsyncSession
from .bot import TwitchBot
from .botAuth import TwitchBotAuth
from Logger.log import logger, log_color

ua = UserAgent()

class TwitchService():
    def __init__(self, account_manager, proxy_manager, url, count_bots, auth_bots, rump_time, proxies):
        self.account_manager:AccountManager = account_manager
        self.proxy_manager:ProxyManager = proxy_manager

        self.channel_name = self.extract_channel_name(url)
        self.channel_url = f"https://www.twitch.tv/{self.channel_name}"
        self.count_bots = count_bots
        self.auth_bots = auth_bots
        self.rump_time = rump_time
        self.bots:List[TwitchBot] = []
        self.threads = []
        self.proxies = proxies
        self.lock = threading.Lock()
        self.running = False
        self.stop_event = asyncio.Event()
        self.stream_session = Streamlink()
        self.stream_session.set_option("http-headers", {
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": ua.random,
            "Client-ID": "ewvlchtxgqq88ru9gmfp1gmyt6h2b93",
            "Referer": "https://www.google.com/"
        })
        logger.info(f"Twitch service иницилизирован для {self.channel_name}")
        

    @classmethod
    async def create(cls, db: AsyncSession, url, count_bots, auth_bots, rump_time=5):
        account_manager = await AccountManager.get_instance(db)
        proxy_manager = await ProxyManager.get_instance(db)
        proxies = await proxy_manager.get_multiple_free_proxies('twitch', count_bots)
        #proxy_account = await proxy_manager.get_free_proxy_and_account('twitch')
        #logger.info(proxy_account)
        return cls(account_manager, proxy_manager, url, count_bots, auth_bots, rump_time, proxies)

    async def is_stream_live(self):
        logger.info(f"Проверка онлайна стрима {log_color.CYAN}{self.channel_name}{log_color.RESET}")
        try:
            streams = self.stream_session.streams(self.channel_url)
            if(bool(streams)):
                logger.info(f"[TWITCH isStreamLive] stream {log_color.CYAN}{self.channel_name}{log_color.RESET} - {log_color.GREEN}Online{log_color.RESET}")
            else:
                logger.info(f"[TWITCH isStreamLive] stream {log_color.CYAN}{self.channel_name}{log_color.RESET} - {log_color.RED}Offline{log_color.RESET}")
            return bool(streams)
        except Exception as e:
            logger.error(f"[TWITCH isStreamLive] Ошибка проверки онлайна стрима {self.channel_name}: {e}")
            return False  

    async def start(self):
        if self.bots:
            logger.debug(f"[TWITCH] Боты, уже запущенные для url {self.channel_name}.")
            return

        logger.info(f"[TWITCH] Запуск {self.count_bots} ботов в течение {self.rump_time} времени")
        logger.info(f"[TWITCH] Получено прокси: {len(self.proxies)}")
        total_delay_range= self.rump_time.minute * 60
        for i in range(self.count_bots- self.auth_bots):
            proxy = self.proxies[i % len(self.proxies)]
            bot = TwitchBot(self.stream_session, self.channel_name, proxy, self.stop_event, id=i)
            self.bots.append(bot)

        for i in range(self.auth_bots):
            proxy = self.proxies[i % len(self.proxies)]
            account = await self.account_manager.get_account_by_proxy_id(proxy_id=proxy.id)
            if(account and account.token and account.user):
                bot = TwitchBotAuth(self.stream_session, self.channel_name, proxy, account, self.stop_event, id=i)
                self.bots.append(bot)

        async def launch_with_random_delay(bot: TwitchBot):
            delay = random.uniform(0, total_delay_range)
            await asyncio.sleep(delay)
            await bot.start()

        tasks = [launch_with_random_delay(bot) for bot in self.bots]
        await asyncio.gather(*tasks)
        asyncio.create_task(self.monitor_bots())


    async def monitor_bots(self, check_interval=60):
        while not self.stop_event.is_set():
            for i, bot in enumerate(self.bots):
                if bot.is_dead():
                    logger.warning(f"[MONITOR] Bot ID:[{bot.id}] неактивен. Перезапуск...")

                    # ✅ Проверка лимита перезапусков
                    if getattr(bot, "restart_attempts", 0) >= getattr(bot, "max_restarts", 5):
                        logger.error(f"[MONITOR] Bot ID:[{bot.id}] достиг лимита перезапусков. Пропускаем.")
                        continue

                    # Остановить старый бот
                    await bot.stop()

                    # Заново создать и перезапустить
                    proxy = self.proxies[i % len(self.proxies)]

                    if isinstance(bot, TwitchBotAuth):
                        account = await self.account_manager.get_account_by_proxy_id(proxy_id=proxy.id)
                        if account:
                            new_bot = TwitchBotAuth(self.stream_session, self.channel_name, proxy, account, self.stop_event, id=bot.id)
                        else:
                            continue
                    else:
                        new_bot = TwitchBot(self.stream_session, self.channel_name, proxy, self.stop_event, id=bot.id)

                    # ✅ Копируем и увеличиваем счётчик перезапусков
                    new_bot.restart_attempts = getattr(bot, "restart_attempts", 0) + 1
                    new_bot.max_restarts = getattr(bot, "max_restarts", 5)

                    self.bots[i] = new_bot
                    asyncio.create_task(new_bot.start())

            await asyncio.sleep(check_interval)
            
    async def stop(self):
        if not self.bots:
            logger.info(f"[TWITCH] Нет ботов для остановки {self.channel_name}")
            return

        logger.info(f"[TWITCH] Остановка {len(self.bots)} ботов для {self.channel_name}...")
        self.stop_event.set()

        # Дождаться завершения всех ботов, если у них есть async-метод завершения
        stop_tasks = [bot.stop() for bot in self.bots if hasattr(bot, "stop") and asyncio.iscoroutinefunction(bot.stop)]
        if stop_tasks:
            await asyncio.gather(*stop_tasks)

        self.bots.clear()
        self.stop_event = asyncio.Event()  # сбрасываем событие на будущее
        logger.info(f"[TWITCH] Все боты остановлены для {self.channel_name}")

    def extract_channel_name(self, input_str):
        """Получает название канала"""
        if "twitch.tv/" in input_str:
            parts = input_str.split("twitch.tv/")
            channel = parts[1].split("/")[0].split("?")[0]
            return channel.lower()
        return input_str.lower()