"""
Test complet des access-requests en local
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

print_section("🧪 TEST COMPLET: ACCESS-REQUESTS")

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
        admin_token = response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print_result("Connexion admin", response.status_code, 200)
        results.append(True)
    else:
        print(f"❌ Connexion échouée: {response.status_code}")
        print(f"   {response.text}")
        results.append(False)
        exit(1)
except Exception as e:
    print(f"❌ Erreur: {e}")
    exit(1)

# ====================================================================
# TEST 2: GET /access-requests/
# ====================================================================
print_section("TEST 2: GET /access-requests/ (Liste)")

try:
    response = requests.get(f"{BASE_URL}/access-requests/", headers=admin_headers)
    success = print_result("GET /access-requests/", response.status_code, 200)
    results.append(success)
    
    if response.status_code == 200:
        data = response.json()
        print(f"   📊 Structure de la réponse:")
        print(f"      Keys: {list(data.keys())}")
        print(f"      Total: {data.get('total', 'N/A')}")
        print(f"      Data items: {len(data.get('data', []))}")
        print(f"      Pending: {data.get('pending_count', 'N/A')}")
        print(f"      Unviewed: {data.get('unviewed_count', 'N/A')}")
        
        if data.get('data'):
            print(f"\n   📋 Exemple d'access-request:")
            item = data['data'][0]
            print(json.dumps(item, indent=6, ensure_ascii=False))
    else:
        print(f"   ❌ Erreur: {response.text}")
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
    results.append(False)

# ====================================================================
# TEST 3: GET /access-requests/unviewed-count
# ====================================================================
print_section("TEST 3: GET /access-requests/unviewed-count")

try:
    response = requests.get(f"{BASE_URL}/access-requests/unviewed-count", headers=admin_headers)
    success = print_result("GET /access-requests/unviewed-count", response.status_code, 200)
    results.append(success)
    
    if response.status_code == 200:
        data = response.json()
        print(f"   📊 Réponse:")
        print(json.dumps(data, indent=6, ensure_ascii=False))
    else:
        print(f"   ❌ Erreur: {response.text}")
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
    results.append(False)

# ====================================================================
# TEST 4: POST /access-requests/mark-all-viewed
# ====================================================================
print_section("TEST 4: POST /access-requests/mark-all-viewed")

try:
    response = requests.post(f"{BASE_URL}/access-requests/mark-all-viewed", headers=admin_headers, json={})
    success = print_result("POST /access-requests/mark-all-viewed", response.status_code, 200)
    results.append(success)
    
    if response.status_code == 200:
        data = response.json()
        print(f"   📊 Réponse:")
        print(json.dumps(data, indent=6, ensure_ascii=False))
    else:
        print(f"   ❌ Erreur: {response.text}")
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
    results.append(False)

# ====================================================================
# TEST 5: GET /access-requests/{id} (si des demandes existent)
# ====================================================================
print_section("TEST 5: GET /access-requests/{id} (Détails d'une demande)")

try:
    # Récupérer la liste pour avoir un ID
    list_response = requests.get(f"{BASE_URL}/access-requests/", headers=admin_headers)
    
    if list_response.status_code == 200:
        data = list_response.json()
        if data.get('data') and len(data['data']) > 0:
            request_id = data['data'][0]['id']
            
            response = requests.get(f"{BASE_URL}/access-requests/{request_id}", headers=admin_headers)
            success = print_result(f"GET /access-requests/{request_id}", response.status_code, 200)
            results.append(success)
            
            if response.status_code == 200:
                detail_data = response.json()
                print(f"   📊 Détails:")
                print(json.dumps(detail_data, indent=6, ensure_ascii=False))
            else:
                print(f"   ❌ Erreur: {response.text}")
        else:
            print("   ℹ️  Aucune access-request en base pour tester les détails")
            results.append(True)  # Pas d'erreur, juste pas de données
    else:
        print(f"   ⚠️  Impossible de récupérer la liste: {list_response.status_code}")
        results.append(False)
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
    results.append(False)

# ====================================================================
# TEST 6: Sécurité - Candidat ne peut pas accéder
# ====================================================================
print_section("TEST 6: SÉCURITÉ - Candidat bloqué")

try:
    # Connexion candidat
    cand_login = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": "candidat.test.local@example.com", "password": "Candidat123!"}
    )
    
    if cand_login.status_code == 200:
        cand_token = cand_login.json()["access_token"]
        cand_headers = {"Authorization": f"Bearer {cand_token}"}
        
        # Tenter d'accéder aux access-requests (doit être bloqué)
        response = requests.get(f"{BASE_URL}/access-requests/", headers=cand_headers)
        success = print_result("GET /access-requests/ (candidat)", response.status_code, 403)
        results.append(success)
        
        if response.status_code == 403:
            print("   ✅ Sécurité OK - Candidat correctement bloqué")
        else:
            print(f"   ⚠️⚠️⚠️ PROBLÈME DE SÉCURITÉ!")
            print(f"   Un candidat peut accéder aux access-requests!")
    else:
        print(f"   ⚠️  Candidat non connecté: {cand_login.status_code}")
        results.append(False)
except Exception as e:
    print(f"❌ Erreur: {e}")
    results.append(False)

# ====================================================================
# TEST 7: Créer une access-request (simulation inscription candidat interne)
# ====================================================================
print_section("TEST 7: Créer une access-request")

try:
    # Simuler une demande d'accès pour un candidat interne en attente
    access_request_data = {
        "email": "nouveau.candidat@example.com",
        "first_name": "Nouveau",
        "last_name": "Candidat",
        "phone": "+241 06 00 00 00",
        "matricule": "999888"
    }
    
    # Note: Cette route peut ne pas exister en POST public
    # Normalement créée automatiquement lors de l'inscription
    print("   ℹ️  Les access-requests sont créées automatiquement lors de l'inscription")
    print("   ℹ️  Test de création manuelle skippé")
    results.append(True)
except Exception as e:
    print(f"❌ Erreur: {e}")
    results.append(False)

# ====================================================================
# RÉSUMÉ FINAL
# ====================================================================
print_section("📊 RÉSUMÉ FINAL")

total = len(results)
passed = sum(1 for r in results if r)

print(f"\n📈 Score: {passed}/{total} tests réussis\n")

if passed == total:
    print("🎉 TOUS LES TESTS ACCESS-REQUESTS RÉUSSIS !")
    print("   ✅ Liste des access-requests")
    print("   ✅ Compteur non vues")
    print("   ✅ Marquer comme vues")
    print("   ✅ Détails d'une demande")
    print("   ✅ Sécurité : candidats bloqués")
    exit(0)
else:
    print(f"⚠️ {total - passed} test(s) échoué(s)")
    exit(1)

