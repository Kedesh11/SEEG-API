"""
Module d'optimisation des requêtes pour l'application SEEG-API (Version MongoDB).
"""
from typing import List, Optional, Type, Any, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import structlog

logger = structlog.get_logger(__name__)

class QueryOptimizer:
    """Classe pour optimiser les requêtes MongoDB."""
    
    @staticmethod
    async def get_user_with_full_profile(db: AsyncIOMotorDatabase, user_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un utilisateur avec son profil candidat"""
        try:
            query = {"_id": ObjectId(user_id)} if len(str(user_id)) == 24 else {"_id": str(user_id)}
            user = await db.users.find_one(query)
            if user:
                profile = await db.candidate_profiles.find_one({"user_id": str(user_id)})
                user["candidate_profile"] = profile
            return user
        except Exception as e:
            logger.error("Error getting user with full profile", error=str(e), user_id=user_id)
            return None

    @staticmethod
    async def get_job_offer_with_relations(db: AsyncIOMotorDatabase, job_id: str) -> Optional[Dict[str, Any]]:
        """Récupère une offre d'emploi avec ses relations (recruteur, candidatures)"""
        try:
            query = {"_id": ObjectId(job_id)} if len(str(job_id)) == 24 else {"_id": str(job_id)}
            job = await db.job_offers.find_one(query)
            if job:
                # Recruiter
                recruiter_id = job.get("recruiter_id")
                if recruiter_id:
                    rec_query = {"_id": ObjectId(recruiter_id)} if len(str(recruiter_id)) == 24 else {"_id": str(recruiter_id)}
                    job["recruiter"] = await db.users.find_one(rec_query)
                
                # Applications
                cursor = db.applications.find({"job_offer_id": str(job_id)})
                job["applications"] = await cursor.to_list(length=100)
            return job
        except Exception as e:
            logger.error("Error getting job offer with relations", error=str(e), job_id=job_id)
            return None

    @staticmethod
    async def get_application_complete(db: AsyncIOMotorDatabase, application_id: str) -> Optional[Dict[str, Any]]:
        """Récupère une candidature avec toutes ses relations."""
        try:
            query = {"_id": ObjectId(application_id)} if len(str(application_id)) == 24 else {"_id": str(application_id)}
            app = await db.applications.find_one(query)
            if not app:
                return None
            
            # Candidate
            candidate_id = app.get("candidate_id") or app.get("user_id")
            if candidate_id:
                app["candidate"] = await QueryOptimizer.get_user_with_full_profile(db, str(candidate_id))
            
            # Job Offer
            job_id = app.get("job_offer_id")
            if job_id:
                job_query = {"_id": ObjectId(job_id)} if len(str(job_id)) == 24 else {"_id": str(job_id)}
                app["job_offer"] = await db.job_offers.find_one(job_query)
            
            # Documents
            doc_cursor = db.application_documents.find({"application_id": str(application_id)})
            app["documents"] = await doc_cursor.to_list(length=50)
            
            # History
            hist_cursor = db.application_history.find({"application_id": str(application_id)}).sort("created_at", -1)
            app["history"] = await hist_cursor.to_list(length=100)
            
            return app
        except Exception as e:
            logger.error("Error getting complete application", error=str(e), application_id=application_id)
            return None

# Fonctions utilitaires (legacy compatible)
async def get_user_with_full_profile(db: AsyncIOMotorDatabase, user_id: str):
    return await QueryOptimizer.get_user_with_full_profile(db, str(user_id))

async def get_job_offer_with_applications(db: AsyncIOMotorDatabase, job_id: str):
    return await QueryOptimizer.get_job_offer_with_relations(db, str(job_id))

async def get_application_complete(db: AsyncIOMotorDatabase, application_id: str):
    return await QueryOptimizer.get_application_complete(db, str(application_id))
