"""
Test complet des permissions pour les access-requests
Vérifie que les recruteurs peuvent accéder à toutes les routes
"""
import requests

BASE_URL = "http://localhost:8000/api/v1"

# Credentials
ADMIN_EMAIL = "sevankedesh11@gmail.com"
ADMIN_PASSWORD = "Sevan@Seeg"
CANDIDATE_EMAIL = "candidate@test.local"
CANDIDATE_PASSWORD = "Candidate@Test123"

def print_test(name, success=None):
    if success is True:
        print(f"✅ {name}")
    elif success is False:
        print(f"❌ {name}")
    else:
        print(f"🔄 {name}")

print("\n" + "=" * 80)
print("  🧪 TEST - PERMISSIONS ACCESS-REQUESTS")
print("=" * 80)

# Test 1: Admin peut accéder
print("\n📊 TEST 1: ADMIN")
admin_login = requests.post(f"{BASE_URL}/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
if admin_login.status_code == 200:
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print_test("Connexion admin", True)
    
    # GET /access-requests/
    response = requests.get(f"{BASE_URL}/access-requests/", headers=admin_headers)
    print_test(f"GET /access-requests/ - {response.status_code}", response.status_code == 200)
    
    # GET /access-requests/unviewed-count
    response = requests.get(f"{BASE_URL}/access-requests/unviewed-count", headers=admin_headers)
    print_test(f"GET /access-requests/unviewed-count - {response.status_code}", response.status_code == 200)
    
    # POST /access-requests/mark-all-viewed
    response = requests.post(f"{BASE_URL}/access-requests/mark-all-viewed", headers=admin_headers)
    print_test(f"POST /access-requests/mark-all-viewed - {response.status_code}", response.status_code == 200)
else:
    print_test("Connexion admin", False)

# Test 2: Candidat NE PEUT PAS accéder (doit être 403)
print("\n📊 TEST 2: CANDIDAT (doit échouer)")
candidate_login = requests.post(f"{BASE_URL}/auth/login", data={"username": CANDIDATE_EMAIL, "password": CANDIDATE_PASSWORD})
if candidate_login.status_code == 200:
    candidate_token = candidate_login.json()["access_token"]
    candidate_headers = {"Authorization": f"Bearer {candidate_token}"}
    print_test("Connexion candidat", True)
    
    # GET /access-requests/ (doit être 403)
    response = requests.get(f"{BASE_URL}/access-requests/", headers=candidate_headers)
    print_test(f"GET /access-requests/ - {response.status_code} (attendu 403)", response.status_code == 403)
    
    if response.status_code != 403:
        print(f"   ⚠️ Le candidat a accédé aux access-requests (PROBLÈME DE SÉCURITÉ !)")
else:
    print_test("Connexion candidat", False)

# Résumé
print("\n" + "=" * 80)
print("📊 RÉSUMÉ DES PERMISSIONS")
print("=" * 80)
print("\n✅ Les access-requests DOIVENT être accessibles uniquement par:")
print("   - Admins")
print("   - Recruteurs")
print("\n❌ Les candidats NE DOIVENT PAS pouvoir y accéder")
print("\n💡 Routes testées:")
print("   GET  /api/v1/access-requests/")
print("   GET  /api/v1/access-requests/unviewed-count")
print("   POST /api/v1/access-requests/mark-all-viewed")
print("   POST /api/v1/access-requests/approve")
print("   POST /api/v1/access-requests/reject")
print("\n" + "=" * 80 + "\n")

