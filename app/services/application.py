"""
Service de gestion des candidatures
"""
import structlog
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from uuid import UUID

from app.models.application import Application, ApplicationDocument, ApplicationDraft
from app.schemas.application import ApplicationCreate, ApplicationUpdate, ApplicationDocumentCreate
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError

logger = structlog.get_logger(__name__)

class ApplicationService:
    """Service de gestion des candidatures"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_application(self, application_data: ApplicationCreate) -> Application:
        """Créer une nouvelle candidature"""
        try:
            # Vérifier qu'il n'y a pas déjà une candidature pour ce job
            existing_result = await self.db.execute(
                select(Application).where(
                    Application.candidate_id == application_data.candidate_id,
                    Application.job_offer_id == application_data.job_offer_id
                )
            )
            existing_application = existing_result.scalar_one_or_none()
            
            if existing_application:
                raise ValidationError("Une candidature existe déjà pour cette offre d'emploi")
            
            application = Application(**application_data.dict())
            self.db.add(application)
            await self.db.commit()
            await self.db.refresh(application)
            
            logger.info("Candidature créée", application_id=str(application.id), candidate_id=str(application.candidate_id))
            return application
        except ValidationError:
            raise
        except Exception as e:
            logger.error("Erreur création candidature", error=str(e))
            raise BusinessLogicError("Erreur lors de la création de la candidature")
    
    async def get_application(self, application_id: UUID) -> Optional[Application]:
        """Récupérer une candidature par son ID"""
        try:
            result = await self.db.execute(
                select(Application).where(Application.id == application_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Erreur récupération candidature", error=str(e), application_id=str(application_id))
            raise BusinessLogicError("Erreur lors de la récupération de la candidature")
    
    async def get_applications(
        self, 
        skip: int = 0, 
        limit: int = 100,
        candidate_id: Optional[UUID] = None,
        job_offer_id: Optional[UUID] = None,
        status: Optional[str] = None
    ) -> List[Application]:
        """Récupérer la liste des candidatures"""
        try:
            query = select(Application)
            
            if candidate_id:
                query = query.where(Application.candidate_id == candidate_id)
            
            if job_offer_id:
                query = query.where(Application.job_offer_id == job_offer_id)
            
            if status:
                query = query.where(Application.status == status)
            
            query = query.offset(skip).limit(limit).order_by(Application.created_at.desc())
            
            result = await self.db.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error("Erreur récupération liste candidatures", error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération des candidatures")
    
    async def update_application(self, application_id: UUID, application_data: ApplicationUpdate) -> Application:
        """Mettre à jour une candidature"""
        try:
            # Vérifier que la candidature existe
            application = await self.get_application(application_id)
            if not application:
                raise NotFoundError("Candidature non trouvée")
            
            # Mettre à jour les champs fournis
            update_data = application_data.dict(exclude_unset=True)
            if update_data:
                await self.db.execute(
                    update(Application)
                    .where(Application.id == application_id)
                    .values(**update_data)
                )
                await self.db.commit()
                
                # Récupérer la candidature mise à jour
                application = await self.get_application(application_id)
            
            logger.info("Candidature mise à jour", application_id=str(application_id))
            return application
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur mise à jour candidature", error=str(e), application_id=str(application_id))
            raise BusinessLogicError("Erreur lors de la mise à jour de la candidature")
    
    async def delete_application(self, application_id: UUID) -> bool:
        """Supprimer une candidature"""
        try:
            # Vérifier que la candidature existe
            application = await self.get_application(application_id)
            if not application:
                raise NotFoundError("Candidature non trouvée")
            
            await self.db.execute(
                delete(Application).where(Application.id == application_id)
            )
            await self.db.commit()
            
            logger.info("Candidature supprimée", application_id=str(application_id))
            return True
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur suppression candidature", error=str(e), application_id=str(application_id))
            raise BusinessLogicError("Erreur lors de la suppression de la candidature")
    
    async def add_document(self, application_id: UUID, document_data: ApplicationDocumentCreate) -> ApplicationDocument:
        """Ajouter un document à une candidature"""
        try:
            # Vérifier que la candidature existe
            application = await self.get_application(application_id)
            if not application:
                raise NotFoundError("Candidature non trouvée")
            
            document = ApplicationDocument(
                application_id=application_id,
                **document_data.dict()
            )
            
            self.db.add(document)
            await self.db.commit()
            await self.db.refresh(document)
            
            logger.info("Document ajouté", document_id=str(document.id), application_id=str(application_id))
            return document
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur ajout document", error=str(e), application_id=str(application_id))
            raise BusinessLogicError("Erreur lors de l'ajout du document")
    
    async def get_application_documents(self, application_id: UUID) -> List[ApplicationDocument]:
        """Récupérer les documents d'une candidature"""
        try:
            result = await self.db.execute(
                select(ApplicationDocument).where(ApplicationDocument.application_id == application_id)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Erreur récupération documents", error=str(e), application_id=str(application_id))
            raise BusinessLogicError("Erreur lors de la récupération des documents")
    
    async def save_draft(self, user_id: UUID, job_offer_id: UUID, form_data: Dict[str, Any], ui_state: Dict[str, Any]) -> ApplicationDraft:
        """Sauvegarder un brouillon de candidature"""
        try:
            # Vérifier s'il existe déjà un brouillon
            result = await self.db.execute(
                select(ApplicationDraft).where(
                    ApplicationDraft.user_id == user_id,
                    ApplicationDraft.job_offer_id == job_offer_id
                )
            )
            draft = result.scalar_one_or_none()
            
            if draft:
                # Mettre à jour le brouillon existant
                await self.db.execute(
                    update(ApplicationDraft)
                    .where(
                        ApplicationDraft.user_id == user_id,
                        ApplicationDraft.job_offer_id == job_offer_id
                    )
                    .values(form_data=form_data, ui_state=ui_state)
                )
                await self.db.commit()
                
                # Récupérer le brouillon mis à jour
                result = await self.db.execute(
                    select(ApplicationDraft).where(
                        ApplicationDraft.user_id == user_id,
                        ApplicationDraft.job_offer_id == job_offer_id
                    )
                )
                draft = result.scalar_one()
            else:
                # Créer un nouveau brouillon
                draft = ApplicationDraft(
                    user_id=user_id,
                    job_offer_id=job_offer_id,
                    form_data=form_data,
                    ui_state=ui_state
                )
                self.db.add(draft)
                await self.db.commit()
                await self.db.refresh(draft)
            
            logger.info("Brouillon sauvegardé", user_id=str(user_id), job_offer_id=str(job_offer_id))
            return draft
            
        except Exception as e:
            logger.error("Erreur sauvegarde brouillon", error=str(e), user_id=str(user_id))
            raise BusinessLogicError("Erreur lors de la sauvegarde du brouillon")
    
    async def get_draft(self, user_id: UUID, job_offer_id: UUID) -> Optional[ApplicationDraft]:
        """Récupérer un brouillon de candidature"""
        try:
            result = await self.db.execute(
                select(ApplicationDraft).where(
                    ApplicationDraft.user_id == user_id,
                    ApplicationDraft.job_offer_id == job_offer_id
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Erreur récupération brouillon", error=str(e), user_id=str(user_id))
            raise BusinessLogicError("Erreur lors de la récupération du brouillon")
