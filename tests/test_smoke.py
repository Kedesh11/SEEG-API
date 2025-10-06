from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_ok():
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body.get("message")
    assert body.get("version")


def test_protected_users_me_unauthorized():
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_auth_login_invalid_payload():
    # Envoi d'un JSON vide/invalides pour forcer une 422
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "", "password": ""},
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422


