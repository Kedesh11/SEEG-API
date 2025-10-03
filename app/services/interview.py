"""
Service pour la gestion des entretiens
Compatible avec InterviewCalendarModal.tsx
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, desc
from datetime import datetime, timedelta, timezone
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
            
        Raises:
            NotFoundError: Si la candidature n'existe pas
            BusinessLogicError: Si le créneau est déjà occupé
        """
        try:
            # Vérification de l'existence de la candidature
            app_result = await self.db.execute(
                select(Application).where(Application.id == slot_data.application_id)
            )
            application = app_result.scalar_one_or_none()
            
            if not application:
                raise NotFoundError("Candidature non trouvée")
            
            # Vérification si le créneau existe déjà
            existing_slot_result = await self.db.execute(
                select(InterviewSlot).where(
                    and_(
                        InterviewSlot.date == slot_data.date,
                        InterviewSlot.time == slot_data.time
                    )
                )
            )
            existing_slot = existing_slot_result.scalar_one_or_none()
            
            if existing_slot:
                # Si le créneau existe et est occupé par une autre application
                if not existing_slot.is_available and existing_slot.application_id != slot_data.application_id:
                    raise BusinessLogicError(
                        f"Le créneau {slot_data.date} à {slot_data.time} est déjà occupé"
                    )
                
                # Si le créneau existe mais est disponible, le mettre à jour
                if existing_slot.is_available:
                    existing_slot.application_id = slot_data.application_id
                    existing_slot.candidate_name = slot_data.candidate_name
                    existing_slot.job_title = slot_data.job_title
                    existing_slot.status = slot_data.status
                    existing_slot.is_available = False
                    existing_slot.location = slot_data.location
                    existing_slot.notes = slot_data.notes
                    existing_slot.updated_at = datetime.now(timezone.utc)
                    
                    await self.db.commit()
                    await self.db.refresh(existing_slot)
                    
                    logger.info(
                        "Interview slot updated from available",
                        slot_id=str(existing_slot.id),
                        application_id=str(slot_data.application_id)
                    )
                    
                    return InterviewSlotResponse.model_validate(existing_slot)
            
            # Créer un nouveau créneau
            interview_slot = InterviewSlot(
                date=slot_data.date,
                time=slot_data.time,
                application_id=slot_data.application_id,
                candidate_name=slot_data.candidate_name,
                job_title=slot_data.job_title,
                status=slot_data.status,
                is_available=False,
                location=slot_data.location,
                notes=slot_data.notes
            )
            
            self.db.add(interview_slot)
            await self.db.commit()
            await self.db.refresh(interview_slot)
            
            logger.info(
                "Interview slot created",
                slot_id=str(interview_slot.id),
                application_id=str(slot_data.application_id),
                date=slot_data.date,
                time=slot_data.time
            )
            
            return InterviewSlotResponse.model_validate(interview_slot)
            
        except (NotFoundError, BusinessLogicError):
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to create interview slot",
                error=str(e),
                application_id=str(slot_data.application_id)
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
            select(InterviewSlot).where(InterviewSlot.id == slot_id)
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
        status: Optional[str] = None,
        is_available: Optional[bool] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        order: Optional[str] = None
    ) -> InterviewSlotListResponse:
        """
        Récupérer la liste des créneaux d'entretien avec filtres
        
        Args:
            skip: Nombre d'éléments à ignorer
            limit: Nombre maximum d'éléments à retourner
            application_id: Filtrer par candidature
            status: Filtrer par statut
            is_available: Filtrer par disponibilité
            date_from: Date de début (YYYY-MM-DD)
            date_to: Date de fin (YYYY-MM-DD)
            order: Ordre de tri (ex: "date:asc,time:asc")
            
        Returns:
            InterviewSlotListResponse: Liste des créneaux d'entretien
        """
        query = select(InterviewSlot)
        count_query = select(func.count(InterviewSlot.id))
        
        conditions = []
        
        if application_id:
            conditions.append(InterviewSlot.application_id == application_id)
        
        if status:
            conditions.append(InterviewSlot.status == status)
        
        if is_available is not None:
            conditions.append(InterviewSlot.is_available == is_available)
        
        if date_from:
            conditions.append(InterviewSlot.date >= date_from)
        
        if date_to:
            conditions.append(InterviewSlot.date <= date_to)
        
        # Exclure les créneaux sans application_id si is_available=false
        if is_available is False:
            conditions.append(InterviewSlot.application_id.isnot(None))
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # Tri par défaut: date ASC, time ASC
        query = query.order_by(InterviewSlot.date.asc(), InterviewSlot.time.asc())
        
        # Pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        interview_slots = result.scalars().all()
        
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar()
        
        page = (skip // limit) + 1 if limit > 0 else 1
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
        
        return InterviewSlotListResponse(
            data=[InterviewSlotResponse.model_validate(slot) for slot in interview_slots],
            total=total_count,
            page=page,
            per_page=limit,
            total_pages=total_pages
        )
    
    async def update_interview_slot(
        self,
        slot_id: str,
        slot_data: InterviewSlotUpdate,
        updated_by: str
    ) -> InterviewSlotResponse:
        """
        Mettre à jour un créneau d'entretien
        
        Logique complexe pour changement de date/heure:
        1. Si date ou time changent, libérer l'ancien créneau
        2. Vérifier si le nouveau créneau existe
        3. Si disponible, l'occuper; sinon créer un nouveau
        
        Args:
            slot_id: ID du créneau d'entretien
            slot_data: Données de mise à jour
            updated_by: ID de l'utilisateur qui effectue la mise à jour
            
        Returns:
            InterviewSlotResponse: Créneau d'entretien mis à jour
        """
        try:
            # Récupérer le créneau actuel
            result = await self.db.execute(
                select(InterviewSlot).where(InterviewSlot.id == slot_id)
            )
            current_slot = result.scalar_one_or_none()
            
            if not current_slot:
                raise NotFoundError(f"Créneau d'entretien avec l'ID {slot_id} non trouvé")
            
            update_data = slot_data.model_dump(exclude_unset=True)
            
            if not update_data:
                return InterviewSlotResponse.model_validate(current_slot)
            
            # Vérifier si la date ou l'heure changent
            date_changed = 'date' in update_data and update_data['date'] != current_slot.date
            time_changed = 'time' in update_data and update_data['time'] != current_slot.time
            
            if date_changed or time_changed:
                # LOGIQUE COMPLEXE: Changement de date/heure
                new_date = update_data.get('date', current_slot.date)
                new_time = update_data.get('time', current_slot.time)
                
                # 1. Libérer l'ancien créneau
                current_slot.is_available = True
                current_slot.application_id = None
                current_slot.candidate_name = None
                current_slot.job_title = None
                current_slot.status = 'cancelled'
                current_slot.notes = 'Créneau libéré lors de la modification'
                current_slot.updated_at = datetime.now(timezone.utc)
                
                logger.info(
                    "Old slot freed during update",
                    old_slot_id=slot_id,
                    old_date=current_slot.date,
                    old_time=current_slot.time
                )
                
                # 2. Vérifier si le nouveau créneau existe
                new_slot_result = await self.db.execute(
                    select(InterviewSlot).where(
                        and_(
                            InterviewSlot.date == new_date,
                            InterviewSlot.time == new_time
                        )
                    )
                )
                existing_new_slot = new_slot_result.scalar_one_or_none()
                
                if existing_new_slot:
                    # Le nouveau créneau existe
                    if not existing_new_slot.is_available and existing_new_slot.application_id:
                        # Occupé par une autre application
                        await self.db.rollback()
                        raise BusinessLogicError(
                            f"Le créneau {new_date} à {new_time} est déjà occupé par une autre candidature"
                        )
                    
                    # Le créneau existe et est disponible, l'occuper
                    existing_new_slot.application_id = current_slot.application_id or update_data.get('application_id')
                    existing_new_slot.candidate_name = update_data.get('candidate_name', current_slot.candidate_name)
                    existing_new_slot.job_title = update_data.get('job_title', current_slot.job_title)
                    existing_new_slot.status = update_data.get('status', 'scheduled')
                    existing_new_slot.is_available = False
                    existing_new_slot.location = update_data.get('location', current_slot.location)
                    existing_new_slot.notes = update_data.get('notes', 'Entretien programmé')
                    existing_new_slot.updated_at = datetime.now(timezone.utc)
                    
                    await self.db.commit()
                    await self.db.refresh(existing_new_slot)
                    
                    logger.info(
                        "Existing slot occupied during update",
                        new_slot_id=str(existing_new_slot.id),
                        new_date=new_date,
                        new_time=new_time
                    )
                    
                    return InterviewSlotResponse.model_validate(existing_new_slot)
                else:
                    # Le nouveau créneau n'existe pas, créer
                    new_slot = InterviewSlot(
                        date=new_date,
                        time=new_time,
                        application_id=current_slot.application_id or update_data.get('application_id'),
                        candidate_name=update_data.get('candidate_name', current_slot.candidate_name),
                        job_title=update_data.get('job_title', current_slot.job_title),
                        status=update_data.get('status', 'scheduled'),
                        is_available=False,
                        location=update_data.get('location', current_slot.location),
                        notes=update_data.get('notes', 'Entretien programmé')
                    )
                    
                    self.db.add(new_slot)
                    await self.db.commit()
                    await self.db.refresh(new_slot)
                    
                    logger.info(
                        "New slot created during update",
                        new_slot_id=str(new_slot.id),
                        new_date=new_date,
                        new_time=new_time
                    )
                    
                    return InterviewSlotResponse.model_validate(new_slot)
            else:
                # Mise à jour simple sans changement de date/heure
                for key, value in update_data.items():
                    setattr(current_slot, key, value)
                
                current_slot.updated_at = datetime.now(timezone.utc)
                
                await self.db.commit()
                await self.db.refresh(current_slot)
                
                logger.info(
                    "Interview slot updated (simple)",
                    slot_id=slot_id,
                    updated_fields=list(update_data.keys())
                )
                
                return InterviewSlotResponse.model_validate(current_slot)
            
        except (NotFoundError, BusinessLogicError):
            await self.db.rollback()
            raise
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
        Supprimer/Annuler un créneau d'entretien (soft delete)
        
        Marque le créneau comme annulé et disponible au lieu de le supprimer physiquement.
        
        Args:
            slot_id: ID du créneau d'entretien
            deleted_by: ID de l'utilisateur qui effectue la suppression
            
        Returns:
            bool: True si la suppression a réussi
        """
        try:
            result = await self.db.execute(
                select(InterviewSlot).where(InterviewSlot.id == slot_id)
            )
            interview_slot = result.scalar_one_or_none()
            
            if not interview_slot:
                raise NotFoundError(f"Créneau d'entretien avec l'ID {slot_id} non trouvé")
            
            # Soft delete: Marquer comme annulé et disponible
            interview_slot.status = 'cancelled'
            interview_slot.is_available = True
            interview_slot.application_id = None
            interview_slot.candidate_name = None
            interview_slot.job_title = None
            interview_slot.notes = 'Entretien annulé'
            interview_slot.updated_at = datetime.now(timezone.utc)
            
            await self.db.commit()
            
            logger.info(
                "Interview slot cancelled (soft delete)",
                slot_id=slot_id,
                deleted_by=deleted_by
            )
            
            return True
            
        except NotFoundError:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to delete interview slot",
                slot_id=slot_id,
                error=str(e)
            )
            raise
    
    async def get_interview_statistics(self) -> InterviewStatsResponse:
        """
        Récupérer les statistiques des entretiens
        
        Returns:
            InterviewStatsResponse: Statistiques des entretiens
        """
        # Nombre total d'entretiens
        total_result = await self.db.execute(
            select(func.count(InterviewSlot.id)).where(
                InterviewSlot.is_available == False
            )
        )
        total_interviews = total_result.scalar()
        
        # Statistiques par statut
        status_result = await self.db.execute(
            select(InterviewSlot.status, func.count(InterviewSlot.id))
            .where(InterviewSlot.is_available == False)
            .group_by(InterviewSlot.status)
        )
        status_stats = {row[0]: row[1] for row in status_result.fetchall()}
        
        return InterviewStatsResponse(
            total_interviews=total_interviews,
            scheduled_interviews=status_stats.get('scheduled', 0),
            completed_interviews=status_stats.get('completed', 0),
            cancelled_interviews=status_stats.get('cancelled', 0),
            interviews_by_status=status_stats
        )
