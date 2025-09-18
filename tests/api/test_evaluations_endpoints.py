"""
Tests pour les endpoints des évaluations
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from app.main import app
from app.models.evaluation import Protocol1Evaluation, Protocol2Evaluation
from app.schemas.evaluation import Protocol1EvaluationCreate, Protocol2EvaluationCreate
from app.core.exceptions import NotFoundError, ValidationError
import uuid

client = TestClient(app)


class TestEvaluationsEndpoints:
    """Tests pour les endpoints des évaluations."""

    @pytest.fixture
    def mock_current_user(self):
        """Mock utilisateur actuel."""
        user = Mock()
        user.id = uuid.uuid4()
        user.role = "recruiter"
        user.email = "recruiter@test.com"
        return user

    @pytest.fixture
    def sample_protocol1_evaluation_data(self):
        """Données d'évaluation protocole 1 de test."""
        return {
            "application_id": str(uuid.uuid4()),
            "evaluator_id": str(uuid.uuid4()),
            "documentary_score": 85,
            "mtp_score": 90,
            "interview_score": 88,
            "overall_score": 87.5,
            "status": "completed",
            "comments": "Excellente candidature"
        }

    @pytest.fixture
    def sample_protocol1_evaluation(self):
        """Évaluation protocole 1 de test."""
        evaluation = Mock(spec=Protocol1Evaluation)
        evaluation.id = uuid.uuid4()
        evaluation.application_id = uuid.uuid4()
        evaluation.evaluator_id = uuid.uuid4()
        evaluation.documentary_score = 85
        evaluation.mtp_score = 90
        evaluation.interview_score = 88
        evaluation.overall_score = 87.5
        evaluation.status = "completed"
        evaluation.comments = "Excellente candidature"
        evaluation.created_at = "2024-01-01T00:00:00Z"
        evaluation.updated_at = "2024-01-01T00:00:00Z"
        return evaluation

    @patch('app.api.v1.endpoints.evaluations.get_current_user')
    @patch('app.api.v1.endpoints.evaluations.EvaluationService')
    def test_create_protocol1_evaluation_success(self, mock_evaluation_service, mock_get_current_user,
                                                mock_current_user, sample_protocol1_evaluation_data,
                                                sample_protocol1_evaluation):
        """Test création d'évaluation protocole 1 avec succès."""
        # Arrange
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_evaluation_service.return_value = mock_service_instance
        mock_service_instance.create_protocol1_evaluation.return_value = sample_protocol1_evaluation

        # Act
        response = client.post("/api/v1/evaluations/protocol1/", json=sample_protocol1_evaluation_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["documentary_score"] == sample_protocol1_evaluation_data["documentary_score"]
        assert data["overall_score"] == sample_protocol1_evaluation_data["overall_score"]
        mock_service_instance.create_protocol1_evaluation.assert_called_once()

    @patch('app.api.v1.endpoints.evaluations.get_current_user')
    @patch('app.api.v1.endpoints.evaluations.EvaluationService')
    def test_get_protocol1_evaluations_success(self, mock_evaluation_service, mock_get_current_user,
                                              mock_current_user, sample_protocol1_evaluation):
        """Test récupération des évaluations protocole 1 avec succès."""
        # Arrange
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_evaluation_service.return_value = mock_service_instance
        mock_service_instance.get_protocol1_evaluations.return_value = [sample_protocol1_evaluation]

        # Act
        response = client.get("/api/v1/evaluations/protocol1/")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["documentary_score"] == sample_protocol1_evaluation.documentary_score

    @patch('app.api.v1.endpoints.evaluations.get_current_user')
    @patch('app.api.v1.endpoints.evaluations.EvaluationService')
    def test_get_protocol1_evaluation_by_id_success(self, mock_evaluation_service, mock_get_current_user,
                                                   mock_current_user, sample_protocol1_evaluation):
        """Test récupération d'une évaluation protocole 1 par ID avec succès."""
        # Arrange
        evaluation_id = str(sample_protocol1_evaluation.id)
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_evaluation_service.return_value = mock_service_instance
        mock_service_instance.get_protocol1_evaluation_by_id.return_value = sample_protocol1_evaluation

        # Act
        response = client.get(f"/api/v1/evaluations/protocol1/{evaluation_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == evaluation_id
        assert data["documentary_score"] == sample_protocol1_evaluation.documentary_score

    @patch('app.api.v1.endpoints.evaluations.get_current_user')
    @patch('app.api.v1.endpoints.evaluations.EvaluationService')
    def test_update_protocol1_evaluation_success(self, mock_evaluation_service, mock_get_current_user,
                                                mock_current_user, sample_protocol1_evaluation):
        """Test mise à jour d'évaluation protocole 1 avec succès."""
        # Arrange
        evaluation_id = str(sample_protocol1_evaluation.id)
        update_data = {"documentary_score": 90, "overall_score": 89.0}
        updated_evaluation = Mock(spec=Protocol1Evaluation)
        updated_evaluation.id = sample_protocol1_evaluation.id
        updated_evaluation.documentary_score = 90
        updated_evaluation.overall_score = 89.0
        
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_evaluation_service.return_value = mock_service_instance
        mock_service_instance.update_protocol1_evaluation.return_value = updated_evaluation

        # Act
        response = client.put(f"/api/v1/evaluations/protocol1/{evaluation_id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["documentary_score"] == 90
        assert data["overall_score"] == 89.0

    @patch('app.api.v1.endpoints.evaluations.get_current_user')
    @patch('app.api.v1.endpoints.evaluations.EvaluationService')
    def test_get_evaluation_statistics_success(self, mock_evaluation_service, mock_get_current_user,
                                              mock_current_user):
        """Test récupération des statistiques d'évaluations avec succès."""
        # Arrange
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_evaluation_service.return_value = mock_service_instance
        mock_service_instance.get_evaluation_statistics.return_value = {
            "total_evaluations": 50,
            "completed_evaluations": 45,
            "pending_evaluations": 5,
            "average_score": 82.5
        }

        # Act
        response = client.get("/api/v1/evaluations/statistics")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_evaluations"] == 50
        assert data["average_score"] == 82.5

    @patch('app.api.v1.endpoints.evaluations.get_current_user')
    @patch('app.api.v1.endpoints.evaluations.EvaluationService')
    def test_get_evaluations_by_application_success(self, mock_evaluation_service, mock_get_current_user,
                                                   mock_current_user, sample_protocol1_evaluation):
        """Test récupération des évaluations par candidature avec succès."""
        # Arrange
        application_id = str(uuid.uuid4())
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_evaluation_service.return_value = mock_service_instance
        mock_service_instance.get_evaluations_by_application.return_value = [sample_protocol1_evaluation]

        # Act
        response = client.get(f"/api/v1/evaluations/application/{application_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
