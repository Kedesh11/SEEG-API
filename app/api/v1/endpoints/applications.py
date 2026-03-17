"""
Endpoints pour la gestion des candidatures
"""
from typing import Any, List, Optional
import base64
import structlog
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from bson import ObjectId

from app.db.database import get_db
from app.services.application import ApplicationService
from app.services.email import EmailService
from app.services.pdf import ApplicationPDFService
from app.services.webhook_etl_trigger import (
    ETLWebhookTriggerService, get_etl_webhook_trigger
)
from app.schemas.application import (
    Application, ApplicationCreate, ApplicationUpdate, ApplicationResponse,
    ApplicationListResponse, ApplicationDocumentWithDataResponse,
    ApplicationDocumentListResponse, ApplicationDocument,
    ApplicationDraftCreateRequest, ApplicationDraftUpdate,
    ApplicationHistoryCreate
)
from app.schemas.application_detail import ApplicationCompleteDetailResponse
from app.core.exceptions import (
    NotFoundError, ValidationError, BusinessLogicError, DatabaseError
)
from app.core.dependencies import get_current_user

logger = structlog.get_logger(__name__)

router = APIRouter(
    tags=["📝 Candidatures"],
)


def safe_log(level: str, message: str, **kwargs):
    """Log avec gestion d'erreur pour éviter les problèmes de handler."""
    try:
        getattr(logger, level)(message, **kwargs)
    except (TypeError, AttributeError):
        print(f"{level.upper()}: {message} - {kwargs}")


def convert_orm_to_schema(orm_obj, schema_class):
    """Convertit un objet dict (Motor) vers un schéma Pydantic."""
    return schema_class.model_validate(orm_obj)


def convert_orm_list_to_schema(orm_list: List, schema_class):
    """Convertit une liste d'objets dict (Motor) vers des schémas Pydantic."""
    return [schema_class.model_validate(item) for item in orm_list]


