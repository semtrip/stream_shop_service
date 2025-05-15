from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from Models.task import BotTask, TaskStatus
from typing import List, Optional
from datetime import datetime


class TaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> List[BotTask]:
        result = await self.db.execute(select(BotTask))
        return result.scalars().all()

    async def get_tasks_by_statuses(self, statuses: List[TaskStatus]) -> List[BotTask]:
        stmt = select(BotTask).where(BotTask.status.in_(statuses))
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_pending_tasks(self) -> List[BotTask]:
        result = await self.db.execute(
            select(BotTask).filter(BotTask.status == TaskStatus.Pending)
        )
        return result.scalars().all()

    async def get_running_tasks(self) -> List[BotTask]:
        result = await self.db.execute(
            select(BotTask).filter(BotTask.status == TaskStatus.Running)
        )
        return result.scalars().all()

    async def get_by_id(self, id: int) -> Optional[BotTask]:
        result = await self.db.execute(select(BotTask).filter(BotTask.id == id))
        return result.scalar_one_or_none()

    async def add_task(self, task: BotTask):
        if task is None:
            raise ValueError("Task cannot be None")
        task.errorMessage = ""
        self.db.add(task)
        await self.db.commit()

    async def update_task(self, task: BotTask):
        if task is None:
            raise ValueError("Task cannot be None")
        try:
            await self.db.merge(task)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            raise e
