"""
Tests pour les modèles de base
"""
import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import sessionmaker
from app.models.base import Base, UUIDMixin, TimestampMixin


class TestModel(UUIDMixin, TimestampMixin, Base):
    """Modèle de test pour les tests."""
    __tablename__ = 'test_model'
    
    name = Column(String(100), nullable=False)


class TestBase:
    """Tests pour la classe Base."""
    
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
    
    def test_base_tablename_generation(self):
        """Test que le nom de table est généré automatiquement."""
        assert TestModel.__tablename__ == 'testmodel'
    
    def test_uuid_mixin_id_generation(self):
        """Test que l'ID UUID est généré automatiquement."""
        test_obj = TestModel(name="test")
        self.session.add(test_obj)
        self.session.commit()
        
        assert test_obj.id is not None
        assert isinstance(test_obj.id, uuid.UUID)
    
    def test_timestamp_mixin_creation(self):
        """Test que les timestamps sont créés automatiquement."""
        test_obj = TestModel(name="test")
        self.session.add(test_obj)
        self.session.commit()
        
        assert test_obj.created_at is not None
        assert isinstance(test_obj.created_at, datetime)
    
    def test_timestamp_mixin_update(self):
        """Test que le timestamp de modification est mis à jour."""
        test_obj = TestModel(name="test")
        self.session.add(test_obj)
        self.session.commit()
        
        original_updated = test_obj.updated_at
        test_obj.name = "updated"
        self.session.commit()
        
        assert test_obj.updated_at > original_updated
