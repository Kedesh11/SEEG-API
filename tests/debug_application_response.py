"""
Debug: Afficher la réponse JSON complète pour voir si candidate et job_offer sont présents
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "sevankedesh11@gmail.com"
ADMIN_PASSWORD = "Sevan@Seeg"

# Connexion
login = requests.post(
    f"{BASE_URL}/auth/login",
    data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    timeout=10
)

token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Récupérer une candidature
apps = requests.get(f"{BASE_URL}/applications/", headers=headers, params={"limit": 1}).json()
app_id = apps.get("data", [])[0].get("id")

# Récupérer les détails
details = requests.get(f"{BASE_URL}/applications/{app_id}", headers=headers).json()

# Afficher la réponse complète
print("\n" + "=" * 100)
print("RÉPONSE COMPLÈTE JSON (formatée)")
print("=" * 100)
print(json.dumps(details, indent=2, ensure_ascii=False, default=str))
print("=" * 100)

# Vérifier les clés principales
data = details.get("data", {})
print("\n📊 ANALYSE:")
print(f"   Clés dans 'data': {list(data.keys())}")
print(f"   'candidate' présent: {'candidate' in data}")
print(f"   'job_offer' présent: {'job_offer' in data}")

if 'candidate' in data:
    print(f"\n✅ CANDIDAT TROUVÉ:")
    print(f"   {json.dumps(data['candidate'], indent=2, ensure_ascii=False, default=str)}")

if 'job_offer' in data:
    print(f"\n✅ OFFRE TROUVÉE:")
    print(f"   {json.dumps(data['job_offer'], indent=2, ensure_ascii=False, default=str)}")

print("\n" + "=" * 100 + "\n")

