"""
Endpoints pour la gestion des évaluations
"""
from typing import Any
import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from app.db.database import get_db
from app.services.evaluation import EvaluationService
from app.schemas.evaluation import (
    Protocol1EvaluationCreate, Protocol1EvaluationUpdate,
    Protocol1EvaluationResponse, Protocol2EvaluationCreate,
    Protocol2EvaluationUpdate, Protocol2EvaluationResponse,
)
from app.core.dependencies import get_current_user
from app.core.exceptions import (
    NotFoundError, ValidationError, BusinessLogicError
)

router = APIRouter()
logger = structlog.get_logger(__name__)


def safe_log(level: str, message: str, **kwargs):
    """Log avec gestion d'erreur pour éviter les problèmes de handler."""
    try:
        getattr(logger, level)(message, **kwargs)
    except (TypeError, AttributeError):
        print(f"{level.upper()}: {message} - {kwargs}")


# Protocol 1 Evaluation Endpoints
@router.post(
    "/protocol1",
    response_model=Protocol1EvaluationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une évaluation Protocole 1",
    openapi_extra={
        "requestBody": {"content": {"application/json": {"example": {
            "application_id": "uuid", "evaluator_id": "uuid", "cv_score": 15
        }}}},
        "responses": {"201": {"content": {"application/json": {"example": {
            "id": "uuid", "application_id": "uuid", "cv_score": 15
        }}}}}
    }
)
async def create_protocol1_evaluation(
    evaluation_data: Protocol1EvaluationCreate,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Créer une nouvelle évaluation Protocol 1

    - **application_id**: ID de la candidature
    - **recommendation**: Recommandation
    """
    try:
        evaluation_service = EvaluationService(db)
        u_id = str(current_user.get("_id", current_user.get("id")))
        result = await evaluation_service.create_protocol1_evaluation(
            evaluation_data, u_id
        )
        if isinstance(result, dict):
            e_id = result.get("id", "N/A")
        else:
            e_id = getattr(result, 'id', 'N/A')
        safe_log(
            "info", "Évaluation Protocol 1 créée",
            evaluation_id=str(e_id), evaluator_id=str(u_id)
        )
        return result
    except (ValidationError, BusinessLogicError) as e:
        safe_log(
            "warning", "Erreur validation création évaluation P1",
            error=str(e),
            evaluator_id=str(current_user.get("_id", current_user.get("id")))
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        safe_log(
            "error", "Erreur création évaluation P1",
            error=str(e),
            evaluator_id=str(current_user.get("_id", current_user.get("id")))
        )
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get(
    "/protocol1/{evaluation_id}",
    response_model=Protocol1EvaluationResponse,
    summary="Récupérer une évaluation Protocole 1 par ID",
    openapi_extra={
        "responses": {
            "200": {"content": {"application/json": {"example": {
                "id": "uuid", "application_id": "uuid"
            }}}},
            "404": {"description": "Non trouvée"}
        }
    }
)
async def get_protocol1_evaluation(
    evaluation_id: str,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Récupérer une évaluation Protocol 1 par son ID

    - **evaluation_id**: ID unique de l'évaluation
    """
    try:
        evaluation_service = EvaluationService(db)
        result = await evaluation_service.\
            get_protocol1_evaluation(evaluation_id)
        safe_log("info", "Évaluation Protocol 1 récupérée",
                 evaluation_id=evaluation_id)
        return result
    except NotFoundError as e:
        safe_log("warning", "Évaluation P1 non trouvée", evaluation_id=evaluation_id)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur évaluation P1",
                 evaluation_id=evaluation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne")


@router.put("/protocol1/{evaluation_id}",
            response_model=Protocol1EvaluationResponse,
            summary="MAJ évaluation Protocole 1",
            openapi_extra={
    "responses": {"200": {"description": "Évaluation mise à jour"}}
})
async def update_protocol1_evaluation(
    evaluation_id: str,
    evaluation_data: Protocol1EvaluationUpdate,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Mettre à jour une évaluation Protocol 1

    - **evaluation_id**: ID de l'évaluation à mettre à jour
    - **evaluation_data**: Données de mise à jour (optionnel)
    """
    try:
        evaluation_service = EvaluationService(db)
        u_id = current_user.get("_id", current_user.get("id"))
        result = await evaluation_service.update_protocol1_evaluation(
            evaluation_id, evaluation_data, str(u_id)
        )
        safe_log("info", "Évaluation Protocol 1 mise à jour",
                 evaluation_id=evaluation_id, evaluator_id=str(u_id))
        return result
    except NotFoundError as e:
        safe_log("warning", "Évaluation P1 non trouvée",
                 evaluation_id=evaluation_id)
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationError, BusinessLogicError) as e:
        safe_log("warning", "Erreur validation MAJ P1",
                 evaluation_id=evaluation_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur MAJ évaluation P1",
                 evaluation_id=evaluation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/protocol1/application/{application_id}",
            response_model=list[Protocol1EvaluationResponse],
            summary="Lister les évaluations Protocole 1 par candidature",
            openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": [
        {"id": "uuid", "application_id": "uuid"}
    ]}}}}
})
async def get_protocol1_evaluations_by_application(
    application_id: str,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Récupérer les évaluations Protocol 1 pour une candidature

    - **application_id**: ID de la candidature
    """
    try:
        evaluation_service = EvaluationService(db)
        results = await evaluation_service.\
            get_protocol1_evaluations_by_application(application_id)
        safe_log("info", "Évaluations Protocol 1 récupérées",
                 application_id=application_id, count=len(results))
        return results
    except Exception as e:
        safe_log("error", "Erreur récupération évaluations P1",
                 application_id=application_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne")


# Protocol 2 Evaluation Endpoints
@router.post(
    "/protocol2",
    response_model=Protocol2EvaluationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une évaluation Protocole 2",
    openapi_extra={
        "requestBody": {"content": {"application/json": {"example": {
            "application_id": "uuid", "evaluator_id": "uuid", "qcm_role_score": 17
        }}}},
        "responses": {"201": {"content": {"application/json": {"example": {
            "id": "uuid", "application_id": "uuid", "qcm_role_score": 17
        }}}}}
    }
)
async def create_protocol2_evaluation(
    evaluation_data: Protocol2EvaluationCreate,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Créer une nouvelle évaluation Protocol 2

    - **application_id**: ID de la candidature
    - **technical_skills_score**: Score de compétences techniques
    - **soft_skills_score**: Score de compétences comportementales
    - **cultural_fit_score**: Score d'adaptation culturelle
    - **leadership_potential_score**: Score de potentiel de leadership
    - **recommendation**: Recommandation
    - **additional_notes**: Notes additionnelles (optionnel)
    """
    try:
        evaluation_service = EvaluationService(db)
        result = await evaluation_service.create_protocol2_evaluation(
            evaluation_data, str(u_id)
        )
        if isinstance(result, dict):
            e_id = result.get("id", "N/A")
        else:
            e_id = getattr(result, 'id', 'N/A')
        safe_log(
            "info", "Évaluation Protocol 2 créée",
            evaluation_id=str(e_id), evaluator_id=str(u_id)
        )
        return result
    except (ValidationError, BusinessLogicError) as e:
        safe_log("warning", "Erreur validation création évaluation P2",
                 error=str(e),
                 evaluator_id=str(current_user.get("_id", current_user.get("id"))))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur création évaluation P2",
                 error=str(e),
                 evaluator_id=str(current_user.get("_id", current_user.get("id"))))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/protocol2/{evaluation_id}",
            response_model=Protocol2EvaluationResponse,
            summary="Récupérer une évaluation Protocole 2 par ID",
            openapi_extra={
    "responses": {
        "200": {"content": {"application/json": {"example": {
            "id": "uuid", "application_id": "uuid"
        }}}},
        "404": {"description": "Non trouvée"}
    }
})
async def get_protocol2_evaluation(
    evaluation_id: str,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Récupérer une évaluation Protocol 2 par son ID

    - **evaluation_id**: ID unique de l'évaluation
    """
    try:
        evaluation_service = EvaluationService(db)
        result = await evaluation_service.get_protocol2_evaluation(evaluation_id)
        safe_log("info", "Évaluation Protocol 2 récupérée", evaluation_id=evaluation_id)
        return result
    except NotFoundError as e:
        safe_log("warning", "Évaluation P2 non trouvée", evaluation_id=evaluation_id)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur évaluation P2", evaluation_id=evaluation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.put("/protocol2/{evaluation_id}",
            response_model=Protocol2EvaluationResponse,
            summary="MAJ évaluation Protocole 2",
            openapi_extra={
    "responses": {"200": {"description": "Évaluation mise à jour"}}
})
async def update_protocol2_evaluation(
    evaluation_id: str,
    evaluation_data: Protocol2EvaluationUpdate,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """Mettre à jour une évaluation Protocol 2"""
    try:
        evaluation_service = EvaluationService(db)
        u_id = current_user.get("_id", current_user.get("id"))
        result = await evaluation_service.update_protocol2_evaluation(
            evaluation_id, evaluation_data, str(u_id)
        )
        safe_log("info", "Évaluation Protocol 2 mise à jour",
                 evaluation_id=evaluation_id, evaluator_id=str(u_id))
        return result
    except NotFoundError as e:
        safe_log("warning", "Évaluation P2 non trouvée pour MAJ",
                 evaluation_id=evaluation_id)
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationError, BusinessLogicError) as e:
        safe_log("warning", "Erreur validation MAJ évaluation P2",
                 evaluation_id=evaluation_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur MAJ évaluation P2",
                 evaluation_id=evaluation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/protocol2/application/{application_id}",
            response_model=list[Protocol2EvaluationResponse],
            summary="Lister les évaluations Protocole 2 par candidature",
            openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": [
        {"id": "uuid", "application_id": "uuid"}
    ]}}}}
})
async def get_protocol2_evaluations_by_application(
    application_id: str,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Récupérer les évaluations Protocol 2 pour une candidature

    - **application_id**: ID de la candidature
    """
    try:
        evaluation_service = EvaluationService(db)
        results = await evaluation_service.\
            get_protocol2_evaluations_by_application(application_id)
        safe_log("info", "Évaluations Protocol 2 récupérées",
                 application_id=application_id, count=len(results))
        return results
    except Exception as e:
        safe_log("error", "Erreur évaluations P2",
                 application_id=application_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne")


# Statistics Endpoint
@router.get("/stats/overview",
            response_model=dict,
            summary="Stats globales évaluations",
            openapi_extra={
    "responses": {"200": {"description": "Statistiques récupérées"}}
})
async def get_evaluation_statistics(
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """Récupérer les statistiques des évaluations."""
    try:
        evaluation_service = EvaluationService(db)
        stats = await evaluation_service.get_evaluation_statistics()
        u_id = str(current_user.get("_id", current_user.get("id")))
        safe_log("info", "Statistiques récupérées", requester_id=u_id)
        return stats
    except Exception as e:
        safe_log("error", "Erreur stats eval", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne")
