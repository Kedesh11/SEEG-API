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
from app.schemas.user import UserResponse, UserUpdate, CandidateProfileResponse, CandidateProfileUpdate, UserWithProfile
from app.services.user import UserService
from app.services.auth import AuthService
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError
import structlog

router = APIRouter(
    tags=["👥 Utilisateurs"],)
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


@router.get("/me", response_model=ResponseSchema[UserWithProfile], summary="RÃ©cupÃ©rer mon profil utilisateur", openapi_extra={
    "responses": {
        "200": {
            "description": "Informations complètes de l'utilisateur avec profil candidat",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Informations utilisateur récupérées",
                        "data": {'id': 'bf0c73bd-09e0-4aad-afaa-94b16901e916', 'email': 'candidate@example.com', 'first_name': 'Jean', 'last_name': 'Dupont', 'role': 'candidate', 'phone': '+24177012345', 'date_of_birth': '1990-05-15', 'sexe': 'M', 'matricule': 12345, 'email_verified': True, 'last_login': '2025-10-15T10:30:00Z', 'is_active': True, 'is_internal_candidate': True, 'adresse': 'Libreville, Gabon', 'candidate_status': 'actif', 'statut': 'actif', 'poste_actuel': 'Développeur Senior', 'annees_experience': 5, 'no_seeg_email': False, 'created_at': '2025-01-10T08:00:00Z', 'updated_at': '2025-10-15T10:30:00Z', 'candidate_profile': {'id': 'profile-uuid', 'user_id': 'bf0c73bd-09e0-4aad-afaa-94b16901e916', 'years_experience': 5, 'current_position': 'Développeur Senior', 'availability': 'Immédiate', 'skills': ['Python', 'FastAPI', 'React', 'PostgreSQL'], 'expected_salary_min': 800000, 'expected_salary_max': 1200000, 'address': 'Libreville, Gabon', 'linkedin_url': 'https://linkedin.com/in/jeandupont', 'portfolio_url': 'https://portfolio.jeandupont.com', 'created_at': '2025-01-10T08:00:00Z', 'updated_at': '2025-10-15T10:30:00Z'}}
                    }
                }
            }
        }
    }
})
async def get_current_user_info(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """RÃ©cupÃ¨re les informations complètes de l'utilisateur actuel avec son profil candidat."""
    try:
        user_service = UserService(db)
        
        # Récupérer le profil candidat si c'est un candidat
        candidate_profile = None
        if current_user.role == "candidate":  # type: ignore
            candidate_profile = await user_service.get_candidate_profile(current_user.id)
        
        # Créer la réponse avec profil
        user_dict = UserResponse.model_validate(current_user).model_dump()
        user_dict["candidate_profile"] = CandidateProfileResponse.model_validate(candidate_profile).model_dump() if candidate_profile else None
        
        safe_log("info", "Informations utilisateur rÃ©cupÃ©rÃ©es", 
                user_id=str(current_user.id),
                has_profile=candidate_profile is not None)
        
        return ResponseSchema(
            success=True,
            message="Informations utilisateur rÃ©cupÃ©rÃ©es",
            data=user_dict
        )
    except Exception as e:
        safe_log("error", "Erreur récupération infos utilisateur", 
                user_id=str(current_user.id), 
                error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération du profil"
        )


@router.put("/me", response_model=ResponseSchema[UserWithProfile], summary="Mettre Ã  jour mon profil utilisateur", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"first_name": "Jean"}}}},
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Profil mis Ã  jour avec succÃ¨s", "data": {"id": "uuid", "first_name": "Jean", "candidate_profile": {}}}}}}}
})
async def update_current_user(
    user_update: UserUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Met Ã  jour les informations de l'utilisateur actuel et retourne toutes les informations."""
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
        
        # ✅ FLUSH puis COMMIT pour persister les changements
        await db.flush()
        await db.refresh(updated_user)
        await db.commit()
        
        # Récupérer le profil candidat si c'est un candidat
        candidate_profile = None
        if updated_user.role == "candidate":  # type: ignore
            candidate_profile = await user_service.get_candidate_profile(updated_user.id)
        
        # Créer la réponse complète avec profil
        user_dict = UserResponse.model_validate(updated_user).model_dump()
        user_dict["candidate_profile"] = CandidateProfileResponse.model_validate(candidate_profile).model_dump() if candidate_profile else None
        
        safe_log("info", "Profil utilisateur mis Ã  jour", 
                user_id=str(current_user.id),
                has_profile=candidate_profile is not None)
        
        return ResponseSchema(
            success=True,
            message="Profil mis Ã  jour avec succÃ¨s",
            data=user_dict
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


@router.get("/{user_id}", response_model=ResponseSchema[UserWithProfile], summary="RÃ©cupÃ©rer un utilisateur par ID avec profil complet", openapi_extra={
    "responses": {
        "200": {
            "description": "Informations complètes de l'utilisateur avec profil candidat",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Utilisateur récupéré avec succès",
                        "data": {
                            "id": "uuid",
                            "email": "user@example.com",
                            "first_name": "Jean",
                            "last_name": "Dupont",
                            "role": "candidate",
                            "adresse": "Libreville",
                            "annees_experience": 5,
                            "poste_actuel": "Développeur",
                            "candidate_profile": {
                                "years_experience": 5,
                                "skills": ["Python", "React"]
                            }
                        }
                    }
                }
            }
        },
        "403": {"description": "Permission insuffisante"},
        "404": {"description": "Utilisateur non trouvÃ©"}
    }
})
async def get_user_by_id(
    user_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Récupère un utilisateur par son ID avec toutes ses informations.
    
    **Permissions:**
    - L'utilisateur peut voir son propre profil
    - Les recruteurs et admins peuvent voir tous les profils
    """
    try:
        # VÃ©rifier les permissions - Recruteur, Admin ou soi-même
        if current_user.id != user_id and current_user.role not in ["admin", "recruiter"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission insuffisante. Accessible uniquement à l'utilisateur, aux recruteurs et aux administrateurs."
            )
        
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvÃ©"
            )
        
        # Récupérer le profil candidat si c'est un candidat
        candidate_profile = None
        if user.role == "candidate":  # type: ignore
            candidate_profile = await user_service.get_candidate_profile(user.id)
        
        # Créer la réponse complète avec profil
        user_dict = UserResponse.model_validate(user).model_dump()
        user_dict["candidate_profile"] = CandidateProfileResponse.model_validate(candidate_profile).model_dump() if candidate_profile else None
        
        safe_log("info", "Utilisateur rÃ©cupÃ©rÃ© avec profil", 
                target_user_id=str(user_id), 
                requester_id=str(current_user.id),
                has_profile=candidate_profile is not None)
        
        return ResponseSchema(
            success=True,
            message="Utilisateur rÃ©cupÃ©rÃ© avec succÃ¨s",
            data=user_dict
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


@router.get(
    "/",
    summary="Lister les utilisateurs (pagination, recherche, tri)",
    openapi_extra={
        "responses": {
            "200": {
                "description": "Liste paginée des utilisateurs",
                "content": {
                    "application/json": {
                        "example": {
                            'success': True,
                            'message': '5 utilisateur(s) récupéré(s)',
                            'data': [
                                {
                                    'id': 'user-1-uuid',
                                    'email': 'admin@seeg-gabon.com',
                                    'first_name': 'Admin',
                                    'last_name': 'SEEG',
                                    'role': 'admin',
                                    'matricule': 1001,
                                    'statut': 'actif',
                                    'is_active': True
                                },
                                {
                                    'id': 'user-2-uuid',
                                    'email': 'recruiter@seeg-gabon.com',
                                    'first_name': 'Marie',
                                    'last_name': 'RECRUTEUSE',
                                    'role': 'recruiter',
                                    'matricule': 1002,
                                    'statut': 'actif',
                                    'is_active': True
                                }
                            ],
                            'total': 5,
                            'page': 1,
                            'per_page': 100
                        }
                    }
                }
            }
        }
    }
)
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
        user_responses = [UserResponse.model_validate(user) for user in users]
        total = len(user_responses)
        current_page = (skip // limit) + 1
        
        safe_log("info", "Liste utilisateurs rÃ©cupÃ©rÃ©e", requester_id=str(current_user.id), count=total)
        
        # Format de réponse compatible avec ApplicationListResponse
        return {
            "success": True,
            "message": f"{total} utilisateur(s) récupéré(s)",
            "data": user_responses,
            "total": total,
            "page": current_page,
            "per_page": limit
        }
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
            data=CandidateProfileResponse.model_validate(candidate_profile)
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


@router.put("/me/profile", response_model=ResponseSchema[UserWithProfile], summary="Mettre à jour mon profil candidat", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"years_experience": 5, "current_position": "Développeur Senior"}}}},
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Profil candidat mis à jour avec succès", "data": {"id": "uuid", "candidate_profile": {"years_experience": 5}}}}}}}
})
async def update_current_user_profile(
    profile_update: CandidateProfileUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mettre à jour le profil candidat de l'utilisateur actuel.
    
    **Accessible uniquement aux candidats**
    
    Champs modifiables :
    - years_experience : Années d'expérience
    - current_position : Poste actuel
    - current_department : Département actuel
    - skills : Compétences (liste)
    - education : Formation
    - availability : Disponibilité
    - expected_salary_min/max : Salaire attendu
    - LinkedIn, Portfolio URLs
    """
    import time
    start_time = time.time()
    update_fields = []  # Initialiser pour éviter les warnings
    
    try:
        # 📊 LOG: Début de requête
        update_fields = list(profile_update.dict(exclude_unset=True).keys())
        safe_log("info", "🚀 Début mise à jour profil candidat", 
                user_id=str(current_user.id),
                user_role=current_user.role,
                fields_count=len(update_fields),
                fields=update_fields)
        
        # 🔐 Vérification permissions
        if current_user.role != "candidate":
            safe_log("warning", "❌ Accès refusé - Utilisateur non candidat",
                    user_id=str(current_user.id),
                    user_role=current_user.role)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seuls les candidats peuvent modifier leur profil candidat"
            )
        
        safe_log("debug", "✅ Permissions validées")
        
        # 🏗️ Création service
        safe_log("debug", "🏗️ Création UserService...")
        user_service = UserService(db)
        
        # 💾 Mise à jour (le profil doit exister - créé lors de la première candidature)
        safe_log("debug", "💾 Appel update_candidate_profile...")
        updated_profile = await user_service.update_candidate_profile(
            user_id=current_user.id,
            profile_data=profile_update
        )
        
        if not updated_profile:
            safe_log("error", "❌ Profil candidat introuvable",
                    user_id=str(current_user.id))
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profil candidat non trouvé. Veuillez d'abord postuler à une offre."
            )
        
        safe_log("debug", "✅ Profil mis à jour en mémoire")
        
        # 💾 Flush puis Commit
        safe_log("debug", "💾 Flush en base...")
        await db.flush()
        safe_log("debug", "✅ Flush réussi")
        
        # 🔄 Rafraîchir le profil et l'utilisateur pour avoir toutes les infos à jour
        await db.refresh(updated_profile)
        await db.refresh(current_user)
        
        safe_log("debug", "💾 Commit transaction...")
        await db.commit()
        safe_log("debug", "✅ Commit réussi")
        
        # 📊 LOG: Performance
        duration = time.time() - start_time
        safe_log("info", "⏱️ Performance update_profile",
                duration_seconds=round(duration, 3),
                fields_updated=len(update_fields))
        
        safe_log("info", "✅ SUCCESS - Profil candidat mis à jour", 
                user_id=str(current_user.id),
                total_duration=round(duration, 3))
        
        # 🎯 Retourner l'utilisateur complet avec le profil candidat
        user_dict = UserResponse.model_validate(current_user).model_dump()
        user_dict["candidate_profile"] = CandidateProfileResponse.model_validate(updated_profile).model_dump()
        
        return ResponseSchema(
            success=True,
            message="Profil candidat mis à jour avec succès",
            data=user_dict
        )
        
    except HTTPException as he:
        # 🔴 LOG: Erreur HTTP
        safe_log("warning", "⚠️ HTTPException dans update_profile",
                user_id=str(current_user.id),
                status_code=he.status_code,
                detail=he.detail)
        raise
    except ValidationError as e:
        # 🔴 LOG: Erreur validation
        safe_log("warning", "⚠️ Erreur validation MAJ profil candidat", 
                user_id=str(current_user.id),
                error_type="ValidationError",
                error=str(e),
                fields=update_fields)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # 🔴 LOG: Erreur critique
        import traceback
        safe_log("error", "❌ ERREUR CRITIQUE - update_profile", 
                user_id=str(current_user.id),
                error_type=type(e).__name__,
                error_message=str(e),
                traceback=traceback.format_exc(),
                fields=update_fields,
                duration_seconds=round(time.time() - start_time, 3))
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne: {str(e)}"
        )
