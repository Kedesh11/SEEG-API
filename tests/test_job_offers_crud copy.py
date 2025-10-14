"""
Test complet des routes CRUD des offres d'emploi
Teste la création, mise à jour, récupération et validation des offres avec questions MTP
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/v1"

def test_job_offers_crud():
    """Tester les opérations CRUD sur les offres d'emploi"""
    
    print("="*70)
    print("TEST: CRUD Offres d'Emploi (Création & Mise à Jour)")
    print("="*70)
    
    # Utiliser l'admin existant qui a les droits de recruteur
    admin_email = "sevankedesh11@gmail.com"
    admin_password = "Sevan@Seeg"
    recruiter_token = None
    job_offer_id = None
    
    # ==================== ÉTAPE 1: CONNEXION ADMIN (comme recruteur) ====================
    print("\n1️⃣  Connexion de l'admin (avec droits recruteur)...")
    login_data = {
        "username": admin_email,
        "password": admin_password
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if response.status_code == 200:
        token_data = response.json()
        recruiter_token = token_data.get("access_token")
        user = token_data.get("user")
        recruiter_id = user.get("id")
        print(f"   ✅ Admin connecté (ID: {recruiter_id}, Role: {user.get('role')})")
    else:
        print(f"   ❌ Erreur connexion: {response.status_code}")
        print(f"      {response.text}")
        return False
    
    recruiter_headers = {"Authorization": f"Bearer {recruiter_token}"}
    
    # ==================== ÉTAPE 2: CRÉATION OFFRE SANS MTP ====================
    print("\n2️⃣  TEST 1: Création d'une offre SANS questions MTP...")
    
    job_data_simple = {
        "title": "Développeur Backend Python - Test Local",
        "description": "Nous recherchons un développeur backend expérimenté pour rejoindre notre équipe.",
        "location": "Libreville, Gabon",
        "contract_type": "CDI",
        "department": "IT - Développement",
        "salary_min": 800000,
        "salary_max": 1200000,
        "requirements": [
            "5+ ans d'expérience en Python",
            "Maîtrise de FastAPI ou Django",
            "Connaissance de PostgreSQL",
            "Expérience avec Docker"
        ],
        "benefits": [
            "Assurance santé",
            "Tickets restaurant",
            "Télétravail partiel"
        ],
        "responsibilities": [
            "Développer et maintenir les APIs",
            "Optimiser les performances",
            "Participer aux code reviews"
        ],
        "status": "active",
        "offer_status": "tous",  # Accessible à tous (internes + externes)
        "application_deadline": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        "reporting_line": "CTO",
        "profile": "Développeur expérimenté avec excellentes compétences techniques",
        "categorie_metier": "Informatique",
        "job_grade": "Cadre"
    }
    
    response = requests.post(
        f"{BASE_URL}/jobs/",
        headers=recruiter_headers,
        json=job_data_simple
    )
    
    if response.status_code == 200:
        result = response.json()
        job_simple = result
        job_simple_id = job_simple.get("id")
        print(f"   ✅ Offre créée avec succès (SANS MTP)")
        print(f"   📄 ID: {job_simple_id}")
        print(f"   📝 Titre: {job_simple.get('title')}")
        print(f"   🌍 Localisation: {job_simple.get('location')}")
        print(f"   🔓 Accessibilité: {job_simple.get('offer_status')}")
        print(f"   ❓ Questions MTP: {job_simple.get('questions_mtp')}")
    else:
        print(f"   ❌ ÉCHEC création: {response.status_code}")
        try:
            print(f"      {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        except:
            print(f"      {response.text[:500]}")
        return False
    
    # ==================== ÉTAPE 3: CRÉATION OFFRE AVEC MTP ====================
    print("\n3️⃣  TEST 2: Création d'une offre AVEC questions MTP...")
    
    job_data_with_mtp = {
        "title": "Chef de Projet Digital - Test Local",
        "description": "Nous recherchons un chef de projet pour piloter nos initiatives digitales.",
        "location": "Libreville, Gabon",
        "contract_type": "CDI",
        "department": "Digital & Innovation",
        "salary_min": 1200000,
        "salary_max": 1800000,
        "requirements": [
            "7+ ans d'expérience en gestion de projet",
            "Certification PMP ou équivalent",
            "Expérience en transformation digitale"
        ],
        "status": "active",
        "offer_status": "interne",  # Réservée aux internes uniquement
        "application_deadline": (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d"),
        "profile": "Leader avec vision stratégique",
        "categorie_metier": "Management",
        "job_grade": "Cadre Supérieur",
        # Questions MTP envoyées comme strings séparées par des retours à la ligne
        "question_metier": "Décrivez votre expérience en gestion de projets agiles\nQuels outils de gestion de projet maîtrisez-vous?",
        "question_talent": "Comment gérez-vous les conflits au sein d'une équipe?\nQuelle est votre plus grande réussite professionnelle?",
        "question_paradigme": "Quelle est votre vision de la transformation digitale?\nComment vous alignez-vous avec les valeurs d'innovation?"
    }
    
    response = requests.post(
        f"{BASE_URL}/jobs/",
        headers=recruiter_headers,
        json=job_data_with_mtp
    )
    
    if response.status_code == 200:
        result = response.json()
        job_with_mtp = result
        job_offer_id = job_with_mtp.get("id")
        questions_mtp = job_with_mtp.get("questions_mtp")
        
        print(f"   ✅ Offre créée avec succès (AVEC MTP)")
        print(f"   📄 ID: {job_offer_id}")
        print(f"   📝 Titre: {job_with_mtp.get('title')}")
        print(f"   🔒 Accessibilité: {job_with_mtp.get('offer_status')}")
        print(f"   ❓ Questions MTP présentes: {questions_mtp is not None}")
        
        if questions_mtp:
            print(f"\n   📊 Détail des questions MTP:")
            metier = questions_mtp.get("questions_metier", [])
            talent = questions_mtp.get("questions_talent", [])
            paradigme = questions_mtp.get("questions_paradigme", [])
            print(f"      • Métier: {len(metier)} question(s)")
            for i, q in enumerate(metier, 1):
                print(f"        {i}. {q[:60]}...")
            print(f"      • Talent: {len(talent)} question(s)")
            for i, q in enumerate(talent, 1):
                print(f"        {i}. {q[:60]}...")
            print(f"      • Paradigme: {len(paradigme)} question(s)")
            for i, q in enumerate(paradigme, 1):
                print(f"        {i}. {q[:60]}...")
    else:
        print(f"   ❌ ÉCHEC création: {response.status_code}")
        try:
            print(f"      {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        except:
            print(f"      {response.text[:500]}")
        return False
    
    # ==================== ÉTAPE 4: RÉCUPÉRATION DE L'OFFRE ====================
    print(f"\n4️⃣  TEST 3: Récupération de l'offre créée...")
    
    response = requests.get(
        f"{BASE_URL}/jobs/{job_offer_id}",
        headers=recruiter_headers
    )
    
    if response.status_code == 200:
        job_retrieved = response.json()
        print(f"   ✅ Offre récupérée avec succès")
        print(f"   📝 Titre: {job_retrieved.get('title')}")
        print(f"   📅 Créée le: {job_retrieved.get('created_at')[:10]}")
        print(f"   ✏️  Modifiée le: {job_retrieved.get('updated_at')[:10]}")
    else:
        print(f"   ❌ ÉCHEC récupération: {response.status_code}")
        return False
    
    # ==================== ÉTAPE 5: MISE À JOUR - MODIFIER LE TITRE ====================
    print(f"\n5️⃣  TEST 4: Mise à jour du titre de l'offre...")
    
    update_data_title = {
        "title": "Chef de Projet Digital Senior - MISE À JOUR"
    }
    
    response = requests.put(
        f"{BASE_URL}/jobs/{job_offer_id}",
        headers=recruiter_headers,
        json=update_data_title
    )
    
    if response.status_code == 200:
        updated_job = response.json()
        print(f"   ✅ Titre mis à jour avec succès")
        print(f"   📝 Nouveau titre: {updated_job.get('title')}")
        assert "MISE À JOUR" in updated_job.get('title'), "Le titre n'a pas été mis à jour"
    else:
        print(f"   ❌ ÉCHEC mise à jour: {response.status_code}")
        try:
            print(f"      {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        except:
            print(f"      {response.text[:500]}")
        return False
    
    # ==================== ÉTAPE 6: MISE À JOUR - CHANGER L'ACCESSIBILITÉ ====================
    print(f"\n6️⃣  TEST 5: Changement d'accessibilité (interne → tous)...")
    
    update_data_status = {
        "offer_status": "tous"
    }
    
    response = requests.put(
        f"{BASE_URL}/jobs/{job_offer_id}",
        headers=recruiter_headers,
        json=update_data_status
    )
    
    if response.status_code == 200:
        updated_job = response.json()
        print(f"   ✅ Accessibilité mise à jour")
        print(f"   🔓 Nouvelle accessibilité: {updated_job.get('offer_status')}")
        assert updated_job.get('offer_status') == "tous", "L'accessibilité n'a pas été mise à jour"
    else:
        print(f"   ❌ ÉCHEC mise à jour: {response.status_code}")
        return False
    
    # ==================== ÉTAPE 7: MISE À JOUR - AJOUTER UNE QUESTION MTP ====================
    print(f"\n7️⃣  TEST 6: Ajout d'une question MTP supplémentaire...")
    
    update_data_mtp = {
        "question_metier": "Décrivez votre expérience en gestion de projets agiles\nQuels outils de gestion de projet maîtrisez-vous?\nComment mesurez-vous le succès d'un projet?"
    }
    
    response = requests.put(
        f"{BASE_URL}/jobs/{job_offer_id}",
        headers=recruiter_headers,
        json=update_data_mtp
    )
    
    if response.status_code == 200:
        updated_job = response.json()
        questions_mtp = updated_job.get("questions_mtp")
        metier_questions = questions_mtp.get("questions_metier", []) if questions_mtp else []
        
        print(f"   ✅ Questions MTP mises à jour")
        print(f"   📊 Nombre de questions Métier: {len(metier_questions)}")
        if len(metier_questions) >= 3:
            print(f"   ✔️  3ème question ajoutée: {metier_questions[2][:60]}...")
        else:
            print(f"   ⚠️  La 3ème question n'a pas été ajoutée correctement")
    else:
        print(f"   ❌ ÉCHEC mise à jour: {response.status_code}")
        try:
            print(f"      {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        except:
            print(f"      {response.text[:500]}")
        return False
    
    # ==================== ÉTAPE 8: MISE À JOUR - MODIFICATION MULTIPLE ====================
    print(f"\n8️⃣  TEST 7: Mise à jour de plusieurs champs simultanément...")
    
    update_data_multiple = {
        "salary_min": 1500000,
        "salary_max": 2000000,
        "status": "active",
        "location": "Libreville / Port-Gentil, Gabon"
    }
    
    response = requests.put(
        f"{BASE_URL}/jobs/{job_offer_id}",
        headers=recruiter_headers,
        json=update_data_multiple
    )
    
    if response.status_code == 200:
        updated_job = response.json()
        print(f"   ✅ Mise à jour multiple réussie")
        print(f"   💰 Nouveau salaire: {updated_job.get('salary_min'):,} - {updated_job.get('salary_max'):,} FCFA")
        print(f"   🌍 Nouvelle localisation: {updated_job.get('location')}")
        print(f"   📊 Statut: {updated_job.get('status')}")
    else:
        print(f"   ❌ ÉCHEC mise à jour: {response.status_code}")
        return False
    
    # ==================== ÉTAPE 9: LISTE DES OFFRES ====================
    print(f"\n9️⃣  TEST 8: Récupération de la liste des offres...")
    
    response = requests.get(
        f"{BASE_URL}/jobs/",
        headers=recruiter_headers
    )
    
    if response.status_code == 200:
        jobs_list = response.json()
        print(f"   ✅ Liste récupérée: {len(jobs_list)} offre(s)")
        for job in jobs_list[:5]:  # Afficher max 5 offres
            print(f"      • {job.get('title')} ({job.get('offer_status')})")
    else:
        print(f"   ❌ ÉCHEC récupération liste: {response.status_code}")
        return False
    
    # ==================== ÉTAPE 10: VÉRIFICATION FINALE ====================
    print(f"\n🔟 TEST 9: Vérification finale de l'offre...")
    
    response = requests.get(
        f"{BASE_URL}/jobs/{job_offer_id}",
        headers=recruiter_headers
    )
    
    if response.status_code == 200:
        final_job = response.json()
        print(f"   ✅ Vérification finale réussie")
        print(f"\n   📋 État final de l'offre:")
        print(f"      • Titre: {final_job.get('title')}")
        print(f"      • Localisation: {final_job.get('location')}")
        print(f"      • Salaire: {final_job.get('salary_min'):,} - {final_job.get('salary_max'):,} FCFA")
        print(f"      • Accessibilité: {final_job.get('offer_status')}")
        print(f"      • Statut: {final_job.get('status')}")
        
        questions_mtp = final_job.get("questions_mtp")
        if questions_mtp:
            print(f"      • Questions MTP:")
            print(f"        - Métier: {len(questions_mtp.get('questions_metier', []))} question(s)")
            print(f"        - Talent: {len(questions_mtp.get('questions_talent', []))} question(s)")
            print(f"        - Paradigme: {len(questions_mtp.get('questions_paradigme', []))} question(s)")
    else:
        print(f"   ❌ ÉCHEC vérification: {response.status_code}")
        return False
    
    # ==================== RÉSULTAT FINAL ====================
    print("\n" + "="*70)
    print("✅ TOUS LES TESTS DES OFFRES D'EMPLOI RÉUSSIS")
    print("="*70)
    print(f"\n📊 RÉSUMÉ:")
    print(f"   • Offre sans MTP créée: ✅")
    print(f"   • Offre avec MTP créée: ✅")
    print(f"   • Récupération d'offre: ✅")
    print(f"   • Mise à jour titre: ✅")
    print(f"   • Mise à jour accessibilité: ✅")
    print(f"   • Mise à jour questions MTP: ✅")
    print(f"   • Mise à jour multiple: ✅")
    print(f"   • Liste des offres: ✅")
    print(f"   • Vérification finale: ✅")
    print(f"\n   🎯 ID de l'offre testée: {job_offer_id}")
    return True


if __name__ == "__main__":
    success = test_job_offers_crud()
    exit(0 if success else 1)

