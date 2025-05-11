from sqlalchemy import Column, Integer, String, Enum, DateTime, Time
from sqlalchemy.orm import relationship
from db import Base
from datetime import datetime
from enum import Enum as PyEnum

# Перечисление для статусов задачи
class TaskStatus(PyEnum):
    Pending = "pending"
    Running = "running"
    Completed = "completed"
    Paused = "paused"
    Cancelled = "cancelled"
    Error = "error"

class BotTask(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.Pending)
    url = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    activity = Column(String, nullable=False)
    countBot = Column(Integer, nullable=False)
    activeBot = Column(Integer, nullable=False, default=0)
    authBot = Column(Integer, nullable=False)
    errors = Column(String, nullable=True)
    time = Column(Time, nullable=False)  # Time in hours
    rampUpTime = Column(Time, nullable=False)  # Time in minutes
    completedTime = Column(DateTime, nullable=True)
    elapsedTime = Column(Time, nullable=True)  # Remaining time in minutes
    lastUpdated = Column(DateTime, default=datetime.utcnow)

