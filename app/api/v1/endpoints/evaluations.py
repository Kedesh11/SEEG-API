"""
Endpoints pour la gestion des Ã©valuations
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.db.database import get_db
from app.services.evaluation import EvaluationService
from app.schemas.evaluation import (
    Protocol1EvaluationCreate, Protocol1EvaluationUpdate, Protocol1EvaluationResponse,
    Protocol2EvaluationCreate, Protocol2EvaluationUpdate, Protocol2EvaluationResponse,
)
from app.core.dependencies import get_current_user
from app.models.user import User
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError

router = APIRouter()
logger = structlog.get_logger(__name__)


def safe_log(level: str, message: str, **kwargs):
    """Log avec gestion d'erreur pour Ã©viter les problÃ¨mes de handler."""
    try:
        getattr(logger, level)(message, **kwargs)
    except (TypeError, AttributeError):
        print(f"{level.upper()}: {message} - {kwargs}")


# Protocol 1 Evaluation Endpoints
@router.post("/protocol1", response_model=Protocol1EvaluationResponse, status_code=status.HTTP_201_CREATED, summary="CrÃ©er une Ã©valuation Protocole 1", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"application_id": "uuid", "evaluator_id": "uuid", "cv_score": 15}}}},
    "responses": {"201": {"content": {"application/json": {"example": {"id": "uuid", "application_id": "uuid", "cv_score": 15}}}}}
})
async def create_protocol1_evaluation(
    evaluation_data: Protocol1EvaluationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    CrÃ©er une nouvelle Ã©valuation Protocol 1
    
    - **application_id**: ID de la candidature
    - **documentary_score**: Score documentaire (0-20)
    - **documentary_notes**: Notes sur le score documentaire (optionnel)
    - **mtp_adherence_score**: Score d'adhÃ©rence MTP (0-20)
    - **mtp_adherence_notes**: Notes sur l'adhÃ©rence MTP (optionnel)
    - **interview_score**: Score d'entretien (0-20)
    - **interview_notes**: Notes sur l'entretien (optionnel)
    - **recommendation**: Recommandation (strongly_recommend, recommend, neutral, not_recommend, strongly_not_recommend)
    - **additional_notes**: Notes additionnelles (optionnel)
    """
    try:
        evaluation_service = EvaluationService(db)
        result = await evaluation_service.create_protocol1_evaluation(
            evaluation_data, str(current_user.id)
        )
        safe_log("info", "Ã‰valuation Protocol 1 crÃ©Ã©e", 
                evaluation_id=str(result.id) if hasattr(result, 'id') else "unknown",
                evaluator_id=str(current_user.id))
        return result
    except (ValidationError, BusinessLogicError) as e:
        safe_log("warning", "Erreur validation crÃ©ation Ã©valuation P1", error=str(e), evaluator_id=str(current_user.id))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur crÃ©ation Ã©valuation P1", error=str(e), evaluator_id=str(current_user.id))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/protocol1/{evaluation_id}", response_model=Protocol1EvaluationResponse, summary="RÃ©cupÃ©rer une Ã©valuation Protocole 1 par ID", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"id": "uuid", "application_id": "uuid"}}}}, "404": {"description": "Non trouvÃ©e"}}
})
async def get_protocol1_evaluation(
    evaluation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    RÃ©cupÃ©rer une Ã©valuation Protocol 1 par son ID
    
    - **evaluation_id**: ID unique de l'Ã©valuation
    """
    try:
        evaluation_service = EvaluationService(db)
        result = await evaluation_service.get_protocol1_evaluation(evaluation_id)
        safe_log("info", "Ã‰valuation Protocol 1 rÃ©cupÃ©rÃ©e", evaluation_id=evaluation_id)
        return result
    except NotFoundError as e:
        safe_log("warning", "Ã‰valuation P1 non trouvÃ©e", evaluation_id=evaluation_id)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur rÃ©cupÃ©ration Ã©valuation P1", evaluation_id=evaluation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.put("/protocol1/{evaluation_id}", response_model=Protocol1EvaluationResponse, summary="Mettre Ã  jour une Ã©valuation Protocole 1", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"cv_score": 16}}}},
    "responses": {"200": {"content": {"application/json": {"example": {"id": "uuid", "cv_score": 16}}}}}
})
async def update_protocol1_evaluation(
    evaluation_id: str,
    evaluation_data: Protocol1EvaluationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mettre Ã  jour une Ã©valuation Protocol 1
    
    - **evaluation_id**: ID de l'Ã©valuation Ã  mettre Ã  jour
    - **evaluation_data**: DonnÃ©es de mise Ã  jour (tous les champs sont optionnels)
    """
    try:
        evaluation_service = EvaluationService(db)
        result = await evaluation_service.update_protocol1_evaluation(
            evaluation_id, evaluation_data, str(current_user.id)
        )
        safe_log("info", "Ã‰valuation Protocol 1 mise Ã  jour", evaluation_id=evaluation_id, evaluator_id=str(current_user.id))
        return result
    except NotFoundError as e:
        safe_log("warning", "Ã‰valuation P1 non trouvÃ©e pour MAJ", evaluation_id=evaluation_id)
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationError, BusinessLogicError) as e:
        safe_log("warning", "Erreur validation MAJ Ã©valuation P1", evaluation_id=evaluation_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur MAJ Ã©valuation P1", evaluation_id=evaluation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/protocol1/application/{application_id}", response_model=List[Protocol1EvaluationResponse], summary="Lister les Ã©valuations Protocole 1 par candidature", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": [{"id": "uuid", "application_id": "uuid"}]}}}}
})
async def get_protocol1_evaluations_by_application(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    RÃ©cupÃ©rer les Ã©valuations Protocol 1 pour une candidature
    
    - **application_id**: ID de la candidature
    """
    try:
        evaluation_service = EvaluationService(db)
        results = await evaluation_service.get_protocol1_evaluations_by_application(application_id)
        safe_log("info", "Ã‰valuations Protocol 1 rÃ©cupÃ©rÃ©es", application_id=application_id, count=len(results))
        return results
    except Exception as e:
        safe_log("error", "Erreur rÃ©cupÃ©ration Ã©valuations P1", application_id=application_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


# Protocol 2 Evaluation Endpoints
@router.post("/protocol2", response_model=Protocol2EvaluationResponse, status_code=status.HTTP_201_CREATED, summary="CrÃ©er une Ã©valuation Protocole 2", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"application_id": "uuid", "evaluator_id": "uuid", "qcm_role_score": 17}}}},
    "responses": {"201": {"content": {"application/json": {"example": {"id": "uuid", "application_id": "uuid", "qcm_role_score": 17}}}}}
})
async def create_protocol2_evaluation(
    evaluation_data: Protocol2EvaluationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    CrÃ©er une nouvelle Ã©valuation Protocol 2
    
    - **application_id**: ID de la candidature
    - **technical_skills_score**: Score de compÃ©tences techniques (0-20)
    - **technical_skills_notes**: Notes sur les compÃ©tences techniques (optionnel)
    - **soft_skills_score**: Score de compÃ©tences comportementales (0-20)
    - **soft_skills_notes**: Notes sur les compÃ©tences comportementales (optionnel)
    - **cultural_fit_score**: Score d'adaptation culturelle (0-20)
    - **cultural_fit_notes**: Notes sur l'adaptation culturelle (optionnel)
    - **leadership_potential_score**: Score de potentiel de leadership (0-20)
    - **leadership_potential_notes**: Notes sur le potentiel de leadership (optionnel)
    - **recommendation**: Recommandation (strongly_recommend, recommend, neutral, not_recommend, strongly_not_recommend)
    - **additional_notes**: Notes additionnelles (optionnel)
    """
    try:
        evaluation_service = EvaluationService(db)
        result = await evaluation_service.create_protocol2_evaluation(
            evaluation_data, str(current_user.id)
        )
        safe_log("info", "Ã‰valuation Protocol 2 crÃ©Ã©e",
                evaluation_id=str(result.id) if hasattr(result, 'id') else "unknown",
                evaluator_id=str(current_user.id))
        return result
    except (ValidationError, BusinessLogicError) as e:
        safe_log("warning", "Erreur validation crÃ©ation Ã©valuation P2", error=str(e), evaluator_id=str(current_user.id))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur crÃ©ation Ã©valuation P2", error=str(e), evaluator_id=str(current_user.id))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/protocol2/{evaluation_id}", response_model=Protocol2EvaluationResponse, summary="RÃ©cupÃ©rer une Ã©valuation Protocole 2 par ID", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"id": "uuid", "application_id": "uuid"}}}}, "404": {"description": "Non trouvÃ©e"}}
})
async def get_protocol2_evaluation(
    evaluation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    RÃ©cupÃ©rer une Ã©valuation Protocol 2 par son ID
    
    - **evaluation_id**: ID unique de l'Ã©valuation
    """
    try:
        evaluation_service = EvaluationService(db)
        result = await evaluation_service.get_protocol2_evaluation(evaluation_id)
        safe_log("info", "Ã‰valuation Protocol 2 rÃ©cupÃ©rÃ©e", evaluation_id=evaluation_id)
        return result
    except NotFoundError as e:
        safe_log("warning", "Ã‰valuation P2 non trouvÃ©e", evaluation_id=evaluation_id)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur rÃ©cupÃ©ration Ã©valuation P2", evaluation_id=evaluation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.put("/protocol2/{evaluation_id}", response_model=Protocol2EvaluationResponse, summary="Mettre Ã  jour une Ã©valuation Protocole 2", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"qcm_codir_score": 16}}}},
    "responses": {"200": {"content": {"application/json": {"example": {"id": "uuid", "qcm_codir_score": 16}}}}}
})
async def update_protocol2_evaluation(
    evaluation_id: str,
    evaluation_data: Protocol2EvaluationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mettre Ã  jour une Ã©valuation Protocol 2
    
    - **evaluation_id**: ID de l'Ã©valuation Ã  mettre Ã  jour
    - **evaluation_data**: DonnÃ©es de mise Ã  jour (tous les champs sont optionnels)
    """
    try:
        evaluation_service = EvaluationService(db)
        result = await evaluation_service.update_protocol2_evaluation(
            evaluation_id, evaluation_data, str(current_user.id)
        )
        safe_log("info", "Ã‰valuation Protocol 2 mise Ã  jour", evaluation_id=evaluation_id, evaluator_id=str(current_user.id))
        return result
    except NotFoundError as e:
        safe_log("warning", "Ã‰valuation P2 non trouvÃ©e pour MAJ", evaluation_id=evaluation_id)
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationError, BusinessLogicError) as e:
        safe_log("warning", "Erreur validation MAJ Ã©valuation P2", evaluation_id=evaluation_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur MAJ Ã©valuation P2", evaluation_id=evaluation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/protocol2/application/{application_id}", response_model=List[Protocol2EvaluationResponse], summary="Lister les Ã©valuations Protocole 2 par candidature", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": [{"id": "uuid", "application_id": "uuid"}]}}}}
})
async def get_protocol2_evaluations_by_application(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    RÃ©cupÃ©rer les Ã©valuations Protocol 2 pour une candidature
    
    - **application_id**: ID de la candidature
    """
    try:
        evaluation_service = EvaluationService(db)
        results = await evaluation_service.get_protocol2_evaluations_by_application(application_id)
        safe_log("info", "Ã‰valuations Protocol 2 rÃ©cupÃ©rÃ©es", application_id=application_id, count=len(results))
        return results
    except Exception as e:
        safe_log("error", "Erreur rÃ©cupÃ©ration Ã©valuations P2", application_id=application_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


# Statistics Endpoint
@router.get("/stats/overview", response_model=dict, summary="Statistiques globales des Ã©valuations", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"protocol1": {"total_evaluations": 0, "average_score": 0}, "protocol2": {"total_evaluations": 0, "average_score": 0}}}}}}
})
async def get_evaluation_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    RÃ©cupÃ©rer les statistiques des Ã©valuations
    
    Retourne:
    - Statistiques Protocol 1 (nombre total, score moyen)
    - Statistiques Protocol 2 (nombre total, score moyen)
    """
    try:
        evaluation_service = EvaluationService(db)
        stats = await evaluation_service.get_evaluation_statistics()
        safe_log("info", "Statistiques Ã©valuations rÃ©cupÃ©rÃ©es", requester_id=str(current_user.id))
        return stats
    except Exception as e:
        safe_log("error", "Erreur rÃ©cupÃ©ration statistiques Ã©valuations", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")
