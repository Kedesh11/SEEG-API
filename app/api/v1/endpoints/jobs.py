"""
Endpoints de gestion des offres d'emploi
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Any, Optional
import structlog

from app.db.database import get_db
from app.schemas.job import (
    JobOfferResponse, JobOfferCreate, JobOfferUpdate, JobOfferPublicResponse
)
from app.services.job import JobOfferService
from app.core.exceptions import ValidationError
from app.core.dependencies import (
    get_current_active_user, get_current_recruiter_user
)

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["💼 Offres d'emploi"])


def safe_log(level: str, message: str, **kwargs):
    """Log avec gestion d'erreur pour éviter les problèmes de handler."""
    try:
        getattr(logger, level)(message, **kwargs)
    except (TypeError, AttributeError):
        print(f"{level.upper()}: {message} - {kwargs}")


@router.get(
    "/",
    response_model=list[JobOfferPublicResponse],
    summary="Liste des offres d'emploi",
    description="Récupérer toutes les offres avec filtrage intelligent"
)
async def get_job_offers(
    skip: int = Query(0, ge=0, description="Ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Retourner"),
    status_filter: Optional[str] = Query(None, description="Statut"),
    location: Optional[str] = Query(None, description="Localisation"),
    contract_type: Optional[str] = Query(None, description="Contrat"),
    current_user: Any = Depends(get_current_active_user),
    db: Any = Depends(get_db)
):
    """
    Récupérer la liste des offres d'emploi avec FILTRAGE AUTOMATIQUE.

    **Filtrage intelligent selon le type de candidat** :
    - **Candidat INTERNE** (avec matricule) : Voit TOUT
    - **Candidat EXTERNE** (sans matricule) : Voit offre accessible
    - **Recruteur/Admin** : Voit TOUT

    **Pagination** : Utilisez `skip` et `limit` pour paginer les résultats
    """
    try:
        job_service = JobOfferService(db)
        # On utilise le service
        all_jobs = await job_service.get_job_offers(
            skip=skip, limit=limit, current_user=current_user
        )

        # Filtres supplémentaires qui pourraient ne pas être dans le service
        filtered_jobs = []
        for job in all_jobs:
            if location and location.lower() not in \
               job.get("location", "").lower():
                continue
            if contract_type and job.get("contract_type") != contract_type:
                continue
            if status_filter and job.get("status") != status_filter:
                continue
            filtered_jobs.append(job)

        jobs = filtered_jobs[:limit]

        is_internal = current_user.get('is_internal_candidate', False)
        u_type = "interne" if is_internal else "externe"
        u_type = "recruiter" if current_user.get('matricule') else "external"
        safe_log("info", "Offres d'emploi récupérées",
                 count=len(jobs), user_type=u_type,
                 role=str(current_user.get('role', 'candidate')))

        return [JobOfferPublicResponse.model_validate(job) for job in jobs]

    except Exception as e:
        safe_log("error", "Erreur offres d'emploi", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la récupération des offres d'emploi"
        )


