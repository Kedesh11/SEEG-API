"""
Gestionnaire de notifications automatiques pour toutes les actions utilisateur
"""
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from uuid import UUID
import structlog

from app.schemas.notification import NotificationCreate
from app.services.notification import NotificationService

logger = structlog.get_logger(__name__)


class NotificationManager:
    """
    Gestionnaire centralisé pour créer des notifications automatiques
    pour toutes les actions utilisateur importantes
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.notification_service = NotificationService(db)
    
    # ==================== NOTIFICATIONS AUTHENTIFICATION ====================
    
    async def notify_user_registered(self, user_id: UUID, email: str) -> None:
        """Notification après inscription réussie"""
        try:
            notification_data = NotificationCreate(
                user_id=str(user_id),
                title="Bienvenue sur SEEG Recrutement ! 🎉",
                message=f"Votre compte a été créé avec succès avec l'email {email}. Vous pouvez maintenant postuler à nos offres d'emploi.",
                type="registration",
                link="/profile"
            )
            await self.notification_service.create_notification(notification_data)
            logger.info("✅ Notification inscription créée", user_id=str(user_id))
        except Exception as e:
            logger.error("❌ Erreur création notification inscription", user_id=str(user_id), error=str(e))
    
    async def notify_password_reset_requested(self, user_id: UUID, email: str) -> None:
        """Notification après demande de réinitialisation de mot de passe"""
        try:
            notification_data = NotificationCreate(
                user_id=str(user_id),
                title="Demande de réinitialisation de mot de passe 🔐",
                message=f"Une demande de réinitialisation de mot de passe a été envoyée à {email}. Vérifiez votre boîte mail.",
                type="password_reset",
                link=None
            )
            await self.notification_service.create_notification(notification_data)
            logger.info("✅ Notification reset password créée", user_id=str(user_id))
        except Exception as e:
            logger.error("❌ Erreur notification reset password", user_id=str(user_id), error=str(e))
    
    async def notify_password_changed(self, user_id: UUID) -> None:
        """Notification après changement de mot de passe"""
        try:
            notification_data = NotificationCreate(
                user_id=str(user_id),
                title="Mot de passe modifié avec succès ✅",
                message="Votre mot de passe a été modifié avec succès. Si vous n'êtes pas à l'origine de cette action, contactez-nous immédiatement.",
                type="password_changed",
                link="/profile/security"
            )
            await self.notification_service.create_notification(notification_data)
            logger.info("✅ Notification changement password créée", user_id=str(user_id))
        except Exception as e:
            logger.error("❌ Erreur notification password changed", user_id=str(user_id), error=str(e))
    
    async def notify_email_verified(self, user_id: UUID) -> None:
        """Notification après vérification d'email"""
        try:
            notification_data = NotificationCreate(
                user_id=str(user_id),
                title="Email vérifié avec succès ✅",
                message="Votre adresse email a été vérifiée. Vous avez maintenant accès à toutes les fonctionnalités de la plateforme.",
                type="email_verified",
                link="/profile"
            )
            await self.notification_service.create_notification(notification_data)
            logger.info("✅ Notification email vérifié créée", user_id=str(user_id))
        except Exception as e:
            logger.error("❌ Erreur notification email verified", user_id=str(user_id), error=str(e))
    
    # ==================== NOTIFICATIONS CANDIDATURES ====================
    
    async def notify_application_submitted(
        self, 
        user_id: UUID, 
        application_id: UUID,
        job_title: str
    ) -> None:
        """Notification après soumission d'une candidature"""
        try:
            notification_data = NotificationCreate(
                user_id=str(user_id),
                related_application_id=str(application_id),
                title="Candidature soumise avec succès ! 🎯",
                message=f"Votre candidature pour le poste '{job_title}' a été soumise avec succès. Nous examinerons votre dossier dans les plus brefs délais.",
                type="application_submitted",
                link=f"/applications/{application_id}"
            )
            await self.notification_service.create_notification(notification_data)
            logger.info("✅ Notification candidature soumise créée", user_id=str(user_id), application_id=str(application_id))
        except Exception as e:
            logger.error("❌ Erreur notification application submitted", user_id=str(user_id), error=str(e))
    
    async def notify_application_draft_saved(
        self,
        user_id: UUID,
        job_offer_id: UUID,
        job_title: str
    ) -> None:
        """Notification après sauvegarde d'un brouillon"""
        try:
            notification_data = NotificationCreate(
                user_id=str(user_id),
                title="Brouillon sauvegardé 💾",
                message=f"Votre brouillon pour le poste '{job_title}' a été sauvegardé. Vous pouvez le reprendre à tout moment.",
                type="draft_saved",
                link=f"/jobs/{job_offer_id}/apply"
            )
            await self.notification_service.create_notification(notification_data)
            logger.info("✅ Notification brouillon sauvegardé créée", user_id=str(user_id))
        except Exception as e:
            logger.error("❌ Erreur notification draft saved", user_id=str(user_id), error=str(e))
    
    async def notify_application_status_changed(
        self,
        user_id: UUID,
        application_id: UUID,
        job_title: str,
        new_status: str
    ) -> None:
        """Notification après changement de statut de candidature"""
        try:
            status_messages = {
                "pending": "Votre candidature est en cours d'examen 🔍",
                "reviewing": "Votre candidature est en cours d'examen approfondi 📋",
                "shortlisted": "Félicitations ! Votre profil a été présélectionné 🌟",
                "interview": "Vous avez été convoqué(e) à un entretien ! 🎯",
                "offer": "Félicitations ! Une offre vous a été faite 🎉",
                "hired": "Félicitations ! Vous avez été recruté(e) 🎊",
                "rejected": "Votre candidature n'a pas été retenue cette fois 😔",
                "withdrawn": "Votre candidature a été retirée ❌"
            }
            
            message = status_messages.get(
                new_status.lower(),
                f"Le statut de votre candidature pour '{job_title}' a été mis à jour: {new_status}"
            )
            
            notification_data = NotificationCreate(
                user_id=str(user_id),
                related_application_id=str(application_id),
                title=f"Mise à jour de candidature - {job_title}",
                message=message,
                type="application_status_changed",
                link=f"/applications/{application_id}"
            )
            await self.notification_service.create_notification(notification_data)
            logger.info("✅ Notification statut candidature créée", user_id=str(user_id), status=new_status)
        except Exception as e:
            logger.error("❌ Erreur notification status changed", user_id=str(user_id), error=str(e))
    
    async def notify_application_document_uploaded(
        self,
        user_id: UUID,
        application_id: UUID,
        document_type: str
    ) -> None:
        """Notification après téléchargement d'un document"""
        try:
            notification_data = NotificationCreate(
                user_id=str(user_id),
                related_application_id=str(application_id),
                title="Document téléchargé avec succès 📄",
                message=f"Votre document ({document_type}) a été téléchargé et ajouté à votre candidature.",
                type="document_uploaded",
                link=f"/applications/{application_id}"
            )
            await self.notification_service.create_notification(notification_data)
            logger.info("✅ Notification document uploaded créée", user_id=str(user_id))
        except Exception as e:
            logger.error("❌ Erreur notification document uploaded", user_id=str(user_id), error=str(e))
    
    # ==================== NOTIFICATIONS ENTRETIENS ====================
    
    async def notify_interview_scheduled(
        self,
        user_id: UUID,
        application_id: UUID,
        interview_date: str,
        interview_type: str,
        job_title: str
    ) -> None:
        """Notification après planification d'un entretien"""
        try:
            notification_data = NotificationCreate(
                user_id=str(user_id),
                related_application_id=str(application_id),
                title="Entretien planifié ! 📅",
                message=f"Un entretien {interview_type} a été planifié pour le poste '{job_title}' le {interview_date}. Consultez les détails.",
                type="interview_scheduled",
                link=f"/applications/{application_id}/interviews"
            )
            await self.notification_service.create_notification(notification_data)
            logger.info("✅ Notification entretien planifié créée", user_id=str(user_id))
        except Exception as e:
            logger.error("❌ Erreur notification interview scheduled", user_id=str(user_id), error=str(e))
    
    async def notify_interview_reminder(
        self,
        user_id: UUID,
        application_id: UUID,
        interview_date: str,
        job_title: str
    ) -> None:
        """Notification rappel d'entretien (24h avant)"""
        try:
            notification_data = NotificationCreate(
                user_id=str(user_id),
                related_application_id=str(application_id),
                title="Rappel : Entretien demain ! ⏰",
                message=f"Rappel : votre entretien pour '{job_title}' est prévu demain ({interview_date}). Bonne préparation !",
                type="interview_reminder",
                link=f"/applications/{application_id}/interviews"
            )
            await self.notification_service.create_notification(notification_data)
            logger.info("✅ Notification rappel entretien créée", user_id=str(user_id))
        except Exception as e:
            logger.error("❌ Erreur notification interview reminder", user_id=str(user_id), error=str(e))
    
    async def notify_interview_cancelled(
        self,
        user_id: UUID,
        application_id: UUID,
        job_title: str
    ) -> None:
        """Notification après annulation d'un entretien"""
        try:
            notification_data = NotificationCreate(
                user_id=str(user_id),
                related_application_id=str(application_id),
                title="Entretien annulé ❌",
                message=f"L'entretien pour le poste '{job_title}' a été annulé. Vous serez contacté(e) pour une nouvelle date.",
                type="interview_cancelled",
                link=f"/applications/{application_id}"
            )
            await self.notification_service.create_notification(notification_data)
            logger.info("✅ Notification entretien annulé créée", user_id=str(user_id))
        except Exception as e:
            logger.error("❌ Erreur notification interview cancelled", user_id=str(user_id), error=str(e))
    
    # ==================== NOTIFICATIONS ÉVALUATIONS ====================
    
    async def notify_evaluation_completed(
        self,
        user_id: UUID,
        application_id: UUID,
        job_title: str
    ) -> None:
        """Notification après évaluation de candidature"""
        try:
            notification_data = NotificationCreate(
                user_id=str(user_id),
                related_application_id=str(application_id),
                title="Évaluation complétée 📊",
                message=f"L'évaluation de votre candidature pour '{job_title}' a été complétée. Consultez les résultats.",
                type="evaluation_completed",
                link=f"/applications/{application_id}/evaluation"
            )
            await self.notification_service.create_notification(notification_data)
            logger.info("✅ Notification évaluation complétée créée", user_id=str(user_id))
        except Exception as e:
            logger.error("❌ Erreur notification evaluation completed", user_id=str(user_id), error=str(e))
    
    # ==================== NOTIFICATIONS OFFRES D'EMPLOI ====================
    
    async def notify_new_job_matching_profile(
        self,
        user_id: UUID,
        job_offer_id: UUID,
        job_title: str,
        match_score: Optional[int] = None
    ) -> None:
        """Notification pour une nouvelle offre correspondant au profil"""
        try:
            match_text = f" (compatibilité: {match_score}%)" if match_score else ""
            notification_data = NotificationCreate(
                user_id=str(user_id),
                title="Nouvelle offre correspondant à votre profil ! 💼",
                message=f"Une nouvelle offre '{job_title}' correspond à votre profil{match_text}. Postulez dès maintenant !",
                type="job_match",
                link=f"/jobs/{job_offer_id}"
            )
            await self.notification_service.create_notification(notification_data)
            logger.info("✅ Notification nouvelle offre créée", user_id=str(user_id))
        except Exception as e:
            logger.error("❌ Erreur notification new job", user_id=str(user_id), error=str(e))
    
    async def notify_job_deadline_approaching(
        self,
        user_id: UUID,
        job_offer_id: UUID,
        job_title: str,
        days_remaining: int
    ) -> None:
        """Notification de rappel avant clôture d'une offre"""
        try:
            notification_data = NotificationCreate(
                user_id=str(user_id),
                title=f"Date limite proche : {job_title} ⏳",
                message=f"Il ne reste que {days_remaining} jour(s) pour postuler au poste '{job_title}'. Ne manquez pas cette opportunité !",
                type="job_deadline",
                link=f"/jobs/{job_offer_id}"
            )
            await self.notification_service.create_notification(notification_data)
            logger.info("✅ Notification deadline job créée", user_id=str(user_id))
        except Exception as e:
            logger.error("❌ Erreur notification job deadline", user_id=str(user_id), error=str(e))
    
    # ==================== NOTIFICATIONS PROFIL ====================
    
    async def notify_profile_completed(self, user_id: UUID, completion_rate: int) -> None:
        """Notification après complétion du profil"""
        try:
            notification_data = NotificationCreate(
                user_id=str(user_id),
                title="Profil complété ! 🎉",
                message=f"Félicitations ! Votre profil est maintenant complet à {completion_rate}%. Vous pouvez commencer à postuler.",
                type="profile_completed",
                link="/profile"
            )
            await self.notification_service.create_notification(notification_data)
            logger.info("✅ Notification profil complété créée", user_id=str(user_id))
        except Exception as e:
            logger.error("❌ Erreur notification profile completed", user_id=str(user_id), error=str(e))
    
    async def notify_profile_updated(self, user_id: UUID) -> None:
        """Notification après mise à jour du profil"""
        try:
            notification_data = NotificationCreate(
                user_id=str(user_id),
                title="Profil mis à jour ✅",
                message="Votre profil a été mis à jour avec succès. Les recruteurs verront les dernières modifications.",
                type="profile_updated",
                link="/profile"
            )
            await self.notification_service.create_notification(notification_data)
            logger.info("✅ Notification profil mis à jour créée", user_id=str(user_id))
        except Exception as e:
            logger.error("❌ Erreur notification profile updated", user_id=str(user_id), error=str(e))
    
    # ==================== NOTIFICATIONS SYSTÈME ====================
    
    async def notify_system_message(
        self,
        user_id: UUID,
        title: str,
        message: str,
        link: Optional[str] = None
    ) -> None:
        """Notification système générique"""
        try:
            notification_data = NotificationCreate(
                user_id=str(user_id),
                title=title,
                message=message,
                type="system",
                link=link
            )
            await self.notification_service.create_notification(notification_data)
            logger.info("✅ Notification système créée", user_id=str(user_id))
        except Exception as e:
            logger.error("❌ Erreur notification system", user_id=str(user_id), error=str(e))
