"""
Test pour vérifier que GET /applications/{id} retourne bien les infos complètes du candidat
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "sevankedesh11@gmail.com"
ADMIN_PASSWORD = "Sevan@Seeg"

print("\n" + "=" * 80)
print("  🧪 TEST - DÉTAILS CANDIDATURE AVEC INFOS CANDIDAT")
print("=" * 80)

# Connexion admin
print("\n🔐 Connexion admin...")
login = requests.post(
    f"{BASE_URL}/auth/login",
    data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    timeout=10
)

if login.status_code != 200:
    print(f"❌ Échec: {login.status_code}")
    exit(1)

token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("✅ Connecté")

# Récupérer une candidature
print("\n📋 Récupération d'une candidature...")
apps_response = requests.get(
    f"{BASE_URL}/applications/",
    headers=headers,
    params={"limit": 1},
    timeout=10
)

if apps_response.status_code != 200:
    print(f"❌ Erreur: {apps_response.status_code}")
    exit(1)

apps_data = apps_response.json()
applications = apps_data.get("data", [])

if not applications:
    print("❌ Aucune candidature trouvée")
    exit(1)

application_id = applications[0].get("id")
print(f"✅ Candidature ID: {application_id}")

# Récupérer les détails de la candidature
print(f"\n📊 Récupération détails candidature...")
print(f"   GET /applications/{application_id}")

details_response = requests.get(
    f"{BASE_URL}/applications/{application_id}",
    headers=headers,
    timeout=10
)

if details_response.status_code == 200:
    response_json = details_response.json()
    details = response_json.get("data", {})
    
    print("\n✅ DÉTAILS RÉCUPÉRÉS !")
    print(f"\n📦 Clés dans la réponse: {list(details.keys())}")
    print(f"\n🆔 ID Candidature: {details.get('id')}")
    print(f"📊 Statut: {details.get('status')}")
    
    # Informations candidat
    candidate = details.get("candidate")
    if candidate:
        print(f"\n👤 CANDIDAT (relations chargées):")
        print(f"   Nom: {candidate.get('first_name')} {candidate.get('last_name')}")
        print(f"   Email: {candidate.get('email')}")
        print(f"   Téléphone: {candidate.get('phone', 'N/A')}")
        print(f"   Date naissance: {candidate.get('date_of_birth', 'N/A')}")
        print(f"   Sexe: {candidate.get('sexe', 'N/A')}")
        print(f"   Statut: {candidate.get('candidate_status', 'N/A')}")
        
        # Profil candidat
        profile = candidate.get("candidate_profile")
        if profile:
            print(f"\n📋 PROFIL CANDIDAT:")
            print(f"   Années expérience: {profile.get('years_experience', 'N/A')}")
            print(f"   Poste actuel: {profile.get('current_position', 'N/A')}")
            print(f"   Département: {profile.get('current_department', 'N/A')}")
            print(f"   Disponibilité: {profile.get('availability', 'N/A')}")
            print(f"   Salaire min: {profile.get('expected_salary_min', 'N/A')}")
            print(f"   Salaire max: {profile.get('expected_salary_max', 'N/A')}")
            
            skills = profile.get('skills')
            if skills and skills != "N/A":
                print(f"   Compétences: Présentes")
            
            education = profile.get('education')
            if education and education != "N/A":
                print(f"   Formation: Présente")
        else:
            print(f"\n📋 PROFIL: Non rempli")
    else:
        print(f"\n⚠️ CANDIDAT: Relation non chargée (seulement candidate_id: {details.get('candidate_id')})")
    
    # Informations offre
    job_offer = details.get("job_offer")
    if job_offer:
        print(f"\n💼 OFFRE D'EMPLOI:")
        print(f"   Titre: {job_offer.get('title')}")
        print(f"   Département: {job_offer.get('department', 'N/A')}")
        print(f"   Type contrat: {job_offer.get('contract_type', 'N/A')}")
        print(f"   Localisation: {job_offer.get('location', 'N/A')}")
    else:
        print(f"\n⚠️ OFFRE: Relation non chargée (seulement job_offer_id: {details.get('job_offer_id')})")
    
    # Documents
    documents = details.get("documents", [])
    print(f"\n📎 DOCUMENTS: {len(documents)} document(s)")
    
    # Historique
    history = details.get("history", [])
    print(f"📜 HISTORIQUE: {len(history)} entrée(s)")
    
    # Entretiens
    interviews = details.get("interview_slots", [])
    print(f"📅 ENTRETIENS: {len(interviews)} entretien(s)")
    
else:
    print(f"❌ Échec: {details_response.status_code}")
    print(f"Détails: {details_response.text[:300]}")

print("\n" + "=" * 80)
print("✅ TEST TERMINÉ")
print("=" * 80)
print("\n💡 Si les relations 'candidate' et 'job_offer' sont présentes,")
print("   les admins et recruteurs ont accès à toutes les informations !")
print("\n" + "=" * 80 + "\n")

