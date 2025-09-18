"""
Configuration des tests pour One HCM SEEG
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.database import get_async_db
from app.models.base import Base

# Configuration de la base de données de test
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(scope="session")
def event_loop():
    """Créer un event loop pour les tests asyncio"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def setup_database():
    """Créer les tables de test"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(setup_database):
    """Créer une session de base de données pour les tests"""
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
def client():
    """Créer un client de test FastAPI"""
    return TestClient(app)

@pytest.fixture
def override_get_db(db_session):
    """Override de la dépendance de base de données"""
    async def _override_get_db():
        yield db_session
    app.dependency_overrides[get_async_db] = _override_get_db
    yield
    app.dependency_overrides.clear()
