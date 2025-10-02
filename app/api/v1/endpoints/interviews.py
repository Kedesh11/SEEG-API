"""
Endpoints pour la gestion des entretiens
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

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


@router.post("/slots", response_model=InterviewSlotResponse, status_code=status.HTTP_201_CREATED, summary="Créer un créneau d'entretien", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {
        "application_id": "uuid",
        "candidate_name": "SEEG KABA Marie",
        "job_title": "Ingénieur Réseaux",
        "date": "2025-10-05",
        "time": "10:00"
    }}}},
    "responses": {"201": {"content": {"application/json": {"example": {
        "id": "uuid", "application_id": "uuid", "candidate_name": "SEEG KABA Marie", "status": "scheduled"
    }}}}}
})
async def create_interview_slot(
    slot_data: InterviewSlotCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Créer un nouveau créneau d'entretien
    
    - **application_id**: ID de la candidature
    - **interviewer_id**: ID de l'interviewer
    - **scheduled_date**: Date et heure de l'entretien
    - **duration_minutes**: Durée en minutes
    - **location**: Lieu de l'entretien
    - **meeting_link**: Lien de la réunion (optionnel)
    - **notes**: Notes additionnelles (optionnel)
    """
    try:
        interview_service = InterviewService(db)
        return await interview_service.create_interview_slot(
            slot_data, str(current_user.id)
        )
    except (ValidationError, BusinessLogicError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/slots", response_model=InterviewSlotListResponse, summary="Lister les créneaux d'entretien (filtres/pagination)", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {
        "slots": [], "total": 0, "page": 1, "per_page": 100, "total_pages": 0
    }}}}}
})
async def get_interview_slots(
    skip: int = Query(0, ge=0, description="Nombre d'éléments à ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum d'éléments à retourner"),
    application_id: Optional[str] = Query(None, description="Filtrer par candidature"),
    interviewer_id: Optional[str] = Query(None, description="Filtrer par interviewer"),
    status: Optional[str] = Query(None, description="Filtrer par statut"),
    date_from: Optional[datetime] = Query(None, description="Date de début"),
    date_to: Optional[datetime] = Query(None, description="Date de fin"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer la liste des créneaux d'entretien
    
    - **skip**: Nombre d'éléments à ignorer (pagination)
    - **limit**: Nombre maximum d'éléments à retourner
    - **application_id**: Filtrer par candidature
    - **interviewer_id**: Filtrer par interviewer
    - **status**: Filtrer par statut (scheduled, completed, cancelled)
    - **date_from**: Date de début pour le filtre
    - **date_to**: Date de fin pour le filtre
    """
    try:
        interview_service = InterviewService(db)
        return await interview_service.get_interview_slots(
            skip=skip,
            limit=limit,
            application_id=application_id,
            interviewer_id=interviewer_id,
            status=status,
            date_from=date_from,
            date_to=date_to
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/slots/{slot_id}", response_model=InterviewSlotResponse, summary="Récupérer un créneau d'entretien par ID", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"id": "uuid", "application_id": "uuid", "status": "scheduled"}}}}, "404": {"description": "Non trouvé"}}
})
async def get_interview_slot(
    slot_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer un créneau d'entretien par son ID
    
    - **slot_id**: ID unique du créneau d'entretien
    """
    try:
        interview_service = InterviewService(db)
        return await interview_service.get_interview_slot(slot_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.put("/slots/{slot_id}", response_model=InterviewSlotResponse, summary="Mettre à jour un créneau d'entretien", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"status": "cancelled"}}}},
    "responses": {"200": {"content": {"application/json": {"example": {"id": "uuid", "status": "cancelled"}}}}}
})
async def update_interview_slot(
    slot_id: str,
    slot_data: InterviewSlotUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Mettre à jour un créneau d'entretien
    
    - **slot_id**: ID du créneau d'entretien à mettre à jour
    - **slot_data**: Données de mise à jour (tous les champs sont optionnels)
    """
    try:
        interview_service = InterviewService(db)
        return await interview_service.update_interview_slot(
            slot_id, slot_data, str(current_user.id)
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationError, BusinessLogicError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.delete("/slots/{slot_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer un créneau d'entretien", openapi_extra={
    "responses": {"204": {"description": "Supprimé"}, "404": {"description": "Non trouvé"}}
})
async def delete_interview_slot(
    slot_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Supprimer un créneau d'entretien
    
    - **slot_id**: ID du créneau d'entretien à supprimer
    """
    try:
        interview_service = InterviewService(db)
        await interview_service.delete_interview_slot(slot_id, str(current_user.id))
        return None
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/calendar/available", response_model=List[InterviewSlotResponse], summary="Lister les créneaux disponibles d'un interviewer", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": []}}}}
})
async def get_available_interview_slots(
    interviewer_id: str = Query(..., description="ID de l'interviewer"),
    date_from: datetime = Query(..., description="Date de début"),
    date_to: datetime = Query(..., description="Date de fin"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer les créneaux d'entretien disponibles pour un interviewer
    
    - **interviewer_id**: ID de l'interviewer
    - **date_from**: Date de début
    - **date_to**: Date de fin
    """
    try:
        interview_service = InterviewService(db)
        return await interview_service.get_available_slots(
            interviewer_id=interviewer_id,
            date_from=date_from,
            date_to=date_to
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/stats/overview", response_model=InterviewStatsResponse, summary="Statistiques globales des entretiens", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {
        "total_interviews": 0,
        "scheduled_interviews": 0,
        "completed_interviews": 0,
        "cancelled_interviews": 0,
        "interviews_by_status": {}
    }}}}}
})
async def get_interview_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer les statistiques des entretiens
    
    Retourne:
    - Nombre total d'entretiens
    - Répartition par statut
    - Entretiens à venir
    - Tendance mensuelle
    """
    try:
        interview_service = InterviewService(db)
        return await interview_service.get_interview_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")
