"""
Tests pour la transformation automatique des questions MTP (Métier, Talent, Paradigme)
Vérifie que le format legacy (strings) est correctement transformé en format structuré (Dict)
"""
import requests
import json
import pytest

API_BASE_URL = "https://seeg-backend-api.azurewebsites.net"

# Credentials pour les tests (à configurer via env vars en production)
ADMIN_EMAIL = "sevankedesh11@gmail.com"
ADMIN_PASSWORD = "Sevan@Seeg"


@pytest.fixture(scope="module")
def admin_token():
    """Fixture pour obtenir un token admin valide"""
    login_data = {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json=login_data,
        timeout=10
    )
    
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        pytest.skip(f"Impossible de se connecter: {response.status_code}")


def test_mtp_transformation_create_legacy_format(admin_token):
    """
    Test 1: Création d'offre avec questions MTP au format legacy (strings)
    Vérifie que la transformation automatique fonctionne
    """
    job_data = {
        "title": "Test MTP - Format Legacy",
        "description": "<p>Test questionnaire MTP avec format legacy</p>",
        "location": "Libreville",
        "contract_type": "CDI",
        "department": "Informatique",
        "status": "active",
        "offer_status": "tous",
        # Format legacy (comme le frontend envoie)
        "question_metier": "1. Décrivez votre expérience dans ce domaine\n2. Quels sont vos principaux outils de travail ?\n3. Comment assurez-vous la qualité de votre travail ?",
        "question_talent": "1. Quelle est votre principale force ?\n2. Comment gérez-vous le stress ?\n3. Décrivez une réussite professionnelle",
        "question_paradigme": "1. Qu'est-ce qui vous motive ?\n2. Comment restez-vous à jour ?\n3. Votre vision du travail en équipe ?"
    }
    
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/jobs/",
        json=job_data,
        headers=headers,
        timeout=15
    )
    
    assert response.status_code == 200, f"Échec création offre: {response.text}"
    
    result = response.json()
    
    # Vérifier que questions_mtp existe et est structuré
    assert result.get('questions_mtp') is not None, "questions_mtp ne doit pas être NULL"
    
    questions_mtp = result['questions_mtp']
    
    # Vérifier la structure
    assert 'questions_metier' in questions_mtp, "questions_metier manquant"
    assert 'questions_talent' in questions_mtp, "questions_talent manquant"
    assert 'questions_paradigme' in questions_mtp, "questions_paradigme manquant"
    
    # Vérifier que les questions sont des listes
    assert isinstance(questions_mtp['questions_metier'], list)
    assert isinstance(questions_mtp['questions_talent'], list)
    assert isinstance(questions_mtp['questions_paradigme'], list)
    
    # Vérifier le nombre de questions
    assert len(questions_mtp['questions_metier']) == 3
    assert len(questions_mtp['questions_talent']) == 3
    assert len(questions_mtp['questions_paradigme']) == 3
    
    # Vérifier le contenu des questions (première question de chaque type)
    assert "Décrivez votre expérience" in questions_mtp['questions_metier'][0]
    assert "principale force" in questions_mtp['questions_talent'][0]
    assert "vous motive" in questions_mtp['questions_paradigme'][0]
    
    return result.get('id')  # Retourner l'ID pour les tests suivants


def test_mtp_transformation_get_retrieval(admin_token):
    """
    Test 2: Récupération d'offre avec GET
    Vérifie que les questions MTP structurées sont bien retournées
    """
    # Créer d'abord une offre
    job_data = {
        "title": "Test MTP - GET Retrieval",
        "description": "<p>Test récupération GET</p>",
        "location": "Port-Gentil",
        "contract_type": "CDD",
        "department": "RH",
        "status": "active",
        "offer_status": "interne",
        "question_metier": "1. Question métier 1\n2. Question métier 2",
        "question_talent": "1. Question talent 1\n2. Question talent 2",
        "question_paradigme": "1. Question paradigme 1\n2. Question paradigme 2"
    }
    
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    create_response = requests.post(
        f"{API_BASE_URL}/api/v1/jobs/",
        json=job_data,
        headers=headers,
        timeout=15
    )
    
    assert create_response.status_code == 200
    job_id = create_response.json()['id']
    
    # Récupérer avec GET
    get_response = requests.get(
        f"{API_BASE_URL}/api/v1/jobs/{job_id}",
        headers=headers,
        timeout=10
    )
    
    assert get_response.status_code == 200, f"Échec GET: {get_response.text}"
    
    get_result = get_response.json()
    
    # Vérifier que questions_mtp existe
    assert get_result.get('questions_mtp') is not None
    
    get_questions_mtp = get_result['questions_mtp']
    
    # Vérifier que les questions sont présentes et correctes
    assert len(get_questions_mtp['questions_metier']) == 2
    assert len(get_questions_mtp['questions_talent']) == 2
    assert len(get_questions_mtp['questions_paradigme']) == 2


