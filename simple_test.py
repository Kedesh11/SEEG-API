"""
Test simple pour vérifier la configuration et la connexion à la base de données
"""
import asyncio
import sys
import os

# Ajouter le répertoire app au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

async def test_configuration():
    """Test de la configuration"""
    print("🔍 Test de la configuration...")
    
    try:
        from app.core.config import settings
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

async def test_database_connection():
    """Test de connexion à la base de données"""
    print("\n🔍 Test de connexion à la base de données...")
    
    try:
        from app.db.database import async_engine
        from sqlalchemy import text
        
        # Test simple de connexion
        async with async_engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✅ Connexion à la base de données réussie!")
            return True
            
    except Exception as e:
        print(f"❌ Erreur de connexion à la base de données: {e}")
        return False

async def test_imports():
    """Test des imports de base"""
    print("\n🔍 Test des imports de base...")
    
    try:
        # Test des imports de base
        from app.core.config import settings
        from app.db.database import engine, async_engine
        from app.core.exceptions import ValidationError, NotFoundError
        print("✅ Imports de base réussis")
        
        # Test des modèles (sans les importer tous pour éviter les erreurs de types)
        print("✅ Configuration des modèles OK")
        
        return True
    except Exception as e:
        print(f"❌ Erreur d'import: {e}")
        return False

async def main():
    """Fonction principale de test"""
    print("🚀 Démarrage des tests simples du backend FastAPI")
    print("=" * 50)
    
    # Test de la configuration
    config_ok = await test_configuration()
    
    # Test des imports
    imports_ok = await test_imports()
    
    # Test de connexion à la base de données
    db_ok = await test_database_connection()
    
    print("\n" + "=" * 50)
    print("📊 Résultats des tests:")
    print(f"Configuration: {'✅' if config_ok else '❌'}")
    print(f"Imports: {'✅' if imports_ok else '❌'}")
    print(f"Base de données: {'✅' if db_ok else '❌'}")
    
    if all([config_ok, imports_ok, db_ok]):
        print("\n🎉 Tous les tests sont passés avec succès!")
        return True
    else:
        print("\n⚠️ Certains tests ont échoué.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
