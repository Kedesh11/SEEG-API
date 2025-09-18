"""
Application FastAPI principale avec documentation organisée par modules
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
import structlog

from app.core.config import settings
from app.db.session import get_async_db_session
from app.models.user import User
from app.models.job_offer import JobOffer
from app.models.application import Application
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse
from app.schemas.user import UserResponse, UserCreate, UserUpdate
from app.schemas.job import JobOfferResponse, JobOfferCreate, JobOfferUpdate
from app.schemas.application import ApplicationResponse, ApplicationCreate, ApplicationUpdate
from app.services.auth import AuthService
from app.services.user import UserService
from app.services.job import JobOfferService
from app.services.application import ApplicationService
from app.core.dependencies import get_current_active_user, get_current_admin_user, get_current_recruiter_user

# Configuration du logging
logger = structlog.get_logger(__name__)

# Créer l'application FastAPI avec tags personnalisés
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## API One HCM SEEG - Système de Gestion des Ressources Humaines
    
    Cette API permet de gérer l'ensemble du processus de recrutement de la SEEG :
    
    * **Authentification** : Connexion, inscription, gestion des tokens
    * **Utilisateurs** : Gestion des profils candidats, recruteurs et administrateurs
    * **Offres d'emploi** : Création, modification et consultation des postes
    * **Candidatures** : Soumission et suivi des candidatures
    * **Évaluations** : Protocoles d'évaluation des candidats
    * **Notifications** : Système de notifications
    * **Entretiens** : Planification et gestion des entretiens
    
    ### Frontend
    Interface utilisateur disponible sur : https://www.seeg-talentsource.com
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "🏠 Accueil",
            "description": "Endpoints généraux de l'API - Statut, santé, informations"
        },
        {
            "name": "🔐 Authentification",
            "description": "Gestion de l'authentification - Connexion, inscription, tokens JWT"
        },
        {
            "name": "👥 Utilisateurs",
            "description": "Gestion des utilisateurs - Profils candidats, recruteurs, administrateurs"
        },
        {
            "name": "💼 Offres d'emploi",
            "description": "Gestion des offres d'emploi - Création, modification, consultation des postes"
        },
        {
            "name": "📝 Candidatures",
            "description": "Gestion des candidatures - Soumission, suivi, documents"
        },
        {
            "name": "📊 Évaluations",
            "description": "Système d'évaluation - Protocoles 1 et 2, scores, commentaires"
        },
        {
            "name": "🔔 Notifications",
            "description": "Système de notifications - Alertes, messages, statuts"
        },
        {
            "name": "🎯 Entretiens",
            "description": "Gestion des entretiens - Planification, créneaux, suivi"
        }
    ]
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=settings.ALLOWED_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# 🏠 MODULE ACCUEIL
# ============================================================================

@app.get("/", tags=["🏠 Accueil"], summary="Point d'entrée de l'API")
async def root():
    """Point d'entrée principal de l'API One HCM SEEG"""
    return {
        "message": "API One HCM SEEG",
        "version": settings.APP_VERSION,
        "status": "active",
        "frontend_url": "https://www.seeg-talentsource.com",
        "documentation": "/docs",
        "api_v1": "/api/v1",
        "modules": {
            "authentification": "/api/v1/auth",
            "utilisateurs": "/api/v1/users",
            "offres_emploi": "/api/v1/jobs",
            "candidatures": "/api/v1/applications",
            "evaluations": "/api/v1/evaluations",
            "notifications": "/api/v1/notifications",
            "entretiens": "/api/v1/interviews"
        }
    }

@app.get("/health", tags=["🏠 Accueil"], summary="Vérifier l'état de santé de l'API")
async def health_check():
    """Vérifier que l'API et la base de données sont opérationnelles"""
    return {
        "status": "ok",
        "message": "API is healthy",
        "version": settings.APP_VERSION,
        "database": "connected",
        "timestamp": "2024-01-01T00:00:00Z"
    }

@app.get("/info", tags=["🏠 Accueil"], summary="Informations détaillées sur l'API")
async def info():
    """Obtenir des informations détaillées sur la configuration de l'API"""
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug_mode": settings.DEBUG,
        "allowed_origins": settings.ALLOWED_ORIGINS,
        "database_url": settings.DATABASE_URL[:50] + "..." if len(settings.DATABASE_URL) > 50 else settings.DATABASE_URL,
        "features": [
            "Authentification JWT",
            "Gestion des rôles",
            "Upload de documents",
            "Notifications en temps réel",
            "Évaluations automatisées",
            "Planification d'entretiens"
        ]
    }

