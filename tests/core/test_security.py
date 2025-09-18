"""
Tests pour les composants de sécurité
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from app.core.security.security import PasswordManager, TokenManager
from app.core.config.config import settings
import jwt


class TestPasswordManager:
    """Tests pour le gestionnaire de mots de passe."""

    def test_hash_password_success(self):
        """Test hachage de mot de passe avec succès."""
        # Arrange
        password = "test_password_123"
        
        # Act
        hashed = PasswordManager.hash_password(password)
        
        # Assert
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")

    def test_verify_password_success(self):
        """Test vérification de mot de passe avec succès."""
        # Arrange
        password = "test_password_123"
        hashed = PasswordManager.hash_password(password)
        
        # Act
        result = PasswordManager.verify_password(password, hashed)
        
        # Assert
        assert result is True

    def test_verify_password_wrong_password(self):
        """Test vérification de mot de passe incorrect."""
        # Arrange
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = PasswordManager.hash_password(password)
        
        # Act
        result = PasswordManager.verify_password(wrong_password, hashed)
        
        # Assert
        assert result is False

    def test_verify_password_invalid_hash(self):
        """Test vérification avec hash invalide."""
        # Arrange
        password = "test_password_123"
        invalid_hash = "invalid_hash"
        
        # Act
        result = PasswordManager.verify_password(password, invalid_hash)
        
        # Assert
        assert result is False


class TestTokenManager:
    """Tests pour le gestionnaire de tokens."""

    @pytest.fixture
    def token_manager(self):
        """Instance du gestionnaire de tokens."""
        return TokenManager()

    @pytest.fixture
    def sample_user_data(self):
        """Données d'utilisateur de test."""
        return {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "email": "test@example.com",
            "role": "candidate"
        }

    def test_create_access_token_success(self, token_manager, sample_user_data):
        """Test création de token d'accès avec succès."""
        # Act
        token = token_manager.create_access_token(sample_user_data)
        
        # Assert
        assert token is not None
        assert isinstance(token, str)
        
        # Vérifier que le token peut être décodé
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert decoded["sub"] == sample_user_data["id"]
        assert decoded["email"] == sample_user_data["email"]
        assert decoded["role"] == sample_user_data["role"]

    def test_create_refresh_token_success(self, token_manager, sample_user_data):
        """Test création de token de rafraîchissement avec succès."""
        # Act
        token = token_manager.create_refresh_token(sample_user_data)
        
        # Assert
        assert token is not None
        assert isinstance(token, str)
        
        # Vérifier que le token peut être décodé
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert decoded["sub"] == sample_user_data["id"]
        assert decoded["type"] == "refresh"

    def test_verify_token_success(self, token_manager, sample_user_data):
        """Test vérification de token avec succès."""
        # Arrange
        token = token_manager.create_access_token(sample_user_data)
        
        # Act
        payload = token_manager.verify_token(token)
        
        # Assert
        assert payload is not None
        assert payload["sub"] == sample_user_data["id"]
        assert payload["email"] == sample_user_data["email"]
        assert payload["role"] == sample_user_data["role"]

    def test_verify_token_invalid(self, token_manager):
        """Test vérification de token invalide."""
        # Arrange
        invalid_token = "invalid_token"
        
        # Act
        payload = token_manager.verify_token(invalid_token)
        
        # Assert
        assert payload is None

    def test_verify_token_expired(self, token_manager, sample_user_data):
        """Test vérification de token expiré."""
        # Arrange
        # Créer un token avec une expiration passée
        expired_data = sample_user_data.copy()
        expired_data["exp"] = datetime.utcnow() - timedelta(hours=1)
        
        with patch('app.core.security.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime.utcnow()
            token = jwt.encode(expired_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        # Act
        payload = token_manager.verify_token(token)
        
        # Assert
        assert payload is None

    def test_get_user_from_token_success(self, token_manager, sample_user_data):
        """Test récupération d'utilisateur depuis token avec succès."""
        # Arrange
        token = token_manager.create_access_token(sample_user_data)
        
        # Act
        user_data = token_manager.get_user_from_token(token)
        
        # Assert
        assert user_data is not None
        assert user_data["id"] == sample_user_data["id"]
        assert user_data["email"] == sample_user_data["email"]
        assert user_data["role"] == sample_user_data["role"]

    def test_get_user_from_token_invalid(self, token_manager):
        """Test récupération d'utilisateur depuis token invalide."""
        # Arrange
        invalid_token = "invalid_token"
        
        # Act
        user_data = token_manager.get_user_from_token(invalid_token)
        
        # Assert
        assert user_data is None

    def test_create_token_pair_success(self, token_manager, sample_user_data):
        """Test création de paire de tokens avec succès."""
        # Act
        access_token, refresh_token = token_manager.create_token_pair(sample_user_data)
        
        # Assert
        assert access_token is not None
        assert refresh_token is not None
        assert isinstance(access_token, str)
        assert isinstance(refresh_token, str)
        
        # Vérifier que les tokens sont différents
        assert access_token != refresh_token

    def test_refresh_access_token_success(self, token_manager, sample_user_data):
        """Test rafraîchissement de token d'accès avec succès."""
        # Arrange
        refresh_token = token_manager.create_refresh_token(sample_user_data)
        
        # Act
        new_access_token = token_manager.refresh_access_token(refresh_token)
        
        # Assert
        assert new_access_token is not None
        assert isinstance(new_access_token, str)
        
        # Vérifier que le nouveau token est valide
        payload = token_manager.verify_token(new_access_token)
        assert payload is not None
        assert payload["sub"] == sample_user_data["id"]

    def test_refresh_access_token_invalid_refresh(self, token_manager):
        """Test rafraîchissement avec token de rafraîchissement invalide."""
        # Arrange
        invalid_refresh_token = "invalid_refresh_token"
        
        # Act
        new_access_token = token_manager.refresh_access_token(invalid_refresh_token)
        
        # Assert
        assert new_access_token is None

    def test_token_expiration_times(self, token_manager, sample_user_data):
        """Test des temps d'expiration des tokens."""
        # Act
        access_token = token_manager.create_access_token(sample_user_data)
        refresh_token = token_manager.create_refresh_token(sample_user_data)
        
        # Assert
        access_payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        refresh_payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # Vérifier que le token de rafraîchissement expire plus tard que le token d'accès
        assert refresh_payload["exp"] > access_payload["exp"]
