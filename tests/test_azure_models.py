"""
Tests des modèles avec la base de données Azure
"""
import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.user import User
from app.models.job_offer import JobOffer
from app.models.application import Application
from app.core.config.config import settings


class TestAzureModels:
    """Tests des modèles avec la base de données Azure."""
    
    def setup_method(self):
        """Configuration pour chaque test."""
        self.engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def teardown_method(self):
        """Nettoyage après chaque test."""
        self.session.close()
    
    def test_create_user_azure(self):
        """Test la création d'un utilisateur dans Azure."""
        try:
            # Créer un utilisateur de test avec un email unique
            test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
            
            user = User(
                email=test_email,
                first_name="Test",
                last_name="User",
                role="candidate"
            )
            
            self.session.add(user)
            self.session.commit()
            
            # Vérifier que l'utilisateur a été créé
            assert user.id is not None
            assert user.email == test_email
            assert user.first_name == "Test"
            assert user.role == "candidate"
            
            print(f"✅ Utilisateur créé avec succès: {user.email}")
            
            # Nettoyer - supprimer l'utilisateur de test
            self.session.delete(user)
            self.session.commit()
            print(f"✅ Utilisateur supprimé: {test_email}")
            
        except Exception as e:
            self.session.rollback()
            pytest.fail(f"❌ Erreur lors de la création de l'utilisateur: {e}")
    
    def test_create_job_offer_azure(self):
        """Test la création d'une offre d'emploi dans Azure."""
        try:
            # Créer un recruteur de test
            recruiter_email = f"recruiter_{uuid.uuid4().hex[:8]}@example.com"
            recruiter = User(
                email=recruiter_email,
                first_name="Test",
                last_name="Recruiter",
                role="recruiter"
            )
            self.session.add(recruiter)
            self.session.commit()
            
            # Créer une offre d'emploi de test
            job_offer = JobOffer(
                recruiter_id=recruiter.id,
                title=f"Test Job {uuid.uuid4().hex[:8]}",
                description="Description de test",
                location="Paris",
                contract_type="CDI"
            )
            
            self.session.add(job_offer)
            self.session.commit()
            
            # Vérifier que l'offre a été créée
            assert job_offer.id is not None
            assert job_offer.title.startswith("Test Job")
            assert job_offer.location == "Paris"
            assert job_offer.recruiter_id == recruiter.id
            
            print(f"✅ Offre d'emploi créée avec succès: {job_offer.title}")
            
            # Nettoyer - supprimer l'offre et le recruteur
            self.session.delete(job_offer)
            self.session.delete(recruiter)
            self.session.commit()
            print(f"✅ Offre d'emploi et recruteur supprimés")
            
        except Exception as e:
            self.session.rollback()
            pytest.fail(f"❌ Erreur lors de la création de l'offre d'emploi: {e}")
    
    def test_create_application_azure(self):
        """Test la création d'une candidature dans Azure."""
        try:
            # Créer un candidat de test
            candidate_email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
            candidate = User(
                email=candidate_email,
                first_name="Test",
                last_name="Candidate",
                role="candidate"
            )
            self.session.add(candidate)
            self.session.commit()
            
            # Créer un recruteur de test
            recruiter_email = f"recruiter_{uuid.uuid4().hex[:8]}@example.com"
            recruiter = User(
                email=recruiter_email,
                first_name="Test",
                last_name="Recruiter",
                role="recruiter"
            )
            self.session.add(recruiter)
            self.session.commit()
            
            # Créer une offre d'emploi de test
            job_offer = JobOffer(
                recruiter_id=recruiter.id,
                title=f"Test Job {uuid.uuid4().hex[:8]}",
                description="Description de test",
                location="Paris",
                contract_type="CDI"
            )
            self.session.add(job_offer)
            self.session.commit()
            
            # Créer une candidature de test
            application = Application(
                candidate_id=candidate.id,
                job_offer_id=job_offer.id,
                cover_letter="Lettre de motivation de test",
                motivation="Motivation de test"
            )
            
            self.session.add(application)
            self.session.commit()
            
            # Vérifier que la candidature a été créée
            assert application.id is not None
            assert application.candidate_id == candidate.id
            assert application.job_offer_id == job_offer.id
            assert application.cover_letter == "Lettre de motivation de test"
            assert application.status == "pending"
            
            print(f"✅ Candidature créée avec succès: {application.id}")
            
            # Nettoyer - supprimer tous les éléments de test
            self.session.delete(application)
            self.session.delete(job_offer)
            self.session.delete(recruiter)
            self.session.delete(candidate)
            self.session.commit()
            print(f"✅ Tous les éléments de test supprimés")
            
        except Exception as e:
            self.session.rollback()
            pytest.fail(f"❌ Erreur lors de la création de la candidature: {e}")
    
    def test_query_existing_users(self):
        """Test la requête des utilisateurs existants."""
        try:
            # Récupérer tous les utilisateurs
            users = self.session.query(User).limit(10).all()
            
            print(f"📊 Nombre d'utilisateurs récupérés: {len(users)}")
            
            for user in users:
                assert user.id is not None
                assert user.email is not None
                assert user.first_name is not None
                assert user.last_name is not None
                assert user.role is not None
                print(f"✅ Utilisateur: {user.email} ({user.role})")
                
        except Exception as e:
            pytest.fail(f"❌ Erreur lors de la requête des utilisateurs: {e}")
    
    def test_query_existing_job_offers(self):
        """Test la requête des offres d'emploi existantes."""
        try:
            # Récupérer toutes les offres d'emploi
            job_offers = self.session.query(JobOffer).limit(10).all()
            
            print(f"📊 Nombre d'offres d'emploi récupérées: {len(job_offers)}")
            
            for job_offer in job_offers:
                assert job_offer.id is not None
                assert job_offer.title is not None
                assert job_offer.description is not None
                assert job_offer.location is not None
                assert job_offer.contract_type is not None
                print(f"✅ Offre: {job_offer.title} ({job_offer.location})")
                
        except Exception as e:
            pytest.fail(f"❌ Erreur lors de la requête des offres d'emploi: {e}")
    
    def test_query_existing_applications(self):
        """Test la requête des candidatures existantes."""
        try:
            # Récupérer toutes les candidatures
            applications = self.session.query(Application).limit(10).all()
            
            print(f"📊 Nombre de candidatures récupérées: {len(applications)}")
            
            for application in applications:
                assert application.id is not None
                assert application.candidate_id is not None
                assert application.job_offer_id is not None
                assert application.status is not None
                print(f"✅ Candidature: {application.id} (statut: {application.status})")
                
        except Exception as e:
            pytest.fail(f"❌ Erreur lors de la requête des candidatures: {e}")
    
    def test_user_relationships(self):
        """Test les relations entre les modèles."""
        try:
            # Récupérer un utilisateur avec ses relations
            user = self.session.query(User).first()
            
            if user:
                print(f"✅ Utilisateur trouvé: {user.email}")
                
                # Vérifier les relations
                if hasattr(user, 'applications'):
                    print(f"📊 Nombre de candidatures: {len(user.applications)}")
                
                if hasattr(user, 'job_offers'):
                    print(f"📊 Nombre d'offres créées: {len(user.job_offers)}")
                
                if hasattr(user, 'candidate_profile'):
                    print(f"📊 Profil candidat: {'Oui' if user.candidate_profile else 'Non'}")
                    
            else:
                print("⚠️ Aucun utilisateur trouvé dans la base de données")
                
        except Exception as e:
            pytest.fail(f"❌ Erreur lors du test des relations: {e}")
