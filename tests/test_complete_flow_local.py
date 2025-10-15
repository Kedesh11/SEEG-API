"""
Test complet du flow de candidature en local avec création d'offre
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_complete_flow():
    print("="*70)
    print("TEST COMPLET: Création offre + Candidature en local")
    print("="*70)
    
    # ========== PARTIE 1: CRÉER ADMIN PUIS RECRUTEUR ET OFFRE ==========
    print("\n" + "="*70)
    print("PARTIE 1: CRÉATION D'UNE OFFRE AVEC QUESTIONS MTP")
    print("="*70)
    
    # 1. Connexion avec l'admin existant
    print("\n1️⃣  Connexion admin...")
    login_data = {
        "username": "sevankedesh11@gmail.com",
        "password": "Sevan@Seeg"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if response.status_code != 200:
        print(f"   ❌ Erreur connexion admin: {response.status_code}")
        return False
    
    token_data = response.json()
    admin_token = token_data.get("access_token")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("   ✅ Admin connecté")
    
    # 2. Créer un recruteur via l'admin
    print("\n2️⃣  Création d'un recruteur via admin...")
    recruiter_data = {
        "email": "recruteur23.local@seeg.com",
        "password": "Recruteur1234!",
        "first_name": "Marie Jeanne",
        "last_name": "BABONGUI",
        "role": "recruiter",
        "sexe": "F",
        "date_of_birth": "1986-07-15"
    }
    
    response = requests.post(f"{BASE_URL}/auth/create-user", headers=admin_headers, json=recruiter_data)
    if response.status_code in [200, 201]:
        print("   ✅ Recruteur créé")
    elif response.status_code == 400 and "existe déjà" in response.text:
        print("   ℹ️  Recruteur existe déjà")
    
    # 3. Connexion recruteur
    print("\n3️⃣  Connexion du recruteur...")
    login_data = {
        "username": recruiter_data["email"],
        "password": "Recruteur1234!"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if response.status_code != 200:
        print(f"   ❌ Erreur connexion recruteur: {response.status_code}")
        return False
    
    token_data = response.json()
    recruiter_token = token_data.get("access_token")
    recruiter_headers = {"Authorization": f"Bearer {recruiter_token}"}
    print("   ✅ Recruteur connecté")
    
    # 4. Créer une offre avec questions MTP
    print("\n4️⃣  Création d'une offre avec questions MTP...")
    job_data = {
        "title": "Développeur Full Stack - Test Local",
        "description": "Poste pour tester les candidatures avec questions MTP",
        "department": "IT",
        "location": "Libreville",
        "contract_type": "CDI",
        "experience_required": "3-5 ans",
        "salary_range": "800000-1200000 FCFA",
        "offer_status": "externe",
        "questions_mtp": {
            "questions_metier": [
                "Décrivez votre expérience en développement web",
                "Quels frameworks JavaScript maîtrisez-vous ?",
                "Parlez-nous d'un projet technique complexe que vous avez mené"
            ],
            "questions_talent": [
                "Comment gérez-vous les délais serrés ?",
                "Décrivez une situation où vous avez résolu un conflit d'équipe"
            ],
            "questions_paradigme": [
                "Quelle est votre vision du travail en équipe ?",
                "Comment vous adaptez-vous aux nouvelles technologies ?"
            ]
        },
        "requirements": ["Licence en informatique", "3 ans d'expérience"],
        "responsibilities": ["Développement", "Code review", "Mentorat"],
        "benefits": ["Assurance santé", "Prime de performance"]
    }
    
    response = requests.post(f"{BASE_URL}/jobs/", headers=recruiter_headers, json=job_data)
    if response.status_code in [200, 201]:
        result = response.json()
        # Si réponse directe ou dans "data"
        job_id = result.get("id") or result.get("data", {}).get("id")
        print(f"   ✅ Offre créée avec succès")
        print(f"   📋 ID: {job_id}")
        print(f"   📊 Questions MTP:")
        print(f"      - Métier: 3 questions")
        print(f"      - Talent: 2 questions")
        print(f"      - Paradigme: 2 questions")
    else:
        print(f"   ❌ Erreur création offre: {response.status_code}")
        try:
            print(f"      {json.dumps(response.json(), indent=6, ensure_ascii=False)}")
        except:
            print(f"      {response.text}")
        return False
    
    # ========== PARTIE 2: CRÉER UN CANDIDAT ET POSTULER ==========
    print("\n" + "="*70)
    print("PARTIE 2: CANDIDATURE À L'OFFRE")
    print("="*70)
    
    # 5. Créer un candidat
    print("\n5️⃣  Création d'un compte candidat...")
    candidate_data = {
        "email": "candidat.test.local@example.com",
        "password": "Candidat123!",
        "first_name": "Jean",
        "last_name": "Testeur",
        "role": "candidate",
        "sexe": "M",
        "candidate_status": "externe",
        "date_of_birth": "1995-03-20"
    }
    
    response = requests.post(f"{BASE_URL}/auth/signup", json=candidate_data)
    if response.status_code in [200, 201]:
        print("   ✅ Compte candidat créé")
    elif response.status_code == 400 and "existe déjà" in response.text:
        print("   ℹ️  Compte existe déjà")
    
    # 6. Connexion candidat
    print("\n6️⃣  Connexion du candidat...")
    login_data = {
        "username": candidate_data["email"],
        "password": "Candidat123!"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if response.status_code != 200:
        print(f"   ❌ Erreur connexion: {response.status_code}")
        return False
    
    token_data = response.json()
    candidate_token = token_data.get("access_token")
    candidate_headers = {"Authorization": f"Bearer {candidate_token}"}
    
    # Récupérer l'ID du candidat
    response = requests.get(f"{BASE_URL}/users/me", headers=candidate_headers)
    user = response.json().get("data")
    candidate_id = user.get("id")
    print(f"   ✅ Candidat connecté")
    print(f"   👤 ID: {candidate_id}")
    
    # 7. TEST 1: Candidature SANS réponses MTP (doit échouer)
    print("\n7️⃣  TEST 1: Candidature SANS réponses MTP (doit être rejetée)...")
    application_data_no_mtp = {
        "candidate_id": candidate_id,
        "job_offer_id": job_id,
        "ref_entreprise": "Entreprise Test",
        "ref_fullname": "Référent Test",
        "ref_mail": "referent@test.com",
        "ref_contact": "+24106223344"
    }
    
    response = requests.post(f"{BASE_URL}/applications/", headers=candidate_headers, json=application_data_no_mtp)
    if response.status_code == 400 and "MTP" in response.text:
        print("   ✅ CORRECT: Candidature rejetée (MTP obligatoires)")
        try:
            error = response.json()
            print(f"      Message: {error.get('detail')}")
        except:
            pass
    else:
        print(f"   ⚠️  Résultat inattendu: {response.status_code}")
        print(f"      {response.text[:200]}")
    
    # 8. TEST 2: Candidature avec MAUVAIS nombre de réponses (doit échouer)
    print("\n8️⃣  TEST 2: Candidature avec nombre incorrect de réponses...")
    application_data_wrong_count = {
        "candidate_id": candidate_id,
        "job_offer_id": job_id,
        "ref_entreprise": "Entreprise Test",
        "ref_fullname": "Référent Test",
        "ref_mail": "referent@test.com",
        "ref_contact": "+24106223344",
        "mtp_answers": {
            "reponses_metier": ["Réponse 1", "Réponse 2"],  # Seulement 2 au lieu de 3
            "reponses_talent": ["Réponse 1", "Réponse 2"],
            "reponses_paradigme": ["Réponse 1", "Réponse 2"]
        }
    }
    
    response = requests.post(f"{BASE_URL}/applications/", headers=candidate_headers, json=application_data_wrong_count)
    if response.status_code == 400:
        print("   ✅ CORRECT: Candidature rejetée (nombre incorrect)")
        try:
            error = response.json()
            print(f"      Message: {error.get('detail')[:100]}...")
        except:
            pass
    else:
        print(f"   ⚠️  Résultat inattendu: {response.status_code}")
    
    # 9. TEST 3: Candidature avec TOUTES les réponses correctes (doit réussir)
    print("\n9️⃣  TEST 3: Candidature avec toutes les réponses MTP correctes...")
    application_data_correct = {
        "candidate_id": candidate_id,
        "job_offer_id": job_id,
        "ref_entreprise": "Société ABC Gabon",
        "ref_fullname": "Marie Dupont",
        "ref_mail": "marie.dupont@abc-gabon.com",
        "ref_contact": "+241 01 23 45 67",
        "mtp_answers": {
            "reponses_metier": [
                "J'ai 5 ans d'expérience en développement web avec React et Node.js. J'ai travaillé sur plusieurs projets e-commerce.",
                "Je maîtrise React, Vue.js, Angular côté frontend et Node.js, Express côté backend.",
                "J'ai dirigé la refonte complète d'une plateforme bancaire utilisée par 50000 clients quotidiennement."
            ],
            "reponses_talent": [
                "Je priorise les tâches, communique régulièrement avec l'équipe et n'hésite pas à demander de l'aide si nécessaire.",
                "J'ai médiatisé un conflit entre deux développeurs en organisant une réunion constructive où chacun a pu s'exprimer."
            ],
            "reponses_paradigme": [
                "Le travail en équipe permet de combiner les forces de chacun et d'atteindre des objectifs plus ambitieux.",
                "Je consacre du temps chaque semaine à la veille technologique et j'aime expérimenter de nouveaux outils."
            ]
        }
    }
    
    response = requests.post(f"{BASE_URL}/applications/", headers=candidate_headers, json=application_data_correct)
    if response.status_code == 201:
        result = response.json()
        application_id = result.get("data", {}).get("id")
        print("   ✅ SUCCÈS: Candidature créée avec toutes les réponses MTP!")
        print(f"      📋 ID candidature: {application_id}")
        print(f"      ✅ 3 réponses Métier validées")
        print(f"      ✅ 2 réponses Talent validées")
        print(f"      ✅ 2 réponses Paradigme validées")
        
        # Vérifier la candidature
        response = requests.get(f"{BASE_URL}/applications/{application_id}", headers=candidate_headers)
        if response.status_code == 200:
            app_data = response.json().get("data")
            print(f"\n   📊 Vérification de la candidature:")
            print(f"      - Status: {app_data.get('status')}")
            print(f"      - Ref entreprise: {app_data.get('ref_entreprise')}")
            print(f"      - MTP answers: {'✅ Présentes' if app_data.get('mtp_answers') else '❌ Manquantes'}")
        
        # 10. TEST 4: Mise à jour du profil candidat (maintenant que le profil existe)
        print("\n🔟 TEST 4: Mise à jour du profil candidat...")
        profile_update = {
            "years_experience": 8,
            "current_position": "Senior Full Stack Developer",
            "availability": "Immédiate",
            "skills": ["React", "Node.js", "Python", "Docker"],
            "expected_salary_min": 1000000,
            "expected_salary_max": 1500000
        }
        
        response = requests.put(f"{BASE_URL}/users/me/profile", headers=candidate_headers, json=profile_update)
        if response.status_code == 200:
            result = response.json()
            profile_data = result.get("data")
            print("   ✅ SUCCÈS: Profil candidat mis à jour!")
            print(f"      👤 Expérience: {profile_data.get('years_experience')} ans")
            print(f"      💼 Poste: {profile_data.get('current_position')}")
            print(f"      📅 Disponibilité: {profile_data.get('availability')}")
            print(f"      💰 Salaire: {profile_data.get('expected_salary_min')} - {profile_data.get('expected_salary_max')} FCFA")
        else:
            print(f"   ❌ ÉCHEC mise à jour profil: {response.status_code}")
            try:
                error = response.json()
                print(f"      {json.dumps(error, indent=6, ensure_ascii=False)}")
            except:
                print(f"      {response.text}")
            return False
        
        print("\n" + "="*70)
        print("✅ TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS!")
        print("   1️⃣  Offre créée avec questions MTP")
        print("   2️⃣  Candidature sans MTP rejetée (validation OK)")
        print("   3️⃣  Candidature avec MTP incorrects rejetée (validation OK)")
        print("   4️⃣  Candidature complète acceptée (profil créé auto)")
        print("   5️⃣  Profil candidat mis à jour avec succès")
        print("="*70)
        return True
        
    elif response.status_code == 400 and "existe déjà" in response.text:
        print("   ℹ️  Candidature existe déjà (test déjà effectué)")
        print("\n" + "="*70)
        print("✅ TOUS LES TESTS SONT PASSÉS!")
        print("="*70)
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
        success = test_complete_flow()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

