"""
Configuration des tests pytest.
Respecte les principes de test-driven development.
"""

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import get_async_db
from app.models.base import Base
from app.core.config import settings


# Configuration de la base de données de test
TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db"

# Moteur de test
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10,
)

# Session de test
TestSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Créer un event loop pour toute la session de test."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Créer une session de base de données pour chaque test."""
    # Créer les tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Créer une session
    async with TestSessionLocal() as session:
        yield session
    
    # Nettoyer après le test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    """Créer un client HTTP pour les tests."""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_async_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """Données de test pour un utilisateur."""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User",
        "phone": "+241123456789",
        "role": "candidat"
    }


@pytest.fixture
def test_job_data():
    """Données de test pour une offre d'emploi."""
    return {
        "title": "Développeur Full Stack",
        "description": "Développement d'applications web modernes",
        "location": "Libreville, Gabon",
        "contract_type": "CDI",
        "department": "Informatique",
        "salary_min": 500000,
        "salary_max": 800000,
        "requirements": ["Python", "React", "PostgreSQL"],
        "responsibilities": ["Développement", "Maintenance", "Tests"],
        "benefits": ["Assurance santé", "Formation", "Télétravail"]
    }


@pytest.fixture
def test_application_data():
    """Données de test pour une candidature."""
    return {
        "cover_letter": "Lettre de motivation de test",
        "motivation": "Motivation pour le poste",
        "availability_start": "2024-01-01",
        "reference_contacts": "Contact de référence",
        "mtp_metier_q1": "Réponse question métier 1",
        "mtp_metier_q2": "Réponse question métier 2",
        "mtp_metier_q3": "Réponse question métier 3",
        "mtp_talent_q1": "Réponse question talent 1",
        "mtp_talent_q2": "Réponse question talent 2",
        "mtp_talent_q3": "Réponse question talent 3",
        "mtp_paradigme_q1": "Réponse question paradigme 1",
        "mtp_paradigme_q2": "Réponse question paradigme 2",
        "mtp_paradigme_q3": "Réponse question paradigme 3"
    }


@pytest.fixture
def auth_headers():
    """Headers d'authentification pour les tests."""
    return {
        "Authorization": "Bearer test_token"
    }


class TestDataFactory:
    """Factory pour créer des données de test."""
    
    @staticmethod
    def create_user_data(**kwargs):
        """Créer des données d'utilisateur de test."""
        default_data = {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "first_name": "Test",
            "last_name": "User",
            "phone": "+241123456789",
            "role": "candidat"
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def create_job_data(**kwargs):
        """Créer des données d'offre d'emploi de test."""
        default_data = {
            "title": "Test Job",
            "description": "Test Description",
            "location": "Test Location",
            "contract_type": "CDI",
            "department": "Test Department"
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def create_application_data(**kwargs):
        """Créer des données de candidature de test."""
        default_data = {
            "cover_letter": "Test cover letter",
            "motivation": "Test motivation"
        }
        default_data.update(kwargs)
        return default_data


@pytest.fixture
def factory():
    """Factory pour créer des données de test."""
    return TestDataFactory
