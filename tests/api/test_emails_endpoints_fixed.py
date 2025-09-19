"""
Tests pour les endpoints d'emails (Version corrigée)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI, status
from app.api.v1.endpoints.emails import router
from app.schemas.email import EmailSend, InterviewEmailRequest, EmailResponse
from app.models.user import User
from app.core.exceptions import EmailError


class TestEmailsEndpoints:
    """Tests pour les endpoints d'emails."""
    
    def setup_method(self):
        """Configuration pour chaque test."""
        self.app = FastAPI()
        self.app.include_router(router, prefix="/emails")
        self.client = TestClient(self.app)
        
        # Mock user pour l'authentification
        self.mock_user = User(
            id="user-id",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role="recruiter"
        )
    
    def _mock_auth_dependency(self):
        """Mock de la dépendance d'authentification"""
        return self.mock_user
    
    @patch('app.api.v1.endpoints.emails.EmailService')
    @patch('app.api.v1.endpoints.emails.get_async_db')
    def test_send_email_success(self, mock_get_db, mock_email_service):
        """Test d'envoi d'email réussi."""
        # Mock des données
        email_data = {
            "to": "recipient@example.com",
            "subject": "Test Subject",
            "body": "Test body content",
            "html_body": "<p>Test HTML content</p>"
        }
        
        # Mock du service
        mock_service_instance = AsyncMock()
        mock_service_instance.send_email.return_value = True
        mock_email_service.return_value = mock_service_instance
        
        # Mock de l'authentification
        with patch('app.api.v1.endpoints.emails.get_current_user', return_value=self.mock_user):
            # Appel de l'endpoint
            response = self.client.post("/emails/send", json=email_data)
        
        # Vérifications
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "Email envoyé avec succès" in data["message"]
        
        # Vérifier que le service a été appelé
        mock_service_instance.send_email.assert_called_once()
    
    @patch('app.api.v1.endpoints.emails.EmailService')
    @patch('app.api.v1.endpoints.emails.get_async_db')
    def test_send_email_failure(self, mock_get_db, mock_email_service):
        """Test d'échec d'envoi d'email."""
        # Mock des données
        email_data = {
            "to": "recipient@example.com",
            "subject": "Test Subject",
            "body": "Test body content"
        }
        
        # Mock du service pour échouer
        mock_service_instance = AsyncMock()
        mock_service_instance.send_email.side_effect = EmailError("SMTP Error")
        mock_email_service.return_value = mock_service_instance
        
        # Mock de l'authentification
        with patch('app.api.v1.endpoints.emails.get_current_user', return_value=self.mock_user):
            # Appel de l'endpoint
            response = self.client.post("/emails/send", json=email_data)
        
        # Vérifications
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Erreur lors de l'envoi de l'email" in data["detail"]
    
    @patch('app.api.v1.endpoints.emails.EmailService')
    @patch('app.api.v1.endpoints.emails.get_async_db')
    def test_send_interview_email_success(self, mock_get_db, mock_email_service):
        """Test d'envoi d'email d'entretien réussi."""
        # Mock des données
        interview_data = {
            "to": "candidate@example.com",
            "candidate_full_name": "Jean Dupont",
            "job_title": "Développeur Full Stack",
            "date": "2024-12-25",
            "time": "14:30",
            "location": "Salle de réunion, 9ème étage",
            "application_id": "app-123",
            "additional_notes": "Apporter votre CV"
        }
        
        # Mock du service
        mock_service_instance = AsyncMock()
        mock_service_instance.send_email.return_value = True
        mock_email_service.return_value = mock_service_instance
        
        # Mock de l'authentification
        with patch('app.api.v1.endpoints.emails.get_current_user', return_value=self.mock_user):
            # Appel de l'endpoint
            response = self.client.post("/emails/send-interview-email", json=interview_data)
        
        # Vérifications
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "Email d'entretien envoyé avec succès" in data["message"]
        
        # Vérifier que le service a été appelé avec les bons paramètres
        mock_service_instance.send_email.assert_called_once()
        call_args = mock_service_instance.send_email.call_args
        assert call_args[1]["to"] == "candidate@example.com"
        assert "Convocation à l'entretien" in call_args[1]["subject"]
        assert "Jean Dupont" in call_args[1]["body"]
        assert "Développeur Full Stack" in call_args[1]["body"]
    
    def test_send_interview_email_invalid_date(self):
        """Test d'envoi d'email d'entretien avec date invalide."""
        # Mock des données avec date invalide
        interview_data = {
            "to": "candidate@example.com",
            "candidate_full_name": "Jean Dupont",
            "job_title": "Développeur Full Stack",
            "date": "invalid-date",
            "time": "14:30"
        }
        
        # Mock de l'authentification
        with patch('app.api.v1.endpoints.emails.get_current_user', return_value=self.mock_user):
            # Appel de l'endpoint
            response = self.client.post("/emails/send-interview-email", json=interview_data)
        
        # Vérifications
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_send_interview_email_invalid_time(self):
        """Test d'envoi d'email d'entretien avec heure invalide."""
        # Mock des données avec heure invalide
        interview_data = {
            "to": "candidate@example.com",
            "candidate_full_name": "Jean Dupont",
            "job_title": "Développeur Full Stack",
            "date": "2024-12-25",
            "time": "25:70"  # Heure invalide
        }
        
        # Mock de l'authentification
        with patch('app.api.v1.endpoints.emails.get_current_user', return_value=self.mock_user):
            # Appel de l'endpoint
            response = self.client.post("/emails/send-interview-email", json=interview_data)
        
        # Vérifications
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch('app.api.v1.endpoints.emails.EmailService')
    @patch('app.api.v1.endpoints.emails.get_async_db')
    def test_get_email_logs_success(self, mock_get_db, mock_email_service):
        """Test de récupération des logs d'emails."""
        # Mock des données de logs
        mock_logs_data = {
            "items": [
                {
                    "id": "log-1",
                    "recipient_email": "test@example.com",
                    "subject": "Test Subject",
                    "status": "sent",
                    "sent_at": "2024-01-01T10:00:00Z",
                    "error_message": None
                }
            ],
            "total": 1,
            "skip": 0,
            "limit": 100,
            "has_more": False
        }
        
        # Mock du service
        mock_service_instance = AsyncMock()
        mock_service_instance.get_email_logs.return_value = mock_logs_data
        mock_email_service.return_value = mock_service_instance
        
        # Mock de l'authentification
        with patch('app.api.v1.endpoints.emails.get_current_user', return_value=self.mock_user):
            # Appel de l'endpoint
            response = self.client.get("/emails/logs")
        
        # Vérifications
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["recipient_email"] == "test@example.com"
        assert data["total"] == 1
    
    @patch('app.api.v1.endpoints.emails.EmailService')
    @patch('app.api.v1.endpoints.emails.get_async_db')
    def test_get_email_logs_with_filters(self, mock_get_db, mock_email_service):
        """Test de récupération des logs d'emails avec filtres."""
        # Mock des données de logs
        mock_logs_data = {
            "items": [],
            "total": 0,
            "skip": 0,
            "limit": 10,
            "has_more": False
        }
        
        # Mock du service
        mock_service_instance = AsyncMock()
        mock_service_instance.get_email_logs.return_value = mock_logs_data
        mock_email_service.return_value = mock_service_instance
        
        # Mock de l'authentification
        with patch('app.api.v1.endpoints.emails.get_current_user', return_value=self.mock_user):
            # Appel de l'endpoint avec filtres
            response = self.client.get("/emails/logs?skip=0&limit=10&status_filter=sent")
        
        # Vérifications
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["total"] == 0
        
        # Vérifier que le service a été appelé avec les bons paramètres
        mock_service_instance.get_email_logs.assert_called_once_with(
            skip=0, limit=10, status="sent"
        )
    
    def test_send_email_unauthorized(self):
        """Test d'envoi d'email sans authentification."""
        email_data = {
            "to": "recipient@example.com",
            "subject": "Test Subject",
            "body": "Test body content"
        }
        
        # Appel de l'endpoint sans authentification
        response = self.client.post("/emails/send", json=email_data)
        
        # Vérifications
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_send_interview_email_unauthorized(self):
        """Test d'envoi d'email d'entretien sans authentification."""
        interview_data = {
            "to": "candidate@example.com",
            "candidate_full_name": "Jean Dupont",
            "job_title": "Développeur Full Stack",
            "date": "2024-12-25",
            "time": "14:30"
        }
        
        # Appel de l'endpoint sans authentification
        response = self.client.post("/emails/send-interview-email", json=interview_data)
        
        # Vérifications
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_email_logs_unauthorized(self):
        """Test de récupération des logs sans authentification."""
        # Appel de l'endpoint sans authentification
        response = self.client.get("/emails/logs")
        
        # Vérifications
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
