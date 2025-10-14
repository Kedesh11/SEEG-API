"""
Endpoints de gestion des utilisateurs.
Respecte le principe de responsabilitÃ© unique (Single Responsibility Principle).
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.security import TokenManager
from app.core.logging.logging import security_logger
from app.db.database import get_db
from app.core.dependencies import get_current_user as core_get_current_user
from app.schemas.base import ResponseSchema, PaginatedResponse, PaginationSchema
from app.schemas.user import UserResponse, UserUpdate, CandidateProfileResponse
from app.services.user import UserService
from app.services.auth import AuthService
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError
import structlog

router = APIRouter()
security_scheme = HTTPBearer()

logger = structlog.get_logger(__name__)


def safe_log(level: str, message: str, **kwargs):
    """Log avec gestion d'erreur pour Ã©viter les problÃ¨mes de handler."""
    try:
        getattr(logger, level)(message, **kwargs)
    except (TypeError, AttributeError):
        print(f"{level.upper()}: {message} - {kwargs}")


async def get_current_user(current_user = Depends(core_get_current_user)):
    return current_user


@router.get("/me", response_model=ResponseSchema[UserResponse], summary="RÃ©cupÃ©rer mon profil utilisateur", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Informations utilisateur rÃ©cupÃ©rÃ©es", "data": {"id": "uuid", "email": "user@seeg.ga"}}}}}}
})
async def get_current_user_info(
    current_user = Depends(get_current_user)
):
    """RÃ©cupÃ¨re les informations de l'utilisateur actuel."""
    safe_log("info", "Informations utilisateur rÃ©cupÃ©rÃ©es", user_id=str(current_user.id))
    return ResponseSchema(
        success=True,
        message="Informations utilisateur rÃ©cupÃ©rÃ©es",
        data=UserResponse.from_orm(current_user)
    )


@router.put("/me", response_model=ResponseSchema[UserResponse], summary="Mettre Ã  jour mon profil utilisateur", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"first_name": "Jean"}}}},
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Profil mis Ã  jour avec succÃ¨s", "data": {"id": "uuid", "first_name": "Jean"}}}}}}
})
async def update_current_user(
    user_update: UserUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Met Ã  jour les informations de l'utilisateur actuel."""
    try:
        user_service = UserService(db)
        updated_user = await user_service.update_user(
            user_id=current_user.id,
            user_data=user_update
        )
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvÃ©"
            )
        
        safe_log("info", "Profil utilisateur mis Ã  jour", user_id=str(current_user.id))
        return ResponseSchema(
            success=True,
            message="Profil mis Ã  jour avec succÃ¨s",
            data=UserResponse.from_orm(updated_user)
        )
        
    except HTTPException:
        raise
    except ValidationError as e:
        safe_log("warning", "Erreur validation MAJ profil", user_id=str(current_user.id), error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur MAJ profil", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la mise Ã  jour du profil"
        )


@router.get("/{user_id}", response_model=ResponseSchema[UserResponse], summary="RÃ©cupÃ©rer un utilisateur par ID", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Utilisateur rÃ©cupÃ©rÃ© avec succÃ¨s", "data": {"id": "uuid"}}}}}, "404": {"description": "Utilisateur non trouvÃ©"}}
})
async def get_user_by_id(
    user_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """RÃ©cupÃ¨re un utilisateur par son ID."""
    try:
        # VÃ©rifier les permissions
        if current_user.id != user_id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission insuffisante"
            )
        
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvÃ©"
            )
        
        safe_log("info", "Utilisateur rÃ©cupÃ©rÃ©", target_user_id=str(user_id), requester_id=str(current_user.id))
        return ResponseSchema(
            success=True,
            message="Utilisateur rÃ©cupÃ©rÃ© avec succÃ¨s",
            data=UserResponse.from_orm(user)
        )
        
    except HTTPException:
        raise
    except NotFoundError as e:
        safe_log("warning", "Utilisateur non trouvÃ©", user_id=str(user_id))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur rÃ©cupÃ©ration utilisateur", user_id=str(user_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la rÃ©cupÃ©ration de l'utilisateur"
        )


