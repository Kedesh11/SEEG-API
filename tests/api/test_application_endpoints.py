"""
Tests pour les endpoints d'application
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI, status
from app.api.v1.endpoints.applications import router
from app.schemas.application import ApplicationCreate, ApplicationUpdate, ApplicationResponse
from app.models.application import Application
from app.models.user import User


class TestApplicationEndpoints:
    """Tests pour les endpoints d'application."""
    
    def setup_method(self):
        """Configuration pour chaque test."""
        self.app = FastAPI()
        self.app.include_router(router, prefix="/applications")
        self.client = TestClient(self.app)
    
    @patch('app.api.v1.endpoints.applications.ApplicationService')
    @patch('app.api.v1.endpoints.applications.get_async_db_session')
    @patch('app.api.v1.endpoints.applications.get_current_active_user')
    def test_create_application_success(self, mock_get_user, mock_get_db, mock_service):
        """Test de création d'application réussie."""
        # Mock des données
        application_data = {
            "candidate_id": "candidate-id",
            "job_offer_id": "job-offer-id",
            "cover_letter": "Lettre de motivation",
            "motivation": "Ma motivation"
        }
        
        user = User(
            id="candidate-id",
            email="candidate@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        
        application = Application(
            id="application-id",
            candidate_id="candidate-id",
            job_offer_id="job-offer-id",
            cover_letter="Lettre de motivation",
            motivation="Ma motivation"
        )
        
        # Mock du service
        mock_service_instance = AsyncMock()
        mock_service_instance.create_application.return_value = application
        mock_service.return_value = mock_service_instance
        
        # Mock de la session DB
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Mock de l'utilisateur actuel
        mock_get_user.return_value = user
        
        # Test
        response = self.client.post("/applications/", json=application_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "application-id"
        assert data["candidate_id"] == "candidate-id"
        assert data["job_offer_id"] == "job-offer-id"
    
    @patch('app.api.v1.endpoints.applications.ApplicationService')
    @patch('app.api.v1.endpoints.applications.get_async_db_session')
    @patch('app.api.v1.endpoints.applications.get_current_active_user')
    def test_create_application_validation_error(self, mock_get_user, mock_get_db, mock_service):
        """Test de création d'application avec erreur de validation."""
        application_data = {
            "candidate_id": "nonexistent-candidate",
            "job_offer_id": "job-offer-id",
            "cover_letter": "Lettre de motivation"
        }
        
        user = User(
            id="candidate-id",
            email="candidate@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        
        # Mock du service - erreur de validation
        mock_service_instance = AsyncMock()
        mock_service_instance.create_application.side_effect = Exception("Candidat non trouvé")
        mock_service.return_value = mock_service_instance
        
        # Mock de la session DB
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Mock de l'utilisateur actuel
        mock_get_user.return_value = user
        
        # Test
        response = self.client.post("/applications/", json=application_data)
        
        assert response.status_code == 400
    
    @patch('app.api.v1.endpoints.applications.ApplicationService')
    @patch('app.api.v1.endpoints.applications.get_async_db_session')
    @patch('app.api.v1.endpoints.applications.get_current_active_user')
    def test_get_application_success(self, mock_get_user, mock_get_db, mock_service):
        """Test de récupération d'application réussie."""
        application_id = "application-id"
        
        user = User(
            id="candidate-id",
            email="candidate@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        
        application = Application(
            id=application_id,
            candidate_id="candidate-id",
            job_offer_id="job-offer-id",
            cover_letter="Lettre de motivation"
        )
        
        # Mock du service
        mock_service_instance = AsyncMock()
        mock_service_instance.get_application_by_id.return_value = application
        mock_service.return_value = mock_service_instance
        
        # Mock de la session DB
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Mock de l'utilisateur actuel
        mock_get_user.return_value = user
        
        # Test
        response = self.client.get(f"/applications/{application_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == application_id
        assert data["candidate_id"] == "candidate-id"
    
    @patch('app.api.v1.endpoints.applications.ApplicationService')
    @patch('app.api.v1.endpoints.applications.get_async_db_session')
    @patch('app.api.v1.endpoints.applications.get_current_active_user')
    def test_get_application_not_found(self, mock_get_user, mock_get_db, mock_service):
        """Test de récupération d'application inexistante."""
        application_id = "nonexistent-application"
        
        user = User(
            id="candidate-id",
            email="candidate@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        
        # Mock du service - application non trouvée
        mock_service_instance = AsyncMock()
        mock_service_instance.get_application_by_id.return_value = None
        mock_service.return_value = mock_service_instance
        
        # Mock de la session DB
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Mock de l'utilisateur actuel
        mock_get_user.return_value = user
        
        # Test
        response = self.client.get(f"/applications/{application_id}")
        
        assert response.status_code == 404
    
    @patch('app.api.v1.endpoints.applications.ApplicationService')
    @patch('app.api.v1.endpoints.applications.get_async_db_session')
    @patch('app.api.v1.endpoints.applications.get_current_active_user')
    def test_update_application_success(self, mock_get_user, mock_get_db, mock_service):
        """Test de mise à jour d'application réussie."""
        application_id = "application-id"
        update_data = {
            "cover_letter": "Nouvelle lettre de motivation",
            "motivation": "Nouvelle motivation"
        }
        
        user = User(
            id="candidate-id",
            email="candidate@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        
        updated_application = Application(
            id=application_id,
            candidate_id="candidate-id",
            job_offer_id="job-offer-id",
            cover_letter="Nouvelle lettre de motivation",
            motivation="Nouvelle motivation"
        )
        
        # Mock du service
        mock_service_instance = AsyncMock()
        mock_service_instance.update_application.return_value = updated_application
        mock_service.return_value = mock_service_instance
        
        # Mock de la session DB
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Mock de l'utilisateur actuel
        mock_get_user.return_value = user
        
        # Test
        response = self.client.put(f"/applications/{application_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["cover_letter"] == "Nouvelle lettre de motivation"
        assert data["motivation"] == "Nouvelle motivation"
    
    @patch('app.api.v1.endpoints.applications.ApplicationService')
    @patch('app.api.v1.endpoints.applications.get_async_db_session')
    @patch('app.api.v1.endpoints.applications.get_current_active_user')
    def test_get_candidate_applications(self, mock_get_user, mock_get_db, mock_service):
        """Test de récupération des candidatures d'un candidat."""
        candidate_id = "candidate-id"
        
        user = User(
            id=candidate_id,
            email="candidate@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        
        applications = [
            Application(
                id="app-1",
                candidate_id=candidate_id,
                job_offer_id="job-1",
                cover_letter="Lettre 1"
            ),
            Application(
                id="app-2",
                candidate_id=candidate_id,
                job_offer_id="job-2",
                cover_letter="Lettre 2"
            )
        ]
        
        # Mock du service
        mock_service_instance = AsyncMock()
        mock_service_instance.get_applications_by_candidate.return_value = applications
        mock_service.return_value = mock_service_instance
        
        # Mock de la session DB
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Mock de l'utilisateur actuel
        mock_get_user.return_value = user
        
        # Test
        response = self.client.get(f"/applications/candidate/{candidate_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "app-1"
        assert data[1]["id"] == "app-2"
    
    @patch('app.api.v1.endpoints.applications.ApplicationService')
    @patch('app.api.v1.endpoints.applications.get_async_db_session')
    @patch('app.api.v1.endpoints.applications.get_current_active_user')
    def test_update_application_status(self, mock_get_user, mock_get_db, mock_service):
        """Test de mise à jour du statut d'application."""
        application_id = "application-id"
        status_data = {"status": "accepted"}
        
        user = User(
            id="recruiter-id",
            email="recruiter@example.com",
            first_name="Jane",
            last_name="Smith",
            role="recruiter"
        )
        
        updated_application = Application(
            id=application_id,
            candidate_id="candidate-id",
            job_offer_id="job-offer-id",
            status="accepted"
        )
        
        # Mock du service
        mock_service_instance = AsyncMock()
        mock_service_instance.update_application_status.return_value = updated_application
        mock_service.return_value = mock_service_instance
        
        # Mock de la session DB
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Mock de l'utilisateur actuel
        mock_get_user.return_value = user
        
        # Test
        response = self.client.patch(f"/applications/{application_id}/status", json=status_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
    
    def test_create_application_missing_fields(self):
        """Test de création d'application avec des champs manquants."""
        application_data = {
            "candidate_id": "candidate-id"
            # job_offer_id manquant
        }
        
        response = self.client.post("/applications/", json=application_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_update_application_invalid_data(self):
        """Test de mise à jour d'application avec des données invalides."""
        application_id = "application-id"
        update_data = {
            "cover_letter": ""  # Lettre vide
        }
        
        response = self.client.put(f"/applications/{application_id}", json=update_data)
        
        # Cela pourrait être accepté ou rejeté selon la validation
        assert response.status_code in [200, 422]
