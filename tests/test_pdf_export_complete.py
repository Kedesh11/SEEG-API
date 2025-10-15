#!/usr/bin/env python3
"""
Test complet pour l'export PDF des candidatures
"""

import requests
import json
import os
from pathlib import Path

# Configuration
BASE_URL = "https://seeg-backend-api.azurewebsites.net/api/v1"
ADMIN_EMAIL = "admin@seeg.com"
ADMIN_PASSWORD = "Admin@2024!"

def login_admin():
    """Se connecter en tant qu'admin"""
    login_data = {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code == 200:
        token_data = response.json()
        return token_data.get("access_token")
    else:
        print(f"❌ Échec de connexion admin: {response.status_code}")
        print(response.text)
        return None

def get_candidate_token():
    """Se connecter en tant que candidat"""
    # Utiliser un candidat existant ou créer un compte de test
    login_data = {
        "email": "candidate@test.com",
        "password": "Test@2024!"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code == 200:
        token_data = response.json()
        return token_data.get("access_token")
    else:
        print(f"❌ Échec de connexion candidat: {response.status_code}")
        print(response.text)
        return None

def test_pdf_export():
    """Test complet de l'export PDF"""
    print("🚀 Test de l'export PDF des candidatures")
    print("=" * 50)
    
    # 1. Se connecter
    admin_token = login_admin()
    if not admin_token:
        print("❌ Impossible de se connecter en tant qu'admin")
        return False
    
    print("✅ Connexion admin réussie")
    
    # 2. Récupérer une candidature existante
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Lister les candidatures
    response = requests.get(f"{BASE_URL}/applications", headers=headers)
    if response.status_code != 200:
        print(f"❌ Impossible de récupérer les candidatures: {response.status_code}")
        print(response.text)
        return False
    
    applications_data = response.json()
    applications = applications_data.get("data", []) if isinstance(applications_data, dict) else applications_data
    
    if not applications:
        print("❌ Aucune candidature trouvée")
        return False
    
    application = applications[0]
    application_id = application.get("id")
    
    print(f"✅ Candidature trouvée: {application_id}")
    print(f"   Candidat: {application.get('candidate', {}).get('first_name', 'N/A')} {application.get('candidate', {}).get('last_name', 'N/A')}")
    print(f"   Poste: {application.get('job_offer', {}).get('title', 'N/A')}")
    
    # 3. Tester l'export PDF
    pdf_response = requests.get(
        f"{BASE_URL}/applications/{application_id}/export/pdf",
        headers=headers,
        params={"format": "A4", "language": "fr"}
    )
    
    if pdf_response.status_code == 200:
        print("✅ Export PDF réussi")
        
        # Vérifier le type de contenu
        content_type = pdf_response.headers.get("content-type", "")
        print(f"   Type de contenu: {content_type}")
        
        # Vérifier la taille
        pdf_size = len(pdf_response.content)
        print(f"   Taille du PDF: {pdf_size} octets")
        
        # Vérifier l'en-tête PDF
        if pdf_response.content.startswith(b"%PDF"):
            print("✅ Fichier PDF valide (en-tête correct)")
        else:
            print("❌ Fichier PDF invalide (mauvais en-tête)")
            return False
        
        # Sauvegarder le PDF pour inspection
        filename = f"test_candidature_{application_id}.pdf"
        output_path = Path("tests") / "output" / filename
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, "wb") as f:
            f.write(pdf_response.content)
        
        print(f"✅ PDF sauvegardé: {output_path}")
        
        # Vérifier le nom de fichier dans les headers
        content_disposition = pdf_response.headers.get("content-disposition", "")
        print(f"   Nom de fichier suggéré: {content_disposition}")
        
        return True
    else:
        print(f"❌ Échec de l'export PDF: {pdf_response.status_code}")
        print(pdf_response.text)
        return False

def test_pdf_export_with_candidate():
    """Test de l'export PDF en tant que candidat"""
    print("\n🎯 Test de l'export PDF en tant que candidat")
    print("=" * 50)
    
    # Se connecter en tant que candidat
    candidate_token = get_candidate_token()
    if not candidate_token:
        print("❌ Impossible de se connecter en tant que candidat")
        return False
    
    print("✅ Connexion candidat réussie")
    
    # Récupérer les candidatures du candidat
    headers = {"Authorization": f"Bearer {candidate_token}"}
    
    response = requests.get(f"{BASE_URL}/applications", headers=headers)
    if response.status_code != 200:
        print(f"❌ Impossible de récupérer les candidatures: {response.status_code}")
        return False
    
    applications_data = response.json()
    applications = applications_data.get("data", []) if isinstance(applications_data, dict) else applications_data
    
    if not applications:
        print("❌ Aucune candidature trouvée pour ce candidat")
        return False
    
    application = applications[0]
    application_id = application.get("id")
    
    print(f"✅ Candidature candidat trouvée: {application_id}")
    
    # Tester l'export PDF
    pdf_response = requests.get(
        f"{BASE_URL}/applications/{application_id}/export/pdf",
        headers=headers,
        params={"format": "A4", "language": "fr"}
    )
    
    if pdf_response.status_code == 200:
        print("✅ Export PDF candidat réussi")
        
        # Sauvegarder le PDF
        filename = f"test_candidat_{application_id}.pdf"
        output_path = Path("tests") / "output" / filename
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, "wb") as f:
            f.write(pdf_response.content)
        
        print(f"✅ PDF candidat sauvegardé: {output_path}")
        return True
    else:
        print(f"❌ Échec de l'export PDF candidat: {pdf_response.status_code}")
        print(pdf_response.text)
        return False

def main():
    """Fonction principale"""
    print("🔧 Test complet de l'export PDF des candidatures")
    print("=" * 60)
    
    # Test 1: Export en tant qu'admin
    success1 = test_pdf_export()
    
    # Test 2: Export en tant que candidat
    success2 = test_pdf_export_with_candidate()
    
    print("\n" + "=" * 60)
    print("📊 RÉSULTATS DES TESTS")
    print("=" * 60)
    print(f"✅ Export PDF Admin: {'PASSÉ' if success1 else 'ÉCHEC'}")
    print(f"✅ Export PDF Candidat: {'PASSÉ' if success2 else 'ÉCHEC'}")
    
    if success1 and success2:
        print("\n🎉 Tous les tests sont passés avec succès !")
        print("📁 Les fichiers PDF ont été sauvegardés dans tests/output/")
    else:
        print("\n❌ Certains tests ont échoué")
    
    return success1 and success2

if __name__ == "__main__":
    main()
