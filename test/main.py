import asyncio
from lite_viewer_bot2 import LiteViewerBot

CHANNEL = "semtrip"  # Заменить на нужный канал
PROXY_FILE = "proxies.txt"
ACCOUNTS_FILE = "accounts.txt"
TOTAL_BOTS = 500
BATCH_SIZE = 5
DELAY_BETWEEN_BATCHES = 1  # секунды

async def main():
    with open(PROXY_FILE, "r") as f:
        proxies = [line.strip() for line in f if line.strip()]
    
    with open(ACCOUNTS_FILE) as f:
        accounts = [l.strip().split() for l in f if l.strip()]

    limit = int(min(TOTAL_BOTS * 1.2, len(proxies), len(accounts)))
    tasks = []

    for offset in range(0, limit, BATCH_SIZE):
        batch = [
            LiteViewerBot(CHANNEL, proxies[i], i + 1, accounts[i][0], accounts[i][1]).start()
            for i in range(offset, min(offset + BATCH_SIZE, limit))
        ]
        # Запускаем батч параллельно
        tasks.extend([asyncio.create_task(bot) for bot in batch])

        # Ждем секунду перед запуском следующего батча
        await asyncio.sleep(DELAY_BETWEEN_BATCHES)

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
