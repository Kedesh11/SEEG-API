"""
Schémas Pydantic pour les notifications
=======================================
Architecture: Type-Safe + Système de notifications temps réel

Schémas principaux:
- NotificationBase/Response: Notification utilisateur
- NotificationListResponse: Liste paginée de notifications
- NotificationStatsResponse: Statistiques notifications
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from uuid import UUID

# ============================================================================
# CONSTANTES - Types de notifications et priorités
# ============================================================================

# Types de notifications
NOTIF_TYPE_APPLICATION = "application"          # Notification liée à une candidature
NOTIF_TYPE_INTERVIEW = "interview"              # Notification liée à un entretien
NOTIF_TYPE_EVALUATION = "evaluation"            # Notification liée à une évaluation
NOTIF_TYPE_SYSTEM = "system"                    # Notification système
NOTIF_TYPE_REMINDER = "reminder"                # Rappel
NOTIF_TYPE_JOB_OFFER = "job_offer"             # Nouvelle offre d'emploi
ALLOWED_NOTIF_TYPES = {
    NOTIF_TYPE_APPLICATION,
    NOTIF_TYPE_INTERVIEW,
    NOTIF_TYPE_EVALUATION,
    NOTIF_TYPE_SYSTEM,
    NOTIF_TYPE_REMINDER,
    NOTIF_TYPE_JOB_OFFER
}


class NotificationBase(BaseModel):
    """
    Schéma de base pour une notification.
    
    Utilisé pour informer les utilisateurs en temps réel des événements
    importants (candidature, entretien, évaluation, etc.).
    """
    title: str = Field(..., min_length=1, max_length=200, description="Titre de la notification")
    message: str = Field(..., min_length=1, description="Message détaillé de la notification")
    type: Optional[str] = Field(None, description=f"Type: {', '.join(ALLOWED_NOTIF_TYPES)}")
    link: Optional[str] = Field(None, description="Lien vers la ressource associée (URL)")
    read: bool = Field(False, description="Notification lue par l'utilisateur")


class NotificationCreate(NotificationBase):
    """
    Schéma pour créer une notification.
    """
    user_id: UUID = Field(..., description="ID de l'utilisateur destinataire")
    related_application_id: Optional[UUID] = Field(None, description="ID de la candidature liée (si applicable)")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "description": "Notification candidature soumise",
                    "value": {
                        "user_id": "550e8400-e29b-41d4-a716-446655440000",
                        "title": "Candidature soumise avec succès",
                        "message": "Votre candidature pour le poste 'Ingénieur DevOps' a été soumise avec succès.",
                        "type": "application",
                        "link": "/applications/724f8672-e3a4-4fa1-9856-06ac455bf518",
                        "related_application_id": "724f8672-e3a4-4fa1-9856-06ac455bf518",
                        "read": False
                    }
                },
                {
                    "description": "Notification entretien planifié",
                    "value": {
                        "user_id": "550e8400-e29b-41d4-a716-446655440000",
                        "title": "Entretien planifié",
                        "message": "Un entretien a été planifié pour le 25 octobre 2024 à 10h00.",
                        "type": "interview",
                        "link": "/interviews/abc-123",
                        "read": False
                    }
                }
            ]
        }
    }


class NotificationUpdate(BaseModel):
    """
    Schéma pour mettre à jour une notification.
    
    Principalement utilisé pour marquer une notification comme lue.
    """
    title: Optional[str] = Field(None, description="Nouveau titre")
    message: Optional[str] = Field(None, description="Nouveau message")
    type: Optional[str] = Field(None, description="Nouveau type")
    link: Optional[str] = Field(None, description="Nouveau lien")
    read: Optional[bool] = Field(None, description="Statut de lecture")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "read": True
            }
        }
    }


class NotificationResponse(NotificationBase):
    """
    Schéma de réponse pour une notification avec métadonnées.
    """
    id: int = Field(..., description="ID unique de la notification")
    user_id: UUID = Field(..., description="ID de l'utilisateur destinataire")
    related_application_id: Optional[UUID] = Field(None, description="ID de la candidature liée")
    created_at: datetime = Field(..., description="Date de création de la notification")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 42,
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Candidature soumise avec succès",
                "message": "Votre candidature pour 'Ingénieur DevOps' a été reçue.",
                "type": "application",
                "link": "/applications/724f8672-e3a4-4fa1-9856-06ac455bf518",
                "related_application_id": "724f8672-e3a4-4fa1-9856-06ac455bf518",
                "read": False,
                "created_at": "2024-10-17T15:30:00Z"
            }
        }
    }


class NotificationListResponse(BaseModel):
    """
    Schéma de réponse pour une liste paginée de notifications.
    """
    notifications: List[NotificationResponse] = Field(..., description="Liste des notifications")
    total: int = Field(..., description="Nombre total de notifications")
    page: int = Field(..., description="Numéro de page actuelle")
    per_page: int = Field(..., description="Nombre de notifications par page")
    total_pages: int = Field(..., description="Nombre total de pages")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "notifications": [
                    {
                        "id": 42,
                        "title": "Candidature soumise",
                        "message": "Votre candidature a été soumise",
                        "type": "application",
                        "read": False,
                        "created_at": "2024-10-17T15:30:00Z"
                    }
                ],
                "total": 10,
                "page": 1,
                "per_page": 20,
                "total_pages": 1
            }
        }
    }


class NotificationStatsResponse(BaseModel):
    """
    Schéma de réponse pour les statistiques des notifications.
    
    Fournit un aperçu rapide du nombre de notifications par type et statut.
    """
    total_notifications: int = Field(..., description="Nombre total de notifications")
    unread_count: int = Field(..., description="Nombre de notifications non lues")
    read_count: int = Field(..., description="Nombre de notifications lues")
    notifications_by_type: Dict[str, int] = Field(..., description="Répartition par type de notification")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total_notifications": 25,
                "unread_count": 5,
                "read_count": 20,
                "notifications_by_type": {
                    "application": 10,
                    "interview": 5,
                    "evaluation": 3,
                    "system": 7
                }
            }
        }
    }
