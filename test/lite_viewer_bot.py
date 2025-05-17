import asyncio
import random
import time
from streamlink import Streamlink
import aiohttp
from aiohttp_socks import ProxyConnector
import uuid
import socket

from headers import Headers

TWITCH_CLIENT_ID = "kimne78kx3ncx6wki5h1ko"
PING_URL = "http://ping.twitch.tv/ping"
IRC_SERVER = "irc.chat.twitch.tv"
IRC_PORT = 6667


class LiteViewerBot:
    def __init__(self, channel_name, proxy, bot_id, irc_username, irc_token):
        self.channel = channel_name
        self.bot_id = bot_id
        self.session = Streamlink()
        self.proxy = proxy

        self.session.set_option("http-proxy", self.proxy)
        self.stream_fd = None

        self.device_id = str(uuid.uuid4())
        self.heartbeat_interval = 15
        self.aiohttp_session = None

        self.irc_username = irc_username
        self.irc_token = "oauth:" + irc_token
        self.irc_reader = None
        self.irc_writer = None

    async def start(self):
        print(f"[BOT-{self.bot_id}] Starting with proxy {self.proxy}")

        connector = ProxyConnector.from_url(self.proxy)
        headers = {
            "Client-ID": TWITCH_CLIENT_ID,
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
        }
        self.aiohttp_session = aiohttp.ClientSession(connector=connector, headers=headers)

        try:
            streams = self.session.streams(f"https://www.twitch.tv/{self.channel}")
            if not streams:
                print(f"[BOT-{self.bot_id}] No streams found for channel {self.channel}")
                return

            stream_quality = "160p"
            stream = streams.get(stream_quality) or next(iter(streams.values()))
            loop = asyncio.get_event_loop()
            # Открываем поток НЕ блокируя event loop
            self.stream_fd = await loop.run_in_executor(None, stream.open)
            print(f"[BOT-{self.bot_id}] Connected to stream {stream_quality}")

            await asyncio.gather(
                self.read_stream(),
                # self.heartbeat_loop()
            )

        except Exception as e:
            print(f"[BOT-{self.bot_id}] Fatal error: {e}")

        finally:
            if self.stream_fd:
                self.stream_fd.close()
            if self.aiohttp_session:
                await self.aiohttp_session.close()
            print(f"[BOT-{self.bot_id}] Closed")

    async def read_stream(self):
        loop = asyncio.get_event_loop()
        while True:
            try:
                data = await loop.run_in_executor(None, self.stream_fd.read, 1024)
                if not data:
                    print(f"[BOT-{self.bot_id}] Stream ended")
                    break
                print(f"[BOT-{self.bot_id}] Received chunk {len(data)} bytes")
                await asyncio.sleep(random.uniform(1.0, 3.0))
            except Exception as e:
                print(f"[BOT-{self.bot_id}] Read error: {e}")
                await asyncio.sleep(5)

    async def heartbeat_loop(self):
        while True:
            payload = {
                "device_id": self.device_id,
                "event": "playerHeartbeat",
                "player": "site",
                "timestamp": int(time.time() * 1000),
                "sequence_number": random.randint(100000, 999999),
            }
            try:
                async with self.aiohttp_session.post(PING_URL, json=payload, timeout=10) as resp:
                    print(f"[BOT-{self.bot_id}] Heartbeat status: {resp.status}")
            except ConnectionResetError:
                print(f"[BOT-{self.bot_id}] Heartbeat connection reset, retrying in 5s...")
                await asyncio.sleep(5)
                continue
            except Exception as e:
                print(f"[BOT-{self.bot_id}] Heartbeat error: {type(e).__name__} – {repr(e)}")

            await asyncio.sleep(self.heartbeat_interval)

    async def connect_to_irc(self):
        try:
            reader, writer = await asyncio.open_connection(IRC_SERVER, IRC_PORT)
            writer.write(f"PASS {self.irc_token}\r\n".encode())
            writer.write(f"NICK {self.irc_username}\r\n".encode())
            writer.write(f"JOIN #{self.channel}\r\n".encode())
            await writer.drain()
            print(f"[BOT-{self.bot_id}] IRC Connected as {self.irc_username}")
            self.irc_reader = reader
            self.irc_writer = writer
        except Exception as e:
            print(f"[BOT-{self.bot_id}] IRC connection error: {e}")

    async def irc_loop(self):
        try:
            while self.irc_reader:
                line = await self.irc_reader.readline()
                if not line:
                    break
                decoded = line.decode(errors="ignore").strip()
                print(f"[BOT-{self.bot_id}] IRC: {decoded}")

                # Ответ на PING от Twitch IRC
                if decoded.startswith("PING"):
                    pong_response = decoded.replace("PING", "PONG")
                    self.irc_writer.write(f"{pong_response}\r\n".encode())
                    await self.irc_writer.drain()

        except Exception as e:
            print(f"[BOT-{self.bot_id}] IRC loop error: {e}")
