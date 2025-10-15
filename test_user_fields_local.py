"""
Test des champs utilisateur en local
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

print("=" * 70)
print("TEST DES CHAMPS UTILISATEUR - LOCAL")
print("=" * 70)

# 1. Connexion
print("\n1️⃣  Connexion candidat...")
login_response = requests.post(
    f"{BASE_URL}/auth/login",
    data={
        "username": "candidate@example.com",
        "password": "TestPassword123!"
    }
)

if login_response.status_code != 200:
    print(f"❌ Erreur connexion: {login_response.status_code}")
    print(login_response.text)
    exit(1)

token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("✅ Connecté!")

# 2. Récupérer le profil actuel
print("\n2️⃣  Récupération profil actuel...")
me_response = requests.get(f"{BASE_URL}/users/me", headers=headers)

if me_response.status_code == 200:
    current_data = me_response.json()["data"]
    print("✅ Profil récupéré")
    print(f"   - Email: {current_data.get('email')}")
    print(f"   - Adresse actuelle: {current_data.get('adresse', 'NON PRÉSENT')}")
    print(f"   - Expérience actuelle: {current_data.get('annees_experience', 'NON PRÉSENT')}")
    print(f"   - Poste actuel: {current_data.get('poste_actuel', 'NON PRÉSENT')}")
else:
    print(f"❌ Erreur: {me_response.status_code}")

# 3. Mettre à jour avec les champs du front
print("\n3️⃣  Mise à jour avec les champs du front...")
update_data = {
    "first_name": "Test",
    "last_name": "Plateforme",
    "phone": "+241 05857896",
    "sexe": "M",
    "adresse": "OWENDO",
    "annees_experience": 5,
    "date_of_birth": "2000-10-13T00:00:00Z",
    "poste_actuel": "NA"
}

update_response = requests.put(
    f"{BASE_URL}/users/me",
    headers=headers,
    json=update_data
)

if update_response.status_code != 200:
    print(f"❌ Erreur: {update_response.status_code}")
    print(update_response.text)
    exit(1)

response_data = update_response.json()["data"]
print("✅ Profil mis à jour!")

# 4. Vérifier que tous les champs sont présents
print("\n4️⃣  Vérification des champs dans la réponse...")
required_fields = {
    "first_name": "Test",
    "last_name": "Plateforme",
    "phone": "+241 05857896",
    "sexe": "M",
    "adresse": "OWENDO",
    "annees_experience": 5,
    "poste_actuel": "NA"
}

missing_fields = []
incorrect_values = []

for field, expected_value in required_fields.items():
    if field in response_data:
        actual_value = response_data[field]
        if actual_value == expected_value or (field == "date_of_birth"):
            print(f"  ✅ {field}: {actual_value}")
        else:
            print(f"  ⚠️  {field}: {actual_value} (attendu: {expected_value})")
            incorrect_values.append(field)
    else:
        print(f"  ❌ {field}: MANQUANT")
        missing_fields.append(field)

# 5. Afficher la réponse complète
print("\n5️⃣  Réponse API complète:")
print(json.dumps(response_data, indent=2, ensure_ascii=False, default=str))

# 6. Résumé
print("\n" + "=" * 70)
if not missing_fields and not incorrect_values:
    print("✅ TOUS LES CHAMPS SONT PRÉSENTS ET CORRECTS!")
elif missing_fields:
    print(f"❌ CHAMPS MANQUANTS: {', '.join(missing_fields)}")
else:
    print(f"⚠️  CHAMPS INCORRECTS: {', '.join(incorrect_values)}")
print("=" * 70)

