"""
Service pour l'envoi d'emails
"""

from typing import List, Optional, Dict, Any
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import SecretStr
from datetime import datetime, timezone
import structlog
import smtplib
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiofiles
import os

from app.core.config.config import settings
from app.core.exceptions import EmailError

logger = structlog.get_logger(__name__)


class EmailService:
    """Service pour l'envoi d'emails"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self._setup_fastmail()

    def _setup_fastmail(self):
        """Configuration de FastMail"""
        # Ne pas configurer FastMail en environnement de test
        if settings.ENVIRONMENT == "testing":
            self.mail_config = None
            self.fastmail = None
            logger.info("FastMail dÃ©sactivÃ© en environnement de test")
            return

        try:
            # Configuration FastMail avec les nouveaux noms de champs (fastapi-mail v1.4+)
            self.mail_config = ConnectionConfig(
                MAIL_USERNAME=settings.SMTP_USERNAME,
                MAIL_PASSWORD=SecretStr(settings.SMTP_PASSWORD),  # SecretStr requis
                MAIL_FROM=settings.MAIL_FROM_EMAIL,
                MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
                MAIL_PORT=settings.SMTP_PORT,
                MAIL_SERVER=settings.SMTP_HOST,
                MAIL_STARTTLS=settings.SMTP_TLS,  # Nouveau nom (anciennement MAIL_TLS)
                MAIL_SSL_TLS=settings.SMTP_SSL,  # Nouveau nom (anciennement MAIL_SSL)
                USE_CREDENTIALS=True,
                VALIDATE_CERTS=True,
            )
            self.fastmail = FastMail(self.mail_config)
            logger.info("✅ FastMail configuré avec succès")
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
        attachments: Optional[List[Any]] = None,  # Type plus flexible
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
        # Normalisation des destinataires (en dehors du try pour éviter "possibly unbound")
        if isinstance(to, str):
            recipients = [to]
        else:
            recipients = to

        try:
            # En environnement de test, simuler l'envoi
            if settings.ENVIRONMENT == "testing":
                logger.info(
                    "Email simulé en environnement de test",
                    to=recipients,
                    subject=subject,
                )
                return True

            # Création du message (fastapi-mail v1.4+)
            # Dans fastapi-mail v1.4+, on utilise 'body' pour le contenu HTML/plain
            message_body = html_body if html_body else body
            message = MessageSchema(
                subject=subject,
                recipients=recipients,
                body=message_body,
                subtype=MessageType.html if html_body else MessageType.plain,
                cc=cc or [],
                bcc=bcc or [],
                attachments=attachments or [],
            )

            # Envoi via FastMail
            if self.fastmail:
                await self.fastmail.send_message(message)
                logger.info(
                    "Email sent successfully via FastMail",
                    to=recipients,
                    subject=subject,
                )
            else:
                # Fallback vers SMTP direct
                await self._send_smtp_direct(message)
                logger.info(
                    "Email sent successfully via SMTP direct",
                    to=recipients,
                    subject=subject,
                )

            # Log de l'email dans la base de données
            await self._log_email(
                to=recipients,
                subject=subject,
                body=body,
                html_body=html_body,
                status="sent",
                error_message=None,
                sent_at=datetime.now(timezone.utc),
            )

            return True

        except Exception as e:
            error_msg = str(e)
            logger.error(
                "Failed to send email", to=recipients, subject=subject, error=error_msg
            )

            # Log de l'erreur dans la base de données
            await self._log_email(
                to=recipients,
                subject=subject,
                body=body,
                html_body=html_body,
                status="failed",
                error_message=error_msg,
                sent_at=datetime.now(timezone.utc),
            )

            raise EmailError(f"Échec de l'envoi de l'email: {error_msg}")

    async def _send_smtp_direct(self, message: MessageSchema):
        """
        Envoi direct via SMTP (fallback)

        Args:
            message: Message Ã  envoyer
        """
        try:
            # CrÃ©ation du message MIME
            msg = MIMEMultipart("alternative")
            msg["Subject"] = message.subject
            msg["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM_EMAIL}>"
            msg["To"] = ", ".join(message.recipients)

            if message.cc:
                msg["Cc"] = ", ".join(message.cc)

            # Ajout du corps du message
            # Dans fastapi-mail v1.4+, body contient le contenu et subtype indique le type
            if message.body and isinstance(message.body, str):
                message_type = (
                    "html" if message.subtype == MessageType.html else "plain"
                )
                part = MIMEText(message.body, message_type, "utf-8")
                msg.attach(part)

            # Connexion SMTP
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)

            if settings.SMTP_TLS:
                server.starttls()

            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)

            # Envoi
            all_recipients = (
                message.recipients + (message.cc or []) + (message.bcc or [])
            )
            server.send_message(msg, to_addrs=all_recipients)
            server.quit()

        except Exception as e:
            raise EmailError(f"Erreur SMTP direct: {str(e)}")

    async def send_application_confirmation(
        self,
        candidate_email: str,
        candidate_name: str,
        job_title: str,
        application_id: str,
    ) -> bool:
        """
        Envoyer un email de confirmation de candidature

        Args:
            candidate_email: Email du candidat
            candidate_name: Nom du candidat
            job_title: Titre du poste
            application_id: ID de la candidature

        Returns:
            bool: True si l'envoi a rÃ©ussi
        """
        subject = f"Confirmation de candidature - {job_title}"

        body = f"""
