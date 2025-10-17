"""
Endpoints pour la gestion des candidatures
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import base64
import uuid as uuid_module
from uuid import UUID
import structlog
from fastapi.responses import StreamingResponse

logger = structlog.get_logger(__name__)

from app.db.database import get_db
from app.services.application import ApplicationService
from app.services.file import FileService
from app.services.email import EmailService
from app.services.pdf import ApplicationPDFService
from app.schemas.application import (
    Application, ApplicationCreate, ApplicationUpdate, ApplicationResponse, ApplicationListResponse,
    ApplicationDocumentResponse, ApplicationDocumentCreate, ApplicationDocumentUpdate,
    ApplicationDocumentWithDataResponse, ApplicationDocumentListResponse,
    ApplicationDocument, FileUploadRequest, MultipleFileUploadRequest,
    ApplicationDraftCreate, ApplicationDraftCreateRequest, ApplicationDraftUpdate, ApplicationDraft, ApplicationDraftInDB,
    ApplicationHistoryCreate, ApplicationHistory, ApplicationHistoryInDB
)
from app.schemas.application_detail import ApplicationCompleteDetailResponse
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.application import Application as ApplicationModel, ApplicationDocument as ApplicationDocumentModel
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError, FileError, DatabaseError
# from app.core.rate_limit import limiter, UPLOAD_LIMITS  # ⚠️ Désactivé temporairement

router = APIRouter(
    tags=["📝 Candidatures"],)


def safe_log(level: str, message: str, **kwargs):
    """Log avec gestion d'erreur pour éviter les problèmes de handler."""
    try:
        getattr(logger, level)(message, **kwargs)
    except (TypeError, AttributeError):
        print(f"{level.upper()}: {message} - {kwargs}")


def convert_orm_to_schema(orm_obj, schema_class):
    """Convertit un objet ORM vers un schéma Pydantic."""
    return schema_class.model_validate(orm_obj)


def convert_orm_list_to_schema(orm_list: List, schema_class):
    """Convertit une liste d'objets ORM vers des schémas Pydantic."""
    return [schema_class.model_validate(item) for item in orm_list]


