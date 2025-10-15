"""
Logger spécialisé pour les événements métier
Permet un suivi précis des actions importantes dans l'application

Principes:
- Traçabilité: Tous les événements métier sont tracés
- Auditabilité: Format standardisé pour l'audit
- Analytics: Données structurées pour l'analyse
- Compliance: Respect des exigences réglementaires
"""
import structlog
from typing import Any, Dict, Optional
from uuid import UUID
from datetime import datetime
from enum import Enum

logger = structlog.get_logger(__name__)


class EventType(Enum):
    """Types d'événements métier standardisés"""
    # Utilisateurs
    USER_REGISTERED = "user.registered"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_PASSWORD_CHANGED = "user.password_changed"
    USER_PASSWORD_RESET_REQUESTED = "user.password_reset_requested"
    USER_EMAIL_VERIFIED = "user.email_verified"
    
    # Candidatures
    APPLICATION_CREATED = "application.created"
    APPLICATION_SUBMITTED = "application.submitted"
    APPLICATION_UPDATED = "application.updated"
    APPLICATION_WITHDRAWN = "application.withdrawn"
    APPLICATION_STATUS_CHANGED = "application.status_changed"
    APPLICATION_DRAFT_SAVED = "application.draft_saved"
    APPLICATION_DOCUMENT_UPLOADED = "application.document_uploaded"
    
    # Offres d'emploi
    JOB_OFFER_CREATED = "job_offer.created"
    JOB_OFFER_UPDATED = "job_offer.updated"
    JOB_OFFER_PUBLISHED = "job_offer.published"
    JOB_OFFER_CLOSED = "job_offer.closed"
    JOB_OFFER_DELETED = "job_offer.deleted"
    
    # Entretiens
    INTERVIEW_SCHEDULED = "interview.scheduled"
    INTERVIEW_RESCHEDULED = "interview.rescheduled"
    INTERVIEW_CANCELLED = "interview.cancelled"
    INTERVIEW_COMPLETED = "interview.completed"
    
    # Évaluations
    EVALUATION_CREATED = "evaluation.created"
    EVALUATION_UPDATED = "evaluation.updated"
    EVALUATION_SUBMITTED = "evaluation.submitted"
    
    # Notifications
    NOTIFICATION_SENT = "notification.sent"
    EMAIL_SENT = "email.sent"
    EMAIL_FAILED = "email.failed"
    
    # Sécurité
    ACCESS_DENIED = "security.access_denied"
    INVALID_TOKEN = "security.invalid_token"
    RATE_LIMIT_EXCEEDED = "security.rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "security.suspicious_activity"


