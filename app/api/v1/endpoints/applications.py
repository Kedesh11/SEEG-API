"""
Endpoints pour la gestion des candidatures
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
import base64
import uuid
import structlog
from fastapi.responses import StreamingResponse

logger = structlog.get_logger(__name__)

from app.db.session import get_async_session as get_async_db
from app.services.application import ApplicationService
from app.services.file import FileService
from app.services.email import EmailService
from app.services.pdf import ApplicationPDFService
from app.schemas.application import (
    ApplicationCreate, ApplicationUpdate, ApplicationResponse, ApplicationListResponse,
    ApplicationDocumentResponse, ApplicationDocumentCreate, ApplicationDocumentUpdate,
    ApplicationDocumentWithDataResponse, ApplicationDocumentListResponse,
    FileUploadRequest, MultipleFileUploadRequest,
    ApplicationDraftCreate, ApplicationDraftUpdate, ApplicationDraft, ApplicationDraftInDB,
    ApplicationHistoryCreate, ApplicationHistory, ApplicationHistoryInDB
)
from app.core.dependencies import get_current_user
from app.models.user import User
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError, FileError
from app.core.rate_limit import limiter, UPLOAD_LIMITS

router = APIRouter()


@router.post("/", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED, summary="Créer une candidature", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {
        "candidate_id": "00000000-0000-0000-0000-000000000001",
        "job_offer_id": "00000000-0000-0000-0000-0000000000AA",
        "reference_contacts": "Mme X (+241...), M. Y (+241...)"
    }}}},
    "responses": {"201": {"content": {"application/json": {"example": {"success": True, "message": "Candidature créée avec succès", "data": {"id": "uuid"}}}}}}
})
async def create_application(
    application_data: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Créer une nouvelle candidature
    
    - **candidate_id**: ID du candidat
    - **job_offer_id**: ID de l'offre d'emploi
    - **reference_contacts**: Contacts de référence (optionnel)
    - **availability_start**: Date de disponibilité (optionnel)
    - **mtp_answers**: Réponses MTP (optionnel)
    """
    try:
        application_service = ApplicationService(db)
        email_service = EmailService(db)
        
        # Création de la candidature
        application = await application_service.create_application(
            application_data, str(current_user.id)
        )
        
        # Envoi d'email de confirmation (en arrière-plan)
        try:
            await email_service.send_application_confirmation(
                application.candidate.email,
                application.job_offer.title
            )
        except Exception as e:
            # Log l'erreur mais ne fait pas échouer la création
            print(f"Erreur envoi email: {e}")
        
        return ApplicationResponse(
            success=True,
            message="Candidature créée avec succès",
            data=application
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.get("/", response_model=ApplicationListResponse, summary="Lister les candidatures (filtres/pagination)", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {
        "success": True,
        "message": "0 candidature(s) trouvée(s)",
        "data": [],
        "total": 0,
        "page": 1,
        "per_page": 100
    }}}}}
})
async def get_applications(
    skip: int = Query(0, ge=0, description="Nombre d'éléments à ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre d'éléments à retourner"),
    status_filter: Optional[str] = Query(None, description="Filtrer par statut"),
    job_offer_id: Optional[str] = Query(None, description="Filtrer par offre d'emploi"),
    candidate_id: Optional[str] = Query(None, description="Filtrer par candidat"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
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
        
        return ApplicationListResponse(
            success=True,
            message=f"{len(applications)} candidature(s) trouvée(s)",
            data=applications,
            total=total,
            page=(skip // limit) + 1,
            per_page=limit
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.get("/{application_id}", response_model=ApplicationResponse, summary="Récupérer une candidature par ID", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Candidature récupérée avec succès", "data": {"id": "uuid"}}}}}, "404": {"description": "Candidature non trouvée"}}
})
async def get_application(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer une candidature par son ID
    """
    try:
        application_service = ApplicationService(db)
        application = await application_service.get_application_by_id(application_id)
        
        if not application:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidature non trouvée")
        
        return ApplicationResponse(
            success=True,
            message="Candidature récupérée avec succès",
            data=application
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.put("/{application_id}", response_model=ApplicationResponse, summary="Mettre à jour une candidature", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"status": "reviewed"}}}},
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Candidature mise à jour avec succès", "data": {"id": "uuid", "status": "reviewed"}}}}}}
})
async def update_application(
    application_id: str,
    application_data: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Mettre à jour une candidature
    """
    try:
        application_service = ApplicationService(db)
        application = await application_service.update_application(application_id, application_data)
        
        return ApplicationResponse(
            success=True,
            message="Candidature mise à jour avec succès",
            data=application
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer une candidature", openapi_extra={
    "responses": {"204": {"description": "Supprimé"}, "404": {"description": "Candidature non trouvée"}}
})
async def delete_application(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Supprimer une candidature
    """
    try:
        application_service = ApplicationService(db)
        await application_service.delete_application(application_id)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


# Endpoints pour les documents PDF
@router.post("/{application_id}/documents", response_model=ApplicationDocumentResponse, status_code=status.HTTP_201_CREATED, summary="Uploader un document PDF", openapi_extra={
    "requestBody": {"content": {"multipart/form-data": {"schema": {"type": "object", "properties": {"document_type": {"type": "string"}, "file": {"type": "string", "format": "binary"}}}, "example": {"document_type": "cv"}}}},
    "responses": {
        "201": {"content": {"application/json": {"example": {"success": True, "message": "Document uploadé avec succès", "data": {"id": "uuid", "file_name": "cv.pdf"}}}}},
        "429": {"description": "Trop d'uploads"}
    }
})
@limiter.limit(UPLOAD_LIMITS)
async def upload_document(
    request: Request,
    application_id: str,
    document_type: Optional[str] = Form(None, description="Type de document: cover_letter, cv, certificats, diplome (optionnel)"),
    file: UploadFile = File(..., description="Fichier PDF à uploader"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Uploader un document PDF pour une candidature
    
    - **application_id**: ID de la candidature
    - **document_type**: Type de document (cover_letter, cv, certificats, diplome) - optionnel
    - **file**: Fichier PDF à uploader (max 10MB)
    """
    try:
        # Vérifier que le fichier est un PDF
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seuls les fichiers PDF sont acceptés"
            )
        
        # Lire le contenu du fichier
        file_content = await file.read()
        
        # Validation de la taille (10MB max)
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Le fichier est trop volumineux. Taille maximale: 10MB. Taille actuelle: {len(file_content) / (1024 * 1024):.2f}MB"
            )
        
        # Vérifier que c'est bien un PDF (magic number)
        if not file_content.startswith(b'%PDF'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le fichier n'est pas un PDF valide"
            )
        
        # Encoder en base64
        file_data_b64 = base64.b64encode(file_content).decode('utf-8')
        
        # Valeur par défaut si non fourni
        resolved_type = (document_type or 'certificats')
        
        # Créer le document
        document_data = ApplicationDocumentCreate(
            application_id=uuid.UUID(application_id),
            document_type=resolved_type,
            file_name=file.filename if file.filename.lower().endswith('.pdf') else f"{file.filename}.pdf",
            file_data=file_data_b64,
            file_size=len(file_content),
            file_type="application/pdf"
        )
        
        application_service = ApplicationService(db)
        document = await application_service.create_document(document_data)
        
        return ApplicationDocumentResponse(
            success=True,
            message="Document uploadé avec succès",
            data=document
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.post("/{application_id}/documents/multiple", response_model=ApplicationDocumentListResponse, status_code=status.HTTP_201_CREATED, summary="Uploader plusieurs documents PDF", openapi_extra={
    "requestBody": {"content": {"multipart/form-data": {"schema": {"type": "object", "properties": {"document_types": {"type": "array", "items": {"type": "string"}}, "files": {"type": "array", "items": {"type": "string", "format": "binary"}}}}, "example": {"document_types": ["cv", "certificats"]}}}},
    "responses": {
        "201": {"content": {"application/json": {"example": {"success": True, "message": "2 document(s) uploadé(s) avec succès", "data": [{"id": "uuid"}], "total": 2}}}},
        "429": {"description": "Trop d'uploads"}
    }
})
@limiter.limit(UPLOAD_LIMITS)
async def upload_multiple_documents(
    request: Request,
    application_id: str,
    files: List[UploadFile] = File(..., description="Fichiers PDF à uploader"),
    document_types: List[str] = Form(..., description="Types de documents correspondants"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Uploader plusieurs documents PDF pour une candidature
    
    - **application_id**: ID de la candidature
    - **files**: Liste des fichiers PDF à uploader (max 10MB chacun)
    - **document_types**: Liste des types de documents correspondants
    """
    try:
        if len(files) != len(document_types):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le nombre de fichiers doit correspondre au nombre de types de documents"
            )
        
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
        application_service = ApplicationService(db)
        documents = []
        
        for file, doc_type in zip(files, document_types):
            # Vérifier que le fichier est un PDF
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Seuls les fichiers PDF sont acceptés. Fichier invalide: {file.filename}"
                )
            
            # Lire le contenu du fichier
            file_content = await file.read()
            
            # Validation de la taille
            if len(file_content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Le fichier '{file.filename}' est trop volumineux. Taille maximale: 10MB. Taille actuelle: {len(file_content) / (1024 * 1024):.2f}MB"
                )
            
            # Vérifier que c'est bien un PDF
            if not file_content.startswith(b'%PDF'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Le fichier n'est pas un PDF valide: {file.filename}"
                )
            
            # Encoder en base64
            file_data_b64 = base64.b64encode(file_content).decode('utf-8')
            
            # Créer le document
            document_data = ApplicationDocumentCreate(
                application_id=uuid.UUID(application_id),
                document_type=doc_type,
                file_name=file.filename,
                file_data=file_data_b64,
                file_size=len(file_content),
                file_type="application/pdf"
            )
            
            document = await application_service.create_document(document_data)
            documents.append(document)
        
        return ApplicationDocumentListResponse(
            success=True,
            message=f"{len(documents)} document(s) uploadé(s) avec succès",
            data=documents,
            total=len(documents)
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.get("/{application_id}/documents", response_model=ApplicationDocumentListResponse, summary="Lister les documents d'une candidature", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "0 document(s) trouvé(s)", "data": [], "total": 0}}}}}
})
async def get_application_documents(
    application_id: str,
    document_type: Optional[str] = Query(None, description="Filtrer par type de document"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer les documents d'une candidature
    
    - **application_id**: ID de la candidature
    - **document_type**: Filtrer par type de document (optionnel)
    """
    try:
        application_service = ApplicationService(db)
        documents = await application_service.get_application_documents(application_id, document_type)
        
        return ApplicationDocumentListResponse(
            success=True,
            message=f"{len(documents)} document(s) trouvé(s)",
            data=documents,
            total=len(documents)
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.get("/{application_id}/documents/{document_id}", response_model=ApplicationDocumentWithDataResponse, summary="Récupérer un document avec données", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Document récupéré avec succès", "data": {"id": "uuid", "file_data": "JVBERi0..."}}}}}, "404": {"description": "Document non trouvé"}}
})
async def get_document_with_data(
    application_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Télécharger le document au format binaire (application/pdf) directement.
    """
    try:
        application_service = ApplicationService(db)
        document = await application_service.get_document_with_data(application_id, document_id)
        if not document or not document.file_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document non trouvé ou sans données")
        try:
            binary = base64.b64decode(document.file_data)
        except Exception:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Données de document invalides")
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
    "responses": {"204": {"description": "Supprimé"}, "404": {"description": "Document non trouvé"}}
})
async def delete_document(
    application_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Supprimer un document d'une candidature
    
    - **application_id**: ID de la candidature
    - **document_id**: ID du document
    """
    try:
        application_service = ApplicationService(db)
        await application_service.delete_document(application_id, document_id)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


# Endpoints pour les statistiques
@router.get("/stats/overview", response_model=dict, summary="Statistiques globales des candidatures", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Statistiques récupérées avec succès", "data": {}}}}}}
})
async def get_application_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        service = ApplicationService(db)
        draft = await service.get_application_draft(application_id, str(current_user.id))
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        service = ApplicationService(db)
        draft = await service.upsert_application_draft(application_id, str(current_user.id), draft_data)
        return {"success": True, "message": "Brouillon enregistré", "data": draft}
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.delete("/{application_id}/draft", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer le brouillon de candidature", openapi_extra={
    "responses": {"204": {"description": "Supprimé"}}
})
async def delete_application_draft(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
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
    db: AsyncSession = Depends(get_async_db)
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        service = ApplicationService(db)
        created = await service.add_application_history(application_id, item, str(current_user.id))
        return {"success": True, "message": "Historique ajouté", "data": created}
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


# ---- Statistiques avancées ----
@router.get("/stats/advanced", response_model=dict, summary="Statistiques avancées des candidatures", openapi_extra={
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "data": {"total_applications": 0}}}}}}
})
async def get_advanced_application_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
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
        # 1. Récupérer la candidature avec toutes les relations
        application_service = ApplicationService(db)
        application = await application_service.get_application_with_relations(application_id)
        
        if not application:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidature non trouvée")
        
        # 2. Vérifier les permissions
        is_admin = hasattr(current_user, 'role') and current_user.role in ['admin', 'observer']
        is_recruiter = hasattr(current_user, 'role') and current_user.role == 'recruiter'
        is_candidate = str(application.candidate_id) == str(current_user.id)

        # Recruteur: vérifier que c'est son offre (relation singulière job_offer)
        if is_recruiter and getattr(application, 'job_offer', None):
            if getattr(application.job_offer, 'recruiter_id', None) is not None:
                if str(application.job_offer.recruiter_id) != str(current_user.id):
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
        pdf_service = ApplicationPDFService(page_format=format, language=language)
        pdf_content = await pdf_service.generate_application_pdf(
            application=application,
            include_documents=include_documents
        )
        
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Erreur génération PDF", application_id=application_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la génération du PDF: {str(e)}"
        )


