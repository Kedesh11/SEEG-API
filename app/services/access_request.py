"""
Service de gestion des demandes d'accès à la plateforme.
"""
from typing import Optional, List, Tuple, cast, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone
import structlog

from app.schemas.access_request import AccessRequestCreate, AccessRequestUpdate
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError, UnauthorizedError

logger = structlog.get_logger(__name__)


class AccessRequestService:
    """Service de gestion des demandes d'accès."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def create_access_request(
        self,
        user_id: Any,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        matricule: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Créer une nouvelle demande d'accès.
        
        Appelé automatiquement lors de l'inscription d'un candidat interne 
        sans email @seeg-gabon.com.
        
        Args:
            user_id: ID de l'utilisateur
            email: Email du demandeur
            first_name: Prénom
            last_name: Nom
            phone: Téléphone
            matricule: Matricule SEEG
            
        Returns:
            Dict[str, Any]: La demande créée
            
        Raises:
            ValidationError: Si les données sont invalides
            BusinessLogicError: Si erreur lors de la création
        """
        try:
            # Vérifier qu'il n'existe pas déjà une demande pending pour cet utilisateur
            user_id_str = str(user_id)
            existing_request = await self.db.access_requests.find_one({
                "user_id": user_id_str,
                "status": "pending"
            })
            
            if existing_request:
                logger.warning("Demande d'accès déjà existante", user_id=user_id_str)
                existing_request["id"] = str(existing_request["_id"])
                return existing_request
            
            # Créer la demande
            access_request = {
                "user_id": user_id_str,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "matricule": matricule,
                "request_type": "internal_no_seeg_email",
                "status": "pending",
                "viewed": False,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            result = await self.db.access_requests.insert_one(access_request)
            access_request["id"] = str(result.inserted_id)
            access_request["_id"] = result.inserted_id
            
            logger.info("Demande d'accès créée", 
                       request_id=access_request["id"],
                       user_id=user_id_str,
                       email=email,
                       matricule=matricule)
            
            return access_request
            
        except Exception as e:
            logger.error("Erreur création demande d'accès", error=str(e), user_id=str(user_id))
            raise BusinessLogicError("Erreur lors de la création de la demande d'accès")
    
    async def get_all_requests(
        self,
        status_filter: Optional[str] = None,
        viewed_filter: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Dict[str, Any]], int, int, int]:
        try:
            filter_query = {}
            if status_filter:
                filter_query["status"] = status_filter
            if viewed_filter is not None:
                filter_query["viewed"] = viewed_filter
            
            # Exécuter les requêtes
            cursor = self.db.access_requests.find(filter_query).sort("created_at", -1).skip(skip).limit(limit)
            requests = await cursor.to_list(length=limit)
            total = await self.db.access_requests.count_documents(filter_query)
            
            # Compter les demandes pending
            pending_count = await self.db.access_requests.count_documents({"status": "pending"})
            
            # Compter les demandes non vues (pour le badge)
            unviewed_count = await self.db.access_requests.count_documents({
                "status": "pending",
                "viewed": False
            })
            
            for req in requests:
                req["id"] = str(req["_id"])
            
            logger.info("Demandes d'accès récupérées",
                       total=total,
                       pending=pending_count,
                       unviewed=unviewed_count)
            
            return requests, total, pending_count, unviewed_count
            
        except Exception as e:
            logger.error("Erreur récupération demandes d'accès", error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération des demandes")
    
    async def get_request_by_id(self, request_id: Any) -> Optional[Dict[str, Any]]:
        """Récupérer une demande d'accès par son ID."""
        try:
            query = {"_id": ObjectId(request_id)} if len(str(request_id)) == 24 else {"_id": str(request_id)}
            request = await self.db.access_requests.find_one(query)
            if request:
                request["id"] = str(request["_id"])
            return request
        except Exception as e:
            logger.error("Erreur récupération demande", request_id=str(request_id), error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération de la demande")
    
    async def approve_request(
        self,
        request_id: Any,
        reviewer_id: Any,
    ) -> Dict[str, Any]:
        """Approuver une demande d'accès (pending -> approved)."""
        try:
            # Récupérer la demande
            request = await self.get_request_by_id(request_id)
            
            if not request:
                raise NotFoundError("Demande d'accès non trouvée")
            
            current_status = request.get("status")
            if current_status != 'pending':
                raise ValidationError(f"La demande a déjà été traitée (statut: {current_status})")
            
            # Mettre à jour le statut de l'utilisateur
            user_id = request.get("user_id")
            user_query = {"_id": ObjectId(user_id)} if len(str(user_id)) == 24 else {"_id": str(user_id)}
            await self.db.users.update_one(
                user_query,
                {"$set": {
                    "statut": "actif",
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            
            # Mettre à jour la demande
            await self.db.access_requests.update_one(
                {"_id": request["_id"]},
                {"$set": {
                    "status": "approved",
                    "reviewed_at": datetime.now(timezone.utc),
                    "reviewed_by": str(reviewer_id),
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            
            request = await self.get_request_by_id(request_id)
            
            logger.info("Demande d'accès approuvée",
                       request_id=str(request_id),
                       user_id=str(user_id),
                       reviewer_id=str(reviewer_id))
            
            return request
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error("Erreur approbation demande", request_id=str(request_id), error=str(e))
            raise BusinessLogicError("Erreur lors de l'approbation de la demande")
    
    async def reject_request(
        self,
        request_id: Any,
        reviewer_id: Any,
        rejection_reason: str,
    ) -> Dict[str, Any]:
        """
        Refuser une demande d'accès.
        
        Actions:
        1. Vérifier que la demande existe et est 'pending'
        2. Vérifier que le motif fait au moins 20 caractères
        3. Mettre à jour users.statut = 'bloqué'
        4. Mettre à jour access_requests.status = 'rejected'
        5. Enregistrer rejection_reason, reviewed_at et reviewed_by
        
        Args:
            request_id: ID de la demande
            reviewer_id: ID du recruteur qui refuse
            rejection_reason: Motif du refus (min 20 caractères)
            
        Returns:
            AccessRequest: La demande mise à jour
            
        Raises:
            NotFoundError: Si la demande n'existe pas
            ValidationError: Si la demande n'est pas 'pending' ou motif trop court
            BusinessLogicError: Si erreur lors du traitement
        """
        try:
            # Valider le motif
            if len(rejection_reason.strip()) < 20:
                raise ValidationError("Le motif de refus doit contenir au moins 20 caractères")
            
            # Récupérer la demande
            request = await self.get_request_by_id(request_id)
            
            if not request:
                raise NotFoundError("Demande d'accès non trouvée")
            
            current_status = request.get("status")
            if current_status != 'pending':
                raise ValidationError(f"La demande a déjà été traitée (statut: {current_status})")
            
            # Mettre à jour le statut de l'utilisateur
            user_id = request.get("user_id")
            user_query = {"_id": ObjectId(user_id)} if len(str(user_id)) == 24 else {"_id": str(user_id)}
            await self.db.users.update_one(
                user_query,
                {"$set": {
                    "statut": "bloqué",
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            
            # Mettre à jour la demande
            await self.db.access_requests.update_one(
                {"_id": request["_id"]},
                {"$set": {
                    "status": "rejected",
                    "rejection_reason": rejection_reason.strip(),
                    "reviewed_at": datetime.now(timezone.utc),
                    "reviewed_by": str(reviewer_id),
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            
            request = await self.get_request_by_id(request_id)
            
            logger.info("Demande d'accès refusée",
                       request_id=str(request_id),
                       user_id=str(user_id),
                       reviewer_id=str(reviewer_id),
                       reason_length=len(rejection_reason))
            
            return request
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error("Erreur refus demande", request_id=str(request_id), error=str(e))
            raise BusinessLogicError("Erreur lors du refus de la demande")
    
    async def mark_all_as_viewed(self) -> int:
        """
        Marquer toutes les demandes pending comme vues.
        
        Appelé automatiquement quand un recruteur visite la page des demandes d'accès.
        
        Returns:
            int: Nombre de demandes marquées comme vues
        """
        try:
            result = await self.db.access_requests.update_many(
                {"status": "pending", "viewed": False},
                {"$set": {"viewed": True, "updated_at": datetime.now(timezone.utc)}}
            )
            
            count = result.modified_count
            logger.info("Demandes marquées comme vues", count=count)
            
            return count
            
        except Exception as e:
            logger.error("Erreur marquage viewed", error=str(e))
            raise BusinessLogicError("Erreur lors du marquage des demandes")
    
    async def mark_request_as_viewed(self, request_id: Any) -> Any:
        try:
            query = {"_id": ObjectId(request_id)} if len(str(request_id)) == 24 else {"_id": str(request_id)}
            result = await self.db.access_requests.update_one(
                query,
                {"$set": {"viewed": True, "updated_at": datetime.now(timezone.utc)}}
            )
            
            if result.matched_count == 0:
                raise NotFoundError("Demande non trouvée")
            
            return await self.get_request_by_id(request_id)
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Erreur marquage viewed", request_id=str(request_id), error=str(e))
            raise BusinessLogicError("Erreur lors du marquage de la demande")
    
    async def get_unviewed_count(self) -> int:
        """
        Obtenir le nombre de demandes non vues (pour le badge).
        
        Returns:
            int: Nombre de demandes pending et non vues
        """
        try:
            count = await self.db.access_requests.count_documents({
                "status": "pending",
                "viewed": False
            })
            return count
        except Exception as e:
            logger.error("Erreur comptage unviewed", error=str(e))
            return 0

