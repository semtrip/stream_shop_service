import asyncio
import random
import time
from streamlink import Streamlink
import aiohttp
from aiohttp_socks import ProxyConnector
import uuid
from Logger.log import logger

TWITCH_CLIENT_ID = "kimne78kx3ncx6wki5h1ko"
IRC_SERVER = "irc.chat.twitch.tv"
IRC_PORT = 6667

class MainBot:
    def __init__(self, channel, proxy, stop_event, bot_id, account=None, audio_only=True):
        self.channel = channel
        self.proxy_obj = proxy
        self.stop_event = stop_event
        self.id = bot_id
        self.account = account
        self.audio_only = audio_only
        self.running = False
        
        # Streamlink конфигурация
        self.streamlink = Streamlink()
        self._configure_streamlink()
        
        # Состояние
        self.last_active = time.time()
        self.stream_fd = None
        self.aiohttp_session = None
        self.irc_reader = None
        self.irc_writer = None
        self.device_id = str(uuid.uuid4())

    def _configure_streamlink(self):
        """Настройка Streamlink с прокси и параметрами Twitch"""
        proxy_url = self._get_proxy_url()
        if proxy_url:
            self.streamlink.set_option("http-proxy", proxy_url)
        
        self.streamlink.set_option("twitch-disable-ads", True)
        self.streamlink.set_option("twitch-disable-hosting", True)
        
        if self.audio_only:
            self.streamlink.set_option("stream-segment-threads", 1)
            self.streamlink.set_option("hls-segment-ignore-names", ["*"])

    async def _get_stream(self):
        """Получает и возвращает новый поток (вызывается постоянно)"""
        try:
            streams = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.streamlink.streams(f"https://www.twitch.tv/{self.channel}")
            )
            
            if not streams:
                logger.warning(f"[BOT {self.id}] Нет доступных потоков")
                return None

            # Выбираем поток (аудио или минимальное качество)
            stream = (streams.get("audio_only") or 
                     streams.get("160p") or 
                     next(iter(streams.values())))
            
            return stream.open()
        except Exception as e:
            logger.error(f"[BOT {self.id}] Ошибка получения потока: {e}")
            return None

    async def start(self):
        self.running = True
        logger.info(f"[BOT {self.id}] Запуск (аудио: {self.audio_only})")

        # Инициализация сессии
        proxy_url = self._get_proxy_url()
        connector = ProxyConnector.from_url(proxy_url) if proxy_url else None
        self.aiohttp_session = aiohttp.ClientSession(
            connector=connector,
            headers={"Client-ID": TWITCH_CLIENT_ID}
        )

        while not self.stop_event.is_set():
            try:
                # 1. Постоянно получаем новый поток
                self.stream_fd = await self._get_stream()
                if not self.stream_fd:
                    await asyncio.sleep(5)
                    continue

                logger.info(f"[BOT {self.id}] Поток подключен")
                
                # 2. Запускаем IRC (если есть аккаунт)
                irc_task = None
                if self.account and hasattr(self.account, 'token'):
                    irc_task = asyncio.create_task(self._irc_loop())

                # 3. Основной цикл чтения потока
                while not self.stop_event.is_set():
                    try:
                        # Читаем данные (важно для поддержания соединения)
                        await asyncio.get_event_loop().run_in_executor(
                            None,
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
                    await asyncio.get_event_loop().run_in_executor(None, self.stream_fd.close)
                if irc_task:
                    irc_task.cancel()
                await asyncio.sleep(3)  # Пауза перед переподключением

        await self.stop()

    async def _irc_loop(self):
        """Подключение к IRC чату (упрощенная версия)"""
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
                await asyncio.get_event_loop().run_in_executor(None, self.stream_fd.close)
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
        """Проверяет, работает ли бот"""
        return not self.running or (time.time() - self.last_active > 60)

    def _get_proxy_url(self):
        """Генерирует URL прокси из объекта"""
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