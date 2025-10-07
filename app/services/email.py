"""
Service pour l'envoi d'emails
"""
from typing import List, Optional, Dict, Any
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, func, desc
from datetime import datetime, timezone
import structlog
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiofiles
import os

from app.models.email import EmailLog
from app.core.config.config import settings
from app.core.exceptions import EmailError

logger = structlog.get_logger(__name__)


class EmailService:
    """Service pour l'envoi d'emails"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._setup_fastmail()
    
    def _setup_fastmail(self):
        """Configuration de FastMail"""
        # Ne pas configurer FastMail en environnement de test
        if settings.ENVIRONMENT == "testing":
            self.mail_config = None
            self.fastmail = None
            logger.info("FastMail désactivé en environnement de test")
            return
            
        try:
            self.mail_config = ConnectionConfig(
                MAIL_USERNAME=settings.SMTP_USERNAME,
                MAIL_PASSWORD=settings.SMTP_PASSWORD,
                MAIL_FROM=settings.MAIL_FROM_EMAIL,
                MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
                MAIL_PORT=settings.SMTP_PORT,
                MAIL_SERVER=settings.SMTP_HOST,
                MAIL_TLS=settings.SMTP_TLS,
                MAIL_SSL=settings.SMTP_SSL,
                USE_CREDENTIALS=True,
                VALIDATE_CERTS=True
            )
            self.fastmail = FastMail(self.mail_config)
        except Exception as e:
            logger.error("Failed to setup FastMail", error=str(e))
            self.fastmail = None
    
    async def send_email(
        self,
        to: str | List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        sender: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Envoyer un email
        
        Args:
            to: Destinataire(s)
            subject: Sujet de l'email
            body: Corps de l'email (texte)
            html_body: Corps de l'email (HTML)
            sender: Expéditeur (optionnel)
            cc: Copie carbone
            bcc: Copie carbone cachée
            attachments: Pièces jointes
            
        Returns:
            bool: True si l'envoi a réussi
            
        Raises:
            EmailError: Si l'envoi échoue
        """
        try:
            # Normalisation des destinataires
            if isinstance(to, str):
                recipients = [to]
            else:
                recipients = to
            
            # En environnement de test, simuler l'envoi
            if settings.ENVIRONMENT == "testing":
                logger.info(
                    "Email simulé en environnement de test",
                    to=recipients,
                    subject=subject
                )
                return True
            
            # Création du message
            message = MessageSchema(
                subject=subject,
                recipients=recipients,
                body=body,
                html=html_body,
                cc=cc or [],
                bcc=bcc or [],
                attachments=attachments or []
            )
            
            # Envoi via FastMail
            if self.fastmail:
                await self.fastmail.send_message(message)
                logger.info(
                    "Email sent successfully via FastMail",
                    to=recipients,
                    subject=subject
                )
            else:
                # Fallback vers SMTP direct
                await self._send_smtp_direct(message)
                logger.info(
                    "Email sent successfully via SMTP direct",
                    to=recipients,
                    subject=subject
                )
            
            # Log de l'email dans la base de données
            await self._log_email(
                to=recipients,
                subject=subject,
                body=body,
                html_body=html_body,
                status="sent",
                error_message=None
            )
            
            return True
            
        except Exception as e:
            error_msg = str(e)
            logger.error(
                "Failed to send email",
                to=recipients if 'recipients' in locals() else to,
                subject=subject,
                error=error_msg
            )
            
            # Log de l'erreur dans la base de données
            await self._log_email(
                to=recipients if 'recipients' in locals() else to,
                subject=subject,
                body=body,
                html_body=html_body,
                status="failed",
                error_message=error_msg
            )
            
            raise EmailError(f"Échec de l'envoi de l'email: {error_msg}")
    
    async def _send_smtp_direct(self, message: MessageSchema):
        """
        Envoi direct via SMTP (fallback)
        
        Args:
            message: Message à envoyer
        """
        try:
            # Création du message MIME
            msg = MIMEMultipart('alternative')
            msg['Subject'] = message.subject
            msg['From'] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM_EMAIL}>"
            msg['To'] = ', '.join(message.recipients)
            
            if message.cc:
                msg['Cc'] = ', '.join(message.cc)
            
            # Ajout du corps du message
            if message.body:
                text_part = MIMEText(message.body, 'plain', 'utf-8')
                msg.attach(text_part)
            
            if message.html:
                html_part = MIMEText(message.html, 'html', 'utf-8')
                msg.attach(html_part)
            
            # Connexion SMTP
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            
            if settings.SMTP_TLS:
                server.starttls()
            
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            
            # Envoi
            all_recipients = message.recipients + (message.cc or []) + (message.bcc or [])
            server.send_message(msg, to_addrs=all_recipients)
            server.quit()
            
        except Exception as e:
            raise EmailError(f"Erreur SMTP direct: {str(e)}")
    
    async def send_application_confirmation(
        self,
        candidate_email: str,
        candidate_name: str,
        job_title: str,
        application_id: str
    ) -> bool:
        """
        Envoyer un email de confirmation de candidature
        
        Args:
            candidate_email: Email du candidat
            candidate_name: Nom du candidat
            job_title: Titre du poste
            application_id: ID de la candidature
            
        Returns:
            bool: True si l'envoi a réussi
        """
        subject = f"Confirmation de candidature - {job_title}"
        
        body = f"""
Bonjour {candidate_name},

Nous avons bien reçu votre candidature pour le poste de {job_title}.

Votre candidature a été enregistrée avec succès et sera examinée par notre équipe de recrutement.

Numéro de candidature: {application_id}

Nous vous contacterons dans les plus brefs délais pour vous informer de la suite du processus.

Cordialement,
L'équipe RH - SEEG
        """
        
        html_body = f"""
        <html>
        <body>
            <h2>Confirmation de candidature</h2>
            <p>Bonjour {candidate_name},</p>
            <p>Nous avons bien reçu votre candidature pour le poste de <strong>{job_title}</strong>.</p>
            <p>Votre candidature a été enregistrée avec succès et sera examinée par notre équipe de recrutement.</p>
            <p><strong>Numéro de candidature:</strong> {application_id}</p>
            <p>Nous vous contacterons dans les plus brefs délais pour vous informer de la suite du processus.</p>
            <p>Cordialement,<br>L'équipe RH - SEEG</p>
        </body>
        </html>
        """
        
        return await self.send_email(
            to=candidate_email,
            subject=subject,
            body=body,
            html_body=html_body
        )
    
    async def send_application_status_update(
        self,
        candidate_email: str,
        candidate_name: str,
        job_title: str,
        new_status: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Envoyer un email de mise à jour du statut de candidature
        
        Args:
            candidate_email: Email du candidat
            candidate_name: Nom du candidat
            job_title: Titre du poste
            new_status: Nouveau statut
            notes: Notes additionnelles
            
        Returns:
            bool: True si l'envoi a réussi
        """
        status_messages = {
            "under_review": "en cours d'examen",
            "shortlisted": "présélectionnée",
            "interview_scheduled": "convoquée pour un entretien",
            "accepted": "acceptée",
            "rejected": "non retenue"
        }
        
        status_text = status_messages.get(new_status, new_status)
        subject = f"Mise à jour de votre candidature - {job_title}"
        
        body = f"""
Bonjour {candidate_name},

Nous vous informons que votre candidature pour le poste de {job_title} est maintenant {status_text}.

{f"Notes: {notes}" if notes else ""}

Nous vous remercions pour votre intérêt et vous tiendrons informé(e) de toute évolution.

Cordialement,
L'équipe RH - SEEG
        """
        
        html_body = f"""
        <html>
        <body>
            <h2>Mise à jour de votre candidature</h2>
            <p>Bonjour {candidate_name},</p>
            <p>Nous vous informons que votre candidature pour le poste de <strong>{job_title}</strong> est maintenant <strong>{status_text}</strong>.</p>
            {f"<p><strong>Notes:</strong> {notes}</p>" if notes else ""}
            <p>Nous vous remercions pour votre intérêt et vous tiendrons informé(e) de toute évolution.</p>
            <p>Cordialement,<br>L'équipe RH - SEEG</p>
        </body>
        </html>
        """
        
        return await self.send_email(
            to=candidate_email,
            subject=subject,
            body=body,
            html_body=html_body
        )
    
    async def send_interview_invitation(
        self,
        candidate_email: str,
        candidate_name: str,
        job_title: str,
        interview_date: datetime,
        interview_location: str,
        interviewer_name: str,
        additional_notes: Optional[str] = None
    ) -> bool:
        """
        Envoyer une invitation d'entretien
        
        Args:
            candidate_email: Email du candidat
            candidate_name: Nom du candidat
            job_title: Titre du poste
            interview_date: Date de l'entretien
            interview_location: Lieu de l'entretien
            interviewer_name: Nom de l'interviewer
            additional_notes: Notes additionnelles
            
        Returns:
            bool: True si l'envoi a réussi
        """
        subject = f"Invitation à un entretien - {job_title}"
        
        formatted_date = interview_date.strftime("%d/%m/%Y à %H:%M")
        
        body = f"""
Bonjour {candidate_name},

Nous avons le plaisir de vous inviter à un entretien pour le poste de {job_title}.

Détails de l'entretien:
- Date et heure: {formatted_date}
- Lieu: {interview_location}
- Interviewer: {interviewer_name}

{f"Notes additionnelles: {additional_notes}" if additional_notes else ""}

Veuillez confirmer votre présence en répondant à cet email.

Cordialement,
L'équipe RH - SEEG
        """
        
        html_body = f"""
        <html>
        <body>
            <h2>Invitation à un entretien</h2>
            <p>Bonjour {candidate_name},</p>
            <p>Nous avons le plaisir de vous inviter à un entretien pour le poste de <strong>{job_title}</strong>.</p>
            <h3>Détails de l'entretien:</h3>
            <ul>
                <li><strong>Date et heure:</strong> {formatted_date}</li>
                <li><strong>Lieu:</strong> {interview_location}</li>
                <li><strong>Interviewer:</strong> {interviewer_name}</li>
            </ul>
            {f"<p><strong>Notes additionnelles:</strong> {additional_notes}</p>" if additional_notes else ""}
            <p>Veuillez confirmer votre présence en répondant à cet email.</p>
            <p>Cordialement,<br>L'équipe RH - SEEG</p>
        </body>
        </html>
        """
        
        return await self.send_email(
            to=candidate_email,
            subject=subject,
            body=body,
            html_body=html_body
        )
    
    async def _log_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        html_body: Optional[str],
        status: str,
        error_message: Optional[str]
    ):
        """
        Enregistrer l'email dans les logs
        
        Args:
            to: Destinataires
            subject: Sujet
            body: Corps du message
            html_body: Corps HTML
            status: Statut de l'envoi
            error_message: Message d'erreur (si applicable)
        """
        try:
            email_log = EmailLog(
                recipient_email=', '.join(to),
                subject=subject,
                body=body,
                html_body=html_body,
                status=status,
                error_message=error_message,
                sent_at=datetime.now(timezone.utc)
            )
            
            self.db.add(email_log)
            await self.db.commit()
            
        except Exception as e:
            logger.error("Failed to log email", error=str(e))
    
    async def get_email_logs(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Récupérer les logs d'emails
        
        Args:
            skip: Nombre d'éléments à ignorer
            limit: Nombre maximum d'éléments à retourner
            status: Filtrer par statut
            
        Returns:
            Dict contenant les logs et les métadonnées de pagination
        """
        query = select(EmailLog)
        count_query = select(func.count(EmailLog.id))
        
        if status:
            query = query.where(EmailLog.status == status)
            count_query = count_query.where(EmailLog.status == status)
        
        query = query.order_by(desc(EmailLog.sent_at))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        logs = result.scalars().all()
        
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar()
        
        return {
            "items": [
                {
                    "id": str(log.id),
                    "recipient_email": log.recipient_email,
                    "subject": log.subject,
                    "status": log.status,
                    "sent_at": log.sent_at,
                    "error_message": log.error_message
                }
                for log in logs
            ],
            "total": total_count,
            "skip": skip,
            "limit": limit,
            "has_more": skip + len(logs) < total_count
        }
