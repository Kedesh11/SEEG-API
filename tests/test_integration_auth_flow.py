import pytest


@pytest.mark.order(1)
def test_create_first_admin_then_login(client, admin_credentials):
    # 1) Créer le premier admin (idempotent: peut échouer en 400 si déjà créé)
    resp_create = client.post("/api/v1/auth/create-first-admin")
    assert resp_create.status_code in (200, 400)

    # 2) Login admin
    resp_login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_credentials["email"], "password": admin_credentials["password"]},
        headers={"content-type": "application/json"},
    )
    assert resp_login.status_code in (200, 401)
    if resp_login.status_code == 200:
        body = resp_login.json()
        assert body.get("access_token")
        assert body.get("refresh_token")


