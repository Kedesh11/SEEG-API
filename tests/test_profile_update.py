"""
Test de mise à jour du profil candidat
"""
import requests

BASE_URL = "http://localhost:8000/api/v1"
CANDIDATE_EMAIL = "candidate@test.local"
CANDIDATE_PASSWORD = "Candidate@Test123"

print("\n" + "=" * 80)
print("  🧪 TEST - MISE À JOUR PROFIL CANDIDAT")
print("=" * 80)

# 1. Connexion candidat
print("\n🔐 Connexion candidat...")
login = requests.post(
    f"{BASE_URL}/auth/login",
    data={"username": CANDIDATE_EMAIL, "password": CANDIDATE_PASSWORD},
    timeout=10
)

if login.status_code != 200:
    print(f"❌ Échec connexion: {login.status_code}")
    print(f"   Détails: {login.text[:200]}")
    exit(1)

token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("✅ Connecté")

# 2. Récupérer le profil actuel
print("\n📋 Récupération profil actuel...")
profile_response = requests.get(
    f"{BASE_URL}/users/me/profile",
    headers=headers,
    timeout=10
)

if profile_response.status_code == 200:
    current_profile = profile_response.json().get("data", {})
    print("✅ Profil actuel récupéré:")
    print(f"   Position: {current_profile.get('current_position', 'N/A')}")
    print(f"   Département: {current_profile.get('current_department', 'N/A')}")
    print(f"   Expérience: {current_profile.get('years_experience', 'N/A')} ans")
    print(f"   Disponibilité: {current_profile.get('availability', 'N/A')}")
else:
    print(f"⚠️ Profil non trouvé (code {profile_response.status_code})")
    current_profile = {}

# 3. Mettre à jour le profil
print("\n🔄 Mise à jour du profil...")
update_data = {
    "years_experience": 7,
    "current_position": "Senior Software Engineer",
    "current_department": "R&D",
    "availability": "1 mois de préavis",
    "expected_salary_min": 3000000,
    "expected_salary_max": 4500000,
    "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Azure"],
    "linkedin_url": "https://www.linkedin.com/in/test-profile"
}

update_response = requests.put(
    f"{BASE_URL}/users/me/profile",
    headers=headers,
    json=update_data,
    timeout=10
)

if update_response.status_code == 200:
    updated_profile = update_response.json().get("data", {})
    print("✅ ✅ PROFIL MIS À JOUR AVEC SUCCÈS !")
    print(f"\n📊 Nouvelles valeurs:")
    print(f"   Position: {updated_profile.get('current_position')}")
    print(f"   Département: {updated_profile.get('current_department')}")
    print(f"   Expérience: {updated_profile.get('years_experience')} ans")
    print(f"   Disponibilité: {updated_profile.get('availability')}")
    print(f"   Salaire min: {updated_profile.get('expected_salary_min')} FCFA")
    print(f"   Salaire max: {updated_profile.get('expected_salary_max')} FCFA")
    print(f"   Compétences: {updated_profile.get('skills', [])[:3]}...")
    print(f"   LinkedIn: {updated_profile.get('linkedin_url')}")
else:
    print(f"❌ Échec mise à jour: {update_response.status_code}")
    print(f"   Détails: {update_response.text[:500]}")

print("\n" + "=" * 80)
print("✅ TEST TERMINÉ")
print("=" * 80)
print(f"\n💡 Endpoint: PUT /api/v1/users/me/profile")
print("   Accessible uniquement aux candidats")
print("\n" + "=" * 80 + "\n")

