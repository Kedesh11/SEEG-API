import os
import pytest
from httpx import AsyncClient
from types import SimpleNamespace

from app.main import app
from app.core.dependencies import get_current_user
from app.services.email import EmailService

REAL_EMAIL = os.environ.get("TEST_REAL_EMAIL", "sevankedesh11@gmail.com")


@pytest.mark.anyio
async def test_send_real_email(monkeypatch, client: AsyncClient):
    # Override get_current_user pour bypasser l'auth
    fake_user = SimpleNamespace(id="00000000-0000-0000-0000-000000000001", email="tester@example.com", role="admin")
    app.dependency_overrides[get_current_user] = lambda: fake_user

    # Restaurer l'envoi réel (le conftest mocke send_email globalement)
    original_send_email = EmailService.send_email.__wrapped__ if hasattr(EmailService.send_email, "__wrapped__") else EmailService.send_email
    monkeypatch.setattr(EmailService, "send_email", original_send_email, raising=False)

    # Désactiver le logging DB pour éviter une dépendance base
    async def _no_log(self, **kwargs):
        return True
    if hasattr(EmailService, "_log_email"):
        monkeypatch.setattr(EmailService, "_log_email", _no_log, raising=False)

    payload = {
        "to": REAL_EMAIL,
        "subject": "[TEST] One HCM SEEG - Email de vérification",
        "body": "Ceci est un email de test envoyé par la suite de tests backend.",
        "html_body": "<p>Ceci est un <strong>email de test</strong> envoyé par la suite de tests backend.</p>"
    }

    resp = await client.post("/api/v1/emails/send", json=payload)

    # Nettoyage override
    app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("success") is True 