@router.post("/", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED, summary="Créer une candidature complète (avec documents)", openapi_extra={
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
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
        safe_log("info", "🚀 DÉBUT création candidature", 
                 user_id=str(current_user.id),
                 user_role=current_user.role,
                 candidate_id=str(application_data.candidate_id),
                 job_offer_id=str(application_data.job_offer_id),
                 has_mtp_answers=application_data.mtp_answers is not None)
        
        application_service = ApplicationService(db)
        email_service = EmailService(db)
        
        # 🔷 ÉTAPE 1.5: Créer le profil candidat s'il n'existe pas
        from app.services.user import UserService
        user_service = UserService(db)
        
        try:
            candidate_profile = await user_service.get_candidate_profile(application_data.candidate_id)
            if not candidate_profile:
                safe_log("info", "📝 Première candidature - Création profil candidat", 
                        candidate_id=str(application_data.candidate_id))
                from app.schemas.user import CandidateProfileCreate
                from app.models.user import User
                
                # Récupérer les infos de l'utilisateur pour initialiser le profil
                result = await db.execute(
                    select(User).where(User.id == application_data.candidate_id)
                )
                candidate = result.scalar_one_or_none()
                
                if candidate:
                    # Créer le profil avec les données disponibles (optionnelles)
                    profile_data = CandidateProfileCreate(
                        user_id=application_data.candidate_id,
                        years_experience=getattr(candidate, 'annees_experience', None),
                        current_position=getattr(candidate, 'poste_actuel', None),
                        address=getattr(candidate, 'adresse', None),
                        skills=[]  # Tableau vide au lieu de None pour PostgreSQL VARCHAR[]
                    )
                    await user_service.create_candidate_profile(
                        user_id=application_data.candidate_id,
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
        application = await application_service.create_application(
            application_data, str(current_user.id)
        )
        safe_log("info", "✅ Candidature créée en mémoire", 
                 application_id=str(application.id),
                 status=application.status)
        
        # 🔷 ÉTAPE 3: Flush et chargement des relations (AVANT commit)
        safe_log("debug", "💾 Flush en base pour obtenir les IDs...")
        await db.flush()
        safe_log("debug", "📧 Chargement explicite des relations...")
        await db.refresh(application, ["candidate", "job_offer"])
        
        # Maintenant on peut accéder aux relations en toute sécurité
        candidate_email = application.candidate.email
        candidate_name = f"{application.candidate.first_name} {application.candidate.last_name}"
        job_title = application.job_offer.title
        application_id = str(application.id)
        safe_log("debug", "✅ Relations chargées",
                 candidate_email=candidate_email,
                 job_title=job_title)
        
        # 🔷 ÉTAPE 4: Persistence définitive en base de données
        safe_log("debug", "💾 Commit transaction en cours...")
        await db.commit()
        safe_log("info", "✅ Transaction committée avec succès")
        
        safe_log("debug", "✅ Candidature persistée définitivement")
        
        # 🔷 ÉTAPE 4.5: Email + Notification candidature (PATTERN UNIFIÉ)
        try:
            from uuid import UUID as UUID_Type
            from app.services.notification_email_manager import NotificationEmailManager
            
            notif_email_manager = NotificationEmailManager(db)
            
            # Convertir les types pour éviter les erreurs de type checking
            candidate_id_uuid = application.candidate_id if isinstance(application.candidate_id, UUID_Type) else UUID_Type(str(application.candidate_id))
            application_id_uuid = application.id if isinstance(application.id, UUID_Type) else UUID_Type(str(application.id))
            
            result = await notif_email_manager.notify_and_email_application_submitted(
                user_id=candidate_id_uuid,
                application_id=application_id_uuid,
                candidate_email=candidate_email,
                candidate_name=candidate_name,
                job_title=job_title
            )
            await db.commit()
            
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
            # Récupérer le nombre réel de documents créés
            documents_result = await db.execute(
                select(ApplicationDocumentModel).where(
                    ApplicationDocumentModel.application_id == application.id  # type: ignore
                )
            )
            documents_count = len(documents_result.scalars().all())
        
        safe_log("info", "🎉 SUCCÈS création candidature complète", 
                 application_id=str(application.id), 
                 candidate_id=str(current_user.id),
                 job_offer_id=str(application.job_offer_id),
                 status=application.status,
                 documents_uploaded=documents_count)
        
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
                 user_id=str(current_user.id),
                 candidate_id=str(application_data.candidate_id),
                 job_offer_id=str(application_data.job_offer_id),
                 has_mtp=application_data.mtp_answers is not None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
    except BusinessLogicError as e:
        error_msg = str(e)
        safe_log("warning", "❌ ERREUR LOGIQUE MÉTIER - Création candidature", 
                 error=error_msg,
                 error_type="BusinessLogicError",
                 user_id=str(current_user.id),
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
                user_id=str(current_user.id),
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


@router.get("/", response_model=ApplicationListResponse, summary="Lister les candidatures (filtres/pagination)", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {
        "success": True,
        "message": "0 candidature(s) trouvÃ©e(s)",
        "data": [],
        "total": 0,
        "page": 1,
        "per_page": 100
    }}}}}
})
async def get_applications(
    skip: int = Query(0, ge=0, description="Nombre d'Ã©lÃ©ments Ã  ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre d'Ã©lÃ©ments Ã  retourner"),
    status_filter: Optional[str] = Query(None, description="Filtrer par statut"),
    job_offer_id: Optional[str] = Query(None, description="Filtrer par offre d'emploi"),
    candidate_id: Optional[str] = Query(None, description="Filtrer par candidat"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    RÃ©cupÃ©rer la liste des candidatures avec filtres
    
    - **skip**: Nombre d'Ã©lÃ©ments Ã  ignorer (pagination)
    - **limit**: Nombre d'Ã©lÃ©ments Ã  retourner (max 1000)
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
        
        safe_log("info", "Liste candidatures récupérée", count=len(applications), requester_id=str(current_user.id))
        return ApplicationListResponse(
            success=True,
            message=f"{len(applications)} candidature(s) trouvée(s)",
            data=convert_orm_list_to_schema(applications, Application),  # type: ignore
            total=total,
            page=(skip // limit) + 1,
            per_page=limit
        )
        
    except Exception as e:
        safe_log("error", "Erreur rÃ©cupÃ©ration liste candidatures", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.get("/{application_id}", response_model=ApplicationResponse, summary="RÃ©cupÃ©rer une candidature par ID", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Candidature rÃ©cupÃ©rÃ©e avec succÃ¨s", "data": {"id": "uuid"}}}}}, "404": {"description": "Candidature non trouvÃ©e"}}
})
async def get_application(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer une candidature par son ID avec toutes les relations
    (candidat, profil candidat, offre d'emploi, documents, historique, entretiens)
    """
    try:
        safe_log("info", "🔍 RECHERCHE candidature",
                 application_id=application_id,
                 user_id=str(current_user.id),
                 user_role=current_user.role)
        
        application_service = ApplicationService(db)
        # Utiliser get_application_with_relations pour charger toutes les relations
        application = await application_service.get_application_with_relations(application_id)
        
        if not application:
            safe_log("warning", "❌ CANDIDATURE INTROUVABLE",
                     application_id=application_id,
                     user_id=str(current_user.id))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidature non trouvée")
        
        # Forcer le chargement explicite des relations pour les admins/recruteurs
        if current_user.role in ["admin", "recruiter"]:
            safe_log("debug", "🔄 Refresh avec relations explicites...")
            await db.refresh(application, ["candidate", "job_offer"])
            safe_log("debug", "✅ Relations refreshées")
        
        safe_log("info", "✅ SUCCÈS récupération candidature",
                 application_id=application_id,
                 requester_id=str(current_user.id),
                 candidate_id=str(application.candidate_id),
                 job_offer_id=str(application.job_offer_id),
                 status=application.status)
        
        # Utiliser la fonction utilitaire pour sérialiser avec relations
        # (uniquement pour admins et recruteurs)
        safe_log("debug", "🎯 Point de décision sérialisation",
                user_role=current_user.role,
                is_admin_or_recruiter=current_user.role in ["admin", "recruiter"])
        
        if current_user.role in ["admin", "recruiter"]:
            safe_log("info", "🔥 ENTRÉE dans le bloc admin/recruiter - appel serializer")
            from app.utils.application_serializer import serialize_application_with_relations
            
            app_dict = serialize_application_with_relations(
                application,
                include_candidate=True,
                include_job_offer=True
            )
            safe_log("info", "🔥 Serializer terminé - vérification clés",
                    has_candidate_key='candidate' in app_dict,
                    has_job_offer_key='job_offer' in app_dict,
                    keys=list(app_dict.keys())[:10])
        else:
            # Pour les candidats, ne pas inclure les relations (juste leurs propres données)
            app_schema = convert_orm_to_schema(application, Application)
            app_dict = app_schema.model_dump()
        
        return ApplicationResponse(
            success=True,
            message="Candidature récupérée avec succès",
            data=app_dict  # type: ignore
        )
        
    except NotFoundError as e:
        safe_log("warning", "❌ NOT FOUND - Récupération candidature",
                 application_id=application_id,
                 user_id=str(current_user.id),
                 error=str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        safe_log("error", "🔥 ERREUR CRITIQUE - Récupération candidature",
                 application_id=application_id,
                 user_id=str(current_user.id),
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
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
            user_id=str(current_user.id)
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
        candidate_id_val = getattr(application, 'candidate_id', None)
        is_candidate = bool(current_user.role == "candidate")
        is_not_owner = bool(str(candidate_id_val) != str(current_user.id))
        if is_candidate and is_not_owner:
            safe_log(
                "warning",
                "🚫 Accès non autorisé",
                application_id=application_id,
                user_id=str(current_user.id)
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
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Candidature mise à  jour avec succÃ¨s", "data": {"id": "uuid", "status": "reviewed"}}}}}}
})
async def update_application(
    application_id: str,
    application_data: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mettre à jour une candidature
    """
    try:
        # 🔷 ÉTAPE 1: Initialisation
        safe_log("info", "🚀 DÉBUT mise à jour candidature",
                 application_id=application_id,
                 user_id=str(current_user.id),
                 user_role=current_user.role,
                 fields_to_update=list(application_data.dict(exclude_unset=True).keys()))
        
        application_service = ApplicationService(db)
        
        # 🔷 ÉTAPE 2: Mise à jour
        safe_log("debug", "📝 Application de la mise à jour...")
        application = await application_service.update_application(application_id, application_data)
        safe_log("info", "✅ Mise à jour appliquée en mémoire")
        
        # 🔷 ÉTAPE 3: Persistence
        safe_log("debug", "💾 Flush en base...")
        await db.flush()
        await db.refresh(application)
        safe_log("debug", "✅ Objet flushé et rafraîchi")
        
        safe_log("debug", "💾 Commit transaction en cours...")
        await db.commit()
        safe_log("info", "✅ Transaction committée avec succès")
        
        safe_log("info", "🎉 SUCCÈS mise à jour candidature", 
                 application_id=application_id,
                 requester_id=str(current_user.id),
                 new_status=application.status)
        
        return ApplicationResponse(
            success=True,
            message="Candidature mise à jour avec succès",
            data=convert_orm_to_schema(application, Application)  # type: ignore
        )
        
    except NotFoundError as e:
        safe_log("warning", "❌ CANDIDATURE NON TROUVÉE - Mise à jour",
                 application_id=application_id,
                 user_id=str(current_user.id),
                 error=str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        safe_log("warning", "❌ VALIDATION ÉCHOUÉE - Mise à jour candidature",
                 application_id=application_id,
                 user_id=str(current_user.id),
                 error=str(e),
                 fields=list(application_data.dict(exclude_unset=True).keys()))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        safe_log("error", "🔥 ERREUR CRITIQUE - Mise à jour candidature",
                 application_id=application_id,
                 user_id=str(current_user.id),
                 error=str(e),
                 error_type=type(e).__name__,
                 traceback=error_traceback)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer une candidature", openapi_extra={
    "responses": {"204": {"description": "SupprimÃ©"}, "404": {"description": "Candidature non trouvÃ©e"}}
})
async def delete_application(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Supprimer une candidature
    """
    try:
        application_service = ApplicationService(db)
        await application_service.delete_application(application_id)
        safe_log("info", "Candidature supprimÃ©e", application_id=application_id, requester_id=str(current_user.id))
        
    except NotFoundError as e:
        safe_log("warning", "Candidature non trouvÃ©e pour suppression", application_id=application_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur suppression candidature", application_id=application_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


# Endpoints pour les documents PDF (lecture seule)
@router.get("/{application_id}/documents", response_model=ApplicationDocumentListResponse, summary="Lister les documents d'une candidature", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "0 document(s) trouvÃ©(s)", "data": [], "total": 0}}}}}
})
async def get_application_documents(
    application_id: str,
    document_type: Optional[str] = Query(None, description="Filtrer par type de document"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    RÃ©cupÃ©rer les documents d'une candidature
    
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
        safe_log("warning", "Candidature non trouvÃ©e pour liste documents", application_id=application_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur rÃ©cupÃ©ration documents", application_id=application_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.get("/{application_id}/documents/{document_id}", response_model=ApplicationDocumentWithDataResponse, summary="RÃ©cupÃ©rer un document avec donnÃ©es", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Document rÃ©cupÃ©rÃ© avec succÃ¨s", "data": {"id": "uuid", "file_data": "JVBERi0..."}}}}}, "404": {"description": "Document non trouvÃ©"}}
})
async def get_document_with_data(
    application_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    RÃ©cupÃ©rer un document avec ses donnÃ©es binaires
    
    - **application_id**: ID de la candidature
    - **document_id**: ID du document
    """
    try:
        application_service = ApplicationService(db)
        document = await application_service.get_document_with_data(application_id, document_id)
        
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document non trouvÃ©")
        
        return ApplicationDocumentWithDataResponse(
            success=True,
            message="Document rÃ©cupÃ©rÃ© avec succÃ¨s",
            data=document
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.get("/{application_id}/documents/{document_id}/download", summary="TÃ©lÃ©charger un document PDF", openapi_extra={
    "responses": {"200": {"description": "Flux binaire PDF"}, "404": {"description": "Document non trouvÃ©"}}
})
async def download_document(
    application_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    TÃ©lÃ©charger le document au format binaire (application/pdf) directement.
    """
    try:
        application_service = ApplicationService(db)
        document = await application_service.get_document_with_data(application_id, document_id)
        if not document or not document.file_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document non trouvÃ© ou sans donnÃ©es")
        try:
            binary = base64.b64decode(document.file_data)
        except Exception:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="DonnÃ©es de document invalides")
        file_name = document.file_name or f"document_{document_id}.pdf"
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
    "responses": {"204": {"description": "SupprimÃ©"}, "404": {"description": "Document non trouvÃ©"}}
})
async def delete_document(
    application_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Supprimer un document d'une candidature
    
    - **application_id**: ID de la candidature
    - **document_id**: ID du document
    """
    try:
        application_service = ApplicationService(db)
        await application_service.delete_document(application_id, document_id)
        safe_log("info", "Document supprimÃ©", application_id=application_id, document_id=document_id, user_id=str(current_user.id))
        
    except NotFoundError as e:
        safe_log("warning", "Document non trouvÃ© pour suppression", application_id=application_id, document_id=document_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur suppression document", application_id=application_id, document_id=document_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


# Endpoints pour les statistiques
@router.get("/stats/overview", response_model=dict, summary="Statistiques globales des candidatures", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Statistiques rÃ©cupÃ©rÃ©es avec succÃ¨s", "data": {}}}}}}
})
async def get_application_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    RÃ©cupÃ©rer les statistiques des candidatures
    """
    try:
        application_service = ApplicationService(db)
        stats = await application_service.get_application_stats()
        
        return {
            "success": True,
            "message": "Statistiques rÃ©cupÃ©rÃ©es avec succÃ¨s",
            "data": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


# ---- Drafts de candidature ----
@router.get("/{application_id}/draft", response_model=dict, summary="RÃ©cupÃ©rer le brouillon de candidature", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "data": {"form_data": {}}}}}}}
})
async def get_application_draft(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        service = ApplicationService(db)
        draft = await service.get_application_draft(application_id, str(current_user.id))
        return {"success": True, "data": draft}
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.post("/{application_id}/draft", response_model=dict, summary="Enregistrer le brouillon de candidature", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"form_data": {"step": 1}}}}},
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Brouillon enregistrÃ©", "data": {}}}}}}
})
async def upsert_application_draft(
    application_id: str,
    draft_data: ApplicationDraftUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        service = ApplicationService(db)
        draft = await service.upsert_application_draft(application_id, str(current_user.id), draft_data)
        return {"success": True, "message": "Brouillon enregistrÃ©", "data": draft}
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.delete("/{application_id}/draft", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer le brouillon de candidature", openapi_extra={
    "responses": {"204": {"description": "SupprimÃ©"}}
})
async def delete_application_draft(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        service = ApplicationService(db)
        await service.delete_application_draft(application_id, str(current_user.id))
        return None
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


# ---- Historique des statuts ----
@router.get("/{application_id}/history", response_model=dict, summary="Lister l'historique de la candidature", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "data": []}}}}}
})
async def list_application_history(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        service = ApplicationService(db)
        history = await service.list_application_history(application_id)
        return {"success": True, "data": history}
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.post("/{application_id}/history", response_model=dict, summary="Ajouter un Ã©vÃ¨nement d'historique", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"new_status": "reviewed", "notes": "Validation des piÃ¨ces"}}}},
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Historique ajoutÃ©", "data": {"id": "uuid"}}}}}}
})
async def add_application_history(
    application_id: str,
    item: ApplicationHistoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        service = ApplicationService(db)
        created = await service.add_application_history(application_id, item, str(current_user.id))
        return {"success": True, "message": "Historique ajoutÃ©", "data": created}
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


# ---- Statistiques avancÃ©es ----
@router.get("/stats/advanced", response_model=dict, summary="Statistiques avancÃ©es des candidatures", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "data": {"total_applications": 0}}}}}}
})
async def get_advanced_application_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        service = ApplicationService(db)
        stats = await service.get_advanced_statistics()
        return {"success": True, "data": stats}
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


# ---- Export PDF de candidature ----
@router.get("/{application_id}/export/pdf", summary="TÃ©lÃ©charger le PDF complet de la candidature", openapi_extra={
    "parameters": [
        {"in": "path", "name": "application_id", "required": True, "schema": {"type": "string", "format": "uuid"}},
        {"in": "query", "name": "include_documents", "required": False, "schema": {"type": "boolean", "default": False}},
        {"in": "query", "name": "format", "required": False, "schema": {"type": "string", "enum": ["A4", "Letter"], "default": "A4"}},
        {"in": "query", "name": "language", "required": False, "schema": {"type": "string", "enum": ["fr", "en"], "default": "fr"}}
    ],
    "responses": {
        "200": {"description": "PDF gÃ©nÃ©rÃ© avec succÃ¨s", "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}}},
        "403": {"description": "AccÃ¨s non autorisÃ©"},
        "404": {"description": "Candidature non trouvÃ©e"}
    }
})
async def export_application_pdf(
    application_id: str,
    include_documents: bool = Query(False, description="Inclure les documents joints (non implÃ©mentÃ© dans cette version)"),
    format: str = Query("A4", description="Format du PDF (A4 ou Letter)"),
    language: str = Query("fr", description="Langue du PDF (fr ou en)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    GÃ©nÃ¨re et tÃ©lÃ©charge un PDF complet de la candidature
    
    Contient:
    - Informations personnelles du candidat
    - DÃ©tails du poste visÃ©
    - Parcours professionnel
    - Formation
    - CompÃ©tences
    - RÃ©ponses MTP (MÃ©tier, Talent, Paradigme)
    - Motivation & DisponibilitÃ©
    - Documents joints (liste)
    - Entretien programmÃ© (si applicable)
    
    Permissions:
    - Candidat: Seulement ses propres candidatures
    - Recruteur: Candidatures de ses offres
    - Admin/Observer: Toutes les candidatures
    """
    try:
        safe_log("info", "🚀 Début export PDF", application_id=application_id, user_id=str(current_user.id))
        
        # 1. RÃ©cupÃ©rer la candidature avec toutes les relations
        safe_log("info", "🔍 Récupération candidature avec relations", application_id=application_id)
        application_service = ApplicationService(db)
        application = await application_service.get_application_with_relations(application_id)
        
        if not application:
            safe_log("warning", "❌ Candidature non trouvée", application_id=application_id)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidature non trouvÃ©e")
        
        safe_log("info", "✅ Candidature récupérée", application_id=application_id, candidate_id=str(getattr(application, 'candidate_id', 'N/A')))
        
        # 2. Vérifier les permissions
        is_admin = hasattr(current_user, 'role') and str(current_user.role) in ['admin', 'observer']
        is_recruiter = hasattr(current_user, 'role') and str(current_user.role) == 'recruiter'
        is_candidate = str(application.candidate_id) == str(current_user.id)

        # Recruteur: vérifier que c'est son offre (relation singulière job_offer)
        if is_recruiter and getattr(application, 'job_offer', None):
            recruiter_id = getattr(application.job_offer, 'recruiter_id', None)
            if recruiter_id is not None:
                if str(recruiter_id) != str(current_user.id):
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
        
        # 3. GÃ©nÃ©rer le PDF
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
        safe_log("warning", "Candidature non trouvÃ©e pour export PDF", application_id=application_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur gÃ©nÃ©ration PDF", application_id=application_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la gÃ©nÃ©ration du PDF: {str(e)}"
        )


# ---- Drafts globaux par offre (job_offer_id) ----
@router.get("/drafts/by-offer", response_model=dict, summary="RÃ©cupÃ©rer le brouillon par offre", openapi_extra={
    "parameters": [
        {"in": "query", "name": "job_offer_id", "required": True, "schema": {"type": "string", "format": "uuid"}}
    ],
    "responses": {
        "200": {"content": {"application/json": {"example": {"success": True, "data": {"form_data": {"step": 1}, "ui_state": {}}}}}},
        "404": {"description": "Aucun brouillon trouvÃ©"}
    }
})
async def get_draft_by_job_offer(
    job_offer_id: str = Query(..., description="ID de l'offre d'emploi"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        safe_log("debug", "🔍 GET draft démarré", user_id=str(current_user.id), job_offer_id=job_offer_id)
        service = ApplicationService(db)
        draft = await service.get_draft(user_id=str(current_user.id), job_offer_id=job_offer_id)
        
        if not draft:
            safe_log("debug", "✅ Aucun brouillon trouvé", user_id=str(current_user.id), job_offer_id=job_offer_id)
            return {"success": True, "data": None}
        
        safe_log("debug", "📦 Brouillon trouvé, conversion en dict...", user_id=str(current_user.id), job_offer_id=job_offer_id)
        
        # Convertir l'objet ORM en dictionnaire de manière sécurisée
        # Utiliser getattr pour éviter les problèmes avec les colonnes SQLAlchemy
        try:
            created_at_val = getattr(draft, 'created_at', None)
            updated_at_val = getattr(draft, 'updated_at', None)
            form_data_val = getattr(draft, 'form_data', None)
            ui_state_val = getattr(draft, 'ui_state', None)
            
            draft_data = {
                "user_id": str(draft.user_id),
                "job_offer_id": str(draft.job_offer_id),
                "form_data": form_data_val if form_data_val is not None else {},
                "ui_state": ui_state_val if ui_state_val is not None else {},
                "created_at": created_at_val.isoformat() if created_at_val is not None else None,
                "updated_at": updated_at_val.isoformat() if updated_at_val is not None else None,
            }
            
            safe_log("info", "✅ Brouillon converti avec succès", user_id=str(current_user.id), job_offer_id=job_offer_id)
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
                user_id=str(current_user.id), 
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Créer ou mettre à jour un brouillon de candidature
    
    Gestion d'erreurs robuste selon les meilleures pratiques :
    - Validation des données
    - Transaction avec commit/rollback approprié
    - Logging structuré pour traçabilité
    - Exceptions spécifiques selon le type d'erreur
    """
    # Récupérer l'ID utilisateur de manière sécurisée (éviter MissingGreenlet)
    user_id = str(getattr(current_user, 'id', None))
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
        
        # Flush pour forcer l'écriture en base et obtenir les valeurs par défaut
        safe_log("debug", "💾 Flush en base...")
        await db.flush()
        await db.refresh(draft)  # Rafraîchir pour obtenir les valeurs par défaut (created_at, updated_at)
        safe_log("debug", "✅ Brouillon flushé et rafraîchi")
        
        # Commit explicite pour persister les données (principe de transaction explicite)
        await db.commit()
        safe_log("info", "✅ Brouillon sauvegardé et commité", 
                user_id=user_id, 
                job_offer_id=job_offer_id_str)
        
        # Créer une notification brouillon (pas d'email nécessaire)
        try:
            from uuid import UUID as UUID_Type
            from app.services.notification_email_manager import NotificationEmailManager
            from sqlalchemy import select
            from app.models.job_offer import JobOffer
            
            # Récupérer le titre de l'offre
            stmt = select(JobOffer).where(JobOffer.id == payload.job_offer_id)
            result = await db.execute(stmt)
            job_offer = result.scalar_one_or_none()
            
            if job_offer:
                notif_email_manager = NotificationEmailManager(db)
                
                # Convertir les types pour éviter les erreurs de type checking
                user_id_uuid = current_user.id if isinstance(current_user.id, UUID_Type) else UUID_Type(str(current_user.id))
                job_offer_id_uuid = payload.job_offer_id if isinstance(payload.job_offer_id, UUID_Type) else UUID_Type(str(payload.job_offer_id))
                
                result = await notif_email_manager.notify_application_draft_saved(
                    user_id=user_id_uuid,
                    job_offer_id=job_offer_id_uuid,
                    job_title=str(job_offer.title)
                )
                await db.commit()
                safe_log("debug", "✅ Notification brouillon créée", 
                        notification_sent=result["notification_sent"])
        except Exception as e:
            safe_log("warning", "⚠️ Erreur notification brouillon", error=str(e))
        
        # Convertir l'objet ORM en dictionnaire pour la réponse
        draft_data = {
            "user_id": str(draft.user_id),
            "job_offer_id": str(draft.job_offer_id),
            "form_data": draft.form_data,
            "ui_state": draft.ui_state,
            "created_at": draft.created_at.isoformat() if draft.created_at is not None else None,
            "updated_at": draft.updated_at.isoformat() if draft.updated_at is not None else None,
        }
        
        return {
            "success": True, 
            "message": "Brouillon enregistré avec succès", 
            "data": draft_data
        }
        
    except ValidationError as e:
        # Erreur de validation : rollback et retourner 400
        await db.rollback()
        safe_log("warning", "⚠️ Validation échouée sauvegarde brouillon", 
                user_id=user_id, 
                error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
        
    except DatabaseError as e:
        # Erreur de base de données : rollback et retourner 500
        await db.rollback()
        safe_log("error", "❌ Erreur BD sauvegarde brouillon", 
                user_id=user_id, 
                error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la sauvegarde du brouillon"
        )
        
    except Exception as e:
        # Erreur inattendue : rollback et retourner 500
        await db.rollback()
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
    "responses": {"204": {"description": "SupprimÃ©"}}
})
async def delete_draft_by_job_offer(
    job_offer_id: str = Query(..., description="ID de l'offre d'emploi"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        service = ApplicationService(db)
        await service.delete_draft(user_id=str(current_user.id), job_offer_id=job_offer_id)
        return None
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")
