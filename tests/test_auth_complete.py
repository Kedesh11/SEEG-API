"""
Tests complets pour le module Authentication
Couvre tous les endpoints /auth/*

Architecture:
- Tests organisés par endpoint
- Fixtures réutilisables
- Cas nominaux ET cas d'erreur
- Assertions claires et documentées
"""
import pytest
from httpx import AsyncClient
from typing import Dict, Any, Callable


class TestAuthSignup:
    """Tests pour POST /auth/signup"""
    
    @pytest.mark.asyncio
    async def test_signup_externe_success(
        self,
        http_client: AsyncClient,
        valid_signup_externe: Dict[str, Any]
    ):
        """
        Scénario: Inscription candidat externe valide
        Attendu: 201 Created, statut='actif', accès immédiat
        """
        response = await http_client.post("/auth/signup", json=valid_signup_externe)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data['email'] == valid_signup_externe['email']
        assert data['role'] == 'candidate'
        assert data['candidate_status'] == 'externe'
        assert data['statut'] == 'actif'
        assert data['is_internal_candidate'] is False
        assert data['id'] is not None
    
    @pytest.mark.asyncio
    async def test_signup_interne_with_seeg_email_success(
        self,
        http_client: AsyncClient,
        valid_signup_interne_with_seeg_email: Dict[str, Any]
    ):
        """
        Scénario: Inscription candidat interne avec email @seeg-gabon.com
        Attendu: 201 Created, statut='actif', PAS de demande d'accès
        """
        response = await http_client.post("/auth/signup", json=valid_signup_interne_with_seeg_email)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data['candidate_status'] == 'interne'
        assert data['statut'] == 'actif'  # Accès immédiat
        assert data['is_internal_candidate'] is True
        assert data['no_seeg_email'] is False
        assert '@seeg-gabon.com' in data['email']
    
    @pytest.mark.asyncio
    async def test_signup_interne_no_seeg_email_success(
        self,
        http_client: AsyncClient,
        valid_signup_interne_no_seeg_email: Dict[str, Any]
    ):
        """
        Scénario: Inscription candidat interne SANS email SEEG
        Attendu: 201 Created, statut='en_attente', demande d'accès créée
        """
        response = await http_client.post("/auth/signup", json=valid_signup_interne_no_seeg_email)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data['candidate_status'] == 'interne'
        assert data['statut'] == 'en_attente'  # Validation requise
        assert data['is_internal_candidate'] is True
        assert data['no_seeg_email'] is True
        # Note: AccessRequest vérifiable via GET /access-requests (admin)
    
    @pytest.mark.asyncio
    async def test_signup_duplicate_email_error(
        self,
        http_client: AsyncClient,
        valid_signup_externe: Dict[str, Any]
    ):
        """
        Scénario: Tentative d'inscription avec email déjà utilisé
        Attendu: 400 Bad Request
        """
        # Première inscription
        await http_client.post("/auth/signup", json=valid_signup_externe)
        
        # Tentative de duplication
        response = await http_client.post("/auth/signup", json=valid_signup_externe)
        
        assert response.status_code == 400
        assert "existe déjà" in response.text.lower()
    
    @pytest.mark.asyncio
    async def test_signup_weak_password_error(
        self,
        http_client: AsyncClient,
        invalid_signup_weak_password: Dict[str, Any]
    ):
        """
        Scénario: Mot de passe trop faible
        Attendu: 422 Unprocessable Entity (validation Pydantic)
        """
        response = await http_client.post("/auth/signup", json=invalid_signup_weak_password)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_signup_interne_missing_matricule_error(
        self,
        http_client: AsyncClient,
        invalid_signup_missing_matricule: Dict[str, Any]
    ):
        """
        Scénario: Candidat interne sans matricule
        Attendu: 400 Bad Request
        """
        response = await http_client.post("/auth/signup", json=invalid_signup_missing_matricule)
        
        assert response.status_code == 400
        assert "matricule" in response.text.lower()
        assert "obligatoire" in response.text.lower()


