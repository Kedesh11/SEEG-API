"""
Endpoints pour la gestion des candidatures
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.services.application import ApplicationService
from app.services.file import FileService
from app.services.email import EmailService
from app.schemas.application import (
    ApplicationCreate, ApplicationUpdate, ApplicationResponse, ApplicationListResponse,
    ApplicationStatusUpdate, ApplicationDocumentResponse, ApplicationDraftCreate,
    ApplicationDraftUpdate, ApplicationDraftResponse, ApplicationStatsResponse
)
from app.core.security import get_current_user
from app.models.user import User
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError, FileError

router = APIRouter()


@router.post("/", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    application_data: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Créer une nouvelle candidature
    
    - **job_offer_id**: ID de l'offre d'emploi
    - **cover_letter**: Lettre de motivation (optionnel)
    - **expected_salary**: Salaire attendu (optionnel)
    - **availability_date**: Date de disponibilité (optionnel)
    - **additional_info**: Informations additionnelles (optionnel)
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
                candidate_email=current_user.email,
                candidate_name=f"{current_user.first_name} {current_user.last_name}",
                job_title="Poste",  # À récupérer depuis l'offre d'emploi
                application_id=str(application.id)
            )
        except Exception as e:
            # Log l'erreur mais ne fait pas échouer la création de candidature
            pass
        
        return application
    except (ValidationError, BusinessLogicError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/", response_model=ApplicationListResponse)
async def get_applications(
    skip: int = Query(0, ge=0, description="Nombre d'éléments à ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum d'éléments à retourner"),
    status: Optional[str] = Query(None, description="Filtrer par statut"),
    job_offer_id: Optional[str] = Query(None, description="Filtrer par offre d'emploi"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer la liste des candidatures
    
    - **skip**: Nombre d'éléments à ignorer (pagination)
    - **limit**: Nombre maximum d'éléments à retourner
    - **status**: Filtrer par statut de candidature
    - **job_offer_id**: Filtrer par offre d'emploi spécifique
    """
    try:
        application_service = ApplicationService(db)
        
        if job_offer_id:
            # Récupérer les candidatures pour une offre d'emploi spécifique
            return await application_service.get_job_applications(
                job_offer_id=job_offer_id,
                skip=skip,
                limit=limit,
                status=status
            )
        else:
            # Récupérer les candidatures du candidat actuel
            return await application_service.get_candidate_applications(
                candidate_id=str(current_user.id),
                skip=skip,
                limit=limit,
                status=status
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer une candidature par son ID
    
    - **application_id**: ID unique de la candidature
    """
    try:
        application_service = ApplicationService(db)
        return await application_service.get_application(application_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.put("/{application_id}/status", response_model=ApplicationResponse)
async def update_application_status(
    application_id: str,
    status_data: ApplicationStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Mettre à jour le statut d'une candidature
    
    - **application_id**: ID de la candidature
    - **status**: Nouveau statut
    - **notes**: Notes sur le changement de statut (optionnel)
    """
    try:
        application_service = ApplicationService(db)
        email_service = EmailService(db)
        
        # Mise à jour du statut
        application = await application_service.update_application_status(
            application_id, status_data, str(current_user.id)
        )
        
        # Envoi d'email de notification (en arrière-plan)
        try:
            await email_service.send_application_status_update(
                candidate_email="candidate@example.com",  # À récupérer depuis la candidature
                candidate_name="Candidat",  # À récupérer depuis la candidature
                job_title="Poste",  # À récupérer depuis l'offre d'emploi
                new_status=status_data.status,
                notes=status_data.notes
            )
        except Exception as e:
            # Log l'erreur mais ne fait pas échouer la mise à jour
            pass
        
        return application
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationError, BusinessLogicError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.post("/{application_id}/documents", response_model=ApplicationDocumentResponse)
async def upload_application_document(
    application_id: str,
    file: UploadFile = File(...),
    document_type: str = Query(..., description="Type de document"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Télécharger un document pour une candidature
    
    - **application_id**: ID de la candidature
    - **file**: Fichier à télécharger
    - **document_type**: Type de document (cv, cover_letter, diploma, certificate, other)
    """
    try:
        file_service = FileService(db)
        
        # Lecture du contenu du fichier
        file_content = await file.read()
        
        # Téléchargement du fichier
        document_info = await file_service.upload_file(
            file_content=file_content,
            filename=file.filename,
            application_id=application_id,
            document_type=document_type,
            uploaded_by=str(current_user.id)
        )
        
        return ApplicationDocumentResponse(**document_info)
    except (ValidationError, FileError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/{application_id}/documents", response_model=List[ApplicationDocumentResponse])
async def get_application_documents(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer les documents d'une candidature
    
    - **application_id**: ID de la candidature
    """
    try:
        application_service = ApplicationService(db)
        return await application_service.get_application_documents(application_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.post("/drafts", response_model=ApplicationDraftResponse, status_code=status.HTTP_201_CREATED)
async def create_application_draft(
    draft_data: ApplicationDraftCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Créer ou mettre à jour un brouillon de candidature
    
    - **job_offer_id**: ID de l'offre d'emploi
    - **cover_letter**: Lettre de motivation (optionnel)
    - **expected_salary**: Salaire attendu (optionnel)
    - **availability_date**: Date de disponibilité (optionnel)
    - **additional_info**: Informations additionnelles (optionnel)
    """
    try:
        application_service = ApplicationService(db)
        return await application_service.create_application_draft(
            draft_data, str(current_user.id)
        )
    except (ValidationError, BusinessLogicError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@router.get("/stats/overview", response_model=ApplicationStatsResponse)
async def get_application_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Récupérer les statistiques des candidatures
    
    Retourne:
    - Nombre total de candidatures
    - Répartition par statut
    - Tendance mensuelle
    """
    try:
        application_service = ApplicationService(db)
        return await application_service.get_application_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")
