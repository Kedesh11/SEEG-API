"""
Endpoints publics (sans authentification)
Pour permettre aux visiteurs de voir les offres d'emploi
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Any
from bson import ObjectId
from uuid import UUID

from app.db.database import get_db
from app.schemas.job import JobOfferPublicResponse, JobOfferDetailPublicResponse
import structlog

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/jobs", response_model=List[JobOfferPublicResponse], summary="Liste des offres publiques (sans auth)")
async def get_public_jobs(
    skip: int = 0,
    limit: int = 100,
    location: Optional[str] = None,
    contract_type: Optional[str] = None,
    db: Any = Depends(get_db),
):
    """
    Récupérer la liste des offres d'emploi publiques (sans authentification).

    **Filtres automatiques :**
    - Offres avec offer_status = 'tous', 'externe' ou 'interne'
    - Uniquement les offres ACTIVES (status = 'active')

    **Filtres optionnels :**
    - location : Filtrer par localisation
    - contract_type : Filtrer par type de contrat (CDI, CDD, Stage, Alternance)

    **Pagination :**
    - skip : Nombre d'offres à ignorer (défaut: 0)
    - limit : Nombre maximum d'offres à retourner (défaut: 100, max: 100)
    """
    try:
        # Requête de base : offres publiques et actives
        # Afficher uniquement les offres "tous" et "externe" (jamais "interne" car pas d'authentification)
        query = {
            "offer_status": {"$in": ["tous", "externe"]},
            "status": "active"
        }

        # Filtres optionnels
        if location:
            query["location"] = {"$regex": location, "$options": "i"}

        if contract_type:
            query["contract_type"] = contract_type

        # Exécution et tri par date de création (plus récentes en premier)
        cursor = db.job_offers.find(query).sort("created_at", -1).skip(skip).limit(min(limit, 100))
        jobs_docs = await cursor.to_list(length=None)

        # Conversion
        jobs = []
        for doc in jobs_docs:
            doc["id"] = str(doc.get("_id"))
            jobs.append(doc)

        logger.info(
            "Liste des offres publiques récupérée",
            count=len(jobs),
            skip=skip,
            limit=limit,
            location=location,
            contract_type=contract_type
        )

        return jobs

    except Exception as e:
        logger.error("Erreur lors de la récupération des offres publiques", error=str(e), error_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des offres"
        )


@router.get("/jobs/count", response_model=dict, summary="Compteur d'offres publiques (sans auth)")
async def get_public_jobs_count(
    db: Any = Depends(get_db),
):
    """
    Compter le nombre d'offres d'emploi publiques disponibles.

    **Retourne :**
    - total : Nombre total d'offres publiques actives
    """
    try:
        # Compter les offres "tous" et "externe"
        query = {
            "offer_status": {"$in": ["tous", "externe"]},
            "status": "active"
        }

        total = await db.job_offers.count_documents(query)

        logger.info("Compteur d'offres publiques", total=total)

        return {
            "total": total,
            "status": "active",
            "type": "public"
        }

    except Exception as e:
        logger.error("Erreur lors du comptage des offres publiques", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du comptage des offres"
        )


@router.get("/jobs/{job_id}", response_model=JobOfferDetailPublicResponse, summary="Détails d'une offre publique (sans auth)")
async def get_public_job_details(
    job_id: str,
    db: Any = Depends(get_db),
):
    """
    Récupérer les détails complets d'une offre d'emploi publique (sans authentification).

    **Restrictions :**
    - Offres avec offer_status = 'tous', 'externe' ou 'interne'
    - Uniquement les offres ACTIVES (status = 'active')

    **Retourne :**
    - Tous les détails de l'offre (titre, description, localisation, etc.)
    - Les questions MTP si disponibles
    - Informations sur le recruteur (nom uniquement, pas d'infos sensibles)
    """
    try:
        # Requête avec vérifications de sécurité
        # Uniquement les offres "tous" et "externe"
        query = {
            "_id": ObjectId(job_id) if len(job_id) == 24 else job_id,
            "offer_status": {"$in": ["tous", "externe"]},
            "status": "active"
        }

        job = await db.job_offers.find_one(query)

        if not job:
            logger.warning("Offre publique non trouvée ou non accessible", job_id=str(job_id))
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offre d'emploi non trouvée ou non accessible publiquement"
            )

        job["id"] = str(job.get("_id"))

        logger.info("Détails de l'offre publique récupérés", job_id=str(job_id), title=job.get("title"))

        return job

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Erreur lors de la récupération des détails de l'offre publique",
            job_id=str(job_id),
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des détails de l'offre"
        )

