"""
Tests pour les endpoints de gestion des entretiens
Compatible avec InterviewCalendarModal.tsx
"""
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import InterviewSlot
from app.models.application import Application
from app.models.job_offer import JobOffer
from app.models.user import User


@pytest.fixture
async def test_job_offer(test_db: AsyncSession):
    """Créer une offre d'emploi de test"""
    job_offer = JobOffer(
        title="Développeur Full Stack",
        description="Poste de développeur",
        department="IT",
        location="Libreville",
        employment_type="CDI",
        status="open",
        is_published=True
    )
    test_db.add(job_offer)
    await test_db.commit()
    await test_db.refresh(job_offer)
    return job_offer


@pytest.fixture
async def test_application(test_db: AsyncSession, test_user: User, test_job_offer: JobOffer):
    """Créer une candidature de test"""
    application = Application(
        user_id=test_user.id,
        job_offer_id=test_job_offer.id,
        status="submitted"
    )
    test_db.add(application)
    await test_db.commit()
    await test_db.refresh(application)
    return application


@pytest.fixture
async def test_interview_slot(test_db: AsyncSession, test_application: Application):
    """Créer un créneau d'entretien de test"""
    slot = InterviewSlot(
        date="2025-10-15",
        time="09:00:00",
        application_id=test_application.id,
        candidate_name="John Doe",
        job_title="Développeur Full Stack",
        status="scheduled",
        is_available=False,
        location="Libreville",
        notes="Entretien technique"
    )
    test_db.add(slot)
    await test_db.commit()
    await test_db.refresh(slot)
    return slot


