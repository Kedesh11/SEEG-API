"""
Runner de tests principal avec rapports détaillés
Execute tous les tests et génère un rapport complet

Usage:
    python run_tests.py                    # Tests locaux
    python run_tests.py --env production   # Tests production
    python run_tests.py --verbose          # Mode verbeux
    python run_tests.py --module auth      # Tests d'un module spécifique
"""
import subprocess
import sys
import argparse
from pathlib import Path
from datetime import datetime
import json


class TestRunner:
    """
    Runner de tests avec rapports
    
    Principes SOLID:
    - Single Responsibility: Exécution et rapport
    - Open/Closed: Extensible via nouveaux modules
    - Dependency Inversion: Config injectable
    """
    
    def __init__(self, env: str = "local", verbose: bool = False, module: str | None = None):
        self.env = env
        self.verbose = verbose
        self.module = module
        self.start_time = datetime.now()
        self.results = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
            "duration": 0
        }
    
    def get_test_pattern(self) -> str:
        """Retourne le pattern de tests à exécuter"""
        if self.module:
            return f"tests/test_{self.module}_complete.py"
        return "tests/"  # Pytest découvrira automatiquement tous les fichiers test_*.py
    
    def run_tests(self) -> int:
        """
        Exécute les tests avec pytest
        
        Returns:
            int: Code de sortie (0 = succès, autre = échec)
        """
        print("\n" + "="*80)
        print("  🧪 RUNNER DE TESTS - SEEG API")
        print("="*80)
        print(f"\n📋 Configuration:")
        print(f"   Environnement: {self.env}")
        print(f"   Mode verbeux: {self.verbose}")
        print(f"   Module: {self.module or 'Tous'}")
        print(f"   Pattern: {self.get_test_pattern()}")
        print()
        
        # Préparer la commande pytest
        cmd = [
            sys.executable,
            "-m", "pytest",
            self.get_test_pattern(),
            "-v" if self.verbose else "-q",
            "--tb=short",
            f"--junit-xml=test-results-{self.env}.xml",
            "-o", "addopts="  # Éviter les options du pyproject.toml
        ]
        
        # Variables d'environnement
        import os
        env_vars = os.environ.copy()
        env_vars['TEST_ENV'] = self.env
        
        try:
            # Exécuter pytest
            result = subprocess.run(
                cmd,
                env=env_vars,
                capture_output=False,
                text=True
            )
            
            return result.returncode
            
        except KeyboardInterrupt:
            print("\n⚠️  Tests interrompus par l'utilisateur")
            return 130
        except Exception as e:
            print(f"\n❌ Erreur fatale: {e}")
            return 1
    
    def generate_report(self, exit_code: int):
        """Génère un rapport final"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        print("\n" + "="*80)
        print("  📊 RAPPORT DE TESTS")
        print("="*80)
        print(f"  Début: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Durée: {duration:.2f}s")
        print(f"  Environnement: {self.env}")
        print(f"  Résultat: {'✅ SUCCÈS' if exit_code == 0 else '❌ ÉCHEC'}")
        print(f"  Rapport XML: test-results-{self.env}.xml")
        print("="*80)
        print()


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="Runner de tests SEEG API avec rapports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python run_tests.py                       # Tests locaux
  python run_tests.py --env production      # Tests production
  python run_tests.py --module auth         # Tests authentification uniquement
  python run_tests.py --verbose             # Mode verbeux
  python run_tests.py --module applications --env production
        """
    )
    
    parser.add_argument(
        "--env",
        choices=["local", "production"],
        default="local",
        help="Environnement de test"
    )
    
    parser.add_argument(
        "--module",
        choices=["auth", "applications", "access_requests", "job_offers", "users", "notifications"],
        help="Module spécifique à tester"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mode verbeux"
    )
    
    args = parser.parse_args()
    
    # Créer et exécuter le runner
    runner = TestRunner(
        env=args.env,
        verbose=args.verbose,
        module=args.module
    )
    
    exit_code = runner.run_tests()
    runner.generate_report(exit_code)
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

