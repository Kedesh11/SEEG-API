"""
Endpoints d'authentification - Système unique et robuste
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import structlog
from pydantic import ValidationError
from app.services.auth import AuthService, UnauthorizedError

from app.db.session import get_async_session as get_async_db_session
from app.schemas.auth import (
    LoginRequest, CandidateSignupRequest, CreateUserRequest, TokenResponse, 
    RefreshTokenRequest, PasswordResetRequest, PasswordResetConfirm, ChangePasswordRequest
)
from app.schemas.user import UserResponse
from app.services.auth import AuthService
from app.core.dependencies import get_current_active_user, get_current_admin_user
from app.models.user import User
from sqlalchemy import select
from app.core.dependencies import get_current_user
from app.schemas.auth import MatriculeVerificationResponse
from app.models.seeg_agent import SeegAgent
from app.core.security.security import TokenManager
from app.core.rate_limit import limiter, AUTH_LIMITS, SIGNUP_LIMITS, DEFAULT_LIMITS

logger = structlog.get_logger(__name__)
router = APIRouter()


async def _login_core(email: str, password: str, db: AsyncSession) -> TokenResponse:
    try:
        auth_service = AuthService(db)
        user = await auth_service.authenticate_user(email, password)
        if not user:
            logger.warning("Tentative de connexion avec des identifiants incorrects", email=email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )
        tokens = await auth_service.create_access_token(user)
        logger.info(
            "Connexion réussie",
            user_id=str(user.id),
            email=user.email,
            role=user.role,
        )
        return tokens
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de la connexion", error=str(e), email=email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur",
        )


@router.post("/token", response_model=TokenResponse, summary="Obtenir un token (déprécié)", include_in_schema=False)
async def login_token_deprecated(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_db_session),
):
    """
    Déprécié: utiliser /api/v1/auth/login
    Reste compatible pour les clients OAuth2 (form-urlencoded)
    """
    return await _login_core(form_data.username, form_data.password, db)


@router.post("/login", response_model=TokenResponse, summary="Connexion utilisateur (JSON ou form)", openapi_extra={
    "requestBody": {
        "content": {
            "application/json": {
                "example": {"email": "candidate@example.com", "password": "MotdepasseFort123!"}
            },
            "application/x-www-form-urlencoded": {
                "schema": {"type": "object", "properties": {"username": {"type": "string"}, "password": {"type": "string"}}},
                "example": {"username": "candidate@example.com", "password": "MotdepasseFort123!"}
            }
        }
    },
    "responses": {
        "200": {
            "content": {"application/json": {"example": {"access_token": "<jwt>", "refresh_token": "<jwt>", "token_type": "bearer", "expires_in": 3600}}}
        },
        "401": {"description": "Email ou mot de passe incorrect"},
        "429": {"description": "Trop de tentatives de connexion"}
    }
})
@limiter.limit(AUTH_LIMITS)
async def login(
    request: Request,
    db: AsyncSession = Depends(get_async_db_session),
):
    """
    Connexion d'un utilisateur via un unique endpoint qui accepte:
    - application/json: {"email": ..., "password": ...}
    - application/x-www-form-urlencoded: username=email, password=...
    """
    try:
        # 1) Si un Authorization: Bearer <token> est fourni et valide, retourner directement de nouveaux tokens
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            try:
                token = auth_header.split(" ", 1)[1].strip()
                payload = TokenManager.verify_token(token)
                if payload and payload.get("sub"):
                    user_id = payload["sub"]
                    result = await db.execute(select(User).where(User.id == user_id))
                    user = result.scalar_one_or_none()
                    if user:
                        auth_service = AuthService(db)
                        return await auth_service.create_access_token(user)
            except Exception:
                # Ignore et poursuivre le flux normal (email/password)
                pass

        content_type = request.headers.get("content-type", "").lower()
        email = None
        password = None

        if content_type.startswith("application/x-www-form-urlencoded") or content_type.startswith("multipart/form-data"):
            form = await request.form()
            email = (form.get("username") or form.get("email") or "").strip()
            password = (form.get("password") or "").strip()
        else:
            body = await request.json()
            email = (body.get("email") or body.get("username") or "").strip()
            password = (body.get("password") or "").strip()

        if not email or not password:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="email/username et password requis")

        return await _login_core(email, password, db)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de la connexion unifiée", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur",
        )


@router.post("/signup", response_model=UserResponse, summary="Inscription candidat", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {
        "email": "new.candidate@seeg.ga",
        "password": "Password#2025",
        "first_name": "Aïcha",
        "last_name": "Mouketou",
        "matricule": 123456,
        "phone": "+24106223344",
        "date_of_birth": "1994-06-12",
        "sexe": "F"
    }}}},
    "responses": {
        "200": {"description": "Utilisateur créé", "content": {"application/json": {"example": {"id": "uuid", "email": "new.candidate@seeg.ga", "role": "candidate"}}}},
        "429": {"description": "Trop de tentatives d'inscription"}
    }
})
@limiter.limit(SIGNUP_LIMITS)
async def signup_candidate(
    request: Request,
    signup_data: CandidateSignupRequest,
    db: AsyncSession = Depends(get_async_db_session)
):
    """
    Inscription d'un candidat (public)
    
    Args:
        signup_data: Données d'inscription du candidat
        db: Session de base de données
        
    Returns:
        UserResponse: Informations du candidat créé
        
    Raises:
        HTTPException: Si l'inscription échoue
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.create_candidate(signup_data)
        logger.info("Inscription candidat réussie", user_id=str(user.id), email=user.email)
        return UserResponse.from_orm(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de l'inscription candidat", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.post("/create-user", response_model=UserResponse, summary="Créer un utilisateur (admin/recruteur)")
async def create_user(
    user_data: CreateUserRequest,
    db: AsyncSession = Depends(get_async_db_session),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Créer un utilisateur (admin/recruteur) - admin seulement
    """
    try:
        auth_service = AuthService(db)
        user = await auth_service.create_user(user_data)
        logger.info(
            "Utilisateur créé par admin",
            user_id=str(user.id),
            email=user.email,
            role=user.role,
            created_by=str(current_admin.id),
        )
        return UserResponse.from_orm(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de la création d'utilisateur", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.post("/create-first-admin", response_model=UserResponse, summary="Créer le premier administrateur")
async def create_first_admin(
    db: AsyncSession = Depends(get_async_db_session)
):
    try:
        result = await db.execute(select(User).where(User.role == "admin"))
        existing_admin = result.scalar_one_or_none()
        if existing_admin:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Un administrateur existe déjà")
        auth_service = AuthService(db)
        hashed_password = auth_service.password_manager.hash_password("Sevan@Seeg")
        admin = User(
            email="sevankedesh11@gmail.com",
            first_name="Sevan Kedesh",
            last_name="IKISSA PENDY",
            role="admin",
            hashed_password=hashed_password,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        logger.info("Premier administrateur créé", user_id=str(admin.id), email=admin.email)
        return UserResponse.from_orm(admin)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de la création du premier admin", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.get("/me", response_model=UserResponse, summary="Obtenir le profil de l'utilisateur connecté", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"id": "uuid", "email": "candidate@example.com", "role": "candidate"}}}}}
})
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    logger.debug("Profil utilisateur demandé", user_id=str(current_user.id), email=current_user.email)
    return UserResponse.from_orm(current_user)


@router.post("/refresh", response_model=TokenResponse, summary="Rafraîchir le token d'accès", openapi_extra={
    "requestBody": {
        "content": {
            "application/json": {
                "example": {"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
            }
        }
    },
    "responses": {
        "200": {
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIs...",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
                        "token_type": "bearer",
                        "expires_in": 3600
                    }
                }
            }
        },
        "401": {"description": "Token de rafraîchissement invalide ou expiré"},
        "429": {"description": "Trop de tentatives de rafraîchissement"}
    }
})
@limiter.limit(AUTH_LIMITS)
async def refresh_token(
    request: Request,
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_db_session),
):
    """
    Rafraîchir le token d'accès en utilisant le token de rafraîchissement
    
    - **refresh_token**: Token de rafraîchissement valide obtenu lors de la connexion
    
    Retourne un nouveau token d'accès et un nouveau token de rafraîchissement.
    """
    try:
        # Vérifier le refresh token
        token_manager = TokenManager()
        payload_data = token_manager.verify_token(payload.refresh_token)
        
        if not payload_data:
            logger.warning("Tentative de refresh avec token invalide")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de rafraîchissement invalide",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Vérifier que c'est bien un refresh token
        if payload_data.get("type") != "refresh":
            logger.warning("Tentative de refresh avec un token d'accès")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Type de token incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Récupérer l'utilisateur
        user_id = payload_data.get("sub")
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning("Utilisateur non trouvé lors du refresh", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utilisateur non trouvé",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Vérifier que le compte est actif
        if not user.is_active:
            logger.warning("Tentative de refresh pour compte désactivé", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Compte désactivé",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Créer de nouveaux tokens
        auth_service = AuthService(db)
        tokens = await auth_service.create_access_token(user)
        
        logger.info("Token rafraîchi avec succès", user_id=str(user.id), email=user.email)
        
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors du rafraîchissement du token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur",
        )


@router.post("/logout", summary="Déconnexion")
async def logout():
    logger.info("Déconnexion utilisateur")
    return {"message": "Déconnexion réussie"}


@router.get("/verify-matricule", response_model=MatriculeVerificationResponse, summary="Vérifier le matricule de l'utilisateur connecté", openapi_extra={
    "responses": {
        "200": {
            "content": {
                "application/json": {
                    "examples": {
                        "valide": {"summary": "Matricule valide", "value": {"valid": True, "agent_matricule": "123456"}},
                        "invalide": {"summary": "Matricule invalide", "value": {"valid": False, "reason": "Matricule non trouvé dans seeg_agents"}}
                    }
                }
            }
        }
    }
})
async def verify_matricule(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db_session)
):
    """
    Vérifie que le matricule fourni lors de l'inscription correspond à un agent actif dans la table seeg_agents.
    Autorise uniquement les rôles candidats.
    """
    if current_user.role != "candidate":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accessible uniquement aux candidats")

    if not current_user.matricule:
        return MatriculeVerificationResponse(valid=False, reason="Aucun matricule enregistré pour cet utilisateur")

    try:
        # Cast matricule to integer to match seeg_agents.matricule type
        try:
            matricule_int = int(str(current_user.matricule).strip())
        except ValueError:
            return MatriculeVerificationResponse(valid=False, reason="Matricule invalide (doit être numérique)")

        result = await db.execute(select(SeegAgent).where(SeegAgent.matricule == matricule_int))
        agent = result.scalar_one_or_none()
        if agent:
            return MatriculeVerificationResponse(valid=True, agent_matricule=str(agent.matricule))
        return MatriculeVerificationResponse(valid=False, reason="Matricule non trouvé dans seeg_agents")
    except Exception as e:
        logger.error("Erreur de vérification de matricule", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.post("/forgot-password", summary="Demander la réinitialisation du mot de passe", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"email": "user@example.com"}}}},
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Email envoyé si l'adresse existe"}}}}}
})
async def forgot_password(
    payload: PasswordResetRequest,
    db: AsyncSession = Depends(get_async_db_session),
):
    try:
        service = AuthService(db)
        await service.reset_password_request(payload.email)
        return {"success": True, "message": "Email envoyé si l'adresse existe"}
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.post("/reset-password", summary="Confirmer la réinitialisation du mot de passe", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"token": "<token>", "new_password": "NouveauMotDePasse123!"}}}},
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Mot de passe réinitialisé"}}}}, "400": {"description": "Token invalide ou expiré"}}
})
async def reset_password(
    payload: PasswordResetConfirm,
    db: AsyncSession = Depends(get_async_db_session),
):
    try:
        service = AuthService(db)
        await service.reset_password_confirm(payload.token, payload.new_password)
        return {"success": True, "message": "Mot de passe réinitialisé"}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.post("/change-password", summary="Changer le mot de passe (connecté)", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"current_password": "Ancien123!", "new_password": "Nouveau123!"}}}},
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Mot de passe modifié"}}}}, "401": {"description": "Mot de passe actuel incorrect"}}
})
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
):
    try:
        service = AuthService(db)
        await service.change_password(str(current_user.id), payload.current_password, payload.new_password)
        return {"success": True, "message": "Mot de passe modifié"}
    except UnauthorizedError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")