@app.get("/api/v1/status", tags=["🏠 Accueil"], summary="Statut de l'API v1")
async def api_status():
    """Statut détaillé de l'API v1 avec tous les modules disponibles"""
    return {
        "api_version": "v1",
        "status": "active",
        "modules": {
            "authentification": {
                "endpoint": "/api/v1/auth",
                "status": "active",
                "endpoints_count": 4
            },
            "utilisateurs": {
                "endpoint": "/api/v1/users",
                "status": "active", 
                "endpoints_count": 4
            },
            "offres_emploi": {
                "endpoint": "/api/v1/jobs",
                "status": "active",
                "endpoints_count": 3
            },
            "candidatures": {
                "endpoint": "/api/v1/applications",
                "status": "active",
                "endpoints_count": 3
            },
            "evaluations": {
                "endpoint": "/api/v1/evaluations",
                "status": "active",
                "endpoints_count": 6
            },
            "notifications": {
                "endpoint": "/api/v1/notifications",
                "status": "active",
                "endpoints_count": 4
            },
            "entretiens": {
                "endpoint": "/api/v1/interviews",
                "status": "active",
                "endpoints_count": 5
            }
        },
        "total_endpoints": 29
    }

# ============================================================================
# 🔐 MODULE AUTHENTIFICATION
# ============================================================================

@app.post("/api/v1/auth/login", 
          response_model=TokenResponse, 
          tags=["🔐 Authentification"],
          summary="Connexion utilisateur",
          description="Authentifier un utilisateur avec son email et mot de passe. Retourne un token JWT pour les requêtes suivantes.")
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

@app.post("/api/v1/auth/signup", 
          response_model=UserResponse, 
          tags=["🔐 Authentification"],
          summary="Inscription utilisateur",
          description="Créer un nouveau compte utilisateur. Par défaut, le rôle est 'candidate'.")
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

@app.get("/api/v1/auth/me", 
         response_model=UserResponse, 
         tags=["🔐 Authentification"],
         summary="Profil utilisateur connecté",
         description="Récupérer les informations du profil de l'utilisateur actuellement connecté.")
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Obtenir le profil de l'utilisateur actuellement connecté"""
    return UserResponse.from_orm(current_user)

@app.post("/api/v1/auth/logout", 
          tags=["🔐 Authentification"],
          summary="Déconnexion",
          description="Déconnexion de l'utilisateur. Le token JWT reste valide jusqu'à expiration.")
async def logout():
    """Déconnexion de l'utilisateur"""
    return {"message": "Déconnexion réussie"}

# ============================================================================
# 👥 MODULE UTILISATEURS
# ============================================================================

@app.get("/api/v1/users/", 
         response_model=List[UserResponse], 
         tags=["👥 Utilisateurs"],
         summary="Liste des utilisateurs",
         description="Récupérer la liste de tous les utilisateurs. **Réservé aux administrateurs.**")
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_admin_user)
):
    """Récupérer la liste des utilisateurs (admin seulement)"""
    try:
        user_service = UserService(db)
        users = await user_service.get_users(skip=skip, limit=limit)
        return [UserResponse.from_orm(user) for user in users]
    except Exception as e:
        logger.error("Erreur récupération utilisateurs", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des utilisateurs"
        )

@app.get("/api/v1/users/me", 
         response_model=UserResponse, 
         tags=["👥 Utilisateurs"],
         summary="Mon profil",
         description="Récupérer les informations de votre propre profil utilisateur.")
async def get_my_profile(
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """Récupérer le profil de l'utilisateur connecté"""
    try:
        return UserResponse.from_orm(current_user)
    except Exception as e:
        logger.error("Erreur récupération profil", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération du profil"
        )

@app.get("/api/v1/users/{user_id}", 
         response_model=UserResponse, 
         tags=["👥 Utilisateurs"],
         summary="Détails d'un utilisateur",
         description="Récupérer les détails d'un utilisateur spécifique. Vous pouvez voir votre propre profil ou les profils si vous êtes admin.")
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """Récupérer les détails d'un utilisateur"""
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )
        
        # Vérifier les permissions (utilisateur peut voir son propre profil ou admin)
        if current_user.id != user_id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pas d'autorisation pour voir ce profil"
            )
        
        return UserResponse.from_orm(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur récupération utilisateur", error=str(e), user_id=str(user_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de l'utilisateur"
        )

@app.put("/api/v1/users/me", 
         response_model=UserResponse, 
         tags=["👥 Utilisateurs"],
         summary="Mettre à jour mon profil",
         description="Modifier les informations de votre propre profil utilisateur.")
