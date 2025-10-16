"""
Test final de tous les endpoints en local
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

print("=" * 80)
print("TEST FINAL - VÉRIFICATION COMPLÈTE EN LOCAL")
print("=" * 80)

# 1. Connexion admin
print("\n1️⃣  Connexion admin...")
admin_login = requests.post(
    f"{BASE_URL}/auth/login",
    data={"username": "sevankedesh11@gmail.com", "password": "Sevan@Seeg"}
)

admin_token = admin_login.json()["access_token"]
admin_headers = {"Authorization": f"Bearer {admin_token}"}
admin_data = admin_login.json()["user"]
print(f"✅ Admin connecté: {admin_data['email']}")

# Vérifier que l'admin a tous les champs
print(f"\n   📊 Champs admin dans la réponse de login:")
print(f"      - adresse: {admin_data.get('adresse', '❌ MANQUANT')}")
print(f"      - annees_experience: {admin_data.get('annees_experience', '❌ MANQUANT')}")
print(f"      - poste_actuel: {admin_data.get('poste_actuel', '❌ MANQUANT')}")
print(f"      - statut: {admin_data.get('statut', '❌ MANQUANT')}")

# 2. Connexion candidat
print("\n2️⃣  Connexion candidat...")
candidate_login = requests.post(
    f"{BASE_URL}/auth/login",
    data={"username": "candidate@example.com", "password": "TestPassword123!"}
)

candidate_token = candidate_login.json()["access_token"]
candidate_headers = {"Authorization": f"Bearer {candidate_token}"}
candidate_data = candidate_login.json()["user"]
candidate_id = candidate_data["id"]
print(f"✅ Candidat connecté: {candidate_data['email']}")
print(f"   ID: {candidate_id}")

# 3. Test GET /users/me
print("\n3️⃣  TEST: GET /users/me (candidat)...")
me_response = requests.get(f"{BASE_URL}/users/me", headers=candidate_headers)

if me_response.status_code == 200:
    me_data = me_response.json()["data"]
    print("✅ GET /users/me fonctionne!")
    print(f"   - adresse: {me_data.get('adresse')}")
    print(f"   - annees_experience: {me_data.get('annees_experience')}")
    print(f"   - poste_actuel: {me_data.get('poste_actuel')}")
    print(f"   - candidate_profile: {'✅ Présent' if me_data.get('candidate_profile') else '❌ null'}")
else:
    print(f"❌ Erreur: {me_response.status_code}")

# 4. Test PUT /users/me avec persistance
print("\n4️⃣  TEST: PUT /users/me (mise à jour + persistance)...")
update_data = {
    "adresse": "Nouvelle adresse test",
    "annees_experience": 10,
    "poste_actuel": "Nouveau poste test"
}

put_response = requests.put(
    f"{BASE_URL}/users/me",
    headers=candidate_headers,
    json=update_data
)

if put_response.status_code == 200:
    put_data = put_response.json()["data"]
    print("✅ PUT /users/me fonctionne!")
    print(f"   - adresse: {put_data.get('adresse')}")
    print(f"   - annees_experience: {put_data.get('annees_experience')}")
    print(f"   - poste_actuel: {put_data.get('poste_actuel')}")
    
    # Vérifier persistance
    print("\n   🔄 Vérification persistance (nouveau GET /users/me)...")
    me_response2 = requests.get(f"{BASE_URL}/users/me", headers=candidate_headers)
    me_data2 = me_response2.json()["data"]
    
    if (me_data2.get('adresse') == update_data['adresse'] and 
        me_data2.get('annees_experience') == update_data['annees_experience'] and
        me_data2.get('poste_actuel') == update_data['poste_actuel']):
        print("   ✅ PERSISTANCE OK - Données sauvegardées en base!")
    else:
        print("   ❌ PERSISTANCE KO - Données non sauvegardées!")
else:
    print(f"❌ Erreur: {put_response.status_code}")

# 5. Test GET /users/{user_id} (admin accède au candidat)
print("\n5️⃣  TEST: GET /users/{candidate_id} (admin)...")
user_response = requests.get(f"{BASE_URL}/users/{candidate_id}", headers=admin_headers)

if user_response.status_code == 200:
    user_data = user_response.json()["data"]
    print("✅ Admin peut accéder au profil candidat!")
    print(f"   - Email: {user_data.get('email')}")
    print(f"   - adresse: {user_data.get('adresse')}")
    print(f"   - annees_experience: {user_data.get('annees_experience')}")
    print(f"   - poste_actuel: {user_data.get('poste_actuel')}")
    print(f"   - candidate_profile: {'✅ Présent' if user_data.get('candidate_profile') else '❌ null'}")
else:
    print(f"❌ Erreur: {user_response.status_code}")

# 6. Test access-requests/unviewed-count (admin)
print("\n6️⃣  TEST: GET /access-requests/unviewed-count (admin)...")
unviewed_response = requests.get(
    f"{BASE_URL}/access-requests/unviewed-count",
    headers=admin_headers
)

if unviewed_response.status_code == 200:
    count = unviewed_response.json().get('count', 0)
    print(f"✅ Endpoint accessible! Demandes non vues: {count}")
else:
    print(f"❌ Erreur: {unviewed_response.status_code}")

print("\n" + "=" * 80)
print("✅ TESTS TERMINÉS")
print("=" * 80)

