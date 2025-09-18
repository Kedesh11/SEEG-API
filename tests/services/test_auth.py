"""
Tests pour le service d'authentification
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from app.services.auth import AuthService
from app.models.user import User
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse
from app.core.exceptions import UnauthorizedError, ValidationError, BusinessLogicError


class TestAuthService:
    """Tests pour le service d'authentification."""
    
    def setup_method(self):
        """Configuration pour chaque test."""
        self.mock_db = AsyncMock()
        self.auth_service = AuthService(self.mock_db)
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self):
        """Test l'authentification réussie d'un utilisateur."""
        # Mock des données
        email = "test@example.com"
        password = "password123"
        hashed_password = "hashed_password"
        
        user = User(
            id="user-id",
            email=email,
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        user.hashed_password = hashed_password
        
        # Mock de la base de données
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        self.mock_db.execute.return_value = mock_result
        
        # Mock du password manager
        with patch.object(self.auth_service.password_manager, 'verify_password', return_value=True):
            result = await self.auth_service.authenticate_user(email, password)
            
            assert result == user
            self.mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self):
        """Test l'authentification avec un utilisateur inexistant."""
        email = "nonexistent@example.com"
        password = "password123"
        
        # Mock de la base de données - utilisateur non trouvé
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute.return_value = mock_result
        
        result = await self.auth_service.authenticate_user(email, password)
        
        assert result is None
        self.mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self):
        """Test l'authentification avec un mauvais mot de passe."""
        email = "test@example.com"
        password = "wrong_password"
        hashed_password = "hashed_password"
        
        user = User(
            id="user-id",
            email=email,
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        user.hashed_password = hashed_password
        
        # Mock de la base de données
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        self.mock_db.execute.return_value = mock_result
        
        # Mock du password manager - mot de passe incorrect
        with patch.object(self.auth_service.password_manager, 'verify_password', return_value=False):
            result = await self.auth_service.authenticate_user(email, password)
            
            assert result is None
            self.mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_user_database_error(self):
        """Test la gestion des erreurs de base de données."""
        email = "test@example.com"
        password = "password123"
        
        # Mock d'une erreur de base de données
        self.mock_db.execute.side_effect = Exception("Database error")
        
        with pytest.raises(UnauthorizedError):
            await self.auth_service.authenticate_user(email, password)
    
    @pytest.mark.asyncio
    async def test_create_user_success(self):
        """Test la création réussie d'un utilisateur."""
        user_data = SignupRequest(
            email="newuser@example.com",
            password="password123",
            first_name="Jane",
            last_name="Smith",
            role="candidate"
        )
        
        # Mock - utilisateur n'existe pas
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute.return_value = mock_result
        
        # Mock du password manager
        with patch.object(self.auth_service.password_manager, 'hash_password', return_value="hashed_password"):
            with patch.object(self.auth_service, '_create_user_instance') as mock_create:
                mock_user = User(
                    id="new-user-id",
                    email=user_data.email,
                    first_name=user_data.first_name,
                    last_name=user_data.last_name,
                    role=user_data.role
                )
                mock_create.return_value = mock_user
                
                result = await self.auth_service.create_user(user_data)
                
                assert result == mock_user
                self.mock_db.execute.assert_called()
                self.mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_create_user_already_exists(self):
        """Test la création d'un utilisateur qui existe déjà."""
        user_data = SignupRequest(
            email="existing@example.com",
            password="password123",
            first_name="Jane",
            last_name="Smith",
            role="candidate"
        )
        
        # Mock - utilisateur existe déjà
        existing_user = User(
            id="existing-user-id",
            email=user_data.email,
            first_name="Existing",
            last_name="User",
            role="candidate"
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user
        self.mock_db.execute.return_value = mock_result
        
        with pytest.raises(ValidationError, match="Un utilisateur avec cet email existe déjà"):
            await self.auth_service.create_user(user_data)
    
    @pytest.mark.asyncio
    async def test_generate_tokens(self):
        """Test la génération de tokens."""
        user = User(
            id="user-id",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        
        # Mock du token manager
        with patch.object(self.auth_service.token_manager, 'create_access_token', return_value="access_token"):
            with patch.object(self.auth_service.token_manager, 'create_refresh_token', return_value="refresh_token"):
                result = await self.auth_service.generate_tokens(user)
                
                assert isinstance(result, TokenResponse)
                assert result.access_token == "access_token"
                assert result.refresh_token == "refresh_token"
                assert result.token_type == "bearer"
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self):
        """Test le rafraîchissement de token réussi."""
        refresh_token = "valid_refresh_token"
        user_id = "user-id"
        
        user = User(
            id=user_id,
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        
        # Mock du token manager
        with patch.object(self.auth_service.token_manager, 'verify_refresh_token', return_value=user_id):
            with patch.object(self.auth_service, 'get_user_by_id', return_value=user):
                with patch.object(self.auth_service, 'generate_tokens') as mock_generate:
                    mock_tokens = TokenResponse(
                        access_token="new_access_token",
                        refresh_token="new_refresh_token",
                        token_type="bearer"
                    )
                    mock_generate.return_value = mock_tokens
                    
                    result = await self.auth_service.refresh_token(refresh_token)
                    
                    assert result == mock_tokens
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self):
        """Test le rafraîchissement avec un token invalide."""
        refresh_token = "invalid_refresh_token"
        
        # Mock du token manager - token invalide
        with patch.object(self.auth_service.token_manager, 'verify_refresh_token', return_value=None):
            with pytest.raises(UnauthorizedError, match="Token de rafraîchissement invalide"):
                await self.auth_service.refresh_token(refresh_token)