@router.post(
    "/",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une candidature complète (avec documents)",
    openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {
        "candidate_id": "00000000-0000-0000-0000-000000000001",
        "job_offer_id": "00000000-0000-0000-0000-0000000000AA",
        "reference_contacts": "Mme X (+241...), M. Y (+241...)",
        "has_been_manager": False,
        "ref_entreprise": "Entreprise ABC",
        "ref_fullname": "Jean Dupont",
        "ref_mail": "jean.dupont@abc.com",
        "ref_contact": "+241 01 02 03 04",
        "documents": [
            {
                "document_type": "cv",
                "file_name": "mon_cv.pdf",
                "file_data": "JVBERi0xLjQKJeLjz9MKMyAwIG9iago8PC9UeXBlIC9QYWdlCi9QYXJlbnQgMSAwIFIKL01lZGlhQm94IFswIDAgNjEyIDc5Ml0KPj4KZW5kb2JqCjQgMCBvYmoKPDwvVHlwZSAvRm9udAo+PgplbmRvYmoKMSAwIG9iago8PC9UeXBlIC9QYWdlcwovS2lkcyBbMyAwIFJdCi9Db3VudCAxCj4+CmVuZG9iagoyIDAgb2JqCjw8L1R5cGUgL0NhdGFsb2cKL1BhZ2VzIDEgMCBSCj4+CmVuZG9iagp4cmVmCjAgNQowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAxMTYgMDAwMDAgbiAKMDAwMDAwMDE3MyAwMDAwMCBuIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwODcgMDAwMDAgbiAKdHJhaWxlcgo8PC9TaXplIDUKL1Jvb3QgMiAwIFIKPj4Kc3RhcnR4cmVmCjIyMgolJUVPRgo="
            },
            {
                "document_type": "cover_letter",
                "file_name": "lettre_motivation.pdf",
                "file_data": "JVBERi0xLjQK... (base64)"
            }
        ]
    }}}},
    "responses": {"201": {"content": {"application/json": {"example": {"success": True, "message": "Candidature créée avec succès (2 documents uploadés)", "data": {"id": "uuid"}}}}}}
})
async def create_application(
    application_data: ApplicationCreate,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db),
    etl_trigger: ETLWebhookTriggerService = Depends(get_etl_webhook_trigger)
):
    """
    Créer une nouvelle candidature COMPLÈTE avec documents OBLIGATOIRES

    **🎯 FLOW UNIQUE ET ATOMIQUE**: Cette route permet de soumettre une candidature complète en une seule requête,
    incluant toutes les informations ET les 3 documents obligatoires.

    **Champs de base:**
    - **candidate_id**: ID du candidat
    - **job_offer_id**: ID de l'offre d'emploi
    - **reference_contacts**: Contacts de référence (optionnel)
    - **availability_start**: Date de disponibilité (optionnel)
    - **mtp_answers**: Réponses MTP (optionnel)
    - **documents**: Liste des 3 documents OBLIGATOIRES (CV, lettre de motivation, diplôme)

    **📄 Documents OBLIGATOIRES (3 minimum):**
    Le champ `documents` DOIT contenir exactement :
    1. **CV** (`document_type: "cv"`)
    2. **Lettre de motivation** (`document_type: "cover_letter"`)
    3. **Diplôme** (`document_type: "diplome"`)

    Format JSON :
    ```json
    "documents": [
        {
            "document_type": "cv",
            "file_name": "mon_cv.pdf",
            "file_data": "JVBERi0xLjQK..." // Contenu PDF encodé en base64
        },
        {
            "document_type": "cover_letter",
            "file_name": "lettre_motivation.pdf",
            "file_data": "JVBERi0xLjQK..."
        },
        {
            "document_type": "diplome",
            "file_name": "mon_diplome.pdf",
            "file_data": "JVBERi0xLjQK..."
        }
    ]
    ```

    **Validations automatiques :**
    - Présence des 3 documents obligatoires
    - Format PDF valide (magic number %PDF)
    - Taille max 10MB par document
    - Upload transactionnel : si la candidature échoue, aucun document n'est sauvegardé

    **Champs spécifiques aux candidats INTERNES (employés SEEG avec matricule):**
    - **has_been_manager**: Indique si le candidat a déjà occupé un poste de chef/manager (OBLIGATOIRE)
    - Les champs ref_* peuvent être NULL

    **Champs spécifiques aux candidats EXTERNES (sans matricule):**
    - **ref_entreprise**: Nom de l'entreprise/organisation recommandante (OBLIGATOIRE)
    - **ref_fullname**: Nom complet du référent (OBLIGATOIRE)
    - **ref_mail**: Adresse e-mail du référent (OBLIGATOIRE)
    - **ref_contact**: Numéro de téléphone du référent (OBLIGATOIRE)
    - Le champ has_been_manager peut rester FALSE par défaut

    **Validation automatique**: Le système vérifie que les champs obligatoires sont bien renseignés selon le type de candidat.

    **📊 Règles MTP (Métier, Talent, Paradigme):**

    Le système valide automatiquement le nombre de questions MTP selon le type de candidat:

    - **Candidats INTERNES** (avec matricule):
      - Questions Métier (mtp_metier_q1, q2, q3...): Maximum 7 questions
      - Questions Talent (mtp_talent_q1, q2, q3...): Maximum 3 questions
      - Questions Paradigme (mtp_paradigme_q1, q2, q3...): Maximum 3 questions
      - **Total: 13 questions maximum**

    - **Candidats EXTERNES** (sans matricule):
      - Questions Métier: Maximum 3 questions
      - Questions Talent: Maximum 3 questions
      - Questions Paradigme: Maximum 3 questions
      - **Total: 9 questions maximum**

    ⚠️ Si les limites sont dépassées, la candidature est automatiquement rejetée avec un message d'erreur détaillé.
    """
    try:
        # 🔷 ÉTAPE 1: Initialisation
        u_id = str(current_user.get("_id", current_user.get("id")))
        safe_log("info", "🚀 DÉBUT création candidature",
                 user_id=u_id,
                 user_role=current_user.get("role"),
                 candidate_id=str(application_data.candidate_id),
                 job_offer_id=str(application_data.job_offer_id),
                 has_mtp_answers=application_data.mtp_answers is not None)

        application_service = ApplicationService(db)
        email_service = EmailService(db)

        # 🔷 ÉTAPE 1.5: Créer le profil candidat s'il n'existe pas
        from app.services.user import UserService
        user_service = UserService(db)

        try:
            c_id = application_data.candidate_id
            cp = await user_service.get_candidate_profile(c_id)
            if not cp:
                safe_log("info", "📝 Création profil candidat",
                         candidate_id=str(c_id))
                from app.schemas.user import CandidateProfileCreate

                c_id = application_data.candidate_id
                is_obj = len(str(c_id)) == 24
                candidate_query = {"_id": ObjectId(c_id)} if is_obj else \
                                  {"_id": str(c_id)}
                candidate = await db.users.find_one(candidate_query)

                if candidate:
                    # Créer le profil avec les données disponibles (optionnelles)
                    profile_data = CandidateProfileCreate(
                        user_id=str(application_data.candidate_id),
                        years_experience=candidate.get('annees_experience'),
                        current_position=candidate.get('poste_actuel'),
                        address=candidate.get('adresse'),
                        skills=[]  # Tableau vide
                    )
                    await user_service.create_candidate_profile(
                        user_id=str(application_data.candidate_id),
                        profile_data=profile_data
                    )
                    safe_log("info", "✅ Profil candidat créé",
                            candidate_id=str(application_data.candidate_id))
        except Exception as e:
            # Ne pas bloquer la candidature si le profil candidat échoue
            safe_log("warning", "⚠️ Erreur création profil candidat (non-bloquant)",
                    error=str(e),
                    candidate_id=str(application_data.candidate_id))

        # 🔷 ÉTAPE 2: Validation et création
        safe_log("debug", "📝 Validation données candidature en cours...")
        u_id = str(current_user.get("_id", current_user.get("id")))
        application = await application_service.create_application(
            application_data, u_id
        )
        safe_log(
            "info", "✅ Candidature créée en mémoire",
            application_id=str(application.get("_id", application.get("id"))),
            status=application.get("status")
        )

        # Récupérer le candidat directement de Motor
        c_id = application.get("candidate_id")
        is_obj = c_id and len(str(c_id)) == 24
        candidate_query = {"_id": ObjectId(c_id)} if is_obj else \
                          {"_id": str(c_id)} if c_id else {}
        candidate_doc = await db.users.find_one(candidate_query) if c_id else None

        # Récupérer l'offre d'emploi
        j_id = application.get("job_offer_id")
        is_obj = j_id and len(str(j_id)) == 24
        job_offer_query = {"_id": ObjectId(j_id)} if is_obj else \
                           {"_id": str(j_id)} if j_id else {}
        job_offer_doc = await db.job_offers.find_one(job_offer_query) \
            if j_id else None

        c_email = candidate_doc.get("email") if candidate_doc else "unknown"
        c_name = f"{candidate_doc.get('first_name', '')} " \
                 f"{candidate_doc.get('last_name', '')}" if candidate_doc \
                 else "Unknown"
        job_title = job_offer_doc.get("title") if job_offer_doc else "Unknown"
        application_id = str(application.get("_id", application.get("id")))

        safe_log("debug", "✅ Relations chargées",
                 candidate_email=c_email,
                 job_title=job_title)

        # 🔷 ÉTAPE 4.5: Email + Notification candidature (PATTERN UNIFIÉ)
        try:
            from uuid import UUID as UUID_Type
            from app.services.notification_email_manager import NotificationEmailManager

            notif_email_manager = NotificationEmailManager(db)

            c_id_raw = application.get("candidate_id")
            c_id_uuid = c_id_raw if isinstance(c_id_raw, UUID_Type) else \
                        UUID_Type(str(c_id_raw))
            a_id_raw = application.get("_id")
            a_id_uuid = a_id_raw if isinstance(a_id_raw, UUID_Type) else \
                        UUID_Type(str(a_id_raw))

            result = await notif_email_manager.notify_and_email_application_submitted(
                user_id=c_id_uuid,
                application_id=a_id_uuid,
                candidate_email=c_email,
                candidate_name=c_name,
                job_title=job_title
            )

            safe_log("info", "✅ Email + notification candidature envoyés",
                    application_id=application_id,
                    email_sent=result["email_sent"],
                    notification_sent=result["notification_sent"])
        except Exception as e:
            safe_log("warning", "⚠️ Erreur email/notification candidature (non-bloquant)",
                    error=str(e), application_id=application_id)
            # Ne pas bloquer la candidature si email/notification échouent (fail-safe)

        # Compter les documents uploadés
        documents_count = 0
        if application_data.documents:
            # Récupérer le nombre réel de documents créés via Motor
            documents_count = await db.application_documents.count_documents({"application_id": str(application.get("_id", application.get("id")))})

        safe_log("info", "🎉 SUCCÈS création candidature complète",
                 application_id=application_id,
                 candidate_id=str(current_user.get("_id", current_user.get("id"))),
                 job_offer_id=str(application.get("job_offer_id")),
                 status=application.get("status"),
                 documents_uploaded=documents_count)

        # 🔷 ÉTAPE 5: Déclenchement automatique du webhook ETL (export vers Blob Storage)
        # Pattern: Fire-and-Forget, non-bloquant, fail-safe
        await etl_trigger.trigger_application_submitted(
            application_id=application_id
        )

        # Message dynamique selon les documents
        if documents_count > 0:
            message = f"Candidature créée avec succès ({documents_count} document(s) uploadé(s))"
        else:
            message = "Candidature créée avec succès"

        return ApplicationResponse(
            success=True,
            message=message,
            data=convert_orm_to_schema(application, Application)  # type: ignore
        )

    except ValidationError as e:
        error_msg = str(e)
        safe_log("warning", "❌ VALIDATION ÉCHOUÉE - Création candidature",
                 error=error_msg,
                 error_type="ValidationError",
                 user_id=str(current_user.get("_id", current_user.get("id"))),
                 candidate_id=str(application_data.candidate_id),
                 job_offer_id=str(application_data.job_offer_id),
                 has_mtp=application_data.mtp_answers is not None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
    except BusinessLogicError as e:
        error_msg = str(e)
        safe_log("warning", "❌ ERREUR LOGIQUE MÉTIER - Création candidature",
                 error=error_msg,
                 error_type="BusinessLogicError",
                 user_id=str(current_user.get("_id", current_user.get("id"))),
                 candidate_id=str(application_data.candidate_id),
                 job_offer_id=str(application_data.job_offer_id))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_msg)
    except Exception as e:
        # Log détaillé avec type et traceback complet
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}"
        error_traceback = traceback.format_exc()
        safe_log("error", "🔥 ERREUR CRITIQUE - Création candidature",
                error=error_msg,
                error_type=type(e).__name__,
                traceback=error_traceback,
                user_id=str(current_user.get("_id", current_user.get("id"))),
                candidate_id=str(application_data.candidate_id),
                job_offer_id=str(application_data.job_offer_id),
                has_mtp=application_data.mtp_answers is not None,
                mtp_count=len(application_data.mtp_answers) if application_data.mtp_answers else 0)
        # En développement, retourner le détail complet pour debug
        import os
        if os.getenv("DEBUG", "false").lower() == "true" or os.getenv("ENVIRONMENT", "production") == "development":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur interne: {error_msg}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur interne du serveur"
            )


