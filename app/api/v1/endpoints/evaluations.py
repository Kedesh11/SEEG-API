"""
Endpoints pour la gestion des évaluations
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.services.evaluation import EvaluationService
from app.schemas.evaluation import (
    Protocol1EvaluationCreate, Protocol1EvaluationUpdate, Protocol1EvaluationResponse,
    Protocol2EvaluationCreate, Protocol2EvaluationUpdate, Protocol2EvaluationResponse,
)
from app.core.dependencies import get_current_user
from app.models.user import User
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError

router = APIRouter()


# Protocol 1 Evaluation Endpoints
@router.post("/protocol1", response_model=Protocol1EvaluationResponse, status_code=status.HTTP_201_CREATED)
async def create_protocol1_evaluation(
    evaluation_data: Protocol1EvaluationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Créer une nouvelle évaluation Protocol 1
    
    - **application_id**: ID de la candidature
    - **documentary_score**: Score documentaire (0-20)
    - **documentary_notes**: Notes sur le score documentaire (optionnel)
    - **mtp_adherence_score**: Score d'adhérence MTP (0-20)
    - **mtp_adherence_notes**: Notes sur l'adhérence MTP (optionnel)
    - **interview_score**: Score d'entretien (0-20)
    - **interview_notes**: Notes sur l'entretien (optionnel)
    - **recommendation**: Recommandation (strongly_recommend, recommend, neutral, not_recommend, strongly_not_recommend)
    - **additional_notes**: Notes additionnelles (optionnel)
    """
    try:
        evaluation_service = EvaluationService(db)
        return await evaluation_service.create_protocol1_evaluation(
            evaluation_data, str(current_user.id)
        )
    except (ValidationError, BusinessLogicError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/protocol1/{evaluation_id}", response_model=Protocol1EvaluationResponse)
async def get_protocol1_evaluation(
    evaluation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer une évaluation Protocol 1 par son ID
    
    - **evaluation_id**: ID unique de l'évaluation
    """
    try:
        evaluation_service = EvaluationService(db)
        return await evaluation_service.get_protocol1_evaluation(evaluation_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.put("/protocol1/{evaluation_id}", response_model=Protocol1EvaluationResponse)
async def update_protocol1_evaluation(
    evaluation_id: str,
    evaluation_data: Protocol1EvaluationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Mettre à jour une évaluation Protocol 1
    
    - **evaluation_id**: ID de l'évaluation à mettre à jour
    - **evaluation_data**: Données de mise à jour (tous les champs sont optionnels)
    """
    try:
        evaluation_service = EvaluationService(db)
        return await evaluation_service.update_protocol1_evaluation(
            evaluation_id, evaluation_data, str(current_user.id)
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationError, BusinessLogicError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/protocol1/application/{application_id}", response_model=List[Protocol1EvaluationResponse])
async def get_protocol1_evaluations_by_application(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer les évaluations Protocol 1 pour une candidature
    
    - **application_id**: ID de la candidature
    """
    try:
        evaluation_service = EvaluationService(db)
        return await evaluation_service.get_protocol1_evaluations_by_application(application_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


# Protocol 2 Evaluation Endpoints
@router.post("/protocol2", response_model=Protocol2EvaluationResponse, status_code=status.HTTP_201_CREATED)
async def create_protocol2_evaluation(
    evaluation_data: Protocol2EvaluationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Créer une nouvelle évaluation Protocol 2
    
    - **application_id**: ID de la candidature
    - **technical_skills_score**: Score de compétences techniques (0-20)
    - **technical_skills_notes**: Notes sur les compétences techniques (optionnel)
    - **soft_skills_score**: Score de compétences comportementales (0-20)
    - **soft_skills_notes**: Notes sur les compétences comportementales (optionnel)
    - **cultural_fit_score**: Score d'adaptation culturelle (0-20)
    - **cultural_fit_notes**: Notes sur l'adaptation culturelle (optionnel)
    - **leadership_potential_score**: Score de potentiel de leadership (0-20)
    - **leadership_potential_notes**: Notes sur le potentiel de leadership (optionnel)
    - **recommendation**: Recommandation (strongly_recommend, recommend, neutral, not_recommend, strongly_not_recommend)
    - **additional_notes**: Notes additionnelles (optionnel)
    """
    try:
        evaluation_service = EvaluationService(db)
        return await evaluation_service.create_protocol2_evaluation(
            evaluation_data, str(current_user.id)
        )
    except (ValidationError, BusinessLogicError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/protocol2/{evaluation_id}", response_model=Protocol2EvaluationResponse)
async def get_protocol2_evaluation(
    evaluation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer une évaluation Protocol 2 par son ID
    
    - **evaluation_id**: ID unique de l'évaluation
    """
    try:
        evaluation_service = EvaluationService(db)
        return await evaluation_service.get_protocol2_evaluation(evaluation_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.put("/protocol2/{evaluation_id}", response_model=Protocol2EvaluationResponse)
async def update_protocol2_evaluation(
    evaluation_id: str,
    evaluation_data: Protocol2EvaluationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Mettre à jour une évaluation Protocol 2
    
    - **evaluation_id**: ID de l'évaluation à mettre à jour
    - **evaluation_data**: Données de mise à jour (tous les champs sont optionnels)
    """
    try:
        evaluation_service = EvaluationService(db)
        return await evaluation_service.update_protocol2_evaluation(
            evaluation_id, evaluation_data, str(current_user.id)
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationError, BusinessLogicError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/protocol2/application/{application_id}", response_model=List[Protocol2EvaluationResponse])
async def get_protocol2_evaluations_by_application(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer les évaluations Protocol 2 pour une candidature
    
    - **application_id**: ID de la candidature
    """
    try:
        evaluation_service = EvaluationService(db)
        return await evaluation_service.get_protocol2_evaluations_by_application(application_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


# Statistics Endpoint
async def get_evaluation_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer les statistiques des évaluations
    
    Retourne:
    - Statistiques Protocol 1 (nombre total, score moyen)
    - Statistiques Protocol 2 (nombre total, score moyen)
    """
    try:
        evaluation_service = EvaluationService(db)
        return await evaluation_service.get_evaluation_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")
