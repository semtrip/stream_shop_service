from sqlalchemy.orm import joinedload
from sqlalchemy.future import select
from sqlalchemy import func, asc
from datetime import datetime
from Models.proxy import Proxy
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession


class ProxyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> List[Proxy]:
        result = await self.db.execute(select(Proxy))
        return result.scalars().all()

    async def get_all_invalid(self) -> List[Proxy]:
        result = await self.db.execute(
            select(Proxy).where(
                Proxy.twitchValid == False,
                Proxy.youtubeValid == False,
                Proxy.kickValid == False
            )
        )
        return result.scalars().all()

    async def get_valid_proxies(self, platform: str) -> List[Proxy]:
        """
        Получение списка валидных прокси для указанной платформы
        
        :param platform: строка 'twitch', 'youtube' или 'kick'
        :return: Список валидных прокси
        """
        # Выбираем валидность в зависимости от переданной платформы
        if platform == 'twitch':
            validity_column = Proxy.twitchValid
        elif platform == 'youtube':
            validity_column = Proxy.youtubeValid
        elif platform == 'kick':
            validity_column = Proxy.kickValid
        else:
            raise ValueError(f"Неподдерживаемая платформа: {platform}")

        result = await self.db.execute(
            select(Proxy).filter(validity_column == True)
        )
        return result.scalars().all()

    async def get_by_id(self, id: int) -> Optional[Proxy]:
        result = await self.db.execute(
            select(Proxy).filter(Proxy.id == id)
        )
        return result.scalar_one_or_none()

    async def bulk_insert_proxies(self, proxies: List[Proxy]) -> int:
        self.db.add_all(proxies)
        await self.db.commit()
        return len(proxies)

    async def add_proxy(self, proxy: Proxy):
        proxy.twitchValid = False
        proxy.youtubeValid = False
        proxy.kickValid = False
        proxy.lastChecked = datetime.now()
        self.db.add(proxy)
        await self.db.commit()

    async def update_proxy(self, proxy: Proxy):
        existing = await self.get_by_id(proxy.id)
        if not existing:
            return
        existing.username = proxy.username
        existing.password = proxy.password
        existing.lastChecked = datetime.now()
        await self.db.commit()

    async def delete_proxy(self, id: int):
        proxy = await self.get_by_id(id)
        if proxy:
            await self.db.delete(proxy)
            await self.db.commit()

    async def get_count(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(Proxy))
        return result.scalar_one()

    async def get_free_proxy(self, platform: str) -> Optional[Proxy]:
        """
        Получение свободного прокси для указанной платформы
        
        :param platform: строка 'twitch', 'youtube' или 'kick'
        :return: Прокси или None
        """
        # Выбираем валидность в зависимости от переданной платформы
        if platform == 'twitch':
            validity_column = Proxy.twitchValid
        elif platform == 'youtube':
            validity_column = Proxy.youtubeValid
        elif platform == 'kick':
            validity_column = Proxy.kickValid
        else:
            raise ValueError(f"Неподдерживаемая платформа: {platform}")

        # Предполагаем, что у вас есть столбец activeAccountsCount
        result = await self.db.execute(
            select(Proxy)
            .filter(
                validity_column == True, 
                Proxy.activeAccountsCount < 3
            )
            .order_by(asc(Proxy.activeAccountsCount))
        )
        return result.scalar_one_or_none()
