"""
Configuration de la base de données
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

# Moteur synchrone
engine = create_engine(
    settings.DATABASE_URL_SYNC,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.DEBUG
)

# Moteur asynchrone
async_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.DEBUG
)

# Session factory synchrone
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Session factory asynchrone
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

def get_db() -> Session:
    """Dependency pour obtenir une session de base de données synchrone"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db() -> AsyncSession:
    """Dependency pour obtenir une session de base de données asynchrone"""
    async with AsyncSessionLocal() as session:
        yield session

async def get_async_session() -> AsyncSession:
    """Générateur pour obtenir une session asynchrone"""
    async with AsyncSessionLocal() as session:
        yield session