@router.get("/", response_model=ResponseSchema[PaginatedResponse[UserResponse]], summary="Lister les utilisateurs (pagination, recherche, tri)", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Utilisateurs rÃ©cupÃ©rÃ©s avec succÃ¨s", "data": {"items": [], "total": 0, "page": 1, "size": 100, "pages": 0, "has_next": False, "has_prev": False}}}}}}
})
async def get_users(
    skip: int = Query(0, ge=0, description="Nombre d'Ã©lÃ©ments Ã  ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum d'Ã©lÃ©ments"),
    role: Optional[str] = Query(None, description="Filtre par rÃ´le"),
    q: Optional[str] = Query(None, description="Recherche texte (nom, email)"),
    sort: Optional[str] = Query(None, description="Champ de tri (first_name, last_name, email, created_at)"),
    order: Optional[str] = Query("desc", description="Ordre de tri: asc|desc"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """RÃ©cupÃ¨re la liste des utilisateurs avec pagination, recherche et tri."""
    try:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission insuffisante"
            )
        user_service = UserService(db)
        users = await user_service.get_users(
            skip=skip,
            limit=limit,
            role=role,
            q=q,
            sort=sort,
            order=order
        )
        user_responses = [UserResponse.from_orm(user) for user in users]
        total = len(user_responses)
        pages = (total + limit - 1) // limit
        current_page = (skip // limit) + 1
        
        safe_log("info", "Liste utilisateurs rÃ©cupÃ©rÃ©e", requester_id=str(current_user.id), count=total)
        return PaginatedResponse(
            success=True,
            message="Utilisateurs recupérés avec succès",
            data=user_responses,
            pagination=PaginationSchema(
                page=current_page,
                per_page=limit,
                total=total,
                pages=pages
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        safe_log("error", "Erreur récupération liste utilisateurs", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des utilisateurs"
        )


@router.delete("/{user_id}", response_model=ResponseSchema[None], summary="Supprimer un utilisateur", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Utilisateur supprimÃ© avec succÃ¨s", "data": None}}}}, "404": {"description": "Utilisateur non trouvÃ©"}}
})
async def delete_user(
    user_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Supprime un utilisateur (suppression logique)."""
    try:
        # Verifier les permissions
        if current_user.id != user_id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission insuffisante"
            )
        
        # Empécher l'auto-suppression pour les admins
        if current_user.id == user_id and current_user.role == "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un administrateur ne peut pas se supprimer lui-mÃªme"
            )
        
        user_service = UserService(db)
        success = await user_service.delete_user(user_id=user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvÃ©"
            )
        
        safe_log("info", "Utilisateur supprimÃ©", user_id=str(user_id), deleted_by=str(current_user.id))
        return ResponseSchema(
            success=True,
            message="Utilisateur supprimÃ© avec succÃ¨s",
            data=None
        )
        
    except HTTPException:
        raise
    except NotFoundError as e:
        safe_log("warning", "Tentative suppression utilisateur inexistant", user_id=str(user_id))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur suppression utilisateur", user_id=str(user_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la suppression de l'utilisateur"
        )


@router.get("/me/profile", response_model=ResponseSchema[CandidateProfileResponse], summary="RÃ©cupÃ©rer mon profil candidat", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Profil candidat rÃ©cupÃ©rÃ© avec succÃ¨s", "data": {"user_id": "uuid"}}}}}, "404": {"description": "Profil candidat non trouvÃ©"}}
})
async def get_current_user_profile(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Récupérer le profil candidat de l'utilisateur actuel."""
    try:
        if current_user.role != "candidate":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seuls les candidats ont un profil candidat"
            )
        
        user_service = UserService(db)
        candidate_profile = await user_service.get_candidate_profile(current_user.id)
        
        if not candidate_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profil candidat non trouvÃ©"
            )
        
        safe_log("info", "Profil candidat rÃ©cupÃ©rÃ©", user_id=str(current_user.id))
        return ResponseSchema(
            success=True,
            message="Profil candidat rÃ©cupÃ©rÃ© avec succÃ¨s",
            data=CandidateProfileResponse.from_orm(candidate_profile)
        )
        
    except HTTPException:
        raise
    except NotFoundError as e:
        safe_log("warning", "Profil candidat non trouvÃ©", user_id=str(current_user.id))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur rÃ©cupÃ©ration profil candidat", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la rÃ©cupÃ©ration du profil candidat"
        )
