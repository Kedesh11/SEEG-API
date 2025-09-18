"""
Script de test simple pour vérifier le backend FastAPI
"""
import asyncio
import sys
import os

# Ajouter le répertoire app au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings
from app.db.session import get_async_session
from app.services.job import JobService
from app.services.user import UserService
from app.schemas.job import JobOfferCreate
from app.schemas.user import UserCreate
from datetime import datetime, timedelta

async def test_database_connection():
    """Test de connexion à la base de données"""
    print("🔍 Test de connexion à la base de données...")
    
    try:
        async for session in get_async_session():
            # Test simple de connexion
            result = await session.execute("SELECT 1")
            print("✅ Connexion à la base de données réussie!")
            break
    except Exception as e:
        print(f"❌ Erreur de connexion à la base de données: {e}")
        return False
    
    return True

async def test_services():
    """Test des services"""
    print("\n🔍 Test des services...")
    
    try:
        async for session in get_async_session():
            # Test du service utilisateur
            user_service = UserService(session)
            print("✅ Service utilisateur initialisé")
            
            # Test du service job
            job_service = JobService(session)
            print("✅ Service job initialisé")
            
            # Test de récupération des statistiques
            job_count = await job_service.get_active_job_offers_count()
            print(f"✅ Nombre d'offres d'emploi actives: {job_count}")
            
            break
    except Exception as e:
        print(f"❌ Erreur lors du test des services: {e}")
        return False
    
    return True

async def test_configuration():
    """Test de la configuration"""
    print("\n🔍 Test de la configuration...")
    
    try:
        print(f"✅ Nom de l'application: {settings.APP_NAME}")
        print(f"✅ Version: {settings.APP_VERSION}")
        print(f"✅ Environnement: {settings.ENVIRONMENT}")
        print(f"✅ Debug: {settings.DEBUG}")
        print(f"✅ Base de données configurée: {bool(settings.DATABASE_URL)}")
        print(f"✅ Clé secrète configurée: {bool(settings.SECRET_KEY)}")
        
        return True
    except Exception as e:
        print(f"❌ Erreur de configuration: {e}")
        return False

async def main():
    """Fonction principale de test"""
    print("🚀 Démarrage des tests du backend FastAPI")
    print("=" * 50)
    
    # Test de la configuration
    config_ok = await test_configuration()
    
    # Test de connexion à la base de données
    db_ok = await test_database_connection()
    
    # Test des services
    services_ok = await test_services()
    
    print("\n" + "=" * 50)
    print("📊 Résultats des tests:")
    print(f"Configuration: {'✅' if config_ok else '❌'}")
    print(f"Base de données: {'✅' if db_ok else '❌'}")
    print(f"Services: {'✅' if services_ok else '❌'}")
    
    if all([config_ok, db_ok, services_ok]):
        print("\n🎉 Tous les tests sont passés avec succès!")
        return True
    else:
        print("\n⚠️ Certains tests ont échoué.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
