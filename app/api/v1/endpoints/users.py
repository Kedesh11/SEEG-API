"""
Endpoints de gestion des utilisateurs.
Respecte le principe de responsabilité unique (Single Responsibility
Principle).
"""

from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer

from app.db.database import get_db
from app.core.dependencies import get_current_user as core_get_current_user
from app.schemas.base import ResponseSchema
from app.schemas.user import (
    UserResponse,
    UserUpdate,
    CandidateProfileResponse,
    CandidateProfileUpdate,
    UserWithProfile,
)
from app.services.user import UserService
from app.core.exceptions import NotFoundError, ValidationError
import structlog

router = APIRouter(
    tags=["👥 Utilisateurs"],
)
security_scheme = HTTPBearer()

logger = structlog.get_logger(__name__)


def safe_log(level: str, message: str, **kwargs):
    """Log avec gestion d'erreur pour éviter les problèmes de handler."""
    try:
        getattr(logger, level)(message, **kwargs)
    except (TypeError, AttributeError):
        print(f"{level.upper()}: {message} - {kwargs}")


async def get_current_user(current_user=Depends(core_get_current_user)):
    return current_user


@router.get(
    "/me",
    response_model=ResponseSchema[UserWithProfile],
    summary="Récupérer mon profil",
    openapi_extra={
        "responses": {
            "200": {
                "description": (
                    "Informations complètes de l'utilisateur avec profil candidat"
                ),
                "content": {
                    "application/json": {
                        "example": {
                            "success": True,
                            "message": "Informations utilisateur récupérées",
                            "data": {
                                "id": "uuid",
                                "email": "candidate@example.com",
                                "first_name": "Jean",
                                "last_name": "Dupont",
                                "role": "candidate",
                                "is_active": True,
                                "candidate_profile": {"id": "profile-uuid"},
                            },
                        }
                    }
                },
            }
        }
    },
)
async def get_current_user_info(
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """Récupère les informations complètes de l'utilisateur."""
    try:
        user_service = UserService(db)

        # Récupérer le profil candidat si c'est un candidat
        candidate_profile = None
        if current_user.get("role") == "candidate":
            user_id = str(current_user.get("_id", current_user.get("id")))
            candidate_profile = await user_service.get_candidate_profile(user_id)

        # Créer la réponse avec profil
        u_resp = UserResponse.model_validate(current_user)
        user_dict = u_resp.model_dump()
        if candidate_profile:
            cp_resp = CandidateProfileResponse.model_validate(candidate_profile)
            user_dict["candidate_profile"] = cp_resp.model_dump()
        else:
            user_dict["candidate_profile"] = None

        safe_log(
            "info",
            "Informations utilisateur récupérées",
            user_id=str(current_user.get("_id", current_user.get("id"))),
            has_profile=candidate_profile is not None,
        )

        return ResponseSchema(
            success=True,
            message="Informations utilisateur récupérées",
            data=user_dict
        )
    except Exception as e:
        safe_log(
            "error",
            "Erreur récupération infos utilisateur",
            user_id=str(current_user.get("_id", current_user.get("id"))),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération du profil"
        )


@router.put(
    "/me",
    response_model=ResponseSchema[UserWithProfile],
    summary="Mettre à jour mon profil",
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {"example": {"first_name": "Jean"}},
            }
        },
        "responses": {
            "200": {
                "content": {
                    "application/json": {
                        "example": {
                            "success": True,
                            "message": "Profil mis à jour",
                            "data": {"id": "uuid"},
                        }
                    }
                }
            }
        },
    },
)
async def update_current_user(
    user_update: UserUpdate,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """Met à jour les informations de l'utilisateur."""
    try:
        user_service = UserService(db)
        user_id = str(current_user.get("_id", current_user.get("id")))
        updated_user = await user_service.update_user(
            user_id=user_id,
            user_data=user_update
        )

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )

        # ✅ MongoDB update handled by user_service

        # Créer la réponse complète avec profil
        u_id = str(updated_user.get("_id", updated_user.get("id")))
        candidate_profile = None
        if updated_user.get("role") == "candidate":
            candidate_profile = await user_service.get_candidate_profile(u_id)

        u_resp = UserResponse.model_validate(updated_user)
        user_dict = u_resp.model_dump()
        if candidate_profile:
            cp_resp = CandidateProfileResponse.model_validate(candidate_profile)
            user_dict["candidate_profile"] = cp_resp.model_dump()
        else:
            user_dict["candidate_profile"] = None

        safe_log(
            "info",
            "Profil utilisateur mis à jour",
            user_id=user_id,
            has_profile=candidate_profile is not None,
        )

        return ResponseSchema(
            success=True,
            message="Profil mis à jour",
            data=user_dict
        )

    except HTTPException:
        raise
    except ValidationError as e:
        safe_log(
            "warning",
            "Erreur validation MAJ profil",
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur MAJ profil", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la mise à jour du profil"
        )


