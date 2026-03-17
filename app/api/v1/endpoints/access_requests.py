"""
Endpoints pour la gestion des demandes d'accès à la plateforme.

Ces endpoints permettent aux recruteurs de :
- Lister les demandes d'accès en attente
- Approuver une demande (active le compte utilisateur)
- Refuser une demande (bloque le compte utilisateur)
- Marquer les demandes comme vues (pour le badge de notification)
"""
import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Any, Optional

from app.db.database import get_db

from app.services.access_request import AccessRequestService
from app.services.email import EmailService
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundError, ValidationError
from app.schemas.access_request import (
    AccessRequestListResponse,
    AccessRequestResponse,
    AccessRequestWithUser,
    AccessRequestApprove,
    AccessRequestReject
)

logger = structlog.get_logger(__name__)
router = APIRouter(
    tags=["🔑 Demandes d'accès"],
)


def safe_log(level: str, message: str, **kwargs):
    """Log avec gestion d'erreur."""
    try:
        getattr(logger, level)(message, **kwargs)
    except (TypeError, AttributeError):
        print(f"{level.upper()}: {message} - {kwargs}")


def require_recruiter_or_admin(current_user: Any) -> None:
    """
    Vérifier que l'utilisateur est recruteur ou admin.

    Raises:
        HTTPException: Si l'utilisateur n'a pas les permissions
    """
    # Accepter les deux formats pour compatibilité : 'recruiter'
    if current_user.get("role") not in ['recruiter', 'admin']:
        safe_log(
            "warning", "🚨 ACCÈS REFUSÉ - Access-requests",
            user_id=str(current_user.get("_id", current_user.get("id"))),
            user_role=current_user.get("role"),
            user_email=current_user.get("email"),
            required_roles=['recruiter', 'admin'],
            security_event="unauthorized_access_attempt"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux recruteurs et administrateurs"
        )

    # ✅ LOG: Accès autorisé
    safe_log(
        "debug", "✅ Accès autorisé - Access-requests",
        user_id=str(current_user.get("_id", current_user.get("id"))),
        user_role=current_user.get("role")
    )


