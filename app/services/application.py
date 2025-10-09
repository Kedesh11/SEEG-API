"""
Service de gestion des candidatures
"""
import structlog
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, desc
from uuid import UUID
import base64

from app.models.application import Application, ApplicationDocument, ApplicationDraft, ApplicationHistory
from app.schemas.application import (
    ApplicationCreate, ApplicationUpdate, ApplicationDocumentCreate, 
    ApplicationDocumentUpdate, ApplicationDocumentWithData,
    ApplicationDraftUpdate, ApplicationHistoryCreate
)
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError

logger = structlog.get_logger(__name__)

class ApplicationService:
    """Service de gestion des candidatures"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_application(self, application_data: ApplicationCreate, user_id: str = None) -> Application:
        """CrÃ©er une nouvelle candidature"""
        try:
            # VÃ©rifier qu'il n'y a pas dÃ©jÃ  une candidature pour ce job
            existing_result = await self.db.execute(
                select(Application).where(
                    Application.candidate_id == application_data.candidate_id,
                    Application.job_offer_id == application_data.job_offer_id
                )
            )
            existing_application = existing_result.scalar_one_or_none()
            
            if existing_application:
                raise ValidationError("Une candidature existe dÃ©jÃ  pour cette offre d'emploi")
            
            application = Application(**application_data.dict())
            self.db.add(application)
            #  PAS de commit ici
            await self.db.refresh(application)
            
            logger.info("Candidature crÃ©Ã©e", application_id=str(application.id), candidate_id=str(application.candidate_id))
            return application
        except ValidationError:
            raise
        except Exception as e:
            logger.error("Erreur crÃ©ation candidature", error=str(e))
            raise BusinessLogicError("Erreur lors de la crÃ©ation de la candidature")
    
    async def get_application_by_id(self, application_id: str) -> Optional[Application]:
        """RÃ©cupÃ©rer une candidature par son ID avec cache"""
        from app.core.cache import cache_application
        from app.db.query_optimizer import QueryOptimizer
        
        @cache_application(expire=600)  # Cache 10 minutes
        async def _get_application(app_id: str):
            try:
                query = select(Application).where(Application.id == UUID(app_id))
                query = QueryOptimizer.optimize_application_query(query)
                
                result = await self.db.execute(query)
                application = result.scalar_one_or_none()
                
                if not application:
                    raise NotFoundError("Candidature non trouvÃ©e")
                
                return application
                
            except ValueError:
                raise ValidationError("ID de candidature invalide")
            except NotFoundError:
                raise
            except Exception as e:
                logger.error("Erreur rÃ©cupÃ©ration candidature", application_id=app_id, error=str(e))
                raise BusinessLogicError("Erreur lors de la rÃ©cupÃ©ration de la candidature")
        
        return await _get_application(application_id)
    
    async def get_application_with_relations(self, application_id: str) -> Optional[Application]:
        """
        RÃ©cupÃ©rer une candidature avec toutes ses relations pour le PDF
        (users, candidate_profiles, job_offers)
        """
        from app.core.cache import cache_key_wrapper
        from app.db.query_optimizer import get_application_complete
        
        @cache_key_wrapper("application:full", expire=300)  # Cache 5 minutes
        async def _get_full_application(app_id: str):
            try:
                application = await get_application_complete(self.db, app_id)
                
                if not application:
                    raise NotFoundError("Candidature non trouvÃ©e")
                
                return application
            except ValueError:
                raise ValidationError("ID de candidature invalide")
            except NotFoundError:
                raise
            except Exception as e:
                logger.error("Erreur rÃ©cupÃ©ration candidature complÃ¨te", application_id=app_id, error=str(e))
                raise BusinessLogicError("Erreur lors de la rÃ©cupÃ©ration de la candidature")
        
        return await _get_full_application(application_id)
    
    async def get_applications(
        self, 
        skip: int = 0, 
        limit: int = 100,
        status_filter: Optional[str] = None,
        job_offer_id: Optional[str] = None,
        candidate_id: Optional[str] = None
    ) -> tuple[List[Application], int]:
        """RÃ©cupÃ©rer la liste des candidatures avec filtres"""
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
            
            # ExÃ©cuter les requÃªtes
            result = await self.db.execute(query)
            applications = result.scalars().all()
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()
            
            return applications, total
        except ValueError as e:
            raise ValidationError("ParamÃ¨tres de filtrage invalides")
        except Exception as e:
            logger.error("Erreur rÃ©cupÃ©ration candidatures", error=str(e))
            raise BusinessLogicError("Erreur lors de la rÃ©cupÃ©ration des candidatures")
    
    async def update_application(self, application_id: str, application_data: ApplicationUpdate) -> Application:
        """Mettre Ã  jour une candidature"""
        try:
            application = await self.get_application_by_id(application_id)
            
            # Mettre Ã  jour les champs fournis
            update_data = application_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(application, field, value)
            
            #  PAS de commit ici
            await self.db.refresh(application)
            
            logger.info("Candidature mise Ã  jour", application_id=application_id)
            return application
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur mise Ã  jour candidature", application_id=application_id, error=str(e))
            raise BusinessLogicError("Erreur lors de la mise Ã  jour de la candidature")
    
    async def delete_application(self, application_id: str) -> None:
        """Supprimer une candidature"""
        try:
            application = await self.get_application_by_id(application_id)
            
            await self.db.delete(application)
            #  PAS de commit ici
            
            logger.info("Candidature supprimÃ©e", application_id=application_id)
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur suppression candidature", application_id=application_id, error=str(e))
            raise BusinessLogicError("Erreur lors de la suppression de la candidature")
    
    # MÃ©thodes pour les documents PDF
    async def create_document(self, document_data: ApplicationDocumentCreate) -> ApplicationDocument:
        """CrÃ©er un nouveau document PDF"""
        try:
            # VÃ©rifier que l'application existe
            application = await self.get_application_by_id(str(document_data.application_id))
            
            # DÃ©coder les donnÃ©es base64
            file_data = base64.b64decode(document_data.file_data)
            
            # CrÃ©er le document
            document = ApplicationDocument(
                application_id=document_data.application_id,
                document_type=document_data.document_type,
                file_name=document_data.file_name,
                file_data=file_data,
                file_size=document_data.file_size,
                file_type=document_data.file_type
            )
            
            self.db.add(document)
            #  PAS de commit ici
            await self.db.refresh(document)
            
            logger.info("Document crÃ©Ã©", document_id=str(document.id), application_id=str(document.application_id))
            return document
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur crÃ©ation document", error=str(e))
            raise BusinessLogicError("Erreur lors de la crÃ©ation du document")
    
    async def get_application_documents(
        self, 
        application_id: str, 
        document_type: Optional[str] = None
    ) -> List[ApplicationDocument]:
        """RÃ©cupÃ©rer les documents d'une candidature"""
        try:
            # VÃ©rifier que l'application existe
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
            logger.error("Erreur rÃ©cupÃ©ration documents", application_id=application_id, error=str(e))
            raise BusinessLogicError("Erreur lors de la rÃ©cupÃ©ration des documents")
    
    async def get_document_with_data(
        self, 
        application_id: str, 
        document_id: str
    ) -> Optional[ApplicationDocumentWithData]:
        """RÃ©cupÃ©rer un document avec ses donnÃ©es binaires"""
        try:
            # VÃ©rifier que l'application existe
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
                raise NotFoundError("Document non trouvÃ©")
            
            # Encoder les donnÃ©es en base64 pour la rÃ©ponse
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
            logger.error("Erreur rÃ©cupÃ©ration document", document_id=document_id, error=str(e))
            raise BusinessLogicError("Erreur lors de la rÃ©cupÃ©ration du document")
    
    async def delete_document(self, application_id: str, document_id: str) -> None:
        """Supprimer un document"""
        try:
            # VÃ©rifier que l'application existe
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
                raise NotFoundError("Document non trouvÃ©")
            
            await self.db.delete(document)
            #  PAS de commit ici
            
            logger.info("Document supprimÃ©", document_id=document_id, application_id=application_id)
        except NotFoundError:
            raise
        except ValueError:
            raise ValidationError("ID invalide")
        except Exception as e:
            logger.error("Erreur suppression document", document_id=document_id, error=str(e))
            raise BusinessLogicError("Erreur lors de la suppression du document")
    
    async def get_application_stats(self) -> Dict[str, Any]:
        """RÃ©cupÃ©rer les statistiques des candidatures"""
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
            logger.error("Erreur rÃ©cupÃ©ration statistiques", error=str(e))
            raise BusinessLogicError("Erreur lors de la rÃ©cupÃ©ration des statistiques")
    
    # MÃ©thodes pour les brouillons (inchangÃ©es)
    async def save_draft(self, draft_data: dict) -> ApplicationDraft:
        """Sauvegarder un brouillon de candidature"""
        try:
            # VÃ©rifier si un brouillon existe dÃ©jÃ 
            result = await self.db.execute(
                select(ApplicationDraft).where(
                    ApplicationDraft.user_id == draft_data["user_id"],
                    ApplicationDraft.job_offer_id == draft_data["job_offer_id"]
                )
            )
            draft = result.scalar_one_or_none()
            
            if draft:
                # Mettre Ã  jour le brouillon existant
                draft.form_data = draft_data.get("form_data")
                draft.ui_state = draft_data.get("ui_state")
            else:
                # CrÃ©er un nouveau brouillon
                draft = ApplicationDraft(**draft_data)
                self.db.add(draft)
            
            #  PAS de commit ici
            await self.db.refresh(draft)
            
            logger.info("Brouillon sauvegardÃ©", user_id=str(draft.user_id), job_offer_id=str(draft.job_offer_id))
            return draft
        except Exception as e:
            logger.error("Erreur sauvegarde brouillon", error=str(e))
            raise BusinessLogicError("Erreur lors de la sauvegarde du brouillon")
    
    async def get_draft(self, user_id: str, job_offer_id: str) -> Optional[ApplicationDraft]:
        """RÃ©cupÃ©rer un brouillon de candidature"""
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
            logger.error("Erreur rÃ©cupÃ©ration brouillon", error=str(e))
            raise BusinessLogicError("Erreur lors de la rÃ©cupÃ©ration du brouillon")
    
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
                #  PAS de commit ici
                logger.info("Brouillon supprimÃ©", user_id=user_id, job_offer_id=job_offer_id)
        except ValueError:
            raise ValidationError("IDs invalides")
        except Exception as e:
            logger.error("Erreur suppression brouillon", error=str(e))
            raise BusinessLogicError("Erreur lors de la suppression du brouillon")

    async def get_application_draft(self, application_id: str, user_id: str) -> Optional[ApplicationDraft]:
        """RÃ©cupÃ©rer le brouillon liÃ© Ã  une candidature (via son job_offer_id)."""
        try:
            application = await self.get_application_by_id(application_id)
            return await self.get_draft(user_id=user_id, job_offer_id=str(application.job_offer_id))
        except Exception as e:
            logger.error("Erreur get_application_draft", application_id=application_id, error=str(e))
            raise BusinessLogicError("Erreur lors de la rÃ©cupÃ©ration du brouillon")

    async def upsert_application_draft(self, application_id: str, user_id: str, draft_data: "ApplicationDraftUpdate") -> ApplicationDraft:
        """CrÃ©er/met Ã  jour le brouillon pour la candidature donnÃ©e (basÃ© sur user_id + job_offer_id)."""
        try:
            application = await self.get_application_by_id(application_id)
            payload = {
                "user_id": user_id,
                "job_offer_id": str(application.job_offer_id),
                "form_data": draft_data.form_data if hasattr(draft_data, "form_data") else None,
                "ui_state": draft_data.ui_state if hasattr(draft_data, "ui_state") else None,
            }
            return await self.save_draft(payload)
        except Exception as e:
            logger.error("Erreur upsert_application_draft", application_id=application_id, error=str(e))
            raise BusinessLogicError("Erreur lors de l'enregistrement du brouillon")

    async def delete_application_draft(self, application_id: str, user_id: str) -> None:
        """Supprimer le brouillon pour la candidature donnÃ©e."""
        try:
            application = await self.get_application_by_id(application_id)
            await self.delete_draft(user_id=user_id, job_offer_id=str(application.job_offer_id))
        except Exception as e:
            logger.error("Erreur delete_application_draft", application_id=application_id, error=str(e))
            raise BusinessLogicError("Erreur lors de la suppression du brouillon")

    async def list_application_history(self, application_id: str) -> List[ApplicationHistory]:
        """Lister l'historique des statuts d'une candidature."""
        try:
            await self.get_application_by_id(application_id)
            result = await self.db.execute(
                select(ApplicationHistory)
                .where(ApplicationHistory.application_id == UUID(application_id))
                .order_by(desc(ApplicationHistory.changed_at))
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Erreur list_application_history", application_id=application_id, error=str(e))
            raise BusinessLogicError("Erreur lors de la rÃ©cupÃ©ration de l'historique")

    async def add_application_history(self, application_id: str, item: "ApplicationHistoryCreate", changed_by_user_id: str | None) -> ApplicationHistory:
        """Ajouter une entrÃ©e d'historique et Ã©ventuellement mettre Ã  jour le statut de la candidature."""
        try:
            application = await self.get_application_by_id(application_id)
            history = ApplicationHistory(
                application_id=UUID(application_id),
                changed_by=UUID(changed_by_user_id) if changed_by_user_id else None,
                previous_status=item.previous_status or application.status,
                new_status=item.new_status or application.status,
                notes=item.notes,
            )
            self.db.add(history)
            # Mettre Ã  jour le statut de l'application si new_status fourni
            if item.new_status and item.new_status != application.status:
                application.status = item.new_status
            #  PAS de commit ici
            await self.db.refresh(history)
            return history
        except Exception as e:
            logger.error("Erreur add_application_history", application_id=application_id, error=str(e))
            raise BusinessLogicError("Erreur lors de l'ajout Ã  l'historique")

    async def get_advanced_statistics(self) -> Dict[str, Any]:
        """Statistiques avancÃ©es des candidatures: par statut, par offre, par mois, documents par type."""
        try:
            # Totaux par statut
            status_rows = await self.db.execute(
                select(Application.status, func.count(Application.id)).group_by(Application.status)
            )
            status_breakdown = {row[0]: int(row[1]) for row in status_rows.fetchall()}

            # Total applications
            total = (await self.db.execute(select(func.count(Application.id)))).scalar() or 0

            # Par offre (counts)
            by_job_rows = await self.db.execute(
                select(Application.job_offer_id, func.count(Application.id))
                .group_by(Application.job_offer_id)
            )
            by_job_offer = {str(row[0]): int(row[1]) for row in by_job_rows.fetchall() if row[0] is not None}

            # Par mois (date_trunc)
            by_month_rows = await self.db.execute(
                select(func.date_trunc('month', Application.created_at), func.count(Application.id))
                .group_by(func.date_trunc('month', Application.created_at))
                .order_by(func.date_trunc('month', Application.created_at))
            )
            by_month = {row[0].date().isoformat(): int(row[1]) for row in by_month_rows.fetchall() if row[0] is not None}

            # Documents par type
            doc_rows = await self.db.execute(
                select(ApplicationDocument.document_type, func.count(ApplicationDocument.id))
                .group_by(ApplicationDocument.document_type)
            )
            documents_by_type = {row[0]: int(row[1]) for row in doc_rows.fetchall() if row[0] is not None}

            return {
                "total_applications": int(total),
                "status_breakdown": status_breakdown,
                "by_job_offer": by_job_offer,
                "by_month": by_month,
                "documents_by_type": documents_by_type,
            }
        except Exception as e:
            logger.error("Erreur statistiques avancÃ©es", error=str(e))
            # Retourner une structure vide mais cohÃ©rente plutÃ´t que 500
            return {
                "total_applications": 0,
                "status_breakdown": {},
                "by_job_offer": {},
                "by_month": {},
                "documents_by_type": {},
            }
