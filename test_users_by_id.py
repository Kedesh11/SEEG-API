"""
Test de l'endpoint GET /users/{user_id} avec différents rôles
"""
import requests

BASE_URL = "http://localhost:8000/api/v1"

print("=" * 80)
print("TEST GET /users/{user_id} - PERMISSIONS ET DONNÉES")
print("=" * 80)

# 1. Connexion candidat pour récupérer son ID
print("\n1️⃣  Connexion candidat...")
candidate_login = requests.post(
    f"{BASE_URL}/auth/login",
    data={"username": "candidate@example.com", "password": "TestPassword123!"}
)

if candidate_login.status_code != 200:
    print(f"❌ Erreur connexion candidat: {candidate_login.status_code}")
    exit(1)

candidate_data = candidate_login.json()["user"]
candidate_id = candidate_data["id"]
candidate_token = candidate_login.json()["access_token"]
candidate_headers = {"Authorization": f"Bearer {candidate_token}"}

print(f"✅ Candidat connecté: {candidate_data['email']}")
print(f"   ID: {candidate_id}")

# 2. Connexion admin
print("\n2️⃣  Connexion admin...")
admin_login = requests.post(
    f"{BASE_URL}/auth/login",
    data={"username": "sevankedesh11@gmail.com", "password": "Sevan@Seeg"}
)

if admin_login.status_code != 200:
    print(f"❌ Erreur connexion admin: {admin_login.status_code}")
    exit(1)

admin_token = admin_login.json()["access_token"]
admin_headers = {"Authorization": f"Bearer {admin_token}"}
print("✅ Admin connecté!")


# 3. Test: Admin accède au profil du candidat
print("\n3️⃣  TEST: Admin accède au profil du candidat...")
response = requests.get(f"{BASE_URL}/users/{candidate_id}", headers=admin_headers)

if response.status_code == 200:
    print("✅ Admin peut accéder au profil du candidat!")
    data = response.json()["data"]
    print(f"   📊 Informations récupérées:")
    
    required_fields = ["email", "first_name", "last_name", "role", 
                      "adresse", "annees_experience", "poste_actuel", "candidate_profile"]
    
    for field in required_fields:
        value = data.get(field)
        status = "✅" if value is not None or field == "candidate_profile" else "⚠️"
        print(f"      {status} {field}: {value if value is not None else 'null'}")
else:
    print(f"❌ Erreur: {response.status_code}")
    print(response.text)

# 4. Test: Candidat accède à son propre profil
print("\n4️⃣  TEST: Candidat accède à son propre profil...")
response = requests.get(f"{BASE_URL}/users/{candidate_id}", headers=candidate_headers)

if response.status_code == 200:
    print("✅ Candidat peut accéder à son propre profil!")
    data = response.json()["data"]
    print(f"   - Adresse: {data.get('adresse')}")
    print(f"   - Expérience: {data.get('annees_experience')}")
    print(f"   - Poste: {data.get('poste_actuel')}")
else:
    print(f"❌ Erreur: {response.status_code}")

print("\n" + "=" * 80)
print("✅ TEST TERMINÉ")
print("=" * 80)

