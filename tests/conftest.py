"""
Configuration pytest centralisée
Importe toutes les fixtures réutilisables

Architecture:
- Fixtures organisées par domaine (auth, app, db, http)
- Scope approprié pour chaque fixture
- Isolation des tests garantie
"""
import pytest
import sys
from pathlib import Path

# Ajouter le projet au PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import des fixtures par domaine
from tests.fixtures.auth_fixtures import (
    valid_signup_externe,
    valid_signup_interne_with_seeg_email,
    valid_signup_interne_no_seeg_email,
    invalid_signup_weak_password,
    invalid_signup_missing_matricule
)

from tests.fixtures.application_fixtures import (
    test_pdf_base64,
    valid_application_data_with_documents,
    invalid_application_missing_documents,
    invalid_application_missing_one_document,
    valid_application_with_extra_documents
)

from tests.fixtures.db_fixtures import (
    event_loop,
    db_session
)

from tests.fixtures.http_fixtures import (
    api_base_url,
    http_client,
    authenticated_client_factory
)


# Configuration pytest
def pytest_configure(config):
    """Configuration globale pytest"""
    config.addinivalue_line("markers", "asyncio: mark test as async")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "slow: mark test as slow")


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup initial pour tous les tests"""
    import os
    # Forcer l'environnement de test
    os.environ['ENVIRONMENT'] = 'testing'
    os.environ['TEST_ENV'] = os.getenv('TEST_ENV', 'local')
    
    yield
    
    # Cleanup si nécessaire


# Ré-export de toutes les fixtures pour qu'elles soient disponibles
__all__ = [
    # Auth
    'valid_signup_externe',
    'valid_signup_interne_with_seeg_email',
    'valid_signup_interne_no_seeg_email',
    'invalid_signup_weak_password',
    'invalid_signup_missing_matricule',
    
    # Applications
    'test_pdf_base64',
    'valid_application_data_with_documents',
    'invalid_application_missing_documents',
    'invalid_application_missing_one_document',
    'valid_application_with_extra_documents',
    
    # Database
    'event_loop',
    'db_session',
    
    # HTTP
    'api_base_url',
    'http_client',
    'authenticated_client_factory',
]
