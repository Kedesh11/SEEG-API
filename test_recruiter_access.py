"""
Test d'accès recruteur à GET /users/{user_id}
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

print("=" * 80)
print("TEST ACCÈS RECRUTEUR À GET /users/{user_id}")
print("=" * 80)

# 1. Connexion recruteur
print("\n1️⃣  Connexion recruteur...")
recruiter_login = requests.post(
    f"{BASE_URL}/auth/login",
    data={
        "username": "foutyaxel9@gmail.com",
        "password": "Fouty123@Seeg2025"
    }
)

if recruiter_login.status_code != 200:
    print(f"❌ Erreur connexion recruteur: {recruiter_login.status_code}")
    print(recruiter_login.text)
    exit(1)

recruiter_data = recruiter_login.json()["user"]
recruiter_token = recruiter_login.json()["access_token"]
recruiter_headers = {"Authorization": f"Bearer {recruiter_token}"}

print(f"✅ Recruteur connecté: {recruiter_data['email']}")
print(f"   Rôle: {recruiter_data['role']}")
print(f"   ID: {recruiter_data['id']}")

# 2. Connexion candidat pour récupérer son ID
print("\n2️⃣  Connexion candidat...")
candidate_login = requests.post(
    f"{BASE_URL}/auth/login",
    data={
        "username": "candidate@example.com",
        "password": "TestPassword123!"
    }
)

if candidate_login.status_code != 200:
    print(f"❌ Erreur connexion candidat: {candidate_login.status_code}")
    exit(1)

candidate_data = candidate_login.json()["user"]
candidate_id = candidate_data["id"]

print(f"✅ Candidat connecté: {candidate_data['email']}")
print(f"   ID: {candidate_id}")

# 3. Test: Recruteur accède au profil du candidat
print("\n3️⃣  TEST: Recruteur accède au profil du candidat...")
print(f"   URL: {BASE_URL}/users/{candidate_id}")

response = requests.get(f"{BASE_URL}/users/{candidate_id}", headers=recruiter_headers)

print(f"   Status Code: {response.status_code}")

if response.status_code == 200:
    print("✅ SUCCÈS! Recruteur peut accéder au profil du candidat!")
    data = response.json()["data"]
    
    print(f"\n   📊 Informations complètes du candidat:")
    print(f"      - ID: {data.get('id')}")
    print(f"      - Email: {data.get('email')}")
    print(f"      - Nom: {data.get('first_name')} {data.get('last_name')}")
    print(f"      - Rôle: {data.get('role')}")
    print(f"      - Phone: {data.get('phone', 'Non renseigné')}")
    print(f"      - Adresse: {data.get('adresse', 'Non renseignée')}")
    print(f"      - Expérience: {data.get('annees_experience', 'Non renseignée')} ans")
    print(f"      - Poste actuel: {data.get('poste_actuel', 'Non renseigné')}")
    print(f"      - Statut: {data.get('statut', 'Non renseigné')}")
    print(f"      - Profil candidat: {'✅ Présent' if data.get('candidate_profile') else '❌ Absent'}")
    
    print(f"\n   📄 Réponse complète:")
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    
elif response.status_code == 403:
    print(f"❌ ÉCHEC! Recruteur bloqué (403 Forbidden)")
    print(f"   Message: {response.json().get('detail', 'Pas de détails')}")
    print(f"\n   ⚠️  Le rôle du recruteur n'est peut-être pas reconnu correctement")
    print(f"   Rôle actuel: {recruiter_data['role']}")
else:
    print(f"❌ Erreur: {response.status_code}")
    print(response.text)

# 4. Test: Recruteur accède à un autre recruteur
print("\n4️⃣  TEST: Recruteur accède à un profil admin...")
admin_login = requests.post(
    f"{BASE_URL}/auth/login",
    data={"username": "sevankedesh11@gmail.com", "password": "Sevan@Seeg"}
)

if admin_login.status_code == 200:
    admin_data = admin_login.json()["user"]
    admin_id = admin_data["id"]
    
    response = requests.get(f"{BASE_URL}/users/{admin_id}", headers=recruiter_headers)
    
    if response.status_code == 200:
        print("✅ Recruteur peut accéder au profil admin!")
    elif response.status_code == 403:
        print("❌ Recruteur bloqué pour accéder au profil admin")
    else:
        print(f"⚠️  Status: {response.status_code}")

print("\n" + "=" * 80)
print("✅ TEST TERMINÉ")
print("=" * 80)

