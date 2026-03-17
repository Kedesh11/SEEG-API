"""
Service pour la gestion des entretiens
Compatible avec InterviewCalendarModal.tsx
"""
from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timedelta, timezone
import structlog
from app.schemas.interview import (
    InterviewSlotCreate, InterviewSlotUpdate, InterviewSlotResponse,
    InterviewSlotListResponse, InterviewStatsResponse
)
from app.core.exceptions import NotFoundError, ValidationError, BusinessLogicError

logger = structlog.get_logger(__name__)


class InterviewService:
    """Service pour la gestion des entretiens"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def create_interview_slot(
        self,
        slot_data: InterviewSlotCreate,
        created_by: str
    ) -> InterviewSlotResponse:
        # Creer un nouveau creneau d'entretien.
        try:
            # Vrification de l'existence de la candidature
            app_id = str(slot_data.application_id)
            app_query = {"_id": ObjectId(app_id)} if len(app_id) == 24 else {"_id": app_id}
            application = await self.db.applications.find_one(app_query)
            
            if not application:
                raise NotFoundError("Candidature non trouve")
            
            # Vrification si le crneau existe dj
            existing_slot = await self.db.interview_slots.find_one({
                "date": slot_data.date,
                "time": slot_data.time
            })
            
            if existing_slot:
                is_available = existing_slot.get("is_available", True)
                other_app = existing_slot.get("application_id")
                
                if not is_available and other_app != app_id:
                    raise BusinessLogicError(
                        f"Le crneau {slot_data.date}  {slot_data.time} est dj occup"
                    )
                
                if is_available:
                    # Update existing available slot
                    update_data = slot_data.model_dump(exclude_unset=True)
                    update_data["is_available"] = False
                    update_data["updated_at"] = datetime.now(timezone.utc)
                    
                    await self.db.interview_slots.update_one(
                        {"_id": existing_slot["_id"]},
                        {"$set": update_data}
                    )
                    
                    slot = await self.db.interview_slots.find_one({"_id": existing_slot["_id"]})
                    slot["id"] = str(slot["_id"])
                    
                    logger.info(
                        "Interview slot updated from available",
                        slot_id=slot["id"],
                        application_id=app_id
                    )
                    return InterviewSlotResponse.model_validate(slot)
            
            # Crer un nouveau crneau
            slot_dict = slot_data.model_dump()
            slot_dict["is_available"] = False
            slot_dict["created_at"] = datetime.now(timezone.utc)
            slot_dict["updated_at"] = datetime.now(timezone.utc)
            slot_dict["created_by"] = str(created_by)
            
            result = await self.db.interview_slots.insert_one(slot_dict)
            slot_dict["_id"] = result.inserted_id
            slot_dict["id"] = str(result.inserted_id)
            
            logger.info(
                "Interview slot created",
                slot_id=slot_dict["id"],
                application_id=app_id,
                date=slot_data.date,
                time=slot_data.time
            )
            
            return InterviewSlotResponse.model_validate(slot_dict)
            
        except (NotFoundError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(
                "Failed to create interview slot",
                error=str(e),
                application_id=str(slot_data.application_id)
            )
            raise
    
    async def get_interview_slot(self, slot_id: str) -> InterviewSlotResponse:
        # Recuperer un creneau d'entretien par son ID.
        query = {"_id": ObjectId(slot_id)} if len(slot_id) == 24 else {"_id": slot_id}
        slot = await self.db.interview_slots.find_one(query)
        
        if not slot:
            raise NotFoundError(f"Crneau d'entretien avec l'ID {slot_id} non trouv")
        
        slot["id"] = str(slot["_id"])
        return InterviewSlotResponse.model_validate(slot)
    
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
        # Recuperer la liste des creneaux d'entretien avec filtres.
        filter_query = {}
        
        if application_id:
            filter_query["application_id"] = str(application_id)
        
        if status:
            filter_query["status"] = status
        
        if is_available is not None:
            filter_query["is_available"] = is_available
        
        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query["$gte"] = date_from
            if date_to:
                date_query["$lte"] = date_to
            filter_query["date"] = date_query
        
        # Exclure les crneaux sans application_id si is_available=false
        if is_available is False:
            filter_query["application_id"] = {"$ne": None}
        
        # Tri
        sort_field = "date"
        sort_dir = 1
        if order:
            # Simple parsing: "date:asc" -> ("date", 1)
            parts = order.split(",")
            if parts:
                p = parts[0].split(":")
                sort_field = p[0]
                sort_dir = -1 if len(p) > 1 and p[1].lower() == "desc" else 1

        cursor = self.db.interview_slots.find(filter_query).sort([(sort_field, sort_dir), ("time", 1)]).skip(skip).limit(limit)
        slots = await cursor.to_list(length=limit)
        total_count = await self.db.interview_slots.count_documents(filter_query)
        
        page = (skip // limit) + 1 if limit > 0 else 1
        total_pages = (total_count + limit - 1) // limit if limit > 0 and total_count else 1
        
        for slot in slots:
            slot["id"] = str(slot["_id"])

        return InterviewSlotListResponse(
            data=[InterviewSlotResponse.model_validate(slot) for slot in slots],
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
        # Mettre a jour un creneau d'entretien.
        try:
            query = {"_id": ObjectId(slot_id)} if len(slot_id) == 24 else {"_id": slot_id}
            current_slot = await self.db.interview_slots.find_one(query)
            
            if not current_slot:
                raise NotFoundError(f"Crneau d'entretien avec l'ID {slot_id} non trouv")
            
            update_data = slot_data.model_dump(exclude_unset=True)
            
            if not update_data:
                current_slot["id"] = str(current_slot["_id"])
                return InterviewSlotResponse.model_validate(current_slot)
            
            # Vrifier si la date ou l'heure changent
            date_changed = 'date' in update_data and update_data['date'] != current_slot.get('date')
            time_changed = 'time' in update_data and update_data['time'] != current_slot.get('time')
            
            if date_changed or time_changed:
                new_date = update_data.get('date', current_slot.get('date'))
                new_time = update_data.get('time', current_slot.get('time'))
                
                # 1. Librer l'ancien crneau
                await self.db.interview_slots.update_one(
                    {"_id": current_slot["_id"]},
                    {"$set": {
                        "is_available": True,
                        "application_id": None,
                        "candidate_name": None,
                        "job_title": None,
                        "status": "cancelled",
                        "notes": "Crneau libr lors de la modification",
                        "updated_at": datetime.now(timezone.utc)
                    }}
                )
                
                # 2. Vrifier si le nouveau crneau existe
                existing_new_slot = await self.db.interview_slots.find_one({
                    "date": new_date,
                    "time": new_time
                })
                
                if existing_new_slot:
                    if not existing_new_slot.get("is_available", True) and existing_new_slot.get("application_id"):
                        raise BusinessLogicError(
                            f"Le crneau {new_date}  {new_time} est dj occup par une autre candidature"
                        )
                    
                    # Le crneau existe et est disponible, l'occuper
                    new_update = {
                        "application_id": str(current_slot.get("application_id") or update_data.get("application_id")),
                        "candidate_name": update_data.get("candidate_name", current_slot.get("candidate_name")),
                        "job_title": update_data.get("job_title", current_slot.get("job_title")),
                        "status": update_data.get("status", "scheduled"),
                        "is_available": False,
                        "location": update_data.get("location", current_slot.get("location")),
                        "notes": update_data.get("notes", "Entretien programm"),
                        "updated_at": datetime.now(timezone.utc)
                    }
                    await self.db.interview_slots.update_one(
                        {"_id": existing_new_slot["_id"]},
                        {"$set": new_update}
                    )
                    
                    slot = await self.db.interview_slots.find_one({"_id": existing_new_slot["_id"]})
                    slot["id"] = str(slot["_id"])
                    return InterviewSlotResponse.model_validate(slot)
                else:
                    # Crer nouveau
                    new_slot = {
                        "date": new_date,
                        "time": new_time,
                        "application_id": str(current_slot.get("application_id") or update_data.get("application_id")),
                        "candidate_name": update_data.get("candidate_name", current_slot.get("candidate_name")),
                        "job_title": update_data.get("job_title", current_slot.get("job_title")),
                        "status": update_data.get("status", "scheduled"),
                        "is_available": False,
                        "location": update_data.get("location", current_slot.get("location")),
                        "notes": update_data.get("notes", "Entretien programm"),
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                        "created_by": str(updated_by)
                    }
                    result = await self.db.interview_slots.insert_one(new_slot)
                    new_slot["id"] = str(result.inserted_id)
                    return InterviewSlotResponse.model_validate(new_slot)
            else:
                # Mise  jour simple
                update_data["updated_at"] = datetime.now(timezone.utc)
                await self.db.interview_slots.update_one(
                    {"_id": current_slot["_id"]},
                    {"$set": update_data}
                )
                
                slot = await self.db.interview_slots.find_one({"_id": current_slot["_id"]})
                slot["id"] = str(slot["_id"])
                return InterviewSlotResponse.model_validate(slot)
            
        except (NotFoundError, BusinessLogicError):
            #  PAS de rollback ici - gr par get_db()
            raise
        except Exception as e:
            #  PAS de rollback ici - gr par get_db()
            logger.error(
                "Failed to update interview slot",
                slot_id=slot_id,
                error=str(e)
            )
            raise
    
    async def delete_interview_slot(self, slot_id: str, deleted_by: str) -> bool:
        # Supprimer/Annuler un creneau d'entretien (soft delete).
        try:
            query = {"_id": ObjectId(slot_id)} if len(slot_id) == 24 else {"_id": slot_id}
            
            result = await self.db.interview_slots.update_one(
                query,
                {"$set": {
                    "status": "cancelled",
                    "is_available": True,
                    "application_id": None,
                    "candidate_name": None,
                    "job_title": None,
                    "notes": "Entretien annul",
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            
            if result.matched_count == 0:
                raise NotFoundError(f"Crneau d'entretien avec l'ID {slot_id} non trouv")
            
            logger.info(
                "Interview slot cancelled (soft delete)",
                slot_id=slot_id,
                deleted_by=deleted_by
            )
            return True
            
        except NotFoundError:
            #  PAS de rollback ici - gr par get_db()
            raise
        except Exception as e:
            #  PAS de rollback ici - gr par get_db()
            logger.error(
                "Failed to delete interview slot",
                slot_id=slot_id,
                error=str(e)
            )
            raise
    
    async def get_interview_statistics(self) -> InterviewStatsResponse:
        # Recuperer les statistiques des entretiens.
        # Nombre total d'entretiens
        total_interviews = await self.db.interview_slots.count_documents({"is_available": False})
        
        # Statistiques par statut
        pipeline = [
            {"$match": {"is_available": False}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        cursor = self.db.interview_slots.aggregate(pipeline)
        status_stats = {item["_id"]: item["count"] async for item in cursor}
        
        return InterviewStatsResponse(
            total_interviews=total_interviews,
            scheduled_interviews=status_stats.get('scheduled', 0),
            completed_interviews=status_stats.get('completed', 0),
            cancelled_interviews=status_stats.get('cancelled', 0),
            interviews_by_status=status_stats
        )
