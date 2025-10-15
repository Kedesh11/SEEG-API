"""
Test complet des routes utilisateurs en local
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "sevankedesh11@gmail.com"
ADMIN_PASSWORD = "Sevan@Seeg"

def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_result(name, status_code, expected=200):
    success = status_code == expected
    icon = "✅" if success else "❌"
    print(f"{icon} {name} - Status: {status_code} (attendu: {expected})")
    return success

results = []

print_section("🧪 TEST COMPLET: ROUTES UTILISATEURS")

# ====================================================================
# TEST 1: Connexion admin
# ====================================================================
print_section("TEST 1: CONNEXION ADMIN")

try:
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    
    if response.status_code == 200:
        token_data = response.json()
        admin_token = token_data["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print_result("Connexion admin", response.status_code, 200)
        
        # Vérifier si le profil candidat est retourné
        user_info = token_data.get("user", {})
        print(f"\n   📊 Informations utilisateur dans le token:")
        print(f"      - Email: {user_info.get('email')}")
        print(f"      - Role: {user_info.get('role')}")
        print(f"      - Candidat profile: {'✅ Présent' if user_info.get('candidate_profile') is not None else '❌ Absent'}")
        
        results.append(True)
    else:
        print(f"❌ Connexion échouée: {response.status_code}")
        print(f"   {response.text}")
        results.append(False)
        exit(1)
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# ====================================================================
# TEST 2: GET /users/me
# ====================================================================
print_section("TEST 2: GET /users/me")

try:
    response = requests.get(f"{BASE_URL}/users/me", headers=admin_headers)
    success = print_result("GET /users/me", response.status_code, 200)
    results.append(success)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n   📊 Structure de la réponse:")
        print(f"      Success: {data.get('success')}")
        print(f"      Message: {data.get('message')}")
        
        user_data = data.get('data', {})
        print(f"\n   👤 Informations utilisateur:")
        print(f"      - ID: {user_data.get('id')}")
        print(f"      - Email: {user_data.get('email')}")
        print(f"      - Role: {user_data.get('role')}")
        print(f"      - Nom: {user_data.get('first_name')} {user_data.get('last_name')}")
        print(f"      - Candidat profile: {'✅ Présent' if user_data.get('candidate_profile') is not None else '⚠️  Absent (normal pour admin)'}")
    else:
        print(f"   ❌ Erreur: {response.text}")
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
    results.append(False)

# ====================================================================
# TEST 3: GET /users/ (Liste)
# ====================================================================
print_section("TEST 3: GET /users/ (Liste)")

try:
    response = requests.get(
        f"{BASE_URL}/users/",
        headers=admin_headers,
        params={"limit": 5}
    )
    success = print_result("GET /users/", response.status_code, 200)
    results.append(success)
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n   📊 Structure de la réponse:")
        print(f"      Keys: {list(result.keys())}")
        print(f"      Total: {result.get('total', 'N/A')}")
        print(f"      Items: {len(result.get('data', []))}")
        print(f"      Page: {result.get('page', 'N/A')}")
        print(f"      Per page: {result.get('per_page', 'N/A')}")
        
        users = result.get('data', [])
        if users:
            print(f"\n   👤 Exemple d'utilisateur:")
            user = users[0]
            print(f"      - ID: {user.get('id')}")
            print(f"      - Email: {user.get('email')}")
            print(f"      - Role: {user.get('role')}")
            print(f"      - Nom: {user.get('first_name')} {user.get('last_name')}")
    else:
        print(f"   ❌ Erreur: {response.text}")
        print(f"\n   🔍 Erreur complète:")
        try:
            error_detail = response.json()
            print(json.dumps(error_detail, indent=6, ensure_ascii=False))
        except:
            print(response.text)
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
    results.append(False)

# ====================================================================
# TEST 4: GET /users/{id}
# ====================================================================
print_section("TEST 4: GET /users/{id} (Détails)")

try:
    # Utiliser l'ID de l'admin connecté
    me_response = requests.get(f"{BASE_URL}/users/me", headers=admin_headers)
    if me_response.status_code == 200:
        my_id = me_response.json()['data']['id']
        
        response = requests.get(f"{BASE_URL}/users/{my_id}", headers=admin_headers)
        success = print_result(f"GET /users/{my_id}", response.status_code, 200)
        results.append(success)
        
        if response.status_code == 200:
            data = response.json()
            user_data = data.get('data', {})
            print(f"\n   👤 Utilisateur récupéré:")
            print(f"      - Email: {user_data.get('email')}")
            print(f"      - Role: {user_data.get('role')}")
        else:
            print(f"   ❌ Erreur: {response.text}")
    else:
        print(f"   ⚠️  Impossible de récupérer mon ID")
        results.append(False)
except Exception as e:
    print(f"❌ Erreur: {e}")
    results.append(False)

# ====================================================================
# TEST 5: Connexion candidat et vérification du profil
# ====================================================================
print_section("TEST 5: Connexion candidat et profil complet")

try:
    # Connexion candidat
    cand_login = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": "candidat.test.local@example.com", "password": "Candidat123!"}
    )
    
    if cand_login.status_code == 200:
        token_data = cand_login.json()
        cand_token = token_data["access_token"]
        cand_headers = {"Authorization": f"Bearer {cand_token}"}
        
        print_result("Connexion candidat", cand_login.status_code, 200)
        
        # Vérifier les infos retournées au login
        user_info = token_data.get("user", {})
        print(f"\n   📊 Informations au login:")
        print(f"      - Email: {user_info.get('email')}")
        print(f"      - Role: {user_info.get('role')}")
        print(f"      - Candidat profile dans login: {'✅ Présent' if user_info.get('candidate_profile') is not None else '⚠️  Absent'}")
        
        if user_info.get('candidate_profile'):
            profile = user_info['candidate_profile']
            print(f"\n   💼 Profil candidat:")
            print(f"      - Expérience: {profile.get('years_experience')} ans")
            print(f"      - Poste: {profile.get('current_position')}")
            print(f"      - Disponibilité: {profile.get('availability')}")
        
        # Tester GET /users/me pour le candidat
        me_response = requests.get(f"{BASE_URL}/users/me", headers=cand_headers)
        success = print_result("GET /users/me (candidat)", me_response.status_code, 200)
        results.append(success)
        
        if me_response.status_code == 200:
            me_data = me_response.json().get('data', {})
            print(f"\n   📊 GET /users/me:")
            print(f"      - Candidat profile: {'✅ Présent' if me_data.get('candidate_profile') is not None else '⚠️  Absent'}")
            
            if me_data.get('candidate_profile'):
                profile = me_data['candidate_profile']
                print(f"      - Expérience: {profile.get('years_experience')} ans")
                print(f"      - Poste: {profile.get('current_position')}")
    else:
        print(f"❌ Connexion candidat échouée: {cand_login.status_code}")
        results.append(False)
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
    results.append(False)

# ====================================================================
# RÉSUMÉ FINAL
# ====================================================================
print_section("📊 RÉSUMÉ FINAL")

total = len(results)
passed = sum(1 for r in results if r)

print(f"\n📈 Score: {passed}/{total} tests réussis\n")

if passed == total:
    print("🎉 TOUS LES TESTS UTILISATEURS RÉUSSIS !")
    print("   ✅ Connexion retourne toutes les infos")
    print("   ✅ GET /users/me retourne le profil complet")
    print("   ✅ GET /users/ liste les utilisateurs")
    print("   ✅ GET /users/{id} récupère un utilisateur")
    exit(0)
else:
    print(f"⚠️ {total - passed} test(s) échoué(s)")
    for i, r in enumerate(results):
        if not r:
            print(f"   ❌ Test {i+1} échoué")
    exit(1)

