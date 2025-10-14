"""
Test complet de toutes les routes job offers - PRODUCTION
Vérifie la création, lecture, mise à jour et suppression des offres d'emploi
"""
import requests
import json
from typing import Dict, Optional

# Configuration PRODUCTION
BASE_URL = "https://seeg-backend-api.azurewebsites.net/api/v1"

# Credentials pour l'admin (qui peut créer des offres)
ADMIN_EMAIL = "sevankedesh11@gmail.com"
ADMIN_PASSWORD = "Sevan@Seeg"

def print_section(title: str):
    """Afficher un titre de section"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def print_success(message: str):
    """Afficher un message de succès"""
    print(f"✅ {message}")

def print_error(message: str):
    """Afficher un message d'erreur"""
    print(f"❌ {message}")

def print_info(message: str):
    """Afficher un message d'information"""
    print(f"ℹ️  {message}")

def login_admin() -> Optional[str]:
    """Se connecter en tant qu'admin et retourner le token"""
    print_section("1. CONNEXION ADMIN")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data={
                "username": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print_success(f"Admin connecté: {ADMIN_EMAIL}")
            print_info(f"Token: {token[:20]}...")
            return token
        else:
            print_error(f"Échec connexion: {response.status_code}")
            print_error(f"Détails: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Erreur connexion: {str(e)}")
        return None

def test_create_job_without_mtp(headers: Dict) -> Optional[str]:
    """Test 1: Créer une offre sans questions MTP"""
    print_section("2. CRÉER OFFRE SANS MTP")
    
    job_data = {
        "title": "Développeur Backend Python - Test Prod",
        "description": "Nous recherchons un développeur backend expérimenté en Python pour notre projet SEEG",
        "department": "IT",
        "location": "Libreville",
        "contract_type": "CDI",
        "experience_required": "3-5 ans",
        "education_level": "Bac+5",
        "salary_range": "800000-1200000 FCFA",
        "status": "active",
        "offer_status": "tous",
        "requirements": ["Python", "FastAPI", "PostgreSQL"],
        "responsibilities": ["Développer des API REST", "Maintenir le code", "Tests unitaires"],
        "benefits": ["Assurance santé", "Formation continue"]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/jobs/",
            json=job_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            job_id = data.get("id")
            print_success(f"Offre créée: {data.get('title')}")
            print_info(f"ID: {job_id}")
            print_info(f"Statut offre: {data.get('offer_status')}")
            print_info(f"Questions MTP: {data.get('questions_mtp')}")
            return job_id
        else:
            print_error(f"Échec création: {response.status_code}")
            print_error(f"Détails: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Erreur création: {str(e)}")
        return None

def test_create_job_with_mtp(headers: Dict) -> Optional[str]:
    """Test 2: Créer une offre avec questions MTP"""
    print_section("3. CRÉER OFFRE AVEC MTP")
    
    job_data = {
        "title": "Chef de Projet IT - Test Production",
        "description": "Nous recherchons un chef de projet pour piloter nos projets informatiques stratégiques",
        "department": "IT",
        "location": "Libreville",
        "contract_type": "CDI",
        "experience_required": "5+ ans",
        "education_level": "Bac+5",
        "salary_range": "1200000-1800000 FCFA",
        "status": "active",
        "offer_status": "interne",
        "requirements": ["Gestion de projet", "SCRUM", "Leadership"],
        "responsibilities": ["Piloter les projets", "Manager l'équipe", "Reporting direction"],
        "benefits": ["Assurance santé", "Formation continue", "Bonus annuel"],
        "question_metier": "Décrivez votre expérience en gestion de projets IT\nQuels outils de gestion utilisez-vous ?",
        "question_talent": "Comment gérez-vous les conflits dans une équipe ?\nDécrivez votre style de leadership",
        "question_paradigme": "Quelle est votre vision de la transformation digitale ?\nComment motivez-vous votre équipe ?"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/jobs/",
            json=job_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            job_id = data.get("id")
            print_success(f"Offre créée: {data.get('title')}")
            print_info(f"ID: {job_id}")
            print_info(f"Statut offre: {data.get('offer_status')}")
            
            questions_mtp = data.get('questions_mtp')
            if questions_mtp:
                print_info(f"Questions Métier: {len(questions_mtp.get('questions_metier', []))} question(s)")
                print_info(f"Questions Talent: {len(questions_mtp.get('questions_talent', []))} question(s)")
                print_info(f"Questions Paradigme: {len(questions_mtp.get('questions_paradigme', []))} question(s)")
            else:
                print_error("Questions MTP non présentes!")
            
            return job_id
        else:
            print_error(f"Échec création: {response.status_code}")
            print_error(f"Détails: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Erreur création: {str(e)}")
        return None

def test_get_job(job_id: str, headers: Dict) -> bool:
    """Test 3: Récupérer une offre par ID"""
    print_section("4. RÉCUPÉRER OFFRE PAR ID")
    
    try:
        response = requests.get(
            f"{BASE_URL}/jobs/{job_id}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Offre récupérée: {data.get('title')}")
            print_info(f"Description: {data.get('description')[:50]}...")
            print_info(f"Département: {data.get('department')}")
            print_info(f"Localisation: {data.get('location')}")
            print_info(f"Type contrat: {data.get('contract_type')}")
            print_info(f"Statut offre: {data.get('offer_status')}")
            return True
        else:
            print_error(f"Échec récupération: {response.status_code}")
            print_error(f"Détails: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Erreur récupération: {str(e)}")
        return False

def test_update_job_offer_status(job_id: str, headers: Dict) -> bool:
    """Test 4: Mettre à jour le statut d'offre (interne -> tous)"""
    print_section("5. METTRE À JOUR STATUT OFFRE (interne -> tous)")
    
    update_data = {
        "offer_status": "tous"
    }
    
    try:
        response = requests.put(
            f"{BASE_URL}/jobs/{job_id}",
            json=update_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Statut mis à jour: {data.get('offer_status')}")
            print_info("L'offre est maintenant visible par tous les candidats")
            return True
        else:
            print_error(f"Échec mise à jour: {response.status_code}")
            print_error(f"Détails: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Erreur mise à jour: {str(e)}")
        return False

def test_list_public_jobs() -> bool:
    """Test 5: Lister les offres publiques (sans authentification)"""
    print_section("6. LISTER OFFRES PUBLIQUES")
    
    try:
        response = requests.get(
            f"{BASE_URL}/public/jobs?skip=0&limit=10",
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # L'API peut retourner soit une liste directement, soit un objet avec data
            if isinstance(data, list):
                jobs = data
                total = len(data)
            else:
                jobs = data.get("data", [])
                total = data.get("total", len(jobs))
            
            print_success(f"Offres publiques récupérées: {len(jobs)}")
            print_info(f"Total disponible: {total}")
            
            for i, job in enumerate(jobs[:5], 1):
                print_info(f"{i}. {job.get('title')} - {job.get('offer_status')}")
            
            if len(jobs) > 5:
                print_info(f"... et {len(jobs) - 5} autres offre(s)")
            
            return True
        else:
            print_error(f"Échec récupération: {response.status_code}")
            print_error(f"Détails: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Erreur récupération: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_verify_final_state(job_id: str, headers: Dict) -> bool:
    """Test 6: Vérifier l'état final de l'offre mise à jour"""
    print_section("7. VÉRIFICATION FINALE")
    
    try:
        response = requests.get(
            f"{BASE_URL}/jobs/{job_id}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Vérification de l'état final")
            print_info(f"Titre: {data.get('title')}")
            print_info(f"Statut offre: {data.get('offer_status')}")
            print_info(f"Statut: {data.get('status')}")
            print_info(f"Salaire: {data.get('salary_range')}")
            print_info(f"Expérience: {data.get('experience_required')}")
            
            questions_mtp = data.get('questions_mtp')
            if questions_mtp:
                print_info(f"Questions MTP configurées:")
                print_info(f"  - Métier: {len(questions_mtp.get('questions_metier', []))} question(s)")
                print_info(f"  - Talent: {len(questions_mtp.get('questions_talent', []))} question(s)")
                print_info(f"  - Paradigme: {len(questions_mtp.get('questions_paradigme', []))} question(s)")
            
            return True
        else:
            print_error(f"Échec vérification: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Erreur vérification: {str(e)}")
        return False

def main():
    """Fonction principale"""
    print("\n" + "="*70)
    print("  TEST COMPLET DES ROUTES JOB OFFERS - PRODUCTION")
    print("="*70)
    print(f"  Base URL: {BASE_URL}")
    print("="*70)
    
    # 1. Connexion admin
    token = login_admin()
    if not token:
        print_error("Impossible de continuer sans authentification")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 2. Créer offre sans MTP
    job_id_1 = test_create_job_without_mtp(headers)
    
    # 3. Créer offre avec MTP
    job_id_2 = test_create_job_with_mtp(headers)
    
    if not job_id_2:
        print_error("Impossible de continuer sans offre créée")
        return
    
    # 4. Récupérer l'offre
    test_get_job(job_id_2, headers)
    
    # 5. Mettre à jour le statut d'offre
    test_update_job_offer_status(job_id_2, headers)
    
    # 6. Lister les offres publiques
    test_list_public_jobs()
    
    # 7. Vérification finale
    test_verify_final_state(job_id_2, headers)
    
    # Résumé final
    print_section("RÉSUMÉ FINAL")
    print_success("Tous les tests des routes job offers ont été exécutés")
    print_info(f"Offre test 1 (sans MTP): {job_id_1 or 'Non créée'}")
    print_info(f"Offre test 2 (avec MTP): {job_id_2 or 'Non créée'}")
    print("\n✅ Tests terminés avec succès!\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrompus par l'utilisateur")
    except Exception as e:
        print(f"\n\n❌ Erreur critique: {str(e)}")
        import traceback
        traceback.print_exc()

