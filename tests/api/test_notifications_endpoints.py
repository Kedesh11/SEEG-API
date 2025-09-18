"""
Tests pour les endpoints des notifications
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from app.main import app
from app.models.notification import Notification
from app.schemas.notification import NotificationCreate, NotificationUpdate
from app.core.exceptions import NotFoundError, ValidationError
import uuid

client = TestClient(app)


class TestNotificationsEndpoints:
    """Tests pour les endpoints des notifications."""

    @pytest.fixture
    def mock_current_user(self):
        """Mock utilisateur actuel."""
        user = Mock()
        user.id = uuid.uuid4()
        user.role = "candidate"
        user.email = "candidate@test.com"
        return user

    @pytest.fixture
    def sample_notification_data(self):
        """Données de notification de test."""
        return {
            "user_id": str(uuid.uuid4()),
            "title": "Nouvelle candidature",
            "message": "Votre candidature a été reçue avec succès",
            "type": "application_received",
            "link": "/applications/123"
        }

    @pytest.fixture
    def sample_notification(self):
        """Notification de test."""
        notification = Mock(spec=Notification)
        notification.id = 1
        notification.user_id = uuid.uuid4()
        notification.title = "Nouvelle candidature"
        notification.message = "Votre candidature a été reçue avec succès"
        notification.type = "application_received"
        notification.link = "/applications/123"
        notification.read = False
        notification.created_at = "2024-01-01T00:00:00Z"
        return notification

    @patch('app.api.v1.endpoints.notifications.get_current_user')
    @patch('app.api.v1.endpoints.notifications.NotificationService')
    def test_create_notification_success(self, mock_notification_service, mock_get_current_user,
                                        mock_current_user, sample_notification_data, sample_notification):
        """Test création de notification avec succès."""
        # Arrange
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_notification_service.return_value = mock_service_instance
        mock_service_instance.create_notification.return_value = sample_notification

        # Act
        response = client.post("/api/v1/notifications/", json=sample_notification_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == sample_notification_data["title"]
        assert data["message"] == sample_notification_data["message"]
        mock_service_instance.create_notification.assert_called_once()

    @patch('app.api.v1.endpoints.notifications.get_current_user')
    @patch('app.api.v1.endpoints.notifications.NotificationService')
    def test_get_notifications_success(self, mock_notification_service, mock_get_current_user,
                                      mock_current_user, sample_notification):
        """Test récupération des notifications avec succès."""
        # Arrange
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_notification_service.return_value = mock_service_instance
        mock_service_instance.get_user_notifications.return_value = [sample_notification]

        # Act
        response = client.get("/api/v1/notifications/")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == sample_notification.title

    @patch('app.api.v1.endpoints.notifications.get_current_user')
    @patch('app.api.v1.endpoints.notifications.NotificationService')
    def test_get_notification_by_id_success(self, mock_notification_service, mock_get_current_user,
                                           mock_current_user, sample_notification):
        """Test récupération d'une notification par ID avec succès."""
        # Arrange
        notification_id = sample_notification.id
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_notification_service.return_value = mock_service_instance
        mock_service_instance.get_notification_by_id.return_value = sample_notification

        # Act
        response = client.get(f"/api/v1/notifications/{notification_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == notification_id
        assert data["title"] == sample_notification.title

    @patch('app.api.v1.endpoints.notifications.get_current_user')
    @patch('app.api.v1.endpoints.notifications.NotificationService')
    def test_mark_notification_as_read_success(self, mock_notification_service, mock_get_current_user,
                                              mock_current_user, sample_notification):
        """Test marquage d'une notification comme lue avec succès."""
        # Arrange
        notification_id = sample_notification.id
        updated_notification = Mock(spec=Notification)
        updated_notification.id = sample_notification.id
        updated_notification.read = True
        
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_notification_service.return_value = mock_service_instance
        mock_service_instance.mark_as_read.return_value = updated_notification

        # Act
        response = client.patch(f"/api/v1/notifications/{notification_id}/read")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["read"] is True

    @patch('app.api.v1.endpoints.notifications.get_current_user')
    @patch('app.api.v1.endpoints.notifications.NotificationService')
    def test_mark_all_notifications_as_read_success(self, mock_notification_service, mock_get_current_user,
                                                   mock_current_user):
        """Test marquage de toutes les notifications comme lues avec succès."""
        # Arrange
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_notification_service.return_value = mock_service_instance
        mock_service_instance.mark_all_as_read.return_value = {"updated_count": 5}

        # Act
        response = client.patch("/api/v1/notifications/mark-all-read")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 5

    @patch('app.api.v1.endpoints.notifications.get_current_user')
    @patch('app.api.v1.endpoints.notifications.NotificationService')
    def test_get_unread_notifications_count_success(self, mock_notification_service, mock_get_current_user,
                                                   mock_current_user):
        """Test récupération du nombre de notifications non lues avec succès."""
        # Arrange
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_notification_service.return_value = mock_service_instance
        mock_service_instance.get_unread_count.return_value = {"unread_count": 3}

        # Act
        response = client.get("/api/v1/notifications/unread-count")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["unread_count"] == 3

    @patch('app.api.v1.endpoints.notifications.get_current_user')
    @patch('app.api.v1.endpoints.notifications.NotificationService')
    def test_delete_notification_success(self, mock_notification_service, mock_get_current_user,
                                        mock_current_user):
        """Test suppression d'une notification avec succès."""
        # Arrange
        notification_id = 1
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_notification_service.return_value = mock_service_instance
        mock_service_instance.delete_notification.return_value = True

        # Act
        response = client.delete(f"/api/v1/notifications/{notification_id}")

        # Assert
        assert response.status_code == 204

    @patch('app.api.v1.endpoints.notifications.get_current_user')
    @patch('app.api.v1.endpoints.notifications.NotificationService')
    def test_get_notifications_by_type_success(self, mock_notification_service, mock_get_current_user,
                                              mock_current_user, sample_notification):
        """Test récupération des notifications par type avec succès."""
        # Arrange
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_notification_service.return_value = mock_service_instance
        mock_service_instance.get_notifications_by_type.return_value = [sample_notification]

        # Act
        response = client.get("/api/v1/notifications/type/application_received")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["type"] == "application_received"