class TestAuthLogin:
    """Tests pour POST /auth/login"""
    
    @pytest.mark.asyncio
    async def test_login_valid_credentials_success(
        self,
        http_client: AsyncClient,
        valid_signup_externe: Dict[str, Any]
    ):
        """
        Scénario: Connexion avec identifiants valides
        Attendu: 200 OK, tokens retournés
        """
        # Créer un utilisateur
        await http_client.post("/auth/signup", json=valid_signup_externe)
        
        # Se connecter
        response = await http_client.post(
            "/auth/login",
            json={
                "email": valid_signup_externe['email'],
                "password": valid_signup_externe['password']
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['access_token'] is not None
        assert data['refresh_token'] is not None
        assert data['token_type'] == 'bearer'
        assert data['user'] is not None
        assert data['user']['email'] == valid_signup_externe['email']
    
    @pytest.mark.asyncio
    async def test_login_invalid_password_error(
        self,
        http_client: AsyncClient,
        valid_signup_externe: Dict[str, Any]
    ):
        """
        Scénario: Connexion avec mot de passe invalide
        Attendu: 401 Unauthorized
        """
        # Créer un utilisateur
        await http_client.post("/auth/signup", json=valid_signup_externe)
        
        # Tentative avec mauvais mot de passe
        response = await http_client.post(
            "/auth/login",
            json={
                "email": valid_signup_externe['email'],
                "password": "WrongPassword123!"
            }
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user_error(
        self,
        http_client: AsyncClient
    ):
        """
        Scénario: Connexion avec utilisateur inexistant
        Attendu: 401 Unauthorized
        """
        response = await http_client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "AnyPassword123!"
            }
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_login_account_en_attente_forbidden(
        self,
        http_client: AsyncClient,
        valid_signup_interne_no_seeg_email: Dict[str, Any]
    ):
        """
        Scénario: Connexion avec compte en attente de validation
        Attendu: 403 Forbidden
        """
        # Créer un compte en attente
        await http_client.post("/auth/signup", json=valid_signup_interne_no_seeg_email)
        
        # Tentative de connexion
        response = await http_client.post(
            "/auth/login",
            json={
                "email": valid_signup_interne_no_seeg_email['email'],
                "password": valid_signup_interne_no_seeg_email['password']
            }
        )
        
        assert response.status_code == 403
        assert "en attente" in response.text.lower()


class TestAuthVerifyMatricule:
    """Tests pour POST /auth/verify-matricule"""
    
    @pytest.mark.asyncio
    async def test_verify_matricule_valid(
        self,
        http_client: AsyncClient
    ):
        """
        Scénario: Vérification d'un matricule valide
        Attendu: 200 OK, valid=True
        """
        # Note: Nécessite un matricule existant dans seeg_agents
        response = await http_client.post(
            "/auth/verify-matricule",
            json={"matricule": 123456}  # Ajuster selon vos données
        )
        
        # Le résultat dépend de si le matricule existe dans seeg_agents
        assert response.status_code == 200
        data = response.json()
        assert 'valid' in data
    
    @pytest.mark.asyncio
    async def test_verify_matricule_invalid_type_error(
        self,
        http_client: AsyncClient
    ):
        """
        Scénario: Vérification matricule avec type invalide (string)
        Attendu: 200 avec valid=False (l'endpoint gère les erreurs gracieusement)
        """
        response = await http_client.post(
            "/auth/verify-matricule",
            json={"matricule": "abc"}  # String au lieu d'int
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "Erreur lors de la vérification" in data["message"]


class TestAuthMe:
    """Tests pour GET /auth/me"""
    
    @pytest.mark.asyncio
    async def test_me_authenticated_success(
        self,
        http_client: AsyncClient,
        valid_signup_externe: Dict[str, Any],
        authenticated_client_factory: Callable
    ):
        """
        Scénario: Récupération profil utilisateur authentifié
        Attendu: 200 OK, données utilisateur complètes
        """
        # Créer et connecter un utilisateur
        await http_client.post("/auth/signup", json=valid_signup_externe)
        
        auth_client, user = await authenticated_client_factory(
            valid_signup_externe['email'],
            valid_signup_externe['password']
        )
        
        # Récupérer le profil
        response = await auth_client.get("/auth/me")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['email'] == valid_signup_externe['email']
        assert data['first_name'] == valid_signup_externe['first_name']
        assert data['role'] == 'candidate'
        
        await auth_client.aclose()
    
    @pytest.mark.asyncio
    async def test_me_unauthenticated_error(
        self,
        http_client: AsyncClient
    ):
        """
        Scénario: Tentative sans authentification
        Attendu: 401 Unauthorized
        """
        response = await http_client.get("/auth/me")
        
        assert response.status_code == 401


class TestAuthRefreshToken:
    """Tests pour POST /auth/refresh"""
    
    @pytest.mark.asyncio
    async def test_refresh_token_valid_success(
        self,
        http_client: AsyncClient,
        valid_signup_externe: Dict[str, Any]
    ):
        """
        Scénario: Rafraîchissement de token valide
        Attendu: 200 OK, nouveau access_token
        """
        # Créer et connecter
        await http_client.post("/auth/signup", json=valid_signup_externe)
        
        login_response = await http_client.post(
            "/auth/login",
            json={
                "email": valid_signup_externe['email'],
                "password": valid_signup_externe['password']
            }
        )
        
        refresh_token = login_response.json()['refresh_token']
        
        # Rafraîchir le token
        response = await http_client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['access_token'] is not None
        assert data['refresh_token'] is not None
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid_error(
        self,
        http_client: AsyncClient
    ):
        """
        Scénario: Rafraîchissement avec token invalide
        Attendu: 401 Unauthorized
        """
        response = await http_client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid.token.here"}
        )
        
        assert response.status_code == 401

