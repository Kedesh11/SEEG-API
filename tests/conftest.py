from fastapi.testclient import TestClient
import pytest
import os


def _configure_env_for_local_db():
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:%20%20%20%20@SEEG:5432/recruteur")
    os.environ.setdefault("DATABASE_URL_SYNC", "postgresql://postgres:%20%20%20%20@SEEG:5432/recruteur")
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("DEBUG", "true")
    os.environ.setdefault("SECRET_KEY", "CHANGE_ME_IN_PROD_32CHARS_MINIMUM_1234567890")
    os.environ.setdefault("JWT_ISSUER", "seeg-api")
    os.environ.setdefault("JWT_AUDIENCE", "seeg-clients")


_configure_env_for_local_db()

from app.main import app  # noqa: E402  # import après config env


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def admin_credentials():
    return {"email": "sevankedesh11@gmail.com", "password": "Sevan@Seeg"}


@pytest.fixture(scope="session")
def get_bearer():
    def _make(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}
    return _make


@pytest.fixture(scope="session")
def admin_token(client, admin_credentials):
    client.post("/api/v1/auth/create-first-admin")
    r = client.post("/api/v1/auth/login", json=admin_credentials, headers={"content-type": "application/json"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def recruiter_credentials():
    return {"email": "recruteur@test.local", "password": "Recrut3ur#2025"}


@pytest.fixture(scope="session")
def recruiter_token(client, recruiter_credentials, admin_token, get_bearer):
    # créer recruteur si besoin
    client.post(
        "/api/v1/auth/create-user",
        json={
            "email": recruiter_credentials["email"],
            "password": recruiter_credentials["password"],
            "first_name": "Jean",
            "last_name": "Mavoungou",
            "role": "recruiter",
        },
        headers={**get_bearer(admin_token), "content-type": "application/json"},
    )
    r = client.post("/api/v1/auth/login", json=recruiter_credentials, headers={"content-type": "application/json"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def candidate_credentials():
    return {"email": "candidate@test.local", "password": "Password#2025"}


@pytest.fixture(scope="session")
def candidate_token(client, candidate_credentials):
    # signup si besoin
    client.post(
        "/api/v1/auth/signup",
        json={
            "email": candidate_credentials["email"],
            "password": candidate_credentials["password"],
            "first_name": "Ada",
            "last_name": "Lovelace",
            "matricule": 123456,
            "date_of_birth": "1990-01-01",
            "sexe": "F"
        },
        headers={"content-type": "application/json"},
    )
    r = client.post("/api/v1/auth/login", json=candidate_credentials, headers={"content-type": "application/json"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def seeded_ids(client, recruiter_token, candidate_token, get_bearer):
    # créer une offre si besoin et retourner ses IDs via endpoints
    r = client.post(
        "/api/v1/jobs",
        json={
            "title": "Ingénieur Systèmes",
            "description": "Gestion systèmes et réseaux",
            "status": "open"
        },
        headers={**get_bearer(recruiter_token), "content-type": "application/json"},
    )
    job_data = r.json() if r.status_code == 200 else {}
    job_id = job_data.get("id") or job_data.get("data", {}).get("id")
    return {"job_offer_id": job_id}