class TestCreateInterviewSlot:
    """Tests pour POST /api/v1/interviews/slots"""
    
    @pytest.mark.asyncio
    async def test_create_slot_success(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        auth_headers: dict,
        test_application: Application
    ):
        """Test création d'un créneau avec succès"""
        payload = {
            "date": "2025-10-20",
            "time": "14:00:00",
            "application_id": str(test_application.id),
            "candidate_name": "Jane Smith",
            "job_title": "Développeur Backend",
            "status": "scheduled",
            "location": "Libreville",
            "notes": "Premier entretien"
        }
        
        response = await client.post(
            "/api/v1/interviews/slots",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["date"] == "2025-10-20"
        assert data["time"] == "14:00:00"
        assert data["candidate_name"] == "Jane Smith"
        assert data["status"] == "scheduled"
        assert data["is_available"] is False
        assert "id" in data
        assert "created_at" in data
    
    @pytest.mark.asyncio
    async def test_create_slot_invalid_date_format(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_application: Application
    ):
        """Test création avec format de date invalide"""
        payload = {
            "date": "20/10/2025",  # Format invalide
            "time": "14:00:00",
            "application_id": str(test_application.id),
            "candidate_name": "Jane Smith",
            "job_title": "Développeur"
        }
        
        response = await client.post(
            "/api/v1/interviews/slots",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation Pydantic
    
    @pytest.mark.asyncio
    async def test_create_slot_invalid_time_format(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_application: Application
    ):
        """Test création avec format d'heure invalide"""
        payload = {
            "date": "2025-10-20",
            "time": "14:00",  # Format invalide (manque les secondes)
            "application_id": str(test_application.id),
            "candidate_name": "Jane Smith",
            "job_title": "Développeur"
        }
        
        response = await client.post(
            "/api/v1/interviews/slots",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_slot_application_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test création avec candidature inexistante"""
        payload = {
            "date": "2025-10-20",
            "time": "14:00:00",
            "application_id": str(uuid4()),  # ID inexistant
            "candidate_name": "Jane Smith",
            "job_title": "Développeur"
        }
        
        response = await client.post(
            "/api/v1/interviews/slots",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "non trouvée" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_create_slot_already_occupied(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        auth_headers: dict,
        test_application: Application,
        test_interview_slot: InterviewSlot
    ):
        """Test création d'un créneau déjà occupé"""
        # Créer une deuxième application
        application2 = Application(
            user_id=test_application.user_id,
            job_offer_id=test_application.job_offer_id,
            status="submitted"
        )
        test_db.add(application2)
        await test_db.commit()
        await test_db.refresh(application2)
        
        payload = {
            "date": test_interview_slot.date,  # Même date
            "time": test_interview_slot.time,  # Même heure
            "application_id": str(application2.id),
            "candidate_name": "Another Candidate",
            "job_title": "Développeur"
        }
        
        response = await client.post(
            "/api/v1/interviews/slots",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 409  # Conflict
        assert "occupé" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_create_slot_update_available_slot(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        auth_headers: dict,
        test_application: Application
    ):
        """Test création qui met à jour un créneau disponible"""
        # Créer un créneau disponible
        available_slot = InterviewSlot(
            date="2025-10-25",
            time="10:00:00",
            is_available=True,
            status="cancelled"
        )
        test_db.add(available_slot)
        await test_db.commit()
        
        payload = {
            "date": "2025-10-25",
            "time": "10:00:00",
            "application_id": str(test_application.id),
            "candidate_name": "New Candidate",
            "job_title": "Développeur"
        }
        
        response = await client.post(
            "/api/v1/interviews/slots",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["is_available"] is False
        assert data["status"] == "scheduled"
        assert data["application_id"] == str(test_application.id)


class TestGetInterviewSlots:
    """Tests pour GET /api/v1/interviews/slots"""
    
    @pytest.mark.asyncio
    async def test_list_slots_empty(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test liste vide de créneaux"""
        response = await client.get(
            "/api/v1/interviews/slots",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert isinstance(data["data"], list)
    
    @pytest.mark.asyncio
    async def test_list_slots_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_interview_slot: InterviewSlot
    ):
        """Test liste avec des créneaux"""
        response = await client.get(
            "/api/v1/interviews/slots",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["data"]) >= 1
        
        slot = data["data"][0]
        assert "id" in slot
        assert "date" in slot
        assert "time" in slot
        assert "is_available" in slot
    
    @pytest.mark.asyncio
    async def test_list_slots_filter_by_date_range(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        auth_headers: dict,
        test_application: Application
    ):
        """Test filtrage par période de dates"""
        # Créer plusieurs créneaux à différentes dates
        slots = [
            InterviewSlot(
                date="2025-10-10",
                time="09:00:00",
                application_id=test_application.id,
                candidate_name="Candidate 1",
                job_title="Dev",
                is_available=False
            ),
            InterviewSlot(
                date="2025-10-15",
                time="10:00:00",
                application_id=test_application.id,
                candidate_name="Candidate 2",
                job_title="Dev",
                is_available=False
            ),
            InterviewSlot(
                date="2025-10-25",
                time="11:00:00",
                application_id=test_application.id,
                candidate_name="Candidate 3",
                job_title="Dev",
                is_available=False
            ),
        ]
        
        for slot in slots:
            test_db.add(slot)
        await test_db.commit()
        
        response = await client.get(
            "/api/v1/interviews/slots?date_from=2025-10-12&date_to=2025-10-20",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Devrait retourner seulement le créneau du 15 octobre
        dates = [slot["date"] for slot in data["data"]]
        assert "2025-10-15" in dates
        assert "2025-10-10" not in dates
        assert "2025-10-25" not in dates
    
    @pytest.mark.asyncio
    async def test_list_slots_filter_by_availability(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        auth_headers: dict,
        test_application: Application
    ):
        """Test filtrage par disponibilité"""
        # Créer des créneaux disponibles et occupés
        occupied = InterviewSlot(
            date="2025-10-15",
            time="09:00:00",
            application_id=test_application.id,
            candidate_name="Candidate",
            job_title="Dev",
            is_available=False
        )
        available = InterviewSlot(
            date="2025-10-16",
            time="09:00:00",
            is_available=True,
            status="cancelled"
        )
        
        test_db.add(occupied)
        test_db.add(available)
        await test_db.commit()
        
        # Filtrer par créneaux occupés
        response = await client.get(
            "/api/v1/interviews/slots?is_available=false",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Tous les créneaux retournés doivent être occupés
        for slot in data["data"]:
            assert slot["is_available"] is False
            assert slot["application_id"] is not None
    
    @pytest.mark.asyncio
    async def test_list_slots_filter_by_status(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        auth_headers: dict,
        test_application: Application
    ):
        """Test filtrage par statut"""
        slots = [
            InterviewSlot(
                date="2025-10-15",
                time="09:00:00",
                application_id=test_application.id,
                candidate_name="C1",
                job_title="D",
                status="scheduled",
                is_available=False
            ),
            InterviewSlot(
                date="2025-10-16",
                time="09:00:00",
                application_id=test_application.id,
                candidate_name="C2",
                job_title="D",
                status="completed",
                is_available=False
            ),
        ]
        
        for slot in slots:
            test_db.add(slot)
        await test_db.commit()
        
        response = await client.get(
            "/api/v1/interviews/slots?status=scheduled",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for slot in data["data"]:
            assert slot["status"] == "scheduled"
    
    @pytest.mark.asyncio
    async def test_list_slots_pagination(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        auth_headers: dict,
        test_application: Application
    ):
        """Test pagination"""
        # Créer 5 créneaux
        for i in range(5):
            slot = InterviewSlot(
                date=f"2025-10-{15+i:02d}",
                time="09:00:00",
                application_id=test_application.id,
                candidate_name=f"Candidate {i}",
                job_title="Dev",
                is_available=False
            )
            test_db.add(slot)
        await test_db.commit()
        
        # Première page (2 éléments)
        response = await client.get(
            "/api/v1/interviews/slots?skip=0&limit=2",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["page"] == 1
        assert data["per_page"] == 2
        
        # Deuxième page
        response = await client.get(
            "/api/v1/interviews/slots?skip=2&limit=2",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["page"] == 2


class TestGetInterviewSlot:
    """Tests pour GET /api/v1/interviews/slots/{id}"""
    
    @pytest.mark.asyncio
    async def test_get_slot_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_interview_slot: InterviewSlot
    ):
        """Test récupération d'un créneau par ID"""
        response = await client.get(
            f"/api/v1/interviews/slots/{test_interview_slot.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_interview_slot.id)
        assert data["date"] == test_interview_slot.date
        assert data["time"] == test_interview_slot.time
    
    @pytest.mark.asyncio
    async def test_get_slot_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test récupération d'un créneau inexistant"""
        response = await client.get(
            f"/api/v1/interviews/slots/{uuid4()}",
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestUpdateInterviewSlot:
    """Tests pour PUT /api/v1/interviews/slots/{id}"""
    
    @pytest.mark.asyncio
    async def test_update_slot_simple(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_interview_slot: InterviewSlot
    ):
        """Test mise à jour simple (sans changement de date/heure)"""
        payload = {
            "status": "completed",
            "notes": "Entretien réussi"
        }
        
        response = await client.put(
            f"/api/v1/interviews/slots/{test_interview_slot.id}",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["notes"] == "Entretien réussi"
        assert data["date"] == test_interview_slot.date  # Inchangé
        assert data["time"] == test_interview_slot.time  # Inchangé
    
    @pytest.mark.asyncio
    async def test_update_slot_change_date(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        auth_headers: dict,
        test_interview_slot: InterviewSlot
    ):
        """Test changement de date (logique complexe)"""
        old_date = test_interview_slot.date
        new_date = "2025-10-20"
        
        payload = {
            "date": new_date
        }
        
        response = await client.put(
            f"/api/v1/interviews/slots/{test_interview_slot.id}",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["date"] == new_date
        
        # Vérifier que l'ancien créneau a été libéré
        await test_db.refresh(test_interview_slot)
        assert test_interview_slot.is_available is True
        assert test_interview_slot.status == "cancelled"
    
    @pytest.mark.asyncio
    async def test_update_slot_change_time(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_interview_slot: InterviewSlot
    ):
        """Test changement d'heure"""
        payload = {
            "time": "14:00:00"
        }
        
        response = await client.put(
            f"/api/v1/interviews/slots/{test_interview_slot.id}",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["time"] == "14:00:00"
    
    @pytest.mark.asyncio
    async def test_update_slot_change_to_occupied_slot(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        auth_headers: dict,
        test_interview_slot: InterviewSlot,
        test_application: Application
    ):
        """Test changement vers un créneau déjà occupé (doit échouer)"""
        # Créer un autre créneau occupé
        occupied_slot = InterviewSlot(
            date="2025-10-25",
            time="15:00:00",
            application_id=test_application.id,
            candidate_name="Other Candidate",
            job_title="Dev",
            is_available=False
        )
        test_db.add(occupied_slot)
        await test_db.commit()
        
        # Essayer de déplacer vers ce créneau
        payload = {
            "date": "2025-10-25",
            "time": "15:00:00"
        }
        
        response = await client.put(
            f"/api/v1/interviews/slots/{test_interview_slot.id}",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 409  # Conflict
        assert "occupé" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_update_slot_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test mise à jour d'un créneau inexistant"""
        payload = {"status": "completed"}
        
        response = await client.put(
            f"/api/v1/interviews/slots/{uuid4()}",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestDeleteInterviewSlot:
    """Tests pour DELETE /api/v1/interviews/slots/{id}"""
    
    @pytest.mark.asyncio
    async def test_delete_slot_success(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        auth_headers: dict,
        test_interview_slot: InterviewSlot
    ):
        """Test suppression (soft delete) d'un créneau"""
        slot_id = test_interview_slot.id
        
        response = await client.delete(
            f"/api/v1/interviews/slots/{slot_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "annulé" in data["message"].lower()
        
        # Vérifier que c'est un soft delete
        await test_db.refresh(test_interview_slot)
        assert test_interview_slot.status == "cancelled"
        assert test_interview_slot.is_available is True
        assert test_interview_slot.application_id is None
    
    @pytest.mark.asyncio
    async def test_delete_slot_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test suppression d'un créneau inexistant"""
        response = await client.delete(
            f"/api/v1/interviews/slots/{uuid4()}",
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestInterviewStatistics:
    """Tests pour GET /api/v1/interviews/stats/overview"""
    
    @pytest.mark.asyncio
    async def test_get_statistics_empty(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test statistiques sans données"""
        response = await client.get(
            "/api/v1/interviews/stats/overview",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_interviews" in data
        assert "scheduled_interviews" in data
        assert "completed_interviews" in data
        assert "cancelled_interviews" in data
        assert "interviews_by_status" in data
        assert data["total_interviews"] == 0
    
    @pytest.mark.asyncio
    async def test_get_statistics_with_data(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        auth_headers: dict,
        test_application: Application
    ):
        """Test statistiques avec des données"""
        # Créer des créneaux avec différents statuts
        slots = [
            InterviewSlot(
                date="2025-10-15",
                time="09:00:00",
                application_id=test_application.id,
                candidate_name="C1",
                job_title="D",
                status="scheduled",
                is_available=False
            ),
            InterviewSlot(
                date="2025-10-16",
                time="09:00:00",
                application_id=test_application.id,
                candidate_name="C2",
                job_title="D",
                status="scheduled",
                is_available=False
            ),
            InterviewSlot(
                date="2025-10-17",
                time="09:00:00",
                application_id=test_application.id,
                candidate_name="C3",
                job_title="D",
                status="completed",
                is_available=False
            ),
        ]
        
        for slot in slots:
            test_db.add(slot)
        await test_db.commit()
        
        response = await client.get(
            "/api/v1/interviews/stats/overview",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_interviews"] == 3
        assert data["scheduled_interviews"] == 2
        assert data["completed_interviews"] == 1
        assert data["interviews_by_status"]["scheduled"] == 2
        assert data["interviews_by_status"]["completed"] == 1


class TestInterviewSlotsOrdering:
    """Tests pour l'ordre de tri des créneaux"""
    
    @pytest.mark.asyncio
    async def test_slots_ordered_by_date_and_time(
        self,
        client: AsyncClient,
        test_db: AsyncSession,
        auth_headers: dict,
        test_application: Application
    ):
        """Test que les créneaux sont triés par date puis par heure"""
        slots = [
            InterviewSlot(
                date="2025-10-15",
                time="14:00:00",
                application_id=test_application.id,
                candidate_name="C1",
                job_title="D",
                is_available=False
            ),
            InterviewSlot(
                date="2025-10-15",
                time="09:00:00",
                application_id=test_application.id,
                candidate_name="C2",
                job_title="D",
                is_available=False
            ),
            InterviewSlot(
                date="2025-10-14",
                time="15:00:00",
                application_id=test_application.id,
                candidate_name="C3",
                job_title="D",
                is_available=False
            ),
        ]
        
        for slot in slots:
            test_db.add(slot)
        await test_db.commit()
        
        response = await client.get(
            "/api/v1/interviews/slots",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Vérifier l'ordre: 14/10 15h, puis 15/10 9h, puis 15/10 14h
        returned_slots = data["data"]
        assert returned_slots[0]["date"] == "2025-10-14"
        assert returned_slots[1]["date"] == "2025-10-15"
        assert returned_slots[1]["time"] == "09:00:00"
        assert returned_slots[2]["date"] == "2025-10-15"
        assert returned_slots[2]["time"] == "14:00:00"
