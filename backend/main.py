import asyncio
from db import AsyncSessionLocal, engine
from Ui.ui import MenuUI
from db_init import init_db
from Ui.commands import Commands

async def main():
    await init_db()
    try:
        async with AsyncSessionLocal() as db:
            menu_ui = MenuUI()
            commands_ui = await Commands(db, menu_ui).initialize()
            
            await commands_ui.showMenu()
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())