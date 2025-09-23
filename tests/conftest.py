import asyncio
import os
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.email import EmailService
from app.services.auth import AuthService
from app.services.job import JobOfferService


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("DEBUG", "false")


@pytest.fixture(autouse=True)
async def monkeypatch_services():
    async def _fake_send_email(self, to, subject, body, html_body=None, sender=None, cc=None, bcc=None, attachments=None):
        return True
    EmailService.send_email = _fake_send_email

    async def _fake_reset_request(self, email: str) -> bool:
        return True
    AuthService.reset_password_request = _fake_reset_request

    async def _fake_reset_confirm(self, token: str, new_password: str) -> bool:
        return True
    AuthService.reset_password_confirm = _fake_reset_confirm

    async def _fake_get_job_offers(self, skip: int = 0, limit: int = 100, recruiter_id=None, status=None):
        return []
    JobOfferService.get_job_offers = _fake_get_job_offers

    yield


@pytest.fixture()
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c 