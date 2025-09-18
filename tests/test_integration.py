"""
Tests d'intégration end-to-end
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from app.main import app
from app.models.user import User
from app.models.job_offer import JobOffer
from app.models.application import Application
from app.core.exceptions import NotFoundError, ValidationError
import uuid
import json

client = TestClient(app)


class TestIntegration:
    """Tests d'intégration end-to-end."""

    @pytest.fixture
    def mock_current_user(self):
        """Mock utilisateur actuel."""
        user = Mock(spec=User)
        user.id = uuid.uuid4()
        user.role = "candidate"
        user.email = "candidate@test.com"
        user.first_name = "John"
        user.last_name = "Doe"
        return user

    @pytest.fixture
    def mock_recruiter_user(self):
        """Mock utilisateur recruteur."""
        user = Mock(spec=User)
        user.id = uuid.uuid4()
        user.role = "recruiter"
        user.email = "recruiter@test.com"
        user.first_name = "Jane"
        user.last_name = "Smith"
        return user

    @pytest.fixture
    def sample_job_offer(self):
        """Offre d'emploi de test."""
        job = Mock(spec=JobOffer)
        job.id = uuid.uuid4()
        job.title = "Développeur Python"
        job.description = "Développement d'applications Python"
        job.location = "Paris"
        job.contract_type = "CDI"
        job.department = "IT"
        job.salary_min = 40000
        job.salary_max = 60000
        job.requirements = ["Python", "Django"]
        job.benefits = ["Mutuelle", "Tickets restaurant"]
        job.responsibilities = ["Développement", "Tests"]
        job.status = "active"
        job.recruiter_id = uuid.uuid4()
        return job

    @pytest.fixture
    def sample_application(self):
        """Candidature de test."""
        application = Mock(spec=Application)
        application.id = uuid.uuid4()
        application.candidate_id = uuid.uuid4()
        application.job_offer_id = uuid.uuid4()
        application.cover_letter = "Lettre de motivation"
        application.motivation = "Ma motivation"
        application.status = "submitted"
        application.created_at = "2024-01-01T00:00:00Z"
        return application

    @patch('app.api.v1.endpoints.auth.get_current_user')
    @patch('app.api.v1.endpoints.jobs.get_current_user')
    @patch('app.api.v1.endpoints.applications.get_current_user')
    def test_complete_application_workflow(self, mock_app_get_user, mock_job_get_user, 
                                         mock_auth_get_user, mock_current_user, 
                                         mock_recruiter_user, sample_job_offer, sample_application):
        """Test du workflow complet de candidature."""
        # Arrange
        mock_auth_get_user.return_value = mock_current_user
        mock_job_get_user.return_value = mock_current_user
        mock_app_get_user.return_value = mock_current_user

        # Mock des services
        with patch('app.api.v1.endpoints.jobs.JobService') as mock_job_service, \
             patch('app.api.v1.endpoints.applications.ApplicationService') as mock_app_service:
            
            # Configuration des mocks
            mock_job_service_instance = AsyncMock()
            mock_job_service.return_value = mock_job_service_instance
            mock_job_service_instance.get_job_offers.return_value = [sample_job_offer]
            mock_job_service_instance.get_job_offer_by_id.return_value = sample_job_offer

            mock_app_service_instance = AsyncMock()
            mock_app_service.return_value = mock_app_service_instance
            mock_app_service_instance.create_application.return_value = sample_application
            mock_app_service_instance.get_applications_by_candidate.return_value = [sample_application]

            # 1. Récupérer les offres d'emploi disponibles
            response = client.get("/api/v1/jobs/")
            assert response.status_code == 200
            jobs = response.json()
            assert len(jobs) == 1
            job_id = jobs[0]["id"]

            # 2. Récupérer les détails d'une offre
            response = client.get(f"/api/v1/jobs/{job_id}")
            assert response.status_code == 200
            job_details = response.json()
            assert job_details["title"] == sample_job_offer.title

            # 3. Créer une candidature
            application_data = {
                "job_offer_id": job_id,
                "cover_letter": "Lettre de motivation pour ce poste",
                "motivation": "Je suis très motivé pour ce poste",
                "reference_contacts": "Contact 1, Contact 2"
            }
            response = client.post("/api/v1/applications/", json=application_data)
            assert response.status_code == 201
            application = response.json()
            assert application["cover_letter"] == application_data["cover_letter"]

            # 4. Récupérer les candidatures du candidat
            response = client.get("/api/v1/applications/my-applications")
            assert response.status_code == 200
            applications = response.json()
            assert len(applications) == 1

    @patch('app.api.v1.endpoints.auth.get_current_user')
    @patch('app.api.v1.endpoints.jobs.get_current_user')
    def test_recruiter_job_management_workflow(self, mock_job_get_user, mock_auth_get_user,
                                             mock_recruiter_user, sample_job_offer):
        """Test du workflow de gestion des offres d'emploi par le recruteur."""
        # Arrange
        mock_auth_get_user.return_value = mock_recruiter_user
        mock_job_get_user.return_value = mock_recruiter_user

        with patch('app.api.v1.endpoints.jobs.JobService') as mock_job_service:
            mock_job_service_instance = AsyncMock()
            mock_job_service.return_value = mock_job_service_instance
            mock_job_service_instance.create_job_offer.return_value = sample_job_offer
            mock_job_service_instance.get_job_offers_by_recruiter.return_value = [sample_job_offer]
            mock_job_service_instance.update_job_offer.return_value = sample_job_offer
            mock_job_service_instance.delete_job_offer.return_value = True

            # 1. Créer une nouvelle offre d'emploi
            job_data = {
                "title": "Développeur Python Senior",
                "description": "Développement d'applications Python avancées",
                "location": "Paris",
                "contract_type": "CDI",
                "department": "IT",
                "salary_min": 50000,
                "salary_max": 70000,
                "requirements": ["Python", "Django", "PostgreSQL"],
                "benefits": ["Mutuelle", "Tickets restaurant"],
                "responsibilities": ["Développement", "Architecture"]
            }
            response = client.post("/api/v1/jobs/", json=job_data)
            assert response.status_code == 201
            created_job = response.json()
            assert created_job["title"] == job_data["title"]

            # 2. Récupérer les offres du recruteur
            response = client.get("/api/v1/jobs/my-offers")
            assert response.status_code == 200
            jobs = response.json()
            assert len(jobs) == 1

            # 3. Mettre à jour l'offre
            job_id = created_job["id"]
            update_data = {"title": "Développeur Python Lead"}
            response = client.put(f"/api/v1/jobs/{job_id}", json=update_data)
            assert response.status_code == 200
            updated_job = response.json()
            assert updated_job["title"] == "Développeur Python Lead"

            # 4. Supprimer l'offre
            response = client.delete(f"/api/v1/jobs/{job_id}")
            assert response.status_code == 204

    @patch('app.api.v1.endpoints.auth.get_current_user')
    @patch('app.api.v1.endpoints.evaluations.get_current_user')
    def test_evaluation_workflow(self, mock_eval_get_user, mock_auth_get_user,
                                mock_recruiter_user):
        """Test du workflow d'évaluation."""
        # Arrange
        mock_auth_get_user.return_value = mock_recruiter_user
        mock_eval_get_user.return_value = mock_recruiter_user

        with patch('app.api.v1.endpoints.evaluations.EvaluationService') as mock_eval_service:
            mock_eval_service_instance = AsyncMock()
            mock_eval_service.return_value = mock_eval_service_instance
            
            # Mock des données d'évaluation
            evaluation_data = {
                "application_id": str(uuid.uuid4()),
                "documentary_score": 85,
                "mtp_score": 90,
                "interview_score": 88,
                "overall_score": 87.5,
                "status": "completed",
                "comments": "Excellente candidature"
            }
            
            mock_eval_service_instance.create_protocol1_evaluation.return_value = evaluation_data
            mock_eval_service_instance.get_protocol1_evaluations.return_value = [evaluation_data]

            # 1. Créer une évaluation
            response = client.post("/api/v1/evaluations/protocol1/", json=evaluation_data)
            assert response.status_code == 201
            evaluation = response.json()
            assert evaluation["documentary_score"] == evaluation_data["documentary_score"]

            # 2. Récupérer les évaluations
            response = client.get("/api/v1/evaluations/protocol1/")
            assert response.status_code == 200
            evaluations = response.json()
            assert len(evaluations) == 1

    @patch('app.api.v1.endpoints.auth.get_current_user')
    @patch('app.api.v1.endpoints.notifications.get_current_user')
    def test_notification_workflow(self, mock_notif_get_user, mock_auth_get_user,
                                  mock_current_user):
        """Test du workflow de notifications."""
        # Arrange
        mock_auth_get_user.return_value = mock_current_user
        mock_notif_get_user.return_value = mock_current_user

        with patch('app.api.v1.endpoints.notifications.NotificationService') as mock_notif_service:
            mock_notif_service_instance = AsyncMock()
            mock_notif_service.return_value = mock_notif_service_instance
            
            # Mock des données de notification
            notification_data = {
                "title": "Nouvelle candidature",
                "message": "Votre candidature a été reçue",
                "type": "application_received"
            }
            
            mock_notif_service_instance.get_user_notifications.return_value = [notification_data]
            mock_notif_service_instance.get_unread_count.return_value = {"unread_count": 1}
            mock_notif_service_instance.mark_as_read.return_value = {**notification_data, "read": True}

            # 1. Récupérer les notifications
            response = client.get("/api/v1/notifications/")
            assert response.status_code == 200
            notifications = response.json()
            assert len(notifications) == 1

            # 2. Récupérer le nombre de notifications non lues
            response = client.get("/api/v1/notifications/unread-count")
            assert response.status_code == 200
            unread_data = response.json()
            assert unread_data["unread_count"] == 1

            # 3. Marquer une notification comme lue
            notification_id = 1
            response = client.patch(f"/api/v1/notifications/{notification_id}/read")
            assert response.status_code == 200
            updated_notification = response.json()
            assert updated_notification["read"] is True

    def test_error_handling_workflow(self):
        """Test de la gestion d'erreurs dans le workflow."""
        # Test avec des endpoints non authentifiés
        response = client.get("/api/v1/jobs/")
        assert response.status_code == 401

        response = client.post("/api/v1/applications/", json={})
        assert response.status_code == 401

        # Test avec des données invalides
        with patch('app.api.v1.endpoints.jobs.get_current_user') as mock_get_user:
            mock_user = Mock()
            mock_user.id = uuid.uuid4()
            mock_user.role = "recruiter"
            mock_get_user.return_value = mock_user

            with patch('app.api.v1.endpoints.jobs.JobService') as mock_job_service:
                mock_job_service_instance = AsyncMock()
                mock_job_service.return_value = mock_job_service_instance
                mock_job_service_instance.create_job_offer.side_effect = ValidationError("Données invalides")

                response = client.post("/api/v1/jobs/", json={"title": ""})
                assert response.status_code == 400

    def test_api_documentation_accessibility(self):
        """Test de l'accessibilité de la documentation API."""
        # Test de l'accès à la documentation Swagger
        response = client.get("/docs")
        assert response.status_code == 200

        # Test de l'accès à la documentation ReDoc
        response = client.get("/redoc")
        assert response.status_code == 200

        # Test de l'accès au schéma OpenAPI
        response = client.get("/openapi.json")
        assert response.status_code == 200
        openapi_schema = response.json()
        assert "openapi" in openapi_schema
        assert "info" in openapi_schema
        assert "paths" in openapi_schema
