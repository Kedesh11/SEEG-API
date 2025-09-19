"""
Dépendances FastAPI pour l'authentification
Système d'authentification unique et robuste
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import structlog

from app.db.session import get_async_session as get_async_db_session
from app.models.user import User
from app.core.security.security import TokenManager

logger = structlog.get_logger(__name__)

# Configuration OAuth2 - utiliser l'endpoint /login standard
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db_session)
) -> User:
    """
    Récupérer l'utilisateur actuel à partir du token JWT
    
    Args:
        token: Token JWT d'authentification
        db: Session de base de données
        
    Returns:
        User: Utilisateur authentifié
        
    Raises:
        HTTPException: Si le token est invalide ou l'utilisateur n'existe pas
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Vérifier et décoder le token
        payload = TokenManager.verify_token(token)
        if payload is None:
            logger.warning("Token invalide ou expiré")
            raise credentials_exception
        
        # Extraire l'ID utilisateur
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("Token sans ID utilisateur")
            raise credentials_exception
            
        logger.debug("Token validé", user_id=user_id)
        
    except Exception as e:
        logger.error("Erreur lors de la validation du token", error=str(e))
        raise credentials_exception
    
    # Récupérer l'utilisateur depuis la base de données
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if user is None:
            logger.warning("Utilisateur non trouvé", user_id=user_id)
            raise credentials_exception
            
        logger.debug("Utilisateur récupéré", user_id=str(user.id), email=user.email)
        return user
        
    except Exception as e:
        logger.error("Erreur lors de la récupération de l'utilisateur", error=str(e))
        raise credentials_exception

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Récupérer l'utilisateur actuel actif
    
    Args:
        current_user: Utilisateur authentifié
        
    Returns:
        User: Utilisateur actif
    """
    # Pour l'instant, on considère que tous les utilisateurs sont actifs
    # Dans le futur, on pourrait ajouter une vérification d'état
    return current_user

async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Récupérer l'utilisateur actuel s'il est administrateur
    
    Args:
        current_user: Utilisateur authentifié
        
    Returns:
        User: Utilisateur administrateur
        
    Raises:
        HTTPException: Si l'utilisateur n'est pas administrateur
    """
    if current_user.role != "admin":
        logger.warning("Tentative d'accès admin par un non-admin", 
                      user_id=str(current_user.id), 
                      role=current_user.role)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_current_recruiter_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Récupérer l'utilisateur actuel s'il est recruteur ou administrateur
    
    Args:
        current_user: Utilisateur authentifié
        
    Returns:
        User: Utilisateur recruteur ou administrateur
        
    Raises:
        HTTPException: Si l'utilisateur n'a pas les permissions de recruteur
    """
    if current_user.role not in ["recruiter", "admin"]:
        logger.warning("Tentative d'accès recruteur par un non-recruteur", 
                      user_id=str(current_user.id), 
                      role=current_user.role)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user
