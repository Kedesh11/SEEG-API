"""
Configuration pour pytest avec base de données Azure
"""
import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.models.base import Base
from app.core.config.config import settings
import os


@pytest.fixture(scope="session")
def event_loop():
    """Créer un event loop pour toute la session de test."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_engine():
    """Créer un moteur de base de données Azure pour les tests."""
    # Utiliser la base de données Azure réelle
    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
    # Ne pas créer/supprimer les tables car elles existent déjà
    yield engine


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Créer une session de base de données Azure pour les tests."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="function")
async def async_db_engine():
    """Créer un moteur de base de données asynchrone Azure pour les tests."""
    # Utiliser la base de données Azure réelle
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def async_db_session(async_db_engine):
    """Créer une session de base de données asynchrone Azure pour les tests."""
    async with AsyncSession(async_db_engine) as session:
        yield session


@pytest.fixture
def sample_user_data():
    """Données d'utilisateur de test."""
    return {
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "role": "candidate",
        "phone": "+33123456789",
        "date_of_birth": "1990-01-01",
        "sexe": "M"
    }


@pytest.fixture
def sample_job_offer_data():
    """Données d'offre d'emploi de test."""
    return {
        "title": "Développeur Python Test",
        "description": "Développement d'applications Python - Test",
        "location": "Paris",
        "contract_type": "CDI",
        "department": "IT",
        "salary_min": 40000,
        "salary_max": 60000,
        "requirements": ["Python", "Django", "PostgreSQL"],
        "benefits": ["Mutuelle", "Tickets restaurant"],
        "responsibilities": ["Développement", "Tests", "Documentation"]
    }


@pytest.fixture
def sample_application_data():
    """Données de candidature de test."""
    return {
        "candidate_id": "candidate-id",
        "job_offer_id": "job-offer-id",
        "cover_letter": "Lettre de motivation - Test",
        "motivation": "Ma motivation - Test",
        "reference_contacts": "Contact 1, Contact 2",
        "availability_start": "2024-06-01T00:00:00Z"
    }


# Marqueurs pytest personnalisés
def pytest_configure(config):
    """Configuration des marqueurs pytest."""
    config.addinivalue_line("markers", "slow: marque les tests comme lents")
    config.addinivalue_line("markers", "integration: marque les tests d'intégration")
    config.addinivalue_line("markers", "unit: marque les tests unitaires")
    config.addinivalue_line("markers", "auth: marque les tests d'authentification")
    config.addinivalue_line("markers", "models: marque les tests de modèles")
    config.addinivalue_line("markers", "services: marque les tests de services")
    config.addinivalue_line("markers", "api: marque les tests d'API")
    config.addinivalue_line("markers", "utils: marque les tests d'utilitaires")
    config.addinivalue_line("markers", "azure: marque les tests avec base de données Azure")


def pytest_collection_modifyitems(config, items):
    """Modifie la collection des tests."""
    for item in items:
        # Ajouter des marqueurs automatiques basés sur le nom du fichier
        if "test_models" in item.nodeid:
            item.add_marker(pytest.mark.models)
        elif "test_services" in item.nodeid:
            item.add_marker(pytest.mark.services)
        elif "test_api" in item.nodeid:
            item.add_marker(pytest.mark.api)
        elif "test_utils" in item.nodeid:
            item.add_marker(pytest.mark.utils)
        elif "test_auth" in item.nodeid:
            item.add_marker(pytest.mark.auth)
        
        # Marquer tous les tests comme utilisant Azure
        item.add_marker(pytest.mark.azure)
