import random
import asyncio
import traceback
from Logger.log import logger
from fake_useragent import UserAgent
import aiohttp
from aiohttp_socks import ProxyConnector
from aiohttp_socks import ProxyType
import m3u8

ua = UserAgent()

class TwitchBot:
    def __init__(self, streamlink_session, channel_name, proxy, stop_event, id, delay_range=(1, 5)):
        self.channel_url = "https://www.twitch.tv/" + channel_name
        self.proxy = proxy
        self.stop_event = stop_event
        self.delay_range = delay_range
        self.stream_session = streamlink_session
        self.running = False
        self.id = id
        self.last_active = asyncio.get_event_loop().time()
        self.restart_attempts = 0
        self.max_restarts = 5

    def configure_proxies(self):    
        if self.proxy.username and self.proxy.password:
            credentials = f"{self.proxy.username}:{self.proxy.password}@"
        else:
            credentials = ""

        if self.proxy.type in ["socks4", "socks5"]:
            return f"socks5://{credentials}{self.proxy.ip}:{self.proxy.port}"
        return f"http://{credentials}{self.proxy.ip}:{self.proxy.port}"

    async def get_url(self):
        url = ""
        try:
            streams = self.stream_session.streams(self.channel_url)
            try:
                url = streams['audio_only'].url
            except KeyError:
                url = streams['worst'].url
        except Exception as e:
            logger.error(f"Error getting stream URL: {e}")
        logger.debug(f"Stream URL: {url}")
        return url

    async def start(self):
        self.running = True
        proxy_url = self.configure_proxies()
        logger.info(f"Bot ID:[{self.id}] Connecting with proxy: {proxy_url}")
        try:

            connector = ProxyConnector(
                proxy_type=ProxyType.SOCKS5 if self.proxy.type.lower() == 'socks5' else ProxyType.SOCKS4,
                host=self.proxy.ip,
                port=self.proxy.port,
                username=self.proxy.username,
                password=self.proxy.password
            )
            headers = {
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "DNT": "1",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": ua.random,
                "Client-ID": "ewvlchtxgqq88ru9gmfp1gmyt6h2b93",
                "Referer": "https://www.google.com/"
            }

            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                self.session = session 
                stream_url = await self.get_simple_stream_url()  # Упрощённый метод получения URL
                if not stream_url:
                    logger.warning("Could not get stream URL")
                    return

                await self.watch_stream(stream_url)
        except Exception as e:
            logger.error(f"Bot ID:[{self.id}] Error starting bot: {e}")
            await asyncio.sleep(5)

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


    async def get_simple_stream_url(self):
        """Упрощённый метод получения URL стрима"""
        try:
            # Здесь можно использовать синхронный Streamlink в отдельном потоке
            streams = await asyncio.to_thread(self.stream_session.streams, self.channel_url)
            return streams.get('audio_only', streams.get('worst')).url
        except Exception as e:
            logger.error(f"Error getting stream URL: {e}")
            return None
    
    def is_inactive(self, threshold=120):
        """Если бот не был активен threshold секунд — считаем его мертвым"""
        now = asyncio.get_event_loop().time()
        return (now - self.last_active) > threshold

    def is_dead(self, threshold=120):
        return not self.running or self.is_inactive(threshold)

    async def stop(self):
        self.running = False
        logger.info("Bot stopped")