@router.get(
    "/",
    response_model=AccessRequestListResponse,
    summary="Lister les demandes d'accès",
    description="""
    Récupérer la liste des demandes d'accès avec filtres.

    **Filtres disponibles** :
    - `status` : Filtrer par statut (pending, approved, rejected)
    - `viewed` : Filtrer par état vu/non vu (true/false)
    - `skip` et `limit` : Pagination

    **Permissions** : Recruteur, Admin

    **Retourne également** :
    - `pending_count` : Nombre de demandes en attente
    - `unviewed_count` : Nombre de demandes non vues (pour le badge de notification)
    """
)
async def list_access_requests(
    status_filter: Optional[str] = Query(None, description="Filtrer par statut: pending, approved, rejected"),
    viewed_filter: Optional[bool] = Query(None, description="Filtrer par état vu/non vu"),
    skip: int = Query(0, ge=0, description="Nombre d'éléments à ignorer"),
    limit: int = Query(100, ge=1, le=500, description="Nombre d'éléments à retourner"),
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """Lister toutes les demandes d'accès avec filtres."""
    import time
    start_time = time.time()

    try:
        # 📊 LOG: Début de requête
        safe_log("info", "🔍 Début récupération access-requests",
                user_id=str(current_user.get("_id", current_user.get("id"))),
                user_role=current_user.get("role"),
                status_filter=status_filter,
                viewed_filter=viewed_filter,
                skip=skip,
                limit=limit)

        # Vérifier les permissions
        safe_log("debug", "🔐 Vérification permissions...")
        require_recruiter_or_admin(current_user)
        safe_log("debug", "✅ Permissions OK")

        # Créer le service
        safe_log("debug", "🏗️ Création AccessRequestService...")
        service = AccessRequestService(db)

        # Récupérer les demandes
        safe_log("debug", "📋 Récupération demandes depuis DB...")
        requests, total, pending_count, unviewed_count = await service.get_all_requests(
            status_filter=status_filter,
            viewed_filter=viewed_filter,
            skip=skip,
            limit=limit
        )

        safe_log("info", "✅ Demandes récupérées",
                count=len(requests),
                total=total,
                pending_count=pending_count,
                unviewed_count=unviewed_count)

        # MongoDB no commit needed for reads
        pass

        # Convertir en schémas Pydantic
        safe_log("debug", "🔄 Conversion vers schémas Pydantic...")
        request_data = [
            AccessRequestWithUser(
                id=req.id,  # type: ignore
                user_id=req.user_id,  # type: ignore
                email=req.email,  # type: ignore
                first_name=req.first_name,
                last_name=req.last_name,
                phone=req.phone,
                matricule=req.matricule,
                request_type=req.request_type,  # type: ignore
                status=req.status,  # type: ignore
                rejection_reason=req.rejection_reason,
                viewed=req.viewed,  # type: ignore
                created_at=req.created_at,  # type: ignore
                reviewed_at=req.reviewed_at,
                reviewed_by=req.reviewed_by
            )
            for req in requests
        ]

        # 📊 LOG: Performance
        duration = time.time() - start_time
        safe_log("info", "⏱️ Performance list_access_requests",
                duration_seconds=round(duration, 3),
                total_count=total,
                returned_count=len(request_data))

        safe_log("info", "✅ SUCCESS - Access-requests retournées",
                total=total,
                returned=len(request_data),
                pending=pending_count,
                unviewed=unviewed_count)

        return AccessRequestListResponse(
            success=True,
            message=f"{total} demande(s) d'accès trouvée(s)",
            data=request_data,
            total=total,
            pending_count=pending_count,
            unviewed_count=unviewed_count
        )

    except HTTPException as he:
        # 🔴 LOG: Erreur HTTP (permissions, etc.)
        safe_log("warning", "⚠️ HTTPException dans list_access_requests",
                user_id=str(current_user.get("_id", current_user.get("id"))),
                status_code=he.status_code,
                detail=he.detail)
        raise
    except Exception as e:
        # 🔴 LOG: Erreur critique avec contexte complet
        import traceback
        safe_log(
            "error", "❌ ERREUR CRITIQUE - list_access_requests",
            user_id=str(current_user.get("_id", current_user.get("id"))),
            user_role=current_user.get("role"),
            error_type=type(e).__name__,
            error_message=str(e),
            traceback=traceback.format_exc(),
            status_filter=status_filter,
            viewed_filter=viewed_filter,
            duration_seconds=round(time.time() - start_time, 3)
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne: {str(e)}"
        )


@router.post(
    "/approve",
    response_model=AccessRequestResponse,
    summary="Approuver une demande d'accès",
    description="""
    Approuver une demande d'accès.

    **Actions effectuées** :
    1. Vérifier que la demande existe et est 'pending'
    2. Mettre à jour `users.statut = 'actif'`
    3. Mettre à jour `access_requests.status = 'approved'`
    4. Enregistrer `reviewed_at` et `reviewed_by`
    5. Envoyer un email de confirmation au candidat

    **Permissions** : Recruteur, Admin
    """
)
async def approve_access_request(
    request_data: AccessRequestApprove,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """Approuver une demande d'accès."""
    try:
        # Vérifier les permissions
        require_recruiter_or_admin(current_user)

        # Créer les services
        access_service = AccessRequestService(db)
        email_service = EmailService(db)

        # Approuver la demande
        approved_request = await access_service.approve_request(
            request_id=request_data.request_id,
            reviewer_id=str(current_user.get("_id", current_user.get("id")))
        )

        # Récupérer le sexe de l'utilisateur pour la salutation
        from bson import ObjectId
        user_id = approved_request.user_id if hasattr(approved_request, 'user_id') else approved_request.get('user_id')
        user_query = {"_id": ObjectId(user_id) if len(str(user_id)) == 24 else user_id}
        approved_user = await db.users.find_one(user_query)

        # Email 4 : Approbation
        try:
            first_name_str = str(approved_request.first_name) if approved_request.first_name is not None else ""
            last_name_str = str(approved_request.last_name) if approved_request.last_name is not None else ""
            sexe_str = str(approved_user.get("sexe")) if approved_user and approved_user.get("sexe") is not None else None

            await email_service.send_access_approved_email(
                to_email=str(approved_request.email),
                first_name=first_name_str,
                last_name=last_name_str,
                sexe=sexe_str
            )
            safe_log("info", "Email d'approbation envoyé",
                    request_id=str(approved_request.id),
                    to=approved_request.email)
        except Exception as e:
            safe_log("warning", "Erreur envoi email approbation", error=str(e))

        safe_log("info", "Demande d'accès approuvée",
                request_id=str(approved_request.id),
                user_id=str(approved_request.user_id),
                reviewer_id=str(current_user.get("_id", current_user.get("id"))))

        return AccessRequestResponse(
            success=True,
            message="Demande d'accès approuvée avec succès. Le candidat peut maintenant se connecter.",
            data=AccessRequestWithUser(
                id=approved_request.id,  # type: ignore
                user_id=approved_request.user_id,  # type: ignore
                email=approved_request.email,  # type: ignore
                first_name=approved_request.first_name,
                last_name=approved_request.last_name,
                phone=approved_request.phone,
                matricule=approved_request.matricule,
                request_type=approved_request.request_type,  # type: ignore
                status=approved_request.status,  # type: ignore
                rejection_reason=approved_request.rejection_reason,
                viewed=approved_request.viewed,  # type: ignore
                created_at=approved_request.created_at,  # type: ignore
                reviewed_at=approved_request.reviewed_at,
                reviewed_by=approved_request.reviewed_by
            )
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        safe_log("error", "Erreur approbation demande", error=str(e), request_id=str(request_data.request_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'approbation de la demande: {str(e)}"
        )


@router.post(
    "/reject",
    response_model=AccessRequestResponse,
    summary="Refuser une demande d'accès",
    description="""
    Refuser une demande d'accès avec un motif.

    **Actions effectuées** :
    1. Vérifier que la demande existe et est 'pending'
    2. Vérifier que le motif fait au moins 20 caractères
    3. Mettre à jour `users.statut = 'bloqué'`
    4. Mettre à jour `access_requests.status = 'rejected'`
    5. Enregistrer `rejection_reason`, `reviewed_at` et `reviewed_by`
    6. Envoyer un email au candidat avec le motif du refus

    **Permissions** : Recruteur, Admin

    **Note** : Le motif de refus doit contenir au moins 20 caractères pour expliquer clairement la raison.
    """
)
async def reject_access_request(
    request_data: AccessRequestReject,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """Refuser une demande d'accès."""
    try:
        # Vérifier les permissions
        require_recruiter_or_admin(current_user)

        # Créer les services
        access_service = AccessRequestService(db)
        email_service = EmailService(db)

        # Refuser la demande
        rejected_request = await access_service.reject_request(
            request_id=request_data.request_id,
            reviewer_id=str(current_user.get("_id", current_user.get("id"))),
            rejection_reason=request_data.rejection_reason
        )

        # Récupérer le sexe de l'utilisateur pour la salutation
        from bson import ObjectId
        user_id = rejected_request.user_id if hasattr(rejected_request, 'user_id') else rejected_request.get('user_id')
        user_query = {"_id": ObjectId(user_id) if len(str(user_id)) == 24 else user_id}
        rejected_user = await db.users.find_one(user_query)

        # Email 5 : Refus avec motif
        try:
            first_name_str = str(rejected_request.first_name) if rejected_request.first_name is not None else ""
            last_name_str = str(rejected_request.last_name) if rejected_request.last_name is not None else ""
            sexe_str = str(rejected_user.get("sexe")) if rejected_user and rejected_user.get("sexe") is not None else None

            await email_service.send_access_rejected_email(
                to_email=str(rejected_request.email),
                first_name=first_name_str,
                last_name=last_name_str,
                rejection_reason=request_data.rejection_reason,
                sexe=sexe_str
            )
            safe_log("info", "Email de refus envoyé",
                    request_id=str(rejected_request.id),
                    to=rejected_request.email)
        except Exception as e:
            safe_log("warning", "Erreur envoi email refus", error=str(e))

        safe_log("info", "Demande d'accès refusée",
                request_id=str(rejected_request.id),
                user_id=str(rejected_request.user_id),
                reviewer_id=str(current_user.get("_id", current_user.get("id"))))

        return AccessRequestResponse(
            success=True,
            message="Demande d'accès refusée. Le candidat a été informé par email.",
            data=AccessRequestWithUser(
                id=rejected_request.id,  # type: ignore
                user_id=rejected_request.user_id,  # type: ignore
                email=rejected_request.email,  # type: ignore
                first_name=rejected_request.first_name,
                last_name=rejected_request.last_name,
                phone=rejected_request.phone,
                matricule=rejected_request.matricule,
                request_type=rejected_request.request_type,  # type: ignore
                status=rejected_request.status,  # type: ignore
                rejection_reason=rejected_request.rejection_reason,
                viewed=rejected_request.viewed,  # type: ignore
                created_at=rejected_request.created_at,  # type: ignore
                reviewed_at=rejected_request.reviewed_at,
                reviewed_by=rejected_request.reviewed_by
            )
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        safe_log("error", "Erreur refus demande", error=str(e), request_id=str(request_data.request_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du refus de la demande: {str(e)}"
        )


@router.post(
    "/mark-all-viewed",
    summary="Marquer toutes les demandes comme vues",
    description="""
    Marquer toutes les demandes en attente comme vues.

    **Usage** : Appelé automatiquement quand un recruteur visite la page des demandes d'accès.
    Cela réinitialise le badge de notification.

    **Permissions** : Recruteur, Admin, Observateur
    """
)
async def mark_all_as_viewed(
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """Marquer toutes les demandes pending comme vues."""
    try:
        # Vérifier les permissions (y compris observateur)
        if current_user.get("role") not in ['recruiter', 'admin', 'observer']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès réservé aux recruteurs, administrateurs et observateurs"
            )

        # Créer le service
        service = AccessRequestService(db)

        # Marquer comme vues
        count = await service.mark_all_as_viewed()



        safe_log("info", "Demandes marquées comme vues",
                count=count,
                user_id=str(current_user.get("_id", current_user.get("id"))))

        return {
            "success": True,
            "message": f"{count} demande(s) marquée(s) comme vue(s)",
            "count": count
        }

    except HTTPException:
        raise
    except Exception as e:
        safe_log("error", "Erreur marquage viewed", error=str(e), user_id=str(current_user.get("_id", current_user.get("id"))))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du marquage des demandes: {str(e)}"
        )


@router.get(
    "/unviewed-count",
    summary="Obtenir le nombre de demandes non vues",
    description="""
    Obtenir le nombre de demandes pending et non vues.

    **Usage** : Pour afficher le badge de notification dans l'interface.

    **Permissions** : Recruteur, Admin, Observateur
    """
)
async def get_unviewed_count(
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """Obtenir le nombre de demandes non vues (pour le badge)."""
    try:
        # Vérifier les permissions
        if current_user.get("role") not in ['recruiter', 'admin', 'observer']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès réservé aux recruteurs, administrateurs et observateurs"
            )

        # Créer le service
        service = AccessRequestService(db)

        # Compter
        count = await service.get_unviewed_count()

        return {
            "success": True,
            "count": count
        }

    except HTTPException:
        raise
    except Exception as e:
        safe_log("error", "Erreur comptage unviewed", error=str(e))
        return {
            "success": False,
            "count": 0,
            "error": str(e)
        }

