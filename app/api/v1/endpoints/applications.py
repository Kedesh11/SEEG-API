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

from app.db.database import get_db
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


def safe_log(level: str, message: str, **kwargs):
    """Log avec gestion d'erreur pour Ã©viter les problÃ¨mes de handler."""
    try:
        getattr(logger, level)(message, **kwargs)
    except (TypeError, AttributeError):
        print(f"{level.upper()}: {message} - {kwargs}")


@router.post("/", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED, summary="CrÃ©er une candidature", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {
        "candidate_id": "00000000-0000-0000-0000-000000000001",
        "job_offer_id": "00000000-0000-0000-0000-0000000000AA",
        "reference_contacts": "Mme X (+241...), M. Y (+241...)"
    }}}},
    "responses": {"201": {"content": {"application/json": {"example": {"success": True, "message": "Candidature crÃ©Ã©e avec succÃ¨s", "data": {"id": "uuid"}}}}}}
})
async def create_application(
    application_data: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    CrÃ©er une nouvelle candidature
    
    - **candidate_id**: ID du candidat
    - **job_offer_id**: ID de l'offre d'emploi
    - **reference_contacts**: Contacts de rÃ©fÃ©rence (optionnel)
    - **availability_start**: Date de disponibilitÃ© (optionnel)
    - **mtp_answers**: RÃ©ponses MTP (optionnel)
    """
    try:
        application_service = ApplicationService(db)
        email_service = EmailService(db)
        
        # CrÃ©ation de la candidature
        application = await application_service.create_application(
            application_data, str(current_user.id)
        )
        
        # Envoi d'email de confirmation (en arriÃ¨re-plan)
        try:
            await email_service.send_application_confirmation(
                application.candidate.email,
                application.job_offer.title
            )
        except Exception as e:
            # Log l'erreur mais ne fait pas Ã©chouer la crÃ©ation
            safe_log("warning", "Erreur envoi email confirmation", error=str(e), application_id=str(application.id))
        
        safe_log("info", "Candidature crÃ©Ã©e", application_id=str(application.id), candidate_id=str(current_user.id))
        return ApplicationResponse(
            success=True,
            message="Candidature crÃ©Ã©e avec succÃ¨s",
            data=application
        )
        
    except ValidationError as e:
        safe_log("warning", "Erreur validation crÃ©ation candidature", error=str(e), user_id=str(current_user.id))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except BusinessLogicError as e:
        safe_log("warning", "Erreur logique mÃ©tier crÃ©ation candidature", error=str(e), user_id=str(current_user.id))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur crÃ©ation candidature", error=str(e), user_id=str(current_user.id))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


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
        
        safe_log("info", "Liste candidatures rÃ©cupÃ©rÃ©e", count=len(applications), requester_id=str(current_user.id))
        return ApplicationListResponse(
            success=True,
            message=f"{len(applications)} candidature(s) trouvÃ©e(s)",
            data=applications,
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
    RÃ©cupÃ©rer une candidature par son ID
    """
    try:
        application_service = ApplicationService(db)
        application = await application_service.get_application_by_id(application_id)
        
        if not application:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidature non trouvÃ©e")
        
        safe_log("info", "Candidature rÃ©cupÃ©rÃ©e", application_id=application_id, requester_id=str(current_user.id))
        return ApplicationResponse(
            success=True,
            message="Candidature rÃ©cupÃ©rÃ©e avec succÃ¨s",
            data=application
        )
        
    except NotFoundError as e:
        safe_log("warning", "Candidature non trouvÃ©e", application_id=application_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur rÃ©cupÃ©ration candidature", application_id=application_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.put("/{application_id}", response_model=ApplicationResponse, summary="Mettre Ã  jour une candidature", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {"status": "reviewed"}}}},
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Candidature mise Ã  jour avec succÃ¨s", "data": {"id": "uuid", "status": "reviewed"}}}}}}
})
async def update_application(
    application_id: str,
    application_data: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mettre Ã  jour une candidature
    """
    try:
        application_service = ApplicationService(db)
        application = await application_service.update_application(application_id, application_data)
        
        safe_log("info", "Candidature mise Ã  jour", application_id=application_id, requester_id=str(current_user.id))
        return ApplicationResponse(
            success=True,
            message="Candidature mise Ã  jour avec succÃ¨s",
            data=application
        )
        
    except NotFoundError as e:
        safe_log("warning", "Candidature non trouvÃ©e pour MAJ", application_id=application_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        safe_log("warning", "Erreur validation MAJ candidature", application_id=application_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur MAJ candidature", application_id=application_id, error=str(e))
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


# Endpoints pour les documents PDF
@router.post("/{application_id}/documents", response_model=ApplicationDocumentResponse, status_code=status.HTTP_201_CREATED, summary="Uploader un document PDF", openapi_extra={
    "requestBody": {"content": {"multipart/form-data": {"schema": {"type": "object", "properties": {"document_type": {"type": "string"}, "file": {"type": "string", "format": "binary"}}}, "example": {"document_type": "cv"}}}},
    "responses": {
        "201": {"content": {"application/json": {"example": {"success": True, "message": "Document uploadÃ© avec succÃ¨s", "data": {"id": "uuid", "file_name": "cv.pdf"}}}}},
        "429": {"description": "Trop d'uploads"}
    }
})
@limiter.limit(UPLOAD_LIMITS)
async def upload_document(
    request: Request,
    application_id: str,
    document_type: Optional[str] = Form(None, description="Type de document: cover_letter, cv, certificats, diplome (optionnel)"),
    file: UploadFile = File(..., description="Fichier PDF Ã  uploader"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Uploader un document PDF pour une candidature
    
    - **application_id**: ID de la candidature
    - **document_type**: Type de document (cover_letter, cv, certificats, diplome) - optionnel
    - **file**: Fichier PDF Ã  uploader (max 10MB)
    """
    try:
        # VÃ©rifier que le fichier est un PDF
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seuls les fichiers PDF sont acceptÃ©s"
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
        
        # VÃ©rifier que c'est bien un PDF (magic number)
        if not file_content.startswith(b'%PDF'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le fichier n'est pas un PDF valide"
            )
        
        # Encoder en base64
        file_data_b64 = base64.b64encode(file_content).decode('utf-8')
        
        # Valeur par dÃ©faut si non fourni
        resolved_type = (document_type or 'certificats')
        
        # CrÃ©er le document
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
        
        safe_log("info", "Document uploadÃ©", 
                application_id=application_id, 
                document_type=resolved_type,
                file_size=len(file_content),
                file_name=file.filename,
                user_id=str(current_user.id))
        
        return ApplicationDocumentResponse(
            success=True,
            message="Document uploadÃ© avec succÃ¨s",
            data=document
        )
        
    except ValueError as e:
        safe_log("warning", "Erreur validation upload document", application_id=application_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        safe_log("warning", "Candidature non trouvÃ©e pour upload", application_id=application_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur upload document", application_id=application_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


@router.post("/{application_id}/documents/multiple", response_model=ApplicationDocumentListResponse, status_code=status.HTTP_201_CREATED, summary="Uploader plusieurs documents PDF", openapi_extra={
    "requestBody": {"content": {"multipart/form-data": {"schema": {"type": "object", "properties": {"document_types": {"type": "array", "items": {"type": "string"}}, "files": {"type": "array", "items": {"type": "string", "format": "binary"}}}}, "example": {"document_types": ["cv", "certificats"]}}}},
    "responses": {
        "201": {"content": {"application/json": {"example": {"success": True, "message": "2 document(s) uploadÃ©(s) avec succÃ¨s", "data": [{"id": "uuid"}], "total": 2}}}},
        "429": {"description": "Trop d'uploads"}
    }
})
@limiter.limit(UPLOAD_LIMITS)
async def upload_multiple_documents(
    request: Request,
    application_id: str,
    files: List[UploadFile] = File(..., description="Fichiers PDF Ã  uploader"),
    document_types: List[str] = Form(..., description="Types de documents correspondants"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Uploader plusieurs documents PDF pour une candidature
    
    - **application_id**: ID de la candidature
    - **files**: Liste des fichiers PDF Ã  uploader (max 10MB chacun)
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
            # VÃ©rifier que le fichier est un PDF
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Seuls les fichiers PDF sont acceptÃ©s. Fichier invalide: {file.filename}"
                )
            
            # Lire le contenu du fichier
            file_content = await file.read()
            
            # Validation de la taille
            if len(file_content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Le fichier '{file.filename}' est trop volumineux. Taille maximale: 10MB. Taille actuelle: {len(file_content) / (1024 * 1024):.2f}MB"
                )
            
            # VÃ©rifier que c'est bien un PDF
            if not file_content.startswith(b'%PDF'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Le fichier n'est pas un PDF valide: {file.filename}"
                )
            
            # Encoder en base64
            file_data_b64 = base64.b64encode(file_content).decode('utf-8')
            
            # CrÃ©er le document
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
        
        safe_log("info", "Documents multiples uploadÃ©s",
                application_id=application_id,
                count=len(documents),
                total_size=sum(d.file_size for d in documents),
                user_id=str(current_user.id))
        
        return ApplicationDocumentListResponse(
            success=True,
            message=f"{len(documents)} document(s) uploadÃ©(s) avec succÃ¨s",
            data=documents,
            total=len(documents)
        )
        
    except ValueError as e:
        safe_log("warning", "Erreur validation upload multiple", application_id=application_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        safe_log("warning", "Candidature non trouvÃ©e pour upload multiple", application_id=application_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur upload documents multiples", application_id=application_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur")


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
        
        safe_log("info", "Documents rÃ©cupÃ©rÃ©s", application_id=application_id, count=len(documents))
        return ApplicationDocumentListResponse(
            success=True,
            message=f"{len(documents)} document(s) trouvÃ©(s)",
            data=documents,
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
        # 1. RÃ©cupÃ©rer la candidature avec toutes les relations
        application_service = ApplicationService(db)
        application = await application_service.get_application_with_relations(application_id)
        
        if not application:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidature non trouvÃ©e")
        
        # 2. VÃ©rifier les permissions
        is_admin = hasattr(current_user, 'role') and current_user.role in ['admin', 'observer']
        is_recruiter = hasattr(current_user, 'role') and current_user.role == 'recruiter'
        is_candidate = str(application.candidate_id) == str(current_user.id)

        # Recruteur: vÃ©rifier que c'est son offre (relation singuliÃ¨re job_offer)
        if is_recruiter and getattr(application, 'job_offer', None):
            if getattr(application.job_offer, 'recruiter_id', None) is not None:
                if str(application.job_offer.recruiter_id) != str(current_user.id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="AccÃ¨s non autorisÃ© : vous ne pouvez tÃ©lÃ©charger que les candidatures de vos offres"
                    )
        
        # Si ni admin, ni recruteur autorisÃ©, ni candidat
        if not (is_admin or is_candidate or is_recruiter):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="AccÃ¨s non autorisÃ©"
            )
        
        # 3. GÃ©nÃ©rer le PDF
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
        safe_log("warning", "Candidature non trouvÃ©e pour export PDF", application_id=application_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        safe_log("error", "Erreur gÃ©nÃ©ration PDF", application_id=application_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la gÃ©nÃ©ration du PDF: {str(e)}"
        )


# ---- Drafts globaux par offre (job_offer_id) ----
@router.get("/drafts", response_model=dict, summary="RÃ©cupÃ©rer le brouillon par offre", openapi_extra={
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
        service = ApplicationService(db)
        draft = await service.get_draft(user_id=str(current_user.id), job_offer_id=job_offer_id)
        if not draft:
            return {"success": True, "data": None}
        return {"success": True, "data": draft}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.post("/drafts", response_model=dict, summary="CrÃ©er/Maj le brouillon par offre", openapi_extra={
    "requestBody": {"content": {"application/json": {"example": {
        "job_offer_id": "00000000-0000-0000-0000-0000000000AA",
        "form_data": {"step": 1, "values": {"firstname": "Ada"}},
        "ui_state": {"currentStep": 2}
    }}}},
    "responses": {"200": {"content": {"application/json": {"example": {"success": True, "message": "Brouillon enregistrÃ©", "data": {}}}}}}
})
async def upsert_draft_by_job_offer(
    payload: ApplicationDraftCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        service = ApplicationService(db)
        # Forcer l'user_id depuis le token, ignorer celui reÃ§u pour sÃ©curitÃ©
        data = {
            "user_id": str(current_user.id),
            "job_offer_id": str(payload.job_offer_id),
            "form_data": payload.form_data,
            "ui_state": payload.ui_state,
        }
        draft = await service.save_draft(data)
        return {"success": True, "message": "Brouillon enregistrÃ©", "data": draft}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.delete("/drafts", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer le brouillon par offre", openapi_extra={
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
