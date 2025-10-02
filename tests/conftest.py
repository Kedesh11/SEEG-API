import asyncio
import os
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace
from uuid import uuid4

from app.main import app
from app.services.email import EmailService
from app.services.auth import AuthService
from app.services.job import JobOfferService
from app.services.application import ApplicationService
from app.core.dependencies import get_async_db_session


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("DEBUG", "false")
    # Désactiver Application Insights pendant les tests
    os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"] = ""


# Mock de session BD
@pytest.fixture
async def mock_db_session():
    """Mock de la session de base de données"""
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.scalar = AsyncMock()
    mock_session.scalars = AsyncMock()
    return mock_session


@pytest.fixture(autouse=True)
async def monkeypatch_services():
    """Mock de tous les services pour les tests"""
    
    # ===== EMAIL SERVICE =====
    async def _fake_send_email(self, to, subject, body, html_body=None, sender=None, cc=None, bcc=None, attachments=None):
        return True
    EmailService.send_email = _fake_send_email

    # ===== AUTH SERVICE =====
    async def _fake_reset_request(self, email: str) -> bool:
        return True
    AuthService.reset_password_request = _fake_reset_request

    async def _fake_reset_confirm(self, token: str, new_password: str) -> bool:
        return True
    AuthService.reset_password_confirm = _fake_reset_confirm
    
    async def _fake_authenticate(self, email: str, password: str):
        """Mock d'authentification qui retourne un faux utilisateur"""
        if email.startswith("test") and password == "test123":
            return SimpleNamespace(
                id=str(uuid4()),
                email=email,
                role="candidate",
                first_name="Test",
                last_name="User",
                is_active=True
            )
        return None
    AuthService.authenticate_user = _fake_authenticate

    # ===== JOB OFFER SERVICE =====
    async def _fake_get_job_offers(self, skip: int = 0, limit: int = 100, recruiter_id=None, status=None):
        return []
    JobOfferService.get_job_offers = _fake_get_job_offers

    # ===== APPLICATION SERVICE =====
    async def _fake_get_application(self, application_id: str):
        """Mock pour récupérer une candidature"""
        return SimpleNamespace(
            id=application_id,
            candidate_id=str(uuid4()),
            job_offer_id=str(uuid4()),
            status="pending",
            cover_letter="Test cover letter"
        )
    ApplicationService.get_application = _fake_get_application
    
    async def _fake_create_document(self, document_data):
        """Mock pour créer un document"""
        return SimpleNamespace(
            id=str(uuid4()),
            application_id=document_data.application_id,
            document_type=document_data.document_type,
            file_name=document_data.file_name,
            file_size=document_data.file_size,
            file_type=document_data.file_type,
            created_at="2025-10-02T12:00:00Z"
        )
    ApplicationService.create_document = _fake_create_document

    yield


@pytest.fixture(autouse=True)
async def mock_db_dependency():
    """Mock de la dépendance get_async_db_session"""
    async def _fake_db_session():
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.refresh = AsyncMock()
        yield mock_session
    
    app.dependency_overrides[get_async_db_session] = _fake_db_session
    yield
    app.dependency_overrides.pop(get_async_db_session, None)


@pytest.fixture()
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c 