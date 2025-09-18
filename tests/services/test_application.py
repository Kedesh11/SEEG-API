"""
Tests pour le service d'application
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from app.services.application import ApplicationService
from app.models.application import Application
from app.models.user import User
from app.models.job_offer import JobOffer
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.core.exceptions import ValidationError, BusinessLogicError


class TestApplicationService:
    """Tests pour le service d'application."""
    
    def setup_method(self):
        """Configuration pour chaque test."""
        self.mock_db = AsyncMock()
        self.application_service = ApplicationService(self.mock_db)
    
    @pytest.mark.asyncio
    async def test_create_application_success(self):
        """Test la création réussie d'une candidature."""
        # Mock des données
        application_data = ApplicationCreate(
            candidate_id="candidate-id",
            job_offer_id="job-offer-id",
            cover_letter="Lettre de motivation",
            motivation="Ma motivation"
        )
        
        candidate = User(
            id="candidate-id",
            email="candidate@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        
        job_offer = JobOffer(
            id="job-offer-id",
            title="Développeur Python",
            description="Description",
            location="Paris",
            contract_type="CDI",
            recruiter_id="recruiter-id"
        )
        
        # Mock de la base de données
        mock_candidate_result = MagicMock()
        mock_candidate_result.scalar_one_or_none.return_value = candidate
        
        mock_job_result = MagicMock()
        mock_job_result.scalar_one_or_none.return_value = job_offer
        
        self.mock_db.execute.side_effect = [mock_candidate_result, mock_job_result]
        
        # Mock de la création d'application
        with patch.object(self.application_service, '_create_application_instance') as mock_create:
            mock_application = Application(
                id="application-id",
                candidate_id="candidate-id",
                job_offer_id="job-offer-id",
                cover_letter="Lettre de motivation",
                motivation="Ma motivation"
            )
            mock_create.return_value = mock_application
            
            result = await self.application_service.create_application(application_data)
            
            assert result == mock_application
            self.mock_db.execute.assert_called()
            self.mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_create_application_candidate_not_found(self):
        """Test la création d'une candidature avec un candidat inexistant."""
        application_data = ApplicationCreate(
            candidate_id="nonexistent-candidate",
            job_offer_id="job-offer-id",
            cover_letter="Lettre de motivation"
        )
        
        # Mock - candidat non trouvé
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute.return_value = mock_result
        
        with pytest.raises(ValidationError, match="Candidat non trouvé"):
            await self.application_service.create_application(application_data)
    
    @pytest.mark.asyncio
    async def test_create_application_job_offer_not_found(self):
        """Test la création d'une candidature avec une offre d'emploi inexistante."""
        application_data = ApplicationCreate(
            candidate_id="candidate-id",
            job_offer_id="nonexistent-job",
            cover_letter="Lettre de motivation"
        )
        
        candidate = User(
            id="candidate-id",
            email="candidate@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        
        # Mock - candidat trouvé, offre non trouvée
        mock_candidate_result = MagicMock()
        mock_candidate_result.scalar_one_or_none.return_value = candidate
        
        mock_job_result = MagicMock()
        mock_job_result.scalar_one_or_none.return_value = None
        
        self.mock_db.execute.side_effect = [mock_candidate_result, mock_job_result]
        
        with pytest.raises(ValidationError, match="Offre d'emploi non trouvée"):
            await self.application_service.create_application(application_data)
    
    @pytest.mark.asyncio
    async def test_create_application_already_exists(self):
        """Test la création d'une candidature qui existe déjà."""
        application_data = ApplicationCreate(
            candidate_id="candidate-id",
            job_offer_id="job-offer-id",
            cover_letter="Lettre de motivation"
        )
        
        candidate = User(
            id="candidate-id",
            email="candidate@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        
        job_offer = JobOffer(
            id="job-offer-id",
            title="Développeur Python",
            description="Description",
            location="Paris",
            contract_type="CDI",
            recruiter_id="recruiter-id"
        )
        
        existing_application = Application(
            id="existing-application-id",
            candidate_id="candidate-id",
            job_offer_id="job-offer-id"
        )
        
        # Mock - candidat et offre trouvés, candidature existe déjà
        mock_candidate_result = MagicMock()
        mock_candidate_result.scalar_one_or_none.return_value = candidate
        
        mock_job_result = MagicMock()
        mock_job_result.scalar_one_or_none.return_value = job_offer
        
        mock_existing_result = MagicMock()
        mock_existing_result.scalar_one_or_none.return_value = existing_application
        
        self.mock_db.execute.side_effect = [mock_candidate_result, mock_job_result, mock_existing_result]
        
        with pytest.raises(BusinessLogicError, match="Une candidature existe déjà pour cette offre"):
            await self.application_service.create_application(application_data)
    
    @pytest.mark.asyncio
    async def test_update_application_success(self):
        """Test la mise à jour réussie d'une candidature."""
        application_id = "application-id"
        update_data = ApplicationUpdate(
            cover_letter="Nouvelle lettre de motivation",
            motivation="Nouvelle motivation"
        )
        
        existing_application = Application(
            id=application_id,
            candidate_id="candidate-id",
            job_offer_id="job-offer-id",
            cover_letter="Ancienne lettre",
            motivation="Ancienne motivation"
        )
        
        # Mock - application trouvée
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_application
        self.mock_db.execute.return_value = mock_result
        
        result = await self.application_service.update_application(application_id, update_data)
        
        assert result.cover_letter == "Nouvelle lettre de motivation"
        assert result.motivation == "Nouvelle motivation"
        self.mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_update_application_not_found(self):
        """Test la mise à jour d'une candidature inexistante."""
        application_id = "nonexistent-application"
        update_data = ApplicationUpdate(cover_letter="Nouvelle lettre")
        
        # Mock - application non trouvée
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute.return_value = mock_result
        
        with pytest.raises(ValidationError, match="Candidature non trouvée"):
            await self.application_service.update_application(application_id, update_data)
    
    @pytest.mark.asyncio
    async def test_get_application_by_id_success(self):
        """Test la récupération d'une candidature par ID."""
        application_id = "application-id"
        
        application = Application(
            id=application_id,
            candidate_id="candidate-id",
            job_offer_id="job-offer-id",
            cover_letter="Lettre de motivation"
        )
        
        # Mock - application trouvée
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = application
        self.mock_db.execute.return_value = mock_result
        
        result = await self.application_service.get_application_by_id(application_id)
        
        assert result == application
        self.mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_application_by_id_not_found(self):
        """Test la récupération d'une candidature inexistante."""
        application_id = "nonexistent-application"
        
        # Mock - application non trouvée
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute.return_value = mock_result
        
        result = await self.application_service.get_application_by_id(application_id)
        
        assert result is None
        self.mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_applications_by_candidate(self):
        """Test la récupération des candidatures d'un candidat."""
        candidate_id = "candidate-id"
        
        applications = [
            Application(
                id="app-1",
                candidate_id=candidate_id,
                job_offer_id="job-1",
                cover_letter="Lettre 1"
            ),
            Application(
                id="app-2",
                candidate_id=candidate_id,
                job_offer_id="job-2",
                cover_letter="Lettre 2"
            )
        ]
        
        # Mock - applications trouvées
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = applications
        self.mock_db.execute.return_value = mock_result
        
        result = await self.application_service.get_applications_by_candidate(candidate_id)
        
        assert len(result) == 2
        assert result[0].id == "app-1"
        assert result[1].id == "app-2"
        self.mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_application_status(self):
        """Test la mise à jour du statut d'une candidature."""
        application_id = "application-id"
        new_status = "accepted"
        
        application = Application(
            id=application_id,
            candidate_id="candidate-id",
            job_offer_id="job-offer-id",
            status="pending"
        )
        
        # Mock - application trouvée
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = application
        self.mock_db.execute.return_value = mock_result
        
        result = await self.application_service.update_application_status(application_id, new_status)
        
        assert result.status == new_status
        self.mock_db.commit.assert_called()
