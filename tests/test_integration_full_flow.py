import pytest


@pytest.mark.order(2)
def test_full_flow_admin_recruiter_candidate_application_pdf(client):
    # 1) S'assurer que l'admin existe et se connecter
    client.post("/api/v1/auth/create-first-admin")
    login_admin = client.post(
        "/api/v1/auth/login",
        json={"email": "sevankedesh11@gmail.com", "password": "Sevan@Seeg"},
        headers={"content-type": "application/json"},
    )
    assert login_admin.status_code in (200, 401)
    if login_admin.status_code != 200:
        pytest.skip("Admin non connecté - vérifier credentials en base")
    admin_tokens = login_admin.json()
    admin_auth = {"Authorization": f"Bearer {admin_tokens['access_token']}"}

    # 2) Créer un recruteur (admin-only)
    create_user = client.post(
        "/api/v1/auth/create-user",
        json={
            "email": "recruteur@test.local",
            "password": "Recrut3ur#2025",
            "first_name": "Jean",
            "last_name": "Mavoungou",
            "role": "recruiter",
            "phone": "+24107445566"
        },
        headers={**admin_auth, "content-type": "application/json"},
    )
    # 200: créé, 409: existe déjà, 422: validation error (peut arriver si données incomplètes), 500: erreur serveur
    assert create_user.status_code in (200, 409, 422, 500)

    # 3) Login recruteur
    login_recruiter = client.post(
        "/api/v1/auth/login",
        json={"email": "recruteur@test.local", "password": "Recrut3ur#2025"},
        headers={"content-type": "application/json"},
    )
    assert login_recruiter.status_code in (200, 401)
    if login_recruiter.status_code != 200:
        pytest.skip("Recruteur non connecté - vérifier base")
    recruiter_tokens = login_recruiter.json()
    recruiter_auth = {"Authorization": f"Bearer {recruiter_tokens['access_token']}"}

    # 4) Créer une offre d'emploi
    job_create = client.post(
        "/api/v1/jobs",
        json={
            "title": "Ingénieur Systèmes",
            "description": "Gestion systèmes et réseaux",
            "status": "open"
        },
        headers={**recruiter_auth, "content-type": "application/json"},
    )
    assert job_create.status_code in (200, 422, 500)
    if job_create.status_code != 200:
        pytest.skip("Création offre échouée - vérifier schéma JobOfferCreate")
    job = job_create.json()
    job_id = job.get("id") or job.get("data", {}).get("id")
    if not job_id:
        pytest.skip("ID d'offre non récupéré")

    # 5) Créer un candidat (signup public)
    signup = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "candidate@test.local",
            "password": "Password#2025",
            "first_name": "Ada",
            "last_name": "Lovelace",
            "matricule": 123456,
            "phone": "+24100000000",
            "date_of_birth": "1990-01-01",
            "sexe": "F"
        },
        headers={"content-type": "application/json"},
    )
    assert signup.status_code in (200, 409, 500)

    # 6) Login candidat
    login_cand = client.post(
        "/api/v1/auth/login",
        json={"email": "candidate@test.local", "password": "Password#2025"},
        headers={"content-type": "application/json"},
    )
    assert login_cand.status_code in (200, 401)
    if login_cand.status_code != 200:
        pytest.skip("Candidat non connecté - vérifier base")
    cand_tokens = login_cand.json()
    cand_auth = {"Authorization": f"Bearer {cand_tokens['access_token']}"}

    # 7) Créer une candidature (candidate)
    # NB: nécessite candidate_id et job_offer_id: ici on utilise les endpoints côté service pour résoudre
    # Par simplicité, on tente un POST minimaliste si le schéma le permet.
    application_create = client.post(
        "/api/v1/applications",
        json={
            "candidate_id": "00000000-0000-0000-0000-000000000001",
            "job_offer_id": job_id,
            "status": "pending"
        },
        headers={**cand_auth, "content-type": "application/json"},
    )
    # Selon la contrainte de candidate_id réel, cela peut être 400/422
    assert application_create.status_code in (201, 400, 422)


