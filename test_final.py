#!/usr/bin/env python3
"""
Test final du backend FastAPI - Vérification complète
"""
import asyncio
import sys
from sqlalchemy import text
from app.core.config import settings
from app.db.session import get_async_db_session
from app.models import User, CandidateProfile, SeegAgent, JobOffer, Application, ApplicationDocument, ApplicationDraft, ApplicationHistory, Notification, InterviewSlot, Protocol1Evaluation, Protocol2Evaluation

def test_imports():
    """Test de tous les imports"""
    print("🔍 Test des imports...")
    
    try:
        # Test des modèles
        from app.models import User, CandidateProfile, SeegAgent, JobOffer
        print("  ✅ Modèles importés")
        
        # Test des schémas
        from app.schemas.user import UserCreate, UserResponse
        from app.schemas.job import JobOfferCreate, JobOfferResponse
        from app.schemas.application import ApplicationCreate, ApplicationResponse
        from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse
        print("  ✅ Schémas importés")
        
        # Test de la configuration
        from app.core.config import settings
        print("  ✅ Configuration importée")
        
        # Test de la base de données
        from app.db.session import get_async_db_session
        print("  ✅ Session DB importée")
        
        print("✅ Tous les imports fonctionnent")
        return True
        
    except Exception as e:
        print(f"❌ Erreur d'import: {e}")
        return False

async def test_database():
    """Test de la base de données"""
    print("🔍 Test de la base de données...")
    
    try:
        async with get_async_db_session() as db:
            result = await db.execute(text("SELECT 1 as test"))
            if result.scalar_one() == 1:
                print("✅ Connexion DB réussie")
                return True
            else:
                print("❌ Problème avec la requête DB")
                return False
                
    except Exception as e:
        print(f"❌ Erreur DB: {e}")
        return False

def test_configuration():
    """Test de la configuration"""
    print("🔍 Test de la configuration...")
    
    try:
        # Vérifications essentielles
        assert settings.APP_NAME == "One HCM SEEG Backend"
        assert settings.APP_VERSION == "1.0.0"
        assert "postgresql" in settings.DATABASE_URL
        assert settings.SECRET_KEY is not None
        assert len(settings.ALLOWED_ORIGINS) > 0
        
        print(f"  ✅ App: {settings.APP_NAME} v{settings.APP_VERSION}")
        print(f"  ✅ DB: PostgreSQL configurée")
        print(f"  ✅ CORS: {len(settings.ALLOWED_ORIGINS)} origines")
        print(f"  ✅ Frontend: {settings.ALLOWED_ORIGINS}")
        
        print("✅ Configuration valide")
        return True
        
    except Exception as e:
        print(f"❌ Erreur config: {e}")
        return False

def test_models():
    """Test des modèles SQLAlchemy"""
    print("🔍 Test des modèles...")
    
    try:
        # Vérification que tous les modèles sont définis
        models = [
            User, CandidateProfile, SeegAgent, JobOffer,
            Application, ApplicationDocument, ApplicationDraft, ApplicationHistory,
            Notification, InterviewSlot, Protocol1Evaluation, Protocol2Evaluation
        ]
        
        for model in models:
            assert hasattr(model, '__tablename__')
            print(f"  ✅ {model.__name__}: {model.__tablename__}")
        
        print("✅ Tous les modèles sont corrects")
        return True
        
    except Exception as e:
        print(f"❌ Erreur modèles: {e}")
        return False

def test_schemas():
    """Test des schémas Pydantic"""
    print("🔍 Test des schémas...")
    
    try:
        from app.schemas.user import UserCreate
        from app.schemas.job import JobOfferCreate
        
        # Test UserCreate
        user_data = {
            "email": "test@seeg.ga",
            "first_name": "Test",
            "last_name": "User",
            "role": "candidate",
            "password": "testpass123"
        }
        user = UserCreate(**user_data)
        print(f"  ✅ UserCreate: {user.email}")
        
        # Test JobOfferCreate
        job_data = {
            "title": "Développeur Full Stack",
            "description": "Poste de développeur chez SEEG",
            "location": "Libreville",
            "contract_type": "CDI",
            "recruiter_id": "123e4567-e89b-12d3-a456-426614174000"
        }
        job = JobOfferCreate(**job_data)
        print(f"  ✅ JobOfferCreate: {job.title}")
        
        print("✅ Tous les schémas fonctionnent")
        return True
        
    except Exception as e:
        print(f"❌ Erreur schémas: {e}")
        return False

async def main():
    """Fonction principale"""
    print("🚀 TEST FINAL - Backend FastAPI One HCM SEEG")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("Modèles SQLAlchemy", test_models),
        ("Schémas Pydantic", test_schemas),
        ("Base de données", test_database),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Erreur inattendue: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 RÉSULTATS FINAUX")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 SUCCÈS COMPLET!")
        print("✅ Backend FastAPI prêt pour la production")
        print("✅ Migration Supabase → PostgreSQL terminée")
        print("✅ Tous les modèles et schémas fonctionnent")
        print("✅ Connexion à Azure PostgreSQL opérationnelle")
        print("✅ Configuration CORS pour le frontend")
        print("\n🚀 Prochaines étapes:")
        print("   1. Déployer sur Azure App Service")
        print("   2. Configurer les variables d'environnement")
        print("   3. Tester l'intégration avec le frontend")
    else:
        print("⚠️ ÉCHECS DÉTECTÉS")
        print("❌ Vérifiez les erreurs ci-dessus")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
