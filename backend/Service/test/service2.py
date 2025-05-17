import asyncio
import contextlib
from contextlib import asynccontextmanager
from typing import List, Optional

from streamlink import Streamlink
from fake_useragent import UserAgent
from sqlalchemy.ext.asyncio import AsyncSession

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
        self.ramp_up_time = ramp_up_time           # В минутах
        self.proxies = proxies

        if len(self.proxies) < self.count_bots:
            raise RuntimeError("Недостаточно прокси для запуска всех ботов")

        self.bots: List[MainBot] = []
        self._stop_event = asyncio.Event()
        self._monitor_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

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
        db: AsyncSession,
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
            live = bool(self.stream_session.streams(self.channel_url))
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
        if self.bots:
            logger.warning("Bots already running")
            return

        logger.info(f"Starting {self.count_bots} bots (ramp-up {self.ramp_up_time} min)")

        auth_accounts = []
        for i in range(self.auth_bots):
            proxy = self.proxies[i]
            acc = await self.account_manager.get_account_by_proxy_id(proxy.id)
            auth_accounts.append(acc if acc and acc.token and acc.user else None)

        for i in range(self.count_bots):
            proxy = self.proxies[i]
            account = auth_accounts[i] if i < self.auth_bots else None
            bot = MainBot(
                channel=self.channel_name,
                proxy=proxy,  # Объект с полями: type, ip, port, username, password
                stop_event=self._stop_event,
                bot_id=i,
                account=account  # Объект с полями user, token (опционально)
            )
            self.bots.append(bot)

        self._monitor_task = asyncio.create_task(self._monitor_bots())

        total_delay = self.ramp_up_time * 60  # секунды
        interval = total_delay / self.count_bots if self.count_bots > 0 else 0

        for i, bot in enumerate(self.bots):
            delay = interval * i
            asyncio.create_task(self._spawn_bot(bot, delay))

    async def _monitor_bots(self):
        while not self._stop_event.is_set():
            try:
                async with self._bot_lock():
                    for idx, bot in enumerate(self.bots):
                        if bot.is_dead():
                            logger.warning(f"Bot {bot.id} dead → restarting")
                            await bot.stop()
                            new_bot = MainBot(
                                    channel=self.channel_name,
                                    proxy=self.proxies[bot.id],  # Объект с полями: type, ip, port, username, password
                                    stop_event=self._stop_event,
                                    bot_id=bot.id,
                                    account=bot.account  # Объект с полями user, token (опционально)
                                )
                            self.bots[idx] = new_bot
                            asyncio.create_task(new_bot.start())
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(5)

    async def stop(self):
        logger.info("Stopping all bots…")
        self._stop_event.set()

        if self._monitor_task:
            self._monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitor_task

        async with self._bot_lock():
            await asyncio.gather(*(b.stop() for b in self.bots), return_exceptions=True)
            self.bots.clear()

        self._stop_event.clear()
        logger.info("All bots stopped")
