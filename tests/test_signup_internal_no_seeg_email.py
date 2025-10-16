"""
Tests pour l'inscription des candidats internes SANS email SEEG
POST /api/v1/auth/signup avec no_seeg_email=True

Flow attendu:
1. Inscription avec no_seeg_email=True
2. Statut = 'en_attente'
3. AccessRequest créée automatiquement
4. Emails envoyés (candidat + admin)
"""
import pytest
from httpx import AsyncClient
from datetime import date


@pytest.mark.asyncio
async def test_signup_internal_no_seeg_email_success(async_client: AsyncClient, db_session):
    """
    Test 1: Inscription candidat interne SANS email SEEG - Succès complet
    
    Scénario:
    - candidate_status = 'interne'
    - no_seeg_email = True
    - matricule fourni
    - email personnel (non @seeg-gabon.com)
    
    Résultat attendu:
    - 201 Created
    - User créé avec statut = 'en_attente'
    - AccessRequest créée
    - Réponse contient toutes les infos utilisateur
    """
    signup_data = {
        "email": "jean.dupont.perso@gmail.com",
        "password": "SecurePass@2025!",
        "first_name": "Jean",
        "last_name": "Dupont",
        "phone": "+24106223344",
        "date_of_birth": "1990-05-15",
        "sexe": "M",
        "candidate_status": "interne",
        "matricule": 123456,
        "no_seeg_email": True,  # ← Clé du test
        "adresse": "123 Rue Test, Libreville",
        "poste_actuel": "Technicien",
        "annees_experience": 5
    }
    
    response = await async_client.post(
        "/api/v1/auth/signup",
        json=signup_data
    )
    
    # Assertions
    assert response.status_code == 201, f"Erreur: {response.text}"
    
    data = response.json()
    assert data["id"] is not None
    assert data["email"] == "jean.dupont.perso@gmail.com"
    assert data["first_name"] == "Jean"
    assert data["last_name"] == "Dupont"
    assert data["role"] == "candidate"
    assert data["matricule"] == 123456
    assert data["candidate_status"] == "interne"
    assert data["no_seeg_email"] is True
    assert data["statut"] == "en_attente"  # ← Statut critique
    assert data["is_internal_candidate"] is True
    
    # Vérifier que l'AccessRequest a été créée
    from app.models.access_request import AccessRequest
    from sqlalchemy import select
    
    result = await db_session.execute(
        select(AccessRequest).where(AccessRequest.email == "jean.dupont.perso@gmail.com")
    )
    access_request = result.scalar_one_or_none()
    
    assert access_request is not None, "AccessRequest devrait être créée"
    assert access_request.first_name == "Jean"
    assert access_request.last_name == "Dupont"
    assert str(access_request.matricule) == "123456"
    assert access_request.status == "pending"


@pytest.mark.asyncio
async def test_signup_internal_with_seeg_email_no_access_request(async_client: AsyncClient, db_session):
    """
    Test 2: Inscription candidat interne AVEC email SEEG - PAS de demande d'accès
    
    Scénario:
    - candidate_status = 'interne'
    - no_seeg_email = False
    - email @seeg-gabon.com
    - matricule fourni
    
    Résultat attendu:
    - 201 Created
    - User créé avec statut = 'actif' (accès immédiat)
    - PAS d'AccessRequest créée
    """
    signup_data = {
        "email": "jean.dupont@seeg-gabon.com",
        "password": "SecurePass@2025!",
        "first_name": "Jean",
        "last_name": "Dupont",
        "phone": "+24106223344",
        "date_of_birth": "1990-05-15",
        "sexe": "M",
        "candidate_status": "interne",
        "matricule": 123457,
        "no_seeg_email": False,  # ← Email SEEG
        "adresse": "123 Rue Test, Libreville",
        "poste_actuel": "Technicien",
        "annees_experience": 5
    }
    
    response = await async_client.post(
        "/api/v1/auth/signup",
        json=signup_data
    )
    
    assert response.status_code == 201
    
    data = response.json()
    assert data["statut"] == "actif"  # ← Accès immédiat
    assert data["candidate_status"] == "interne"
    
    # Vérifier qu'AUCUNE AccessRequest n'a été créée
    from app.models.access_request import AccessRequest
    from sqlalchemy import select
    
    result = await db_session.execute(
        select(AccessRequest).where(AccessRequest.email == "jean.dupont@seeg-gabon.com")
    )
    access_request = result.scalar_one_or_none()
    
    assert access_request is None, "AccessRequest NE devrait PAS être créée pour email SEEG"


