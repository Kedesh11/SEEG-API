"""
Endpoints d'authentification - Système unique et robuste
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import structlog

from app.db.session import get_async_session as get_async_db_session
from app.schemas.auth import (
    LoginRequest, CandidateSignupRequest, CreateUserRequest, TokenResponse
)
from app.schemas.user import UserResponse
from app.services.auth import AuthService
from app.core.dependencies import get_current_active_user, get_current_admin_user
from app.models.user import User
from sqlalchemy import select
from app.core.dependencies import get_current_user
from app.schemas.auth import MatriculeVerificationResponse
from app.models.seeg_agent import SeegAgent

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.post("/token", response_model=TokenResponse, summary="Obtenir un token (OAuth2 standard)")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_db_session)
):
    """
    Connexion OAuth2 standard pour obtenir un token d'accès
    Compatible avec Swagger UI et clients OAuth2
    
    Args:
        form_data: Données de connexion OAuth2 (username=email, password)
        db: Session de base de données
        
    Returns:
        TokenResponse: Tokens d'accès et de rafraîchissement
        
    Raises:
        HTTPException: Si les identifiants sont incorrects
    """
    try:
        auth_service = AuthService(db)
        
        # Authentifier l'utilisateur (username = email dans notre cas)
        user = await auth_service.authenticate_user(form_data.username, form_data.password)
        if not user:
            logger.warning("Tentative de connexion OAuth2 avec des identifiants incorrects", 
                         email=form_data.username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Créer les tokens
        tokens = await auth_service.create_access_token(user)
        
        logger.info("Connexion OAuth2 réussie", 
                   user_id=str(user.id), 
                   email=user.email,
                   role=user.role)
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de la connexion OAuth2", error=str(e), email=form_data.username)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )

@router.post("/login", response_model=TokenResponse, summary="Connexion utilisateur (JSON)")
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_async_db_session)
):
    """
    Connexion d'un utilisateur avec email et mot de passe (format JSON)
    Pour les clients personnalisés
    
    Args:
        login_data: Données de connexion (email, password)
        db: Session de base de données
        
    Returns:
        TokenResponse: Tokens d'accès et de rafraîchissement
        
    Raises:
        HTTPException: Si les identifiants sont incorrects
    """
    try:
        auth_service = AuthService(db)
        
        # Authentifier l'utilisateur
        user = await auth_service.authenticate_user(login_data.email, login_data.password)
        if not user:
            logger.warning("Tentative de connexion avec des identifiants incorrects", 
                         email=login_data.email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Créer les tokens
        tokens = await auth_service.create_access_token(user)
        
        logger.info("Connexion réussie", 
                   user_id=str(user.id), 
                   email=user.email,
                   role=user.role)
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de la connexion", error=str(e), email=login_data.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )

@router.post("/signup", response_model=UserResponse, summary="Inscription candidat")
async def signup_candidate(
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
        
        # Créer le candidat
        user = await auth_service.create_candidate(signup_data)
        
        logger.info("Inscription candidat réussie", 
                   user_id=str(user.id), 
                   email=user.email)
        return UserResponse.from_orm(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de l'inscription candidat", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )

@router.post("/create-user", response_model=UserResponse, summary="Créer un utilisateur (admin/recruteur)")
async def create_user(
    user_data: CreateUserRequest,
    db: AsyncSession = Depends(get_async_db_session),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Créer un utilisateur (admin/recruteur) - admin seulement
    
    Args:
        user_data: Données de l'utilisateur à créer
        db: Session de base de données
        current_admin: Administrateur authentifié
        
    Returns:
        UserResponse: Informations de l'utilisateur créé
        
    Raises:
        HTTPException: Si la création échoue
    """
    try:
        auth_service = AuthService(db)
        
        # Créer l'utilisateur
        user = await auth_service.create_user(user_data)
        
        logger.info("Utilisateur créé par admin", 
                   user_id=str(user.id), 
                   email=user.email, 
                   role=user.role,
                   created_by=str(current_admin.id))
        return UserResponse.from_orm(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de la création d'utilisateur", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )

@router.post("/create-first-admin", response_model=UserResponse, summary="Créer le premier administrateur")
async def create_first_admin(
    db: AsyncSession = Depends(get_async_db_session)
):
    """
    Créer le premier administrateur (endpoint temporaire)
    
    Args:
        db: Session de base de données
        
    Returns:
        UserResponse: Informations de l'administrateur créé
        
    Raises:
        HTTPException: Si un admin existe déjà ou si la création échoue
    """
    try:
        # Vérifier si un admin existe déjà
        result = await db.execute(
            select(User).where(User.role == "admin")
        )
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un administrateur existe déjà"
            )
        
        # Créer le premier admin
        auth_service = AuthService(db)
        hashed_password = auth_service.password_manager.hash_password("Sevan@Seeg")
        
        admin = User(
            email="sevankedesh11@gmail.com",
            first_name="Sevan Kedesh",
            last_name="IKISSA PENDY",
            role="admin",
            hashed_password=hashed_password
        )
        
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        
        logger.info("Premier administrateur créé", 
                   user_id=str(admin.id), 
                   email=admin.email)
        return UserResponse.from_orm(admin)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur lors de la création du premier admin", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )

@router.get("/me", response_model=UserResponse, summary="Obtenir le profil de l'utilisateur connecté")
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtenir le profil de l'utilisateur actuellement connecté
    
    Args:
        current_user: Utilisateur authentifié
        
    Returns:
        UserResponse: Profil de l'utilisateur
    """
    logger.debug("Profil utilisateur demandé", 
                user_id=str(current_user.id), 
                email=current_user.email)
    return UserResponse.from_orm(current_user)

@router.post("/logout", summary="Déconnexion")
async def logout():
    """
    Déconnexion de l'utilisateur
    
    Returns:
        Dict: Message de confirmation
    """
    logger.info("Déconnexion utilisateur")
    return {"message": "Déconnexion réussie"}

@router.get("/verify-matricule", response_model=MatriculeVerificationResponse, summary="Vérifier le matricule de l'utilisateur connecté")
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
        result = await db.execute(select(SeegAgent).where(SeegAgent.matricule == current_user.matricule))
        agent = result.scalar_one_or_none()
        if agent:
            return MatriculeVerificationResponse(valid=True, agent_matricule=str(agent.matricule))
        return MatriculeVerificationResponse(valid=False, reason="Matricule non trouvé dans seeg_agents")
    except Exception as e:
        logger.error("Erreur de vérification de matricule", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")
