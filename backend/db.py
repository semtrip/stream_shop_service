from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Строка подключения к базе данных
DATABASE_URL = "postgresql+asyncpg://postgres:root@localhost:5432/service"

# Создаем асинхронный движок для SQLAlchemy
engine = create_async_engine(DATABASE_URL, echo=False, future=True)

# Создаем базовый класс для моделей
Base = declarative_base()

# Создаем асинхронную сессию
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Функция для получения сессии
def get_db():
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        db.close()