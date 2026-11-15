from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine( 
    settings.database_url,
    pool_size=20,
    max_overflow=10,
    pool_timeout=5,      # fail in 5s, not 30s
    pool_pre_ping=True,
    connect_args={"timeout": 3, "command_timeout": 5},
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_session():
    async with SessionLocal() as session:
        yield session