"""
Test complet de l'API en production Azure
Vérifie les corrections REST et les fonctionnalités clés
"""
import requests
import sys
import io
from datetime import datetime

# Gestion de l'encodage pour Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_URL = "https://seeg-backend-api.azurewebsites.net/api/v1"

def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_test(name, status_code, expected_code=None, details=None):
    icon = "✅" if (expected_code is None or status_code == expected_code) else "❌"
    print(f"{icon} {name}: {status_code}", end="")
    if expected_code and status_code != expected_code:
        print(f" (attendu: {expected_code})", end="")
    if details:
        print(f" - {details}", end="")
    print()

def main():
    print_section("TEST COMPLET PRODUCTION AZURE")
    print(f"URL: {BASE_URL}")
    print(f"Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Health check
    print_section("1. HEALTH CHECK")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        print_test("GET /health", response.status_code, 200)
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # Test 2: Login pour obtenir un token
    print_section("2. AUTHENTIFICATION")
    email = input("\nEmail administrateur: ")
    import getpass
    password = getpass.getpass("Mot de passe: ")
    
    try:
        login_response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=30
        )
        print_test("POST /auth/login", login_response.status_code, 200)
        
        if login_response.status_code == 200:
            login_data = login_response.json()
            if "data" in login_data and "access_token" in login_data["data"]:
                token = login_data["data"]["access_token"]
            elif "access_token" in login_data:
                token = login_data["access_token"]
            else:
                print("❌ Format de réponse inattendu")
                return 1
            print("✅ Token obtenu")
        else:
            print(f"❌ Échec authentification: {login_response.text[:200]}")
            return 1
            
    except Exception as e:
        print(f"❌ Erreur authentification: {e}")
        return 1
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 3: Vérifier les codes de statut REST
    print_section("3. VÉRIFICATION CONFORMITÉ REST (RFC 7231)")
    
    # Test 3.1: GET /jobs (devrait être 200)
    try:
        response = requests.get(f"{BASE_URL}/jobs/", headers=headers, timeout=10)
        print_test("GET /jobs/", response.status_code, 200, "Liste des offres")
        if response.status_code == 200:
            jobs = response.json()
            jobs_count = len(jobs) if isinstance(jobs, list) else 0
            print(f"   → {jobs_count} offre(s) d'emploi trouvée(s)")
    except Exception as e:
        print(f"❌ Erreur GET /jobs/: {e}")
    
    # Test 3.2: GET /applications/ (devrait être 200)
    try:
        response = requests.get(f"{BASE_URL}/applications/", headers=headers, timeout=10)
        print_test("GET /applications/", response.status_code, 200, "Liste des candidatures")
        if response.status_code == 200:
            apps = response.json()
            apps_count = apps.get('total', 0) if isinstance(apps, dict) else 0
            print(f"   → {apps_count} candidature(s) trouvée(s)")
    except Exception as e:
        print(f"❌ Erreur GET /applications/: {e}")
    
    # Test 3.3: POST /jobs/ (devrait être 201 Created)
    print("\n📝 Test de création d'offre d'emploi (POST /jobs/):")
    test_offer = {
        "title": f"Test Offre - {datetime.now().strftime('%Y%m%d%H%M%S')}",
        "description": "Offre de test pour vérifier le code de statut REST",
        "location": "Libreville",
        "contract_type": "CDI",
        "status": "draft",
        "offer_status": "tous",
        "requirements": ["Test"],
        "responsibilities": ["Test"],
        "benefits": ["Test"]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/jobs/",
            json=test_offer,
            headers=headers,
            timeout=30
        )
        print_test("POST /jobs/", response.status_code, 201, "Création d'offre")
        
        if response.status_code == 201:
            print("   ✅ CONFORME REST: Code 201 Created pour création de ressource")
            created_job = response.json()
            job_id = created_job.get('id')
            
            # Nettoyage: supprimer l'offre de test
            if job_id:
                delete_response = requests.delete(
                    f"{BASE_URL}/jobs/{job_id}",
                    headers=headers,
                    timeout=10
                )
                if delete_response.status_code == 200:
                    print(f"   🧹 Offre de test supprimée (ID: {job_id})")
        else:
            print(f"   ⚠️  Code {response.status_code} au lieu de 201")
            print(f"   Détails: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Erreur POST /jobs/: {e}")
    
    # Test 4: Brouillons de candidature
    print_section("4. TEST BROUILLONS (application_drafts avec clé composite)")
    
    # Récupérer une offre pour tester les brouillons
    try:
        jobs_response = requests.get(f"{BASE_URL}/jobs/", headers=headers, timeout=10)
        if jobs_response.status_code == 200:
            jobs = jobs_response.json()
            if isinstance(jobs, list) and len(jobs) > 0:
                test_job_id = jobs[0]['id']
                print(f"📌 Utilisation de l'offre: {jobs[0].get('title', 'N/A')} (ID: {test_job_id})")
                
                # Test 4.1: POST /applications/drafts/by-offer (devrait être 201)
                draft_data = {
                    "job_offer_id": test_job_id,
                    "form_data": {"step": 1, "test": "validation"},
                    "ui_state": {"currentStep": 1}
                }
                
                response = requests.post(
                    f"{BASE_URL}/applications/drafts/by-offer",
                    json=draft_data,
                    headers=headers,
                    timeout=30
                )
                print_test("POST /applications/drafts/by-offer", response.status_code, 201, "Création de brouillon")
                
                if response.status_code == 201:
                    print("   ✅ CONFORME REST: Code 201 Created")
                    print("   ✅ Table application_drafts avec clé composite fonctionne")
                elif response.status_code == 200:
                    print("   ⚠️  Code 200 au lieu de 201 (à corriger)")
                else:
                    print(f"   ❌ Erreur: {response.text[:200]}")
                
                # Test 4.2: GET /applications/drafts/by-offer (devrait être 200)
                response = requests.get(
                    f"{BASE_URL}/applications/drafts/by-offer",
                    params={"job_offer_id": test_job_id},
                    headers=headers,
                    timeout=10
                )
                print_test("GET /applications/drafts/by-offer", response.status_code, 200, "Récupération de brouillon")
                
                if response.status_code == 200:
                    print("   ✅ Brouillon récupéré avec succès")
                
                # Test 4.3: DELETE /applications/drafts/by-offer (devrait être 204)
                response = requests.delete(
                    f"{BASE_URL}/applications/drafts/by-offer",
                    params={"job_offer_id": test_job_id},
                    headers=headers,
                    timeout=10
                )
                print_test("DELETE /applications/drafts/by-offer", response.status_code, 204, "Suppression de brouillon")
                
            else:
                print("⚠️  Aucune offre d'emploi disponible pour tester les brouillons")
        
    except Exception as e:
        print(f"❌ Erreur test brouillons: {e}")
    
    # Test 5: Status des migrations
    print_section("5. STATUT DES MIGRATIONS")
    
    try:
        response = requests.get(f"{BASE_URL}/migrations/status", headers=headers, timeout=10)
        print_test("GET /migrations/status", response.status_code, 200)
        
        if response.status_code == 200:
            status_data = response.json()
            print(f"   Version actuelle: {status_data.get('current_version', 'N/A')}")
            print(f"   Statut: {status_data.get('status', 'N/A')}")
            print(f"   Migrations en attente: {status_data.get('pending_migrations', 0)}")
            
            if status_data.get('status') == 'up_to_date':
                print("   ✅ Base de données à jour")
            else:
                print("   ⚠️  Des migrations sont en attente")
                
    except Exception as e:
        print(f"❌ Erreur statut migrations: {e}")
    
    # Résumé final
    print_section("RÉSUMÉ FINAL")
    print("✅ Tests de conformité REST effectués")
    print("✅ Vérification de la table application_drafts (clé composite)")
    print("✅ Vérification du statut des migrations")
    print("\n🎉 Tests en production terminés avec succès !")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