@router.post(
    "/",
    response_model=JobOfferResponse,
    status_code=status.HTTP_201_CREATED,  # Standard REST : 201 pour création de ressource
    summary="Créer une offre d'emploi",
    description=("Créer une nouvelle offre d'emploi avec questions "
                 "MTP optionnelles")
)
async def create_job_offer(
    job_data: JobOfferCreate,
    db: Any = Depends(get_db),
    current_user: Any = Depends(get_current_recruiter_user)
):
    """
    Créer une nouvelle offre d'emploi avec support complet des questions MTP.

    **Questions MTP (Métier, Talent, Paradigme)** - Optionnelles :
    - `question_metier` : Évalue les compétences techniques et opérationnelles
    - `question_talent` : Évalue les aptitudes personnelles et le potentiel
    - `question_paradigme` : Évalue la vision, les valeurs et la compatibilité culturelle

    **Accessibilité** :
    - `offer_status='interne'` : Réservée aux candidats internes uniquement
    - `offer_status='externe'` : Réservée aux candidats externes uniquement
    - `offer_status='tous'` : Accessible à tous (internes + externes)

    **Permissions** : Accessible uniquement aux recruteurs et administrateurs
    """
    try:
        u_id = str(current_user.get("_id", current_user.get("id")))
        safe_log("info", "🚀 DÉBUT création offre d'emploi",
                 recruiter_id=u_id,
                 title=job_data.title,
                 location=job_data.location,
                 offer_status=job_data.offer_status,
                 has_questions_mtp=job_data.questions_mtp is not None)

        job_service = JobOfferService(db)

        c_id = str(current_user.get("_id", current_user.get("id")))
        safe_log("debug", "✅ Service initialisé", recruiter_id=c_id)

        # 🔷 ÉTAPE 2: Création
        safe_log("debug", "📝 Création offre...")
        job_offer = await job_service.create_job_offer(job_data, c_id)

        j_id = str(job_offer.get("_id", job_offer.get("id")))
        safe_log("info", "🎉 SUCCÈS création offre",
                 job_id=j_id, recruiter_id=c_id,
                 title=job_offer.get("title"))
        return JobOfferResponse.model_validate(job_offer)

    except ValidationError as e:
        error_msg = str(e)
        safe_log("warning", "❌ VALIDATION ÉCHOUÉE - Création offre",
                 error=error_msg,
                 error_type="ValidationError",
                 recruiter_id=str(current_user.get("_id", current_user.get("id"))),
                 title=job_data.title if job_data else "N/A")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
    except Exception as e:
        # Log détaillé avec traceback
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}"
        error_traceback = traceback.format_exc()
        safe_log("error", "🔥 ERREUR CRITIQUE - Création offre",
                 error=error_msg,
                 error_type=type(e).__name__,
                 recruiter_id=str(current_user.get("_id", "N/A")))

        # Mode debug
        is_debug = os.getenv("DEBUG", "false").lower() == "true"
        env = os.getenv("ENVIRONMENT", "production")
        if is_debug or env == "development":
            raise HTTPException(
                status_code=500, detail=f"Erreur interne: {error_msg}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la création de l'offre d'emploi"
            )

@router.get(
    "/{job_id}",
    response_model=JobOfferResponse,
    summary="Détails d'une offre d'emploi",
    description="Récupérer tous les détails d'une offre incluant les questions MTP"
)
async def get_job_offer(
    job_id: str,
    current_user: Any = Depends(get_current_active_user),
    db: Any = Depends(get_db)
):
    """
    Récupérer les détails complets d'une offre d'emploi.

    **Informations retournées** :
    - Toutes les informations de l'offre (titre, description, localisation, etc.)
    - Les 3 questions MTP si définies (question_metier, question_talent, question_paradigme)
    - Les métadonnées (dates de création/modification, statut, etc.)

    **Permissions** : Accessible à tous les utilisateurs authentifiés

    **Filtrage automatique** : Les candidats externes ne verront que les offres avec `offer_status='tous'` ou `'externe'`
    """
    try:
        job_service = JobOfferService(db)
        job_offer = await job_service.get_job_offer_by_id(job_id)

        if not job_offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offre d'emploi non trouvée"
            )

        return JobOfferResponse.model_validate(job_offer)
    except HTTPException:
        raise
    except Exception as e:
        safe_log("error", "Erreur récupération offre",
                 error=str(e), job_id=str(job_id))
        raise HTTPException(
            status_code=500, detail="Erreur interne"
        )

