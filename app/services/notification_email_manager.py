"""
Gestionnaire unifié pour l'envoi d'emails ET de notifications
Respect des principes SOLID et des meilleures pratiques de génie logiciel

Principes appliqués:
- Single Responsibility: Chaque méthode gère une seule action utilisateur
- Open/Closed: Facilement extensible pour de nouvelles notifications
- Dependency Injection: Les services sont injectés, pas créés
- Fail-Safe: Les erreurs d'email/notification ne bloquent jamais l'action principale
- Logging: Traçabilité complète de toutes les opérations
- Idempotence: Les notifications peuvent être envoyées plusieurs fois sans effet de bord
"""
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, Any, Union
from uuid import UUID
import structlog

from app.services.email import EmailService
from app.services.notification_manager import NotificationManager
from app.core.exceptions import EmailError

logger = structlog.get_logger(__name__)


class NotificationEmailManager:
    """
    Gestionnaire unifié pour envoyer simultanément des emails et des notifications
    
    Architecture:
    - Composition > Héritage: Utilise EmailService et NotificationManager
    - Fail-Safe: Les erreurs n'interrompent jamais le flux principal
    - Atomic Operations: Chaque notification/email est indépendant
    - Detailed Logging: Traçabilité complète
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialiser le gestionnaire avec injection de dÃ©pendances
        
        Args:
            db: Base de donnÃ©es MongoDB
        """
        self.db = db
        self.email_service = EmailService(db)
        self.notification_manager = NotificationManager(db)
    
    # ==================== INSCRIPTION ====================
    
    async def notify_and_email_registration(
        self,
        user_id: Union[UUID, str],
        email: str,
        first_name: str,
        last_name: str,
        sexe: Optional[str] = None
    ) -> dict:
        """
        Envoyer email de bienvenue + notification après inscription
        
        Pattern: Fail-Safe avec retour détaillé du statut
        
        Args:
            user_id: ID de l'utilisateur
            email: Email de l'utilisateur
            first_name: Prénom
            last_name: Nom
            sexe: Sexe (pour personnalisation email)
            
        Returns:
            dict: Statut de chaque envoi {email_sent: bool, notification_sent: bool}
        """
        result = {"email_sent": False, "notification_sent": False}
        
        # 1. Envoi email (non-bloquant)
        try:
            logger.info("📧 Envoi email bienvenue", user_id=str(user_id), email=email)
            await self.email_service.send_welcome_email(
                to_email=email,
                first_name=first_name,
                last_name=last_name,
                sexe=sexe
            )
            result["email_sent"] = True
            logger.info("✅ Email bienvenue envoyé", user_id=str(user_id))
        except EmailError as e:
            logger.warning("⚠️ Erreur envoi email bienvenue", 
                          user_id=str(user_id), error=str(e))
        except Exception as e:
            logger.error("❌ Erreur inattendue email bienvenue", 
                        user_id=str(user_id), error=str(e), exc_info=True)
        
        # 2. Création notification (non-bloquant)
        try:
            logger.info("🔔 Création notification bienvenue", user_id=str(user_id))
            await self.notification_manager.notify_user_registered(
                user_id=user_id,
                email=email
            )
            result["notification_sent"] = True
            logger.info("✅ Notification bienvenue créée", user_id=str(user_id))
        except Exception as e:
            logger.error("❌ Erreur création notification bienvenue", 
                        user_id=str(user_id), error=str(e), exc_info=True)
        
        return result
    
    # ==================== RÉINITIALISATION MOT DE PASSE ====================
    
    async def notify_and_email_password_reset_request(
        self,
        user_id: Union[UUID, str],
        email: str
    ) -> dict:
        """
        Notification après demande de réinitialisation de mot de passe
        
        Note: L'email de reset avec le token est envoyé par AuthService.reset_password_request
        Cette méthode ajoute uniquement la notification dans l'application
        
        Args:
            user_id: ID de l'utilisateur
            email: Email de l'utilisateur
            
        Returns:
            dict: Statut de l'envoi {notification_sent: bool}
        """
        result = {"notification_sent": False}
        
        # Création notification (non-bloquant)
        try:
            logger.info("🔔 Création notification reset password", 
                       user_id=str(user_id), email=email)
            await self.notification_manager.notify_password_reset_requested(
                user_id=user_id,
                email=email
            )
            result["notification_sent"] = True
            logger.info("✅ Notification reset password créée", user_id=str(user_id))
        except Exception as e:
            logger.error("❌ Erreur notification reset password", 
                        user_id=str(user_id), error=str(e), exc_info=True)
        
        return result
    
    async def notify_and_email_password_changed(
        self,
        user_id: Union[UUID, str],
        email: str,
        first_name: str,
        last_name: str
    ) -> dict:
        """
        Notification après changement de mot de passe réussi
        
        Args:
            user_id: ID de l'utilisateur
            email: Email de l'utilisateur
            first_name: Prénom
            last_name: Nom
            
        Returns:
            dict: Statut {email_sent: bool, notification_sent: bool}
        """
        result = {"email_sent": False, "notification_sent": False}
        
        # 1. Envoi email de confirmation (sécurité)
        try:
            logger.info("📧 Envoi email changement password", 
                       user_id=str(user_id), email=email)
            
            subject = "🔐 Votre mot de passe a été modifié"
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .alert {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Mot de passe modifié</h1>
        </div>
        <div class="content">
            <p>Bonjour {first_name} {last_name},</p>
            
            <p>Votre mot de passe a été modifié avec succès.</p>
            
            <div class="alert">
                <strong>⚠️ Si vous n'êtes pas à l'origine de cette modification:</strong>
                <ul>
                    <li>Contactez immédiatement notre support</li>
                    <li>Changez votre mot de passe dès que possible</li>
                </ul>
            </div>
            
            <p>Date de modification: {self._get_current_datetime_formatted()}</p>
            
            <p>Cordialement,<br>L'équipe SEEG Recrutement</p>
        </div>
        <div class="footer">
            <p>&copy; 2025 SEEG - Société d'Énergie et d'Eau du Gabon</p>
        </div>
    </div>
</body>
</html>
            """
            
            await self.email_service.send_email(
                to=email,
                subject=subject,
                body=f"Votre mot de passe a été modifié. Si vous n'êtes pas à l'origine de cette action, contactez-nous immédiatement.",
                html_body=html_body
            )
            result["email_sent"] = True
            logger.info("✅ Email changement password envoyé", user_id=str(user_id))
        except Exception as e:
            logger.warning("⚠️ Erreur envoi email changement password", 
                          user_id=str(user_id), error=str(e))
        
        # 2. Création notification
        try:
            logger.info("🔔 Création notification changement password", 
                       user_id=str(user_id))
            await self.notification_manager.notify_password_changed(user_id=user_id)
            result["notification_sent"] = True
            logger.info("✅ Notification changement password créée", user_id=str(user_id))
        except Exception as e:
            logger.error("❌ Erreur notification changement password", 
                        user_id=str(user_id), error=str(e), exc_info=True)
        
        return result
    
    # ==================== CANDIDATURE ====================
    
    async def notify_and_email_application_submitted(
        self,
        user_id: Union[UUID, str],
        application_id: Union[UUID, str],
        candidate_email: str,
        candidate_name: str,
        job_title: str
    ) -> dict:
        """
        Envoyer email + notification après soumission de candidature
        
        Args:
            user_id: ID de l'utilisateur
            application_id: ID de la candidature
            candidate_email: Email du candidat
            candidate_name: Nom complet du candidat
            job_title: Titre du poste
            
        Returns:
            dict: Statut {email_sent: bool, notification_sent: bool}
        """
        result = {"email_sent": False, "notification_sent": False}
        
        # 1. Envoi email de confirmation
        try:
            logger.info("📧 Envoi email confirmation candidature", 
                       user_id=str(user_id), application_id=str(application_id))
            await self.email_service.send_application_confirmation(
                candidate_email=candidate_email,
                candidate_name=candidate_name,
                job_title=job_title,
                application_id=str(application_id)
            )
            result["email_sent"] = True
            logger.info("✅ Email confirmation candidature envoyé", 
                       application_id=str(application_id))
        except Exception as e:
            logger.warning("⚠️ Erreur envoi email confirmation candidature", 
                          application_id=str(application_id), error=str(e))
        
        # 2. Création notification
        try:
            logger.info("🔔 Création notification candidature", 
                       user_id=str(user_id), application_id=str(application_id))
            await self.notification_manager.notify_application_submitted(
                user_id=user_id,
                application_id=application_id,
                job_title=job_title
            )
            result["notification_sent"] = True
            logger.info("✅ Notification candidature créée", 
                       application_id=str(application_id))
        except Exception as e:
            logger.error("❌ Erreur notification candidature", 
                        application_id=str(application_id), error=str(e), exc_info=True)
        
        return result
    
    async def notify_application_draft_saved(
        self,
        user_id: Union[UUID, str],
        job_offer_id: Union[UUID, str],
        job_title: str
    ) -> dict:
        """
        Notification uniquement pour sauvegarde de brouillon (pas d'email nécessaire)
        
        Args:
            user_id: ID de l'utilisateur
            job_offer_id: ID de l'offre d'emploi
            job_title: Titre du poste
            
        Returns:
            dict: Statut {notification_sent: bool}
        """
        result = {"notification_sent": False}
        
        try:
            logger.info("🔔 Création notification brouillon", 
                       user_id=str(user_id), job_offer_id=str(job_offer_id))
            await self.notification_manager.notify_application_draft_saved(
                user_id=user_id,
                job_offer_id=job_offer_id,
                job_title=job_title
            )
            result["notification_sent"] = True
            logger.info("✅ Notification brouillon créée", user_id=str(user_id))
        except Exception as e:
            logger.error("❌ Erreur notification brouillon", 
                        user_id=str(user_id), error=str(e), exc_info=True)
        
        return result
    
    async def notify_and_email_application_status_changed(
        self,
        user_id: Union[UUID, str],
        application_id: Union[UUID, str],
        candidate_email: str,
        candidate_name: str,
        job_title: str,
        new_status: str
    ) -> dict:
        """
        Envoyer email + notification après changement de statut de candidature
        
        Args:
            user_id: ID de l'utilisateur
            application_id: ID de la candidature
            candidate_email: Email du candidat
            candidate_name: Nom du candidat
            job_title: Titre du poste
            new_status: Nouveau statut
            
        Returns:
            dict: Statut {email_sent: bool, notification_sent: bool}
        """
        result = {"email_sent": False, "notification_sent": False}
        
        # 1. Envoi email
        try:
            logger.info("📧 Envoi email changement statut candidature", 
                       application_id=str(application_id), status=new_status)
            await self.email_service.send_application_status_update(
                candidate_email=candidate_email,
                candidate_name=candidate_name,
                job_title=job_title,
                new_status=new_status,
                notes=None
            )
            result["email_sent"] = True
            logger.info("✅ Email changement statut envoyé", 
                       application_id=str(application_id))
        except Exception as e:
            logger.warning("⚠️ Erreur envoi email changement statut", 
                          application_id=str(application_id), error=str(e))
        
        # 2. Création notification
        try:
            logger.info("🔔 Création notification changement statut", 
                       application_id=str(application_id), status=new_status)
            await self.notification_manager.notify_application_status_changed(
                user_id=user_id,
                application_id=application_id,
                job_title=job_title,
                new_status=new_status
            )
            result["notification_sent"] = True
            logger.info("✅ Notification changement statut créée", 
                       application_id=str(application_id))
        except Exception as e:
            logger.error("❌ Erreur notification changement statut", 
                        application_id=str(application_id), error=str(e), exc_info=True)
        
        return result
    
    # ==================== ENTRETIENS ====================
    
    async def notify_and_email_interview_scheduled(
        self,
        candidate_id: Union[UUID, str],
        candidate_email: str,
        candidate_name: str,
        application_id: Union[UUID, str],
        job_title: str,
        interview_date: str,  # Format: "YYYY-MM-DD"
        interview_time: str,  # Format: "HH:MM:SS"
        interview_location: str,
        interviewer_name: str,
        notes: Optional[str] = None
    ) -> dict:
        """
        Envoyer email + notification après planification d'entretien
        
        Args:
            candidate_id: ID du candidat
            candidate_email: Email du candidat
            candidate_name: Nom du candidat
            application_id: ID de la candidature
            job_title: Titre du poste
            interview_date: Date (YYYY-MM-DD)
            interview_time: Heure (HH:MM:SS)
            interview_location: Lieu
            interviewer_name: Nom de l'interviewer
            notes: Notes additionnelles
            
        Returns:
            dict: Statut {email_sent: bool, notification_sent: bool}
        """
        result = {"email_sent": False, "notification_sent": False}
        
        # Formater la date et l'heure pour affichage
        from datetime import datetime
        try:
            dt = datetime.strptime(f"{interview_date} {interview_time}", "%Y-%m-%d %H:%M:%S")
            formatted_datetime = dt.strftime("%d/%m/%Y à %H:%M")
            day_name = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"][dt.weekday()]
        except Exception:
            formatted_datetime = f"{interview_date} à {interview_time}"
            day_name = ""
        
        # 1. Envoi email d'invitation détaillé
        try:
            logger.info("📧 Envoi email invitation entretien", 
                       candidate_id=str(candidate_id), 
                       application_id=str(application_id))
            
            subject = f"🎯 Invitation à un entretien - {job_title}"
            
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                line-height: 1.6; color: #333; background-color: #f5f5f5; }}
        .container {{ max-width: 650px; margin: 20px auto; background: white; 
                      border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); 
                   color: white; padding: 40px 30px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 28px; font-weight: 600; }}
        .content {{ padding: 40px 30px; }}
        .interview-card {{ background: #f8fafc; border-left: 4px solid #3b82f6; 
                           padding: 20px; margin: 25px 0; border-radius: 8px; }}
        .interview-detail {{ margin: 12px 0; padding: 10px 0; }}
        .interview-detail-label {{ font-weight: 600; color: #1e3a8a; 
                                   display: inline-block; width: 140px; }}
        .interview-detail-value {{ color: #334155; }}
        .important-note {{ background: #fef3c7; border-left: 4px solid #f59e0b; 
                           padding: 15px; margin: 20px 0; border-radius: 8px; }}
        .instructions {{ background: #e0f2fe; padding: 20px; margin: 20px 0; 
                        border-radius: 8px; border-left: 4px solid #0284c7; }}
        .instructions h3 {{ margin-top: 0; color: #0c4a6e; }}
        .instructions ul {{ margin: 10px 0; padding-left: 20px; }}
        .instructions li {{ margin: 8px 0; color: #334155; }}
        .footer {{ background: #f1f5f9; padding: 25px 30px; text-align: center; 
                   color: #64748b; font-size: 13px; }}
        .cta-button {{ display: inline-block; background: #3b82f6; color: white; 
                       padding: 12px 30px; text-decoration: none; border-radius: 6px; 
                       margin: 20px 0; font-weight: 600; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Invitation à un Entretien</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">SEEG - Recrutement</p>
        </div>
        
        <div class="content">
            <p>Bonjour <strong>{candidate_name}</strong>,</p>
            
            <p>Nous avons le plaisir de vous informer que votre candidature pour le poste de 
            <strong>{job_title}</strong> a retenu notre attention.</p>
            
            <p>Nous vous invitons à un entretien selon les modalités suivantes :</p>
            
            <div class="interview-card">
                <div class="interview-detail">
                    <span class="interview-detail-label">📅 Date :</span>
                    <span class="interview-detail-value"><strong>{day_name} {formatted_datetime}</strong></span>
                </div>
                <div class="interview-detail">
                    <span class="interview-detail-label">📍 Lieu :</span>
                    <span class="interview-detail-value">{interview_location}</span>
                </div>
                <div class="interview-detail">
                    <span class="interview-detail-label">👤 Interviewer :</span>
                    <span class="interview-detail-value">{interviewer_name}</span>
                </div>
                <div class="interview-detail">
                    <span class="interview-detail-label">⏱️ Durée estimée :</span>
                    <span class="interview-detail-value">1 heure</span>
                </div>
                {f'''<div class="interview-detail">
                    <span class="interview-detail-label">📝 Notes :</span>
                    <span class="interview-detail-value">{notes}</span>
                </div>''' if notes else ''}
            </div>
            
            <div class="important-note">
                <strong>⚠️ Important :</strong> Merci de confirmer votre présence en répondant à cet email 
                dans les 48 heures. En cas d'empêchement, contactez-nous au plus vite pour reprogrammer.
            </div>
            
            <div class="instructions">
                <h3>📋 Instructions pour l'entretien :</h3>
                <ul>
                    <li>✅ Apportez une pièce d'identité valide</li>
                    <li>✅ Arrivez 15 minutes en avance</li>
                    <li>✅ Préparez des questions sur le poste et l'entreprise</li>
                    <li>✅ Apportez vos documents originaux (diplômes, attestations)</li>
                    <li>✅ Habillez-vous de manière professionnelle</li>
                </ul>
            </div>
            
            <p>Nous vous souhaitons bonne chance pour cet entretien !</p>
            
            <p>Cordialement,<br>
            <strong>L'équipe Recrutement SEEG</strong><br>
            Société d'Énergie et d'Eau du Gabon</p>
        </div>
        
        <div class="footer">
            <p>&copy; 2025 SEEG - Société d'Énergie et d'Eau du Gabon</p>
            <p>Email automatique - Pour toute question, répondez directement à cet email</p>
        </div>
    </div>
</body>
</html>
            """
            
            await self.email_service.send_email(
                to=candidate_email,
                subject=subject,
                body=f"Invitation à un entretien pour {job_title} le {formatted_datetime}",
                html_body=html_body
            )
            result["email_sent"] = True
            logger.info("✅ Email invitation entretien envoyé", 
                       candidate_email=candidate_email)
        except Exception as e:
            logger.warning("⚠️ Erreur envoi email invitation entretien", 
                          candidate_email=candidate_email, error=str(e))
        
        # 2. Création notification
        try:
            logger.info("🔔 Création notification entretien", 
                       candidate_id=str(candidate_id))
            await self.notification_manager.notify_interview_scheduled(
                user_id=candidate_id,
                application_id=application_id,
                interview_date=formatted_datetime,
                interview_type="entretien",
                job_title=job_title
            )
            result["notification_sent"] = True
            logger.info("✅ Notification entretien créée", 
                       candidate_id=str(candidate_id))
        except Exception as e:
            logger.error("❌ Erreur notification entretien", 
                        candidate_id=str(candidate_id), error=str(e), exc_info=True)
        
        return result
    
    # ==================== MÉTHODES UTILITAIRES ====================
    
    def _get_current_datetime_formatted(self) -> str:
        """
        Obtenir la date et l'heure actuelles formatées
        
        Returns:
            str: Date et heure au format "JJ/MM/AAAA à HH:MM"
        """
        from datetime import datetime
        now = datetime.now()
        return now.strftime("%d/%m/%Y à %H:%M")

