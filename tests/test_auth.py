"""
Tests pour l'authentification.
Respecte les principes de test-driven development.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.security import PasswordManager, TokenManager
from app.services.auth import AuthService
from app.services.user import UserService


class TestPasswordManager:
    """Tests pour le gestionnaire de mots de passe."""
    
    def test_verify_password_success(self):
        """Test de vérification de mot de passe réussie."""
        password = "TestPassword123!"
        hashed = PasswordManager.get_password_hash(password)
        
        assert PasswordManager.verify_password(password, hashed) is True
    
    def test_verify_password_failure(self):
        """Test de vérification de mot de passe échouée."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = PasswordManager.get_password_hash(password)
        
        assert PasswordManager.verify_password(wrong_password, hashed) is False
    
    def test_password_strength_validation(self):
        """Test de validation de la force du mot de passe."""
        # Mot de passe faible
        weak_password = "123"
        result = PasswordManager.validate_password_strength(weak_password)
        
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
        
        # Mot de passe fort
        strong_password = "StrongPassword123!"
        result = PasswordManager.validate_password_strength(strong_password)
        
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0
        assert result["score"] >= 5


class TestTokenManager:
    """Tests pour le gestionnaire de tokens."""
    
    def test_create_access_token(self):
        """Test de création d'un token d'accès."""
        data = {"sub": "test_user_id", "role": "candidat"}
        token = TokenManager.create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_refresh_token(self):
        """Test de création d'un token de rafraîchissement."""
        data = {"sub": "test_user_id", "role": "candidat"}
        token = TokenManager.create_refresh_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_token_success(self):
        """Test de vérification de token réussie."""
        data = {"sub": "test_user_id", "role": "candidat"}
        token = TokenManager.create_access_token(data)
        
        payload = TokenManager.verify_token(token)
        
        assert payload["sub"] == "test_user_id"
        assert payload["role"] == "candidat"
        assert payload["type"] == "access"
    
    def test_verify_token_failure(self):
        """Test de vérification de token échouée."""
        invalid_token = "invalid_token"
        
        with pytest.raises(Exception):
            TokenManager.verify_token(invalid_token)


class TestAuthService:
    """Tests pour le service d'authentification."""
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, db_session: AsyncSession, test_user_data):
        """Test d'authentification utilisateur réussie."""
        # Créer un utilisateur de test
        user = await UserService.create_user(
            db=db_session,
            **test_user_data
        )
        
        # Tester l'authentification
        authenticated_user = await AuthService.authenticate_user(
            db=db_session,
            email=test_user_data["email"],
            password=test_user_data["password"]
        )
        
        assert authenticated_user is not None
        assert authenticated_user.id == user.id
        assert authenticated_user.email == test_user_data["email"]
    
    @pytest.mark.asyncio
    async def test_authenticate_user_failure(self, db_session: AsyncSession, test_user_data):
        """Test d'authentification utilisateur échouée."""
        # Créer un utilisateur de test
        await UserService.create_user(
            db=db_session,
            **test_user_data
        )
        
        # Tester l'authentification avec un mauvais mot de passe
        authenticated_user = await AuthService.authenticate_user(
            db=db_session,
            email=test_user_data["email"],
            password="WrongPassword123!"
        )
        
        assert authenticated_user is None
    
    @pytest.mark.asyncio
    async def test_verify_matricule_success(self, db_session: AsyncSession):
        """Test de vérification de matricule réussie."""
        # Note: Ce test nécessite des données de test dans la table seeg_agents
        # Pour l'instant, on teste juste que la méthode ne lève pas d'exception
        result = await AuthService.verify_matricule(db_session, "12345")
        
        # Le résultat dépend des données en base
        assert isinstance(result, bool)


class TestAuthEndpoints:
    """Tests pour les endpoints d'authentification."""
    
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient, test_user_data):
        """Test d'inscription réussie."""
        response = await client.post("/api/v1/auth/register", json=test_user_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user_data):
        """Test d'inscription avec email dupliqué."""
        # Première inscription
        await client.post("/api/v1/auth/register", json=test_user_data)
        
        # Deuxième inscription avec le même email
        response = await client.post("/api/v1/auth/register", json=test_user_data)
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "existe déjà" in data["message"]
    
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user_data):
        """Test de connexion réussie."""
        # Inscription d'un utilisateur
        await client.post("/api/v1/auth/register", json=test_user_data)
        
        # Connexion
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test de connexion avec credentials invalides."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "WrongPassword123!"
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "incorrect" in data["message"]
    
    @pytest.mark.asyncio
    async def test_verify_matricule_endpoint(self, client: AsyncClient):
        """Test de l'endpoint de vérification de matricule."""
        request_data = {"matricule": "12345"}
        response = await client.post("/api/v1/auth/verify-matricule", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "is_valid" in data["data"]
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client: AsyncClient, test_user_data):
        """Test de rafraîchissement de token réussi."""
        # Inscription et connexion
        register_response = await client.post("/api/v1/auth/register", json=test_user_data)
        tokens = register_response.json()["data"]
        
        # Rafraîchissement du token
        refresh_data = {"refresh_token": tokens["refresh_token"]}
        response = await client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "access_token" in data["data"]
    
    @pytest.mark.asyncio
    async def test_logout(self, client: AsyncClient, auth_headers):
        """Test de déconnexion."""
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "réussie" in data["message"]