Bonjour {candidate_name},

Nous avons bien reÃ§u votre candidature pour le poste de {job_title}.

Votre candidature a Ã©tÃ© enregistrÃ©e avec succÃ¨s et sera examinÃ©e par notre Ã©quipe de recrutement.

NumÃ©ro de candidature: {application_id}

Nous vous contacterons dans les plus brefs dÃ©lais pour vous informer de la suite du processus.

Cordialement,
L'Ã©quipe RH - SEEG
        """

        html_body = f"""
        <html>
        <body>
            <h2>Confirmation de candidature</h2>
            <p>Bonjour {candidate_name},</p>
            <p>Nous avons bien reÃ§u votre candidature pour le poste de <strong>{job_title}</strong>.</p>
            <p>Votre candidature a Ã©tÃ© enregistrÃ©e avec succÃ¨s et sera examinÃ©e par notre Ã©quipe de recrutement.</p>
            <p><strong>NumÃ©ro de candidature:</strong> {application_id}</p>
            <p>Nous vous contacterons dans les plus brefs dÃ©lais pour vous informer de la suite du processus.</p>
            <p>Cordialement,<br>L'Ã©quipe RH - SEEG</p>
        </body>
        </html>
        """

        return await self.send_email(
            to=candidate_email, subject=subject, body=body, html_body=html_body
        )

    async def send_application_status_update(
        self,
        candidate_email: str,
        candidate_name: str,
        job_title: str,
        new_status: str,
        notes: Optional[str] = None,
    ) -> bool:
        """
        Envoyer un email de mise Ã  jour du statut de candidature

        Args:
            candidate_email: Email du candidat
            candidate_name: Nom du candidat
            job_title: Titre du poste
            new_status: Nouveau statut
            notes: Notes additionnelles

        Returns:
            bool: True si l'envoi a rÃ©ussi
        """
        status_messages = {
            "under_review": "en cours d'examen",
            "shortlisted": "prÃ©sÃ©lectionnÃ©e",
            "interview_scheduled": "convoquÃ©e pour un entretien",
            "accepted": "acceptÃ©e",
            "rejected": "non retenue",
        }

        status_text = status_messages.get(new_status, new_status)
        subject = f"Mise Ã  jour de votre candidature - {job_title}"

        body = f"""
Bonjour {candidate_name},

Nous vous informons que votre candidature pour le poste de {job_title} est maintenant {status_text}.

{f"Notes: {notes}" if notes else ""}

