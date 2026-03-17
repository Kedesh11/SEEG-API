"""
Service de gestion des candidatures
"""
import structlog
import json
from typing import Optional, List, Dict, Any
from app.utils.json_utils import JSONDataHandler
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from uuid import UUID
import base64

from app.schemas.application import (
    ApplicationCreate, ApplicationUpdate, ApplicationDocumentCreate, 
    ApplicationDocumentUpdate, ApplicationDocumentWithData,
    ApplicationDraftUpdate, ApplicationHistoryCreate
)
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError, DatabaseError

logger = structlog.get_logger(__name__)

class ApplicationService:
    """Service de gestion des candidatures"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
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
        logger = structlog.get_logger(__name__)
        
        # Récupérer l'offre avec ses questions MTP
        query = {"_id": ObjectId(job_offer_id)} if len(str(job_offer_id)) == 24 else {"_id": str(job_offer_id)}
        job_offer = await self.db.job_offers.find_one(query)
        
        if job_offer is None:
            raise ValidationError("Offre d'emploi introuvable")
        
        # Si l'offre n'a pas de questions MTP, pas de validation nécessaire
        questions_mtp = job_offer.get('questions_mtp')
        if not questions_mtp:
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
    
    async def create_application(self, application_data: ApplicationCreate, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Créer une nouvelle candidature avec validation des questions MTP et documents.
        
        Le système valide automatiquement:
        1. Qu'il n'existe pas déjà une candidature pour cette offre
        2. Que le nombre de questions MTP respecte les limites du type de candidat
        3. Upload automatique des documents fournis (si présents)
        
        Args:
            application_data: Données de la candidature (avec documents optionnels)
            user_id: ID de l'utilisateur (optionnel)
            
        Returns:
            Application: La candidature créée avec ses documents
            
        Raises:
            ValidationError: Si validation échoue (doublon, limites MTP, documents invalides)
            BusinessLogicError: Si erreur lors de la création
        """
        logger = structlog.get_logger(__name__)
        try:
            # Vérifier qu'il n'y a pas déjà une candidature pour ce job
            existing_application = await self.db.applications.find_one({
                "candidate_id": str(application_data.candidate_id),
                "job_offer_id": str(application_data.job_offer_id)
            })
            
            if existing_application:
                raise ValidationError("Une candidature existe déjà pour cette offre d'emploi")
            
            # Valider que les réponses MTP correspondent aux questions de l'offre
            # Si l'offre a des questions MTP, les réponses sont obligatoires
            await self._validate_mtp_answers(
                application_data.job_offer_id,
                application_data
            )
            
            # Extraire les documents avant de créer l'application
            documents_to_upload = application_data.documents
            
            # Créer la candidature (sans les documents dans le dict)
            from datetime import datetime
            import uuid
            
            application_dict = application_data.dict(exclude={'documents'})
            application_dict["_id"] = str(uuid.uuid4())
            application_dict["candidate_id"] = str(application_dict.get("candidate_id"))
            application_dict["job_offer_id"] = str(application_dict.get("job_offer_id"))
            application_dict["created_at"] = datetime.utcnow()
            application_dict["updated_at"] = datetime.utcnow()
            
            if "status" not in application_dict or not application_dict["status"]:
                application_dict["status"] = "soumis"
                
            await self.db.applications.insert_one(application_dict)
            application = application_dict
            
            logger.info("Candidature créée", 
                       application_id=str(application["_id"]), 
                       candidate_id=str(application["candidate_id"]),
                       has_documents=documents_to_upload is not None and len(documents_to_upload) > 0)
            
            # Upload des documents si fournis
            if documents_to_upload:
                uploaded_count = 0
                for doc_data in documents_to_upload:
                    try:
                        # Valider le document
                        if not isinstance(doc_data, dict):
                            logger.warning("Document invalide (pas un dict)", doc_data_type=type(doc_data).__name__)
                            continue
                        
                        document_type = doc_data.get('document_type', 'certificats')
                        file_name = doc_data.get('file_name', 'document.pdf')
                        file_data_b64 = doc_data.get('file_data')
                        
                        if not file_data_b64:
                            logger.warning("Document sans données (file_data manquant)", 
                                         document_type=document_type, 
                                         file_name=file_name)
                            continue
                        
                        # Décoder pour obtenir la taille
                        try:
                            file_content = base64.b64decode(file_data_b64)
                            file_size = len(file_content)
                            
                            # Validation PDF
                            if not file_content.startswith(b'%PDF'):
                                logger.warning("Document n'est pas un PDF valide", 
                                             document_type=document_type,
                                             file_name=file_name)
                                continue
                            
                            # Validation taille (max 10MB)
                            MAX_FILE_SIZE = 10 * 1024 * 1024
                            if file_size > MAX_FILE_SIZE:
                                logger.warning("Document trop volumineux", 
                                             document_type=document_type,
                                             file_name=file_name,
                                             size_mb=f"{file_size / (1024 * 1024):.2f}")
                                continue
                            
                        except Exception as decode_error:
                            logger.warning("Erreur décodage base64", 
                                         document_type=document_type,
                                         file_name=file_name,
                                         error=str(decode_error))
                            continue
                        
                        # Créer le document
                        document_create = ApplicationDocumentCreate(
                            application_id=application["_id"],
                            document_type=document_type,
                            file_name=file_name,
                            file_data=file_data_b64,
                            file_size=file_size,
                            file_type="application/pdf"
                        )
                        
                        document = await self.create_document(document_create)
                        uploaded_count += 1
                        
                        logger.info("Document uploadé", 
                                   application_id=str(application["_id"]),
                                   document_id=str(document.get("_id", document.get("id"))),
                                   document_type=document_type,
                                   file_name=file_name)
                        
                    except Exception as doc_error:
                        logger.error("Erreur upload document individuel", 
                                   application_id=str(application["_id"]),
                                   error=str(doc_error),
                                   document_data=doc_data)
                        # Continuer avec les autres documents
                        continue
                
                logger.info("Documents uploadés avec la candidature", 
                           application_id=str(application["_id"]),
                           total_uploaded=uploaded_count,
                           total_provided=len(documents_to_upload))
            
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
    
    async def get_application_by_id(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Récupérer une candidature par son ID avec cache"""
        from app.core.cache import cache_application
        
        @cache_application(expire=600)  # Cache 10 minutes
        async def _get_application(app_id: str):
            try:
                query = {"_id": ObjectId(app_id)} if len(app_id) == 24 else {"_id": app_id}
                application = await self.db.applications.find_one(query)
                
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
    
    async def get_application_with_relations(self, application_id: str) -> Optional[Dict[str, Any]]:
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
    ) -> tuple[List[Dict[str, Any]], int]:
        """Récupérer la liste des candidatures avec filtres"""
        try:
            filter_query = {}
            if status_filter:
                filter_query["status"] = status_filter
            if job_offer_id:
                filter_query["job_offer_id"] = str(job_offer_id)
            if candidate_id:
                filter_query["candidate_id"] = str(candidate_id)
            
            cursor = self.db.applications.find(filter_query).skip(skip).limit(limit)
            applications = await cursor.to_list(length=limit)
            
            total = await self.db.applications.count_documents(filter_query)
            
            return applications, total
        except ValueError as e:
            raise ValidationError("Paramètres de filtrage invalides")
        except Exception as e:
            logger.error("Erreur récupération candidatures", error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération des candidatures")
    
    async def update_application(self, application_id: str, application_data: ApplicationUpdate) -> Dict[str, Any]:
        """Mettre à jour une candidature"""
        try:
            update_data = application_data.dict(exclude_unset=True)
            from datetime import datetime
            update_data["updated_at"] = datetime.utcnow()
            
            query = {"_id": ObjectId(application_id)} if len(application_id) == 24 else {"_id": application_id}
            
            result = await self.db.applications.update_one(
                query,
                {"$set": update_data}
            )
            
            if result.matched_count == 0:
                raise NotFoundError("Candidature non trouvée")
            
            application = await self.get_application_by_id(application_id)
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
            query = {"_id": ObjectId(application_id)} if len(application_id) == 24 else {"_id": application_id}
            result = await self.db.applications.delete_one(query)
            
            if result.deleted_count == 0:
                raise NotFoundError("Candidature non trouvée")
            
            logger.info("Candidature supprimée", application_id=application_id)
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur suppression candidature", application_id=application_id, error=str(e))
            raise BusinessLogicError("Erreur lors de la suppression de la candidature")
    
    # Méthodes pour les documents PDF
    async def create_document(self, document_data: ApplicationDocumentCreate) -> Dict[str, Any]:
        """Créer un nouveau document PDF"""
        try:
            # Vérifier que l'application existe
            await self.get_application_by_id(str(document_data.application_id))
            
            # Décoder les données base64
            file_data = base64.b64decode(document_data.file_data)
            
            # Créer le document
            import uuid
            from datetime import datetime
            doc_id = str(uuid.uuid4())
            document_dict = {
                "_id": doc_id,
                "application_id": str(document_data.application_id),
                "document_type": document_data.document_type,
                "file_name": document_data.file_name,
                "file_data": file_data,
                "file_size": document_data.file_size,
                "file_type": document_data.file_type,
                "uploaded_at": datetime.utcnow()
            }
            
            await self.db.application_documents.insert_one(document_dict)
            
            logger.info("Document créé", document_id=doc_id, application_id=str(document_data.application_id))
            return document_dict
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur création document", error=str(e))
            raise BusinessLogicError("Erreur lors de la création du document")
    
    async def get_application_documents(
        self, 
        application_id: str, 
        document_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Récupérer les documents d'une candidature"""
        try:
            # Vérifier que l'application existe
            await self.get_application_by_id(application_id)
            
            query = {"application_id": str(application_id)}
            
            if document_type:
                query["document_type"] = document_type
            
            cursor = self.db.application_documents.find(query, {"file_data": 0})
            documents = await cursor.to_list(length=None)
            
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
    ) -> Optional[Dict[str, Any]]:
        """Récupérer un document avec ses données binaires"""
        try:
            query = {"_id": document_id, "application_id": application_id}
            if len(document_id) == 24:
                query["_id"] = ObjectId(document_id)
                
            document = await self.db.application_documents.find_one(query)
            
            if not document:
                raise NotFoundError("Document non trouvé")
            
            # Encoder les données en base64 pour la réponse
            file_data_b64 = base64.b64encode(document["file_data"]).decode('utf-8')
            
            document["file_data"] = file_data_b64
            document["id"] = document.pop("_id", document_id)
            return document
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
            
            query = {"_id": document_id, "application_id": application_id}
            if len(document_id) == 24:
                query["_id"] = ObjectId(document_id)
                
            result = await self.db.application_documents.delete_one(query)
            
            if result.deleted_count == 0:
                raise NotFoundError("Document non trouvé")
            
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
            status_pipeline = [
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ]
            status_cursor = self.db.applications.aggregate(status_pipeline)
            status_counts = {str(doc["_id"]): int(doc["count"]) async for doc in status_cursor if doc.get("_id")}
            
            # Compter le total
            total = await self.db.applications.count_documents({})
            
            # Compter les documents par type
            doc_type_pipeline = [
                {"$group": {"_id": "$document_type", "count": {"$sum": 1}}}
            ]
            doc_type_cursor = self.db.application_documents.aggregate(doc_type_pipeline)
            doc_type_counts = {str(doc["_id"]): int(doc["count"]) async for doc in doc_type_cursor if doc.get("_id")}
            
            return {
                "total_applications": total,
                "status_breakdown": status_counts,
                "document_types": doc_type_counts
            }
        except Exception as e:
            logger.error("Erreur récupération statistiques", error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération des statistiques")
    
    # Méthodes pour les brouillons (inchangées)
    async def save_draft(self, draft_data: dict) -> Dict[str, Any]:
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
            
            user_id = str(draft_data["user_id"])
            job_offer_id = str(draft_data["job_offer_id"])
            
            logger.debug("🔍 Recherche brouillon existant", user_id=user_id, job_offer_id=job_offer_id)
            
            query = {"user_id": user_id, "job_offer_id": job_offer_id}
            
            import uuid
            from datetime import datetime
            import pymongo
            
            parsed_draft_data = JSONDataHandler.safe_parse_json(draft_data, {})
            form_data = JSONDataHandler.safe_get_dict_value(parsed_draft_data, "form_data")
            ui_state = JSONDataHandler.safe_get_dict_value(parsed_draft_data, "ui_state")
            
            update_data = {
                "$set": {
                    "user_id": user_id,
                    "job_offer_id": job_offer_id,
                    "form_data": form_data,
                    "ui_state": ui_state,
                    "updated_at": datetime.utcnow()
                },
                "$setOnInsert": {
                    "_id": str(uuid.uuid4()),
                    "created_at": datetime.utcnow()
                }
            }
            
            draft = await self.db.application_drafts.find_one_and_update(
                query,
                update_data,
                upsert=True,
                return_document=pymongo.ReturnDocument.AFTER
            )
            
            logger.info("✅ Brouillon sauvegardé avec succès", 
                       user_id=user_id, 
                       job_offer_id=job_offer_id,
                       has_form_data=form_data is not None,
                       has_ui_state=ui_state is not None)
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
    
    async def get_draft(self, user_id: str, job_offer_id: str) -> Optional[Dict[str, Any]]:
        """Récupérer un brouillon de candidature"""
        logger = structlog.get_logger(__name__)
        try:
            query = {"user_id": str(user_id), "job_offer_id": str(job_offer_id)}
            return await self.db.application_drafts.find_one(query)
        except ValueError:
            raise ValidationError("IDs invalides")
        except Exception as e:
            logger.error("Erreur récupération brouillon", error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération du brouillon")
    
    async def delete_draft(self, user_id: str, job_offer_id: str) -> None:
        """Supprimer un brouillon de candidature"""
        try:
            query = {"user_id": str(user_id), "job_offer_id": str(job_offer_id)}
            result = await self.db.application_drafts.delete_one(query)
            
            if result.deleted_count > 0:
                logger.info("Brouillon supprimé", user_id=user_id, job_offer_id=job_offer_id)
        except ValueError:
            raise ValidationError("IDs invalides")
        except Exception as e:
            logger.error("Erreur suppression brouillon", error=str(e))
            raise BusinessLogicError("Erreur lors de la suppression du brouillon")

    async def get_application_draft(self, application_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Récupérer le brouillon lié à une candidature (via son job_offer_id)."""
        logger = structlog.get_logger(__name__)
        try:
            application = await self.get_application_by_id(application_id)
            if not application:
                raise NotFoundError("Candidature non trouvée")
            return await self.get_draft(user_id=user_id, job_offer_id=str(application.get("job_offer_id")))
        except Exception as e:
            logger.error("Erreur get_application_draft", application_id=application_id, error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération du brouillon")

    async def upsert_application_draft(self, application_id: str, user_id: str, draft_data: "ApplicationDraftUpdate") -> Dict[str, Any]:
        """Créer/met à jour le brouillon pour la candidature donnée (basé sur user_id + job_offer_id)."""
        logger = structlog.get_logger(__name__)
        try:
            application = await self.get_application_by_id(application_id)
            if not application:
                raise NotFoundError("Candidature non trouvée")
            payload = {
                "user_id": user_id,
                "job_offer_id": str(application.get("job_offer_id")),
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
            await self.delete_draft(user_id=user_id, job_offer_id=str(application.get("job_offer_id")))
        except Exception as e:
            logger.error("Erreur delete_application_draft", application_id=application_id, error=str(e))
            raise BusinessLogicError("Erreur lors de la suppression du brouillon")

    async def list_application_history(self, application_id: str) -> List[Dict[str, Any]]:
        """Lister l'historique des statuts d'une candidature."""
        try:
            import pymongo
            await self.get_application_by_id(application_id)
            cursor = self.db.application_history.find({"application_id": str(application_id)}).sort("changed_at", pymongo.DESCENDING)
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error("Erreur list_application_history", application_id=application_id, error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération de l'historique")

    async def add_application_history(self, application_id: str, item: "ApplicationHistoryCreate", changed_by_user_id: str | None) -> Dict[str, Any]:
        """Ajouter une entrée d'historique et éventuellement mettre à jour le statut de la candidature."""
        try:
            application = await self.get_application_by_id(application_id)
            if not application:
                raise NotFoundError("Candidature non trouvée")
                
            import uuid
            from datetime import datetime
            from bson import ObjectId
            
            history_dict = {
                "_id": str(uuid.uuid4()),
                "application_id": str(application_id),
                "changed_by": str(changed_by_user_id) if changed_by_user_id else None,
                "previous_status": item.previous_status or application.get("status"),
                "new_status": item.new_status or application.get("status"),
                "notes": item.notes,
                "changed_at": datetime.utcnow()
            }
            await self.db.application_history.insert_one(history_dict)
            
            # Mettre à jour le statut de l'application si new_status fourni
            if item.new_status and item.new_status != application.get("status"):
                query = {"_id": ObjectId(application_id)} if len(application_id) == 24 else {"_id": application_id}
                await self.db.applications.update_one(query, {"$set": {"status": item.new_status, "updated_at": datetime.utcnow()}})
            
            return history_dict
        except Exception as e:
            logger.error("Erreur add_application_history", application_id=application_id, error=str(e))
            raise BusinessLogicError("Erreur lors de l'ajout à l'historique")

    async def get_advanced_statistics(self) -> Dict[str, Any]:
        """Statistiques avancées des candidatures: par statut, par offre, par mois, documents par type."""
        try:
            total = await self.db.applications.count_documents({})
            
            # Totaux par statut
            status_pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
            status_cursor = self.db.applications.aggregate(status_pipeline)
            status_breakdown = {str(doc["_id"]): doc["count"] async for doc in status_cursor if doc.get("_id")}

            # Par offre (counts)
            job_pipeline = [{"$group": {"_id": "$job_offer_id", "count": {"$sum": 1}}}]
            job_cursor = self.db.applications.aggregate(job_pipeline)
            by_job_offer = {str(doc["_id"]): doc["count"] async for doc in job_cursor if doc.get("_id")}

            # Par mois (dateToString)
            month_pipeline = [
                {"$match": {"created_at": {"$ne": None}}},
                {"$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m", "date": "$created_at"}},
                    "count": {"$sum": 1}
                }},
                {"$sort": {"_id": 1}}
            ]
            month_cursor = self.db.applications.aggregate(month_pipeline)
            by_month = {f"{doc['_id']}-01": doc["count"] async for doc in month_cursor if doc.get("_id")}

            # Documents par type
            doc_pipeline = [{"$group": {"_id": "$document_type", "count": {"$sum": 1}}}]
            doc_cursor = self.db.application_documents.aggregate(doc_pipeline)
            documents_by_type = {str(doc["_id"]): doc["count"] async for doc in doc_cursor if doc.get("_id")}

            return {
                "total_applications": total,
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
        application_id: str
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
        - Dependency Inversion : Dépend d'abstractions (AsyncIOMotorDatabase)
        
        Args:
            application_id: UUID ou ObjectId de la candidature
            
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
            
            from bson import ObjectId
            query = {"_id": ObjectId(application_id)} if len(str(application_id)) == 24 else {"_id": str(application_id)}
            application = await self.db.applications.find_one(query)
            
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
            
            # Charger les documents
            documents_cursor = self.db.application_documents.find({"application_id": str(application["_id"])})
            documents = await documents_cursor.to_list(length=None)
            
            # Charger l'utilisateur
            candidate_id = application.get("candidate_id")
            candidate_query = {"_id": ObjectId(candidate_id)} if candidate_id and len(str(candidate_id)) == 24 else {"_id": str(candidate_id)}
            candidate = await self.db.users.find_one(candidate_query) if candidate_id else None
            
            # Récupérer le profil candidat
            candidate_profile = await self.db.candidate_profiles.find_one({"user_id": str(candidate_id)}) if candidate_id else None
            
            # Récupérer l'offre d'emploi
            job_offer_id = application.get("job_offer_id")
            job_offer_query = {"_id": ObjectId(job_offer_id)} if job_offer_id and len(str(job_offer_id)) == 24 else {"_id": str(job_offer_id)}
            job_offer = await self.db.job_offers.find_one(job_offer_query) if job_offer_id else None
            
            if not job_offer:
                logger.warning(
                    "Offre d'emploi non trouvée",
                    job_offer_id=str(application.get("job_offer_id"))
                )
                raise NotFoundError(
                    "Offre d'emploi associée non trouvée",
                    resource="JobOffer",
                    resource_id=str(application.get("job_offer_id"))
                )
            
            # Construire les détails du candidat
            skills_value = candidate_profile.get("skills", []) if candidate_profile else []
            if isinstance(skills_value, str):
                try:
                    skills_value = json.loads(skills_value)
                except:
                    skills_value = []
                    
            candidate_data = {
                "user_id": str(candidate.get("_id")) if candidate else None,
                "email": candidate.get("email") if candidate else None,
                "firstname": candidate.get("first_name") if candidate else None,
                "lastname": candidate.get("last_name") if candidate else None,
                "phone": candidate.get("phone") if candidate else None,
                "address": candidate_profile.get("address") if candidate_profile else None,
                "city": None,
                "country": None,
                "birth_date": candidate_profile.get("birth_date") if candidate_profile else None,
                "nationality": None,
                "current_job_title": candidate_profile.get("current_position") if candidate_profile else None,
                "years_of_experience": candidate_profile.get("years_experience") if candidate_profile else None,
                "education_level": candidate_profile.get("education") if candidate_profile else None,
                "skills": skills_value,
                "languages": [],
                "documents": []
            }
            
            for doc in documents:
                candidate_data["documents"].append({
                    "id": str(doc.get("_id", doc.get("id"))),
                    "document_type": doc.get("document_type"),
                    "file_name": doc.get("file_name"),
                    "file_path": f"/api/v1/applications/{application_id}/documents/{str(doc.get('_id', doc.get('id')))}/download",
                    "file_size": doc.get("file_size"),
                    "uploaded_at": doc.get("uploaded_at").isoformat() if doc.get("uploaded_at") else None
                })
            
            # Construire les détails de l'offre
            salary_min = job_offer.get("salary_min")
            salary_max = job_offer.get("salary_max")
            salary_range = None
            if salary_min and salary_max:
                salary_range = f"{salary_min} - {salary_max} FCFA"
            elif salary_min:
                salary_range = f"À partir de {salary_min} FCFA"
            elif salary_max:
                salary_range = f"Jusqu'à {salary_max} FCFA"
                
            deadline_val = job_offer.get("application_deadline") or job_offer.get("date_limite")
            
            job_offer_data = {
                "id": str(job_offer.get("_id", job_offer.get("id"))),
                "title": job_offer.get("title"),
                "description": job_offer.get("description"),
                "location": job_offer.get("location"),
                "contract_type": job_offer.get("contract_type"),
                "salary_range": salary_range,
                "requirements": job_offer.get("requirements", []),
                "responsibilities": job_offer.get("responsibilities", []),
                "benefits": job_offer.get("benefits", []),
                "status": job_offer.get("status"),
                "offer_status": job_offer.get("offer_status", "tous"),
                "created_at": job_offer.get("created_at").isoformat() if job_offer.get("created_at") else None,
                "updated_at": job_offer.get("updated_at").isoformat() if job_offer.get("updated_at") else None,
                "deadline": deadline_val.isoformat() if deadline_val else None,
                "questions_mtp": None
            }
            
            questions_mtp = job_offer.get("questions_mtp")
            if questions_mtp is not None:
                if isinstance(questions_mtp, str):
                    try:
                        questions_mtp = json.loads(questions_mtp)
                    except:
                        questions_mtp = {}
                
                job_offer_data["questions_mtp"] = {
                    "questions_metier": questions_mtp.get("questions_metier", []),
                    "questions_talent": questions_mtp.get("questions_talent", []),
                    "questions_paradigme": questions_mtp.get("questions_paradigme", [])
                }
            
            mtp_answers_data = None
            mtp_answers = application.get("mtp_answers")
            if mtp_answers is not None:
                if isinstance(mtp_answers, str):
                    try:
                        mtp_answers = json.loads(mtp_answers)
                    except:
                        mtp_answers = {}
                
                mtp_answers_data = {
                    "reponses_metier": mtp_answers.get("reponses_metier", []),
                    "reponses_talent": mtp_answers.get("reponses_talent", []),
                    "reponses_paradigme": mtp_answers.get("reponses_paradigme", [])
                }
            
            reference_data = None
            if application.get("ref_entreprise") or application.get("ref_fullname"):
                reference_data = {
                    "entreprise": application.get("ref_entreprise"),
                    "fullname": application.get("ref_fullname"),
                    "email": application.get("ref_mail"),
                    "contact": application.get("ref_contact")
                }
            
            availability_start = application.get("availability_start")
            
            complete_details = {
                "application_id": str(application.get("_id", application.get("id"))),
                "status": application.get("status"),
                "created_at": application.get("created_at").isoformat() if application.get("created_at") else None,
                "updated_at": application.get("updated_at").isoformat() if application.get("updated_at") else None,
                "reference_contacts": application.get("reference_contacts"),
                "availability_start": availability_start.isoformat() if availability_start else None,
                "has_been_manager": application.get("has_been_manager"),
                "reference": reference_data,
                "candidate": candidate_data,
                "job_offer": job_offer_data,
                "mtp_answers": mtp_answers_data
            }
            
            logger.info(
                "Détails complets récupérés avec succès",
                application_id=str(application_id),
                candidate_email=candidate.get("email") if candidate else None,
                job_title=job_offer.get("title")
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