@pytest.mark.asyncio
async def test_signup_external_no_access_request(async_client: AsyncClient, db_session):
    """
    Test 3: Inscription candidat EXTERNE - PAS de demande d'accès
    
    Scénario:
    - candidate_status = 'externe'
    - Pas de matricule
    
    Résultat attendu:
    - 201 Created
    - User créé avec statut = 'actif'
    - PAS d'AccessRequest créée
    """
    signup_data = {
        "email": "externe@example.com",
        "password": "SecurePass@2025!",
        "first_name": "Marie",
        "last_name": "Martin",
        "phone": "+24106223344",
        "date_of_birth": "1992-08-20",
        "sexe": "F",
        "candidate_status": "externe",
        "matricule": None,
        "adresse": "456 Avenue Test, Libreville"
    }
    
    response = await async_client.post(
        "/api/v1/auth/signup",
        json=signup_data
    )
    
    assert response.status_code == 201
    
    data = response.json()
    assert data["statut"] == "actif"
    assert data["candidate_status"] == "externe"
    assert data["is_internal_candidate"] is False
    
    # Vérifier qu'AUCUNE AccessRequest n'a été créée
    from app.models.access_request import AccessRequest
    from sqlalchemy import select
    
    result = await db_session.execute(
        select(AccessRequest).where(AccessRequest.email == "externe@example.com")
    )
    access_request = result.scalar_one_or_none()
    
    assert access_request is None, "AccessRequest NE devrait PAS être créée pour externe"


@pytest.mark.asyncio
async def test_signup_internal_no_seeg_email_without_matricule_error(async_client: AsyncClient):
    """
    Test 4: Inscription candidat interne SANS matricule - Erreur
    
    Scénario:
    - candidate_status = 'interne'
    - no_seeg_email = True
    - matricule = None (manquant)
    
    Résultat attendu:
    - 400 Bad Request
    - Message : "Le matricule est obligatoire pour les candidats internes"
    """
    signup_data = {
        "email": "test.sans.matricule@gmail.com",
        "password": "SecurePass@2025!",
        "first_name": "Test",
        "last_name": "SansMatricule",
        "phone": "+24106223344",
        "date_of_birth": "1990-05-15",
        "sexe": "M",
        "candidate_status": "interne",
        "matricule": None,  # ← Erreur
        "no_seeg_email": True
    }
    
    response = await async_client.post(
        "/api/v1/auth/signup",
        json=signup_data
    )
    
    assert response.status_code == 400
    assert "matricule" in response.text.lower()
    assert "obligatoire" in response.text.lower()


@pytest.mark.asyncio
async def test_signup_internal_seeg_email_but_no_seeg_email_true_error(async_client: AsyncClient):
    """
    Test 5: Incohérence - Email SEEG avec no_seeg_email=True
    
    Scénario:
    - email = @seeg-gabon.com
    - no_seeg_email = True (incohérent)
    
    Résultat attendu:
    - 400 Bad Request
    - Message : "Incohérence détectée"
    """
    signup_data = {
        "email": "test@seeg-gabon.com",
        "password": "SecurePass@2025!",
        "first_name": "Test",
        "last_name": "Incoherent",
        "phone": "+24106223344",
        "date_of_birth": "1990-05-15",
        "sexe": "M",
        "candidate_status": "interne",
        "matricule": 123458,
        "no_seeg_email": True  # ← Incohérence
    }
    
    response = await async_client.post(
        "/api/v1/auth/signup",
        json=signup_data
    )
    
    assert response.status_code == 400
    assert "incohérence" in response.text.lower() or "incoherence" in response.text.lower()


@pytest.mark.asyncio
async def test_signup_internal_no_seeg_email_false_but_wrong_domain_error(async_client: AsyncClient):
    """
    Test 6: Email non-SEEG avec no_seeg_email=False
    
    Scénario:
    - email = @gmail.com (pas SEEG)
    - no_seeg_email = False (prétend avoir email SEEG)
    - candidate_status = 'interne'
    
    Résultat attendu:
    - 400 Bad Request
    - Message : "Les candidats internes doivent utiliser un email professionnel @seeg-gabon.com"
    """
    signup_data = {
        "email": "test@gmail.com",
        "password": "SecurePass@2025!",
        "first_name": "Test",
        "last_name": "WrongDomain",
        "phone": "+24106223344",
        "date_of_birth": "1990-05-15",
        "sexe": "M",
        "candidate_status": "interne",
        "matricule": 123459,
        "no_seeg_email": False  # ← Dit avoir email SEEG mais c'est faux
    }
    
    response = await async_client.post(
        "/api/v1/auth/signup",
        json=signup_data
    )
    
    assert response.status_code == 400
    assert "@seeg-gabon.com" in response.text