@router.get(
    "/",
    response_model=ApplicationListResponse,
    summary="Lister les candidatures (filtres/pagination)",
    openapi_extra={
        "responses": {
            "200": {
                "content": {
                    "application/json": {
                        "example": {
                            "success": True,
                            "message": "0 candidature(s) trouvée(s)",
                            "data": [],
                            "total": 0,
                            "page": 1,
                            "per_page": 100
                        }
                    }
                }
            }
        }
    }
)
async def get_applications(
    skip: int = Query(0, ge=0, description="Ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Retourner"),
    status_filter: Optional[str] = Query(None, description="Filtrer par statut"),
    job_offer_id: Optional[str] = Query(None, description="Filtrer par offre d'emploi"),
    candidate_id: Optional[str] = Query(None, description="Filtrer par candidat"),
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Récupérer la liste des candidatures avec filtres

    - **skip**: Nombre d'éléments à ignorer (pagination)
    - **limit**: Nombre d'éléments à retourner (max 1000)
    - **status_filter**: Filtrer par statut (pending, reviewed, accepted, rejected)
    - **job_offer_id**: Filtrer par offre d'emploi
    - **candidate_id**: Filtrer par candidat
    """
    try:
        application_service = ApplicationService(db)

        applications, total = await application_service.get_applications(
            skip=skip,
            limit=limit,
            status_filter=status_filter,
            job_offer_id=job_offer_id,
            candidate_id=candidate_id
        )

        safe_log("info", "Liste candidatures récupérée", count=len(applications), requester_id=str(current_user.get("_id", current_user.get("id"))))
        return ApplicationListResponse(
            success=True,
            message=f"{len(applications)} candidature(s) trouvée(s)",
            data=convert_orm_list_to_schema(applications, Application),  # type: ignore
            total=total,
            page=(skip // limit) + 1,
            per_page=limit
        )

    except Exception as e:
        safe_log("error", "Erreur récupération liste candidatures", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.get("/{application_id}", response_model=ApplicationResponse, summary="Récupérer une candidature par ID", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Candidature récupérée avec succès", "data": {"id": "uuid"}}}}}, "404": {"description": "Candidature non trouvée"}}
})
async def get_application(
    application_id: str,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Récupérer une candidature par son ID avec toutes les relations
    (candidat, profil candidat, offre d'emploi, documents, historique, entretiens)
    """
    try:
        safe_log("info", "🔍 RECHERCHE candidature",
                 application_id=application_id,
                 user_id=str(current_user.get("_id", current_user.get("id"))),
                 user_role=current_user.get('role', 'candidate'))

        application_service = ApplicationService(db)
        application = await application_service.get_application_with_relations(application_id)

        if not application:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidature non trouvée")

        # Pour Motor, get_application_with_relations devrait déjà renvoyer un dict combiné.
        # On va l'assainir pour qu'il corresponde au schéma

        app_dict = application
        if hasattr(application, 'model_dump'):
            app_dict = application.model_dump()

        return ApplicationResponse(
            success=True,
            message="Candidature récupérée avec succès",
            data=app_dict  # type: ignore
        )

    except NotFoundError as e:
        safe_log("warning", "❌ NOT FOUND - Récupération candidature",
                 application_id=application_id,
                 user_id=str(current_user.get("_id", current_user.get("id"))),
                 error=str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        safe_log("error", "🔥 ERREUR CRITIQUE - Récupération candidature",
                 application_id=application_id,
                 user_id=str(current_user.get("_id", current_user.get("id"))),
                 error=str(e),
                 error_type=type(e).__name__,
                 traceback=error_traceback)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.get(
    "/{application_id}/complete",
    response_model=ApplicationCompleteDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Récupérer les détails complets d'une candidature",
    description="Récupère tous les détails : candidat + profil + documents, offre + questions MTP, réponses MTP"
)
async def get_complete_application_details(
    application_id: str,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    **Récupère les détails complets d'une candidature**

    Inclut :
    - Informations de la candidature (statut, dates, références)
    - Profil complet du candidat avec documents téléversés
    - Détails de l'offre d'emploi avec questions MTP
    - Réponses MTP du candidat

    Contrôle d'accès :
    - Admin/Recruteur : Toutes les candidatures
    - Candidat : Uniquement ses propres candidatures
    """
    try:
        safe_log(
            "info",
            "🔍 Récupération détails complets",
            application_id=application_id,
            user_id=str(current_user.get("_id", current_user.get("id")))
        )

        application_service = ApplicationService(db)

        # Vérifier existence et accès
        application = await application_service.get_application_with_relations(application_id)

        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidature non trouvée"
            )

        # Contrôle d'accès
        candidate_id_val = application.get('candidate_id') if isinstance(application, dict) else getattr(application, 'candidate_id', None)
        is_candidate = current_user.get('role', '') == "candidate"
        is_not_owner = str(candidate_id_val) != str(current_user.get("_id", current_user.get("id")))
        if is_candidate and is_not_owner:
            safe_log(
                "warning",
                "🚫 Accès non autorisé",
                application_id=application_id,
                user_id=str(current_user.get("_id", current_user.get("id")))
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès interdit"
            )

        # Récupérer détails complets
        complete_details = await application_service.get_complete_application_details(
            UUID(application_id)
        )

        safe_log(
            "info",
            "✅ Détails complets récupérés",
            application_id=application_id,
            documents_count=len(complete_details["candidate"]["documents"])
        )

        return ApplicationCompleteDetailResponse(
            success=True,
            message="Détails récupérés avec succès",
            data=complete_details  # type: ignore
        )

    except HTTPException:
        raise

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except Exception as e:
        import traceback
        safe_log(
            "error",
            "🔥 Erreur détails complets",
            error=str(e),
            traceback=traceback.format_exc()
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne"
        )


@router.put("/{application_id}", response_model=ApplicationResponse, summary="Mettre à jour une candidature", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"status": "reviewed"}}}},
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Candidature mise à  jour avec succès", "data": {"id": "uuid", "status": "reviewed"}}}}}}
})
async def update_application(
    application_id: str,
    application_data: ApplicationUpdate,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Mettre à jour une candidature
    """
    try:
        # 🔷 ÉTAPE 1: Initialisation
        safe_log("info", "🚀 DÉBUT mise à jour candidature",
                 application_id=application_id,
                 user_id=str(current_user.get("_id", current_user.get("id"))))
        application_service = ApplicationService(db)

        # 🔷 ÉTAPE 2: Mise à jour
        safe_log("debug", "📝 Application de la mise à jour...")
        application = await application_service.update_application(application_id, application_data)
        safe_log("info", "✅ Mise à jour appliquée en base")

        safe_log("info", "🎉 SUCCÈS mise à jour candidature",
                 application_id=application_id,
                 requester_id=str(current_user.get("_id", current_user.get("id"))),
                 new_status=application.get("status"))

        return ApplicationResponse(
            success=True,
            message="Candidature mise à jour avec succès",
            data=convert_orm_to_schema(application, Application)  # type: ignore
        )

    except NotFoundError as e:
        safe_log("warning", "❌ CANDIDATURE NON TROUVÉE - Mise à jour",
                 application_id=application_id,
                 user_id=str(current_user.get("_id", current_user.get("id"))),
                 error=str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        safe_log("warning", "❌ VALIDATION ÉCHOUÉE - Mise à jour candidature",
                 application_id=application_id,
                 user_id=str(current_user.get("_id", current_user.get("id"))),
                 error=str(e),
                 fields=list(application_data.dict(exclude_unset=True).keys()))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        safe_log("error", "🔥 ERREUR CRITIQUE - Mise à jour candidature",
                 application_id=application_id,
                 user_id=str(current_user.get("_id", current_user.get("id"))),
                 error=str(e),
                 error_type=type(e).__name__,
                 traceback=error_traceback)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une candidature",
    openapi_extra={
        "responses": {
            "204": {"description": "Supprimé"},
            "404": {"description": "Candidature non trouvée"}
        }
    }
)
async def delete_application(
    application_id: str,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Supprimer une candidature
    """
    try:
        application_service = ApplicationService(db)
        await application_service.delete_application(application_id)
        u_id = str(current_user.get("_id", current_user.get("id")))
        safe_log("info", "Candidature supprimée",
                 application_id=application_id, requester_id=u_id)

    except NotFoundError as e:
        safe_log("warning", "Candidature non trouvée pour suppression", application_id=application_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur suppression candidature", application_id=application_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


# Endpoints pour les documents PDF (lecture seule)
@router.get(
    "/{application_id}/documents",
    response_model=ApplicationDocumentListResponse,
    summary="Lister les documents d'une candidature",
    openapi_extra={
        "responses": {
            "200": {
                "content": {
                    "application/json": {
                        "example": {
                            "success": True,
                            "message": "0 document(s) trouvé(s)",
                            "data": [],
                            "total": 0
                        }
                    }
                }
            }
        }
    }
)
async def get_application_documents(
    application_id: str,
    document_type: Optional[str] = Query(None, description="Filtrer par type de document"),
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Récupérer les documents d'une candidature

    - **application_id**: ID de la candidature
    - **document_type**: Filtrer par type de document (optionnel)
    """
    try:
        application_service = ApplicationService(db)
        documents = await application_service.get_application_documents(application_id, document_type)

        safe_log("info", "Documents récupérés", application_id=application_id, count=len(documents))
        return ApplicationDocumentListResponse(
            success=True,
            message=f"{len(documents)} document(s) trouvé(s)",
            data=convert_orm_list_to_schema(documents, ApplicationDocument),  # type: ignore
            total=len(documents)
        )

    except NotFoundError as e:
        safe_log("warning", "Candidature non trouvée pour liste documents", application_id=application_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur récupération documents", application_id=application_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.get(
    "/{application_id}/documents/{document_id}",
    response_model=ApplicationDocumentWithDataResponse,
    summary="Récupérer un document avec données",
    openapi_extra={
        "responses": {
            "200": {
                "content": {
                    "application/json": {
                        "example": {
                            "success": True,
                            "message": "Document récupéré avec succès",
                            "data": {
                                "id": "uuid",
                                "file_data": "JVBERi0..."
                            }
                        }
                    }
                }
            },
            "404": {"description": "Document non trouvé"}
        }
    }
)
async def get_document_with_data(
    application_id: str,
    document_id: str,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Récupérer un document avec ses données binaires

    - **application_id**: ID de la candidature
    - **document_id**: ID du document
    """
    try:
        application_service = ApplicationService(db)
        document = await application_service.get_document_with_data(application_id, document_id)

        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document non trouvé")

        return ApplicationDocumentWithDataResponse(
            success=True,
            message="Document récupéré avec succès",
            data=document
        )

    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.get("/{application_id}/documents/{document_id}/download", summary="Télécharger un document PDF", openapi_extra={
    "responses": {"200": {"description": "Flux binaire PDF"}, "404": {"description": "Document non trouvé"}}
})
async def download_document(
    application_id: str,
    document_id: str,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Télécharger le document au format binaire (application/pdf) directement.
    """
    try:
        application_service = ApplicationService(db)
        document = await application_service.get_document_with_data(application_id, document_id)
        if not document or not document.get("file_data"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document non trouvé ou sans données")
        try:
            binary = base64.b64decode(document.get("file_data"))
        except Exception:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Données de document invalides")
        file_name = document.get("file_name") or f"document_{document_id}.pdf"
        if not file_name.lower().endswith('.pdf'):
            file_name = f"{file_name}.pdf"
        # Forcer le type PDF
        media_type = "application/pdf"
        headers = {"Content-Disposition": f"attachment; filename=\"{file_name}\""}
        return StreamingResponse(iter([binary]), media_type=media_type, headers=headers)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.delete("/{application_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer un document", openapi_extra={
    "responses": {"204": {"description": "Supprimé"}, "404": {"description": "Document non trouvé"}}
})
async def delete_document(
    application_id: str,
    document_id: str,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Supprimer un document d'une candidature

    - **application_id**: ID de la candidature
    - **document_id**: ID du document
    """
    try:
        application_service = ApplicationService(db)
        await application_service.delete_document(application_id, document_id)
        safe_log("info", "Document supprimé", application_id=application_id, document_id=document_id, user_id=str(current_user.get("_id", current_user.get("id"))))

    except NotFoundError as e:
        safe_log("warning", "Document non trouvé pour suppression", application_id=application_id, document_id=document_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur suppression document", application_id=application_id, document_id=document_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


# Endpoints pour les statistiques
@router.get("/stats/overview", response_model=dict, summary="Statistiques globales des candidatures", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Statistiques récupérées avec succès", "data": {}}}}}}
})
async def get_application_stats(
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Récupérer les statistiques des candidatures
    """
    try:
        application_service = ApplicationService(db)
        stats = await application_service.get_application_stats()

        return {
            "success": True,
            "message": "Statistiques récupérées avec succès",
            "data": stats
        }

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


# ---- Drafts de candidature ----
@router.get("/{application_id}/draft", response_model=dict, summary="Récupérer le brouillon de candidature", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "data": {"form_data": {}}}}}}}
})
async def get_application_draft(
    application_id: str,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    try:
        service = ApplicationService(db)
        draft = await service.get_application_draft(application_id, str(current_user.get("_id", current_user.get("id"))))
        return {"success": True, "data": draft}
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.post("/{application_id}/draft", response_model=dict, summary="Enregistrer le brouillon de candidature", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"form_data": {"step": 1}}}}},
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Brouillon enregistré", "data": {}}}}}}
})
async def upsert_application_draft(
    application_id: str,
    draft_data: ApplicationDraftUpdate,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    try:
        service = ApplicationService(db)
        draft = await service.upsert_application_draft(application_id, str(current_user.get("_id", current_user.get("id"))), draft_data)
        return {"success": True, "message": "Brouillon enregistré", "data": draft}
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.delete("/{application_id}/draft", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer le brouillon de candidature", openapi_extra={
    "responses": {"204": {"description": "Supprimé"}}
})
async def delete_application_draft(
    application_id: str,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    try:
        service = ApplicationService(db)
        await service.delete_application_draft(application_id, str(current_user.get("_id", current_user.get("id"))))
        return None
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


# ---- Historique des statuts ----
@router.get("/{application_id}/history", response_model=dict, summary="Lister l'historique de la candidature", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "data": []}}}}}
})
async def list_application_history(
    application_id: str,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    try:
        service = ApplicationService(db)
        history = await service.list_application_history(application_id)
        return {"success": True, "data": history}
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.post("/{application_id}/history", response_model=dict, summary="Ajouter un évènement d'historique", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"new_status": "reviewed", "notes": "Validation des pièces"}}}},
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Historique ajouté", "data": {"id": "uuid"}}}}}}
})
async def add_application_history(
    application_id: str,
    item: ApplicationHistoryCreate,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    try:
        service = ApplicationService(db)
        created = await service.add_application_history(application_id, item, str(current_user.get("_id", current_user.get("id"))))
        return {"success": True, "message": "Historique ajouté", "data": created}
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


# ---- Statistiques avancées ----
@router.get("/stats/advanced", response_model=dict, summary="Statistiques avancées des candidatures", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "data": {"total_applications": 0}}}}}}
})
async def get_advanced_application_stats(
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    try:
        service = ApplicationService(db)
        stats = await service.get_advanced_statistics()
        return {"success": True, "data": stats}
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


# ---- Export PDF de candidature ----
@router.get("/{application_id}/export/pdf", summary="Télécharger le PDF complet de la candidature", openapi_extra={
    "parameters": [
        {"in": "path", "name": "application_id", "required": True, "schema": {"type": "string", "format": "uuid"}},
        {"in": "query", "name": "include_documents", "required": False, "schema": {"type": "boolean", "default": False}},
        {"in": "query", "name": "format", "required": False, "schema": {"type": "string", "enum": ["A4", "Letter"], "default": "A4"}},
        {"in": "query", "name": "language", "required": False, "schema": {"type": "string", "enum": ["fr", "en"], "default": "fr"}}
    ],
    "responses": {
        "200": {"description": "PDF généré avec succès", "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}}},
        "403": {"description": "Accès non autorisé"},
        "404": {"description": "Candidature non trouvée"}
    }
})
async def export_application_pdf(
    application_id: str,
    include_documents: bool = Query(False, description="Inclure les documents joints (non implémenté dans cette version)"),
    format: str = Query("A4", description="Format du PDF (A4 ou Letter)"),
    language: str = Query("fr", description="Langue du PDF (fr ou en)"),
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Génère et télécharge un PDF complet de la candidature

    Contient:
    - Informations personnelles du candidat
    - Détails du poste visé
    - Parcours professionnel
    - Formation
    - Compétences
    - Réponses MTP (Métier, Talent, Paradigme)
    - Motivation & Disponibilité
    - Documents joints (liste)
    - Entretien programmé (si applicable)

    Permissions:
    - Candidat: Seulement ses propres candidatures
    - Recruteur: Candidatures de ses offres
    - Admin/Observer: Toutes les candidatures
    """
    try:
        safe_log("info", "🚀 Début export PDF", application_id=application_id, user_id=str(current_user.get("_id", current_user.get("id"))))

        # 1. Récupérer la candidature avec toutes les relations
        safe_log("info", "🔍 Récupération candidature avec relations", application_id=application_id)
        application_service = ApplicationService(db)
        application = await application_service.get_application_with_relations(application_id)

        if not application:
            safe_log("warning", "❌ Candidature non trouvée", application_id=application_id)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidature non trouvée")

        safe_log("info", "✅ Candidature récupérée", application_id=application_id, candidate_id=str(getattr(application, 'candidate_id', 'N/A')))

        # 2. Vérifier les permissions
        is_admin = current_user.get('role') in ['admin', 'observer']
        is_recruiter = current_user.get('role') == 'recruiter'
        is_candidate = str(application.get("candidate_id")) == str(current_user.get("_id", current_user.get("id")))

        if is_recruiter and getattr(application, 'job_offer', None):
            recruiter_id = getattr(application.job_offer, 'recruiter_id', None)
            if str(recruiter_id) != str(current_user.get("_id", current_user.get("id"))):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Accès non autorisé : vous ne pouvez télécharger que les candidatures de vos offres"
                )

        # Si ni admin, ni recruteur autorisé, ni candidat
        if not (is_admin or is_candidate or is_recruiter):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé"
            )

        # 3. Générer le PDF
        safe_log("info", "🔧 Création service PDF", application_id=application_id, format=format, language=language)
        pdf_service = ApplicationPDFService(page_format=format, language=language)

        safe_log("info", "📄 Génération PDF en cours", application_id=application_id)
        pdf_content = await pdf_service.generate_application_pdf(
            application=application,
            include_documents=include_documents
        )

        safe_log("info", "✅ PDF généré", application_id=application_id, pdf_size=len(pdf_content))

        # 4. Construire le nom du fichier
        filename = ApplicationPDFService.get_filename(application)

        # 5. Retourner le PDF
        return StreamingResponse(
            iter([pdf_content]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except NotFoundError as e:
        safe_log("warning", "Candidature non trouvée pour export PDF", application_id=application_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur génération PDF", application_id=application_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la génération du PDF: {str(e)}"
        )


# ---- Drafts globaux par offre (job_offer_id) ----
@router.get("/drafts/by-offer", response_model=dict, summary="Récupérer le brouillon par offre", openapi_extra={
    "parameters": [
        {"in": "query", "name": "job_offer_id", "required": True, "schema": {"type": "string", "format": "uuid"}}
    ],
    "responses": {
        "200": {"content": {"application/json": {"example": {"success": True, "data": {"form_data": {"step": 1}, "ui_state": {}}}}}},
        "404": {"description": "Aucun brouillon trouvé"}
    }
})
async def get_draft_by_job_offer(
    job_offer_id: str = Query(..., description="ID de l'offre d'emploi"),
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    try:
        safe_log("debug", "🔍 GET draft démarré", user_id=str(current_user.get("_id", current_user.get("id"))), job_offer_id=job_offer_id)
        service = ApplicationService(db)
        draft = await service.get_draft(user_id=str(current_user.get("_id", current_user.get("id"))), job_offer_id=job_offer_id)

        if not draft:
            safe_log(
                "debug", "✅ Aucun brouillon trouvé",
                user_id=str(current_user.get("_id", current_user.get("id"))),
                job_offer_id=job_offer_id
            )
            return {"success": True, "data": None}

        safe_log("debug", "📦 Brouillon trouvé, conversion en dict...", user_id=str(current_user.get("_id", current_user.get("id"))), job_offer_id=job_offer_id)

        # Convertir l'objet ORM en dictionnaire de manière sécurisée
        # Utiliser getattr pour éviter les problèmes avec les colonnes SQLAlchemy
        try:
            created_at_val = getattr(draft, 'created_at', None)
            updated_at_val = getattr(draft, 'updated_at', None)
            form_data_val = getattr(draft, 'form_data', None)
            ui_state_val = getattr(draft, 'ui_state', None)

            draft_data = {
                "user_id": str(draft.get("user_id")),
                "job_offer_id": str(draft.get("job_offer_id")),
                "form_data": form_data_val if form_data_val is not None else {},
                "ui_state": ui_state_val if ui_state_val is not None else {},
                "created_at": created_at_val.isoformat() if hasattr(created_at_val, 'isoformat') else created_at_val,
                "updated_at": updated_at_val.isoformat() if hasattr(updated_at_val, 'isoformat') else updated_at_val,
            }

            safe_log("info", "✅ Brouillon converti avec succès", user_id=str(current_user.get("_id", current_user.get("id"))), job_offer_id=job_offer_id)
            return {"success": True, "data": draft_data}
        except Exception as convert_error:
            safe_log("error", "❌ Erreur conversion brouillon", error=str(convert_error), error_type=type(convert_error).__name__)
            raise

    except ValidationError as e:
        safe_log("warning", "⚠️ Validation error GET draft", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessLogicError as e:
        safe_log("error", "❌ Business logic error GET draft", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur métier: {str(e)}")
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        safe_log("error", "❌ Erreur inattendue GET draft",
                error=str(e),
                error_type=type(e).__name__,
                trace=error_trace,
                user_id=str(current_user.get("_id", current_user.get("id"))),
                job_offer_id=job_offer_id)
        raise HTTPException(status_code=500, detail=f"Erreur interne: {type(e).__name__} - {str(e)}")


@router.post(
    "/drafts/by-offer",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,  # Standard REST : 201 pour création de ressource
    summary="Créer/Maj le brouillon par offre",
    openapi_extra={
        "requestBody": {"content": {"application/json": {"example": {
            "job_offer_id": "00000000-0000-0000-0000-0000000000AA",
            "form_data": {"step": 1, "values": {"firstname": "Ada"}},
            "ui_state": {"currentStep": 2}
        }}}},
        "responses": {"201": {"content": {"application/json": {"example": {"success": True, "message": "Brouillon enregistré", "data": {}}}}}}
    }
)
async def upsert_draft_by_job_offer(
    payload: ApplicationDraftCreateRequest,
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """
    Créer ou mettre à jour un brouillon de candidature

    Gestion d'erreurs robuste selon les meilleures pratiques :
    - Validation des données
    - Transaction avec commit/rollback approprié
    - Logging structuré pour traçabilité
    - Exceptions spécifiques selon le type d'erreur
    """
    # Récupérer l'ID utilisateur de manière sécurisée
    user_id = str(current_user.get("_id", current_user.get("id")))
    job_offer_id_str = str(payload.job_offer_id)

    try:
        safe_log("info", "🚀 Début sauvegarde brouillon",
                user_id=user_id,
                job_offer_id=job_offer_id_str)

        service = ApplicationService(db)

        # Forcer l'user_id depuis le token pour sécurité (principe de moindre privilège)
        data = {
            "user_id": user_id,
            "job_offer_id": job_offer_id_str,
            "form_data": payload.form_data,
            "ui_state": payload.ui_state,
        }

        # Sauvegarder le brouillon
        draft = await service.save_draft(data)

        # MongoDB auto-commit
        safe_log("info", "✅ Brouillon sauvegardé",
                user_id=user_id,
                job_offer_id=job_offer_id_str)

        # Créer une notification brouillon (pas d'email nécessaire)
        try:
            from uuid import UUID as UUID_Type
            from app.services.notification_email_manager import NotificationEmailManager
            from bson import ObjectId

            # Récupérer le titre de l'offre
            job_id = payload.job_offer_id
            job_query = {"_id": ObjectId(job_id) if len(str(job_id)) == 24 else job_id}
            job_offer = await db.job_offers.find_one(job_query)

            if job_offer:
                notif_email_manager = NotificationEmailManager(db)

                # Convertir les types pour éviter les erreurs de type checking
                user_id_uuid = user_id if isinstance(user_id, UUID_Type) else UUID_Type(str(user_id))
                job_offer_id_uuid = payload.job_offer_id if isinstance(payload.job_offer_id, UUID_Type) else UUID_Type(str(payload.job_offer_id))

                result = await notif_email_manager.notify_application_draft_saved(
                    user_id=user_id_uuid,
                    job_offer_id=job_offer_id_uuid,
                    job_title=str(job_offer.get("title"))
                )
                safe_log("debug", "✅ Notification brouillon créée",
                        notification_sent=result["notification_sent"])
        except Exception as e:
            safe_log("warning", "⚠️ Erreur notification brouillon", error=str(e))

        # Convertir l'objet ORM en dictionnaire pour la réponse
        draft_data = {
            "user_id": str(draft.get("user_id")),
            "job_offer_id": str(draft.get("job_offer_id")),
            "form_data": draft.get("form_data"),
            "ui_state": draft.get("ui_state"),
            "created_at": draft.get("created_at").isoformat() if hasattr(draft.get("created_at"), 'isoformat') else draft.get("created_at"),
            "updated_at": draft.get("updated_at").isoformat() if hasattr(draft.get("updated_at"), 'isoformat') else draft.get("updated_at"),
        }

        return {
            "success": True,
            "message": "Brouillon enregistré avec succès",
            "data": draft_data
        }

    except ValidationError as e:
        # Erreur de validation
        safe_log("warning", "⚠️ Validation échouée sauvegarde brouillon",
                user_id=user_id,
                error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except DatabaseError as e:
        # Erreur de base de données
        safe_log("error", "❌ Erreur BD sauvegarde brouillon",
                user_id=user_id,
                error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la sauvegarde du brouillon"
        )

    except Exception as e:
        # Erreur inattendue
        safe_log("error", "❌ Erreur inattendue sauvegarde brouillon",
                user_id=user_id,
                error_type=type(e).__name__,
                error=str(e),
                exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Une erreur interne s'est produite"
        )


@router.delete("/drafts/by-offer", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer le brouillon par offre", openapi_extra={
    "parameters": [
        {"in": "query", "name": "job_offer_id", "required": True, "schema": {"type": "string", "format": "uuid"}}
    ],
    "responses": {"204": {"description": "Supprimé"}}
})
async def delete_draft_by_job_offer(
    job_offer_id: str = Query(..., description="ID de l'offre d'emploi"),
    current_user: Any = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    try:
        service = ApplicationService(db)
        await service.delete_draft(user_id=str(current_user.get("_id", current_user.get("id"))), job_offer_id=job_offer_id)
        return None
    except ValidationError as e:
        safe_log("warning", "⚠️ Erreur validation suppression brouillon", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        safe_log("error", "❌ Erreur suppression brouillon", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")
