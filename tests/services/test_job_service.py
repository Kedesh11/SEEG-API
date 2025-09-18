"""
Tests pour le service des offres d'emploi
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.job import JobService
from app.models.job_offer import JobOffer
from app.models.user import User
from app.schemas.job import JobOfferCreate, JobOfferUpdate
from app.core.exceptions import NotFoundError, ValidationError
import uuid


class TestJobService:
    """Tests pour le service des offres d'emploi."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock session de base de données."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def job_service(self, mock_db_session):
        """Instance du service JobService."""
        return JobService(mock_db_session)

    @pytest.fixture
    def sample_user(self):
        """Utilisateur de test."""
        user = Mock(spec=User)
        user.id = uuid.uuid4()
        user.role = "recruiter"
        user.email = "recruiter@test.com"
        return user

    @pytest.fixture
    def sample_job_offer_data(self):
        """Données d'offre d'emploi de test."""
        return JobOfferCreate(
            title="Développeur Python Senior",
            description="Développement d'applications Python avancées",
            location="Paris",
            contract_type="CDI",
            department="IT",
            salary_min=50000,
            salary_max=70000,
            requirements=["Python", "Django", "PostgreSQL"],
            benefits=["Mutuelle", "Tickets restaurant"],
            responsibilities=["Développement", "Architecture"]
        )

    @pytest.fixture
    def sample_job_offer(self):
        """Offre d'emploi de test."""
        job = Mock(spec=JobOffer)
        job.id = uuid.uuid4()
        job.title = "Développeur Python Senior"
        job.description = "Développement d'applications Python avancées"
        job.location = "Paris"
        job.contract_type = "CDI"
        job.department = "IT"
        job.salary_min = 50000
        job.salary_max = 70000
        job.requirements = ["Python", "Django", "PostgreSQL"]
        job.benefits = ["Mutuelle", "Tickets restaurant"]
        job.responsibilities = ["Développement", "Architecture"]
        job.status = "active"
        job.recruiter_id = uuid.uuid4()
        return job

    @pytest.mark.asyncio
    async def test_create_job_offer_success(self, job_service, mock_db_session, 
                                          sample_user, sample_job_offer_data, sample_job_offer):
        """Test création d'offre d'emploi avec succès."""
        # Arrange
        mock_db_session.add = Mock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()
        
        with patch('app.services.job.JobOffer') as mock_job_offer_class:
            mock_job_offer_class.return_value = sample_job_offer
            
            # Act
            result = await job_service.create_job_offer(sample_job_offer_data, sample_user.id)
            
            # Assert
            assert result == sample_job_offer
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_job_offer_validation_error(self, job_service, sample_user):
        """Test création d'offre d'emploi avec erreur de validation."""
        # Arrange
        invalid_data = JobOfferCreate(
            title="",  # Titre vide
            description="Description",
            location="Paris",
            contract_type="CDI",
            department="IT",
            salary_min=50000,
            salary_max=70000,
            requirements=[],
            benefits=[],
            responsibilities=[]
        )
        
        # Act & Assert
        with pytest.raises(ValidationError):
            await job_service.create_job_offer(invalid_data, sample_user.id)

    @pytest.mark.asyncio
    async def test_get_job_offers_success(self, job_service, mock_db_session, sample_job_offer):
        """Test récupération des offres d'emploi avec succès."""
        # Arrange
        mock_query = AsyncMock()
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_job_offer]
        mock_db_session.execute.return_value = mock_query
        
        # Act
        result = await job_service.get_job_offers(skip=0, limit=10)
        
        # Assert
        assert len(result) == 1
        assert result[0] == sample_job_offer

    @pytest.mark.asyncio
    async def test_get_job_offer_by_id_success(self, job_service, mock_db_session, sample_job_offer):
        """Test récupération d'une offre d'emploi par ID avec succès."""
        # Arrange
        job_id = sample_job_offer.id
        mock_query = AsyncMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_job_offer
        mock_db_session.execute.return_value = mock_query
        
        # Act
        result = await job_service.get_job_offer_by_id(job_id)
        
        # Assert
        assert result == sample_job_offer

    @pytest.mark.asyncio
    async def test_get_job_offer_by_id_not_found(self, job_service, mock_db_session):
        """Test récupération d'une offre d'emploi inexistante."""
        # Arrange
        job_id = uuid.uuid4()
        mock_query = AsyncMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db_session.execute.return_value = mock_query
        
        # Act & Assert
        with pytest.raises(NotFoundError):
            await job_service.get_job_offer_by_id(job_id)

    @pytest.mark.asyncio
    async def test_update_job_offer_success(self, job_service, mock_db_session, sample_job_offer):
        """Test mise à jour d'offre d'emploi avec succès."""
        # Arrange
        job_id = sample_job_offer.id
        update_data = JobOfferUpdate(title="Développeur Python Lead")
        
        mock_query = AsyncMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_job_offer
        mock_db_session.execute.return_value = mock_query
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()
        
        # Act
        result = await job_service.update_job_offer(job_id, update_data)
        
        # Assert
        assert result == sample_job_offer
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_job_offer_success(self, job_service, mock_db_session, sample_job_offer):
        """Test suppression d'offre d'emploi avec succès."""
        # Arrange
        job_id = sample_job_offer.id
        mock_query = AsyncMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_job_offer
        mock_db_session.execute.return_value = mock_query
        mock_db_session.delete = Mock()
        mock_db_session.commit = AsyncMock()
        
        # Act
        result = await job_service.delete_job_offer(job_id)
        
        # Assert
        assert result is True
        mock_db_session.delete.assert_called_once_with(sample_job_offer)
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_job_offers_by_recruiter_success(self, job_service, mock_db_session, 
                                                      sample_job_offer, sample_user):
        """Test récupération des offres d'emploi par recruteur avec succès."""
        # Arrange
        recruiter_id = sample_user.id
        mock_query = AsyncMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_job_offer]
        mock_db_session.execute.return_value = mock_query
        
        # Act
        result = await job_service.get_job_offers_by_recruiter(recruiter_id)
        
        # Assert
        assert len(result) == 1
        assert result[0] == sample_job_offer

    @pytest.mark.asyncio
    async def test_search_job_offers_success(self, job_service, mock_db_session, sample_job_offer):
        """Test recherche d'offres d'emploi avec succès."""
        # Arrange
        search_query = "python"
        location = "paris"
        mock_query = AsyncMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_job_offer]
        mock_db_session.execute.return_value = mock_query
        
        # Act
        result = await job_service.search_job_offers(search_query, location)
        
        # Assert
        assert len(result) == 1
        assert result[0] == sample_job_offer

    @pytest.mark.asyncio
    async def test_get_job_offer_statistics_success(self, job_service, mock_db_session):
        """Test récupération des statistiques d'offres d'emploi avec succès."""
        # Arrange
        mock_query = AsyncMock()
        mock_query.scalar.return_value = 10
        mock_db_session.execute.return_value = mock_query
        
        # Act
        result = await job_service.get_job_offer_statistics()
        
        # Assert
        assert "total" in result
        assert "active" in result
        assert "closed" in result
