"""
Test de mise à jour des champs utilisateur manquants
"""
import requests

BASE_URL = "https://seeg-backend-api.azurewebsites.net/api/v1"

# 1. Se connecter
print("🔐 Connexion...")
login_response = requests.post(
    f"{BASE_URL}/auth/login",
    data={
        "username": "kevin@cnx4-0.com",
        "password": "Motdepasse123!"
    }
)

if login_response.status_code != 200:
    print(f"❌ Erreur connexion: {login_response.status_code}")
    print(login_response.text)
    exit(1)

token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("✅ Connecté!")

# 2. Mettre à jour le profil avec les champs manquants
print("\n📝 Mise à jour du profil...")
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

data = update_response.json()["data"]
print("✅ Profil mis à jour!")

# 3. Vérifier que tous les champs sont présents
print("\n🔍 Vérification des champs...")
required_fields = [
    "first_name", "last_name", "phone", "sexe",
    "adresse", "annees_experience", "poste_actuel"
]

missing_fields = []
for field in required_fields:
    if field in data:
        print(f"  ✅ {field}: {data[field]}")
    else:
        print(f"  ❌ {field}: MANQUANT")
        missing_fields.append(field)

if missing_fields:
    print(f"\n❌ Champs manquants: {', '.join(missing_fields)}")
else:
    print("\n✅ Tous les champs sont présents!")

print("\n📊 Réponse complète:")
import json
print(json.dumps(data, indent=2, ensure_ascii=False))

