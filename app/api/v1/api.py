"""
API Router principal pour la version 1
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, jobs, public, candidates
from app.api.v1.endpoints import webhooks

api_router = APIRouter()

# Inclure tous les routers d'endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["🔐 Authentification"])
api_router.include_router(users.router, prefix="/users", tags=["👥 Utilisateurs"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["💼 Offres d'emploi"])
api_router.include_router(candidates.router, tags=["👤 Informations Candidats"])
api_router.include_router(public.router, prefix="/public", tags=["🌐 Endpoints Publics (sans auth)"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])

# Endpoint de statut de l'API
@api_router.get("/status", summary="Statut de l'API v1")
async def api_status():
    """Statut de l'API v1"""
    return {
        "api_version": "v1",
        "status": "active",
        "endpoints": {
            "auth": "/api/v1/auth",
            "users": "/api/v1/users", 
            "jobs": "/api/v1/jobs",
            "public": "/api/v1/public (SANS authentification)",
            "webhooks": "/api/v1/webhooks"
        }
    }
