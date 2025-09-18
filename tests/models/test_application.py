"""
Tests pour le modèle Application
"""
import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.application import Application
from app.models.user import User
from app.models.job_offer import JobOffer


class TestApplication:
    """Tests pour le modèle Application."""
    
    def setup_method(self):
        """Configuration pour chaque test."""
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Créer des données de test
        self.candidate = User(
            email="candidate@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        self.recruiter = User(
            email="recruiter@example.com",
            first_name="Jane",
            last_name="Smith",
            role="recruiter"
        )
        self.job_offer = JobOffer(
            title="Développeur Python",
            description="Poste de développeur",
            recruiter_id=self.recruiter.id
        )
        
        self.session.add_all([self.candidate, self.recruiter, self.job_offer])
        self.session.commit()
    
    def teardown_method(self):
        """Nettoyage après chaque test."""
        self.session.close()
        Base.metadata.drop_all(self.engine)
    
    def test_application_creation(self):
        """Test la création d'une candidature."""
        application = Application(
            candidate_id=self.candidate.id,
            job_offer_id=self.job_offer.id,
            cover_letter="Lettre de motivation",
            motivation="Ma motivation"
        )
        self.session.add(application)
        self.session.commit()
        
        assert application.id is not None
        assert application.candidate_id == self.candidate.id
        assert application.job_offer_id == self.job_offer.id
        assert application.status == "pending"
        assert application.cover_letter == "Lettre de motivation"
        assert application.motivation == "Ma motivation"
    
    def test_application_default_status(self):
        """Test que le statut par défaut est 'pending'."""
        application = Application(
            candidate_id=self.candidate.id,
            job_offer_id=self.job_offer.id
        )
        self.session.add(application)
        self.session.commit()
        
        assert application.status == "pending"
    
    def test_application_mtp_answers(self):
        """Test le stockage des réponses MTP."""
        mtp_answers = {
            "metier": {
                "q1": "Réponse 1",
                "q2": "Réponse 2",
                "q3": "Réponse 3"
            },
            "paradigme": {
                "q1": "Réponse 1",
                "q2": "Réponse 2",
                "q3": "Réponse 3"
            },
            "talent": {
                "q1": "Réponse 1",
                "q2": "Réponse 2",
                "q3": "Réponse 3"
            }
        }
        
        application = Application(
            candidate_id=self.candidate.id,
            job_offer_id=self.job_offer.id,
            mtp_answers=mtp_answers
        )
        self.session.add(application)
        self.session.commit()
        
        assert application.mtp_answers == mtp_answers
    
    def test_application_individual_mtp_fields(self):
        """Test les champs MTP individuels."""
        application = Application(
            candidate_id=self.candidate.id,
            job_offer_id=self.job_offer.id,
            mtp_metier_q1="Réponse métier 1",
            mtp_metier_q2="Réponse métier 2",
            mtp_metier_q3="Réponse métier 3",
            mtp_paradigme_q1="Réponse paradigme 1",
            mtp_paradigme_q2="Réponse paradigme 2",
            mtp_paradigme_q3="Réponse paradigme 3",
            mtp_talent_q1="Réponse talent 1",
            mtp_talent_q2="Réponse talent 2",
            mtp_talent_q3="Réponse talent 3"
        )
        self.session.add(application)
        self.session.commit()
        
        assert application.mtp_metier_q1 == "Réponse métier 1"
        assert application.mtp_metier_q2 == "Réponse métier 2"
        assert application.mtp_metier_q3 == "Réponse métier 3"
        assert application.mtp_paradigme_q1 == "Réponse paradigme 1"
        assert application.mtp_paradigme_q2 == "Réponse paradigme 2"
        assert application.mtp_paradigme_q3 == "Réponse paradigme 3"
        assert application.mtp_talent_q1 == "Réponse talent 1"
        assert application.mtp_talent_q2 == "Réponse talent 2"
        assert application.mtp_talent_q3 == "Réponse talent 3"
    
    def test_application_availability(self):
        """Test la gestion de la disponibilité."""
        availability_date = datetime(2024, 6, 1)
        application = Application(
            candidate_id=self.candidate.id,
            job_offer_id=self.job_offer.id,
            availability_start=availability_date
        )
        self.session.add(application)
        self.session.commit()
        
        assert application.availability_start == availability_date
    
    def test_application_urls(self):
        """Test les URLs optionnelles."""
        application = Application(
            candidate_id=self.candidate.id,
            job_offer_id=self.job_offer.id,
            url_idee_projet="https://example.com/projet",
            url_lettre_integrite="https://example.com/integrite"
        )
        self.session.add(application)
        self.session.commit()
        
        assert application.url_idee_projet == "https://example.com/projet"
        assert application.url_lettre_integrite == "https://example.com/integrite"
    
    def test_application_foreign_keys(self):
        """Test que les clés étrangères sont correctement définies."""
        application = Application(
            candidate_id=self.candidate.id,
            job_offer_id=self.job_offer.id
        )
        self.session.add(application)
        self.session.commit()
        
        # Vérifier les relations
        assert application.candidate == self.candidate
        assert application.job_offer == self.job_offer