@router.put(
    "/{job_id}",
    response_model=JobOfferResponse,
    summary="Mettre à jour une offre d'emploi",
    description="Modifier une offre existante, y compris ses questions MTP"
)
async def update_job_offer(
    job_id: str,
    job_data: JobOfferUpdate,
    db: Any = Depends(get_db),
    current_user: Any = Depends(get_current_recruiter_user)
):
    """
    Mettre à jour une offre d'emploi existante.

    **Champs modifiables** :
    - Toutes les informations de l'offre (titre, description, localisation, etc.)
    - Les questions MTP individuellement ou ensemble :
      - `question_metier`
      - `question_talent`
      - `question_paradigme`
    - Le statut de l'offre (active, closed, etc.)
    - L'accessibilité (`offer_status`: 'tous', 'interne', 'externe')

    **Permissions** : Seul le recruteur propriétaire ou un administrateur peut modifier l'offre

    **Note** : Vous pouvez mettre à jour uniquement les champs que vous souhaitez modifier
    """
    try:
        # 🔷 ÉTAPE 1: Initialisation
        update_fields = job_data.dict(exclude_unset=True)
        safe_log("info", "🚀 DÉBUT mise à jour offre d'emploi",
                job_id=str(job_id),
                user_id=str(current_user.get("_id", current_user.get("id"))),
                user_role=current_user.get("role"),
                fields_to_update=list(update_fields.keys()))

        job_service = JobOfferService(db)

        # 🔷 ÉTAPE 2: Vérification existence et permissions
        safe_log("debug", "🔍 Vérification existence offre...")
        job_offer = await job_service.get_job_offer_by_id(job_id)
        if not job_offer:
            safe_log("warning", "❌ Offre non trouvée", job_id=str(job_id))
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offre d'emploi non trouvée"
            )
        safe_log("debug", "✅ Offre trouvée", title=job_offer.get("title"))

        safe_log("debug", "🔐 Vérification permissions...")
        if str(job_offer.get("recruiter_id")) != str(current_user.get("_id", current_user.get("id"))) and str(current_user.get("role")) != "admin":
            safe_log("warning", "❌ Permissions insuffisantes",
                     job_recruiter_id=str(job_offer.get("recruiter_id")),
                     current_user_id=str(current_user.get("_id", current_user.get("id"))))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pas d'autorisation pour modifier cette offre d'emploi"
            )
        safe_log("debug", "✅ Permissions validées")

        # 🔷 ÉTAPE 3: Mise à jour
        safe_log("debug", "📝 Application des modifications...")
        updated_job = await job_service.update_job_offer(job_id, job_data)

        safe_log("info", "🎉 SUCCÈS mise à jour offre d'emploi complète",
                job_id=str(job_id),
                recruiter_id=str(current_user.get("_id", current_user.get("id"))),
                fields_updated=list(update_fields.keys()))
        return JobOfferResponse.model_validate(updated_job)
    except HTTPException:
        # Relancer les HTTPExceptions (déjà loguées)
        raise
    except ValidationError as e:
        error_msg = str(e)
        safe_log("warning", "❌ VALIDATION ÉCHOUÉE - Mise à jour offre",
                 error=error_msg,
                 error_type="ValidationError",
                 job_id=str(job_id),
                 user_id=str(current_user.get("_id", current_user.get("id"))))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
    except Exception as e:
        # Log détaillé avec traceback
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}"
        error_traceback = traceback.format_exc()
        safe_log("error", "🔥 ERREUR CRITIQUE - Mise à jour offre d'emploi",
                error=error_msg,
                error_type=type(e).__name__,
                traceback=error_traceback,
                job_id=str(job_id),
                user_id=str(current_user.get("_id", current_user.get("id"))))
        # En mode debug ou development, retourner plus de détails
        import os
        if os.getenv("DEBUG", "false").lower() == "true" or os.getenv("ENVIRONMENT", "production") == "development":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur interne: {error_msg}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la mise à jour de l'offre d'emploi"
            )

