"""
Tests pour le modèle User
"""
import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.user import User


class TestUser:
    """Tests pour le modèle User."""
    
    def setup_method(self):
        """Configuration pour chaque test."""
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def teardown_method(self):
        """Nettoyage après chaque test."""
        self.session.close()
        Base.metadata.drop_all(self.engine)
    
    def test_user_creation(self):
        """Test la création d'un utilisateur."""
        user = User(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        self.session.add(user)
        self.session.commit()
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.role == "candidate"
        assert user.created_at is not None
        assert user.updated_at is not None
    
    def test_user_email_unique(self):
        """Test que l'email doit être unique."""
        user1 = User(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        user2 = User(
            email="test@example.com",
            first_name="Jane",
            last_name="Smith",
            role="recruiter"
        )
        
        self.session.add(user1)
        self.session.commit()
        
        self.session.add(user2)
        with pytest.raises(Exception):  # IntegrityError
            self.session.commit()
    
    def test_user_matricule_unique(self):
        """Test que le matricule doit être unique."""
        user1 = User(
            email="test1@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate",
            matricule="MAT001"
        )
        user2 = User(
            email="test2@example.com",
            first_name="Jane",
            last_name="Smith",
            role="recruiter",
            matricule="MAT001"
        )
        
        self.session.add(user1)
        self.session.commit()
        
        self.session.add(user2)
        with pytest.raises(Exception):  # IntegrityError
            self.session.commit()
    
    def test_user_required_fields(self):
        """Test que les champs requis sont obligatoires."""
        # Test sans email
        user = User(
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        self.session.add(user)
        with pytest.raises(Exception):
            self.session.commit()
    
    def test_user_role_validation(self):
        """Test la validation des rôles."""
        valid_roles = ["candidate", "recruiter", "admin", "observer"]
        
        for role in valid_roles:
            user = User(
                email=f"test_{role}@example.com",
                first_name="John",
                last_name="Doe",
                role=role
            )
            self.session.add(user)
            self.session.commit()
            self.session.delete(user)
            self.session.commit()
    
    def test_user_optional_fields(self):
        """Test que les champs optionnels peuvent être vides."""
        user = User(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate",
            phone="+1234567890",
            date_of_birth=datetime(1990, 1, 1),
            sexe="M"
        )
        self.session.add(user)
        self.session.commit()
        
        assert user.phone == "+1234567890"
        assert user.date_of_birth == datetime(1990, 1, 1)
        assert user.sexe == "M"
    
    def test_user_timestamps(self):
        """Test que les timestamps sont mis à jour correctement."""
        user = User(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        self.session.add(user)
        self.session.commit()
        
        original_updated = user.updated_at
        user.first_name = "Jane"
        self.session.commit()
        
        assert user.updated_at > original_updated