class BusinessLogger:
    """
    Logger spécialisé pour les événements métier
    
    Usage:
        business_logger = BusinessLogger()
        business_logger.log_user_registered(
            user_id="123",
            email="user@example.com",
            role="candidate"
        )
    """
    
    def __init__(self):
        self.logger = structlog.get_logger("business")
    
    def _log_event(
        self,
        event_type: EventType,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        level: str = "info"
    ):
        """
        Logger un événement métier de manière standardisée
        
        Args:
            event_type: Type d'événement
            entity_id: ID de l'entité concernée
            user_id: ID de l'utilisateur qui a déclenché l'événement
            details: Détails additionnels
            level: Niveau de log (info, warning, error)
        """
        event_data = {
            "event_type": event_type.value,
            "entity_id": entity_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "category": "business_event"
        }
        
        if details:
            event_data["details"] = details
        
        # Emoji selon le type d'événement
        emoji = self._get_event_emoji(event_type)
        message = f"{emoji} {event_type.value}"
        
        getattr(self.logger, level)(message, **event_data)
    
    def _get_event_emoji(self, event_type: EventType) -> str:
        """Obtenir l'emoji approprié pour le type d'événement"""
        emoji_map = {
            # Utilisateurs
            "user.registered": "👤➕",
            "user.login": "🔐",
            "user.logout": "👋",
            "user.updated": "👤✏️",
            "user.deleted": "👤❌",
            "user.password_changed": "🔐✅",
            "user.password_reset_requested": "🔐🔄",
            "user.email_verified": "✉️✅",
            
            # Candidatures
            "application.created": "📝➕",
            "application.submitted": "📨",
            "application.updated": "📝✏️",
            "application.withdrawn": "📝❌",
            "application.status_changed": "📝🔄",
            "application.draft_saved": "💾",
            "application.document_uploaded": "📄⬆️",
            
            # Offres
            "job_offer.created": "💼➕",
            "job_offer.updated": "💼✏️",
            "job_offer.published": "💼📢",
            "job_offer.closed": "💼🔒",
            "job_offer.deleted": "💼❌",
            
            # Entretiens
            "interview.scheduled": "📅➕",
            "interview.rescheduled": "📅🔄",
            "interview.cancelled": "📅❌",
            "interview.completed": "📅✅",
            
            # Évaluations
            "evaluation.created": "📊➕",
            "evaluation.updated": "📊✏️",
            "evaluation.submitted": "📊📤",
            
            # Notifications
            "notification.sent": "🔔",
            "email.sent": "📧",
            "email.failed": "📧❌",
            
            # Sécurité
            "security.access_denied": "🚫",
            "security.invalid_token": "🔐❌",
            "security.rate_limit_exceeded": "🚦",
            "security.suspicious_activity": "⚠️🔍"
        }
        
        return emoji_map.get(event_type.value, "📌")
    
    # ==================== MÉTHODES UTILISATEURS ====================
    
    def log_user_registered(
        self,
        user_id: str,
        email: str,
        role: str,
        **kwargs
    ):
        """Logger l'inscription d'un utilisateur"""
        self._log_event(
            EventType.USER_REGISTERED,
            entity_id=user_id,
            user_id=user_id,
            details={"email": email, "role": role, **kwargs}
        )
    
    def log_user_login(
        self,
        user_id: str,
        email: str,
        ip_address: Optional[str] = None,
        **kwargs
    ):
        """Logger une connexion réussie"""
        self._log_event(
            EventType.USER_LOGIN,
            entity_id=user_id,
            user_id=user_id,
            details={"email": email, "ip_address": ip_address, **kwargs}
        )
    
    def log_user_password_changed(
        self,
        user_id: str,
        changed_by: str,
        **kwargs
    ):
        """Logger un changement de mot de passe"""
        self._log_event(
            EventType.USER_PASSWORD_CHANGED,
            entity_id=user_id,
            user_id=changed_by,
            details={"target_user_id": user_id, **kwargs}
        )
    
    # ==================== MÉTHODES CANDIDATURES ====================
    
    def log_application_submitted(
        self,
        application_id: str,
        candidate_id: str,
        job_offer_id: str,
        job_title: str,
        **kwargs
    ):
        """Logger la soumission d'une candidature"""
        self._log_event(
            EventType.APPLICATION_SUBMITTED,
            entity_id=application_id,
            user_id=candidate_id,
            details={
                "job_offer_id": job_offer_id,
                "job_title": job_title,
                **kwargs
            }
        )
    
    def log_application_status_changed(
        self,
        application_id: str,
        candidate_id: str,
        old_status: str,
        new_status: str,
        changed_by: str,
        **kwargs
    ):
        """Logger un changement de statut de candidature"""
        self._log_event(
            EventType.APPLICATION_STATUS_CHANGED,
            entity_id=application_id,
            user_id=changed_by,
            details={
                "candidate_id": candidate_id,
                "old_status": old_status,
                "new_status": new_status,
                **kwargs
            }
        )
    
    def log_application_draft_saved(
        self,
        user_id: str,
        job_offer_id: str,
        **kwargs
    ):
        """Logger la sauvegarde d'un brouillon"""
        self._log_event(
            EventType.APPLICATION_DRAFT_SAVED,
            entity_id=f"{user_id}_{job_offer_id}",
            user_id=user_id,
            details={"job_offer_id": job_offer_id, **kwargs}
        )
    
    def log_document_uploaded(
        self,
        application_id: str,
        document_id: str,
        document_type: str,
        user_id: str,
        **kwargs
    ):
        """Logger l'upload d'un document"""
        self._log_event(
            EventType.APPLICATION_DOCUMENT_UPLOADED,
            entity_id=document_id,
            user_id=user_id,
            details={
                "application_id": application_id,
                "document_type": document_type,
                **kwargs
            }
        )
    
    # ==================== MÉTHODES OFFRES D'EMPLOI ====================
    
    def log_job_offer_created(
        self,
        job_offer_id: str,
        title: str,
        created_by: str,
        **kwargs
    ):
        """Logger la création d'une offre d'emploi"""
        self._log_event(
            EventType.JOB_OFFER_CREATED,
            entity_id=job_offer_id,
            user_id=created_by,
            details={"title": title, **kwargs}
        )
    
    def log_job_offer_published(
        self,
        job_offer_id: str,
        title: str,
        published_by: str,
        **kwargs
    ):
        """Logger la publication d'une offre"""
        self._log_event(
            EventType.JOB_OFFER_PUBLISHED,
            entity_id=job_offer_id,
            user_id=published_by,
            details={"title": title, **kwargs}
        )
    
    # ==================== MÉTHODES NOTIFICATIONS ====================
    
    def log_notification_sent(
        self,
        notification_id: str,
        user_id: str,
        notification_type: str,
        channel: str = "in_app",
        **kwargs
    ):
        """Logger l'envoi d'une notification"""
        self._log_event(
            EventType.NOTIFICATION_SENT,
            entity_id=notification_id,
            user_id=user_id,
            details={
                "notification_type": notification_type,
                "channel": channel,
                **kwargs
            }
        )
    
    def log_email_sent(
        self,
        recipient: str,
        subject: str,
        email_type: str,
        **kwargs
    ):
        """Logger l'envoi d'un email"""
        self._log_event(
            EventType.EMAIL_SENT,
            details={
                "recipient": recipient,
                "subject": subject,
                "email_type": email_type,
                **kwargs
            }
        )
    
    def log_email_failed(
        self,
        recipient: str,
        subject: str,
        error: str,
        **kwargs
    ):
        """Logger l'échec d'envoi d'un email"""
        self._log_event(
            EventType.EMAIL_FAILED,
            details={
                "recipient": recipient,
                "subject": subject,
                "error": error,
                **kwargs
            },
            level="error"
        )
    
    # ==================== MÉTHODES SÉCURITÉ ====================
    
    def log_access_denied(
        self,
        user_id: Optional[str],
        resource: str,
        action: str,
        reason: str,
        **kwargs
    ):
        """Logger un refus d'accès"""
        self._log_event(
            EventType.ACCESS_DENIED,
            user_id=user_id,
            details={
                "resource": resource,
                "action": action,
                "reason": reason,
                **kwargs
            },
            level="warning"
        )
    
    def log_suspicious_activity(
        self,
        user_id: Optional[str],
        activity_type: str,
        details: Dict[str, Any],
        **kwargs
    ):
        """Logger une activité suspecte"""
        self._log_event(
            EventType.SUSPICIOUS_ACTIVITY,
            user_id=user_id,
            details={
                "activity_type": activity_type,
                **details,
                **kwargs
            },
            level="warning"
        )


# Instance globale pour faciliter l'utilisation
business_logger = BusinessLogger()

