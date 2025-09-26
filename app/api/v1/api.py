"""
API Router principal pour la version 1
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, jobs
from app.api.v1.endpoints import webhooks

api_router = APIRouter()

# Inclure tous les routers d'endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Job Offers"])
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
            "webhooks": "/api/v1/webhooks"
        }
    }
