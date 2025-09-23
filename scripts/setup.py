#!/usr/bin/env python3
"""
Script de configuration initiale du backend.
Respecte les principes de génie logiciel.
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config.config import settings
from app.db.database import create_tables_async
from app.core.logging.logging import LoggingConfig


async def setup_database():
    """Configure la base de données."""
    print("🗄️  Configuration de la base de données...")
    
    try:
        await create_tables_async()
        print("✅ Tables créées avec succès")
    except Exception as e:
        print(f"❌ Erreur lors de la création des tables: {e}")
        return False
    
    return True


def setup_alembic():
    """Configure Alembic pour les migrations."""
    print("🔄 Configuration d'Alembic...")
    
    try:
        # Initialisation d'Alembic
        subprocess.run(["alembic", "init", "app/db/migrations"], check=True)
        print("✅ Alembic initialisé")
        
        # Génération de la première migration
        subprocess.run(["alembic", "revision", "--autogenerate", "-m", "Initial migration"], check=True)
        print("✅ Migration initiale générée")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de la configuration d'Alembic: {e}")
        return False


def install_dependencies():
    """Installe les dépendances Python."""
    print("📦 Installation des dépendances...")
    
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("✅ Dépendances installées")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de l'installation des dépendances: {e}")
        return False


def setup_environment():
    """Configure l'environnement."""
    print("🔧 Configuration de l'environnement...")
    
    # Vérification du fichier .env
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            print("📝 Création du fichier .env à partir de .env.example")
            with open(".env.example", "r") as src, open(".env", "w") as dst:
                dst.write(src.read())
        else:
            print("⚠️  Fichier .env non trouvé. Veuillez le créer manuellement.")
            return False
    
    print("✅ Environnement configuré")
    return True


def setup_pre_commit():
    """Configure pre-commit hooks."""
    print("🪝 Configuration des hooks pre-commit...")
    
    try:
        subprocess.run(["pre-commit", "install"], check=True)
        print("✅ Hooks pre-commit installés")
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Pre-commit non disponible: {e}")
        return False


async def main():
    """Fonction principale de configuration."""
    print("🚀 Configuration du backend One HCM SEEG")
    print("=" * 50)
    
    # Configuration du logging
    LoggingConfig.setup_logging()
    
    steps = [
        ("Environnement", setup_environment),
        ("Dépendances", install_dependencies),
        ("Base de données", setup_database),
        ("Alembic", setup_alembic),
        ("Pre-commit", setup_pre_commit),
    ]
    
    success_count = 0
    
    for step_name, step_func in steps:
        print(f"\n📋 {step_name}...")
        try:
            if asyncio.iscoroutinefunction(step_func):
                result = await step_func()
            else:
                result = step_func()
            
            if result:
                success_count += 1
            else:
                print(f"❌ Échec de l'étape: {step_name}")
        except Exception as e:
            print(f"❌ Erreur lors de l'étape {step_name}: {e}")
    
    print("\n" + "=" * 50)
    print(f"🎉 Configuration terminée: {success_count}/{len(steps)} étapes réussies")
    
    if success_count == len(steps):
        print("\n✅ Le backend est prêt à être utilisé!")
        print("\n📝 Prochaines étapes:")
        print("1. Configurez vos variables d'environnement dans .env")
        print("2. Lancez le serveur avec: python -m uvicorn app.main:app --reload")
        print("3. Accédez à la documentation: http://localhost:8000/docs")
    else:
        print("\n⚠️  Certaines étapes ont échoué. Vérifiez les erreurs ci-dessus.")


if __name__ == "__main__":
    asyncio.run(main())
