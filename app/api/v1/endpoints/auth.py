"""
Endpoints d'authentification
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import structlog

from app.db.session import get_async_session as get_async_db_session
from app.schemas.auth import (
    LoginRequest, SignupRequest, TokenResponse, 
    RefreshTokenRequest, PasswordResetRequest, PasswordResetConfirm
)
from app.schemas.user import UserResponse
from app.services.auth import AuthService
from app.core.dependencies import get_current_active_user
from app.models.user import User

logger = structlog.get_logger(__name__)
router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/login", response_model=TokenResponse, summary="Connexion utilisateur")
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_async_db_session)
):
    """Connexion d'un utilisateur avec email et mot de passe"""
    try:
        auth_service = AuthService(db)
        
        # Authentifier l'utilisateur
        user = await auth_service.authenticate_user(login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Créer les tokens
        tokens = await auth_service.create_access_token(user)
        
        logger.info("Connexion réussie", user_id=str(user.id), email=user.email)
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de la connexion", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )

@router.post("/signup", response_model=UserResponse, summary="Inscription utilisateur")
async def signup(
    signup_data: SignupRequest,
    db: AsyncSession = Depends(get_async_db_session)
):
    """Inscription d'un nouvel utilisateur"""
    try:
        auth_service = AuthService(db)
        
        # Créer l'utilisateur
        user = await auth_service.create_user(signup_data)
        
        logger.info("Inscription réussie", user_id=str(user.id), email=user.email)
        return UserResponse.from_orm(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de l'inscription", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )

@router.get("/me", response_model=UserResponse, summary="Obtenir le profil de l'utilisateur connecté")
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Obtenir le profil de l'utilisateur actuellement connecté"""
    return UserResponse.from_orm(current_user)

@router.post("/logout", summary="Déconnexion")
async def logout():
    """Déconnexion de l'utilisateur"""
    return {"message": "Déconnexion réussie"}
