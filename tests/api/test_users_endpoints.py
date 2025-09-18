"""
Tests pour les endpoints des utilisateurs
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from app.main import app
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.exceptions import NotFoundError, ValidationError
import uuid

client = TestClient(app)


class TestUsersEndpoints:
    """Tests pour les endpoints des utilisateurs."""

    @pytest.fixture
    def mock_current_user(self):
        """Mock utilisateur actuel."""
        user = Mock(spec=User)
        user.id = uuid.uuid4()
        user.role = "admin"
        user.email = "admin@test.com"
        return user

    @pytest.fixture
    def sample_user_data(self):
        """Données d'utilisateur de test."""
        return {
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "candidate",
            "phone": "+33123456789",
            "date_of_birth": "1990-01-01",
            "sexe": "M"
        }

    @pytest.fixture
    def sample_user(self):
        """Utilisateur de test."""
        user = Mock(spec=User)
        user.id = uuid.uuid4()
        user.email = "test@example.com"
        user.first_name = "John"
        user.last_name = "Doe"
        user.role = "candidate"
        user.phone = "+33123456789"
        user.date_of_birth = "1990-01-01"
        user.sexe = "M"
        user.created_at = "2024-01-01T00:00:00Z"
        user.updated_at = "2024-01-01T00:00:00Z"
        return user

    @patch('app.api.v1.endpoints.users.get_current_user')
    @patch('app.api.v1.endpoints.users.UserService')
    def test_create_user_success(self, mock_user_service, mock_get_current_user,
                                mock_current_user, sample_user_data, sample_user):
        """Test création d'utilisateur avec succès."""
        # Arrange
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_user_service.return_value = mock_service_instance
        mock_service_instance.create_user.return_value = sample_user

        # Act
        response = client.post("/api/v1/users/", json=sample_user_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == sample_user_data["email"]
        assert data["first_name"] == sample_user_data["first_name"]
        mock_service_instance.create_user.assert_called_once()

    @patch('app.api.v1.endpoints.users.get_current_user')
    def test_create_user_unauthorized(self, mock_get_current_user):
        """Test création d'utilisateur sans autorisation."""
        # Arrange
        mock_get_current_user.side_effect = Exception("Unauthorized")

        # Act
        response = client.post("/api/v1/users/", json={})

        # Assert
        assert response.status_code == 401

    @patch('app.api.v1.endpoints.users.get_current_user')
    @patch('app.api.v1.endpoints.users.UserService')
    def test_get_users_success(self, mock_user_service, mock_get_current_user,
                              mock_current_user, sample_user):
        """Test récupération des utilisateurs avec succès."""
        # Arrange
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_user_service.return_value = mock_service_instance
        mock_service_instance.get_users.return_value = [sample_user]

        # Act
        response = client.get("/api/v1/users/")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["email"] == sample_user.email

    @patch('app.api.v1.endpoints.users.get_current_user')
    @patch('app.api.v1.endpoints.users.UserService')
    def test_get_user_by_id_success(self, mock_user_service, mock_get_current_user,
                                   mock_current_user, sample_user):
        """Test récupération d'un utilisateur par ID avec succès."""
        # Arrange
        user_id = str(sample_user.id)
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_user_service.return_value = mock_service_instance
        mock_service_instance.get_user_by_id.return_value = sample_user

        # Act
        response = client.get(f"/api/v1/users/{user_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["email"] == sample_user.email

    @patch('app.api.v1.endpoints.users.get_current_user')
    @patch('app.api.v1.endpoints.users.UserService')
    def test_get_user_by_id_not_found(self, mock_user_service, mock_get_current_user,
                                     mock_current_user):
        """Test récupération d'un utilisateur inexistant."""
        # Arrange
        user_id = str(uuid.uuid4())
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_user_service.return_value = mock_service_instance
        mock_service_instance.get_user_by_id.side_effect = NotFoundError("Utilisateur non trouvé")

        # Act
        response = client.get(f"/api/v1/users/{user_id}")

        # Assert
        assert response.status_code == 404

    @patch('app.api.v1.endpoints.users.get_current_user')
    @patch('app.api.v1.endpoints.users.UserService')
    def test_update_user_success(self, mock_user_service, mock_get_current_user,
                                mock_current_user, sample_user):
        """Test mise à jour d'utilisateur avec succès."""
        # Arrange
        user_id = str(sample_user.id)
        update_data = {"first_name": "Jane"}
        updated_user = Mock(spec=User)
        updated_user.id = sample_user.id
        updated_user.first_name = "Jane"
        updated_user.last_name = sample_user.last_name
        updated_user.email = sample_user.email
        
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_user_service.return_value = mock_service_instance
        mock_service_instance.update_user.return_value = updated_user

        # Act
        response = client.put(f"/api/v1/users/{user_id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Jane"

    @patch('app.api.v1.endpoints.users.get_current_user')
    @patch('app.api.v1.endpoints.users.UserService')
    def test_delete_user_success(self, mock_user_service, mock_get_current_user,
                                mock_current_user):
        """Test suppression d'utilisateur avec succès."""
        # Arrange
        user_id = str(uuid.uuid4())
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_user_service.return_value = mock_service_instance
        mock_service_instance.delete_user.return_value = True

        # Act
        response = client.delete(f"/api/v1/users/{user_id}")

        # Assert
        assert response.status_code == 204

    @patch('app.api.v1.endpoints.users.get_current_user')
    @patch('app.api.v1.endpoints.users.UserService')
    def test_get_user_profile_success(self, mock_user_service, mock_get_current_user,
                                     mock_current_user, sample_user):
        """Test récupération du profil utilisateur avec succès."""
        # Arrange
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_user_service.return_value = mock_service_instance
        mock_service_instance.get_user_profile.return_value = sample_user

        # Act
        response = client.get("/api/v1/users/me")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == sample_user.email

    @patch('app.api.v1.endpoints.users.get_current_user')
    @patch('app.api.v1.endpoints.users.UserService')
    def test_search_users(self, mock_user_service, mock_get_current_user,
                         mock_current_user, sample_user):
        """Test recherche d'utilisateurs."""
        # Arrange
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_user_service.return_value = mock_service_instance
        mock_service_instance.search_users.return_value = [sample_user]

        # Act
        response = client.get("/api/v1/users/search?q=john&role=candidate")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
