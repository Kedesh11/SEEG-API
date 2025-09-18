"""
Tests pour les endpoints des offres d'emploi
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.models.job_offer import JobOffer
from app.models.user import User
from app.schemas.job import JobOfferCreate, JobOfferUpdate
from app.core.exceptions import NotFoundError, ValidationError
import uuid

client = TestClient(app)


class TestJobsEndpoints:
    """Tests pour les endpoints des offres d'emploi."""

    @pytest.fixture
    def mock_current_user(self):
        """Mock utilisateur actuel."""
        user = Mock(spec=User)
        user.id = uuid.uuid4()
        user.role = "recruiter"
        user.email = "recruiter@test.com"
        return user

    @pytest.fixture
    def sample_job_offer_data(self):
        """Données d'offre d'emploi de test."""
        return {
            "title": "Développeur Python Senior",
            "description": "Développement d'applications Python avancées",
            "location": "Paris",
            "contract_type": "CDI",
            "department": "IT",
            "salary_min": 50000,
            "salary_max": 70000,
            "requirements": ["Python", "Django", "PostgreSQL", "Docker"],
            "benefits": ["Mutuelle", "Tickets restaurant", "Télétravail"],
            "responsibilities": ["Développement", "Architecture", "Mentoring"]
        }

    @pytest.fixture
    def sample_job_offer(self):
        """Offre d'emploi de test."""
        job = Mock(spec=JobOffer)
        job.id = uuid.uuid4()
        job.title = "Développeur Python Senior"
        job.description = "Développement d'applications Python avancées"
        job.location = "Paris"
        job.contract_type = "CDI"
        job.department = "IT"
        job.salary_min = 50000
        job.salary_max = 70000
        job.requirements = ["Python", "Django", "PostgreSQL"]
        job.benefits = ["Mutuelle", "Tickets restaurant"]
        job.responsibilities = ["Développement", "Architecture"]
        job.status = "active"
        job.recruiter_id = uuid.uuid4()
        job.created_at = "2024-01-01T00:00:00Z"
        job.updated_at = "2024-01-01T00:00:00Z"
        return job

    @patch('app.api.v1.endpoints.jobs.get_current_user')
    @patch('app.api.v1.endpoints.jobs.JobService')
    def test_create_job_offer_success(self, mock_job_service, mock_get_current_user, 
                                     mock_current_user, sample_job_offer_data, sample_job_offer):
        """Test création d'offre d'emploi avec succès."""
        # Arrange
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_job_service.return_value = mock_service_instance
        mock_service_instance.create_job_offer.return_value = sample_job_offer

        # Act
        response = client.post("/api/v1/jobs/", json=sample_job_offer_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == sample_job_offer_data["title"]
        assert data["description"] == sample_job_offer_data["description"]
        assert data["location"] == sample_job_offer_data["location"]
        mock_service_instance.create_job_offer.assert_called_once()

    @patch('app.api.v1.endpoints.jobs.get_current_user')
    def test_create_job_offer_unauthorized(self, mock_get_current_user):
        """Test création d'offre d'emploi sans autorisation."""
        # Arrange
        mock_get_current_user.side_effect = Exception("Unauthorized")

        # Act
        response = client.post("/api/v1/jobs/", json={})

        # Assert
        assert response.status_code == 401

    @patch('app.api.v1.endpoints.jobs.get_current_user')
    @patch('app.api.v1.endpoints.jobs.JobService')
    def test_get_job_offers_success(self, mock_job_service, mock_get_current_user, 
                                   mock_current_user, sample_job_offer):
        """Test récupération des offres d'emploi avec succès."""
        # Arrange
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_job_service.return_value = mock_service_instance
        mock_service_instance.get_job_offers.return_value = [sample_job_offer]

        # Act
        response = client.get("/api/v1/jobs/")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == sample_job_offer.title

    @patch('app.api.v1.endpoints.jobs.get_current_user')
    @patch('app.api.v1.endpoints.jobs.JobService')
    def test_get_job_offer_by_id_success(self, mock_job_service, mock_get_current_user,
                                        mock_current_user, sample_job_offer):
        """Test récupération d'une offre d'emploi par ID avec succès."""
        # Arrange
        job_id = str(sample_job_offer.id)
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_job_service.return_value = mock_service_instance
        mock_service_instance.get_job_offer_by_id.return_value = sample_job_offer

        # Act
        response = client.get(f"/api/v1/jobs/{job_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_id
        assert data["title"] == sample_job_offer.title

    @patch('app.api.v1.endpoints.jobs.get_current_user')
    @patch('app.api.v1.endpoints.jobs.JobService')
    def test_get_job_offer_by_id_not_found(self, mock_job_service, mock_get_current_user,
                                          mock_current_user):
        """Test récupération d'une offre d'emploi inexistante."""
        # Arrange
        job_id = str(uuid.uuid4())
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_job_service.return_value = mock_service_instance
        mock_service_instance.get_job_offer_by_id.side_effect = NotFoundError("Offre non trouvée")

        # Act
        response = client.get(f"/api/v1/jobs/{job_id}")

        # Assert
        assert response.status_code == 404

    @patch('app.api.v1.endpoints.jobs.get_current_user')
    @patch('app.api.v1.endpoints.jobs.JobService')
    def test_update_job_offer_success(self, mock_job_service, mock_get_current_user,
                                     mock_current_user, sample_job_offer):
        """Test mise à jour d'offre d'emploi avec succès."""
        # Arrange
        job_id = str(sample_job_offer.id)
        update_data = {"title": "Développeur Python Lead"}
        updated_job = Mock(spec=JobOffer)
        updated_job.id = sample_job_offer.id
        updated_job.title = "Développeur Python Lead"
        updated_job.description = sample_job_offer.description
        
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_job_service.return_value = mock_service_instance
        mock_service_instance.update_job_offer.return_value = updated_job

        # Act
        response = client.put(f"/api/v1/jobs/{job_id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Développeur Python Lead"

    @patch('app.api.v1.endpoints.jobs.get_current_user')
    @patch('app.api.v1.endpoints.jobs.JobService')
    def test_delete_job_offer_success(self, mock_job_service, mock_get_current_user,
                                     mock_current_user):
        """Test suppression d'offre d'emploi avec succès."""
        # Arrange
        job_id = str(uuid.uuid4())
        mock_get_current_user.return_value = mock_current_user
        mock_service_instance = AsyncMock()
        mock_job_service.return_value = mock_service_instance
        mock_service_instance.delete_job_offer.return_value = True

        # Act
        response = client.delete(f"/api/v1/jobs/{job_id}")

        # Assert
        assert response.status_code == 204
