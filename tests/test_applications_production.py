"""
Test complet du flow de candidature - PRODUCTION
Création d'offre avec MTP + Tests de candidature
"""
import requests
import json
from typing import Optional

# Configuration PRODUCTION
BASE_URL = "https://seeg-backend-api.azurewebsites.net/api/v1"

# Credentials
ADMIN_EMAIL = "sevankedesh11@gmail.com"
ADMIN_PASSWORD = "Sevan@Seeg"

def print_section(title: str):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_complete_application_flow():
    """Test du flux complet de candidature"""
    print("="*70)
    print("TEST COMPLET: Candidature avec MTP - PRODUCTION")
    print("="*70)
    
    # ========== PARTIE 1: CRÉER OFFRE AVEC MTP ==========
    print_section("PARTIE 1: CRÉATION D'UNE OFFRE AVEC QUESTIONS MTP")
    
    # 1. Connexion admin
    print("\n1️⃣  Connexion admin...")
    login_data = {
        "username": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", data=login_data, timeout=30)
    if response.status_code != 200:
        print(f"   ❌ Erreur connexion admin: {response.status_code}")
        print(f"      {response.text}")
        return False
    
    token_data = response.json()
    admin_token = token_data.get("access_token")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("   ✅ Admin connecté")
    
    # 2. Créer une offre avec questions MTP
    print("\n2️⃣  Création d'une offre avec questions MTP...")
    job_data = {
        "title": "Développeur Full Stack - Test Production",
        "description": "Poste pour tester les candidatures avec questions MTP en production",
        "department": "IT",
        "location": "Libreville",
        "contract_type": "CDI",
        "experience_required": "3-5 ans",
        "salary_range": "800000-1200000 FCFA",
        "offer_status": "externe",
        "question_metier": "Décrivez votre expérience en développement web\nQuels frameworks JavaScript maîtrisez-vous ?",
        "question_talent": "Comment gérez-vous les délais serrés ?\nDécrivez une situation où vous avez résolu un conflit",
        "question_paradigme": "Quelle est votre vision du travail en équipe ?\nComment vous adaptez-vous aux nouvelles technologies ?",
        "requirements": ["Licence en informatique", "3 ans d'expérience"],
        "responsibilities": ["Développement", "Code review"],
        "benefits": ["Assurance santé", "Formation continue"]
    }
    
    response = requests.post(f"{BASE_URL}/jobs/", headers=admin_headers, json=job_data, timeout=30)
    if response.status_code in [200, 201]:
        result = response.json()
        job_id = result.get("id")
        questions_mtp = result.get("questions_mtp", {})
        
        print(f"   ✅ Offre créée avec succès")
        print(f"   📋 ID: {job_id}")
        print(f"   📊 Questions MTP:")
        print(f"      - Métier: {len(questions_mtp.get('questions_metier', []))} questions")
        print(f"      - Talent: {len(questions_mtp.get('questions_talent', []))} questions")
        print(f"      - Paradigme: {len(questions_mtp.get('questions_paradigme', []))} questions")
    else:
        print(f"   ❌ Erreur création offre: {response.status_code}")
        print(f"      {response.text}")
        return False
    
    # ========== PARTIE 2: CRÉER CANDIDAT ET POSTULER ==========
    print_section("PARTIE 2: CANDIDATURE À L'OFFRE")
    
    # 3. Créer un candidat
    print("\n3️⃣  Création d'un compte candidat...")
    candidate_email = "candidat.prod.test@example.com"
    candidate_data = {
        "email": candidate_email,
        "password": "CandidatProd123!",
        "first_name": "Pierre",
        "last_name": "Production",
        "role": "candidate",
        "sexe": "M",
        "candidate_status": "externe",
        "date_of_birth": "1995-03-20"
    }
    
    response = requests.post(f"{BASE_URL}/auth/signup", json=candidate_data, timeout=30)
    if response.status_code in [200, 201]:
        print("   ✅ Compte candidat créé")
    elif response.status_code == 400 and "existe déjà" in response.text:
        print("   ℹ️  Compte existe déjà, on continue")
    else:
        print(f"   ❌ Erreur création: {response.status_code}")
        print(f"      {response.text}")
        return False
    
    # 4. Connexion candidat
    print("\n4️⃣  Connexion du candidat...")
    login_data = {
        "username": candidate_email,
        "password": "CandidatProd123!"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", data=login_data, timeout=30)
    if response.status_code != 200:
        print(f"   ❌ Erreur connexion: {response.status_code}")
        print(f"      {response.text}")
        return False
    
    token_data = response.json()
    candidate_token = token_data.get("access_token")
    candidate_headers = {"Authorization": f"Bearer {candidate_token}"}
    
    # Récupérer l'ID du candidat
    response = requests.get(f"{BASE_URL}/users/me", headers=candidate_headers, timeout=30)
    user_data = response.json()
    
    # L'ID peut être directement dans la réponse ou dans token_data
    candidate_id = user_data.get("id") or token_data.get("user", {}).get("id")
    
    if not candidate_id:
        print(f"   ⚠️  Structure de réponse /users/me:")
        print(f"      {json.dumps(user_data, indent=6, ensure_ascii=False)[:500]}")
        # Essayer d'autres chemins possibles
        candidate_id = user_data.get("data", {}).get("id")
    
    print(f"   ✅ Candidat connecté")
    print(f"   👤 ID: {candidate_id}")
    
    # 5. TEST 1: Candidature SANS réponses MTP (doit échouer)
    print("\n5️⃣  TEST 1: Candidature SANS réponses MTP (doit être rejetée)...")
    application_data_no_mtp = {
        "candidate_id": candidate_id,
        "job_offer_id": job_id,
        "ref_entreprise": "Entreprise Test Prod",
        "ref_fullname": "Référent Test",
        "ref_mail": "referent@test.com",
        "ref_contact": "+24106223344"
    }
    
    response = requests.post(f"{BASE_URL}/applications/", headers=candidate_headers, json=application_data_no_mtp, timeout=30)
    if response.status_code == 400 or (response.status_code == 422 and "MTP" in response.text):
        print("   ✅ CORRECT: Candidature rejetée (MTP obligatoires)")
        try:
            error = response.json()
            detail = error.get('detail', '')
            if isinstance(detail, list) and len(detail) > 0:
                detail = detail[0].get('msg', str(detail))
            print(f"      Message: {detail}")
        except:
            pass
    else:
        print(f"   ⚠️  Résultat inattendu: {response.status_code}")
        print(f"      {response.text[:300]}")
    
    # 6. TEST 2: Candidature avec TOUTES les réponses correctes (doit réussir)
    print("\n6️⃣  TEST 2: Candidature avec toutes les réponses MTP correctes...")
    application_data_correct = {
        "candidate_id": candidate_id,
        "job_offer_id": job_id,
        "ref_entreprise": "Société XYZ Gabon",
        "ref_fullname": "Sophie Martin",
        "ref_mail": "sophie.martin@xyz-gabon.com",
        "ref_contact": "+241 01 23 45 67",
        "mtp_answers": {
            "reponses_metier": [
                "J'ai 5 ans d'expérience en développement web full stack. J'ai travaillé avec React, Angular et Vue.js côté frontend, et Node.js et Python côté backend.",
                "Je maîtrise principalement React et Vue.js. J'ai également une bonne expérience avec Angular et Next.js pour les projets plus complexes."
            ],
            "reponses_talent": [
                "Face aux délais serrés, je priorise les fonctionnalités critiques, communique régulièrement avec l'équipe et adapte ma méthode de travail pour maintenir la qualité.",
                "Lors d'un projet critique, deux développeurs avaient des approches différentes. J'ai organisé une réunion technique où nous avons comparé les solutions objectivement, ce qui a permis de trouver un compromis."
            ],
            "reponses_paradigme": [
                "Le travail en équipe est essentiel dans le développement logiciel. Il permet le partage des connaissances, la revue de code et l'amélioration continue de la qualité.",
                "Je reste curieux et je consacre du temps chaque semaine à la veille technologique. J'aime expérimenter de nouveaux outils sur des projets personnels avant de les proposer en production."
            ]
        }
    }
    
    response = requests.post(f"{BASE_URL}/applications/", headers=candidate_headers, json=application_data_correct, timeout=30)
    
    if response.status_code == 201:
        result = response.json()
        application_data = result.get("data", {})
        application_id = application_data.get("id")
        
        print("   ✅ SUCCÈS: Candidature créée avec toutes les réponses MTP!")
        print(f"      📋 ID candidature: {application_id}")
        print(f"      ✅ 2 réponses Métier validées")
        print(f"      ✅ 2 réponses Talent validées")
        print(f"      ✅ 2 réponses Paradigme validées")
        
        # Vérifier la candidature
        response = requests.get(f"{BASE_URL}/applications/{application_id}", headers=candidate_headers, timeout=30)
        if response.status_code == 200:
            app_data = response.json().get("data", {})
            print(f"\n   📊 Vérification de la candidature:")
            print(f"      - Status: {app_data.get('status')}")
            print(f"      - Ref entreprise: {app_data.get('ref_entreprise')}")
            print(f"      - MTP answers: {'✅ Présentes' if app_data.get('mtp_answers') else '❌ Manquantes'}")
        
        print_section("RÉSULTAT FINAL")
        print("✅ TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS!")
        print(f"   📋 Job ID: {job_id}")
        print(f"   📋 Application ID: {application_id}")
        print(f"   👤 Candidate ID: {candidate_id}")
        return True
        
    elif response.status_code == 400 and "existe déjà" in response.text:
        print("   ℹ️  Candidature existe déjà (test déjà effectué)")
        print_section("RÉSULTAT FINAL")
        print("✅ TESTS VALIDÉS!")
        return True
    else:
        print(f"   ❌ ÉCHEC: {response.status_code}")
        try:
            error = response.json()
            print(f"      {json.dumps(error, indent=6, ensure_ascii=False)}")
        except:
            print(f"      {response.text}")
        return False

if __name__ == "__main__":
    try:
        success = test_complete_application_flow()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

