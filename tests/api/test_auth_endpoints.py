"""
Tests pour les endpoints d'authentification
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI, status
from app.api.v1.endpoints.auth import router
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse
from app.models.user import User


class TestAuthEndpoints:
    """Tests pour les endpoints d'authentification."""
    
    def setup_method(self):
        """Configuration pour chaque test."""
        self.app = FastAPI()
        self.app.include_router(router, prefix="/auth")
        self.client = TestClient(self.app)
    
    @patch('app.api.v1.endpoints.auth.AuthService')
    @patch('app.api.v1.endpoints.auth.get_async_db_session')
    def test_login_success(self, mock_get_db, mock_auth_service):
        """Test de connexion réussie."""
        # Mock des données
        login_data = {
            "email": "test@example.com",
            "password": "password123"
        }
        
        user = User(
            id="user-id",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        
        tokens = TokenResponse(
            access_token="access_token",
            refresh_token="refresh_token",
            token_type="bearer"
        )
        
        # Mock du service
        mock_service_instance = AsyncMock()
        mock_service_instance.authenticate_user.return_value = user
        mock_service_instance.create_access_token.return_value = tokens
        mock_auth_service.return_value = mock_service_instance
        
        # Mock de la session DB
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Test
        response = self.client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "access_token"
        assert data["refresh_token"] == "refresh_token"
        assert data["token_type"] == "bearer"
    
    @patch('app.api.v1.endpoints.auth.AuthService')
    @patch('app.api.v1.endpoints.auth.get_async_db_session')
    def test_login_invalid_credentials(self, mock_get_db, mock_auth_service):
        """Test de connexion avec des identifiants invalides."""
        login_data = {
            "email": "test@example.com",
            "password": "wrong_password"
        }
        
        # Mock du service - authentification échouée
        mock_service_instance = AsyncMock()
        mock_service_instance.authenticate_user.return_value = None
        mock_auth_service.return_value = mock_service_instance
        
        # Mock de la session DB
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Test
        response = self.client.post("/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "Email ou mot de passe incorrect" in data["detail"]
    
    @patch('app.api.v1.endpoints.auth.AuthService')
    @patch('app.api.v1.endpoints.auth.get_async_db_session')
    def test_signup_success(self, mock_get_db, mock_auth_service):
        """Test d'inscription réussie."""
        signup_data = {
            "email": "newuser@example.com",
            "password": "password123",
            "first_name": "Jane",
            "last_name": "Smith",
            "role": "candidate"
        }
        
        user = User(
            id="new-user-id",
            email="newuser@example.com",
            first_name="Jane",
            last_name="Smith",
            role="candidate"
        )
        
        tokens = TokenResponse(
            access_token="access_token",
            refresh_token="refresh_token",
            token_type="bearer"
        )
        
        # Mock du service
        mock_service_instance = AsyncMock()
        mock_service_instance.create_user.return_value = user
        mock_service_instance.create_access_token.return_value = tokens
        mock_auth_service.return_value = mock_service_instance
        
        # Mock de la session DB
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Test
        response = self.client.post("/auth/signup", json=signup_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["access_token"] == "access_token"
        assert data["refresh_token"] == "refresh_token"
        assert data["token_type"] == "bearer"
    
    @patch('app.api.v1.endpoints.auth.AuthService')
    @patch('app.api.v1.endpoints.auth.get_async_db_session')
    def test_signup_user_already_exists(self, mock_get_db, mock_auth_service):
        """Test d'inscription avec un utilisateur existant."""
        signup_data = {
            "email": "existing@example.com",
            "password": "password123",
            "first_name": "Jane",
            "last_name": "Smith",
            "role": "candidate"
        }
        
        # Mock du service - utilisateur existe déjà
        mock_service_instance = AsyncMock()
        mock_service_instance.create_user.side_effect = Exception("Un utilisateur avec cet email existe déjà")
        mock_auth_service.return_value = mock_service_instance
        
        # Mock de la session DB
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Test
        response = self.client.post("/auth/signup", json=signup_data)
        
        assert response.status_code == 400
    
    @patch('app.api.v1.endpoints.auth.AuthService')
    @patch('app.api.v1.endpoints.auth.get_async_db_session')
    def test_refresh_token_success(self, mock_get_db, mock_auth_service):
        """Test de rafraîchissement de token réussi."""
        refresh_data = {
            "refresh_token": "valid_refresh_token"
        }
        
        tokens = TokenResponse(
            access_token="new_access_token",
            refresh_token="new_refresh_token",
            token_type="bearer"
        )
        
        # Mock du service
        mock_service_instance = AsyncMock()
        mock_service_instance.refresh_token.return_value = tokens
        mock_auth_service.return_value = mock_service_instance
        
        # Mock de la session DB
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Test
        response = self.client.post("/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "new_access_token"
        assert data["refresh_token"] == "new_refresh_token"
    
    @patch('app.api.v1.endpoints.auth.AuthService')
    @patch('app.api.v1.endpoints.auth.get_async_db_session')
    def test_refresh_token_invalid(self, mock_get_db, mock_auth_service):
        """Test de rafraîchissement avec un token invalide."""
        refresh_data = {
            "refresh_token": "invalid_refresh_token"
        }
        
        # Mock du service - token invalide
        mock_service_instance = AsyncMock()
        mock_service_instance.refresh_token.side_effect = Exception("Token de rafraîchissement invalide")
        mock_auth_service.return_value = mock_service_instance
        
        # Mock de la session DB
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Test
        response = self.client.post("/auth/refresh", json=refresh_data)
        
        assert response.status_code == 401
    
    def test_login_missing_fields(self):
        """Test de connexion avec des champs manquants."""
        login_data = {
            "email": "test@example.com"
            # password manquant
        }
        
        response = self.client.post("/auth/login", json=login_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_signup_missing_fields(self):
        """Test d'inscription avec des champs manquants."""
        signup_data = {
            "email": "test@example.com",
            "password": "password123"
            # first_name, last_name, role manquants
        }
        
        response = self.client.post("/auth/signup", json=signup_data)
        
        assert response.status_code == 422  # Validation error
