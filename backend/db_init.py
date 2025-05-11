import asyncio
from db import engine, Base


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("База данных и таблицы успешно инициализированы.")
