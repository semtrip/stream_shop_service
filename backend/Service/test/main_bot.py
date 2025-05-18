import asyncio
import time
import uuid
from streamlink import Streamlink
import aiohttp
from aiohttp_socks import ProxyConnector
from Logger.log import logger
import contextlib


TWITCH_CLIENT_ID = "kimne78kx3ncx6wki5h1ko"
IRC_SERVER = "irc.chat.twitch.tv"
IRC_PORT = 6667


class MainBot:
    def __init__(self, channel, proxy, stop_event, bot_id, executor, account=None, audio_only=True):
        self.channel = channel
        self.proxy_obj = proxy
        self.stop_event = stop_event
        self.id = bot_id
        self.account = account
        self.audio_only = audio_only
        self.executor = executor
        self.running = False

        self.streamlink = Streamlink()
        self._configure_streamlink()

        self.last_active = time.time()
        self.stream_fd = None
        self.aiohttp_session = None
        self.irc_reader = None
        self.irc_writer = None
        self.device_id = str(uuid.uuid4())

    def _configure_streamlink(self):
        proxy_url = self._get_proxy_url()
        if proxy_url:
            self.streamlink.set_option("http-proxy", proxy_url)

        self.streamlink.set_option("twitch-disable-ads", True)
        self.streamlink.set_option("twitch-disable-hosting", True)

        if self.audio_only:
            self.streamlink.set_option("stream-segment-threads", 1)
            self.streamlink.set_option("hls-segment-ignore-names", ["*"])

    async def _get_stream(self):
        try:
            streams = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.streamlink.streams(f"https://www.twitch.tv/{self.channel}")
            )

            if not streams:
                logger.warning(f"[BOT {self.id}] Нет доступных потоков")
                return None

            stream = (
                streams.get("audio_only") or
                streams.get("160p") or
                next(iter(streams.values()))
            )

            return stream.open()
        except Exception as e:
            logger.error(f"[BOT {self.id}] Ошибка получения потока: {e}")
            return None

    async def start(self):
        if self.running:
            return
        self.running = True
        logger.info(f"[BOT {self.id}] Запуск (аудио: {self.audio_only})")

        proxy_url = self._get_proxy_url()
        connector = ProxyConnector.from_url(proxy_url) if proxy_url else None
        self.aiohttp_session = aiohttp.ClientSession(
            connector=connector,
            headers={"Client-ID": TWITCH_CLIENT_ID}
        )

        irc_task = None

        while not self.stop_event.is_set():
            try:
                self.stream_fd = await self._get_stream()
                if not self.stream_fd:
                    await asyncio.sleep(5)
                    continue

                logger.info(f"[BOT {self.id}] Поток подключен")

                if self.account and hasattr(self.account, 'token'):
                    irc_task = asyncio.create_task(self._irc_loop())

                while not self.stop_event.is_set():
                    try:
                        await asyncio.get_event_loop().run_in_executor(
                            self.executor,
                            lambda: self.stream_fd.read(8192)
                        )
                        self.last_active = time.time()
                        await asyncio.sleep(1)
                    except Exception as e:
                        logger.warning(f"[BOT {self.id}] Ошибка чтения: {e}")
                        break

            except Exception as e:
                logger.error(f"[BOT {self.id}] Ошибка: {e}")
            finally:
                if self.stream_fd:
                    await asyncio.get_event_loop().run_in_executor(self.executor, self.stream_fd.close)
                if irc_task:
                    irc_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await irc_task
                await asyncio.sleep(3)

        await self.stop()

    async def _irc_loop(self):
        try:
            self.irc_reader, self.irc_writer = await asyncio.open_connection(
                IRC_SERVER, IRC_PORT
            )
            self.irc_writer.write(f"PASS oauth:{self.account.token}\r\n".encode())
            self.irc_writer.write(f"NICK {self.account.user}\r\n".encode())
            self.irc_writer.write(f"JOIN #{self.channel}\r\n".encode())
            await self.irc_writer.drain()
            logger.info(f"[BOT {self.id}] IRC подключен")

            while not self.stop_event.is_set():
                line = await self.irc_reader.readline()
                if not line:
                    break
                if line.startswith(b"PING"):
                    self.irc_writer.write(b"PONG :tmi.twitch.tv\r\n")
                    await self.irc_writer.drain()

        except Exception as e:
            logger.warning(f"[BOT {self.id}] IRC ошибка: {e}")
        finally:
            if self.irc_writer:
                self.irc_writer.close()
                await self.irc_writer.wait_closed()

    async def stop(self):
        if not self.running:
            return

        self.running = False
        try:
            if self.stream_fd:
                await asyncio.get_event_loop().run_in_executor(self.executor, self.stream_fd.close)
            if self.aiohttp_session:
                await self.aiohttp_session.close()
            if self.irc_writer:
                self.irc_writer.close()
                await self.irc_writer.wait_closed()
        except Exception as e:
            logger.error(f"[BOT {self.id}] Ошибка остановки: {e}")
        finally:
            logger.info(f"[BOT {self.id}] Остановлен")

    def is_dead(self):
        return not self.running or (time.time() - self.last_active > 25)

    def _get_proxy_url(self):
        if not self.proxy_obj:
            return None

        proxy_type = getattr(self.proxy_obj, 'type', 'socks5')
        ip = getattr(self.proxy_obj, 'ip', '')
        port = getattr(self.proxy_obj, 'port', '')
        username = getattr(self.proxy_obj, 'username', '')
        password = getattr(self.proxy_obj, 'password', '')

        if username and password:
            return f"{proxy_type}://{username}:{password}@{ip}:{port}"
        return f"{proxy_type}://{ip}:{port}"
