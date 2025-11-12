from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker 
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator 
import os 
from dotenv import load_dotenv 

try: 
    from models import Base, Task 
except ImportError: 
    class Base(DeclarativeBase): 
        pass 

load_dotenv() 
 
DATABASE_URL = os.getenv("DATABASE_URL") 
 
# Создаем engine с отключенным кэшем prepared statements
engine = create_async_engine( 
    DATABASE_URL, 
    connect_args={
        "statement_cache_size": 0,  # Отключаем кэш prepared statements
        "prepared_statement_name_func": lambda: "",  # Отключаем именованные prepared statements
    }
) 

AsyncSessionLocal = async_sessionmaker( 
    bind=engine, 
    autoflush=False, 
    expire_on_commit=False,
    class_=AsyncSession
) 
 
async def init_db(): 
    try:
        async with engine.begin() as conn: 
            await conn.run_sync(Base.metadata.create_all) 
        print("База данных инициализирована!")
    except Exception as e:
        print(f"Ошибка при инициализации базы данных: {e}")
        raise
 
async def drop_db(): 
    async with engine.begin() as conn: 
        await conn.run_sync(Base.metadata.drop_all) 
    print("Все таблицы удалены!") 
 
async def get_async_session() -> AsyncGenerator[AsyncSession, None]: 
    async with AsyncSessionLocal() as session: 
        try:
            yield session
        finally:
            await session.close()

