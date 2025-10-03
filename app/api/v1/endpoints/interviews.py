"""
Endpoints pour la gestion des entretiens
Compatible avec InterviewCalendarModal.tsx
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.services.interview import InterviewService
from app.schemas.interview import (
    InterviewSlotCreate, InterviewSlotUpdate, InterviewSlotResponse,
    InterviewSlotListResponse, InterviewStatsResponse
)
from app.core.dependencies import get_current_user
from app.models.user import User
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError

router = APIRouter()


@router.post(
    "/slots",
    response_model=InterviewSlotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un créneau d'entretien",
    tags=["🎯 Entretiens"],
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
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
        return await interview_service.create_interview_slot(
            slot_data, str(current_user.id)
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except (ValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get(
    "/slots",
    response_model=InterviewSlotListResponse,
    summary="Lister les créneaux d'entretien (avec filtres)",
    tags=["🎯 Entretiens"],
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
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
        return await interview_service.get_interview_slots(
            skip=skip,
            limit=limit,
            application_id=application_id,
            status=status,
            is_available=is_available,
            date_from=date_from,
            date_to=date_to,
            order=order
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get(
    "/slots/{slot_id}",
    response_model=InterviewSlotResponse,
    summary="Récupérer un créneau d'entretien par ID",
    tags=["🎯 Entretiens"],
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer un créneau d'entretien par son ID
    """
    try:
        interview_service = InterviewService(db)
        return await interview_service.get_interview_slot(slot_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.put(
    "/slots/{slot_id}",
    response_model=InterviewSlotResponse,
    summary="Mettre à jour un créneau d'entretien",
    tags=["🎯 Entretiens"],
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
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
        return await interview_service.update_interview_slot(
            slot_id, slot_data, str(current_user.id)
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except (ValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.delete(
    "/slots/{slot_id}",
    status_code=status.HTTP_200_OK,
    summary="Annuler un créneau d'entretien (soft delete)",
    tags=["🎯 Entretiens"],
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
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
        await interview_service.delete_interview_slot(slot_id, str(current_user.id))
        return {
            "message": "Entretien annulé avec succès",
            "slot_id": slot_id
        }
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get(
    "/stats/overview",
    response_model=InterviewStatsResponse,
    summary="Statistiques globales des entretiens",
    tags=["🎯 Entretiens"],
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
    db: AsyncSession = Depends(get_async_db)
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
        return await interview_service.get_interview_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")
