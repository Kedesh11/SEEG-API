"""
Service de gestion des candidatures
"""
import structlog
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_
from uuid import UUID
import base64

from app.models.application import Application, ApplicationDocument, ApplicationDraft
from app.schemas.application import (
    ApplicationCreate, ApplicationUpdate, ApplicationDocumentCreate, 
    ApplicationDocumentUpdate, ApplicationDocumentWithData
)
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError

logger = structlog.get_logger(__name__)

class ApplicationService:
    """Service de gestion des candidatures"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_application(self, application_data: ApplicationCreate, user_id: str = None) -> Application:
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
    
    async def get_application_by_id(self, application_id: str) -> Optional[Application]:
        """Récupérer une candidature par son ID"""
        try:
            result = await self.db.execute(
                select(Application).where(Application.id == UUID(application_id))
            )
            application = result.scalar_one_or_none()
            
            if not application:
                raise NotFoundError("Candidature non trouvée")
            
            return application
        except ValueError:
            raise ValidationError("ID de candidature invalide")
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur récupération candidature", application_id=application_id, error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération de la candidature")
    
    async def get_applications(
        self, 
        skip: int = 0, 
        limit: int = 100,
        status_filter: Optional[str] = None,
        job_offer_id: Optional[str] = None,
        candidate_id: Optional[str] = None
    ) -> tuple[List[Application], int]:
        """Récupérer la liste des candidatures avec filtres"""
        try:
            query = select(Application)
            count_query = select(func.count(Application.id))
            
            # Appliquer les filtres
            conditions = []
            if status_filter:
                conditions.append(Application.status == status_filter)
            if job_offer_id:
                conditions.append(Application.job_offer_id == UUID(job_offer_id))
            if candidate_id:
                conditions.append(Application.candidate_id == UUID(candidate_id))
            
            if conditions:
                query = query.where(and_(*conditions))
                count_query = count_query.where(and_(*conditions))
            
            # Pagination
            query = query.offset(skip).limit(limit)
            
            # Exécuter les requêtes
            result = await self.db.execute(query)
            applications = result.scalars().all()
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()
            
            return applications, total
        except ValueError as e:
            raise ValidationError("Paramètres de filtrage invalides")
        except Exception as e:
            logger.error("Erreur récupération candidatures", error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération des candidatures")
    
    async def update_application(self, application_id: str, application_data: ApplicationUpdate) -> Application:
        """Mettre à jour une candidature"""
        try:
            application = await self.get_application_by_id(application_id)
            
            # Mettre à jour les champs fournis
            update_data = application_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(application, field, value)
            
            await self.db.commit()
            await self.db.refresh(application)
            
            logger.info("Candidature mise à jour", application_id=application_id)
            return application
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur mise à jour candidature", application_id=application_id, error=str(e))
            raise BusinessLogicError("Erreur lors de la mise à jour de la candidature")
    
    async def delete_application(self, application_id: str) -> None:
        """Supprimer une candidature"""
        try:
            application = await self.get_application_by_id(application_id)
            
            await self.db.delete(application)
            await self.db.commit()
            
            logger.info("Candidature supprimée", application_id=application_id)
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur suppression candidature", application_id=application_id, error=str(e))
            raise BusinessLogicError("Erreur lors de la suppression de la candidature")
    
    # Méthodes pour les documents PDF
    async def create_document(self, document_data: ApplicationDocumentCreate) -> ApplicationDocument:
        """Créer un nouveau document PDF"""
        try:
            # Vérifier que l'application existe
            application = await self.get_application_by_id(str(document_data.application_id))
            
            # Décoder les données base64
            file_data = base64.b64decode(document_data.file_data)
            
            # Créer le document
            document = ApplicationDocument(
                application_id=document_data.application_id,
                document_type=document_data.document_type,
                file_name=document_data.file_name,
                file_data=file_data,
                file_size=document_data.file_size,
                file_type=document_data.file_type
            )
            
            self.db.add(document)
            await self.db.commit()
            await self.db.refresh(document)
            
            logger.info("Document créé", document_id=str(document.id), application_id=str(document.application_id))
            return document
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur création document", error=str(e))
            raise BusinessLogicError("Erreur lors de la création du document")
    
    async def get_application_documents(
        self, 
        application_id: str, 
        document_type: Optional[str] = None
    ) -> List[ApplicationDocument]:
        """Récupérer les documents d'une candidature"""
        try:
            # Vérifier que l'application existe
            await self.get_application_by_id(application_id)
            
            query = select(ApplicationDocument).where(
                ApplicationDocument.application_id == UUID(application_id)
            )
            
            if document_type:
                query = query.where(ApplicationDocument.document_type == document_type)
            
            result = await self.db.execute(query)
            documents = result.scalars().all()
            
            return documents
        except NotFoundError:
            raise
        except ValueError:
            raise ValidationError("ID de candidature invalide")
        except Exception as e:
            logger.error("Erreur récupération documents", application_id=application_id, error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération des documents")
    
    async def get_document_with_data(
        self, 
        application_id: str, 
        document_id: str
    ) -> Optional[ApplicationDocumentWithData]:
        """Récupérer un document avec ses données binaires"""
        try:
            # Vérifier que l'application existe
            await self.get_application_by_id(application_id)
            
            result = await self.db.execute(
                select(ApplicationDocument).where(
                    and_(
                        ApplicationDocument.id == UUID(document_id),
                        ApplicationDocument.application_id == UUID(application_id)
                    )
                )
            )
            document = result.scalar_one_or_none()
            
            if not document:
                raise NotFoundError("Document non trouvé")
            
            # Encoder les données en base64 pour la réponse
            file_data_b64 = base64.b64encode(document.file_data).decode('utf-8')
            
            return ApplicationDocumentWithData(
                id=document.id,
                application_id=document.application_id,
                document_type=document.document_type,
                file_name=document.file_name,
                file_size=document.file_size,
                file_type=document.file_type,
                uploaded_at=document.uploaded_at,
                file_data=file_data_b64
            )
        except NotFoundError:
            raise
        except ValueError:
            raise ValidationError("ID invalide")
        except Exception as e:
            logger.error("Erreur récupération document", document_id=document_id, error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération du document")
    
    async def delete_document(self, application_id: str, document_id: str) -> None:
        """Supprimer un document"""
        try:
            # Vérifier que l'application existe
            await self.get_application_by_id(application_id)
            
            result = await self.db.execute(
                select(ApplicationDocument).where(
                    and_(
                        ApplicationDocument.id == UUID(document_id),
                        ApplicationDocument.application_id == UUID(application_id)
                    )
                )
            )
            document = result.scalar_one_or_none()
            
            if not document:
                raise NotFoundError("Document non trouvé")
            
            await self.db.delete(document)
            await self.db.commit()
            
            logger.info("Document supprimé", document_id=document_id, application_id=application_id)
        except NotFoundError:
            raise
        except ValueError:
            raise ValidationError("ID invalide")
        except Exception as e:
            logger.error("Erreur suppression document", document_id=document_id, error=str(e))
            raise BusinessLogicError("Erreur lors de la suppression du document")
    
    async def get_application_stats(self) -> Dict[str, Any]:
        """Récupérer les statistiques des candidatures"""
        try:
            # Compter par statut
            status_result = await self.db.execute(
                select(Application.status, func.count(Application.id))
                .group_by(Application.status)
            )
            status_counts = dict(status_result.fetchall())
            
            # Compter le total
            total_result = await self.db.execute(select(func.count(Application.id)))
            total = total_result.scalar()
            
            # Compter les documents par type
            doc_type_result = await self.db.execute(
                select(ApplicationDocument.document_type, func.count(ApplicationDocument.id))
                .group_by(ApplicationDocument.document_type)
            )
            doc_type_counts = dict(doc_type_result.fetchall())
            
            return {
                "total_applications": total,
                "status_breakdown": status_counts,
                "document_types": doc_type_counts
            }
        except Exception as e:
            logger.error("Erreur récupération statistiques", error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération des statistiques")
    
    # Méthodes pour les brouillons (inchangées)
    async def save_draft(self, draft_data: dict) -> ApplicationDraft:
        """Sauvegarder un brouillon de candidature"""
        try:
            # Vérifier si un brouillon existe déjà
            result = await self.db.execute(
                select(ApplicationDraft).where(
                    ApplicationDraft.user_id == draft_data["user_id"],
                    ApplicationDraft.job_offer_id == draft_data["job_offer_id"]
                )
            )
            draft = result.scalar_one_or_none()
            
            if draft:
                # Mettre à jour le brouillon existant
                draft.form_data = draft_data.get("form_data")
                draft.ui_state = draft_data.get("ui_state")
            else:
                # Créer un nouveau brouillon
                draft = ApplicationDraft(**draft_data)
                self.db.add(draft)
            
            await self.db.commit()
            await self.db.refresh(draft)
            
            logger.info("Brouillon sauvegardé", user_id=str(draft.user_id), job_offer_id=str(draft.job_offer_id))
            return draft
        except Exception as e:
            logger.error("Erreur sauvegarde brouillon", error=str(e))
            raise BusinessLogicError("Erreur lors de la sauvegarde du brouillon")
    
    async def get_draft(self, user_id: str, job_offer_id: str) -> Optional[ApplicationDraft]:
        """Récupérer un brouillon de candidature"""
        try:
            result = await self.db.execute(
                select(ApplicationDraft).where(
                    ApplicationDraft.user_id == UUID(user_id),
                    ApplicationDraft.job_offer_id == UUID(job_offer_id)
                )
            )
            return result.scalar_one_or_none()
        except ValueError:
            raise ValidationError("IDs invalides")
        except Exception as e:
            logger.error("Erreur récupération brouillon", error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération du brouillon")
    
    async def delete_draft(self, user_id: str, job_offer_id: str) -> None:
        """Supprimer un brouillon de candidature"""
        try:
            result = await self.db.execute(
                select(ApplicationDraft).where(
                    ApplicationDraft.user_id == UUID(user_id),
                    ApplicationDraft.job_offer_id == UUID(job_offer_id)
                )
            )
            draft = result.scalar_one_or_none()
            
            if draft:
                await self.db.delete(draft)
                await self.db.commit()
                logger.info("Brouillon supprimé", user_id=user_id, job_offer_id=job_offer_id)
        except ValueError:
            raise ValidationError("IDs invalides")
        except Exception as e:
            logger.error("Erreur suppression brouillon", error=str(e))
            raise BusinessLogicError("Erreur lors de la suppression du brouillon")
