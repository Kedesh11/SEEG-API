"""
Service de gestion des candidatures
"""
import structlog
import json
from typing import Optional, List, Dict, Any
from app.utils.json_utils import JSONDataHandler
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, desc
from sqlalchemy.orm import selectinload, joinedload
from uuid import UUID
import base64

from app.models.application import Application, ApplicationDocument, ApplicationDraft, ApplicationHistory
from app.models.user import User
from app.models.job_offer import JobOffer
from app.models.candidate_profile import CandidateProfile
from app.schemas.application import (
    ApplicationCreate, ApplicationUpdate, ApplicationDocumentCreate, 
    ApplicationDocumentUpdate, ApplicationDocumentWithData,
    ApplicationDraftUpdate, ApplicationHistoryCreate
)
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError, DatabaseError

logger = structlog.get_logger(__name__)

class ApplicationService:
    """Service de gestion des candidatures"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def _validate_mtp_answers(
        self,
        job_offer_id: UUID,
        application_data: ApplicationCreate
    ) -> None:
        """
        Valide que les réponses MTP correspondent aux questions de l'offre.
        
        Règle: Le candidat doit répondre à TOUTES les questions MTP de l'offre.
        Le nombre de réponses doit correspondre exactement au nombre de questions.
        
        Args:
            job_offer_id: UUID de l'offre d'emploi
            application_data: Données de la candidature
            
        Raises:
            ValidationError: Si le nombre de réponses ne correspond pas aux questions
        """
        from app.models.job_offer import JobOffer
        logger = structlog.get_logger(__name__)
        
        # Récupérer l'offre avec ses questions MTP
        job_result = await self.db.execute(
            select(JobOffer).where(JobOffer.id == job_offer_id)
        )
        job_offer = job_result.scalar_one_or_none()
        
        if job_offer is None:
            raise ValidationError("Offre d'emploi introuvable")
        
        # Si l'offre n'a pas de questions MTP, pas de validation nécessaire
        # Utiliser getattr pour éviter les warnings du type checker avec SQLAlchemy
        questions_mtp = getattr(job_offer, 'questions_mtp', None)
        if questions_mtp is None:
            logger.info("Pas de questions MTP pour cette offre", job_offer_id=str(job_offer_id))
            return
        
        # Si le candidat n'a pas fourni de réponses mais l'offre a des questions, erreur
        if application_data.mtp_answers is None:
            raise ValidationError("Les réponses MTP sont obligatoires pour cette offre")
        
        # Compter les questions et réponses pour chaque catégorie
        questions = questions_mtp
        answers = application_data.mtp_answers
        
        errors = []
        
        # Parser les données JSON de manière sécurisée
        logger.debug("🔍 Validation MTP", questions_type=type(questions).__name__, answers_type=type(answers).__name__)
        
        # Utilisation de notre utilitaire JSON sécurisé
        questions = JSONDataHandler.safe_parse_json(questions, {})
        answers = JSONDataHandler.safe_parse_json(answers, {})
        
        logger.debug("🔍 Données parsées", questions_keys=list(questions.keys()) if isinstance(questions, dict) else "N/A", 
                    answers_keys=list(answers.keys()) if isinstance(answers, dict) else "N/A")
        
        # S'assurer que les données parsées sont des dictionnaires
        if not isinstance(questions, dict):
            logger.warning("⚠️ Questions n'est pas un dictionnaire", questions_type=type(questions).__name__)
            questions = {}
        if not isinstance(answers, dict):
            logger.warning("⚠️ Answers n'est pas un dictionnaire", answers_type=type(answers).__name__)
            answers = {}
        
        # Vérifier Métier
        nb_questions_metier = len(JSONDataHandler.safe_get_list(questions.get('questions_metier'), []))
        nb_reponses_metier = len(JSONDataHandler.safe_get_list(answers.get('reponses_metier'), []))
        if nb_questions_metier != nb_reponses_metier:
            errors.append(f"Métier: {nb_reponses_metier} réponse(s) fournie(s) pour {nb_questions_metier} question(s)")
        
        # Vérifier Talent
        nb_questions_talent = len(JSONDataHandler.safe_get_list(questions.get('questions_talent'), []))
        nb_reponses_talent = len(JSONDataHandler.safe_get_list(answers.get('reponses_talent'), []))
        if nb_questions_talent != nb_reponses_talent:
            errors.append(f"Talent: {nb_reponses_talent} réponse(s) fournie(s) pour {nb_questions_talent} question(s)")
        
        # Vérifier Paradigme
        nb_questions_paradigme = len(JSONDataHandler.safe_get_list(questions.get('questions_paradigme'), []))
        nb_reponses_paradigme = len(JSONDataHandler.safe_get_list(answers.get('reponses_paradigme'), []))
        if nb_questions_paradigme != nb_reponses_paradigme:
            errors.append(f"Paradigme: {nb_reponses_paradigme} réponse(s) fournie(s) pour {nb_questions_paradigme} question(s)")
        
        if errors:
            error_message = "Le nombre de réponses MTP ne correspond pas aux questions de l'offre:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.warning(
                "Validation MTP échouée",
                job_offer_id=str(job_offer_id),
                errors=errors,
                nb_questions_metier=nb_questions_metier,
                nb_reponses_metier=nb_reponses_metier,
                nb_questions_talent=nb_questions_talent,
                nb_reponses_talent=nb_reponses_talent,
                nb_questions_paradigme=nb_questions_paradigme,
                nb_reponses_paradigme=nb_reponses_paradigme
            )
            raise ValidationError(error_message)
        
        logger.info(
            "Validation MTP réussie",
            job_offer_id=str(job_offer_id),
            metier=f"{nb_reponses_metier}/{nb_questions_metier}",
            talent=f"{nb_reponses_talent}/{nb_questions_talent}",
            paradigme=f"{nb_reponses_paradigme}/{nb_questions_paradigme}"
        )
    
    async def create_application(self, application_data: ApplicationCreate, user_id: Optional[str] = None) -> Application:
        """
        Créer une nouvelle candidature avec validation des questions MTP.
        
        Le système valide automatiquement:
        1. Qu'il n'existe pas déjà une candidature pour cette offre
        2. Que le nombre de questions MTP respecte les limites du type de candidat
        
        Args:
            application_data: Données de la candidature
            user_id: ID de l'utilisateur (optionnel)
            
        Returns:
            Application: La candidature créée
            
        Raises:
            ValidationError: Si validation échoue (doublon ou limites MTP dépassées)
            BusinessLogicError: Si erreur lors de la création
        """
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
            
            # Valider que les réponses MTP correspondent aux questions de l'offre
            # Si l'offre a des questions MTP, les réponses sont obligatoires
            await self._validate_mtp_answers(
                application_data.job_offer_id,
                application_data
            )
            
            # Créer la candidature
            application = Application(**application_data.dict())
            self.db.add(application)
            # Flush pour obtenir l'ID et persister l'objet dans la session
            await self.db.flush()
            await self.db.refresh(application)
            
            logger.info("Candidature créée", application_id=str(application.id), candidate_id=str(application.candidate_id))
            return application
        except ValidationError:
            raise
        except Exception as e:
            # Log détaillé avec traceback
            import traceback
            error_traceback = traceback.format_exc()
            logger.error("Erreur création candidature", 
                        error=str(e), 
                        error_type=type(e).__name__,
                        traceback=error_traceback,
                        candidate_id=str(application_data.candidate_id),
                        job_offer_id=str(application_data.job_offer_id))
            # Retourner l'erreur originale pour un meilleur debugging
            raise BusinessLogicError(f"Erreur lors de la création de la candidature: {type(e).__name__} - {str(e)}")
    
    async def get_application_by_id(self, application_id: str) -> Optional[Application]:
        """Récupérer une candidature par son ID avec cache"""
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
                    raise NotFoundError("Candidature non trouvée")
                
                return application
                
            except ValueError:
                raise ValidationError("ID de candidature invalide")
            except NotFoundError:
                raise
            except Exception as e:
                logger.error("Erreur récupération candidature", application_id=app_id, error=str(e))
                raise BusinessLogicError("Erreur lors de la récupération de la candidature")
        
        return await _get_application(application_id)
    
    async def get_application_with_relations(self, application_id: str) -> Optional[Application]:
        """
        Récupérer une candidature avec toutes ses relations pour le PDF
        (users, candidate_profiles, job_offers)
        """
        from app.db.query_optimizer import get_application_complete
        
        # DÉSACTIVATION TEMPORAIRE DU CACHE pour voir les modifications en temps réel
        try:
            logger.debug("🔍 Récupération application complète (SANS CACHE)", application_id=application_id)
            application = await get_application_complete(self.db, application_id)
            
            if not application:
                logger.warning("⚠️ Application non trouvée", application_id=application_id)
                raise NotFoundError("Candidature non trouvée")
            
            logger.debug("✅ Application récupérée", application_id=application_id, 
                       mtp_answers_type=type(getattr(application, 'mtp_answers', None)).__name__)
            return application
        except ValueError:
            raise ValidationError("ID de candidature invalide")
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur récupération candidature complète", application_id=application_id, error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération de la candidature")
    
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
            
            # Exécuter les requêtes
            result = await self.db.execute(query)
            applications = list(result.scalars().all())
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar() or 0
            
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
            if not application:
                raise NotFoundError("Candidature non trouvée")
            
            # Mettre à jour les champs fournis
            update_data = application_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(application, field, value)
            
            # Flush pour persister les modifications
            await self.db.flush()
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
            #  PAS de commit ici
            
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
            from app.models.application import ApplicationDocument as ApplicationDocumentModel
            document = ApplicationDocumentModel(
                application_id=document_data.application_id,  # type: ignore
                document_type=document_data.document_type,  # type: ignore
                file_name=document_data.file_name,  # type: ignore
                file_data=file_data,  # type: ignore
                file_size=document_data.file_size,  # type: ignore
                file_type=document_data.file_type  # type: ignore
            )
            
            self.db.add(document)
            #  PAS de commit ici - le endpoint fera le commit
            # Flush pour obtenir l'ID et persister l'objet dans la session
            await self.db.flush()
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
            documents = list(result.scalars().all())
            
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
            file_data_b64 = base64.b64encode(document.file_data).decode('utf-8')  # type: ignore
            
            return ApplicationDocumentWithData(
                id=document.id,  # type: ignore
                application_id=document.application_id,  # type: ignore
                document_type=document.document_type,  # type: ignore
                file_name=document.file_name,  # type: ignore
                file_size=document.file_size,  # type: ignore
                file_type=document.file_type,  # type: ignore
                uploaded_at=document.uploaded_at,  # type: ignore
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
            #  PAS de commit ici
            
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
            status_counts = {str(row[0]): int(row[1]) for row in status_result.fetchall()}
            
            # Compter le total
            total_result = await self.db.execute(select(func.count(Application.id)))
            total = total_result.scalar()
            
            # Compter les documents par type
            doc_type_result = await self.db.execute(
                select(ApplicationDocument.document_type, func.count(ApplicationDocument.id))
                .group_by(ApplicationDocument.document_type)
            )
            doc_type_counts = {str(row[0]): int(row[1]) for row in doc_type_result.fetchall()}
            
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
        """
        Sauvegarder un brouillon de candidature
        
        Args:
            draft_data: Données du brouillon à sauvegarder
            
        Returns:
            ApplicationDraft: Brouillon sauvegardé
            
        Raises:
            ValidationError: Si les données sont invalides
            DatabaseError: Si erreur de base de données
            BusinessLogicError: Pour toute autre erreur métier
        """
        try:
            logger.debug("🔍 Début sauvegarde brouillon", draft_data_keys=list(draft_data.keys()))
            
            # Validation des champs requis
            required_fields = ["user_id", "job_offer_id"]
            for field in required_fields:
                if field not in draft_data:
                    raise ValidationError(
                        f"Champ requis manquant: {field}",
                        field=field,
                        details={"provided_fields": list(draft_data.keys())}
                    )
            
            user_id = draft_data["user_id"]
            job_offer_id = draft_data["job_offer_id"]
            
            logger.debug("🔍 Recherche brouillon existant", user_id=str(user_id), job_offer_id=str(job_offer_id))
            
            # Vérifier si un brouillon existe déjà
            result = await self.db.execute(
                select(ApplicationDraft).where(
                    ApplicationDraft.user_id == user_id,
                    ApplicationDraft.job_offer_id == job_offer_id
                )
            )
            draft = result.scalar_one_or_none()
            
            if draft:
                # Mettre à jour le brouillon existant
                logger.debug("🔄 Mise à jour brouillon existant", user_id=str(user_id), job_offer_id=str(job_offer_id))
                
                # Utilisation de notre utilitaire JSON sécurisé
                parsed_draft_data = JSONDataHandler.safe_parse_json(draft_data, {})
                
                draft.form_data = JSONDataHandler.safe_get_dict_value(parsed_draft_data, "form_data")  # type: ignore
                draft.ui_state = JSONDataHandler.safe_get_dict_value(parsed_draft_data, "ui_state")  # type: ignore
                
                # Flush pour persister les modifications
                await self.db.flush()
                logger.debug("✅ Brouillon mis à jour et flushed")
                
            else:
                # Créer un nouveau brouillon
                logger.debug("🆕 Création nouveau brouillon", user_id=str(user_id), job_offer_id=str(job_offer_id))
                
                # Préparer les données pour la création
                draft_create_data = {
                    "user_id": user_id,
                    "job_offer_id": job_offer_id,
                    "form_data": JSONDataHandler.safe_get_dict_value(draft_data, "form_data"),
                    "ui_state": JSONDataHandler.safe_get_dict_value(draft_data, "ui_state")
                }
                
                draft = ApplicationDraft(**draft_create_data)
                self.db.add(draft)
                
                # Flush pour persister l'objet dans la session
                await self.db.flush()
                logger.debug("✅ Nouveau brouillon créé et flushed")
            
            # Refresh pour obtenir les valeurs mises à jour de la DB
            await self.db.refresh(draft)
            logger.debug("✅ Brouillon refreshed")
            
            #  PAS de commit ici - le commit sera fait par l'endpoint
            
            logger.info("✅ Brouillon sauvegardé avec succès", 
                       user_id=str(draft.user_id), 
                       job_offer_id=str(draft.job_offer_id),
                       has_form_data=draft.form_data is not None,
                       has_ui_state=draft.ui_state is not None)
            return draft
            
        except ValidationError:
            # Propager les erreurs de validation sans modification
            logger.warning("⚠️ Erreur de validation brouillon", user_id=draft_data.get("user_id"), job_offer_id=draft_data.get("job_offer_id"))
            raise
            
        except Exception as e:
            # Logger avec détails complets pour debugging
            logger.error(
                "❌ Erreur inattendue sauvegarde brouillon", 
                error_type=type(e).__name__,
                error=str(e),
                user_id=draft_data.get("user_id"),
                job_offer_id=draft_data.get("job_offer_id"),
                draft_data_keys=list(draft_data.keys()) if isinstance(draft_data, dict) else "N/A",
                exc_info=True
            )
            raise DatabaseError(
                "Erreur lors de la sauvegarde du brouillon",
                operation="save_draft",
                details={"error_type": type(e).__name__, "error_message": str(e)}
            )
    
    async def get_draft(self, user_id: str, job_offer_id: str) -> Optional[ApplicationDraft]:
        """Récupérer un brouillon de candidature"""
        logger = structlog.get_logger(__name__)
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
                #  PAS de commit ici
                logger.info("Brouillon supprimé", user_id=user_id, job_offer_id=job_offer_id)
        except ValueError:
            raise ValidationError("IDs invalides")
        except Exception as e:
            logger.error("Erreur suppression brouillon", error=str(e))
            raise BusinessLogicError("Erreur lors de la suppression du brouillon")

    async def get_application_draft(self, application_id: str, user_id: str) -> Optional[ApplicationDraft]:
        """Récupérer le brouillon lié à une candidature (via son job_offer_id)."""
        logger = structlog.get_logger(__name__)
        try:
            application = await self.get_application_by_id(application_id)
            if not application:
                raise NotFoundError("Candidature non trouvée")
            return await self.get_draft(user_id=user_id, job_offer_id=str(application.job_offer_id))
        except Exception as e:
            logger.error("Erreur get_application_draft", application_id=application_id, error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération du brouillon")

    async def upsert_application_draft(self, application_id: str, user_id: str, draft_data: "ApplicationDraftUpdate") -> ApplicationDraft:
        """Créer/met à jour le brouillon pour la candidature donnée (basé sur user_id + job_offer_id)."""
        logger = structlog.get_logger(__name__)
        try:
            application = await self.get_application_by_id(application_id)
            if not application:
                raise NotFoundError("Candidature non trouvée")
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
        """Supprimer le brouillon pour la candidature donnée."""
        logger = structlog.get_logger(__name__)
        try:
            application = await self.get_application_by_id(application_id)
            if not application:
                raise NotFoundError("Candidature non trouvée")
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
            return list(result.scalars().all())
        except Exception as e:
            logger.error("Erreur list_application_history", application_id=application_id, error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération de l'historique")

    async def add_application_history(self, application_id: str, item: "ApplicationHistoryCreate", changed_by_user_id: str | None) -> ApplicationHistory:
        """Ajouter une entrée d'historique et éventuellement mettre à jour le statut de la candidature."""
        try:
            application = await self.get_application_by_id(application_id)
            if not application:
                raise NotFoundError("Candidature non trouvée")
                
            history = ApplicationHistory(
                application_id=UUID(application_id),  # type: ignore
                changed_by=UUID(changed_by_user_id) if changed_by_user_id else None,  # type: ignore
                previous_status=item.previous_status or application.status,  # type: ignore
                new_status=item.new_status or application.status,  # type: ignore
                notes=item.notes,  # type: ignore
            )
            self.db.add(history)
            # Mettre à jour le statut de l'application si new_status fourni
            if item.new_status and item.new_status != application.status:  # type: ignore
                application.status = item.new_status  # type: ignore
            #  PAS de commit ici
            await self.db.refresh(history)
            return history
        except Exception as e:
            logger.error("Erreur add_application_history", application_id=application_id, error=str(e))
            raise BusinessLogicError("Erreur lors de l'ajout à l'historique")

    async def get_advanced_statistics(self) -> Dict[str, Any]:
        """Statistiques avancées des candidatures: par statut, par offre, par mois, documents par type."""
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
            logger.error("Erreur statistiques avancées", error=str(e))
            # Retourner une structure vide mais cohérente plutôt que 500
            return {
                "total_applications": 0,
                "status_breakdown": {},
                "by_job_offer": {},
                "by_month": {},
                "documents_by_type": {},
            }
    
    async def get_complete_application_details(
        self,
        application_id: UUID
    ) -> Dict[str, Any]:
        """
        Récupérer les détails complets d'une candidature
        
        Inclut :
        - Informations de la candidature
        - Profil complet du candidat avec documents
        - Détails de l'offre d'emploi avec questions MTP
        - Réponses MTP du candidat
        
        Cette méthode respecte les principes SOLID :
        - Single Responsibility : Récupère uniquement les détails complets
        - Open/Closed : Extensible sans modification
        - Liskov Substitution : Peut être utilisée partout où une méthode de récupération est attendue
        - Interface Segregation : Interface claire et unique
        - Dependency Inversion : Dépend d'abstractions (AsyncSession)
        
        Args:
            application_id: UUID de la candidature
            
        Returns:
            Dict contenant toutes les informations complètes
            
        Raises:
            NotFoundError: Si la candidature n'existe pas
            DatabaseError: En cas d'erreur de base de données
        """
        try:
            logger.info(
                "Récupération détails complets candidature",
                application_id=str(application_id)
            )
            
            # Récupérer la candidature avec toutes les relations chargées (eager loading)
            # Principe : Éviter le problème N+1 queries
            stmt = (
                select(Application)
                .options(
                    joinedload(Application.candidate),  # Charger l'utilisateur
                    selectinload(Application.documents),  # Charger les documents
                )
                .where(Application.id == application_id)
            )
            
            result = await self.db.execute(stmt)
            application = result.unique().scalar_one_or_none()
            
            if not application:
                logger.warning(
                    "Candidature non trouvée",
                    application_id=str(application_id)
                )
                raise NotFoundError(
                    "Candidature non trouvée",
                    resource="Application",
                    resource_id=str(application_id)
                )
            
            # Récupérer le profil candidat
            candidate_profile_stmt = (
                select(CandidateProfile)
                .where(CandidateProfile.user_id == application.candidate_id)
            )
            candidate_profile_result = await self.db.execute(candidate_profile_stmt)
            candidate_profile = candidate_profile_result.scalar_one_or_none()
            
            # Récupérer l'offre d'emploi
            job_offer_stmt = (
                select(JobOffer)
                .where(JobOffer.id == application.job_offer_id)
            )
            job_offer_result = await self.db.execute(job_offer_stmt)
            job_offer = job_offer_result.scalar_one_or_none()
            
            if not job_offer:
                logger.warning(
                    "Offre d'emploi non trouvée",
                    job_offer_id=str(application.job_offer_id)
                )
                raise NotFoundError(
                    "Offre d'emploi associée non trouvée",
                    resource="JobOffer",
                    resource_id=str(application.job_offer_id)
                )
            
            # Construire les détails du candidat
            # Parser les skills et languages si ce sont des chaînes JSON
            skills_value = getattr(candidate_profile, 'skills', None) if candidate_profile else None
            if skills_value and isinstance(skills_value, str):
                try:
                    skills_value = json.loads(skills_value)
                except:
                    skills_value = []
            elif not skills_value:
                skills_value = []
            
            # Note: CandidateProfile n'a pas de champ languages dans la DB actuelle
            # On le récupère depuis le modèle User si disponible
            
            candidate_data = {
                "user_id": str(application.candidate.id),
                "email": application.candidate.email,
                "firstname": application.candidate.first_name,
                "lastname": application.candidate.last_name,
                "phone": application.candidate.phone,
                "address": getattr(candidate_profile, 'address', None) if candidate_profile else None,
                "city": None,  # Pas dans le modèle actuel
                "country": None,  # Pas dans le modèle actuel
                "birth_date": getattr(candidate_profile, 'birth_date', None) if candidate_profile else None,
                "nationality": None,  # Pas dans le modèle actuel
                "current_job_title": getattr(candidate_profile, 'current_position', None) if candidate_profile else None,
                "years_of_experience": getattr(candidate_profile, 'years_experience', None) if candidate_profile else None,
                "education_level": getattr(candidate_profile, 'education', None) if candidate_profile else None,
                "skills": skills_value,
                "languages": [],  # Pas dans le modèle actuel
                "documents": []
            }
            
            # Ajouter les documents téléversés
            for doc in application.documents:
                candidate_data["documents"].append({
                    "id": str(doc.id),
                    "document_type": doc.document_type,
                    "file_name": doc.file_name,
                    "file_path": f"/api/v1/applications/{application_id}/documents/{doc.id}/download",
                    "file_size": doc.file_size,
                    "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None
                })
            
            # Construire les détails de l'offre
            # Construire salary_range à partir de salary_min et salary_max
            salary_min = getattr(job_offer, 'salary_min', None)
            salary_max = getattr(job_offer, 'salary_max', None)
            salary_range = None
            if salary_min and salary_max:
                salary_range = f"{salary_min} - {salary_max} FCFA"
            elif salary_min:
                salary_range = f"À partir de {salary_min} FCFA"
            elif salary_max:
                salary_range = f"Jusqu'à {salary_max} FCFA"
            
            # Utiliser application_deadline ou date_limite
            deadline_val = getattr(job_offer, 'application_deadline', None) or getattr(job_offer, 'date_limite', None)
            
            job_offer_data = {
                "id": str(job_offer.id),
                "title": job_offer.title,
                "description": job_offer.description,
                "location": job_offer.location,
                "contract_type": job_offer.contract_type,
                "salary_range": salary_range,
                "requirements": job_offer.requirements or [],
                "responsibilities": job_offer.responsibilities or [],
                "benefits": job_offer.benefits or [],
                "status": job_offer.status,
                "offer_status": getattr(job_offer, 'offer_status', 'tous'),
                "created_at": job_offer.created_at.isoformat() if job_offer.created_at else None,
                "updated_at": job_offer.updated_at.isoformat() if job_offer.updated_at else None,
                "deadline": deadline_val.isoformat() if deadline_val else None,
                "questions_mtp": None
            }
            
            # Ajouter les questions MTP si elles existent
            questions_mtp_value = getattr(job_offer, 'questions_mtp', None)
            if questions_mtp_value is not None:
                questions_mtp = questions_mtp_value
                if isinstance(questions_mtp, str):
                    questions_mtp = json.loads(questions_mtp)
                
                job_offer_data["questions_mtp"] = {
                    "questions_metier": questions_mtp.get("questions_metier", []),
                    "questions_talent": questions_mtp.get("questions_talent", []),
                    "questions_paradigme": questions_mtp.get("questions_paradigme", [])
                }
            
            # Construire les réponses MTP du candidat
            mtp_answers_data = None
            mtp_answers_value = getattr(application, 'mtp_answers', None)
            if mtp_answers_value is not None:
                mtp_answers = mtp_answers_value
                if isinstance(mtp_answers, str):
                    mtp_answers = json.loads(mtp_answers)
                
                mtp_answers_data = {
                    "reponses_metier": mtp_answers.get("reponses_metier", []),
                    "reponses_talent": mtp_answers.get("reponses_talent", []),
                    "reponses_paradigme": mtp_answers.get("reponses_paradigme", [])
                }
            
            # Construire les informations de référence
            reference_data = None
            ref_entreprise_value = getattr(application, 'ref_entreprise', None)
            ref_fullname_value = getattr(application, 'ref_fullname', None)
            if ref_entreprise_value or ref_fullname_value:
                reference_data = {
                    "entreprise": application.ref_entreprise,
                    "fullname": application.ref_fullname,
                    "email": application.ref_mail,
                    "contact": application.ref_contact
                }
            
            # Construire la réponse complète
            availability_start_value = getattr(application, 'availability_start', None)
            complete_details = {
                "application_id": str(application.id),
                "status": application.status,
                "created_at": application.created_at.isoformat() if application.created_at else None,
                "updated_at": application.updated_at.isoformat() if application.updated_at else None,
                "reference_contacts": application.reference_contacts,
                "availability_start": availability_start_value.isoformat() if availability_start_value else None,
                "has_been_manager": application.has_been_manager,
                "reference": reference_data,
                "candidate": candidate_data,
                "job_offer": job_offer_data,
                "mtp_answers": mtp_answers_data
            }
            
            logger.info(
                "Détails complets récupérés avec succès",
                application_id=str(application_id),
                candidate_email=application.candidate.email,
                job_title=job_offer.title
            )
            
            return complete_details
            
        except NotFoundError:
            # Propager l'erreur NotFoundError sans modification
            raise
            
        except Exception as e:
            logger.error(
                "Erreur récupération détails complets",
                application_id=str(application_id),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            raise DatabaseError(
                "Erreur lors de la récupération des détails complets de la candidature",
                operation="get_complete_application_details",
                details={
                    "application_id": str(application_id),
                    "error": str(e)
                }
            )
