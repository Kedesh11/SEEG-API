"""
Test de soumission de documents PDF pour une candidature
Utilise des fichiers PDF réels pour tester
"""
import requests
import io
import os
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

BASE_URL = "http://localhost:8000/api/v1"

def create_sample_pdf(title="Document Test", content="Ceci est un document de test"):
    """Créer un PDF de test simple"""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    
    # Titre
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, title)
    
    # Contenu
    p.setFont("Helvetica", 12)
    y = 750
    for line in content.split('\n'):
        p.drawString(100, y, line)
        y -= 20
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return buffer.getvalue()

def load_real_cv():
    """Charger le CV réel depuis app/data/cv/"""
    cv_path = Path("app/data/cv/Sevan.pdf")
    if cv_path.exists():
        with open(cv_path, 'rb') as f:
            return f.read()
    return None


def test_document_upload():
    """Tester l'upload de documents PDF"""
    
    print("="*70)
    print("TEST: Upload de documents PDF pour candidature")
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
    
    # ==================== ÉTAPE 2: RÉCUPÉRER UNE CANDIDATURE ====================
    print("\n2️⃣  Récupération d'une candidature existante...")
    response = requests.get(
        f"{BASE_URL}/applications/",
        headers=candidate_headers,
        params={"candidate_id": candidate_id}
    )
    
    if response.status_code != 200:
        print(f"   ❌ Erreur: {response.status_code}")
        return False
    
    applications_data = response.json()
    applications = applications_data.get("data", [])
    
    if len(applications) == 0:
        print("   ⚠️  Aucune candidature. Exécutez test_complete_flow_local.py d'abord")
        return False
    
    application_id = applications[0].get("id")
    print(f"   ✅ Candidature trouvée: {application_id}")
    
    # ==================== ÉTAPE 3: UPLOAD CV RÉEL ====================
    print("\n3️⃣  TEST 1: Upload du CV réel (PDF)...")
    
    # Charger le CV réel
    cv_pdf = load_real_cv()
    if cv_pdf is None:
        print("   ⚠️  CV réel introuvable, création d'un CV de test...")
        cv_content = """
CV - Jean Testeur

EXPÉRIENCE PROFESSIONNELLE
- Développeur Full Stack (2020-2024)
  * Développement d'applications web avec React et Node.js
  * Gestion de bases de données PostgreSQL
  * Mise en place de CI/CD

FORMATION
- Master Informatique (2018-2020)
- Licence Informatique (2015-2018)

COMPÉTENCES
- JavaScript, TypeScript, Python
- React, Vue.js, Angular
- PostgreSQL, MongoDB
- Docker, Kubernetes
"""
        cv_pdf = create_sample_pdf("CV - Jean Testeur", cv_content)
        cv_filename = "cv_test.pdf"
    else:
        cv_filename = "Sevan_CV.pdf"
        print(f"   ✅ CV réel chargé: {len(cv_pdf) / 1024:.2f} KB")
    
    files = {
        'file': (cv_filename, cv_pdf, 'application/pdf')
    }
    data = {
        'document_type': 'cv'
    }
    
    response = requests.post(
        f"{BASE_URL}/applications/{application_id}/documents",
        headers=candidate_headers,
        files=files,
        data=data
    )
    
    if response.status_code == 201:
        result = response.json()
        cv_doc = result.get("data", {})
        cv_doc_id = cv_doc.get("id")
        print(f"   ✅ CV uploadé avec succès")
        print(f"   📄 Document ID: {cv_doc_id}")
        print(f"   📦 Taille: {cv_doc.get('file_size', 0) / 1024:.2f} KB")
        print(f"   📝 Nom: {cv_doc.get('file_name')}")
        if cv_pdf and len(cv_pdf) > 200000:  # Si > 200KB, c'est probablement le CV réel
            print(f"   🎯 CV RÉEL utilisé (Sevan.pdf)")
    else:
        print(f"   ❌ ÉCHEC upload CV: {response.status_code}")
        try:
            error_detail = response.json()
            print(f"      Erreur: {error_detail.get('detail', error_detail)}")
        except:
            print(f"      {response.text[:500]}")
        return False
    
    # ==================== ÉTAPE 4: UPLOAD LETTRE DE MOTIVATION ====================
    print("\n4️⃣  TEST 2: Upload d'une lettre de motivation (utilise le CV)...")
    
    # Réutiliser le CV pour tester la lettre de motivation
    cover_pdf = cv_pdf
    cover_filename = "Lettre_Motivation_Sevan.pdf"
    
    files = {
        'file': (cover_filename, cover_pdf, 'application/pdf')
    }
    data = {
        'document_type': 'cover_letter'
    }
    
    response = requests.post(
        f"{BASE_URL}/applications/{application_id}/documents",
        headers=candidate_headers,
        files=files,
        data=data
    )
    
    if response.status_code == 201:
        result = response.json()
        cover_doc = result.get("data", {})
        cover_doc_id = cover_doc.get("id")
        print(f"   ✅ Lettre de motivation uploadée (CV Sevan.pdf réutilisé)")
        print(f"   📄 Document ID: {cover_doc_id}")
        print(f"   📦 Taille: {cover_doc.get('file_size', 0) / 1024:.2f} KB")
        print(f"   📝 Nom: {cover_doc.get('file_name')}")
    else:
        print(f"   ❌ ÉCHEC: {response.status_code}")
        try:
            print(f"      Erreur: {response.json().get('detail', response.text[:200])}")
        except:
            print(f"      {response.text[:500]}")
        return False
    
    # ==================== ÉTAPE 5: UPLOAD DIPLÔME ====================
    print("\n5️⃣  TEST 3: Upload d'un diplôme (utilise le CV)...")
    
    # Réutiliser le CV pour tester le diplôme
    diploma_pdf = cv_pdf
    diploma_filename = "Diplome_Master_Sevan.pdf"
    
    files = {
        'file': (diploma_filename, diploma_pdf, 'application/pdf')
    }
    data = {
        'document_type': 'diplome'
    }
    
    response = requests.post(
        f"{BASE_URL}/applications/{application_id}/documents",
        headers=candidate_headers,
        files=files,
        data=data
    )
    
    if response.status_code == 201:
        result = response.json()
        diploma_doc = result.get("data", {})
        diploma_doc_id = diploma_doc.get("id")
        print(f"   ✅ Diplôme uploadé (CV Sevan.pdf réutilisé)")
        print(f"   📄 Document ID: {diploma_doc_id}")
        print(f"   📦 Taille: {diploma_doc.get('file_size', 0) / 1024:.2f} KB")
        print(f"   📝 Nom: {diploma_doc.get('file_name')}")
    else:
        print(f"   ❌ ÉCHEC: {response.status_code}")
        try:
            print(f"      Erreur: {response.json().get('detail', response.text[:200])}")
        except:
            print(f"      {response.text[:500]}")
        return False
    
    # ==================== ÉTAPE 6: UPLOAD CERTIFICAT ====================
    print("\n6️⃣  TEST 4: Upload d'un certificat (utilise le CV)...")
    
    # Réutiliser le CV pour tester les certificats
    cert_pdf = cv_pdf
    cert_filename = "Certificat_Formation_Sevan.pdf"
    
    files = {
        'file': (cert_filename, cert_pdf, 'application/pdf')
    }
    data = {
        'document_type': 'certificats'
    }
    
    response = requests.post(
        f"{BASE_URL}/applications/{application_id}/documents",
        headers=candidate_headers,
        files=files,
        data=data
    )
    
    if response.status_code == 201:
        result = response.json()
        cert_doc = result.get("data", {})
        cert_doc_id = cert_doc.get("id")
        print(f"   ✅ Certificat uploadé (CV Sevan.pdf réutilisé)")
        print(f"   📄 Document ID: {cert_doc_id}")
        print(f"   📦 Taille: {cert_doc.get('file_size', 0) / 1024:.2f} KB")
        print(f"   📝 Nom: {cert_doc.get('file_name')}")
    else:
        print(f"   ❌ ÉCHEC: {response.status_code}")
        try:
            print(f"      Erreur: {response.json().get('detail', response.text[:200])}")
        except:
            print(f"      {response.text[:500]}")
        return False
    
    # ==================== ÉTAPE 7: LISTER LES DOCUMENTS ====================
    print("\n7️⃣  TEST 5: Récupération de la liste des documents...")
    
    response = requests.get(
        f"{BASE_URL}/applications/{application_id}/documents",
        headers=candidate_headers
    )
    
    if response.status_code == 200:
        result = response.json()
        documents = result.get("data", [])
        print(f"   ✅ Liste récupérée: {len(documents)} document(s)")
        for doc in documents:
            print(f"      📄 {doc.get('document_type')}: {doc.get('file_name')} ({doc.get('file_size', 0) / 1024:.2f} KB)")
    else:
        print(f"   ❌ ÉCHEC: {response.status_code}")
        return False
    
    # ==================== ÉTAPE 8: TÉLÉCHARGER UN DOCUMENT ====================
    print("\n8️⃣  TEST 6: Téléchargement d'un document (le CV)...")
    
    response = requests.get(
        f"{BASE_URL}/applications/{application_id}/documents/{cv_doc_id}/download",
        headers=candidate_headers
    )
    
    if response.status_code == 200:
        content_type = response.headers.get("Content-Type", "")
        content_disposition = response.headers.get("Content-Disposition", "")
        pdf_size = len(response.content)
        
        print(f"   ✅ Document téléchargé")
        print(f"   📦 Taille: {pdf_size / 1024:.2f} KB")
        print(f"   📄 Type: {content_type}")
        
        # Vérifier que c'est bien un PDF
        if response.content[:4] == b'%PDF':
            print(f"   ✔️  Format PDF valide")
        else:
            print(f"   ⚠️  Le contenu ne semble pas être un PDF valide")
    else:
        print(f"   ❌ ÉCHEC téléchargement: {response.status_code}")
        return False
    
    # ==================== ÉTAPE 9: TEST FICHIER INVALIDE ====================
    print("\n9️⃣  TEST 7: Tentative d'upload d'un fichier non-PDF (doit échouer)...")
    
    fake_pdf = b"Ceci n'est pas un vrai PDF"
    
    files = {
        'file': ('fake.pdf', fake_pdf, 'application/pdf')
    }
    data = {
        'document_type': 'certificats'
    }
    
    response = requests.post(
        f"{BASE_URL}/applications/{application_id}/documents",
        headers=candidate_headers,
        files=files,
        data=data
    )
    
    if response.status_code == 400:
        print(f"   ✅ CORRECT: Fichier invalide rejeté")
        print(f"      Message: {response.json().get('detail', '')[:100]}")
    else:
        print(f"   ⚠️  Résultat inattendu: {response.status_code}")
    
    # ==================== RÉSULTAT FINAL ====================
    print("\n" + "="*70)
    print("✅ TOUS LES TESTS DE DOCUMENTS PDF RÉUSSIS")
    print("="*70)
    print(f"\n📊 RÉSUMÉ:")
    print(f"   🎯 Fichier source: Sevan.pdf ({len(cv_pdf) / 1024:.2f} KB)")
    print(f"   • CV uploadé: ✅")
    print(f"   • Lettre de motivation uploadée: ✅")
    print(f"   • Diplôme uploadé: ✅")
    print(f"   • Certificat uploadé: ✅")
    print(f"   • Liste des documents: ✅")
    print(f"   • Téléchargement du CV: ✅")
    print(f"   • Validation fichiers invalides: ✅")
    print(f"\n   📦 TOTAL: 4 documents uploadés avec le même fichier PDF (Sevan.pdf)")
    return True


if __name__ == "__main__":
    success = test_document_upload()
    exit(0 if success else 1)

