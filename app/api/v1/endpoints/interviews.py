"""
Endpoints pour la gestion des entretiens
Compatible avec InterviewCalendarModal.tsx
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.interview import InterviewService
from app.schemas.interview import (
    InterviewSlotCreate, InterviewSlotUpdate, InterviewSlotResponse,
    InterviewSlotListResponse, InterviewStatsResponse
)
from app.core.dependencies import get_current_user
from app.models.user import User
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError
import structlog

router = APIRouter()
logger = structlog.get_logger(__name__)


def safe_log(level: str, message: str, **kwargs):
    """Log avec gestion d'erreur pour Ã©viter les problÃ¨mes de handler."""
    try:
        getattr(logger, level)(message, **kwargs)
    except (TypeError, AttributeError):
        print(f"{level.upper()}: {message} - {kwargs}")


@router.post(
    "/slots",
    response_model=InterviewSlotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="CrÃ©er un crÃ©neau d'entretien",
    tags=["ðŸŽ¯ Entretiens"],
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "example": {
                        "date": "2025-10-15",
                        "time": "09:00:00",
                        "application_id": "00000000-0000-0000-0000-0000000000AA",
                        "candidate_name": "John Doe",
                        "job_title": "DÃ©veloppeur Full Stack",
                        "status": "scheduled",
                        "location": "Libreville",
                        "notes": "Entretien technique"
                    }
                }
            }
        },
        "responses": {
            "201": {
                "description": "CrÃ©neau crÃ©Ã© avec succÃ¨s",
                "content": {
                    "application/json": {
                        "example": {
                            "id": "uuid",
                            "date": "2025-10-15",
                            "time": "09:00:00",
                            "application_id": "uuid",
                            "candidate_name": "John Doe",
                            "job_title": "DÃ©veloppeur Full Stack",
                            "status": "scheduled",
                            "is_available": False,
                            "location": "Libreville",
                            "notes": "Entretien technique",
                            "created_at": "2025-10-02T10:00:00Z",
                            "updated_at": "2025-10-02T10:00:00Z"
                        }
                    }
                }
            },
            "404": {
                "description": "Candidature non trouvÃ©e"
            },
            "409": {
                "description": "CrÃ©neau dÃ©jÃ  occupÃ©",
                "content": {
                    "application/json": {
                        "example": {
                            "detail": "Le crÃ©neau 2025-10-15 Ã  09:00:00 est dÃ©jÃ  occupÃ©"
                        }
                    }
                }
            },
            "400": {
                "description": "Format de date/heure invalide"
            }
        }
    }
)
async def create_interview_slot(
    slot_data: InterviewSlotCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    CrÃ©er un nouveau crÃ©neau d'entretien
    
    **Validations** :
    - VÃ©rifier que le crÃ©neau n'existe pas dÃ©jÃ 
    - VÃ©rifier que le crÃ©neau n'est pas dÃ©jÃ  occupÃ©
    - Valider le format de la date (YYYY-MM-DD)
    - Valider le format de l'heure (HH:mm:ss)
    - VÃ©rifier que l'application_id existe
    
    **Si le crÃ©neau existe et est disponible** : Le mettre Ã  jour au lieu d'en crÃ©er un nouveau
    """
    try:
        interview_service = InterviewService(db)
        result = await interview_service.create_interview_slot(
            slot_data, str(current_user.id)
        )
        # Commit pour persister l'entretien
        await db.commit()
        
        safe_log("info", "CrÃ©neau d'entretien crÃ©Ã©", 
                slot_id=str(result.id) if hasattr(result, 'id') else "unknown",
                date=slot_data.date,
                time=slot_data.time,
                user_id=str(current_user.id))
        
        # 🔔 Envoyer email + notification au candidat (PATTERN UNIFIÉ)
        try:
            safe_log("debug", "🔍 Début envoi email + notification entretien", 
                    application_id=str(slot_data.application_id))
            
            from uuid import UUID as UUID_Type
            from app.services.notification_email_manager import NotificationEmailManager
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from app.models.application import Application
            
            safe_log("debug", "🔍 Imports réussis")
            
            # Récupérer les détails de la candidature avec eager loading
            stmt = (
                select(Application)
                .options(
                    selectinload(Application.candidate),
                    selectinload(Application.job_offer)
                )
                .where(Application.id == slot_data.application_id)
            )
            safe_log("debug", "🔍 Statement préparé")
            
            app_result = await db.execute(stmt)
            application = app_result.scalar_one_or_none()
            
            safe_log("debug", "🔍 Application récupérée", 
                    found=application is not None)
            
            if application:
                # Les relations sont déjà chargées avec selectinload
                safe_log("debug", "🔍 Extraction données candidat...")
                candidate_email = application.candidate.email
                candidate_full_name = f"{application.candidate.first_name} {application.candidate.last_name}"
                job_title = application.job_offer.title
                
                safe_log("debug", "🔍 Données extraites", 
                        candidate_email=str(candidate_email),
                        candidate_name=candidate_full_name,
                        job_title=str(job_title))
                
                # Nom de l'interviewer
                interviewer_name = f"{current_user.first_name} {current_user.last_name}" if hasattr(current_user, 'first_name') else "L'équipe RH SEEG"
                
                safe_log("debug", "🔍 Création NotificationEmailManager...")
                notif_email_manager = NotificationEmailManager(db)
                safe_log("debug", "✅ NotificationEmailManager créé")
                
                # Convertir les types
                safe_log("debug", "🔍 Conversion types UUID...")
                candidate_id_uuid = application.candidate_id if isinstance(application.candidate_id, UUID_Type) else UUID_Type(str(application.candidate_id))
                application_id_uuid = application.id if isinstance(application.id, UUID_Type) else UUID_Type(str(application.id))
                
                safe_log("debug", "🔍 Appel notify_and_email_interview_scheduled...",
                        candidate_id=str(candidate_id_uuid),
                        interview_date=slot_data.date,
                        interview_time=slot_data.time)
                
                notification_result = await notif_email_manager.notify_and_email_interview_scheduled(
                    candidate_id=candidate_id_uuid,
                    candidate_email=str(candidate_email),
                    candidate_name=candidate_full_name,
                    application_id=application_id_uuid,
                    job_title=str(job_title),
                    interview_date=slot_data.date,
                    interview_time=slot_data.time,
                    interview_location=slot_data.location or "À confirmer",
                    interviewer_name=interviewer_name,
                    notes=slot_data.notes
                )
                
                safe_log("debug", "🔍 Résultat notification_result", 
                        email_sent=notification_result.get("email_sent"),
                        notification_sent=notification_result.get("notification_sent"))
                
                safe_log("debug", "💾 Commit final...")
                await db.commit()
                safe_log("debug", "✅ Commit réussi")
                
                safe_log("info", "✅ Email + notification entretien envoyés",
                        application_id=str(slot_data.application_id),
                        email_sent=notification_result["email_sent"],
                        notification_sent=notification_result["notification_sent"])
            else:
                safe_log("warning", "Application non trouvée pour notification",
                        application_id=str(slot_data.application_id))
        except Exception as e:
            safe_log("error", "❌ ERREUR email/notification entretien", 
                    error=str(e),
                    error_type=type(e).__name__,
                    application_id=str(slot_data.application_id),
                    exc_info=True)
            import traceback
            traceback.print_exc()  # Afficher la trace complète pour debugging
            # TEMPORAIRE: Propager l'erreur pour debugging (normalement fail-safe)
            raise HTTPException(
                status_code=500,
                detail=f"Erreur email/notification: {str(e)}"
            )
        
        return result
    except NotFoundError as e:
        safe_log("warning", "Candidature non trouvÃ©e pour crÃ©ation crÃ©neau", error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        safe_log("warning", "CrÃ©neau dÃ©jÃ  occupÃ©", date=slot_data.date, time=slot_data.time, error=str(e))
        raise HTTPException(status_code=409, detail=str(e))
    except (ValidationError, ValueError) as e:
        safe_log("warning", "Erreur validation crÃ©ation crÃ©neau", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur crÃ©ation crÃ©neau entretien", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get(
    "/slots",
    response_model=InterviewSlotListResponse,
    summary="Lister les crÃ©neaux d'entretien (avec filtres)",
    tags=["ðŸŽ¯ Entretiens"],
    openapi_extra={
        "responses": {
            "200": {
                "description": "Liste des crÃ©neaux",
                "content": {
                    "application/json": {
                        "example": {
                            "data": [
                                {
                                    "id": "uuid",
                                    "date": "2025-10-15",
                                    "time": "09:00:00",
                                    "application_id": "uuid",
                                    "candidate_name": "John Doe",
                                    "job_title": "DÃ©veloppeur Full Stack",
                                    "status": "scheduled",
                                    "is_available": False,
                                    "location": "Libreville",
                                    "notes": "Entretien technique",
                                    "created_at": "2025-10-02T10:00:00Z",
                                    "updated_at": "2025-10-02T10:00:00Z"
                                }
                            ],
                            "total": 15,
                            "page": 1,
                            "per_page": 50,
                            "total_pages": 1
                        }
                    }
                }
            }
        }
    }
)
async def get_interview_slots(
    skip: int = Query(0, ge=0, description="Nombre d'Ã©lÃ©ments Ã  ignorer (pagination)"),
    limit: int = Query(50, ge=1, le=1000, description="Nombre maximum d'Ã©lÃ©ments Ã  retourner"),
    application_id: Optional[str] = Query(None, description="Filtrer par candidature"),
    status: Optional[str] = Query(None, description="Filtrer par statut (scheduled, completed, cancelled)"),
    is_available: Optional[bool] = Query(None, description="Filtrer par disponibilitÃ© (true=libre, false=occupÃ©)"),
    date_from: Optional[str] = Query(None, description="Date de dÃ©but (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    order: Optional[str] = Query(None, description="Ordre de tri (ex: date:asc,time:asc)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    RÃ©cupÃ©rer la liste des crÃ©neaux d'entretien
    
    **Filtres disponibles** :
    - `date_from` / `date_to` : PÃ©riode (YYYY-MM-DD)
    - `is_available` : true = crÃ©neaux libres, false = crÃ©neaux occupÃ©s
    - `application_id` : Filtrer par candidature
    - `status` : scheduled, completed, cancelled
    - `order` : Ordre de tri (date:asc,time:asc par dÃ©faut)
    
    **Comportements spÃ©cifiques** :
    - Retourne uniquement les crÃ©neaux occupÃ©s si `is_available=false`
    - Exclut les crÃ©neaux sans `application_id` si `is_available=false`
    - Tri par dÃ©faut : date ASC, puis time ASC
    """
    try:
        interview_service = InterviewService(db)
        results = await interview_service.get_interview_slots(
            skip=skip,
            limit=limit,
            application_id=application_id,
            status=status,
            is_available=is_available,
            date_from=date_from,
            date_to=date_to,
            order=order
        )
        safe_log("info", "CrÃ©neaux entretiens rÃ©cupÃ©rÃ©s", count=results.total if hasattr(results, 'total') else 0, user_id=str(current_user.id))
        return results
    except Exception as e:
        safe_log("error", "Erreur rÃ©cupÃ©ration crÃ©neaux", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get(
    "/slots/{slot_id}",
    response_model=InterviewSlotResponse,
    summary="RÃ©cupÃ©rer un crÃ©neau d'entretien par ID",
    tags=["ðŸŽ¯ Entretiens"],
    openapi_extra={
        "responses": {
            "200": {
                "description": "CrÃ©neau trouvÃ©",
                "content": {
                    "application/json": {
                        "example": {
                            "id": "uuid",
                            "date": "2025-10-15",
                            "time": "09:00:00",
                            "application_id": "uuid",
                            "candidate_name": "John Doe",
                            "status": "scheduled"
                        }
                    }
                }
            },
            "404": {
                "description": "CrÃ©neau non trouvÃ©"
            }
        }
    }
)
async def get_interview_slot(
    slot_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    RÃ©cupÃ©rer un crÃ©neau d'entretien par son ID
    """
    try:
        interview_service = InterviewService(db)
        result = await interview_service.get_interview_slot(slot_id)
        safe_log("info", "CrÃ©neau entretien rÃ©cupÃ©rÃ©", slot_id=slot_id)
        return result
    except NotFoundError as e:
        safe_log("warning", "CrÃ©neau non trouvÃ©", slot_id=slot_id)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur rÃ©cupÃ©ration crÃ©neau", slot_id=slot_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.put(
    "/slots/{slot_id}",
    response_model=InterviewSlotResponse,
    summary="Mettre Ã  jour un crÃ©neau d'entretien",
    tags=["ðŸŽ¯ Entretiens"],
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "example": {
                        "date": "2025-10-16",
                        "time": "10:00:00",
                        "status": "scheduled",
                        "notes": "Entretien reportÃ©"
                    }
                }
            }
        },
        "responses": {
            "200": {
                "description": "CrÃ©neau mis Ã  jour",
                "content": {
                    "application/json": {
                        "example": {
                            "id": "uuid",
                            "date": "2025-10-16",
                            "time": "10:00:00",
                            "status": "scheduled"
                        }
                    }
                }
            },
            "404": {
                "description": "CrÃ©neau non trouvÃ©"
            },
            "409": {
                "description": "Nouveau crÃ©neau dÃ©jÃ  occupÃ©",
                "content": {
                    "application/json": {
                        "example": {
                            "detail": "Le crÃ©neau 2025-10-16 Ã  10:00:00 est dÃ©jÃ  occupÃ© par une autre candidature"
                        }
                    }
                }
            }
        }
    }
)
async def update_interview_slot(
    slot_id: str,
    slot_data: InterviewSlotUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mettre Ã  jour un crÃ©neau d'entretien
    
    **Logique complexe pour changement de date/heure** :
    
    Lorsque la **date** ou **l'heure** change :
    1. LibÃ©rer l'ancien crÃ©neau (marquer comme disponible)
    2. VÃ©rifier si le nouveau crÃ©neau existe
    3. Si disponible, l'occuper ; sinon crÃ©er un nouveau crÃ©neau
    
    **Tous les champs sont optionnels** :
    - `date` : YYYY-MM-DD
    - `time` : HH:mm:ss
    - `application_id` : Changer la candidature liÃ©e
    - `candidate_name`
    - `job_title`
    - `status` : scheduled, completed, cancelled
    - `location`
    - `notes`
    """
    try:
        interview_service = InterviewService(db)
        result = await interview_service.update_interview_slot(
            slot_id, slot_data, str(current_user.id)
        )
        safe_log("info", "CrÃ©neau d'entretien mis Ã  jour", slot_id=slot_id, user_id=str(current_user.id))
        return result
    except NotFoundError as e:
        safe_log("warning", "CrÃ©neau non trouvÃ© pour MAJ", slot_id=slot_id)
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        safe_log("warning", "Erreur logique mÃ©tier MAJ crÃ©neau", slot_id=slot_id, error=str(e))
        raise HTTPException(status_code=409, detail=str(e))
    except (ValidationError, ValueError) as e:
        safe_log("warning", "Erreur validation MAJ crÃ©neau", slot_id=slot_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur MAJ crÃ©neau", slot_id=slot_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.delete(
    "/slots/{slot_id}",
    status_code=status.HTTP_200_OK,
    summary="Annuler un crÃ©neau d'entretien (soft delete)",
    tags=["ðŸŽ¯ Entretiens"],
    openapi_extra={
        "responses": {
            "200": {
                "description": "Entretien annulÃ© avec succÃ¨s",
                "content": {
                    "application/json": {
                        "example": {
                            "message": "Entretien annulÃ© avec succÃ¨s",
                            "slot_id": "uuid"
                        }
                    }
                }
            },
            "404": {
                "description": "CrÃ©neau non trouvÃ©"
            }
        }
    }
)
async def delete_interview_slot(
    slot_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Annuler un crÃ©neau d'entretien (soft delete)
    
    **Logique** :
    - Ne supprime pas physiquement le crÃ©neau
    - Marque le statut comme "cancelled"
    - LibÃ¨re le crÃ©neau (`is_available = true`)
    - Dissocie la candidature (`application_id = null`)
    - Conserve les donnÃ©es pour l'historique
    """
    try:
        interview_service = InterviewService(db)
        await interview_service.delete_interview_slot(slot_id, str(current_user.id))
        safe_log("info", "CrÃ©neau d'entretien annulÃ©", slot_id=slot_id, user_id=str(current_user.id))
        return {
            "message": "Entretien annulÃ© avec succÃ¨s",
            "slot_id": slot_id
        }
    except NotFoundError as e:
        safe_log("warning", "CrÃ©neau non trouvÃ© pour annulation", slot_id=slot_id)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur annulation crÃ©neau", slot_id=slot_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get(
    "/stats/overview",
    response_model=InterviewStatsResponse,
    summary="Statistiques globales des entretiens",
    tags=["ðŸŽ¯ Entretiens"],
    openapi_extra={
        "responses": {
            "200": {
                "content": {
                    "application/json": {
                        "example": {
                            "total_interviews": 120,
                            "scheduled_interviews": 45,
                            "completed_interviews": 60,
                            "cancelled_interviews": 15,
                            "interviews_by_status": {
                                "scheduled": 45,
                                "completed": 60,
                                "cancelled": 15
                            }
                        }
                    }
                }
            }
        }
    }
)
async def get_interview_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    RÃ©cupÃ©rer les statistiques des entretiens
    
    Retourne:
    - Nombre total d'entretiens
    - RÃ©partition par statut
    - Statistiques globales
    """
    try:
        interview_service = InterviewService(db)
        stats = await interview_service.get_interview_statistics()
        safe_log("info", "Statistiques entretiens rÃ©cupÃ©rÃ©es", user_id=str(current_user.id))
        return stats
    except Exception as e:
        safe_log("error", "Erreur rÃ©cupÃ©ration statistiques entretiens", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")
