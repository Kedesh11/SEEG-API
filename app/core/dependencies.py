"""
Dépendances FastAPI pour l'authentification
Système d'authentification unique et robuste
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
import structlog
from bson import ObjectId

from app.core.security.security import TokenManager
from app.db.database import get_db

logger = structlog.get_logger(__name__)

# Configuration OAuth2 - utiliser l'unique endpoint /login pour Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
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
        user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        
        if user_doc is None:
            logger.warning("Utilisateur non trouvé", user_id=user_id)
            raise credentials_exception
            
        logger.debug("Utilisateur récupéré", user_id=str(user_doc["_id"]), email=user_doc.get("email"))
        
        # Pour l'instant, on retourne un objet mock pour la compatibilité.
        # Plus tard, il faudra utiliser un schéma Pydantic complet.
        class UserMock:
            """Objet mock pour l'utilisateur authentifié (compatibilité descendante)"""
            def __init__(self, doc):
                self.id = str(doc.get("_id"))
                self.email = doc.get("email")
                self.role = doc.get("role")
                self.is_internal_candidate = doc.get("is_internal_candidate", False)
                self.candidate_status = doc.get("candidate_status")
        
        return UserMock(user_doc)
        
    except Exception as e:
        logger.error("Erreur lors de la récupération de l'utilisateur", error=str(e))
        raise credentials_exception

async def get_current_active_user(current_user: any = Depends(get_current_user)):
    """
    Récupérer l'utilisateur actuel actif
    
    Args:
        current_user: Utilisateur authentifié (UserMock)
        
    Returns:
        UserMock: Utilisateur actif
    """
    # Pour l'instant, on considère que tous les utilisateurs sont actifs
    # Dans le futur, on pourrait ajouter une vérification d'état
    return current_user

async def get_current_admin_user(current_user: any = Depends(get_current_active_user)):
    """
    Récupérer l'utilisateur actuel s'il est administrateur
    
    Args:
        current_user: Utilisateur authentifié
        
    Returns:
        UserMock: Utilisateur administrateur
        
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

async def get_current_recruiter_user(current_user: any = Depends(get_current_active_user)):
    """
    Récupérer l'utilisateur actuel s'il est recruteur ou administrateur.
    
    Permissions:
    - Créer, modifier, supprimer des offres d'emploi
    - Gérer les candidatures (changer statuts)
    - Voir tous les candidats
    - Planifier des entretiens
    - Créer des évaluations
    
    Args:
        current_user: Utilisateur authentifié
        
    Returns:
        UserMock: Utilisateur recruteur ou administrateur
        
    Raises:
        HTTPException: Si l'utilisateur n'a pas les permissions de recruteur
    """
    if current_user.role not in ["recruiter", "admin"]:
        logger.warning("Tentative d'accès recruteur par un non-recruteur", 
                      user_id=str(current_user.id), 
                      role=current_user.role)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acces refuse: role recruteur ou admin requis"
        )
    return current_user

async def get_current_observer_user(current_user: any = Depends(get_current_active_user)):
    """
    Récupérer l'utilisateur actuel s'il est observateur, recruteur ou administrateur.
    
    Permissions (LECTURE SEULE):
    - Voir toutes les offres d'emploi
    - Voir toutes les candidatures
    - Voir les statistiques
    - Voir les entretiens
    - Voir les évaluations
    
    AUCUNE action de modification/création/suppression autorisée.
    
    Args:
        current_user: Utilisateur authentifié
        
    Returns:
        UserMock: Utilisateur observateur, recruteur ou administrateur
        
    Raises:
        HTTPException: Si l'utilisateur n'a pas les permissions d'observateur
    """
    if current_user.role not in ["observer", "recruiter", "admin"]:
        logger.warning("Tentative d'accès observateur par un utilisateur non autorise", 
                      user_id=str(current_user.id), 
                      role=current_user.role)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acces refuse: role observateur, recruteur ou admin requis"
        )
    return current_user

async def get_current_candidate_user(current_user: any = Depends(get_current_active_user)):
    """
    Récupérer l'utilisateur actuel s'il est candidat.
    
    Permissions:
    - Voir son propre profil
    - Modifier son propre profil
    - Voir les offres d'emploi (filtrées selon interne/externe)
    - Soumettre des candidatures
    - Voir ses propres candidatures
    - Upload de documents PDF
    
    Args:
        current_user: Utilisateur authentifié
        
    Returns:
        UserMock: Utilisateur candidat
        
    Raises:
        HTTPException: Si l'utilisateur n'est pas un candidat
    """
    if current_user.role != "candidate":
        logger.warning("Tentative d'accès candidat par un non-candidat", 
                      user_id=str(current_user.id), 
                      role=current_user.role)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acces refuse: role candidat requis"
        )
    return current_user