@router.get(
    "/{user_id}",
    response_model=ResponseSchema[UserWithProfile],
    summary="Récupérer un utilisateur par ID avec profil complet",
    openapi_extra={
        "responses": {
            "200": {
                "description": (
                    "Informations complètes de l'utilisateur avec profil candidat"
                ),
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
                                    "skills": ["Python", "React"],
                                },
                            },
                        }
                    }
                },
            },
            "403": {"description": "Permission insuffisante"},
            "404": {"description": "Utilisateur non trouvé"},
        }
    },
)
async def get_user_by_id(
    user_id: Any,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Récupère un utilisateur par son ID avec toutes ses informations.

    **Permissions:**
    - L'utilisateur peut voir son propre profil
    - Les recruteurs et admins peuvent voir tous les profils
    """
    try:
        current_user_id = str(current_user.get("_id", current_user.get("id")))
        # Vérifier les permissions - Recruteur, Admin ou soi-même
        if (
            current_user_id != str(user_id)
            and current_user.get("role") not in ["admin", "recruiter"]
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission insuffisante."
            )

        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )

        # Récupérer le profil candidat si c'est un candidat
        u_id = str(user.get("_id", user.get("id")))
        candidate_profile = None
        if user.get("role") == "candidate":
            candidate_profile = await user_service.get_candidate_profile(u_id)

        u_resp = UserResponse.model_validate(user)
        user_dict = u_resp.model_dump()
        if candidate_profile:
            cp_resp = CandidateProfileResponse.model_validate(candidate_profile)
            user_dict["candidate_profile"] = cp_resp.model_dump()
        else:
            user_dict["candidate_profile"] = None

        safe_log(
            "info",
            "Utilisateur récupéré avec profil",
            target_user_id=str(user_id),
            requester_id=current_user_id,
            has_profile=candidate_profile is not None,
        )

        return ResponseSchema(
            success=True,
            message="Utilisateur récupéré avec succès",
            data=user_dict
        )

    except HTTPException:
        raise
    except NotFoundError as e:
        safe_log("warning", "Utilisateur non trouvé", user_id=str(user_id))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        safe_log("error", "Erreur récupération utilisateur",
                 user_id=str(user_id), error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la récupération de l'utilisateur"
        )


@router.get(
    "/",
    summary="Lister les utilisateurs",
    openapi_extra={
        "responses": {
            "200": {
                "description": "Liste paginée",
                "content": {
                    "application/json": {
                        "example": {
                            "success": True,
                            "message": "Utilisateurs récupérés",
                            "data": [{"id": "uuid", "email": "admin@example.com"}],
                            "total": 5, "page": 1, "per_page": 100
                        }
                    }
                }
            }
        }
    }
)
async def get_users(
    skip: int = Query(0, ge=0, description="Nombre d'éléments à ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum d'éléments"),
    role: Optional[str] = Query(None, description="Filtre par rôle"),
    q: Optional[str] = Query(None, description="Recherche texte (nom, email)"),
    sort: Optional[str] = Query(
        None,
        description="Champ de tri (first_name, last_name, email, created_at)",
    ),
    order: Optional[str] = Query("desc", description="Ordre de tri: asc|desc"),
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """Récupère la liste des utilisateurs."""
    try:
        if current_user.get("role") != "admin":
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

        safe_log(
            "info",
            "Liste utilisateurs récupérée",
            requester_id=str(current_user.get("_id", current_user.get("id"))),
            count=total,
        )

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
        safe_log(
            "error",
            "Erreur récupération liste utilisateurs",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des utilisateurs"
        )


@router.delete(
    "/{user_id}",
    response_model=ResponseSchema[None],
    summary="Supprimer un utilisateur",
    openapi_extra={
        "responses": {
            "200": {"description": "Utilisateur supprimé"},
            "404": {"description": "Utilisateur non trouvé"},
        }
    },
)
async def delete_user(
    user_id: Any,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """Supprime un utilisateur (suppression logique)."""
    try:
        current_user_id = str(current_user.get("_id", current_user.get("id")))
        # Verifier les permissions
        if current_user_id != str(user_id) and current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission insuffisante"
            )

        # Empécher l'auto-suppression pour les admins
        if current_user_id == str(user_id) and current_user.get("role") == "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un administrateur ne peut pas se supprimer lui-même"
            )

        user_service = UserService(db)
        success = await user_service.delete_user(user_id=user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )

        safe_log(
            "info",
            "Utilisateur supprimé",
            user_id=str(user_id),
            deleted_by=current_user_id,
        )
        return ResponseSchema(
            success=True,
            message="Utilisateur supprimé",
            data=None
        )

    except HTTPException:
        raise
    except NotFoundError as e:
        safe_log(
            "warning",
            "Tentative suppression utilisateur inexistant",
            user_id=str(user_id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        safe_log(
            "error",
            "Erreur suppression utilisateur",
            user_id=str(user_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la suppression de l'utilisateur"
        )


@router.get(
    "/me/profile",
    response_model=ResponseSchema[CandidateProfileResponse],
    summary="Mon profil candidat",
    openapi_extra={
        "responses": {
            "200": {"description": "Profil récupéré"},
            "404": {"description": "Profil non trouvé"},
        }
    },
)
async def get_current_user_profile(
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """Récupérer le profil candidat de l'utilisateur actuel."""
    try:
        current_user_id = str(current_user.get("_id", current_user.get("id")))
        if current_user.get("role") != "candidate":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seuls les candidats ont un profil candidat"
            )

        user_service = UserService(db)
        candidate_profile = await user_service.get_candidate_profile(current_user_id)

        if not candidate_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profil candidat non trouvé"
            )

        safe_log("info", "Profil candidat récupéré", user_id=current_user_id)
        return ResponseSchema(
            success=True,
            message="Profil candidat récupéré",
            data=CandidateProfileResponse.model_validate(candidate_profile)
        )

    except HTTPException:
        raise
    except NotFoundError as e:
        safe_log("warning", "Profil candidat non trouvé", user_id=current_user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        safe_log(
            "error",
            "Erreur profil candidat",
            user_id=current_user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la récupération du profil candidat"
        )


@router.put(
    "/me/profile",
    response_model=ResponseSchema[UserWithProfile],
    summary="MAJ profil candidat",
    openapi_extra={"responses": {"200": {"description": "Profil mis à jour"}}},
)
async def update_current_user_profile(
    profile_update: CandidateProfileUpdate,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
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
        current_user_id = str(current_user.get("_id", current_user.get("id")))
        # 📊 LOG: Début de requête
        update_fields = list(profile_update.dict(exclude_unset=True).keys())
        safe_log(
            "info",
            "🚀 Début mise à jour profil candidat",
            user_id=current_user_id,
            user_role=current_user.get("role"),
            fields_count=len(update_fields),
            fields=update_fields,
        )

        # 🔐 Vérification permissions
        if current_user.get("role") != "candidate":
            safe_log(
                "warning",
                "❌ Accès refusé - Utilisateur non candidat",
                user_id=current_user_id,
                user_role=current_user.get("role"),
            )
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
            user_id=current_user_id,
            profile_data=profile_update
        )

        if not updated_profile:
            safe_log(
                "error",
                "❌ Profil candidat introuvable",
                user_id=current_user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Profil candidat non trouvé. Veuillez d'abord postuler à une offre."
                ),
            )

        safe_log("debug", "✅ Profil mis à jour en mémoire")

        # Note: MongoDB requires less explicit flush/refresh

        # 📊 LOG: Performance
        duration = time.time() - start_time
        safe_log(
            "info",
            "⏱️ Performance update_profile",
            duration_seconds=round(duration, 3),
            fields_updated=len(update_fields),
        )

        safe_log(
            "info",
            "✅ SUCCESS - Profil candidat mis à jour",
            user_id=current_user_id,
            total_duration=round(duration, 3),
        )

        # 🎯 Retourner l'utilisateur complet avec le profil candidat
        u_resp = UserResponse.model_validate(current_user)
        user_dict = u_resp.model_dump()
        cp_resp = CandidateProfileResponse.model_validate(updated_profile)
        user_dict["candidate_profile"] = cp_resp.model_dump()

        return ResponseSchema(
            success=True,
            message="Profil candidat mis à jour avec succès",
            data=user_dict
        )

    except HTTPException as he:
        # 🔴 LOG: Erreur HTTP
        safe_log(
            "warning",
            "⚠️ HTTPException dans update_profile",
            user_id=current_user_id,
            status_code=he.status_code,
            detail=he.detail,
        )
        raise
    except ValidationError as e:
        # 🔴 LOG: Erreur validation
        safe_log(
            "warning",
            "⚠️ Erreur validation MAJ profil candidat",
            user_id=current_user_id,
            error_type="ValidationError",
            error=str(e),
            fields=update_fields,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        # 🔴 LOG: Erreur critique
        import traceback
        safe_log(
            "error",
            "❌ ERREUR CRITIQUE - update_profile",
            user_id=current_user_id,
            error_type=type(e).__name__,
            error_message=str(e),
            traceback=traceback.format_exc(),
            fields=update_fields,
            duration_seconds=round(time.time() - start_time, 3),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne: {str(e)}"
        )
