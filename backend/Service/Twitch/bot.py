import random
from Logger.log import logger
from streamlink import Streamlink
from fake_useragent import UserAgent
import asyncio
import aiohttp
from aiohttp_socks import ProxyConnector
import traceback
import requests

ua = UserAgent()

class TwitchBot:
    def __init__(self, streamlink_session, chanel_name, proxy, stop_event, delay_range=(1, 5)):
        self.channel_url = "https://www.twitch.tv/" + chanel_name
        self.proxy = proxy
        self.stop_event = stop_event
        self.delay_range = delay_range
        self.stream_session = streamlink_session
        self.session: aiohttp.ClientSession = None
        self.running = False

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
        headers = {"User-Agent": ua.random}
        proxy_url = self.configure_proxies()
        logger.info(f"Connecting with proxy: {proxy_url}")

        # connector = ProxyConnector.from_url(proxy_url)
        # self.session = aiohttp.ClientSession(connector=connector, headers=headers)

        session = requests.Session() 
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        while not self.stop_event.is_set():
            try:
                url = await self.get_url()
                if url:
                    #async with self.session.head(url, timeout=10):
                    # def send_head():
                    #     return session.head(url, proxies=proxies, headers=headers, timeout=10)

                    # await asyncio.get_event_loop().run_in_executor(None, send_head)

                    with requests.Session() as s:
                        s.head(url, proxies=proxies, headers=headers, timeout=10)

                    logger.info(f"Bot connected: {url}")
            except Exception as e:
                logger.error(f"Bot error: {e}")
                logger.error(traceback.format_exc())

            await asyncio.sleep(random.randint(*self.delay_range))

        await self.stop()

    async def stop(self):
        if self.session:
            await self.session.close()
        self.running = False
        logger.info("Bot session closed")
