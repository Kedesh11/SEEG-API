"""
Test global de toutes les fonctionnalités demandées
"""
import requests

BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "sevankedesh11@gmail.com"
ADMIN_PASSWORD = "Sevan@Seeg"
# Utiliser le compte candidat existant dont on connaît les credentials
CANDIDATE_EMAIL = "candidate@example.com"
# Si ce mot de passe ne fonctionne pas, le test créera un nouveau candidat
CANDIDATE_PASSWORD = "TestPassword123!"  # Mot de passe par défaut pour tests (min 12 chars)

def print_section(title):
    print("\n" + "=" * 100)
    print(f"  {title}")
    print("=" * 100)

def test_result(name, success):
    icon = "✅" if success else "❌"
    print(f"{icon} {name}")
    return success

results = {}

print_section("🧪 TEST GLOBAL - TOUTES LES FONCTIONNALITÉS")

# Variables globales pour éviter les warnings
admin_headers = None
candidate_headers = None

# Fonction helper pour créer un candidat si nécessaire
def ensure_candidate_exists():
    """Crée le compte candidat s'il n'existe pas"""
    login_test = requests.post(f"{BASE_URL}/auth/login", data={"username": CANDIDATE_EMAIL, "password": CANDIDATE_PASSWORD})
    if login_test.status_code == 200:
        return True
    
    # Créer le compte
    signup = requests.post(
        f"{BASE_URL}/auth/signup",
        json={
            "email": CANDIDATE_EMAIL,
            "password": CANDIDATE_PASSWORD,
            "first_name": "Jessy",
            "last_name": "MOUVIOSSI",
            "phone": "+241 06 12 34 56",
            "date_of_birth": "2000-01-01",
            "sexe": "M",
            "role": "candidate",
            "candidate_status": "externe"
        }
    )
    return signup.status_code in [200, 201]

# ====================================================================
# TEST 1: Informations complètes du candidat dans les candidatures
# ====================================================================
print_section("TEST 1: INFORMATIONS CANDIDAT DANS CANDIDATURES")

admin_login = requests.post(f"{BASE_URL}/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
if admin_login.status_code == 200:
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Récupérer une candidature
    apps = requests.get(f"{BASE_URL}/applications/", headers=admin_headers, params={"limit": 1}).json()
    if apps.get("data"):
        app_id = apps["data"][0]["id"]
        details = requests.get(f"{BASE_URL}/applications/{app_id}", headers=admin_headers).json()
        data = details.get("data", {})
        
        has_candidate = "candidate" in data
        has_profile = has_candidate and data.get("candidate", {}).get("candidate_profile") is not None
        has_job_offer = "job_offer" in data
        
        results["candidate_info"] = test_result(
            f"Infos candidat présentes: {has_candidate}, Profil: {has_profile}, Offre: {has_job_offer}",
            has_candidate and has_job_offer
        )
        
        if has_candidate:
            candidate = data["candidate"]
            print(f"   👤 Candidat: {candidate.get('first_name')} {candidate.get('last_name')}")
            print(f"   📧 Email: {candidate.get('email')}")
            if has_profile:
                profile = candidate.get("candidate_profile", {})
                print(f"   💼 Poste: {profile.get('current_position', 'N/A')}")
                print(f"   📅 Expérience: {profile.get('years_experience', 'N/A')} ans")
    else:
        results["candidate_info"] = test_result("Aucune candidature pour tester", False)
else:
    results["candidate_info"] = test_result("Connexion admin échouée", False)

# ====================================================================
# TEST 2: Mise à jour profil candidat
# ====================================================================
print_section("TEST 2: MISE À JOUR PROFIL CANDIDAT")

# S'assurer que le candidat existe
ensure_candidate_exists()

candidate_login = requests.post(f"{BASE_URL}/auth/login", data={"username": CANDIDATE_EMAIL, "password": CANDIDATE_PASSWORD})
if candidate_login.status_code == 200:
    candidate_token = candidate_login.json()["access_token"]
    candidate_headers = {"Authorization": f"Bearer {candidate_token}"}
    
    # Mettre à jour le profil
    update_data = {
        "years_experience": 8,
        "current_position": "Tech Lead",
        "availability": "Immédiate"
    }
    
    update_response = requests.put(
        f"{BASE_URL}/users/me/profile",
        headers=candidate_headers,
        json=update_data
    )
    
    results["profile_update"] = test_result(
        f"PUT /users/me/profile - {update_response.status_code}",
        update_response.status_code == 200
    )
    
    if update_response.status_code == 200:
        updated = update_response.json().get("data", {})
        print(f"   Position: {updated.get('current_position')}")
        print(f"   Expérience: {updated.get('years_experience')} ans")
else:
    results["profile_update"] = test_result("Connexion candidat échouée", False)

# ====================================================================
# TEST 3: Access-requests accessibles par admin
# ====================================================================
print_section("TEST 3: ACCESS-REQUESTS - ADMIN")

if admin_login.status_code == 200 and admin_headers:
    routes_to_test = [
        ("GET", "/access-requests/"),
        ("GET", "/access-requests/unviewed-count"),
        ("POST", "/access-requests/mark-all-viewed"),
    ]
    
    access_results = []
    for method, route in routes_to_test:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{route}", headers=admin_headers)
        else:
            response = requests.post(f"{BASE_URL}{route}", headers=admin_headers, json={})
        
        success = response.status_code in [200, 201]
        test_result(f"{method} {route} - {response.status_code}", success)
        access_results.append(success)
    
    results["access_requests_admin"] = all(access_results)
else:
    results["access_requests_admin"] = False

# ====================================================================
# TEST 4: Access-requests INTERDITS aux candidats
# ====================================================================
print_section("TEST 4: ACCESS-REQUESTS - CANDIDAT (doit échouer)")

if candidate_login.status_code == 200 and candidate_headers:
    response = requests.get(f"{BASE_URL}/access-requests/", headers=candidate_headers)
    
    results["access_requests_security"] = test_result(
        f"GET /access-requests/ (candidat) - {response.status_code} (attendu 403)",
        response.status_code == 403
    )
    
    if response.status_code != 403:
        print(f"   ⚠️⚠️⚠️ PROBLÈME DE SÉCURITÉ: Candidat peut accéder aux access-requests!")
else:
    results["access_requests_security"] = False

# ====================================================================
# RÉSUMÉ FINAL
# ====================================================================
print_section("📊 RÉSUMÉ FINAL")

total = len(results)
passed = sum(1 for r in results.values() if r)

print(f"\n📈 Score: {passed}/{total} tests réussis\n")

for test_name, success in results.items():
    icon = "✅" if success else "❌"
    print(f"{icon} {test_name}")

if passed == total:
    print("\n🎉 TOUS LES TESTS RÉUSSIS !")
    print("   ✅ Informations candidat complètes retournées")
    print("   ✅ Mise à jour profil fonctionnelle")
    print("   ✅ Access-requests accessibles par admin/recruteurs")
    print("   ✅ Sécurité : candidats bloqués des access-requests")
else:
    print(f"\n⚠️ {total - passed} test(s) échoué(s)")

print("\n" + "=" * 100 + "\n")

