from sqlalchemy.orm import joinedload
from sqlalchemy.future import select
from Models.account import Account
from datetime import datetime
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import func


class AccountRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_valid_accounts(self, count: int = 10) -> List[Account]:
        result = await self.db.execute(
            select(Account)
            .options(joinedload(Account.proxy))
            .filter(Account.isValid == True)
            .order_by(Account.lastChecked)
            .limit(count)
        )
        return result.scalars().all()

    async def get_random_valid_accounts(self, count: int = 10) -> List[Account]:
        result = await self.db.execute(
            select(Account)
            .options(joinedload(Account.proxy))
            .filter(Account.isValid == True, Account.proxy_id != None)
            .order_by(func.random())
            .limit(count)
        )
        return result.scalars().all()

    async def update_account(self, account: Account):
        account.lastChecked = datetime.utcnow()
        self.db.merge(account)
        await self.db.commit()
    
    async def get_all(self) -> List[Account]:
        result = await self.db.execute(
            select(Account)
        )
        return result.scalars().all()

    async def get_all_twitch(self) -> List[Account]:
        result = await self.db.execute(
            select(Account)
            .filter(func.lower(Account.platform) == 'twitch')
        )
        return result.scalars().all()
    
    async def get_all_youtube(self) -> List[Account]:
        result = await self.db.execute(
            select(Account)
            .filter(func.lower(Account.platform) == 'youtube')
        )
        return result.scalars().all()
    
    async def get_all_kick(self) -> List[Account]:
        result = await self.db.execute(
            select(Account)
            .filter(func.lower(Account.platform) == 'kick')
        )
        return result.scalars().all()

    async def add_account(self, account: Account):
        self.db.add(account)
        await self.db.commit()

    async def add_accounts(self, accounts: List[Account]):
        self.db.add_all(accounts)
        await self.db.commit()
