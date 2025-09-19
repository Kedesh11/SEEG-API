"""
Tests pour le service email
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from app.services.email import EmailService
from app.models.email import EmailLog
from app.core.exceptions import EmailError


class TestEmailService:
    """Tests pour le service email."""
    
    def setup_method(self):
        """Configuration pour chaque test."""
        self.mock_db = AsyncMock()
        self.email_service = EmailService(self.mock_db)
    
    @patch('app.services.email.FastMail')
    def test_setup_fastmail_success(self, mock_fastmail):
        """Test de configuration FastMail réussie."""
        # Mock de FastMail
        mock_fastmail_instance = MagicMock()
        mock_fastmail.return_value = mock_fastmail_instance
        
        # Créer un nouveau service
        service = EmailService(self.mock_db)
        
        # Vérifications
        assert service.fastmail is not None
        mock_fastmail.assert_called_once()
    
    @patch('app.services.email.FastMail')
    def test_setup_fastmail_failure(self, mock_fastmail):
        """Test de configuration FastMail échouée."""
        # Mock de FastMail pour échouer
        mock_fastmail.side_effect = Exception("Configuration error")
        
        # Créer un nouveau service
        service = EmailService(self.mock_db)
        
        # Vérifications
        assert service.fastmail is None
    
    @patch('app.services.email.EmailService._log_email')
    async def test_send_email_success_fastmail(self, mock_log_email):
        """Test d'envoi d'email réussi avec FastMail."""
        # Mock FastMail
        mock_fastmail = AsyncMock()
        self.email_service.fastmail = mock_fastmail
        
        # Appel de la méthode
        result = await self.email_service.send_email(
            to="test@example.com",
            subject="Test Subject",
            body="Test body",
            html_body="<p>Test HTML</p>"
        )
        
        # Vérifications
        assert result is True
        mock_fastmail.send_message.assert_called_once()
        mock_log_email.assert_called_once()
    
    @patch('app.services.email.EmailService._send_smtp_direct')
    @patch('app.services.email.EmailService._log_email')
    async def test_send_email_success_smtp_direct(self, mock_log_email, mock_smtp_direct):
        """Test d'envoi d'email réussi avec SMTP direct."""
        # Pas de FastMail disponible
        self.email_service.fastmail = None
        
        # Appel de la méthode
        result = await self.email_service.send_email(
            to="test@example.com",
            subject="Test Subject",
            body="Test body"
        )
        
        # Vérifications
        assert result is True
        mock_smtp_direct.assert_called_once()
        mock_log_email.assert_called_once()
    
    @patch('app.services.email.EmailService._log_email')
    async def test_send_email_failure(self, mock_log_email):
        """Test d'échec d'envoi d'email."""
        # Mock FastMail pour échouer
        mock_fastmail = AsyncMock()
        mock_fastmail.send_message.side_effect = Exception("SMTP Error")
        self.email_service.fastmail = mock_fastmail
        
        # Test de l'exception
        with pytest.raises(EmailError) as exc_info:
            await self.email_service.send_email(
                to="test@example.com",
                subject="Test Subject",
                body="Test body"
            )
        
        # Vérifications
        assert "Échec de l'envoi de l'email" in str(exc_info.value)
        mock_log_email.assert_called_once()
    
    @patch('app.services.email.EmailService.send_email')
    async def test_send_application_confirmation(self, mock_send_email):
        """Test d'envoi d'email de confirmation de candidature."""
        mock_send_email.return_value = True
        
        # Appel de la méthode
        result = await self.email_service.send_application_confirmation(
            candidate_email="candidate@example.com",
            candidate_name="Jean Dupont",
            job_title="Développeur",
            application_id="app-123"
        )
        
        # Vérifications
        assert result is True
        mock_send_email.assert_called_once()
        
        # Vérifier les paramètres
        call_args = mock_send_email.call_args
        assert call_args[1]["to"] == "candidate@example.com"
        assert "Confirmation de candidature" in call_args[1]["subject"]
        assert "Jean Dupont" in call_args[1]["body"]
        assert "Développeur" in call_args[1]["body"]
    
    @patch('app.services.email.EmailService.send_email')
    async def test_send_application_status_update(self, mock_send_email):
        """Test d'envoi d'email de mise à jour de statut."""
        mock_send_email.return_value = True
        
        # Appel de la méthode
        result = await self.email_service.send_application_status_update(
            candidate_email="candidate@example.com",
            candidate_name="Jean Dupont",
            job_title="Développeur",
            new_status="shortlisted",
            notes="Candidat retenu pour l'entretien"
        )
        
        # Vérifications
        assert result is True
        mock_send_email.assert_called_once()
        
        # Vérifier les paramètres
        call_args = mock_send_email.call_args
        assert call_args[1]["to"] == "candidate@example.com"
        assert "Mise à jour de votre candidature" in call_args[1]["subject"]
        assert "présélectionnée" in call_args[1]["body"]
    
    @patch('app.services.email.EmailService.send_email')
    async def test_send_interview_invitation(self, mock_send_email):
        """Test d'envoi d'invitation d'entretien."""
        mock_send_email.return_value = True
        
        interview_date = datetime(2024, 12, 25, 14, 30)
        
        # Appel de la méthode
        result = await self.email_service.send_interview_invitation(
            candidate_email="candidate@example.com",
            candidate_name="Jean Dupont",
            job_title="Développeur",
            interview_date=interview_date,
            interview_location="Salle de réunion",
            interviewer_name="Marie Martin",
            additional_notes="Apporter votre CV"
        )
        
        # Vérifications
        assert result is True
        mock_send_email.assert_called_once()
        
        # Vérifier les paramètres
        call_args = mock_send_email.call_args
        assert call_args[1]["to"] == "candidate@example.com"
        assert "Invitation à un entretien" in call_args[1]["subject"]
        assert "25/12/2024 à 14:30" in call_args[1]["body"]
        assert "Salle de réunion" in call_args[1]["body"]
    
    async def test_log_email_success(self):
        """Test de log d'email réussi."""
        # Appel de la méthode
        await self.email_service._log_email(
            to=["test@example.com"],
            subject="Test Subject",
            body="Test body",
            html_body="<p>Test HTML</p>",
            status="sent",
            error_message=None
        )
        
        # Vérifications
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()
        
        # Vérifier l'objet EmailLog créé
        email_log = self.mock_db.add.call_args[0][0]
        assert isinstance(email_log, EmailLog)
        assert email_log.recipient_email == "test@example.com"
        assert email_log.subject == "Test Subject"
        assert email_log.status == "sent"
    
    async def test_log_email_failure(self):
        """Test de log d'email échoué."""
        # Mock de l'erreur de base de données
        self.mock_db.add.side_effect = Exception("Database error")
        
        # Appel de la méthode (ne doit pas lever d'exception)
        await self.email_service._log_email(
            to=["test@example.com"],
            subject="Test Subject",
            body="Test body",
            html_body=None,
            status="failed",
            error_message="SMTP Error"
        )
        
        # Vérifications
        self.mock_db.add.assert_called_once()
        # commit ne doit pas être appelé à cause de l'erreur
        self.mock_db.commit.assert_not_called()
    
    @patch('app.services.email.select')
    @patch('app.services.email.func')
    @patch('app.services.email.desc')
    async def test_get_email_logs_success(self, mock_desc, mock_func, mock_select):
        """Test de récupération des logs d'emails."""
        # Mock des résultats de base de données
        mock_log = MagicMock()
        mock_log.id = "log-1"
        mock_log.recipient_email = "test@example.com"
        mock_log.subject = "Test Subject"
        mock_log.status = "sent"
        mock_log.sent_at = datetime.now()
        mock_log.error_message = None
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_log]
        
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        
        self.mock_db.execute.side_effect = [mock_result, mock_count_result]
        
        # Appel de la méthode
        result = await self.email_service.get_email_logs(skip=0, limit=10, status="sent")
        
        # Vérifications
        assert result["total"] == 1
        assert len(result["items"]) == 1
        assert result["items"][0]["recipient_email"] == "test@example.com"
        assert result["skip"] == 0
        assert result["limit"] == 10
        assert result["has_more"] is False
    
    @patch('app.services.email.select')
    @patch('app.services.email.func')
    @patch('app.services.email.desc')
    async def test_get_email_logs_with_pagination(self, mock_desc, mock_func, mock_select):
        """Test de récupération des logs avec pagination."""
        # Mock des résultats de base de données
        mock_logs = [MagicMock() for _ in range(5)]
        for i, log in enumerate(mock_logs):
            log.id = f"log-{i}"
            log.recipient_email = f"test{i}@example.com"
            log.subject = f"Subject {i}"
            log.status = "sent"
            log.sent_at = datetime.now()
            log.error_message = None
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_logs
        
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 25  # Total de 25 logs
        
        self.mock_db.execute.side_effect = [mock_result, mock_count_result]
        
        # Appel de la méthode avec pagination
        result = await self.email_service.get_email_logs(skip=10, limit=5)
        
        # Vérifications
        assert result["total"] == 25
        assert len(result["items"]) == 5
        assert result["skip"] == 10
        assert result["limit"] == 5
        assert result["has_more"] is True  # 10 + 5 < 25