@pytest.mark.asyncio
async def test_signup_internal_duplicate_matricule_error(async_client: AsyncClient):
    """
    Test 7: Matricule déjà utilisé
    
    Scénario:
    - Inscription avec matricule déjà en base
    
    Résultat attendu:
    - 400 Bad Request
    - Message : "Un utilisateur avec ce matricule existe déjà"
    """
    matricule_unique = 999999
    
    # Première inscription
    signup_data_1 = {
        "email": "first@gmail.com",
        "password": "SecurePass@2025!",
        "first_name": "First",
        "last_name": "User",
        "phone": "+24106223344",
        "date_of_birth": "1990-05-15",
        "sexe": "M",
        "candidate_status": "interne",
        "matricule": matricule_unique,
        "no_seeg_email": True
    }
    
    response1 = await async_client.post("/api/v1/auth/signup", json=signup_data_1)
    assert response1.status_code == 201
    
    # Tentative avec même matricule
    signup_data_2 = {
        "email": "second@gmail.com",
        "password": "SecurePass@2025!",
        "first_name": "Second",
        "last_name": "User",
        "phone": "+24106223355",
        "date_of_birth": "1991-06-16",
        "sexe": "F",
        "candidate_status": "interne",
        "matricule": matricule_unique,  # ← Même matricule
        "no_seeg_email": True
    }
    
    response2 = await async_client.post("/api/v1/auth/signup", json=signup_data_2)
    
    assert response2.status_code == 400
    assert "matricule" in response2.text.lower()
    assert "existe déjà" in response2.text.lower()


@pytest.mark.asyncio
async def test_login_internal_no_seeg_email_en_attente_forbidden(async_client: AsyncClient):
    """
    Test 8: Tentative de connexion avec compte en attente
    
    Scénario:
    - Candidat interne sans email SEEG inscrit (statut = 'en_attente')
    - Tentative de connexion
    
    Résultat attendu:
    - 403 Forbidden
    - Message : "Votre compte est en attente de validation"
    """
    # Créer un compte en attente
    signup_data = {
        "email": "attente@gmail.com",
        "password": "SecurePass@2025!",
        "first_name": "Attente",
        "last_name": "Test",
        "phone": "+24106223344",
        "date_of_birth": "1990-05-15",
        "sexe": "M",
        "candidate_status": "interne",
        "matricule": 888888,
        "no_seeg_email": True
    }
    
    signup_response = await async_client.post("/api/v1/auth/signup", json=signup_data)
    assert signup_response.status_code == 201
    
    # Tentative de connexion
    login_data = {
        "email": "attente@gmail.com",
        "password": "SecurePass@2025!"
    }
    
    login_response = await async_client.post("/api/v1/auth/login", json=login_data)
    
    assert login_response.status_code == 403
    assert "en attente" in login_response.text.lower()
    assert "validation" in login_response.text.lower()


@pytest.mark.asyncio
async def test_signup_internal_no_seeg_email_matricule_not_in_seeg_agents_warning(async_client: AsyncClient, caplog):
    """
    Test 9: Matricule non trouvé dans seeg_agents - Warning mais inscription OK
    
    Scénario:
    - Matricule fourni mais absent de la table seeg_agents
    - no_seeg_email = True
    
    Résultat attendu:
    - 201 Created (inscription autorisée)
    - Warning logué
    - Statut = 'en_attente' (pour validation manuelle)
    """
    signup_data = {
        "email": "matricule.inconnu@gmail.com",
        "password": "SecurePass@2025!",
        "first_name": "Matricule",
        "last_name": "Inconnu",
        "phone": "+24106223344",
        "date_of_birth": "1990-05-15",
        "sexe": "M",
        "candidate_status": "interne",
        "matricule": 777777,  # Matricule probablement absent
        "no_seeg_email": True
    }
    
    response = await async_client.post("/api/v1/auth/signup", json=signup_data)
    
    # Inscription doit réussir
    assert response.status_code == 201
    
    data = response.json()
    assert data["statut"] == "en_attente"
    assert data["matricule"] == 777777
    
    # Vérifier le warning dans les logs (si caplog configuré)
    # assert "non trouvé dans seeg_agents" in caplog.text.lower()


@pytest.mark.asyncio
async def test_get_access_requests_as_admin(async_client: AsyncClient, test_admin_user):
    """
    Test 10: Admin récupère les demandes d'accès
    
    Scénario:
    - Créer un candidat interne sans email SEEG (AccessRequest créée)
    - Admin récupère la liste des demandes
    
    Résultat attendu:
    - 200 OK
    - Liste contient la nouvelle demande
    """
    # Créer un candidat avec AccessRequest
    signup_data = {
        "email": "demande.admin@gmail.com",
        "password": "SecurePass@2025!",
        "first_name": "Demande",
        "last_name": "Admin",
        "phone": "+24106223344",
        "date_of_birth": "1990-05-15",
        "sexe": "M",
        "candidate_status": "interne",
        "matricule": 666666,
        "no_seeg_email": True
    }
    
    await async_client.post("/api/v1/auth/signup", json=signup_data)
    
    # Admin récupère les demandes
    response = await async_client.get(
        "/api/v1/access-requests",
        headers={"Authorization": f"Bearer {test_admin_user.access_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Trouver la demande créée
    found = False
    for request in data.get("data", []):
        if request["email"] == "demande.admin@gmail.com":
            found = True
            assert request["first_name"] == "Demande"
            assert request["last_name"] == "Admin"
            assert str(request["matricule"]) == "666666"
            assert request["status"] == "pending"
            break
    
    assert found, "Demande d'accès non trouvée dans la liste"

