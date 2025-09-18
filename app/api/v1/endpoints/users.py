"""
Endpoints de gestion des utilisateurs.
Respecte le principe de responsabilité unique (Single Responsibility Principle).
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.security import TokenManager
from app.core.logging.logging import security_logger
from app.db.database import get_async_db
from app.schemas.base import ResponseSchema, PaginatedResponse
from app.schemas.user import UserResponse, UserUpdate, CandidateProfileResponse
from app.services.user import UserService
from app.services.auth import AuthService

router = APIRouter()
security_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_async_db)
):
    """Dépendance pour récupérer l'utilisateur actuel."""
    try:
        user_id = TokenManager.get_user_id_from_token(credentials.credentials)
        user_service = UserService(db)
        user = await user_service.get_user_by_id(UUID(user_id))
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Compte désactivé"
            )
        
        return user
    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_error(
            operation="GET_CURRENT_USER",
            table="users",
            error=e
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide"
        )


@router.get("/me", response_model=ResponseSchema[UserResponse])
async def get_current_user_info(
    current_user = Depends(get_current_user)
):
    """Récupère les informations de l'utilisateur actuel."""
    return ResponseSchema(
        success=True,
        message="Informations utilisateur récupérées",
        data=UserResponse.from_orm(current_user)
    )


@router.put("/me", response_model=ResponseSchema[UserResponse])
async def update_current_user(
    user_update: UserUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Met à jour les informations de l'utilisateur actuel."""
    try:
        updated_user = await UserService.update_user(
            db=db,
            user_id=current_user.id,
            update_data=user_update
        )
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )
        
        return ResponseSchema(
            success=True,
            message="Profil mis à jour avec succès",
            data=UserResponse.from_orm(updated_user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la mise à jour du profil"
        )


@router.get("/{user_id}", response_model=ResponseSchema[UserResponse])
async def get_user_by_id(
    user_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Récupère un utilisateur par son ID."""
    try:
        # Vérifier les permissions
        if current_user.id != user_id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission insuffisante"
            )
        
        user_service = UserService(db)
        user = await user_service.get_user_by_id(UUID(user_id))
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )
        
        return ResponseSchema(
            success=True,
            message="Utilisateur récupéré avec succès",
            data=UserResponse.from_orm(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de l'utilisateur"
        )


@router.get("/", response_model=ResponseSchema[PaginatedResponse[UserResponse]])
async def get_users(
    skip: int = Query(0, ge=0, description="Nombre d'éléments à ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum d'éléments"),
    role: Optional[str] = Query(None, description="Filtre par rôle"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Récupère la liste des utilisateurs avec pagination."""
    try:
        # Vérifier les permissions (seuls les admins peuvent voir tous les utilisateurs)
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission insuffisante"
            )
        
        users = await UserService.get_users(
            db=db,
            skip=skip,
            limit=limit,
            role=role
        )
        
        # Convertir en schémas de réponse
        user_responses = [UserResponse.from_orm(user) for user in users]
        
        # Calculer le total (simplifié - dans une vraie implémentation, on ferait une requête COUNT)
        total = len(user_responses)
        pages = (total + limit - 1) // limit
        current_page = (skip // limit) + 1
        
        paginated_response = PaginatedResponse(
            items=user_responses,
            total=total,
            page=current_page,
            size=limit,
            pages=pages,
            has_next=current_page < pages,
            has_prev=current_page > 1
        )
        
        return ResponseSchema(
            success=True,
            message="Utilisateurs récupérés avec succès",
            data=paginated_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des utilisateurs"
        )


@router.delete("/{user_id}", response_model=ResponseSchema[None])
async def delete_user(
    user_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Supprime un utilisateur (suppression logique)."""
    try:
        # Vérifier les permissions
        if current_user.id != user_id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission insuffisante"
            )
        
        # Empêcher l'auto-suppression pour les admins
        if current_user.id == user_id and current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un administrateur ne peut pas se supprimer lui-même"
            )
        
        success = await UserService.delete_user(db=db, user_id=user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )
        
        return ResponseSchema(
            success=True,
            message="Utilisateur supprimé avec succès",
            data=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la suppression de l'utilisateur"
        )


@router.get("/me/profile", response_model=ResponseSchema[CandidateProfileResponse])
async def get_current_user_profile(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Récupère le profil candidat de l'utilisateur actuel."""
    try:
        if not current_user.is_candidate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seuls les candidats ont un profil candidat"
            )
        
        user_with_profile = await UserService.get_user_with_profile(db, str(current_user.id))
        
        if not user_with_profile or not user_with_profile.candidate_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profil candidat non trouvé"
            )
        
        return ResponseSchema(
            success=True,
            message="Profil candidat récupéré avec succès",
            data=CandidateProfileResponse.from_orm(user_with_profile.candidate_profile)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération du profil candidat"
        )
