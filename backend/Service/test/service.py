import asyncio
import contextlib
from contextlib import asynccontextmanager
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor

from streamlink import Streamlink
from fake_useragent import UserAgent

from Managers.proxy_manager import ProxyManager
from Managers.account_manager import AccountManager
from .main_bot import MainBot
from Logger.log import logger, log_color


ua = UserAgent()


class TwitchService:
    def __init__(
        self,
        account_manager: AccountManager,
        proxy_manager: ProxyManager,
        url: str,
        count_bots: int,
        auth_bots: int,
        ramp_up_time: int,
        proxies: List,
    ):
        self.account_manager = account_manager
        self.proxy_manager = proxy_manager
        self.channel_name = self._extract_channel_name(url)
        self.channel_url = f"https://www.twitch.tv/{self.channel_name}"

        self.count_bots = count_bots
        self.auth_bots = min(auth_bots, count_bots)
        self.ramp_up_time = ramp_up_time
        self.proxies = proxies

        if len(self.proxies) < self.count_bots:
            raise RuntimeError("Недостаточно прокси для запуска всех ботов")

        self.bots: List[MainBot] = []
        self._stop_event = asyncio.Event()
        self._monitor_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        self.executor = ThreadPoolExecutor(max_workers=max(50, self.count_bots * 2))
        self.stream_session = Streamlink()
        self.stream_session.set_option(
            "http-headers",
            {
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "DNT": "1",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": ua.random,
                "Client-ID": "ewvlchtxgqq88ru9gmfp1gmyt6h2b93",
                "Referer": "https://www.google.com/",
            },
        )
        logger.info(f"Initialized TwitchService for channel: {self.channel_name}")

    @classmethod
    async def create(
        cls,
        db,
        url: str,
        count_bots: int,
        auth_bots: int,
        ramp_up_time: int = 5,
    ):
        am = await AccountManager.get_instance(db)
        pm = await ProxyManager.get_instance(db)
        proxies = await pm.get_multiple_free_proxies("twitch", count_bots)
        return cls(am, pm, url, count_bots, auth_bots, ramp_up_time, proxies)

    @staticmethod
    def _extract_channel_name(src: str) -> str:
        return (
            src.split("twitch.tv/")[1].split("/")[0].split("?")[0].lower()
            if "twitch.tv/" in src
            else src.lower()
        )

    @asynccontextmanager
    async def _bot_lock(self):
        async with self._lock:
            yield

    async def is_stream_live(self) -> bool:
        logger.info(f"Checking stream status for {log_color.CYAN}{self.channel_name}{log_color.RESET}")
        try:
            streams = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.stream_session.streams(self.channel_url)
            )
            live = bool(streams)
            st = "Online" if live else "Offline"
            logger.info(f"[Stream Status] {self.channel_name} - {st}")
            return live
        except Exception as e:
            logger.error(f"Error checking stream: {e}")
            return False

    async def _spawn_bot(self, bot: MainBot, delay: float):
        if delay > 0:
            logger.info(f"Bot ID:[{bot.id}] will start in {delay:.1f} seconds")
            await asyncio.sleep(delay)
        if self._stop_event.is_set():
            logger.info(f"Bot ID:[{bot.id}] start aborted (stop event set)")
            return
        logger.info(f"Bot ID:[{bot.id}] starting now")
        await bot.start()
        logger.info(f"Bot ID:[{bot.id}] started successfully")

    async def start(self):
        logger.info(f"Starting TwitchService with {self.count_bots} bots")
        self._stop_event.clear()
        self.bots.clear()

        # Prepare bots
        for i in range(self.count_bots):
            proxy = self.proxies[i]
            account = None
            if i < self.auth_bots:
                account = await self.account_manager.get_account_by_proxy_id(proxy.id)
            bot = MainBot(
                channel=self.channel_name,
                proxy=proxy,
                stop_event=self._stop_event,
                bot_id=i,
                executor=self.executor,
                account=account,
                audio_only=True,
            )
            self.bots.append(bot)

        # Ramp-up logic (равномерный старт ботов)
        if self.ramp_up_time > 0:
            delay_between = self.ramp_up_time / max(self.count_bots - 1, 1)
        else:
            delay_between = 0

        # Запуск ботов с задержкой
        tasks = []
        for idx, bot in enumerate(self.bots):
            delay = idx * delay_between
            tasks.append(asyncio.create_task(self._spawn_bot(bot, delay)))

        # Запуск мониторинга состояния ботов
        self._monitor_task = asyncio.create_task(self._monitor_bots())

        await asyncio.gather(*tasks)

    async def _monitor_bots(self):
        logger.info("Starting bots monitoring task")
        try:
            while not self._stop_event.is_set():
                async with self._bot_lock():
                    online_bots = [bot for bot in self.bots if bot.running and not bot.is_dead()]
                    count_online = len(online_bots)
                    logger.info(f"Online bots: {count_online}/{self.count_bots}")

                    # Если ботов слишком мало, можно попытаться их перезапустить
                    if count_online < self.count_bots * 0.95:
                        logger.warning(f"Недостаточно онлайн ботов ({count_online}), проверяем и рестартуем")
                        for bot in self.bots:
                            if not bot.running or bot.is_dead():
                                logger.info(f"Перезапуск бота ID:{bot.id}")
                                asyncio.create_task(bot.start())

                await asyncio.sleep(5)
        except asyncio.CancelledError:
            logger.info("Мониторинг ботов отменен")
        except Exception as e:
            logger.error(f"Ошибка в мониторинге ботов: {e}")

    async def stop(self):
        logger.info("Stopping TwitchService and all bots")
        self._stop_event.set()

        if self._monitor_task:
            self._monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitor_task

        # Останавливаем всех ботов параллельно
        await asyncio.gather(*(bot.stop() for bot in self.bots), return_exceptions=True)
        logger.info("All bots stopped")
