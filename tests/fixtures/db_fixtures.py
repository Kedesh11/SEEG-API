"""
Fixtures pour la base de données
Gestion des sessions de test et données de base
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Crée un event loop pour toute la session de tests"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session():
    """
    Crée une session de base de données pour chaque test
    Rollback automatique à la fin pour isolation des tests
    """
    # Créer un engine de test
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )
    
    # Créer une session factory
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        async with session.begin():
            yield session
            # Rollback automatique à la fin
            await session.rollback()
    
    await engine.dispose()