def test_mtp_transformation_post_get_consistency(admin_token):
    """
    Test 3: Cohérence POST/GET
    Vérifie que les questions MTP sont identiques entre POST et GET
    """
    job_data = {
        "title": "Test MTP - Cohérence POST/GET",
        "description": "<p>Test cohérence</p>",
        "location": "Franceville",
        "contract_type": "Stage",
        "department": "Marketing",
        "status": "active",
        "offer_status": "externe",
        "question_metier": "Question 1\nQuestion 2\nQuestion 3",
        "question_talent": "Talent 1\nTalent 2",
        "question_paradigme": "Paradigme 1\nParadigme 2\nParadigme 3"
    }
    
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    # POST
    post_response = requests.post(
        f"{API_BASE_URL}/api/v1/jobs/",
        json=job_data,
        headers=headers,
        timeout=15
    )
    
    assert post_response.status_code == 200
    post_result = post_response.json()
    post_questions = post_result['questions_mtp']
    job_id = post_result['id']
    
    # GET
    get_response = requests.get(
        f"{API_BASE_URL}/api/v1/jobs/{job_id}",
        headers=headers,
        timeout=10
    )
    
    assert get_response.status_code == 200
    get_result = get_response.json()
    get_questions = get_result['questions_mtp']
    
    # Vérifier que les questions sont identiques
    assert post_questions == get_questions, "Les questions MTP doivent être identiques entre POST et GET"


def test_mtp_transformation_update_legacy_format(admin_token):
    """
    Test 4: Mise à jour avec format legacy
    Vérifie que la transformation fonctionne aussi pour les PUT/PATCH
    """
    # Créer une offre
    job_data = {
        "title": "Test MTP - Update",
        "description": "<p>Test mise à jour</p>",
        "location": "Oyem",
        "contract_type": "CDI",
        "status": "active",
        "offer_status": "tous"
    }
    
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    create_response = requests.post(
        f"{API_BASE_URL}/api/v1/jobs/",
        json=job_data,
        headers=headers,
        timeout=15
    )
    
    assert create_response.status_code == 200
    job_id = create_response.json()['id']
    
    # Mettre à jour avec questions MTP
    update_data = {
        "question_metier": "Nouvelle question métier 1\nNouvelle question métier 2",
        "question_talent": "Nouveau talent 1\nNouveau talent 2",
        "question_paradigme": "Nouveau paradigme 1"
    }
    
    update_response = requests.put(
        f"{API_BASE_URL}/api/v1/jobs/{job_id}",
        json=update_data,
        headers=headers,
        timeout=15
    )
    
    assert update_response.status_code == 200
    
    updated_result = update_response.json()
    
    # Vérifier que les questions ont été mises à jour
    assert updated_result.get('questions_mtp') is not None
    questions = updated_result['questions_mtp']
    
    assert len(questions['questions_metier']) == 2
    assert len(questions['questions_talent']) == 2
    assert len(questions['questions_paradigme']) == 1
    assert "Nouvelle question métier" in questions['questions_metier'][0]


def test_mtp_validation_limits(admin_token):
    """
    Test 5: Validation des limites MTP
    Vérifie que les limites (7 métier, 3 talent, 3 paradigme) sont respectées
    """
    # Tester avec trop de questions métier (> 7)
    job_data = {
        "title": "Test MTP - Limites",
        "description": "<p>Test validation limites</p>",
        "location": "Libreville",
        "contract_type": "CDI",
        "status": "active",
        "offer_status": "tous",
        "question_metier": "Q1\nQ2\nQ3\nQ4\nQ5\nQ6\nQ7\nQ8",  # 8 questions (> 7)
        "question_talent": "T1\nT2\nT3",
        "question_paradigme": "P1\nP2\nP3"
    }
    
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/jobs/",
        json=job_data,
        headers=headers,
        timeout=15
    )
    
    # Devrait échouer avec 422 (validation error)
    assert response.status_code == 422, "La validation des limites MTP doit rejeter les questions en excès"


if __name__ == "__main__":
    """
    Permet d'exécuter les tests manuellement pour vérification rapide
    """
    print("\n🧪 TEST DES QUESTIONS MTP - TRANSFORMATION AUTOMATIQUE")
    print("=" * 60)
    
    # Obtenir le token
    login_data = {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json=login_data,
        timeout=10
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print("✅ Token obtenu\n")
        
        try:
            print("Test 1: Création avec format legacy...")
            test_mtp_transformation_create_legacy_format(token)
            print("✅ PASS\n")
            
            print("Test 2: Récupération avec GET...")
            test_mtp_transformation_get_retrieval(token)
            print("✅ PASS\n")
            
            print("Test 3: Cohérence POST/GET...")
            test_mtp_transformation_post_get_consistency(token)
            print("✅ PASS\n")
            
            print("Test 4: Mise à jour avec format legacy...")
            test_mtp_transformation_update_legacy_format(token)
            print("✅ PASS\n")
            
            print("Test 5: Validation des limites...")
            test_mtp_validation_limits(token)
            print("✅ PASS\n")
            
            print("=" * 60)
            print("✅ TOUS LES TESTS PASSENT !")
            
        except AssertionError as e:
            print(f"❌ ÉCHEC: {e}")
    else:
        print(f"❌ Impossible de se connecter: {response.status_code}")

