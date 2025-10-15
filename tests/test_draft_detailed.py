#!/usr/bin/env python3
"""
Test détaillé de sauvegarde de brouillon avec traçage complet
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000/api/v1"

def test_draft_detailed():
    """Test détaillé avec logs"""
    print("🔍 Test détaillé sauvegarde brouillon")
    print("=" * 60)
    
    # 1. Se connecter
    print("🔐 Connexion...")
    login_data = {
        "email": "sevankedesh11@gmail.com",
        "password": "Sevan@Seeg"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"❌ Connexion échouée: {response.status_code}")
        print(f"Réponse: {response.text}")
        return
    
    token = response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Connecté")
    
    # 2. Récupérer une offre d'emploi
    print("\n📋 Récupération offre d'emploi...")
    jobs_response = requests.get(f"{BASE_URL}/jobs", headers=headers)
    if jobs_response.status_code != 200:
        print(f"❌ Récupération offres échouée: {jobs_response.status_code}")
        return
    
    jobs = jobs_response.json() if isinstance(jobs_response.json(), list) else jobs_response.json().get("data", [])
    if not jobs:
        print("❌ Aucune offre d'emploi trouvée")
        return
    
    job_id = jobs[0].get("id")
    print(f"✅ Offre sélectionnée: {job_id}")
    
    # 3. Tester la sauvegarde de brouillon
    print("\n📝 Test sauvegarde brouillon...")
    
    draft_data = {
        "user_id": "37b2f065-71bb-4380-be60-72ba61671cd3",
        "job_offer_id": job_id,
        "form_data": {
            "personal_info": {
                "first_name": "Test",
                "last_name": "User"
            },
            "step_completed": 1
        },
        "ui_state": {
            "current_step": 1,
            "progress": 25
        }
    }
    
    print(f"📤 Envoi payload:")
    print(json.dumps(draft_data, indent=2))
    
    draft_response = requests.post(
        f"{BASE_URL}/applications/drafts",
        headers=headers,
        json=draft_data
    )
    
    print(f"\n📥 Réponse HTTP: {draft_response.status_code}")
    print(f"Headers: {dict(draft_response.headers)}")
    
    if draft_response.status_code == 200:
        response_data = draft_response.json()
        print("\n✅ SUCCÈS!")
        print(json.dumps(response_data, indent=2))
        
        # 4. Test de récupération
        print("\n🔍 Test récupération brouillon...")
        get_response = requests.get(
            f"{BASE_URL}/applications/drafts?job_offer_id={job_id}",
            headers=headers
        )
        
        if get_response.status_code == 200:
            print("✅ Récupération réussie")
            print(json.dumps(get_response.json(), indent=2))
        else:
            print(f"❌ Récupération échouée: {get_response.status_code}")
            print(get_response.text)
    else:
        print(f"\n❌ ÉCHEC: {draft_response.status_code}")
        try:
            error_data = draft_response.json()
            print(json.dumps(error_data, indent=2))
        except:
            print(f"Réponse brute: {draft_response.text}")

if __name__ == "__main__":
    test_draft_detailed()

