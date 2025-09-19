#!/usr/bin/env python3
"""
Script pour exécuter tous les tests du projet One HCM SEEG (Version mise à jour)
"""
import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Exécute une commande et retourne True si elle réussit"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - RÉUSSI")
            if result.stdout:
                print(f"   Sortie: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} - ÉCHEC")
            if result.stderr:
                print(f"   Erreur: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description} - ERREUR: {e}")
        return False

def main():
    print("🚀 Démarrage de tous les tests du projet HCM-SEEG (Version mise à jour)")
    
    success = True
    
    # Tests de base
    success &= run_command(
        "python -m pytest tests/test_security.py -v --tb=short",
        "Tests de sécurité"
    )
    
    success &= run_command(
        "python -m pytest tests/test_connection.py -v --tb=short",
        "Tests de connexion"
    )
    
    success &= run_command(
        "python -m pytest tests/test_e2e.py -v --tb=short",
        "Tests end-to-end"
    )
    
    # Tests Azure
    success &= run_command(
        "python -m pytest tests/test_azure_*.py -v --tb=short",
        "Tests Azure"
    )
    
    # Tests des modèles
    success &= run_command(
        "python -m pytest tests/models/ -v --tb=short",
        "Tests des modèles"
    )
    
    # Tests des services
    success &= run_command(
        "python -m pytest tests/services/ -v --tb=short",
        "Tests des services"
    )
    
    # Tests d'API
    success &= run_command(
        "python -m pytest tests/api/ -v --tb=short",
        "Tests d'API"
    )
    
    # Tests spécifiques aux nouveaux endpoints
    success &= run_command(
        "python -m pytest tests/api/test_emails_endpoints.py -v --tb=short",
        "Tests des endpoints email"
    )
    
    success &= run_command(
        "python -m pytest tests/services/test_email.py -v --tb=short",
        "Tests du service email"
    )
    
    # Tests d'intégration
    success &= run_command(
        "python -m pytest tests/test_integration.py -v --tb=short",
        "Tests d'intégration"
    )
    
    # Tests d'amélioration
    success &= run_command(
        "python -m pytest tests/test_improvements.py -v --tb=short",
        "Tests d'amélioration"
    )
    
    # Tests d'endpoints optimisés
    success &= run_command(
        "python -m pytest tests/test_optimized_endpoints.py -v --tb=short",
        "Tests d'endpoints optimisés"
    )
    
    # Rapport de couverture
    print("\n📊 Génération du rapport de couverture...")
    run_command(
        "python -m pytest --cov=app --cov-report=html --cov-report=term-missing",
        "Rapport de couverture de code"
    )
    
    # Résumé final
    print("\n" + "="*60)
    if success:
        print("🎉 TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS !")
        print("✅ Le projet est prêt pour la production")
        print("📧 Les endpoints email sont fonctionnels")
    else:
        print("⚠️  CERTAINS TESTS ONT ÉCHOUÉ")
        print("❌ Veuillez corriger les erreurs avant de continuer")
    
    print("="*60)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
