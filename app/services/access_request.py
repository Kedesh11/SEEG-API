"""
Service de gestion des demandes d'accès à la plateforme.
"""
import structlog
from typing import Optional, List, Tuple, cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, desc, text
from uuid import UUID
from datetime import datetime, timezone

from app.models.access_request import AccessRequest
from app.models.user import User
from app.schemas.access_request import AccessRequestCreate, AccessRequestUpdate
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError, UnauthorizedError

logger = structlog.get_logger(__name__)


class AccessRequestService:
    """Service de gestion des demandes d'accès."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_access_request(
        self,
        user_id: UUID,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        matricule: Optional[str] = None
    ) -> AccessRequest:
        """
        Créer une nouvelle demande d'accès.
        
        Appelé automatiquement lors de l'inscription d'un candidat interne 
        sans email @seeg-gabon.com.
        
        Args:
            user_id: UUID de l'utilisateur
            email: Email du demandeur
            first_name: Prénom
            last_name: Nom
            phone: Téléphone
            matricule: Matricule SEEG
            
        Returns:
            AccessRequest: La demande créée
            
        Raises:
            ValidationError: Si les données sont invalides
            BusinessLogicError: Si erreur lors de la création
        """
        try:
            # Vérifier qu'il n'existe pas déjà une demande pending pour cet utilisateur
            try:
                existing_result = await self.db.execute(
                    select(AccessRequest).where(
                        and_(
                            AccessRequest.user_id == user_id,
                            AccessRequest.status == 'pending'
                        )
                    )
                )
            except Exception as e:
                # Correction automatique locale: si la colonne updated_at manque sur la table access_requests,
                # on l'ajoute dynamiquement pour éviter l'erreur UndefinedColumn
                err_msg = str(e)
                if 'updated_at' in err_msg and 'UndefinedColumn' in err_msg:
                    await self.db.execute(text("ALTER TABLE access_requests ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NULL"))
                    await self.db.flush()
                    existing_result = await self.db.execute(
                        select(AccessRequest).where(
                            and_(
                                AccessRequest.user_id == user_id,
                                AccessRequest.status == 'pending'
                            )
                        )
                    )
                else:
                    raise
            existing_request = existing_result.scalar_one_or_none()
            
            if existing_request:
                logger.warning("Demande d'accès déjà existante", user_id=str(user_id))
                return existing_request
            
            # Créer la demande
            access_request = AccessRequest()
            access_request.user_id = user_id  # type: ignore
            access_request.email = email  # type: ignore
            access_request.first_name = first_name  # type: ignore
            access_request.last_name = last_name  # type: ignore
            access_request.phone = phone  # type: ignore
            access_request.matricule = matricule  # type: ignore
            access_request.request_type = "internal_no_seeg_email"  # type: ignore
            access_request.status = "pending"  # type: ignore
            access_request.viewed = False  # type: ignore
            
            self.db.add(access_request)
            # PAS de commit ici - responsabilité de l'appelant
            await self.db.flush()  # Pour obtenir l'ID
            await self.db.refresh(access_request)
            
            logger.info("Demande d'accès créée", 
                       request_id=str(access_request.id),
                       user_id=str(user_id),
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
        limit: int = 100
    ) -> Tuple[List[AccessRequest], int, int, int]:
        """
        Récupérer toutes les demandes d'accès avec filtres.
        
        Args:
            status_filter: Filtrer par statut (pending, approved, rejected)
            viewed_filter: Filtrer par viewed (True/False)
            skip: Nombre d'éléments à ignorer (pagination)
            limit: Nombre d'éléments à retourner
            
        Returns:
            Tuple[List[AccessRequest], total, pending_count, unviewed_count]:
                - Liste des demandes
                - Nombre total de demandes
                - Nombre de demandes pending
                - Nombre de demandes non vues (pour le badge)
        """
        try:
            # Construire la requête de base
            query = select(AccessRequest).order_by(desc(AccessRequest.created_at))
            count_query = select(func.count(AccessRequest.id))
            
            # Appliquer les filtres
            conditions = []
            if status_filter:
                conditions.append(AccessRequest.status == status_filter)
            if viewed_filter is not None:
                conditions.append(AccessRequest.viewed == viewed_filter)
            
            if conditions:
                query = query.where(and_(*conditions))
                count_query = count_query.where(and_(*conditions))
            
            # Pagination
            query = query.offset(skip).limit(limit)
            
            # Exécuter les requêtes
            result = await self.db.execute(query)
            requests = list(result.scalars().all())
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar() or 0
            
            # Compter les demandes pending
            pending_result = await self.db.execute(
                select(func.count(AccessRequest.id)).where(AccessRequest.status == 'pending')
            )
            pending_count = pending_result.scalar() or 0
            
            # Compter les demandes non vues (pour le badge)
            unviewed_result = await self.db.execute(
                select(func.count(AccessRequest.id)).where(
                    and_(
                        AccessRequest.status == 'pending',
                        AccessRequest.viewed == False
                    )
                )
            )
            unviewed_count = unviewed_result.scalar() or 0
            
            logger.info("Demandes d'accès récupérées",
                       total=total,
                       pending=pending_count,
                       unviewed=unviewed_count)
            
            return requests, total, pending_count, unviewed_count
            
        except Exception as e:
            logger.error("Erreur récupération demandes d'accès", error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération des demandes")
    
    async def get_request_by_id(self, request_id: UUID) -> Optional[AccessRequest]:
        """Récupérer une demande d'accès par son ID."""
        try:
            result = await self.db.execute(
                select(AccessRequest).where(AccessRequest.id == request_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Erreur récupération demande", request_id=str(request_id), error=str(e))
            raise BusinessLogicError("Erreur lors de la récupération de la demande")
    
    async def approve_request(
        self,
        request_id: UUID,
        reviewer_id: UUID
    ) -> AccessRequest:
        """
        Approuver une demande d'accès.
        
        Actions:
        1. Vérifier que la demande existe et est 'pending'
        2. Mettre à jour users.statut = 'actif'
        3. Mettre à jour access_requests.status = 'approved'
        4. Enregistrer reviewed_at et reviewed_by
        
        Args:
            request_id: ID de la demande
            reviewer_id: ID du recruteur qui approuve
            
        Returns:
            AccessRequest: La demande mise à jour
            
        Raises:
            NotFoundError: Si la demande n'existe pas
            ValidationError: Si la demande n'est pas 'pending'
            BusinessLogicError: Si erreur lors du traitement
        """
        try:
            # Récupérer la demande
            request = await self.get_request_by_id(request_id)
            
            if not request:
                raise NotFoundError("Demande d'accès non trouvée")
            
            current_status: str = cast(str, request.status)
            if current_status != 'pending':
                raise ValidationError(f"La demande a déjà été traitée (statut: {current_status})")
            
            # Mettre à jour le statut de l'utilisateur
            await self.db.execute(
                update(User)
                .where(User.id == request.user_id)
                .values(
                    statut='actif',
                    updated_at=datetime.now(timezone.utc)
                )
            )
            
            # Mettre à jour la demande
            await self.db.execute(
                update(AccessRequest)
                .where(AccessRequest.id == request_id)
                .values(
                    status='approved',
                    reviewed_at=datetime.now(timezone.utc),
                    reviewed_by=reviewer_id
                )
            )
            
            # PAS de commit ici - responsabilité de l'appelant
            await self.db.flush()
            await self.db.refresh(request)
            
            logger.info("Demande d'accès approuvée",
                       request_id=str(request_id),
                       user_id=str(request.user_id),
                       reviewer_id=str(reviewer_id))
            
            return request
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error("Erreur approbation demande", request_id=str(request_id), error=str(e))
            raise BusinessLogicError("Erreur lors de l'approbation de la demande")
    
    async def reject_request(
        self,
        request_id: UUID,
        reviewer_id: UUID,
        rejection_reason: str
    ) -> AccessRequest:
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
            
            current_status: str = cast(str, request.status)
            if current_status != 'pending':
                raise ValidationError(f"La demande a déjà été traitée (statut: {current_status})")
            
            # Mettre à jour le statut de l'utilisateur
            await self.db.execute(
                update(User)
                .where(User.id == request.user_id)
                .values(
                    statut='bloqué',
                    updated_at=datetime.now(timezone.utc)
                )
            )
            
            # Mettre à jour la demande
            await self.db.execute(
                update(AccessRequest)
                .where(AccessRequest.id == request_id)
                .values(
                    status='rejected',
                    rejection_reason=rejection_reason.strip(),
                    reviewed_at=datetime.now(timezone.utc),
                    reviewed_by=reviewer_id
                )
            )
            
            # PAS de commit ici - responsabilité de l'appelant
            await self.db.flush()
            await self.db.refresh(request)
            
            logger.info("Demande d'accès refusée",
                       request_id=str(request_id),
                       user_id=str(request.user_id),
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
            result = await self.db.execute(
                update(AccessRequest)
                .where(
                    and_(
                        AccessRequest.status == 'pending',
                        AccessRequest.viewed == False
                    )
                )
                .values(viewed=True)
            )
            
            # PAS de commit ici - responsabilité de l'appelant
            await self.db.flush()
            
            count = result.rowcount or 0
            logger.info("Demandes marquées comme vues", count=count)
            
            return count
            
        except Exception as e:
            logger.error("Erreur marquage viewed", error=str(e))
            raise BusinessLogicError("Erreur lors du marquage des demandes")
    
    async def mark_request_as_viewed(self, request_id: UUID) -> AccessRequest:
        """
        Marquer une demande spécifique comme vue.
        
        Args:
            request_id: ID de la demande
            
        Returns:
            AccessRequest: La demande mise à jour
        """
        try:
            request = await self.get_request_by_id(request_id)
            
            if not request:
                raise NotFoundError("Demande non trouvée")
            
            await self.db.execute(
                update(AccessRequest)
                .where(AccessRequest.id == request_id)
                .values(viewed=True)
            )
            
            # PAS de commit ici
            await self.db.flush()
            await self.db.refresh(request)
            
            return request
            
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
            result = await self.db.execute(
                select(func.count(AccessRequest.id)).where(
                    and_(
                        AccessRequest.status == 'pending',
                        AccessRequest.viewed == False
                    )
                )
            )
            return result.scalar() or 0
        except Exception as e:
            logger.error("Erreur comptage unviewed", error=str(e))
            return 0

