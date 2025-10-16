"""
Endpoints de gestion des offres d'emploi
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
import structlog

from app.db.database import get_db
from app.schemas.job import JobOfferResponse, JobOfferCreate, JobOfferUpdate
from app.services.job import JobOfferService
from app.core.dependencies import get_current_active_user, get_current_recruiter_user
from app.models.user import User
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError
from app.core.config.config import settings

logger = structlog.get_logger(__name__)
router = APIRouter(
    tags=["💼 Offres d'emploi"],)


def safe_log(level: str, message: str, **kwargs):
    """Log avec gestion d'erreur pour éviter les problèmes de handler."""
    try:
        getattr(logger, level)(message, **kwargs)
    except (TypeError, AttributeError):
        print(f"{level.upper()}: {message} - {kwargs}")

@router.get(
    "/",
    response_model=List[JobOfferResponse],
    summary="Liste des offres d'emploi",
    description="Récupérer toutes les offres avec leurs questions MTP et filtrage intelligent"
)
async def get_job_offers(
    skip: int = Query(0, ge=0, description="Nombre d'elements a ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre d'elements a retourner"),
    status_filter: Optional[str] = Query(None, description="Filtrer par statut"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer la liste des offres d'emploi avec FILTRAGE AUTOMATIQUE.
    
    **Données retournées** :
    - Toutes les informations des offres (titre, description, localisation, etc.)
    - Les 3 questions MTP pour chaque offre (question_metier, question_talent, question_paradigme)
    - Les métadonnées (dates, statut, etc.)
    
    **Filtrage intelligent selon le type de candidat** :
    - **Candidat INTERNE** (employé SEEG avec matricule) : Voit TOUTES les offres
    - **Candidat EXTERNE** (sans matricule) : Voit UNIQUEMENT les offres accessibles (`offer_status='tous'` ou `'externe'`)
    - **Recruteur/Admin** : Voit TOUTES les offres
    
    **Pagination** : Utilisez `skip` et `limit` pour paginer les résultats
    """
    try:
        job_service = JobOfferService(db)
        job_offers = await job_service.get_job_offers(skip=skip, limit=limit, status=status_filter, current_user=current_user)
        safe_log("info", "Offres d'emploi recuperees", 
                count=len(job_offers),
                user_type="interne" if bool(current_user.is_internal_candidate) else "externe",
                role=str(current_user.role))
        return [JobOfferResponse.from_orm(job) for job in job_offers]
    except Exception as e:
        safe_log("error", "Erreur recuperation offres d'emploi", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des offres d'emploi"
        )

@router.post(
    "/",
    response_model=JobOfferResponse,
    status_code=status.HTTP_201_CREATED,  # Standard REST : 201 pour création de ressource
    summary="Créer une offre d'emploi",
    description="Créer une nouvelle offre d'emploi (interne ou externe) avec questions MTP optionnelles"
)
async def create_job_offer(
    job_data: JobOfferCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
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
        # 🔷 ÉTAPE 1: Initialisation
        safe_log("info", "🚀 DÉBUT création offre d'emploi", 
                recruiter_id=str(current_user.id),
                title=job_data.title,
                location=job_data.location,
                offer_status=job_data.offer_status,
                has_questions_mtp=job_data.questions_mtp is not None)
        
        job_service = JobOfferService(db)
        
        safe_log("debug", "✅ Service initialisé avec recruteur ID", recruiter_id=str(current_user.id))
        
        # 🔷 ÉTAPE 2: Création en mémoire
        safe_log("debug", "📝 Création offre en mémoire...")
        job_offer = await job_service.create_job_offer(job_data, current_user.id)
        safe_log("info", "✅ Offre créée en mémoire", job_id=str(job_offer.id))
        
        # 🔷 ÉTAPE 3: Persistence en base de données
        safe_log("debug", "💾 Commit transaction en cours...")
        await db.commit()
        safe_log("info", "✅ Transaction committée avec succès")
        
        await db.refresh(job_offer)
        safe_log("debug", "✅ Objet rafraîchi depuis la BDD")
        
        safe_log("info", "🎉 SUCCÈS création offre d'emploi complète", 
                job_id=str(job_offer.id), 
                recruiter_id=str(current_user.id),
                title=job_offer.title,
                department=job_offer.department,
                offer_status=job_offer.offer_status)
        return JobOfferResponse.from_orm(job_offer)
        
    except ValidationError as e:
        error_msg = str(e)
        safe_log("warning", "❌ VALIDATION ÉCHOUÉE - Création offre", 
                 error=error_msg,
                 error_type="ValidationError",
                 recruiter_id=str(current_user.id),
                 title=job_data.title if job_data else "N/A")
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
    except Exception as e:
        # Log détaillé avec traceback
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}"
        error_traceback = traceback.format_exc()
        safe_log("error", "🔥 ERREUR CRITIQUE - Création offre d'emploi", 
                error=error_msg,
                error_type=type(e).__name__,
                traceback=error_traceback,
                recruiter_id=str(current_user.id),
                title=job_data.title if job_data else "N/A")
        await db.rollback()
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
                detail="Erreur lors de la création de l'offre d'emploi"
            )

@router.get(
    "/{job_id}",
    response_model=JobOfferResponse,
    summary="Détails d'une offre d'emploi",
    description="Récupérer tous les détails d'une offre incluant les questions MTP"
)
async def get_job_offer(
    job_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
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
        
        return JobOfferResponse.from_orm(job_offer)
    except HTTPException:
        raise
    except Exception as e:
        safe_log("error", "Erreur récupération offre d'emploi", error=str(e), job_id=str(job_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de l'offre d'emploi"
        )

@router.put(
    "/{job_id}",
    response_model=JobOfferResponse,
    summary="Mettre à jour une offre d'emploi",
    description="Modifier une offre existante, y compris ses questions MTP"
)
async def update_job_offer(
    job_id: UUID,
    job_data: JobOfferUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
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
                user_id=str(current_user.id),
                user_role=current_user.role,
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
        safe_log("debug", "✅ Offre trouvée", title=job_offer.title)
        
        safe_log("debug", "🔐 Vérification permissions...")
        if job_offer.recruiter_id != current_user.id and str(current_user.role) != "admin":
            safe_log("warning", "❌ Permissions insuffisantes", 
                     job_recruiter_id=str(job_offer.recruiter_id),
                     current_user_id=str(current_user.id))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pas d'autorisation pour modifier cette offre d'emploi"
            )
        safe_log("debug", "✅ Permissions validées")
        
        # 🔷 ÉTAPE 3: Mise à jour
        safe_log("debug", "📝 Application des modifications...")
        updated_job = await job_service.update_job_offer(job_id, job_data)
        safe_log("info", "✅ Modifications appliquées en mémoire")
        
        # 🔷 ÉTAPE 4: Persistence en base de données
        safe_log("debug", "💾 Commit transaction en cours...")
        await db.commit()
        safe_log("info", "✅ Transaction committée avec succès")
        
        await db.refresh(updated_job)
        safe_log("debug", "✅ Objet rafraîchi depuis la BDD")
        
        safe_log("info", "🎉 SUCCÈS mise à jour offre d'emploi complète", 
                job_id=str(job_id), 
                recruiter_id=str(current_user.id),
                fields_updated=list(update_fields.keys()))
        return JobOfferResponse.from_orm(updated_job)
    except HTTPException:
        # Relancer les HTTPExceptions (déjà loguées)
        raise
    except ValidationError as e:
        error_msg = str(e)
        safe_log("warning", "❌ VALIDATION ÉCHOUÉE - Mise à jour offre", 
                 error=error_msg,
                 error_type="ValidationError",
                 job_id=str(job_id),
                 user_id=str(current_user.id))
        await db.rollback()
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
                user_id=str(current_user.id))
        await db.rollback()
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
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
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
        
        if job_offer.recruiter_id != current_user.id and str(current_user.role) != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pas d'autorisation pour supprimer cette offre d'emploi"
            )
        
        success = await job_service.delete_job_offer(job_id)
        
        # ✅ Commit explicite pour persister la suppression
        await db.commit()
        
        if success:
            safe_log("info", "Offre d'emploi supprimée", job_id=str(job_id), recruiter_id=str(current_user.id))
            return {"message": "Offre d'emploi supprimée avec succès"}
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

@router.get("/{job_id}/applications", response_model=JobOfferResponse, summary="Candidatures d'une offre")
async def get_job_offer_applications(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
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
        
        if job_offer.recruiter_id != current_user.id and str(current_user.role) != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pas d'autorisation pour voir les candidatures de cette offre"
            )
        
        # Utiliser l'offre déjà récupérée
        job_with_applications = job_offer
        
        if not job_with_applications:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Offre d'emploi non trouve"
            )
        
        # Type assertion pour satisfaire le linter
        applications_count = len(getattr(job_with_applications, 'applications', []))
        safe_log("info", "Candidatures récupérées pour offre", job_id=str(job_id), count=applications_count)
        return JobOfferResponse.from_orm(job_with_applications)
        
    except HTTPException:
        raise
    except Exception as e:
        safe_log("error", "Erreur récupération candidatures", error=str(e), job_id=str(job_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des candidatures"
        )

@router.get("/recruiter/my-jobs", response_model=List[JobOfferResponse], summary="Mes offres d'emploi")
async def get_my_job_offers(
    skip: int = Query(0, ge=0, description="Nombre d'éléments à ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre d'éléments à retourner"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
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
        job_offers = [job for job in all_jobs if str(job.recruiter_id) == str(current_user.id)]
        safe_log("info", "Mes offres d'emploi récupérées", recruiter_id=str(current_user.id), count=len(job_offers))
        return [JobOfferResponse.from_orm(job) for job in job_offers]
    except Exception as e:
        safe_log("error", "Erreur récupération mes offres d'emploi", error=str(e), recruiter_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de vos offres d'emploi"
        )

@router.get("/recruiter/statistics", summary="Statistiques du recruteur")
async def get_recruiter_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Récupérer les statistiques du recruteur connecté"""
    try:
        job_service = JobOfferService(db)
        
        # Récupérer le nombre total d'offres du recruteur
        total_jobs = await job_service.get_job_offers_count(current_user=current_user)
        
        # Statistiques simples pour le moment
        stats = {
            "recruiter_id": str(current_user.id),
            "total_offers": total_jobs,
            "message": "Statistiques de base (version simplifiée)"
        }
        
        safe_log("info", "Statistiques recruteur récupérées", recruiter_id=str(current_user.id))
        return stats
    except Exception as e:
        safe_log("error", "Erreur récupération statistiques", error=str(e), recruiter_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des statistiques"
        )
