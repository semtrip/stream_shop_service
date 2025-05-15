import asyncio
from db import AsyncSessionLocal, engine
from sqlalchemy.ext.asyncio import AsyncSession
from db_init import init_db
from Ui.commands import Commands
from Managers.task_manager import TaskManager
from Managers.proxy_manager import ProxyManager
from Managers.account_manager import AccountManager

async def main():
    await init_db()
    try:
        async with AsyncSessionLocal() as db:
            await initialization(db)
            commands_ui = await Commands.create(db)
            
            await commands_ui.showMenu()
    finally:
        await engine.dispose()


async def initialization(db: AsyncSession):
    await TaskManager.get_instance(db)
    await ProxyManager.get_instance(db)
    await AccountManager.get_instance(db)
    
if __name__ == "__main__":
    asyncio.run(main())