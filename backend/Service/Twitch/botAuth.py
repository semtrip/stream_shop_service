import random
import asyncio
from Logger.log import logger
from fake_useragent import UserAgent
import aiohttp
from aiohttp_socks import ProxyConnector, ProxyType
import m3u8
from Models.account import Account

ua = UserAgent()

class TwitchBotAuth:
    def __init__(self, streamlink_session, channel_name, proxy, account: Account, stop_event, id, delay_range=(1, 5)):
        self.channel_url = "https://www.twitch.tv/" + channel_name
        self.channel_name = channel_name
        self.proxy = proxy
        self.stop_event = stop_event
        self.delay_range = delay_range
        self.stream_session = streamlink_session
        self.running = False
        self.id = id
        self.last_active = asyncio.get_event_loop().time()
        self.restart_attempts = 0
        self.max_restarts = 5

        self.username = account.user
        self.oauth_token = account.token
        self.use_auth = bool(account.user and account.token)

        self.irc_host = "irc.chat.twitch.tv"
        self.irc_port = 6667  # Можно 6697 для SSL, но тогда надо менять asyncio.open_connection
        self.reader = None
        self.writer = None
        self.session = None
        self.connector = None

    def configure_proxies(self):
        if self.proxy.username and self.proxy.password:
            credentials = f"{self.proxy.username}:{self.proxy.password}@"
        else:
            credentials = ""

        if self.proxy.type.lower() in ["socks4", "socks5"]:
            # Используем ProxyConnector для aiohttp
            return f"socks5://{credentials}{self.proxy.ip}:{self.proxy.port}"
        return f"http://{credentials}{self.proxy.ip}:{self.proxy.port}"

    async def start(self):
        self.running = True
        proxy_url = self.configure_proxies()
        logger.info(f"Bot ID:[{self.id}] Connecting with proxy: {proxy_url}")

        try:
            # Настраиваем прокси-коннектор только для aiohttp (просмотр потока)
            if self.proxy and self.proxy.type.lower() in ["socks4", "socks5"]:
                self.connector = ProxyConnector(
                    proxy_type=ProxyType.SOCKS5 if self.proxy.type.lower() == 'socks5' else ProxyType.SOCKS4,
                    host=self.proxy.ip,
                    port=self.proxy.port,
                    username=self.proxy.username,
                    password=self.proxy.password,
                    rdns=True
                )
            else:
                self.connector = None

            headers = {
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "DNT": "1",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": ua.random,
                "Client-ID": "ewvlchtxgqq88ru9gmfp1gmyt6h2b93",
                "Referer": "https://www.google.com/"
            }

            self.session = aiohttp.ClientSession(connector=self.connector, headers=headers)

            while not self.stop_event.is_set() and self.running:
                try:
                    stream_url = await self.get_simple_stream_url()
                    if not stream_url:
                        logger.warning(f"Bot ID:[{self.id}] Could not get stream URL, retrying...")
                        await asyncio.sleep(5)
                        continue

                    watch_task = asyncio.create_task(self.watch_stream(stream_url))
                    chat_task = asyncio.create_task(self.connect_chat())

                    done, pending = await asyncio.wait(
                        {watch_task, chat_task},
                        return_when=asyncio.FIRST_COMPLETED,
                        timeout=300
                    )

                    for task in pending:
                        task.cancel()
                        try:
                            await task
                        except (asyncio.CancelledError, Exception) as e:
                            logger.debug(f"Bot ID:[{self.id}] Task cancellation error: {e}")

                    if not self.stop_event.is_set():
                        logger.info(f"Bot ID:[{self.id}] One of tasks completed, restarting...")
                        await asyncio.sleep(5)

                except Exception as e:
                    logger.error(f"Bot ID:[{self.id}] Main loop error: {e}")
                    await asyncio.sleep(10)

        except Exception as e:
            logger.error(f"Bot ID:[{self.id}] Fatal error in start: {e}")
            self.running = False
        finally:
            await self.stop()
            

    async def watch_stream(self, stream_url):
        logger.info(f"Bot ID:[{self.id}] Watching stream...")
        retry_count = 0
        max_retries = 3

        try:
            while not self.stop_event.is_set() and self.running and retry_count < max_retries:
                try:
                    async with self.session.get(stream_url) as resp:
                        if resp.status != 200:
                            logger.warning(f"Bot ID:[{self.id}] Bad status: {resp.status}")
                            retry_count += 1
                            await asyncio.sleep(5)
                            continue

                        playlist = await resp.text()
                        m3u8_obj = m3u8.loads(playlist)
                        segment_urls = [seg.uri for seg in m3u8_obj.segments]

                        if not segment_urls:
                            logger.warning(f"Bot ID:[{self.id}] No segments found.")
                            retry_count += 1
                            await asyncio.sleep(5)
                            continue

                        retry_count = 0

                        for segment in segment_urls:
                            if self.stop_event.is_set() or not self.running:
                                return
                            try:
                                full_segment_url = segment if segment.startswith("http") else \
                                    stream_url.rsplit("/", 1)[0] + "/" + segment

                                async with self.session.get(full_segment_url) as seg_resp:
                                    if seg_resp.status == 200:
                                        self.last_active = asyncio.get_event_loop().time()
                                    else:
                                        logger.warning(f"Bot ID:[{self.id}] Bad segment status: {seg_resp.status}")
                            except Exception as e:
                                logger.error(f"Bot ID:[{self.id}] Error downloading segment: {e}")

                            await asyncio.sleep(random.uniform(*self.delay_range))

                except Exception as e:
                    logger.error(f"Bot ID:[{self.id}] Watch loop error: {e}")
                    retry_count += 1
                    await asyncio.sleep(5 * retry_count)

        except Exception as e:
            logger.error(f"Bot ID:[{self.id}] Fatal stream error: {e}")
        finally:
            self.running = False

    async def connect_chat(self):
        nick = self.username if self.use_auth else f"justinfan{random.randint(10000, 99999)}"
        logger.info(f"Bot ID:[{self.id}] Connecting to chat as {nick}")

        retry_count = 0
        max_retries = 5

        while not self.stop_event.is_set() and self.running and retry_count < max_retries:
            try:
                self.reader, self.writer = await asyncio.open_connection(
                    self.irc_host,
                    self.irc_port,
                    ssl=False  # Для SSL надо использовать 6697 и ssl=True
                )

                if self.use_auth:
                    self.writer.write(f"PASS oauth:{self.oauth_token}\r\n".encode())
                    self.writer.write(f"NICK {nick}\r\n".encode())
                else:
                    self.writer.write(f"PASS oauth:fake\r\n".encode())
                    self.writer.write(f"NICK {nick}\r\n".encode())

                self.writer.write(f"JOIN #{self.channel_name}\r\n".encode())
                await self.writer.drain()

                # Запускаем задачу пинга, чтобы держать соединение живым
                ping_task = asyncio.create_task(self.ping_loop())

                while not self.stop_event.is_set() and self.running:
                    try:
                        line = await asyncio.wait_for(self.reader.readline(), timeout=120)
                        if not line:
                            raise ConnectionResetError("Connection closed by server")

                        decoded = line.decode(errors='ignore').strip()
                        logger.debug(f"ChatBot ID:[{self.id}] <- {decoded}")

                        if decoded.startswith("PING"):
                            self.writer.write("PONG :tmi.twitch.tv\r\n".encode())
                            await self.writer.drain()

                    except asyncio.TimeoutError:
                        logger.debug(f"ChatBot ID:[{self.id}] No data received, sending PING")
                        self.writer.write("PING :tmi.twitch.tv\r\n".encode())
                        await self.writer.drain()
                    except Exception as e:
                        logger.error(f"ChatBot ID:[{self.id}] Chat error: {e}")
                        break

                ping_task.cancel()
                try:
                    await ping_task
                except asyncio.CancelledError:
                    pass

            except Exception as e:
                logger.error(f"ChatBot ID:[{self.id}] Connection error: {e}")
                retry_count += 1
                await asyncio.sleep(min(5 * retry_count, 60))  # Ограничиваем паузу до 60 секунд

            finally:
                if self.writer:
                    try:
                        self.writer.close()
                        await self.writer.wait_closed()
                    except Exception:
                        pass
                self.reader = None
                self.writer = None
                self.running = False

    async def ping_loop(self):
        """Keep connection alive with periodic PINGs"""
        while not self.stop_event.is_set() and self.running:
            try:
                if self.writer and not self.writer.is_closing():
                    self.writer.write("PING :tmi.twitch.tv\r\n".encode())
                    await self.writer.drain()
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"ChatBot ID:[{self.id}] Ping loop error: {e}")
                break

                

    async def get_simple_stream_url(self):
        """Get stream URL using streamlink (sync wrapped в async)"""
        try:
            streams = await asyncio.to_thread(self.stream_session.streams, self.channel_url)
            # берем наименее качественный поток, чтобы нагрузка была минимальна
            url = streams.get('audio_only', streams.get('worst'))
            if url:
                return url.url
            return None
        except Exception as e:
            logger.error(f"Bot ID:[{self.id}] Error getting stream URL: {e}")
            return None

    def is_inactive(self, threshold=120):
        """Если бот не был активен threshold секунд — считаем его мертвым"""
        now = asyncio.get_event_loop().time()
        return (now - self.last_active) > threshold

    def is_dead(self, threshold=120):
        return not self.running or self.is_inactive(threshold)

    async def stop(self):
        if not self.running:
            return
        self.running = False
        logger.info(f"Bot ID:[{self.id}] Stopping bot...")
        if self.session:
            await self.session.close()
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
        self.reader = None
        self.writer = None
