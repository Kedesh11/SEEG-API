"""
Service pour la gestion des entretiens
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, desc
from datetime import datetime, timedelta
import structlog

from app.models.interview import InterviewSlot
from app.models.application import Application
from app.schemas.interview import (
    InterviewSlotCreate, InterviewSlotUpdate, InterviewSlotResponse,
    InterviewSlotListResponse, InterviewStatsResponse
)
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError

logger = structlog.get_logger(__name__)


class InterviewService:
    """Service pour la gestion des entretiens"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_interview_slot(
        self,
        slot_data: InterviewSlotCreate,
        created_by: str
    ) -> InterviewSlotResponse:
        """
        Créer un nouveau créneau d'entretien
        
        Args:
            slot_data: Données du créneau d'entretien
            created_by: ID de l'utilisateur qui crée le créneau
            
        Returns:
            InterviewSlotResponse: Créneau d'entretien créé
        """
        try:
            # Vérification de l'existence de la candidature
            app_result = await self.db.execute(
                select(Application).where(Application.id == slot_data.application_id)
            )
            application = app_result.scalar_one_or_none()
            
            if not application:
                raise NotFoundError("Candidature non trouvée")
            
            # Validation de la date
            if slot_data.scheduled_date < datetime.utcnow():
                raise ValidationError("La date de l'entretien ne peut pas être dans le passé")
            
            # Vérification des conflits d'horaire
            existing_slot = await self.db.execute(
                select(InterviewSlot).where(
                    and_(
                        InterviewSlot.interviewer_id == slot_data.interviewer_id,
                        InterviewSlot.scheduled_date == slot_data.scheduled_date,
                        InterviewSlot.status.in_(["scheduled", "rescheduled"])
                    )
                )
            )
            
            if existing_slot.scalar_one_or_none():
                raise BusinessLogicError("Un entretien est déjà programmé à cette heure pour cet interviewer")
            
            # Création du créneau d'entretien
            interview_slot = InterviewSlot(
                application_id=slot_data.application_id,
                interviewer_id=slot_data.interviewer_id,
                scheduled_date=slot_data.scheduled_date,
                duration_minutes=slot_data.duration_minutes,
                location=slot_data.location,
                meeting_link=slot_data.meeting_link,
                notes=slot_data.notes,
                status=slot_data.status
            )
            
            self.db.add(interview_slot)
            await self.db.commit()
            await self.db.refresh(interview_slot)
            
            logger.info(
                "Interview slot created",
                slot_id=str(interview_slot.id),
                application_id=slot_data.application_id,
                interviewer_id=slot_data.interviewer_id,
                scheduled_date=slot_data.scheduled_date
            )
            
            return InterviewSlotResponse.model_validate(interview_slot)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to create interview slot",
                error=str(e),
                application_id=slot_data.application_id,
                interviewer_id=slot_data.interviewer_id
            )
            raise
    
    async def get_interview_slot(self, slot_id: str) -> InterviewSlotResponse:
        """
        Récupérer un créneau d'entretien par son ID
        
        Args:
            slot_id: ID du créneau d'entretien
            
        Returns:
            InterviewSlotResponse: Créneau d'entretien
        """
        result = await self.db.execute(
            select(InterviewSlot)
            .options(
                selectinload(InterviewSlot.application),
                selectinload(InterviewSlot.interviewer)
            )
            .where(InterviewSlot.id == slot_id)
        )
        interview_slot = result.scalar_one_or_none()
        
        if not interview_slot:
            raise NotFoundError(f"Créneau d'entretien avec l'ID {slot_id} non trouvé")
        
        return InterviewSlotResponse.model_validate(interview_slot)
    
    async def get_interview_slots(
        self,
        skip: int = 0,
        limit: int = 100,
        application_id: Optional[str] = None,
        interviewer_id: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> InterviewSlotListResponse:
        """
        Récupérer la liste des créneaux d'entretien avec filtres
        
        Args:
            skip: Nombre d'éléments à ignorer
            limit: Nombre maximum d'éléments à retourner
            application_id: Filtrer par candidature
            interviewer_id: Filtrer par interviewer
            status: Filtrer par statut
            date_from: Date de début
            date_to: Date de fin
            
        Returns:
            InterviewSlotListResponse: Liste des créneaux d'entretien
        """
        query = select(InterviewSlot)
        count_query = select(func.count(InterviewSlot.id))
        
        conditions = []
        
        if application_id:
            conditions.append(InterviewSlot.application_id == application_id)
        
        if interviewer_id:
            conditions.append(InterviewSlot.interviewer_id == interviewer_id)
        
        if status:
            conditions.append(InterviewSlot.status == status)
        
        if date_from:
            conditions.append(InterviewSlot.scheduled_date >= date_from)
        
        if date_to:
            conditions.append(InterviewSlot.scheduled_date <= date_to)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        query = query.order_by(InterviewSlot.scheduled_date.asc())
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        interview_slots = result.scalars().all()
        
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar()
        
        return InterviewSlotListResponse(
            items=[InterviewSlotResponse.model_validate(slot) for slot in interview_slots],
            total=total_count,
            skip=skip,
            limit=limit,
            has_more=skip + len(interview_slots) < total_count
        )
    
    async def update_interview_slot(
        self,
        slot_id: str,
        slot_data: InterviewSlotUpdate,
        updated_by: str
    ) -> InterviewSlotResponse:
        """
        Mettre à jour un créneau d'entretien
        
        Args:
            slot_id: ID du créneau d'entretien
            slot_data: Données de mise à jour
            updated_by: ID de l'utilisateur qui effectue la mise à jour
            
        Returns:
            InterviewSlotResponse: Créneau d'entretien mis à jour
        """
        try:
            # Vérification de l'existence du créneau
            result = await self.db.execute(
                select(InterviewSlot).where(InterviewSlot.id == slot_id)
            )
            interview_slot = result.scalar_one_or_none()
            
            if not interview_slot:
                raise NotFoundError(f"Créneau d'entretien avec l'ID {slot_id} non trouvé")
            
            # Mise à jour des champs
            update_data = slot_data.model_dump(exclude_unset=True)
            if update_data:
                # Validation de la date si fournie
                if 'scheduled_date' in update_data and update_data['scheduled_date'] < datetime.utcnow():
                    raise ValidationError("La date de l'entretien ne peut pas être dans le passé")
                
                # Mise à jour du statut avec timestamps
                if 'status' in update_data:
                    if update_data['status'] == 'completed':
                        update_data['completed_at'] = datetime.utcnow()
                    elif update_data['status'] == 'cancelled':
                        update_data['cancelled_at'] = datetime.utcnow()
                
                update_data["updated_at"] = datetime.utcnow()
                
                await self.db.execute(
                    update(InterviewSlot)
                    .where(InterviewSlot.id == slot_id)
                    .values(**update_data)
                )
                
                await self.db.commit()
                
                # Récupération du créneau mis à jour
                result = await self.db.execute(
                    select(InterviewSlot).where(InterviewSlot.id == slot_id)
                )
                interview_slot = result.scalar_one()
                
                logger.info(
                    "Interview slot updated",
                    slot_id=slot_id,
                    updated_by=updated_by,
                    updated_fields=list(update_data.keys())
                )
            
            return InterviewSlotResponse.model_validate(interview_slot)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to update interview slot",
                slot_id=slot_id,
                error=str(e)
            )
            raise
    
    async def delete_interview_slot(self, slot_id: str, deleted_by: str) -> bool:
        """
        Supprimer un créneau d'entretien
        
        Args:
            slot_id: ID du créneau d'entretien
            deleted_by: ID de l'utilisateur qui effectue la suppression
            
        Returns:
            bool: True si la suppression a réussi
        """
        try:
            # Vérification de l'existence du créneau
            result = await self.db.execute(
                select(InterviewSlot).where(InterviewSlot.id == slot_id)
            )
            interview_slot = result.scalar_one_or_none()
            
            if not interview_slot:
                raise NotFoundError(f"Créneau d'entretien avec l'ID {slot_id} non trouvé")
            
            # Suppression du créneau
            await self.db.execute(
                delete(InterviewSlot).where(InterviewSlot.id == slot_id)
            )
            
            await self.db.commit()
            
            logger.info(
                "Interview slot deleted",
                slot_id=slot_id,
                deleted_by=deleted_by
            )
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to delete interview slot",
                slot_id=slot_id,
                error=str(e)
            )
            raise
    
    async def get_available_slots(
        self,
        interviewer_id: str,
        date_from: datetime,
        date_to: datetime
    ) -> List[InterviewSlotResponse]:
        """
        Récupérer les créneaux disponibles pour un interviewer
        
        Args:
            interviewer_id: ID de l'interviewer
            date_from: Date de début
            date_to: Date de fin
            
        Returns:
            List[InterviewSlotResponse]: Liste des créneaux disponibles
        """
        result = await self.db.execute(
            select(InterviewSlot)
            .where(
                and_(
                    InterviewSlot.interviewer_id == interviewer_id,
                    InterviewSlot.scheduled_date >= date_from,
                    InterviewSlot.scheduled_date <= date_to,
                    InterviewSlot.status.in_(["scheduled", "rescheduled"])
                )
            )
            .order_by(InterviewSlot.scheduled_date.asc())
        )
        
        interview_slots = result.scalars().all()
        return [InterviewSlotResponse.model_validate(slot) for slot in interview_slots]
    
    async def get_interview_statistics(self) -> InterviewStatsResponse:
        """
        Récupérer les statistiques des entretiens
        
        Returns:
            InterviewStatsResponse: Statistiques des entretiens
        """
        # Nombre total d'entretiens
        total_result = await self.db.execute(select(func.count(InterviewSlot.id)))
        total_interviews = total_result.scalar()
        
        # Statistiques par statut
        status_result = await self.db.execute(
            select(InterviewSlot.status, func.count(InterviewSlot.id))
            .group_by(InterviewSlot.status)
        )
        status_stats = {row[0]: row[1] for row in status_result.fetchall()}
        
        # Entretiens à venir (prochains 7 jours)
        upcoming_date = datetime.utcnow() + timedelta(days=7)
        upcoming_result = await self.db.execute(
            select(InterviewSlot)
            .where(
                and_(
                    InterviewSlot.scheduled_date >= datetime.utcnow(),
                    InterviewSlot.scheduled_date <= upcoming_date,
                    InterviewSlot.status == "scheduled"
                )
            )
            .order_by(InterviewSlot.scheduled_date.asc())
            .limit(10)
        )
        upcoming_interviews = [InterviewSlotResponse.model_validate(slot) for slot in upcoming_result.scalars().all()]
        
        # Statistiques par mois (derniers 12 mois)
        monthly_result = await self.db.execute(
            select(
                func.date_trunc('month', InterviewSlot.scheduled_date).label('month'),
                func.count(InterviewSlot.id).label('count')
            )
            .where(InterviewSlot.scheduled_date >= datetime.utcnow() - timedelta(days=365))
            .group_by(func.date_trunc('month', InterviewSlot.scheduled_date))
            .order_by('month')
        )
        monthly_stats = {row[0]: row[1] for row in monthly_result.fetchall()}
        
        return InterviewStatsResponse(
            total_interviews=total_interviews,
            status_distribution=status_stats,
            upcoming_interviews=upcoming_interviews,
            monthly_trend=monthly_stats
        )
