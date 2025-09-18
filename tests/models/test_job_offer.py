"""
Tests pour le modèle JobOffer
"""
import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.job_offer import JobOffer
from app.models.user import User


class TestJobOffer:
    """Tests pour le modèle JobOffer."""
    
    def setup_method(self):
        """Configuration pour chaque test."""
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Créer un recruteur de test
        self.recruiter = User(
            email="recruiter@example.com",
            first_name="Jane",
            last_name="Smith",
            role="recruiter"
        )
        self.session.add(self.recruiter)
        self.session.commit()
    
    def teardown_method(self):
        """Nettoyage après chaque test."""
        self.session.close()
        Base.metadata.drop_all(self.engine)
    
    def test_job_offer_creation(self):
        """Test la création d'une offre d'emploi."""
        job_offer = JobOffer(
            recruiter_id=self.recruiter.id,
            title="Développeur Python",
            description="Développement d'applications Python",
            location="Paris",
            contract_type="CDI"
        )
        self.session.add(job_offer)
        self.session.commit()
        
        assert job_offer.id is not None
        assert job_offer.recruiter_id == self.recruiter.id
        assert job_offer.title == "Développeur Python"
        assert job_offer.description == "Développement d'applications Python"
        assert job_offer.location == "Paris"
        assert job_offer.contract_type == "CDI"
        assert job_offer.status == "active"
    
    def test_job_offer_required_fields(self):
        """Test que les champs requis sont obligatoires."""
        # Test sans title
        job_offer = JobOffer(
            recruiter_id=self.recruiter.id,
            description="Description",
            location="Paris",
            contract_type="CDI"
        )
        self.session.add(job_offer)
        with pytest.raises(Exception):
            self.session.commit()
    
    def test_job_offer_optional_fields(self):
        """Test que les champs optionnels peuvent être vides."""
        job_offer = JobOffer(
            recruiter_id=self.recruiter.id,
            title="Développeur Python",
            description="Description",
            location="Paris",
            contract_type="CDI",
            department="IT",
            salary_min=40000,
            salary_max=60000,
            requirements=["Python", "Django", "PostgreSQL"],
            benefits=["Mutuelle", "Tickets restaurant"],
            responsibilities=["Développement", "Tests", "Documentation"]
        )
        self.session.add(job_offer)
        self.session.commit()
        
        assert job_offer.department == "IT"
        assert job_offer.salary_min == 40000
        assert job_offer.salary_max == 60000
        assert job_offer.requirements == ["Python", "Django", "PostgreSQL"]
        assert job_offer.benefits == ["Mutuelle", "Tickets restaurant"]
        assert job_offer.responsibilities == ["Développement", "Tests", "Documentation"]
    
    def test_job_offer_deadlines(self):
        """Test la gestion des dates limites."""
        deadline = datetime(2024, 12, 31)
        start_date = datetime(2024, 1, 1)
        
        job_offer = JobOffer(
            recruiter_id=self.recruiter.id,
            title="Développeur Python",
            description="Description",
            location="Paris",
            contract_type="CDI",
            application_deadline=deadline,
            start_date=start_date
        )
        self.session.add(job_offer)
        self.session.commit()
        
        assert job_offer.application_deadline == deadline
        assert job_offer.start_date == start_date
    
    def test_job_offer_status(self):
        """Test la gestion du statut."""
        job_offer = JobOffer(
            recruiter_id=self.recruiter.id,
            title="Développeur Python",
            description="Description",
            location="Paris",
            contract_type="CDI",
            status="draft"
        )
        self.session.add(job_offer)
        self.session.commit()
        
        assert job_offer.status == "draft"
    
    def test_job_offer_foreign_key(self):
        """Test que la clé étrangère vers le recruteur est correcte."""
        job_offer = JobOffer(
            recruiter_id=self.recruiter.id,
            title="Développeur Python",
            description="Description",
            location="Paris",
            contract_type="CDI"
        )
        self.session.add(job_offer)
        self.session.commit()
        
        # Vérifier la relation
        assert job_offer.recruiter == self.recruiter
    
    def test_job_offer_timestamps(self):
        """Test que les timestamps sont mis à jour correctement."""
        job_offer = JobOffer(
            recruiter_id=self.recruiter.id,
            title="Développeur Python",
            description="Description",
            location="Paris",
            contract_type="CDI"
        )
        self.session.add(job_offer)
        self.session.commit()
        
        original_updated = job_offer.updated_at
        job_offer.title = "Développeur Senior Python"
        self.session.commit()
        
        assert job_offer.updated_at > original_updated
    
    def test_job_offer_json_fields(self):
        """Test le stockage de données JSON."""
        job_offer = JobOffer(
            recruiter_id=self.recruiter.id,
            title="Développeur Python",
            description="Description",
            location="Paris",
            contract_type="CDI",
            requirements=["Python", "Django", "PostgreSQL", "Docker"],
            benefits=["Mutuelle", "Tickets restaurant", "Télétravail"],
            responsibilities=["Développement", "Tests", "Documentation", "Code review"]
        )
        self.session.add(job_offer)
        self.session.commit()
        
        # Vérifier que les listes sont correctement stockées
        assert len(job_offer.requirements) == 4
        assert "Python" in job_offer.requirements
        assert len(job_offer.benefits) == 3
        assert "Télétravail" in job_offer.benefits
        assert len(job_offer.responsibilities) == 4
        assert "Code review" in job_offer.responsibilities
