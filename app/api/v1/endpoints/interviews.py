"""
Endpoints pour la gestion des entretiens
Compatible avec InterviewCalendarModal.tsx
"""
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.database import get_db
from app.services.interview import InterviewService
from app.schemas.interview import (
    InterviewSlotCreate, InterviewSlotUpdate, InterviewSlotResponse,
    InterviewSlotListResponse, InterviewStatsResponse
)
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError
import structlog

router = APIRouter()
logger = structlog.get_logger(__name__)


def safe_log(level: str, message: str, **kwargs):
    """Log avec gestion d'erreur pour éviter les problèmes de handler."""
    try:
        getattr(logger, level)(message, **kwargs)
    except (TypeError, AttributeError):
        print(f"{level.upper()}: {message} - {kwargs}")


@router.post(
    "/slots",
    response_model=InterviewSlotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un créneau d'entretien",
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
                        "job_title": "Développeur Full Stack",
                        "status": "scheduled",
                        "location": "Libreville",
                        "notes": "Entretien technique"
                    }
                }
            }
        },
        "responses": {
            "201": {
                "description": "Créneau créé avec succès",
                "content": {
                    "application/json": {
                        "example": {
                            "id": "uuid",
                            "date": "2025-10-15",
                            "time": "09:00:00",
                            "application_id": "uuid",
                            "candidate_name": "John Doe",
                            "job_title": "Développeur Full Stack",
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
                "description": "Candidature non trouvée"
            },
            "409": {
                "description": "Créneau déjà occupé",
                "content": {
                    "application/json": {
                        "example": {
                            "detail": "Le créneau 2025-10-15 à 09:00:00 est déjà occupé"
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
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Créer un nouveau créneau d'entretien

    **Validations** :
    - Vérifier que le créneau n'existe pas déjà
    - Vérifier que le créneau n'est pas déjà occupé
    - Valider le format de la date (YYYY-MM-DD)
    - Valider le format de l'heure (HH:mm:ss)
    - Vérifier que l'application_id existe

    **Si le créneau existe et est disponible** : Le mettre à jour au lieu d'en créer un nouveau
    """
    try:
        interview_service = InterviewService(db)
        result = await interview_service.create_interview_slot(
            slot_data, str(current_user.id)
        )
        # MongoDB (Motor) handle commits automatiquement

        safe_log("info", "Créneau d'entretien créé",
                slot_id=str(result.id) if hasattr(result, 'id') else "unknown",
                date=slot_data.date,
                time=slot_data.time,
                user_id=str(current_user.get("_id", current_user.get("id"))))

        # 🔔 Envoyer email + notification au candidat (PATTERN UNIFIÉ)
        try:
            safe_log("debug", "🔍 Début envoi email + notification entretien",
                    application_id=str(slot_data.application_id))

            from uuid import UUID as UUID_Type
            from app.services.notification_email_manager import NotificationEmailManager
            from bson import ObjectId

            safe_log("debug", "🔍 Imports réussis")

            # Récupérer les détails de la candidature
            app_id = slot_data.application_id
            app_query = {"_id": ObjectId(app_id) if len(str(app_id)) == 24 else app_id}
            application = await db.applications.find_one(app_query)

            safe_log("debug", "🔍 Application récupérée",
                    found=application is not None)

            if application:
                candidate_id = application.get("candidate_id")
                job_offer_id = application.get("job_offer_id")

                cand_query = {"_id": ObjectId(candidate_id) if len(str(candidate_id)) == 24 else candidate_id}
                candidate = await db.users.find_one(cand_query)

                offer_query = {"_id": ObjectId(job_offer_id) if len(str(job_offer_id)) == 24 else job_offer_id}
                job_offer = await db.job_offers.find_one(offer_query)

                if candidate and job_offer:
                    safe_log("debug", "🔍 Extraction données candidat...")
                    candidate_email = candidate.get("email")
                    candidate_full_name = f"{candidate.get('first_name')} {candidate.get('last_name')}"
                    job_title = job_offer.get("title")

                    safe_log("debug", "🔍 Données extraites",
                            candidate_email=str(candidate_email),
                            candidate_name=candidate_full_name,
                            job_title=str(job_title))

                    # Nom de l'interviewer
                    interviewer_name = f"{current_user.get('first_name')} {current_user.get('last_name')}" if current_user.get('first_name') else "L'équipe RH SEEG"

                    safe_log("debug", "🔍 Création NotificationEmailManager...")
                    notif_email_manager = NotificationEmailManager(db)
                    safe_log("debug", "✅ NotificationEmailManager créé")

                    # Convertir les types
                    safe_log("debug", "🔍 Conversion types UUID...")
                    candidate_id_uuid = candidate_id if isinstance(candidate_id, UUID_Type) else UUID_Type(str(candidate_id))
                    application_id_uuid = application.get("_id") if isinstance(application.get("_id"), UUID_Type) else UUID_Type(str(application.get("_id", application.get("id"))))

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

                    safe_log("info", "✅ Email + notification entretien envoyés",
                            application_id=str(slot_data.application_id),
                            email_sent=notification_result.get("email_sent"),
                            notification_sent=notification_result.get("notification_sent"))
                else:
                    safe_log("warning", "Candidate ou Job Offer non trouvé pour l'application",
                            application_id=str(slot_data.application_id))
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
        safe_log("warning", "Candidature non trouvée pour création créneau", error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        safe_log("warning", "Créneau déjà occupé", date=slot_data.date, time=slot_data.time, error=str(e))
        raise HTTPException(status_code=409, detail=str(e))
    except (ValidationError, ValueError) as e:
        safe_log("warning", "Erreur validation création créneau", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur création créneau entretien", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get(
    "/slots",
    response_model=InterviewSlotListResponse,
    summary="Lister les créneaux d'entretien (avec filtres)",
    tags=["ðŸŽ¯ Entretiens"],
    openapi_extra={
        "responses": {
            "200": {
                "description": "Liste des créneaux",
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
                                    "job_title": "Développeur Full Stack",
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
    skip: int = Query(0, ge=0, description="Nombre d'éléments à ignorer (pagination)"),
    limit: int = Query(50, ge=1, le=1000, description="Nombre maximum d'éléments à retourner"),
    application_id: Optional[str] = Query(None, description="Filtrer par candidature"),
    status: Optional[str] = Query(None, description="Filtrer par statut (scheduled, completed, cancelled)"),
    is_available: Optional[bool] = Query(None, description="Filtrer par disponibilité (true=libre, false=occupé)"),
    date_from: Optional[str] = Query(None, description="Date de début (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    order: Optional[str] = Query(None, description="Ordre de tri (ex: date:asc,time:asc)"),
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Récupérer la liste des créneaux d'entretien

    **Filtres disponibles** :
    - `date_from` / `date_to` : Période (YYYY-MM-DD)
    - `is_available` : true = créneaux libres, false = créneaux occupés
    - `application_id` : Filtrer par candidature
    - `status` : scheduled, completed, cancelled
    - `order` : Ordre de tri (date:asc,time:asc par défaut)

    **Comportements spécifiques** :
    - Retourne uniquement les créneaux occupés si `is_available=false`
    - Exclut les créneaux sans `application_id` si `is_available=false`
    - Tri par défaut : date ASC, puis time ASC
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
        safe_log("info", "Créneaux entretiens récupérés", count=results.total if hasattr(results, 'total') else 0, user_id=str(current_user.get("_id", current_user.get("id"))))
        return results
    except Exception as e:
        safe_log("error", "Erreur récupération créneaux", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get(
    "/slots/{slot_id}",
    response_model=InterviewSlotResponse,
    summary="Récupérer un créneau d'entretien par ID",
    tags=["ðŸŽ¯ Entretiens"],
    openapi_extra={
        "responses": {
            "200": {
                "description": "Créneau trouvé",
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
                "description": "Créneau non trouvé"
            }
        }
    }
)
async def get_interview_slot(
    slot_id: str,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Récupérer un créneau d'entretien par son ID
    """
    try:
        interview_service = InterviewService(db)
        result = await interview_service.get_interview_slot(slot_id)
        safe_log("info", "Créneau entretien récupéré", slot_id=slot_id)
        return result
    except NotFoundError as e:
        safe_log("warning", "Créneau non trouvé", slot_id=slot_id)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur récupération créneau", slot_id=slot_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.put(
    "/slots/{slot_id}",
    response_model=InterviewSlotResponse,
    summary="Mettre à jour un créneau d'entretien",
    tags=["ðŸŽ¯ Entretiens"],
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "example": {
                        "date": "2025-10-16",
                        "time": "10:00:00",
                        "status": "scheduled",
                        "notes": "Entretien reporté"
                    }
                }
            }
        },
        "responses": {
            "200": {
                "description": "Créneau mis à jour",
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
                "description": "Créneau non trouvé"
            },
            "409": {
                "description": "Nouveau créneau déjà occupé",
                "content": {
                    "application/json": {
                        "example": {
                            "detail": "Le créneau 2025-10-16 à 10:00:00 est déjà occupé par une autre candidature"
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
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Mettre à jour un créneau d'entretien

    **Logique complexe pour changement de date/heure** :

    Lorsque la **date** ou **l'heure** change :
    1. Libérer l'ancien créneau (marquer comme disponible)
    2. Vérifier si le nouveau créneau existe
    3. Si disponible, l'occuper ; sinon créer un nouveau créneau

    **Tous les champs sont optionnels** :
    - `date` : YYYY-MM-DD
    - `time` : HH:mm:ss
    - `application_id` : Changer la candidature liée
    - `candidate_name`
    - `job_title`
    - `status` : scheduled, completed, cancelled
    - `location`
    - `notes`
    """
    try:
        interview_service = InterviewService(db)
        result = await interview_service.update_interview_slot(
            slot_id, slot_data, str(current_user.get("_id", current_user.get("id")))
        )
        safe_log("info", "Créneau d'entretien mis à jour", slot_id=slot_id, user_id=str(current_user.get("_id", current_user.get("id"))))
        return result
    except NotFoundError as e:
        safe_log("warning", "Créneau non trouvé pour MAJ", slot_id=slot_id)
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        safe_log("warning", "Erreur logique métier MAJ créneau", slot_id=slot_id, error=str(e))
        raise HTTPException(status_code=409, detail=str(e))
    except (ValidationError, ValueError) as e:
        safe_log("warning", "Erreur validation MAJ créneau", slot_id=slot_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur MAJ créneau", slot_id=slot_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.delete(
    "/slots/{slot_id}",
    status_code=status.HTTP_200_OK,
    summary="Annuler un créneau d'entretien (soft delete)",
    tags=["ðŸŽ¯ Entretiens"],
    openapi_extra={
        "responses": {
            "200": {
                "description": "Entretien annulé avec succès",
                "content": {
                    "application/json": {
                        "example": {
                            "message": "Entretien annulé avec succès",
                            "slot_id": "uuid"
                        }
                    }
                }
            },
            "404": {
                "description": "Créneau non trouvé"
            }
        }
    }
)
async def delete_interview_slot(
    slot_id: str,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Annuler un créneau d'entretien (soft delete)

    **Logique** :
    - Ne supprime pas physiquement le créneau
    - Marque le statut comme "cancelled"
    - Libère le créneau (`is_available = true`)
    - Dissocie la candidature (`application_id = null`)
    - Conserve les données pour l'historique
    """
    try:
        interview_service = InterviewService(db)
        await interview_service.delete_interview_slot(slot_id, str(current_user.get("_id", current_user.get("id"))))
        safe_log("info", "Créneau d'entretien annulé", slot_id=slot_id, user_id=str(current_user.get("_id", current_user.get("id"))))
        return {
            "message": "Entretien annulé avec succès",
            "slot_id": slot_id
        }
    except NotFoundError as e:
        safe_log("warning", "Créneau non trouvé pour annulation", slot_id=slot_id)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur annulation créneau", slot_id=slot_id, error=str(e))
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
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Récupérer les statistiques des entretiens

    Retourne:
    - Nombre total d'entretiens
    - Répartition par statut
    - Statistiques globales
    """
    try:
        interview_service = InterviewService(db)
        stats = await interview_service.get_interview_statistics()
        safe_log("info", "Statistiques entretiens récupérées", user_id=str(current_user.get("_id", current_user.get("id"))))
        return stats
    except Exception as e:
        safe_log("error", "Erreur récupération statistiques entretiens", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")
