"""
Fichier de test global pour exécuter tous les tests
"""
import pytest
import sys
from pathlib import Path


def test_imports():
    """Test que tous les modules peuvent être importés."""
    try:
        # Test des modèles
        from app.models.base import Base, UUIDMixin, TimestampMixin
        from app.models.user import User
        from app.models.application import Application
        from app.models.job_offer import JobOffer
        from app.models.evaluation import Protocol1Evaluation, Protocol2Evaluation
        from app.models.notification import Notification
        from app.models.interview import InterviewSlot
        
        # Test des services
        from app.services.auth import AuthService
        from app.services.application import ApplicationService
        
        # Test des schémas
        from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse
        from app.schemas.application import ApplicationCreate, ApplicationUpdate
        
        # Test des utilitaires
        from app.utils.validators import validate_email, validate_password
        from app.utils.helpers import format_date, calculate_age
        
        print("✅ Tous les imports sont réussis")
        return True
        
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        return False


def test_basic_functionality():
    """Test des fonctionnalités de base."""
    try:
        # Test de validation d'email
        from app.utils.validators import validate_email
        assert validate_email("test@example.com") == True
        assert validate_email("invalid-email") == False
        
        # Test de validation de mot de passe
        from app.utils.validators import validate_password
        assert validate_password("Password123!") == True
        assert validate_password("weak") == False
        
        # Test de formatage de date
        from app.utils.helpers import format_date
        from datetime import date
        test_date = date(2024, 3, 15)
        assert format_date(test_date, "fr") == "15/03/2024"
        
        print("✅ Fonctionnalités de base testées avec succès")
        return True
        
    except Exception as e:
        print(f"❌ Erreur dans les fonctionnalités de base: {e}")
        return False


def test_model_creation():
    """Test de création des modèles."""
    try:
        from app.models.user import User
        from app.models.job_offer import JobOffer
        from app.models.application import Application
        
        # Test création utilisateur
        user = User(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role="candidate"
        )
        assert user.email == "test@example.com"
        assert user.first_name == "John"
        assert user.role == "candidate"
        
        # Test création offre d'emploi
        job_offer = JobOffer(
            title="Développeur Python",
            description="Description",
            location="Paris",
            contract_type="CDI",
            recruiter_id="recruiter-id"
        )
        assert job_offer.title == "Développeur Python"
        assert job_offer.location == "Paris"
        
        # Test création candidature
        application = Application(
            candidate_id="candidate-id",
            job_offer_id="job-offer-id",
            cover_letter="Lettre de motivation"
        )
        assert application.candidate_id == "candidate-id"
        assert application.cover_letter == "Lettre de motivation"
        
        print("✅ Création des modèles testée avec succès")
        return True
        
    except Exception as e:
        print(f"❌ Erreur dans la création des modèles: {e}")
        return False


def test_security_components():
    """Test des composants de sécurité."""
    try:
        from app.core.security.security import PasswordManager, TokenManager
        
        # Test gestionnaire de mots de passe
        password_manager = PasswordManager()
        password = "test_password_123"
        hashed = password_manager.hash_password(password)
        assert password_manager.verify_password(password, hashed) == True
        assert password_manager.verify_password("wrong_password", hashed) == False
        
        # Test gestionnaire de tokens
        token_manager = TokenManager()
        user_id = "user-123"
        access_token = token_manager.create_access_token(user_id)
        refresh_token = token_manager.create_refresh_token(user_id)
        
        assert access_token is not None
        assert refresh_token is not None
        
        # Vérification des tokens
        verified_user_id = token_manager.verify_access_token(access_token)
        assert verified_user_id == user_id
        
        print("✅ Composants de sécurité testés avec succès")
        return True
        
    except Exception as e:
        print(f"❌ Erreur dans les composants de sécurité: {e}")
        return False


def run_all_tests():
    """Exécute tous les tests."""
    print("🚀 Démarrage des tests globaux")
    print("=" * 50)
    
    tests = [
        ("Test des imports", test_imports),
        ("Test des fonctionnalités de base", test_basic_functionality),
        ("Test de création des modèles", test_model_creation),
        ("Test des composants de sécurité", test_security_components)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} - RÉUSSI")
            else:
                print(f"❌ {test_name} - ÉCHOUÉ")
        except Exception as e:
            print(f"❌ {test_name} - ERREUR: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Résultats: {passed}/{total} tests réussis")
    
    if passed == total:
        print("🎉 Tous les tests sont passés avec succès!")
        return True
    else:
        print("⚠️  Certains tests ont échoué.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
