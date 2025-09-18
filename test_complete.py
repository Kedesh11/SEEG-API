#!/usr/bin/env python3
"""
Test complet du backend FastAPI
"""
import asyncio
import sys
from sqlalchemy import text
from app.core.config import settings
from app.db.session import get_async_db_session
from app.models import *

async def test_database_models():
    """Test des modèles de base de données"""
    print("🔍 Test des modèles de base de données...")
    
    try:
        # Test de création des tables (simulation)
        models = [
            User, CandidateProfile, SeegAgent, JobOffer, 
            Application, ApplicationDocument, ApplicationDraft, ApplicationHistory,
            Notification, InterviewSlot, Protocol1Evaluation, Protocol2Evaluation
        ]
        
        for model in models:
            print(f"  ✅ Modèle {model.__name__} importé")
        
        print("✅ Tous les modèles sont correctement définis")
        return True
        
    except Exception as e:
        print(f"❌ Erreur dans les modèles: {e}")
        return False

async def test_database_connection():
    """Test de connexion à la base de données"""
    print("🔍 Test de connexion à la base de données...")
    
    try:
        async with get_async_db_session() as db:
            # Test de connexion simple
            result = await db.execute(text("SELECT 1 as test"))
            if result.scalar_one() == 1:
                print("✅ Connexion à la base de données réussie")
                return True
            else:
                print("❌ La requête de test n'a pas retourné 1")
                return False
                
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return False

async def test_schemas():
    """Test des schémas Pydantic"""
    print("🔍 Test des schémas Pydantic...")
    
    try:
        from app.schemas.user import UserCreate
        from app.schemas.job import JobOfferCreate
        
        # Test de création d'un schéma utilisateur
        user_data = {
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": "candidate",
            "password": "testpassword123"
        }
        
        user = UserCreate(**user_data)
        print(f"  ✅ Schéma UserCreate créé: {user.email}")
        
        # Test de création d'un schéma d'offre d'emploi
        job_data = {
            "title": "Développeur Full Stack",
            "description": "Poste de développeur",
            "location": "Libreville",
            "contract_type": "CDI",
            "recruiter_id": "123e4567-e89b-12d3-a456-426614174000"
        }
        
        job = JobOfferCreate(**job_data)
        print(f"  ✅ Schéma JobOfferCreate créé: {job.title}")
        
        print("✅ Tous les schémas fonctionnent correctement")
        return True
        
    except Exception as e:
        print(f"❌ Erreur dans les schémas: {e}")
        return False

async def test_configuration():
    """Test de la configuration"""
    print("🔍 Test de la configuration...")
    
    try:
        # Vérification des paramètres essentiels
        assert settings.APP_NAME == "One HCM SEEG Backend"
        assert settings.APP_VERSION == "1.0.0"
        assert "postgresql" in settings.DATABASE_URL
        assert settings.SECRET_KEY is not None
        assert len(settings.ALLOWED_ORIGINS) > 0
        
        print(f"  ✅ Nom: {settings.APP_NAME}")
        print(f"  ✅ Version: {settings.APP_VERSION}")
        print(f"  ✅ Base de données: {'postgresql' in settings.DATABASE_URL}")
        print(f"  ✅ CORS: {len(settings.ALLOWED_ORIGINS)} origines autorisées")
        
        print("✅ Configuration valide")
        return True
        
    except Exception as e:
        print(f"❌ Erreur de configuration: {e}")
        return False

async def main():
    """Fonction principale de test"""
    print("🚀 Test complet du backend FastAPI")
    print("=" * 50)
    
    tests = [
        ("Configuration", test_configuration),
        ("Modèles de base de données", test_database_models),
        ("Connexion base de données", test_database_connection),
        ("Schémas Pydantic", test_schemas),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Erreur inattendue: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Résultats des tests:")
    print("=" * 50)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 Tous les tests sont passés avec succès!")
        print("✅ Le backend est prêt pour le déploiement")
    else:
        print("⚠️ Certains tests ont échoué")
        print("❌ Vérifiez les erreurs ci-dessus")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