# ---- Drafts globaux par offre (job_offer_id) ----
@router.get("/drafts", response_model=dict, summary="Récupérer le brouillon par offre", openapi_extra={
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        service = ApplicationService(db)
        draft = await service.get_draft(user_id=str(current_user.id), job_offer_id=job_offer_id)
        if not draft:
            return {"success": True, "data": None}
        return {"success": True, "data": draft}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.post("/drafts", response_model=dict, summary="Créer/Maj le brouillon par offre", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {
        "job_offer_id": "00000000-0000-0000-0000-0000000000AA",
        "form_data": {"step": 1, "values": {"firstname": "Ada"}},
        "ui_state": {"currentStep": 2}
    }}}},
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Brouillon enregistré", "data": {}}}}}}
})
async def upsert_draft_by_job_offer(
    payload: ApplicationDraftCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        service = ApplicationService(db)
        # Forcer l'user_id depuis le token, ignorer celui reçu pour sécurité
        data = {
            "user_id": str(current_user.id),
            "job_offer_id": str(payload.job_offer_id),
            "form_data": payload.form_data,
            "ui_state": payload.ui_state,
        }
        draft = await service.save_draft(data)
        return {"success": True, "message": "Brouillon enregistré", "data": draft}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.delete("/drafts", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer le brouillon par offre", openapi_extra={
    "parameters": [
        {"in": "query", "name": "job_offer_id", "required": True, "schema": {"type": "string", "format": "uuid"}}
    ],
    "responses": {"204": {"description": "Supprimé"}}
})
async def delete_draft_by_job_offer(
    job_offer_id: str = Query(..., description="ID de l'offre d'emploi"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        service = ApplicationService(db)
        await service.delete_draft(user_id=str(current_user.id), job_offer_id=job_offer_id)
        return None
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")