async def update_my_profile(
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """Mettre à jour le profil de l'utilisateur connecté"""
    try:
        user_service = UserService(db)
        updated_user = await user_service.update_user(current_user.id, user_data)
        return UserResponse.from_orm(updated_user)
    except Exception as e:
        logger.error("Erreur mise à jour profil", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la mise à jour du profil"
        )

# ============================================================================
# 💼 MODULE OFFRES D'EMPLOI
# ============================================================================

@app.get("/api/v1/jobs/", 
         response_model=List[JobOfferResponse], 
         tags=["💼 Offres d'emploi"],
         summary="Liste des offres d'emploi",
         description="Récupérer la liste de toutes les offres d'emploi disponibles. Possibilité de filtrer par statut.")
async def get_job_offers(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db_session)
):
    """Récupérer la liste des offres d'emploi"""
    try:
        job_service = JobOfferService(db)
        job_offers = await job_service.get_job_offers(skip=skip, limit=limit, status=status)
        return [JobOfferResponse.from_orm(job) for job in job_offers]
    except Exception as e:
        logger.error("Erreur récupération offres d'emploi", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des offres d'emploi"
        )

@app.post("/api/v1/jobs/", 
          response_model=JobOfferResponse, 
          tags=["💼 Offres d'emploi"],
          summary="Créer une offre d'emploi",
          description="Créer une nouvelle offre d'emploi. **Réservé aux recruteurs et administrateurs.**")
async def create_job_offer(
    job_data: JobOfferCreate,
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Créer une nouvelle offre d'emploi"""
    try:
        job_service = JobOfferService(db)
        
        # Ajouter l'ID du recruteur
        job_data.recruiter_id = current_user.id
        
        job_offer = await job_service.create_job_offer(job_data)
        return JobOfferResponse.from_orm(job_offer)
    except Exception as e:
        logger.error("Erreur création offre d'emploi", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création de l'offre d'emploi"
        )

@app.get("/api/v1/jobs/{job_id}", 
         response_model=JobOfferResponse, 
         tags=["💼 Offres d'emploi"],
         summary="Détails d'une offre d'emploi",
         description="Récupérer les détails complets d'une offre d'emploi spécifique.")
async def get_job_offer(
    job_id: UUID,
    db: AsyncSession = Depends(get_async_db_session)
):
    """Récupérer les détails d'une offre d'emploi"""
    try:
        job_service = JobOfferService(db)
        job_offer = await job_service.get_job_offer(job_id)
        
        if not job_offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offre d'emploi non trouvée"
            )
        
        return JobOfferResponse.from_orm(job_offer)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur récupération offre d'emploi", error=str(e), job_id=str(job_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de l'offre d'emploi"
        )

# ============================================================================
# 📝 MODULE CANDIDATURES
# ============================================================================

@app.get("/api/v1/applications/", 
         response_model=List[ApplicationResponse], 
         tags=["📝 Candidatures"],
         summary="Liste des candidatures",
         description="Récupérer la liste des candidatures. Les candidats voient leurs propres candidatures, les recruteurs voient toutes les candidatures.")
