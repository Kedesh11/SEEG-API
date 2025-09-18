"""
Tests pour le modèle Notification
"""
import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.notification import Notification
from app.models.user import User
from app.models.application import Application
from app.models.job_offer import JobOffer


class TestNotification:
    """Tests pour le modèle Notification."""
    
    def setup_method(self):
        """Configuration pour chaque test."""
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Créer des données de test
        self.user = User(
            email="user@example.com",
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
            description="Description",
            location="Paris",
            contract_type="CDI",
            recruiter_id=self.recruiter.id
        )
        
        self.application = Application(
            candidate_id=self.user.id,
            job_offer_id=self.job_offer.id
        )
        
        self.session.add_all([self.user, self.recruiter, self.job_offer, self.application])
        self.session.commit()
    
    def teardown_method(self):
        """Nettoyage après chaque test."""
        self.session.close()
        Base.metadata.drop_all(self.engine)
    
    def test_notification_creation(self):
        """Test la création d'une notification."""
        notification = Notification(
            user_id=self.user.id,
            title="Nouvelle candidature",
            message="Votre candidature a été reçue",
            type="application_status"
        )
        self.session.add(notification)
        self.session.commit()
        
        assert notification.id is not None
        assert notification.user_id == self.user.id
        assert notification.title == "Nouvelle candidature"
        assert notification.message == "Votre candidature a été reçue"
        assert notification.type == "application_status"
        assert notification.read == False
    
    def test_notification_with_application(self):
        """Test une notification liée à une candidature."""
        notification = Notification(
            user_id=self.user.id,
            title="Statut de candidature",
            message="Votre candidature a été mise à jour",
            type="application_status",
            application_id=self.application.id
        )
        self.session.add(notification)
        self.session.commit()
        
        assert notification.application_id == self.application.id
        assert notification.application == self.application
    
    def test_notification_types(self):
        """Test différents types de notifications."""
        types = ["application_status", "interview_scheduled", "evaluation_complete", "system"]
        
        for notification_type in types:
            notification = Notification(
                user_id=self.user.id,
                title=f"Notification {notification_type}",
                message=f"Message pour {notification_type}",
                type=notification_type
            )
            self.session.add(notification)
            self.session.commit()
            
            assert notification.type == notification_type
            self.session.delete(notification)
            self.session.commit()
    
    def test_notification_read_status(self):
        """Test le statut de lecture des notifications."""
        notification = Notification(
            user_id=self.user.id,
            title="Test notification",
            message="Message de test",
            type="system"
        )
        self.session.add(notification)
        self.session.commit()
        
        # Par défaut, non lue
        assert notification.read == False
        
        # Marquer comme lue
        notification.read = True
        self.session.commit()
        assert notification.read == True
    
    def test_notification_timestamps(self):
        """Test que les timestamps sont correctement gérés."""
        notification = Notification(
            user_id=self.user.id,
            title="Test notification",
            message="Message de test",
            type="system"
        )
        self.session.add(notification)
        self.session.commit()
        
        assert notification.created_at is not None
        assert isinstance(notification.created_at, datetime)
        
        # Mise à jour
        original_updated = notification.updated_at
        notification.read = True
        self.session.commit()
        
        assert notification.updated_at > original_updated
    
    def test_notification_foreign_keys(self):
        """Test que les clés étrangères sont correctement définies."""
        notification = Notification(
            user_id=self.user.id,
            title="Test notification",
            message="Message de test",
            type="system",
            application_id=self.application.id
        )
        self.session.add(notification)
        self.session.commit()
        
        # Vérifier les relations
        assert notification.user == self.user
        assert notification.application == self.application
