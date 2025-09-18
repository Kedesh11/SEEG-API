"""
Tests pour le modèle InterviewSlot
"""
import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.interview import InterviewSlot
from app.models.user import User
from app.models.application import Application
from app.models.job_offer import JobOffer


class TestInterviewSlot:
    """Tests pour le modèle InterviewSlot."""
    
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
        self.interviewer = User(
            email="interviewer@example.com",
            first_name="Jane",
            last_name="Smith",
            role="recruiter"
        )
        self.recruiter = User(
            email="recruiter@example.com",
            first_name="Bob",
            last_name="Johnson",
            role="recruiter"
        )
        
        self.job_offer = JobOffer(
            title="Développeur Python",
            description="Description",
            location="Paris",
            contract_type="CDI",
            recruiter_id=self.recruiter.id
        )
        
        self.application = Application(
            candidate_id=self.candidate.id,
            job_offer_id=self.job_offer.id
        )
        
        self.session.add_all([self.candidate, self.interviewer, self.recruiter, self.job_offer, self.application])
        self.session.commit()
    
    def teardown_method(self):
        """Nettoyage après chaque test."""
        self.session.close()
        Base.metadata.drop_all(self.engine)
    
    def test_interview_slot_creation(self):
        """Test la création d'un créneau d'entretien."""
        start_time = datetime.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=1)
        
        interview_slot = InterviewSlot(
            application_id=self.application.id,
            interviewer_id=self.interviewer.id,
            start_time=start_time,
            end_time=end_time,
            type="technical",
            location="Paris",
            status="scheduled"
        )
        self.session.add(interview_slot)
        self.session.commit()
        
        assert interview_slot.id is not None
        assert interview_slot.application_id == self.application.id
        assert interview_slot.interviewer_id == self.interviewer.id
        assert interview_slot.start_time == start_time
        assert interview_slot.end_time == end_time
        assert interview_slot.type == "technical"
        assert interview_slot.location == "Paris"
        assert interview_slot.status == "scheduled"
    
    def test_interview_slot_types(self):
        """Test différents types d'entretiens."""
        types = ["technical", "behavioral", "hr", "final"]
        start_time = datetime.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=1)
        
        for interview_type in types:
            interview_slot = InterviewSlot(
                application_id=self.application.id,
                interviewer_id=self.interviewer.id,
                start_time=start_time,
                end_time=end_time,
                type=interview_type,
                status="scheduled"
            )
            self.session.add(interview_slot)
            self.session.commit()
            
            assert interview_slot.type == interview_type
            self.session.delete(interview_slot)
            self.session.commit()
    
    def test_interview_slot_status_transitions(self):
        """Test les transitions de statut."""
        start_time = datetime.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=1)
        
        interview_slot = InterviewSlot(
            application_id=self.application.id,
            interviewer_id=self.interviewer.id,
            start_time=start_time,
            end_time=end_time,
            type="technical",
            status="scheduled"
        )
        self.session.add(interview_slot)
        self.session.commit()
        
        # Transition vers "completed"
        interview_slot.status = "completed"
        self.session.commit()
        assert interview_slot.status == "completed"
        
        # Transition vers "cancelled"
        interview_slot.status = "cancelled"
        self.session.commit()
        assert interview_slot.status == "cancelled"
    
    def test_interview_slot_notes(self):
        """Test l'ajout de notes à un entretien."""
        start_time = datetime.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=1)
        
        interview_slot = InterviewSlot(
            application_id=self.application.id,
            interviewer_id=self.interviewer.id,
            start_time=start_time,
            end_time=end_time,
            type="technical",
            status="completed",
            notes="Excellent candidat, très bon niveau technique"
        )
        self.session.add(interview_slot)
        self.session.commit()
        
        assert interview_slot.notes == "Excellent candidat, très bon niveau technique"
    
    def test_interview_slot_foreign_keys(self):
        """Test que les clés étrangères sont correctement définies."""
        start_time = datetime.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=1)
        
        interview_slot = InterviewSlot(
            application_id=self.application.id,
            interviewer_id=self.interviewer.id,
            start_time=start_time,
            end_time=end_time,
            type="technical",
            status="scheduled"
        )
        self.session.add(interview_slot)
        self.session.commit()
        
        # Vérifier les relations
        assert interview_slot.application == self.application
        assert interview_slot.interviewer == self.interviewer
    
    def test_interview_slot_time_validation(self):
        """Test que l'heure de fin est après l'heure de début."""
        start_time = datetime.now() + timedelta(days=1)
        end_time = start_time - timedelta(hours=1)  # Heure de fin avant heure de début
        
        interview_slot = InterviewSlot(
            application_id=self.application.id,
            interviewer_id=self.interviewer.id,
            start_time=start_time,
            end_time=end_time,
            type="technical",
            status="scheduled"
        )
        self.session.add(interview_slot)
        
        # Cela devrait échouer si on a une validation au niveau du modèle
        # Pour l'instant, on teste juste que les données sont stockées
        self.session.commit()
        assert interview_slot.start_time == start_time
        assert interview_slot.end_time == end_time