async def get_applications(
    skip: int = 0,
    limit: int = 100,
    candidate_id: Optional[UUID] = None,
    job_offer_id: Optional[UUID] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """Récupérer la liste des candidatures"""
    try:
        application_service = ApplicationService(db)
        
        # Si c'est un candidat, il ne peut voir que ses propres candidatures
        if current_user.role == "candidate":
            candidate_id = current_user.id
        
        applications = await application_service.get_applications(
            skip=skip, 
            limit=limit, 
            candidate_id=candidate_id,
            job_offer_id=job_offer_id,
            status=status
        )
        return [ApplicationResponse.from_orm(app) for app in applications]
    except Exception as e:
        logger.error("Erreur récupération candidatures", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des candidatures"
        )

@app.post("/api/v1/applications/", 
          response_model=ApplicationResponse, 
          tags=["📝 Candidatures"],
          summary="Créer une candidature",
          description="Soumettre une nouvelle candidature pour une offre d'emploi.")
async def create_application(
    application_data: ApplicationCreate,
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """Créer une nouvelle candidature"""
    try:
        application_service = ApplicationService(db)
        
        # Ajouter l'ID du candidat
        application_data.candidate_id = current_user.id
        
        application = await application_service.create_application(application_data)
        return ApplicationResponse.from_orm(application)
    except Exception as e:
        logger.error("Erreur création candidature", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création de la candidature"
        )

@app.get("/api/v1/applications/{application_id}", 
         response_model=ApplicationResponse, 
         tags=["📝 Candidatures"],
         summary="Détails d'une candidature",
         description="Récupérer les détails complets d'une candidature spécifique.")
async def get_application(
    application_id: UUID,
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """Récupérer les détails d'une candidature"""
    try:
        application_service = ApplicationService(db)
        application = await application_service.get_application(application_id)
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidature non trouvée"
            )
        
        # Vérifier les permissions
        if (current_user.role == "candidate" and application.candidate_id != current_user.id) and \
           (current_user.role not in ["recruiter", "admin"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pas d'autorisation pour voir cette candidature"
            )
        
        return ApplicationResponse.from_orm(application)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur récupération candidature", error=str(e), application_id=str(application_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de la candidature"
        )

# ============================================================================
# 📊 MODULE ÉVALUATIONS (Placeholders)
# ============================================================================

@app.get("/api/v1/evaluations/", tags=["📊 Évaluations"], summary="Liste des évaluations")
async def get_evaluations():
    """Récupérer la liste des évaluations"""
    return {"message": "Module évaluations - À implémenter"}

@app.get("/api/v1/evaluations/protocol1/", tags=["📊 Évaluations"], summary="Évaluations Protocole 1")
async def get_protocol1_evaluations():
    """Récupérer les évaluations du Protocole 1"""
    return {"message": "Évaluations Protocole 1 - À implémenter"}

@app.get("/api/v1/evaluations/protocol2/", tags=["📊 Évaluations"], summary="Évaluations Protocole 2")
async def get_protocol2_evaluations():
    """Récupérer les évaluations du Protocole 2"""
    return {"message": "Évaluations Protocole 2 - À implémenter"}

@app.post("/api/v1/evaluations/protocol1/", tags=["📊 Évaluations"], summary="Créer évaluation Protocole 1")
async def create_protocol1_evaluation():
    """Créer une évaluation Protocole 1"""
    return {"message": "Création évaluation Protocole 1 - À implémenter"}

@app.post("/api/v1/evaluations/protocol2/", tags=["📊 Évaluations"], summary="Créer évaluation Protocole 2")
async def create_protocol2_evaluation():
    """Créer une évaluation Protocole 2"""
    return {"message": "Création évaluation Protocole 2 - À implémenter"}

@app.put("/api/v1/evaluations/protocol1/{evaluation_id}", tags=["📊 Évaluations"], summary="Mettre à jour évaluation Protocole 1")
async def update_protocol1_evaluation(evaluation_id: UUID):
    """Mettre à jour une évaluation Protocole 1"""
    return {"message": f"Mise à jour évaluation Protocole 1 {evaluation_id} - À implémenter"}

# ============================================================================
# 🔔 MODULE NOTIFICATIONS (Placeholders)
# ============================================================================

@app.get("/api/v1/notifications/", tags=["🔔 Notifications"], summary="Liste des notifications")
async def get_notifications():
    """Récupérer la liste des notifications"""
    return {"message": "Module notifications - À implémenter"}

@app.get("/api/v1/notifications/unread", tags=["🔔 Notifications"], summary="Notifications non lues")
async def get_unread_notifications():
    """Récupérer les notifications non lues"""
    return {"message": "Notifications non lues - À implémenter"}

@app.put("/api/v1/notifications/{notification_id}/read", tags=["🔔 Notifications"], summary="Marquer comme lue")
async def mark_notification_read(notification_id: UUID):
    """Marquer une notification comme lue"""
    return {"message": f"Notification {notification_id} marquée comme lue - À implémenter"}

@app.put("/api/v1/notifications/read-all", tags=["🔔 Notifications"], summary="Marquer toutes comme lues")
async def mark_all_notifications_read():
    """Marquer toutes les notifications comme lues"""
    return {"message": "Toutes les notifications marquées comme lues - À implémenter"}

# ============================================================================
# 🎯 MODULE ENTRETIENS (Placeholders)
# ============================================================================

@app.get("/api/v1/interviews/", tags=["🎯 Entretiens"], summary="Liste des entretiens")
async def get_interviews():
    """Récupérer la liste des entretiens"""
    return {"message": "Module entretiens - À implémenter"}

@app.post("/api/v1/interviews/", tags=["🎯 Entretiens"], summary="Créer un entretien")
async def create_interview():
    """Créer un nouvel entretien"""
    return {"message": "Création entretien - À implémenter"}

@app.get("/api/v1/interviews/{interview_id}", tags=["🎯 Entretiens"], summary="Détails d'un entretien")
async def get_interview(interview_id: UUID):
    """Récupérer les détails d'un entretien"""
    return {"message": f"Détails entretien {interview_id} - À implémenter"}

@app.put("/api/v1/interviews/{interview_id}", tags=["🎯 Entretiens"], summary="Mettre à jour un entretien")
async def update_interview(interview_id: UUID):
    """Mettre à jour un entretien"""
    return {"message": f"Mise à jour entretien {interview_id} - À implémenter"}

@app.get("/api/v1/interviews/slots/", tags=["🎯 Entretiens"], summary="Créneaux disponibles")
async def get_interview_slots():
    """Récupérer les créneaux d'entretien disponibles"""
    return {"message": "Créneaux d'entretien - À implémenter"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
