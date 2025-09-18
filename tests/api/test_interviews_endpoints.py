"""
Tests pour les endpoints des entretiens
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from app.main import app
from app.models.interview import InterviewSlot
from app.schemas.interview import InterviewSlotCreate, InterviewSlotUpdate
from app.core.exceptions import NotFoundError, ValidationError
import uuid
from datetime import datetime, timedelta

client = TestClient(app)


class TestInterviewsEndpoints:
    """Tests pour les endpoints des entretiens."""

    @pytest.fixture
    def mock_current_user(self):
        """Mock utilisateur actuel."""
        user = Mock()
        user.id = uuid.uuid4()
        user.role = "recruiter"
        user.email = "recruiter@test.com"
        return user

    @pytest.fixture
    def sample_interview_data(self):
        """Données d'entretien de test."""
        return {
            "application_id": str(uuid.uuid4()),
            "interviewer_id": str(uuid.uuid4()),
            "scheduled_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "duration_minutes": 60,
            "type": "technical",
            "location": "Bureau Paris",
            "notes": "Entretien technique Python"
        }

    @pytest.fixture
    def sample_interview(self):
        """Entretien de test."""
        interview = Mock(spec=InterviewSlot)
        interview.id = uuid.uuid4()
        interview.application_id = uuid.uuid4()
        interview.interviewer_id = uuid.uuid4()
        interview.scheduled_date = datetime.now() + timedelta(days=7)
        interview.duration_minutes = 60
        interview.type = "technical"
        interview.location = "Bureau Paris"
        interview.status = "scheduled"
        interview.notes = "Entretien technique Python"
        interview.created_at = "2024-01-01T00:00:00Z"
        interview.updated_at = "2024-01-01T00:00:00Z"
        return interview

    @patch('app.api.v1.endpoints.interviews.get_current_user')
    @patch('app.api.v1.endpoints.interviews.InterviewService')
    def test_create_interview_success(self, mock_interview_service, mock_get_current_user,
                                     mock_current_user, sample_interview_data, sample_interview):
        """Test création d'entretien avec succès."""
        # Arrange
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_interview_service.return_value = mock_service_instance
        mock_service_instance.create_interview_slot.return_value = sample_interview

        # Act
        response = client.post("/api/v1/interviews/", json=sample_interview_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == sample_interview_data["type"]
        assert data["duration_minutes"] == sample_interview_data["duration_minutes"]
        mock_service_instance.create_interview_slot.assert_called_once()

    @patch('app.api.v1.endpoints.interviews.get_current_user')
    @patch('app.api.v1.endpoints.interviews.InterviewService')
    def test_get_interviews_success(self, mock_interview_service, mock_get_current_user,
                                   mock_current_user, sample_interview):
        """Test récupération des entretiens avec succès."""
        # Arrange
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_interview_service.return_value = mock_service_instance
        mock_service_instance.get_interview_slots.return_value = [sample_interview]

        # Act
        response = client.get("/api/v1/interviews/")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["type"] == sample_interview.type

    @patch('app.api.v1.endpoints.interviews.get_current_user')
    @patch('app.api.v1.endpoints.interviews.InterviewService')
    def test_get_interview_by_id_success(self, mock_interview_service, mock_get_current_user,
                                        mock_current_user, sample_interview):
        """Test récupération d'un entretien par ID avec succès."""
        # Arrange
        interview_id = str(sample_interview.id)
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_interview_service.return_value = mock_service_instance
        mock_service_instance.get_interview_slot_by_id.return_value = sample_interview

        # Act
        response = client.get(f"/api/v1/interviews/{interview_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == interview_id
        assert data["type"] == sample_interview.type

    @patch('app.api.v1.endpoints.interviews.get_current_user')
    @patch('app.api.v1.endpoints.interviews.InterviewService')
    def test_update_interview_success(self, mock_interview_service, mock_get_current_user,
                                     mock_current_user, sample_interview):
        """Test mise à jour d'entretien avec succès."""
        # Arrange
        interview_id = str(sample_interview.id)
        update_data = {"status": "completed", "notes": "Entretien terminé avec succès"}
        updated_interview = Mock(spec=InterviewSlot)
        updated_interview.id = sample_interview.id
        updated_interview.status = "completed"
        updated_interview.notes = "Entretien terminé avec succès"
        
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_interview_service.return_value = mock_service_instance
        mock_service_instance.update_interview_slot.return_value = updated_interview

        # Act
        response = client.put(f"/api/v1/interviews/{interview_id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["notes"] == "Entretien terminé avec succès"

    @patch('app.api.v1.endpoints.interviews.get_current_user')
    @patch('app.api.v1.endpoints.interviews.InterviewService')
    def test_get_interviews_by_application_success(self, mock_interview_service, mock_get_current_user,
                                                  mock_current_user, sample_interview):
        """Test récupération des entretiens par candidature avec succès."""
        # Arrange
        application_id = str(uuid.uuid4())
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_interview_service.return_value = mock_service_instance
        mock_service_instance.get_interviews_by_application.return_value = [sample_interview]

        # Act
        response = client.get(f"/api/v1/interviews/application/{application_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    @patch('app.api.v1.endpoints.interviews.get_current_user')
    @patch('app.api.v1.endpoints.interviews.InterviewService')
    def test_get_interviews_by_interviewer_success(self, mock_interview_service, mock_get_current_user,
                                                  mock_current_user, sample_interview):
        """Test récupération des entretiens par intervieweur avec succès."""
        # Arrange
        interviewer_id = str(uuid.uuid4())
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_interview_service.return_value = mock_service_instance
        mock_service_instance.get_interviews_by_interviewer.return_value = [sample_interview]

        # Act
        response = client.get(f"/api/v1/interviews/interviewer/{interviewer_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    @patch('app.api.v1.endpoints.interviews.get_current_user')
    @patch('app.api.v1.endpoints.interviews.InterviewService')
    def test_get_interview_calendar_success(self, mock_interview_service, mock_get_current_user,
                                           mock_current_user, sample_interview):
        """Test récupération du calendrier d'entretiens avec succès."""
        # Arrange
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_interview_service.return_value = mock_service_instance
        mock_service_instance.get_interview_calendar.return_value = [sample_interview]

        # Act
        response = client.get("/api/v1/interviews/calendar?month=2024-01")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