@router.delete("/{job_id}", summary="Supprimer une offre d'emploi")
async def delete_job_offer(
    job_id: str,
    db: Any = Depends(get_db),
    current_user: Any = Depends(get_current_recruiter_user)
):
    """Supprimer une offre d'emploi"""
    try:
        job_service = JobOfferService(db)

        # Verifierfier que l'offre appartient au recruteur
        job_offer = await job_service.get_job_offer_by_id(job_id)
        if not job_offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offre d'emploi non trouvée"
            )

        if str(job_offer.get("recruiter_id")) != str(current_user.get("_id", current_user.get("id"))) and str(current_user.get("role", "")) != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pas d'autorisation pour supprimer cette offre d'emploi"
            )

        success = await job_service.delete_job_offer(job_id)

        if success:
            u_id = str(current_user.get("_id", current_user.get("id")))
            safe_log("info", "Offre supprimée", job_id=str(job_id),
                     recruiter_id=u_id)
            return {"message": "Offre supprimée avec succès"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la suppression de l'offre d'emploi"
            )
    except HTTPException:
        raise
    except Exception as e:
        safe_log("error", "Erreur suppression offre d'emploi", error=str(e), job_id=str(job_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la suppression de l'offre d'emploi"
        )

@router.get(
    "/{job_id}/applications",
    response_model=JobOfferResponse,
    summary="Candidatures d'une offre"
)
async def get_job_offer_applications(
    job_id: str,
    db: Any = Depends(get_db),
    current_user: Any = Depends(get_current_recruiter_user)
):
    """Récupérer les candidatures d'une offre d'emploi"""
    try:
        job_service = JobOfferService(db)

        # Vérifier que l'offre appartient au recruteur
        job_offer = await job_service.get_job_offer_by_id(job_id)
        if not job_offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offre d'emploi non trouvée"
            )

        u_id = str(current_user.get("_id", current_user.get("id")))
        is_admin = str(current_user.get("role", "")) == "admin"
        if str(job_offer.get("recruiter_id")) != u_id and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pas d'autorisation pour voir les candidatures"
            )

        # Type assertion pour satisfaire le linter
        applications_count = len(job_offer.get('applications', []))
        safe_log("info", "Candidatures récupérées",
                 job_id=str(job_id), count=applications_count)
        return JobOfferResponse.model_validate(job_offer)

    except HTTPException:
        raise
    except Exception as e:
        safe_log("error", "Erreur candidatures",
                 error=str(e), job_id=str(job_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des candidatures"
        )

@router.get("/recruiter/my-jobs", response_model=list[JobOfferResponse], summary="Mes offres d'emploi")
async def get_my_job_offers(
    skip: int = Query(0, ge=0, description="Nombre d'éléments à ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre d'éléments à retourner"),
    db: Any = Depends(get_db),
    current_user: Any = Depends(get_current_recruiter_user)
):
    """Récupérer les offres d'emploi du recruteur connecté"""
    try:
        job_service = JobOfferService(db)
        # Récupérer toutes les offres puis filtrer par recruteur
        all_jobs = await job_service.get_job_offers(
            skip=skip,
            limit=limit,
            current_user=current_user
        )
        # Filtrer pour ne garder que les offres du recruteur
        u_id = str(current_user.get("_id", current_user.get("id")))
        job_offers = [
            job for job in all_jobs
            if str(job.get("recruiter_id")) == u_id
        ]
        safe_log("info", "Mes offres récupérées",
                 recruiter_id=u_id, count=len(job_offers))
        return [JobOfferResponse.model_validate(job) for job in job_offers]
    except Exception as e:
        u_id = str(current_user.get("_id", current_user.get("id")))
        safe_log("error", "Erreur mes offres", error=str(e), recruiter_id=u_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de vos offres"
        )

@router.get("/recruiter/statistics", summary="Statistiques du recruteur")
async def get_recruiter_statistics(
    db: Any = Depends(get_db),
    current_user: Any = Depends(get_current_recruiter_user)
):
    """Récupérer les statistiques du recruteur connecté"""
    try:
        job_service = JobOfferService(db)

        # Récupérer le nombre total d'offres du recruteur
        total_jobs = await job_service.get_job_offers_count(current_user=current_user)

        # Statistiques simples pour le moment
        stats = {
            "recruiter_id": str(current_user.get("_id", current_user.get("id"))),
            "total_offers": total_jobs,
            "message": "Statistiques de base (version simplifiée)"
        }

        u_id = str(current_user.get("_id", current_user.get("id")))
        safe_log("info", "Stats recruteur récupérées", recruiter_id=u_id)
        return stats
    except Exception as e:
        safe_log("error", "Erreur récupération statistiques", error=str(e), recruiter_id=str(current_user.get("_id", current_user.get("id"))))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des statistiques"
        )
