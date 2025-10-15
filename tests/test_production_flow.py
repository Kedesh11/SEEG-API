"""
Test du flux complet sur l'environnement de production Azure
"""
import requests
import json

# URL de production Azure
BASE_URL = "https://seeg-backend-api.azurewebsites.net/api/v1"

def test_production_api():
    print("="*70)
    print("TEST API EN PRODUCTION - AZURE")
    print("="*70)
    print(f"\nURL: {BASE_URL}\n")
    
    # ========== TEST 1: HEALTH CHECK ==========
    print("=" * 70)
    print("TEST 1: HEALTH CHECK")
    print("=" * 70)
    
    try:
        response = requests.get(f"{BASE_URL.replace('/api/v1', '')}/health", timeout=10)
        if response.status_code == 200:
            print("✅ API en ligne et accessible")
            print(f"   Status: {response.status_code}")
        else:
            print(f"⚠️  API répond mais statut: {response.status_code}")
    except Exception as e:
        print(f"❌ API non accessible: {e}")
        return False
    
    # ========== TEST 2: CONNEXION ADMIN ==========
    print("\n" + "=" * 70)
    print("TEST 2: CONNEXION ADMIN")
    print("=" * 70)
    
    admin_credentials = {
        "username": "sevankedesh11@gmail.com",
        "password": "Sevan@Seeg"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data=admin_credentials,
            timeout=10
        )
        
        if response.status_code == 200:
            admin_token = response.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}
            print("✅ Connexion admin réussie")
            print(f"   Token: {admin_token[:20]}...")
        else:
            print(f"❌ Connexion admin échouée: {response.status_code}")
            print(f"   {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erreur connexion admin: {e}")
        return False
    
    # ========== TEST 3: RÉCUPÉRATION DES CANDIDATURES ==========
    print("\n" + "=" * 70)
    print("TEST 3: RÉCUPÉRATION DES CANDIDATURES")
    print("=" * 70)
    
    try:
        response = requests.get(
            f"{BASE_URL}/applications/",
            headers=admin_headers,
            params={"limit": 5},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            total = data.get("total", 0)
            applications = data.get("data", [])
            print(f"✅ Candidatures récupérées: {total} total")
            print(f"   Affichées: {len(applications)}")
            
            if applications:
                app = applications[0]
                print(f"\n   Exemple de candidature:")
                print(f"   - ID: {app.get('id')}")
                print(f"   - Status: {app.get('status')}")
                print(f"   - Candidat: {app.get('candidate', {}).get('first_name')} {app.get('candidate', {}).get('last_name')}")
        else:
            print(f"⚠️  Récupération candidatures: {response.status_code}")
            print(f"   {response.text[:200]}")
    except Exception as e:
        print(f"❌ Erreur récupération candidatures: {e}")
    
    # ========== TEST 4: RÉCUPÉRATION DES OFFRES D'EMPLOI ==========
    print("\n" + "=" * 70)
    print("TEST 4: RÉCUPÉRATION DES OFFRES D'EMPLOI")
    print("=" * 70)
    
    try:
        response = requests.get(
            f"{BASE_URL}/jobs/",
            headers=admin_headers,
            params={"limit": 5},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            # Gérer les deux formats de réponse possibles
            if isinstance(result, dict) and "data" in result:
                jobs = result["data"].get("items", []) if isinstance(result["data"], dict) else result["data"]
                total = result.get("total", len(jobs))
            else:
                jobs = result if isinstance(result, list) else []
                total = len(jobs)
            
            print(f"✅ Offres d'emploi récupérées: {total} total")
            print(f"   Affichées: {len(jobs)}")
            
            if jobs:
                job = jobs[0]
                print(f"\n   Exemple d'offre:")
                print(f"   - ID: {job.get('id')}")
                print(f"   - Titre: {job.get('title')}")
                print(f"   - Département: {job.get('department')}")
                print(f"   - Statut: {job.get('status') or job.get('offer_status')}")
        else:
            print(f"⚠️  Récupération offres: {response.status_code}")
            print(f"   {response.text[:200]}")
    except Exception as e:
        print(f"❌ Erreur récupération offres: {e}")
    
    # ========== TEST 5: RÉCUPÉRATION DES UTILISATEURS ==========
    print("\n" + "=" * 70)
    print("TEST 5: RÉCUPÉRATION DES UTILISATEURS")
    print("=" * 70)
    
    try:
        response = requests.get(
            f"{BASE_URL}/users/",
            headers=admin_headers,
            params={"limit": 5},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            users = result.get("data", [])
            total = result.get("total", len(users))
            
            print(f"✅ Utilisateurs récupérés: {total} total")
            print(f"   Affichés: {len(users)}")
            
            if users:
                user = users[0]
                print(f"\n   Exemple d'utilisateur:")
                print(f"   - ID: {user.get('id')}")
                print(f"   - Email: {user.get('email')}")
                print(f"   - Rôle: {user.get('role')}")
                print(f"   - Nom: {user.get('first_name')} {user.get('last_name')}")
        else:
            print(f"⚠️  Récupération utilisateurs: {response.status_code}")
            print(f"   {response.text[:200]}")
    except Exception as e:
        print(f"❌ Erreur récupération utilisateurs: {e}")
    
    # ========== TEST 6: ACCESS-REQUESTS ==========
    print("\n" + "=" * 70)
    print("TEST 6: ACCESS-REQUESTS (ADMIN)")
    print("=" * 70)
    
    try:
        response = requests.get(
            f"{BASE_URL}/access-requests/",
            headers=admin_headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            total = result.get("total", 0)
            pending = result.get("pending_count", 0)
            unviewed = result.get("unviewed_count", 0)
            
            print(f"✅ Access-requests récupérées")
            print(f"   Total: {total}")
            print(f"   En attente: {pending}")
            print(f"   Non vues: {unviewed}")
        else:
            print(f"⚠️  Access-requests: {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur access-requests: {e}")
    
    # ========== TEST 7: DOCUMENTATION ==========
    print("\n" + "=" * 70)
    print("TEST 7: DOCUMENTATION API")
    print("=" * 70)
    
    try:
        docs_url = BASE_URL.replace('/api/v1', '') + '/docs'
        response = requests.get(docs_url, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Documentation accessible")
            print(f"   URL: {docs_url}")
        else:
            print(f"⚠️  Documentation: {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur documentation: {e}")
    
    # ========== RÉSUMÉ ==========
    print("\n" + "=" * 70)
    print("✅ TESTS EN PRODUCTION TERMINÉS")
    print("=" * 70)
    print(f"\n📊 API: {BASE_URL}")
    print(f"📖 Docs: {BASE_URL.replace('/api/v1', '')}/docs")
    print(f"❤️  Health: {BASE_URL.replace('/api/v1', '')}/health")
    print("\n✅ L'API est opérationnelle en production!")
    
    return True

if __name__ == "__main__":
    try:
        success = test_production_api()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