Nous vous remercions pour votre intÃ©rÃªt et vous tiendrons informÃ©(e) de toute Ã©volution.

Cordialement,
L'Ã©quipe RH - SEEG
        """

        html_body = f"""
        <html>
        <body>
            <h2>Mise Ã  jour de votre candidature</h2>
            <p>Bonjour {candidate_name},</p>
            <p>Nous vous informons que votre candidature pour le poste de <strong>{job_title}</strong> est maintenant <strong>{status_text}</strong>.</p>
            {f"<p><strong>Notes:</strong> {notes}</p>" if notes else ""}
            <p>Nous vous remercions pour votre intÃ©rÃªt et vous tiendrons informÃ©(e) de toute Ã©volution.</p>
            <p>Cordialement,<br>L'Ã©quipe RH - SEEG</p>
        </body>
        </html>
        """

        return await self.send_email(
            to=candidate_email, subject=subject, body=body, html_body=html_body
        )

    async def send_interview_invitation(
        self,
        candidate_email: str,
        candidate_name: str,
        job_title: str,
        interview_date: datetime,
        interview_location: str,
        interviewer_name: str,
        additional_notes: Optional[str] = None,
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
            bool: True si l'envoi a rÃ©ussi
        """
        subject = f"Invitation Ã  un entretien - {job_title}"

        formatted_date = interview_date.strftime("%d/%m/%Y Ã  %H:%M")

        body = f"""
Bonjour {candidate_name},

Nous avons le plaisir de vous inviter Ã  un entretien pour le poste de {job_title}.

DÃ©tails de l'entretien:
- Date et heure: {formatted_date}
- Lieu: {interview_location}
- Interviewer: {interviewer_name}

{f"Notes additionnelles: {additional_notes}" if additional_notes else ""}

Veuillez confirmer votre prÃ©sence en rÃ©pondant Ã  cet email.

Cordialement,
L'Ã©quipe RH - SEEG
        """

        html_body = f"""
        <html>
        <body>
            <h2>Invitation Ã  un entretien</h2>
            <p>Bonjour {candidate_name},</p>
            <p>Nous avons le plaisir de vous inviter Ã  un entretien pour le poste de <strong>{job_title}</strong>.</p>
            <h3>DÃ©tails de l'entretien:</h3>
            <ul>
                <li><strong>Date et heure:</strong> {formatted_date}</li>
                <li><strong>Lieu:</strong> {interview_location}</li>
                <li><strong>Interviewer:</strong> {interviewer_name}</li>
            </ul>
            {f"<p><strong>Notes additionnelles:</strong> {additional_notes}</p>" if additional_notes else ""}
            <p>Veuillez confirmer votre prÃ©sence en rÃ©pondant Ã  cet email.</p>
            <p>Cordialement,<br>L'Ã©quipe RH - SEEG</p>
        </body>
        </html>
        """

        return await self.send_email(
            to=candidate_email, subject=subject, body=body, html_body=html_body
        )

    async def _log_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        html_body: Optional[str],
        status: str,
        error_message: Optional[str],
        sent_at: datetime,
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
            sent_at: Date d'envoi
        """
        try:
            # Adapter au modèle EmailLog existant - Version MongoDB
            email_log = {
                "to": ", ".join(to),
                "subject": subject,
                "html": html_body if html_body else body,
                "category": status,
                "sent_at": sent_at,
                "email_metadata": (
                    {
                        "body_plain": body,
                        "status": status,
                        "error_message": error_message,
                    }
                    if error_message
                    else {"body_plain": body, "status": status}
                ),
            }

            await self.db.email_logs.insert_one(email_log)

        except Exception as e:
            logger.error("Failed to log email", error=str(e))

    async def get_email_logs(
        self, skip: int = 0, limit: int = 100, category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Récupérer les logs d'emails

        Args:
            skip: Nombre d'éléments à ignorer
            limit: Nombre maximum d'éléments à retourner
            category: Filtrer par catégorie (status)

        Returns:
            Dict contenant les logs et les métadonnées de pagination
        """
        try:
            filter_query = {}
            if category:
                filter_query["category"] = category

            cursor = (
                self.db.email_logs.find(filter_query)
                .sort("sent_at", -1)
                .skip(skip)
                .limit(limit)
            )
            logs = await cursor.to_list(length=limit)

            total_count = await self.db.email_logs.count_documents(filter_query)

            return {
                "items": [
                    {
                        "id": str(log.get("_id", log.get("id"))),
                        "recipient_email": log.get("to"),
                        "subject": log.get("subject"),
                        "status": log.get("category"),
                        "sent_at": log.get("sent_at"),
                        "error_message": (
                            log.get("email_metadata", {}).get("error_message")
                            if log.get("email_metadata")
                            else None
                        ),
                    }
                    for log in logs
                ],
                "total": total_count,
                "skip": skip,
                "limit": limit,
                "has_more": skip + len(logs) < total_count,
            }
        except Exception as e:
            logger.error("Failed to get email logs", error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération des logs d'emails")

    # ========================================================================
    # TEMPLATES EMAIL - SYSTÈME D'AUTHENTIFICATION v2.0
    # ========================================================================

    def _get_salutation(
        self, sexe: Optional[str], first_name: str, last_name: str
    ) -> str:
        """
        Générer la salutation appropriée selon le sexe.

        Args:
            sexe: 'M' (Homme) ou 'F' (Femme)
            first_name: Prénom
            last_name: Nom

        Returns:
            str: "Monsieur Jean Dupont" ou "Madame Marie Martin"
        """
        if sexe == "M":
            return f"Monsieur {first_name} {last_name}"
        elif sexe == "F":
            return f"Madame {first_name} {last_name}"
        else:
            return f"{first_name} {last_name}"

    async def send_welcome_email(
        self, to_email: str, first_name: str, last_name: str, sexe: Optional[str] = None
    ) -> bool:
        """
        Email 1 : Bienvenue sur la plateforme (pour candidats avec statut='actif').

        Envoyé à :
        - Candidats EXTERNES après inscription
        - Candidats INTERNES avec email @seeg-gabon.com après inscription

        Args:
            to_email: Email du candidat
            first_name: Prénom
            last_name: Nom
            sexe: 'M' ou 'F' pour personnaliser la salutation
        """
        salutation = self._get_salutation(sexe, first_name, last_name)

        subject = "Bienvenue sur OneHCM - SEEG Talent Source"

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #00C7B7 0%, #0078D4 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
        .info-box {{ background: #E3F2FD; border-left: 4px solid #0078D4; padding: 15px; margin: 20px 0; border-radius: 4px; }}
        .button {{ display: inline-block; background: #00C7B7; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; }}
        ul {{ line-height: 2; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Bienvenue sur OneHCM</h1>
            <p>SEEG Talent Source</p>
        </div>
        <div class="content">
            <p><strong>{salutation},</strong></p>
            
            <p>Bienvenue sur la plateforme <strong>OneHCM - SEEG Talent Source</strong> !</p>
            
            <p>Votre compte a été créé avec succès. Vous pouvez désormais :</p>
            <ul>
                <li>Consulter les offres d'emploi disponibles</li>
                <li>Postuler aux postes qui vous intéressent</li>
                <li>Suivre l'état de vos candidatures</li>
                <li>Mettre à jour votre profil</li>
            </ul>
            
            <p>Pour vous connecter, rendez-vous sur :</p>
            <p style="text-align: center;">
                <a href="{settings.PUBLIC_APP_URL}" class="button">Se connecter à OneHCM</a>
            </p>
            
            <div class="info-box">
                <p><strong>📧 Besoin d'aide ?</strong></p>
                <p>Contactez-nous : <a href="mailto:support@seeg-talentsource.com">support@seeg-talentsource.com</a></p>
            </div>
            
            <p>Cordialement,<br>
            <strong>L'équipe OneHCM - SEEG Talent Source</strong><br>
            <a href="{settings.PUBLIC_APP_URL}">{settings.PUBLIC_APP_URL}</a></p>
        </div>
        <div class="footer">
            <p>&copy; 2025 SEEG - Société d'Énergie et d'Eau du Gabon</p>
            <p>OneHCM - Système de Gestion des Ressources Humaines</p>
        </div>
    </div>
</body>
</html>
        """

        plain_body = f"""
{salutation},

Bienvenue sur la plateforme OneHCM - SEEG Talent Source !

Votre compte a été créé avec succès. Vous pouvez désormais :
- Consulter les offres d'emploi disponibles
- Postuler aux postes qui vous intéressent
- Suivre l'état de vos candidatures
- Mettre à jour votre profil

Pour vous connecter, rendez-vous sur :
{settings.PUBLIC_APP_URL}

📧 Besoin d'aide ?
Contactez-nous : support@seeg-talentsource.com

Cordialement,
L'équipe OneHCM - SEEG Talent Source
{settings.PUBLIC_APP_URL}
        """

        try:
            await self.send_email(
                to=to_email, subject=subject, body=plain_body, html_body=html_body
            )
            logger.info(
                "Email de bienvenue envoyé",
                to=to_email,
                name=f"{first_name} {last_name}",
            )
            return True
        except Exception as e:
            logger.error("Erreur envoi email bienvenue", to=to_email, error=str(e))
            return False

    async def send_access_request_pending_email(
        self, to_email: str, first_name: str, last_name: str, sexe: Optional[str] = None
    ) -> bool:
        """
        Email 2 : Demande d'accès en cours de traitement.

        Envoyé aux candidats internes sans email @seeg-gabon.com.
        Leur compte est en attente de validation par un recruteur.

        Args:
            to_email: Email du candidat
            first_name: Prénom
            last_name: Nom
            sexe: 'M' ou 'F'
        """
        salutation = self._get_salutation(sexe, first_name, last_name)

        subject = "Demande d'Accès en Cours de Traitement - OneHCM"

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
        .warning-box {{ background: #FFF3E0; border-left: 4px solid #FF9800; padding: 15px; margin: 20px 0; border-radius: 4px; }}
        .info-box {{ background: #E3F2FD; border-left: 4px solid #0078D4; padding: 15px; margin: 20px 0; border-radius: 4px; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⏳ Demande d'Accès en Cours de Traitement</h1>
        </div>
        <div class="content">
            <p><strong>{salutation},</strong></p>
            
            <p>Votre demande d'accès à la plateforme <strong>OneHCM - SEEG Talent Source</strong> a bien été enregistrée.</p>
            
            <div class="warning-box">
                <p><strong>⏳ Statut : En attente de validation</strong></p>
                <p>Notre équipe va examiner votre demande et vous recevrez un email de confirmation une fois votre accès validé.</p>
                <p>Cela peut prendre quelques jours ouvrables.</p>
            </div>
            
            <div class="info-box">
                <p><strong>📞 Questions ?</strong></p>
                <p>Contact : <a href="mailto:support@seeg-talentsource.com">support@seeg-talentsource.com</a></p>
            </div>
            
            <p>Cordialement,<br>
            <strong>L'équipe OneHCM - SEEG Talent Source</strong><br>
            <a href="{settings.PUBLIC_APP_URL}">{settings.PUBLIC_APP_URL}</a></p>
        </div>
        <div class="footer">
            <p>&copy; 2025 SEEG - Société d'Énergie et d'Eau du Gabon</p>
        </div>
    </div>
</body>
</html>
        """

        plain_body = f"""
{salutation},

Votre demande d'accès à la plateforme OneHCM - SEEG Talent Source a bien été enregistrée.

⏳ STATUT : EN ATTENTE DE VALIDATION

Notre équipe va examiner votre demande et vous recevrez un email de confirmation 
une fois votre accès validé. Cela peut prendre quelques jours ouvrables.

📞 Questions ?
Contact : support@seeg-talentsource.com

Cordialement,
L'équipe OneHCM - SEEG Talent Source
{settings.PUBLIC_APP_URL}
        """

        try:
            await self.send_email(
                to=to_email, subject=subject, body=plain_body, html_body=html_body
            )
            logger.info(
                "Email demande en attente envoyé",
                to=to_email,
                name=f"{first_name} {last_name}",
            )
            return True
        except Exception as e:
            logger.error(
                "Erreur envoi email demande en attente", to=to_email, error=str(e)
            )
            return False

    async def send_access_request_notification_to_admin(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone: Optional[str],
        matricule: Optional[str],
        date_of_birth: Optional[str],
        sexe: Optional[str],
        adresse: Optional[str],
    ) -> bool:
        """
        Email 3 : Notification admin - Nouvelle demande d'accès.

        Envoyé à support@seeg-talentsource.com quand un candidat interne
        sans email SEEG s'inscrit.

        Args:
            first_name: Prénom du candidat
            last_name: Nom du candidat
            email: Email du candidat
            phone: Téléphone
            matricule: Matricule SEEG
            date_of_birth: Date de naissance
            sexe: Sexe (M/F)
            adresse: Adresse
        """
        sexe_label = (
            "Homme" if sexe == "M" else ("Femme" if sexe == "F" else "Non précisé")
        )

        subject = "🔔 Nouvelle Demande d'Accès - OneHCM"

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #0078D4 0%, #00C7B7 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
        .info-card {{ background: white; border: 1px solid #ddd; padding: 20px; margin: 20px 0; border-radius: 6px; }}
        .info-row {{ display: flex; padding: 8px 0; border-bottom: 1px solid #eee; }}
        .info-label {{ font-weight: bold; min-width: 150px; color: #555; }}
        .info-value {{ color: #333; }}
        .button {{ display: inline-block; background: #00C7B7; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔔 Nouvelle Demande d'Accès</h1>
        </div>
        <div class="content">
            <p>Une nouvelle demande d'accès à la plateforme a été enregistrée.</p>
            
            <div class="info-card">
                <h3>📋 Informations du Candidat</h3>
                <div class="info-row">
                    <div class="info-label">Nom complet :</div>
                    <div class="info-value">{first_name} {last_name}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Email :</div>
                    <div class="info-value">{email}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Téléphone :</div>
                    <div class="info-value">{phone or 'Non renseigné'}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Matricule SEEG :</div>
                    <div class="info-value"><strong>{matricule}</strong></div>
                </div>
                <div class="info-row">
                    <div class="info-label">Date de naissance :</div>
                    <div class="info-value">{date_of_birth or 'Non renseignée'}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Sexe :</div>
                    <div class="info-value">{sexe_label}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Adresse :</div>
                    <div class="info-value">{adresse or 'Non renseignée'}</div>
                </div>
            </div>
            
            <p><strong>Type de demande :</strong> Candidat interne sans email professionnel SEEG</p>
            <p><strong>Date de la demande :</strong> {datetime.now(timezone.utc).strftime('%d/%m/%Y à %H:%M')}</p>
            
            <p style="text-align: center;">
                <a href="{settings.PUBLIC_APP_URL}/recruiter/access-requests" class="button">
                    Accéder au Dashboard Recruteur
                </a>
            </p>
            
            <p>Cordialement,<br>
            <strong>Système OneHCM - SEEG Talent Source</strong></p>
        </div>
        <div class="footer">
            <p>Email automatique - Ne pas répondre</p>
        </div>
    </div>
</body>
</html>
        """

        plain_body = f"""
🔔 NOUVELLE DEMANDE D'ACCÈS

Une nouvelle demande d'accès à la plateforme a été enregistrée.

INFORMATIONS DU CANDIDAT
------------------------
Nom complet : {first_name} {last_name}
Email : {email}
Téléphone : {phone or 'Non renseigné'}
Matricule SEEG : {matricule}
Date de naissance : {date_of_birth or 'Non renseignée'}
Sexe : {sexe_label}
Adresse : {adresse or 'Non renseignée'}

Type de demande : Candidat interne sans email professionnel SEEG
Date de la demande : {datetime.now(timezone.utc).strftime('%d/%m/%Y à %H:%M')}

Accéder au Dashboard Recruteur :
{settings.PUBLIC_APP_URL}/recruiter/access-requests

Cordialement,
Système OneHCM - SEEG Talent Source
        """

        admin_email = "support@seeg-talentsource.com"

        try:
            await self.send_email(
                to=admin_email, subject=subject, body=plain_body, html_body=html_body
            )
            logger.info(
                "Email notification admin envoyé",
                to=admin_email,
                candidate=f"{first_name} {last_name}",
                matricule=matricule,
            )
            return True
        except Exception as e:
            logger.error("Erreur envoi notification admin", error=str(e))
            return False

    async def send_access_approved_email(
        self, to_email: str, first_name: str, last_name: str, sexe: Optional[str] = None
    ) -> bool:
        """
        Email 4 : Demande d'accès approuvée.

        Envoyé au candidat quand un recruteur approuve sa demande d'accès.
        Le compte passe de 'en_attente' à 'actif'.

        Args:
            to_email: Email du candidat
            first_name: Prénom
            last_name: Nom
            sexe: 'M' ou 'F'
        """
        salutation = self._get_salutation(sexe, first_name, last_name)

        subject = "✅ Accès Approuvé - OneHCM"

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
        .success-box {{ background: #E8F5E9; border-left: 4px solid #4CAF50; padding: 15px; margin: 20px 0; border-radius: 4px; }}
        .info-box {{ background: #E3F2FD; border-left: 4px solid #0078D4; padding: 15px; margin: 20px 0; border-radius: 4px; }}
        .button {{ display: inline-block; background: #4CAF50; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: bold; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; }}
        ul {{ line-height: 2; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ Demande d'Accès Approuvée</h1>
        </div>
        <div class="content">
            <p><strong>{salutation},</strong></p>
            
            <p><strong>Bonne nouvelle !</strong> Votre demande d'accès à la plateforme <strong>OneHCM - SEEG Talent Source</strong> a été approuvée.</p>
            
            <div class="success-box">
                <p style="font-size: 18px; margin: 0;"><strong>✅ Votre compte est maintenant actif !</strong></p>
            </div>
            
            <p>Vous pouvez désormais vous connecter et accéder à toutes les fonctionnalités :</p>
            <ul>
                <li>Consulter les offres d'emploi</li>
                <li>Postuler aux postes disponibles</li>
                <li>Suivre vos candidatures</li>
                <li>Gérer votre profil</li>
            </ul>
            
            <p style="text-align: center;">
                <a href="{settings.PUBLIC_APP_URL}" class="button">Se Connecter Maintenant</a>
            </p>
            
            <div class="info-box">
                <p><strong>📧 Besoin d'aide ?</strong></p>
                <p>Contact : <a href="mailto:support@seeg-talentsource.com">support@seeg-talentsource.com</a></p>
            </div>
            
            <p>Cordialement,<br>
            <strong>L'équipe OneHCM - SEEG Talent Source</strong><br>
            <a href="{settings.PUBLIC_APP_URL}">{settings.PUBLIC_APP_URL}</a></p>
        </div>
        <div class="footer">
            <p>&copy; 2025 SEEG - Société d'Énergie et d'Eau du Gabon</p>
        </div>
    </div>
</body>
</html>
        """

        plain_body = f"""
{salutation},

Bonne nouvelle ! Votre demande d'accès à la plateforme OneHCM - SEEG Talent Source a été approuvée.

✅ VOTRE COMPTE EST MAINTENANT ACTIF !

Vous pouvez désormais vous connecter et accéder à toutes les fonctionnalités :
- Consulter les offres d'emploi
- Postuler aux postes disponibles
- Suivre vos candidatures
- Gérer votre profil

Se connecter : {settings.PUBLIC_APP_URL}

📧 Besoin d'aide ?
Contact : support@seeg-talentsource.com

Cordialement,
L'équipe OneHCM - SEEG Talent Source
{settings.PUBLIC_APP_URL}
        """

        try:
            await self.send_email(
                to=to_email, subject=subject, body=plain_body, html_body=html_body
            )
            logger.info(
                "Email d'approbation envoyé",
                to=to_email,
                name=f"{first_name} {last_name}",
            )
            return True
        except Exception as e:
            logger.error("Erreur envoi email approbation", to=to_email, error=str(e))
            return False

    async def send_access_rejected_email(
        self,
        to_email: str,
        first_name: str,
        last_name: str,
        rejection_reason: str,
        sexe: Optional[str] = None,
    ) -> bool:
        """
        Email 5 : Demande d'accès refusée.

        Envoyé au candidat quand un recruteur refuse sa demande d'accès.
        Le compte passe de 'en_attente' à 'bloqué'.
        Inclut le motif du refus saisi par le recruteur.

        Args:
            to_email: Email du candidat
            first_name: Prénom
            last_name: Nom
            rejection_reason: Motif du refus (≥ 20 caractères)
            sexe: 'M' ou 'F'
        """
        salutation = self._get_salutation(sexe, first_name, last_name)

        subject = "❌ Demande d'Accès Refusée - OneHCM"

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #F44336 0%, #D32F2F 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
        .error-box {{ background: #FFEBEE; border-left: 4px solid #F44336; padding: 15px; margin: 20px 0; border-radius: 4px; }}
        .info-box {{ background: #E3F2FD; border-left: 4px solid #0078D4; padding: 15px; margin: 20px 0; border-radius: 4px; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>❌ Demande d'Accès Refusée</h1>
        </div>
        <div class="content">
            <p><strong>{salutation},</strong></p>
            
            <p>Nous vous informons que votre demande d'accès à la plateforme <strong>OneHCM - SEEG Talent Source</strong> n'a pas pu être validée.</p>
            
            <div class="error-box">
                <p><strong>❌ Motif du refus</strong></p>
                <p style="margin: 10px 0; padding: 10px; background: white; border-radius: 4px;">{rejection_reason}</p>
            </div>
            
            <p>Si vous pensez qu'il s'agit d'une erreur ou si vous avez des questions, n'hésitez pas à contacter notre équipe support.</p>
            
            <div class="info-box">
                <p><strong>📞 Contact Support</strong></p>
                <p><a href="mailto:support@seeg-talentsource.com">support@seeg-talentsource.com</a></p>
            </div>
            
            <p>Cordialement,<br>
            <strong>L'équipe OneHCM - SEEG Talent Source</strong><br>
            <a href="{settings.PUBLIC_APP_URL}">{settings.PUBLIC_APP_URL}</a></p>
        </div>
        <div class="footer">
            <p>&copy; 2025 SEEG - Société d'Énergie et d'Eau du Gabon</p>
        </div>
    </div>
</body>
</html>
        """

        plain_body = f"""
{salutation},

Nous vous informons que votre demande d'accès à la plateforme OneHCM - SEEG Talent Source 
n'a pas pu être validée.

❌ MOTIF DU REFUS
-----------------
{rejection_reason}

Si vous pensez qu'il s'agit d'une erreur ou si vous avez des questions, 
n'hésitez pas à contacter notre équipe support.

📞 CONTACT SUPPORT
support@seeg-talentsource.com

Cordialement,
L'équipe OneHCM - SEEG Talent Source
{settings.PUBLIC_APP_URL}
        """

        try:
            await self.send_email(
                to=to_email, subject=subject, body=plain_body, html_body=html_body
            )
            logger.info(
                "Email de refus envoyé", to=to_email, name=f"{first_name} {last_name}"
            )
            return True
        except Exception as e:
            logger.error("Erreur envoi email refus", to=to_email, error=str(e))
            return False
