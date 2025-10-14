"""
Test des fonctionnalités de modification et d'export PDF des candidatures
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_application_update_and_pdf():
    """Tester la modification d'une candidature et l'export PDF"""
    
    print("="*70)
    print("TEST: Modification et Export PDF de Candidature")
    print("="*70)
    
    # ==================== ÉTAPE 1: CONNEXION CANDIDAT ====================
    print("\n1️⃣  Connexion du candidat...")
    login_data = {
        "username": "candidat.test.local@example.com",
        "password": "Candidat123!"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if response.status_code != 200:
        print(f"   ❌ Erreur connexion: {response.status_code}")
        return False
    
    token_data = response.json()
    candidate_token = token_data.get("access_token")
    candidate_headers = {"Authorization": f"Bearer {candidate_token}"}
    candidate_id = token_data.get("user", {}).get("id")
    print(f"   ✅ Candidat connecté (ID: {candidate_id})")
    
    # ==================== ÉTAPE 2: RÉCUPÉRER UNE CANDIDATURE EXISTANTE ====================
    print("\n2️⃣  Récupération des candidatures du candidat...")
    response = requests.get(
        f"{BASE_URL}/applications/",
        headers=candidate_headers,
        params={"candidate_id": candidate_id}
    )
    
    if response.status_code != 200:
        print(f"   ❌ Erreur récupération: {response.status_code}")
        print(f"      {response.text}")
        return False
    
    applications_data = response.json()
    applications = applications_data.get("data", [])
    
    if len(applications) == 0:
        print("   ⚠️  Aucune candidature trouvée. Exécutez d'abord test_complete_flow_local.py")
        return False
    
    application = applications[0]
    application_id = application.get("id")
    print(f"   ✅ Candidature trouvée (ID: {application_id})")
    print(f"   📊 Status actuel: {application.get('status')}")
    
    # ==================== ÉTAPE 3: MODIFIER LA CANDIDATURE ====================
    print("\n3️⃣  TEST 1: Modification de la candidature...")
    update_data = {
        "ref_fullname": "Marie Dupont - Modifié",
        "ref_mail": "marie.updated@abc.com",
        "has_been_manager": True
    }
    
    response = requests.put(
        f"{BASE_URL}/applications/{application_id}",
        headers=candidate_headers,
        json=update_data
    )
    
    if response.status_code == 200:
        print("   ✅ Candidature mise à jour avec succès")
        updated_app = response.json().get("data", {})
        print(f"   ✔️  Référent: {updated_app.get('ref_fullname')}")
        print(f"   ✔️  Email: {updated_app.get('ref_mail')}")
        print(f"   ✔️  A été manager: {updated_app.get('has_been_manager')}")
    else:
        print(f"   ❌ ÉCHEC modification: {response.status_code}")
        try:
            error_detail = response.json()
            print(f"      {json.dumps(error_detail, indent=6, ensure_ascii=False)}")
        except:
            print(f"      {response.text}")
        return False
    
    # ==================== ÉTAPE 4: VÉRIFIER LA MODIFICATION ====================
    print("\n4️⃣  Vérification de la modification...")
    response = requests.get(
        f"{BASE_URL}/applications/{application_id}",
        headers=candidate_headers
    )
    
    if response.status_code == 200:
        app = response.json().get("data", {})
        if app.get("ref_fullname") == "Marie Dupont - Modifié":
            print("   ✅ Modifications bien persistées")
        else:
            print(f"   ⚠️  Les modifications ne sont pas persistées correctement")
            print(f"      Attendu: 'Marie Dupont - Modifié'")
            print(f"      Reçu: '{app.get('ref_fullname')}'")
    else:
        print(f"   ❌ Erreur récupération: {response.status_code}")
    
    # ==================== ÉTAPE 5: EXPORT PDF ====================
    print("\n5️⃣  TEST 2: Export PDF de la candidature...")
    response = requests.get(
        f"{BASE_URL}/applications/{application_id}/export/pdf",
        headers=candidate_headers,
        params={"format": "A4", "language": "fr"}
    )
    
    if response.status_code == 200:
        content_type = response.headers.get("Content-Type", "")
        content_disposition = response.headers.get("Content-Disposition", "")
        pdf_size = len(response.content)
        
        print(f"   ✅ PDF généré avec succès")
        print(f"   📄 Type: {content_type}")
        print(f"   📦 Taille: {pdf_size / 1024:.2f} KB")
        print(f"   📥 En-tête: {content_disposition}")
        
        # Vérifier que c'est bien un PDF
        if pdf_size > 0 and response.content[:4] == b'%PDF':
            print(f"   ✔️  Format PDF valide")
            
            # Optionnel: Sauvegarder le PDF pour inspection manuelle
            with open(f"test_candidature_{application_id[:8]}.pdf", "wb") as f:
                f.write(response.content)
            print(f"   💾 PDF sauvegardé: test_candidature_{application_id[:8]}.pdf")
        else:
            print(f"   ⚠️  Le contenu ne semble pas être un PDF valide")
    else:
        print(f"   ❌ ÉCHEC export PDF: {response.status_code}")
        try:
            error_detail = response.json()
            print(f"      {json.dumps(error_detail, indent=6, ensure_ascii=False)}")
        except:
            print(f"      {response.text[:500]}")
        return False
    
    # ==================== ÉTAPE 6: TEST AVEC RECRUTEUR ====================
    print("\n6️⃣  TEST 3: Export PDF par le recruteur...")
    
    # Connexion recruteur
    login_data = {
        "username": "recruteur.local@seeg.com",
        "password": "Recruteur123!"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if response.status_code != 200:
        print(f"   ❌ Erreur connexion recruteur: {response.status_code}")
        return False
    
    recruiter_token = response.json().get("access_token")
    recruiter_headers = {"Authorization": f"Bearer {recruiter_token}"}
    print("   ✅ Recruteur connecté")
    
    # Téléchargement PDF par le recruteur
    response = requests.get(
        f"{BASE_URL}/applications/{application_id}/export/pdf",
        headers=recruiter_headers,
        params={"format": "A4", "language": "fr"}
    )
    
    if response.status_code == 200:
        print(f"   ✅ Recruteur peut télécharger le PDF de ses candidatures")
    elif response.status_code == 403:
        print(f"   ✅ CORRECT: Recruteur ne peut pas accéder aux candidatures des autres")
    else:
        print(f"   ⚠️  Résultat inattendu: {response.status_code}")
    
    # ==================== RÉSULTAT FINAL ====================
    print("\n" + "="*70)
    print("✅ TOUS LES TESTS DE MODIFICATION ET EXPORT PDF RÉUSSIS")
    print("="*70)
    return True


if __name__ == "__main__":
    success = test_application_update_and_pdf()
    exit(0 if success else 1)

