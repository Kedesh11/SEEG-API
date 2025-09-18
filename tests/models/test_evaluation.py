"""
Tests pour les modèles d'évaluation
"""
import pytest
import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.evaluation import Protocol1Evaluation, Protocol2Evaluation
from app.models.user import User
from app.models.application import Application
from app.models.job_offer import JobOffer


class TestProtocol1Evaluation:
    """Tests pour le modèle Protocol1Evaluation."""
    
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
        self.evaluator = User(
            email="evaluator@example.com",
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
        
        self.session.add_all([self.candidate, self.evaluator, self.recruiter, self.job_offer, self.application])
        self.session.commit()
    
    def teardown_method(self):
        """Nettoyage après chaque test."""
        self.session.close()
        Base.metadata.drop_all(self.engine)
    
    def test_protocol1_evaluation_creation(self):
        """Test la création d'une évaluation Protocol 1."""
        evaluation = Protocol1Evaluation(
            application_id=self.application.id,
            evaluator_id=self.evaluator.id
        )
        self.session.add(evaluation)
        self.session.commit()
        
        assert evaluation.id is not None
        assert evaluation.application_id == self.application.id
        assert evaluation.evaluator_id == self.evaluator.id
        assert evaluation.status == "pending"
        assert evaluation.completed == False
        assert evaluation.documents_verified == False
    
    def test_protocol1_evaluation_documentary_scores(self):
        """Test l'enregistrement des scores documentaires."""
        evaluation = Protocol1Evaluation(
            application_id=self.application.id,
            evaluator_id=self.evaluator.id,
            cv_score=Decimal('8.5'),
            cv_comments="Excellent CV",
            diplomes_certificats_score=Decimal('9.0'),
            diplomes_certificats_comments="Diplômes pertinents",
            lettre_motivation_score=Decimal('7.5'),
            lettre_motivation_comments="Bonne motivation",
            documentary_score=Decimal('8.3')
        )
        self.session.add(evaluation)
        self.session.commit()
        
        assert evaluation.cv_score == Decimal('8.5')
        assert evaluation.cv_comments == "Excellent CV"
        assert evaluation.diplomes_certificats_score == Decimal('9.0')
        assert evaluation.diplomes_certificats_comments == "Diplômes pertinents"
        assert evaluation.lettre_motivation_score == Decimal('7.5')
        assert evaluation.lettre_motivation_comments == "Bonne motivation"
        assert evaluation.documentary_score == Decimal('8.3')
    
    def test_protocol1_evaluation_mtp_scores(self):
        """Test l'enregistrement des scores MTP."""
        evaluation = Protocol1Evaluation(
            application_id=self.application.id,
            evaluator_id=self.evaluator.id,
            metier_score=Decimal('8.0'),
            metier_comments="Très bon niveau technique",
            metier_notes="Expérience solide",
            paradigme_score=Decimal('7.5'),
            paradigme_comments="Bonne approche",
            paradigme_notes="Réflexion pertinente",
            talent_score=Decimal('8.5'),
            talent_comments="Talents évidents",
            talent_notes="Potentiel élevé",
            mtp_score=Decimal('8.0')
        )
        self.session.add(evaluation)
        self.session.commit()
        
        assert evaluation.metier_score == Decimal('8.0')
        assert evaluation.metier_comments == "Très bon niveau technique"
        assert evaluation.metier_notes == "Expérience solide"
        assert evaluation.paradigme_score == Decimal('7.5')
        assert evaluation.paradigme_comments == "Bonne approche"
        assert evaluation.paradigme_notes == "Réflexion pertinente"
        assert evaluation.talent_score == Decimal('8.5')
        assert evaluation.talent_comments == "Talents évidents"
        assert evaluation.talent_notes == "Potentiel élevé"
        assert evaluation.mtp_score == Decimal('8.0')
    
    def test_protocol1_evaluation_interview_scores(self):
        """Test l'enregistrement des scores d'entretien."""
        evaluation = Protocol1Evaluation(
            application_id=self.application.id,
            evaluator_id=self.evaluator.id,
            interview_metier_score=Decimal('8.5'),
            interview_metier_comments="Excellent entretien technique",
            interview_paradigme_score=Decimal('8.0'),
            interview_paradigme_comments="Bonne réflexion",
            interview_talent_score=Decimal('9.0'),
            interview_talent_comments="Talents confirmés"
        )
        self.session.add(evaluation)
        self.session.commit()
        
        assert evaluation.interview_metier_score == Decimal('8.5')
        assert evaluation.interview_metier_comments == "Excellent entretien technique"
        assert evaluation.interview_paradigme_score == Decimal('8.0')
        assert evaluation.interview_paradigme_comments == "Bonne réflexion"
        assert evaluation.interview_talent_score == Decimal('9.0')
        assert evaluation.interview_talent_comments == "Talents confirmés"
    
    def test_protocol1_evaluation_status_transitions(self):
        """Test les transitions de statut."""
        evaluation = Protocol1Evaluation(
            application_id=self.application.id,
            evaluator_id=self.evaluator.id
        )
        self.session.add(evaluation)
        self.session.commit()
        
        # Test transition vers "in_progress"
        evaluation.status = "in_progress"
        self.session.commit()
        assert evaluation.status == "in_progress"
        
        # Test transition vers "completed"
        evaluation.status = "completed"
        evaluation.completed = True
        self.session.commit()
        assert evaluation.status == "completed"
        assert evaluation.completed == True
    
    def test_protocol1_evaluation_foreign_keys(self):
        """Test que les clés étrangères sont correctement définies."""
        evaluation = Protocol1Evaluation(
            application_id=self.application.id,
            evaluator_id=self.evaluator.id
        )
        self.session.add(evaluation)
        self.session.commit()
        
        # Vérifier les relations
        assert evaluation.application == self.application
        assert evaluation.evaluator == self.evaluator
    
    def test_protocol1_evaluation_unique_application(self):
        """Test qu'une application ne peut avoir qu'une évaluation Protocol 1."""
        evaluation1 = Protocol1Evaluation(
            application_id=self.application.id,
            evaluator_id=self.evaluator.id
        )
        evaluation2 = Protocol1Evaluation(
            application_id=self.application.id,
            evaluator_id=self.evaluator.id
        )
        
        self.session.add(evaluation1)
        self.session.commit()
        
        self.session.add(evaluation2)
        with pytest.raises(Exception):  # IntegrityError
            self.session.commit()


class TestProtocol2Evaluation:
    """Tests pour le modèle Protocol2Evaluation."""
    
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
        self.evaluator = User(
            email="evaluator@example.com",
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
        
        self.session.add_all([self.candidate, self.evaluator, self.recruiter, self.job_offer, self.application])
        self.session.commit()
    
    def teardown_method(self):
        """Nettoyage après chaque test."""
        self.session.close()
        Base.metadata.drop_all(self.engine)
    
    def test_protocol2_evaluation_creation(self):
        """Test la création d'une évaluation Protocol 2."""
        evaluation = Protocol2Evaluation(
            application_id=self.application.id,
            evaluator_id=self.evaluator.id
        )
        self.session.add(evaluation)
        self.session.commit()
        
        assert evaluation.id is not None
        assert evaluation.application_id == self.application.id
        assert evaluation.evaluator_id == self.evaluator.id
        assert evaluation.status == "pending"
        assert evaluation.completed == False
    
    def test_protocol2_evaluation_scores(self):
        """Test l'enregistrement des scores Protocol 2."""
        evaluation = Protocol2Evaluation(
            application_id=self.application.id,
            evaluator_id=self.evaluator.id,
            technical_score=Decimal('8.5'),
            technical_comments="Excellent niveau technique",
            behavioral_score=Decimal('8.0'),
            behavioral_comments="Bonne attitude",
            cultural_fit_score=Decimal('9.0'),
            cultural_fit_comments="Parfait fit culturel",
            overall_score=Decimal('8.5')
        )
        self.session.add(evaluation)
        self.session.commit()
        
        assert evaluation.technical_score == Decimal('8.5')
        assert evaluation.technical_comments == "Excellent niveau technique"
        assert evaluation.behavioral_score == Decimal('8.0')
        assert evaluation.behavioral_comments == "Bonne attitude"
        assert evaluation.cultural_fit_score == Decimal('9.0')
        assert evaluation.cultural_fit_comments == "Parfait fit culturel"
        assert evaluation.overall_score == Decimal('8.5')
