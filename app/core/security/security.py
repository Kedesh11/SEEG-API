"""
Gestion de la sécurité et de l'authentification
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
import structlog

from app.core.config.config import settings

logger = structlog.get_logger(__name__)

# Configuration du hachage des mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PasswordManager:
    """Gestionnaire des mots de passe"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hacher un mot de passe
        
        Args:
            password: Mot de passe en clair
            
        Returns:
            str: Mot de passe haché
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Vérifier un mot de passe
        
        Args:
            plain_password: Mot de passe en clair
            hashed_password: Mot de passe haché
            
        Returns:
            bool: True si le mot de passe est correct
        """
        return pwd_context.verify(plain_password, hashed_password)


class TokenManager:
    """Gestionnaire des tokens JWT"""
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Créer un token d'accès
        
        Args:
            data: Données à encoder dans le token
            expires_delta: Durée d'expiration personnalisée
            
        Returns:
            str: Token JWT
        """
        to_encode = data.copy()

        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({
            "exp": expire,
            "iat": now,
            "nbf": now,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
        })
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """
        Créer un token de rafraîchissement
        
        Args:
            data: Données à encoder dans le token
            
        Returns:
            str: Token de rafraîchissement JWT
        """
        to_encode = data.copy()
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({
            "exp": expire,
            "iat": now,
            "nbf": now,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "type": "refresh"
        })
        
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Vérifier et décoder un token
        
        Args:
            token: Token JWT à vérifier
            
        Returns:
            Optional[Dict]: Données décodées ou None si invalide
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                audience=settings.JWT_AUDIENCE,
                options={"verify_aud": True}
            )
            return payload
        except JWTError as e:
            logger.warning("Token verification failed", error=str(e))
            return None
    
    @staticmethod
    def get_user_id_from_token(token: str) -> Optional[str]:
        """
        Extraire l'ID utilisateur d'un token
        
        Args:
            token: Token JWT
            
        Returns:
            Optional[str]: ID utilisateur ou None
        """
        payload = TokenManager.verify_token(token)
        if payload:
            return payload.get("sub")
        return None


class RoleManager:
    """
    Gestionnaire des rôles et permissions.
    
    Hiérarchie des rôles:
    1. admin: Toutes les permissions (gestion système)
    2. recruiter: Gestion complète du recrutement (CRUD sur tout)
    3. observer: Lecture seule (monitoring, statistiques)
    4. candidate: Actions limitées à ses propres données
    """
    
    # Définition complète des permissions par rôle
    ROLES = {
        "admin": ["*"],  # Toutes les permissions système
        
        "recruiter": [
            # Offres d'emploi
            "create_job_offer",
            "read_job_offers",
            "update_job_offer",
            "delete_job_offer",
            "publish_job_offer",
            # Candidatures
            "read_all_applications",
            "update_application_status",
            "delete_application",
            # Candidats
            "read_all_candidates",
            "read_candidate_profile",
            # Entretiens
            "create_interview",
            "update_interview",
            "delete_interview",
            "read_interviews",
            # Évaluations
            "create_evaluation",
            "update_evaluation",
            "read_evaluations",
            # Notifications
            "send_notification",
            # Statistiques
            "read_statistics"
        ],
        
        "observer": [
            # Lecture seule - AUCUNE modification
            "read_job_offers",
            "read_all_applications",
            "read_all_candidates",
            "read_interviews",
            "read_evaluations",
            "read_statistics"
        ],
        
        "candidate": [
            # Profil personnel
            "read_own_profile",
            "update_own_profile",
            # Offres (avec filtrage interne/externe)
            "read_job_offers",
            # Candidatures personnelles
            "create_application",
            "read_own_applications",
            "update_own_application",  # Retirer une candidature
            # Documents
            "upload_document",
            "read_own_documents"
        ]
    }
    
    @staticmethod
    def has_permission(user_role: str, permission: str) -> bool:
        """
        Vérifier si un rôle a une permission
        
        Args:
            user_role: Rôle de l'utilisateur
            permission: Permission à vérifier
            
        Returns:
            bool: True si l'utilisateur a la permission
        """
        if user_role not in RoleManager.ROLES:
            return False
        
        user_permissions = RoleManager.ROLES[user_role]
        
        # L'admin a toutes les permissions
        if "*" in user_permissions:
            return True
        
        return permission in user_permissions
    
    @staticmethod
    def get_user_permissions(user_role: str) -> list:
        """
        Obtenir toutes les permissions d'un rôle
        
        Args:
            user_role: Rôle de l'utilisateur
            
        Returns:
            list: Liste des permissions
        """
        return RoleManager.ROLES.get(user_role, [])
    
    @staticmethod
    def is_valid_role(role: str) -> bool:
        """
        Vérifier si un rôle est valide
        
        Args:
            role: Rôle à vérifier
            
        Returns:
            bool: True si le rôle est valide
        """
        return role in RoleManager.ROLES


def create_password_reset_token(email: str) -> str:
    """
    Créer un token de réinitialisation de mot de passe
    
    Args:
        email: Email de l'utilisateur
        
    Returns:
        str: Token de réinitialisation
    """
    data = {"email": email, "type": "password_reset"}
    expire = datetime.now(timezone.utc) + timedelta(hours=1)  # Token valide 1 heure
    data.update({"exp": expire})
    
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Vérifier un token de réinitialisation de mot de passe
    
    Args:
        token: Token à vérifier
        
    Returns:
        Optional[str]: Email de l'utilisateur ou None si invalide
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        if payload.get("type") != "password_reset":
            return None
        
        return payload.get("email")
    except JWTError:
        return None

# Dépendances pour l'authentification
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.models.user import User
from sqlalchemy import select

# Configuration du bearer token
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Récupérer l'utilisateur actuel à partir du token JWT
    
    Args:
        credentials: Credentials HTTP Bearer
        db: Session de base de données
        
    Returns:
        User: Utilisateur actuel
        
    Raises:
        HTTPException: Si le token est invalide ou l'utilisateur n'existe pas
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = TokenManager.verify_token(credentials.credentials)
        if payload is None:
            raise credentials_exception
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # Récupérer l'utilisateur depuis la base de données
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
        
    return user
