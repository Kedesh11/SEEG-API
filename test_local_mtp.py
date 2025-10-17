#!/usr/bin/env python3
"""
Test local du système MTP (Métier, Talent, Paradigme)
Teste la création d'offre avec questions MTP et candidature avec réponses
"""
import asyncio
import httpx
import base64
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"

# Lire le vrai PDF depuis le dossier data/cv
PDF_PATH = Path("app/data/cv/Sevan.pdf")
with open(PDF_PATH, "rb") as f:
    PDF = base64.b64encode(f.read()).decode('utf-8')

print(f"📄 PDF chargé: {PDF_PATH.name} ({len(PDF)} caractères en base64)")

async def main():
    async with httpx.AsyncClient(timeout=60.0, base_url=BASE_URL) as client:
        print("\n" + "="*80)
        print("🧪 TEST LOCAL - Système MTP Flexible")
        print("="*80)
        
        # 1. Login admin
        print("\n[1/4] Connexion admin...")
        login = await client.post("/auth/login", json={
            "email": "sevankedesh11@gmail.com",
            "password": "Sevan@Seeg"
        })
        
        if login.status_code != 200:
            print(f"❌ Login failed: {login.status_code}")
            print(f"Response: {login.text}")
            print("💡 Assurez-vous que l'API est démarrée: uvicorn app.main:app --reload")
            return False
        
        token = login.json()["access_token"]
        user = login.json()["user"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"✅ Admin connecté: {user['first_name']} {user['last_name']}")
        
        # 2. Créer une offre avec questions MTP flexibles
        print("\n[2/4] Création d'une offre avec questions MTP...")
        job_data = {
            "title": "Ingénieur DevOps - Test MTP",
            "description": "Poste pour tester le système MTP flexible",
            "location": "Libreville",
            "contract_type": "CDI",
            "status": "active",
            "offer_status": "tous",
            "questions_mtp": {
                "questions_metier": [
                    "Décrivez votre expérience avec Kubernetes",
                    "Quels outils CI/CD avez-vous utilisés?",
                    "Parlez-nous de votre plus grand projet DevOps"
                ],
                "questions_talent": [
                    "Comment gérez-vous le stress des incidents production?",
                    "Quelle est votre approche pour apprendre de nouvelles technologies?"
                ],
                "questions_paradigme": [
                    "Quelle est votre vision de l'automatisation en entreprise?"
                ]
            }
        }
        
        job_response = await client.post("/jobs/", json=job_data, headers=headers)
        
        if job_response.status_code != 201:
            print(f"❌ Création offre échouée: {job_response.status_code}")
            print(f"Response: {job_response.text}")
            return False
        
        job = job_response.json()
        print(f"✅ Offre créée: {job['title']}")
        print(f"   ID: {job['id']}")
        if job.get('questions_mtp'):
            print(f"   Questions métier: {len(job['questions_mtp']['questions_metier'])}")
            print(f"   Questions talent: {len(job['questions_mtp']['questions_talent'])}")
            print(f"   Questions paradigme: {len(job['questions_mtp']['questions_paradigme'])}")
        
        # 3. Créer un candidat externe pour tester
        print("\n[3/4] Création d'un candidat test...")
        candidate_data = {
            "email": f"test.mtp.{asyncio.get_event_loop().time()}@gmail.com",
            "password": "TestSecure123!",
            "first_name": "Test",
            "last_name": "MTP",
            "phone": "+24106111111",
            "date_of_birth": "1990-05-15",
            "sexe": "M",
            "candidate_status": "externe"
        }
        
        signup_response = await client.post("/auth/signup", json=candidate_data)
        
        if signup_response.status_code != 201:
            print(f"❌ Création candidat échouée: {signup_response.status_code}")
            print(f"Response: {signup_response.text}")
            return False
        
        candidate = signup_response.json()
        print(f"✅ Candidat créé: {candidate['first_name']} {candidate['last_name']}")
        print(f"   ID: {candidate['id']}")
        
        # Login du candidat pour obtenir un token
        print("   🔑 Login du candidat...")
        candidate_login = await client.post("/auth/login", json={
            "email": candidate_data["email"],
            "password": candidate_data["password"]
        })
        
        if candidate_login.status_code != 200:
            print(f"❌ Login candidat échoué: {candidate_login.status_code}")
            return False
        
        candidate_token = candidate_login.json()["access_token"]
        candidate_headers = {"Authorization": f"Bearer {candidate_token}"}
        print(f"   ✅ Token obtenu")
        
        # 4. Soumettre candidature avec réponses MTP
        print("\n[4/4] Soumission candidature avec réponses MTP...")
        app_data = {
            "candidate_id": candidate['id'],
            "job_offer_id": job['id'],
            "mtp_answers": {
                "reponses_metier": [
                    "J'ai 3 ans d'expérience avec Kubernetes en production...",
                    "Jenkins, GitLab CI, GitHub Actions, ArgoCD...",
                    "Migration d'une infrastructure on-premise vers Azure avec 99.9% uptime..."
                ],
                "reponses_talent": [
                    "Je reste calme et méthodique, je priorise selon l'impact...",
                    "Documentation technique, tutoriels, projets personnels..."
                ],
                "reponses_paradigme": [
                    "L'automatisation libère les équipes pour l'innovation stratégique..."
                ]
            },
            "documents": [
                {"document_type": "cv", "file_name": "Sevan_CV.pdf", "file_data": PDF},
                {"document_type": "cover_letter", "file_name": "Sevan_Lettre.pdf", "file_data": PDF},
                {"document_type": "diplome", "file_name": "Sevan_Diplome.pdf", "file_data": PDF}
            ]
        }
        
        app_response = await client.post("/applications/", json=app_data, headers=candidate_headers)
        
        print(f"\n📊 RÉSULTAT: HTTP {app_response.status_code}")
        print("="*80)
        
        if app_response.status_code == 201:
            app_json = app_response.json()
            print(f"\n✅ Réponse complète: {list(app_json.keys())}")
            
            # Le endpoint retourne {"success": true, "message": "...", "data": {...}}
            if "data" in app_json:
                app = app_json["data"]
            else:
                app = app_json
            
            print("\n✅ ✅ ✅ SUCCÈS ! ✅ ✅ ✅\n")
            print(f"Application ID: {app['id']}")
            print(f"Status: {app['status']}")
            print(f"\n🎉 Système MTP Flexible fonctionne parfaitement !")
            
            if app.get('mtp_answers'):
                print(f"\n📝 Réponses MTP enregistrées:")
                print(f"   Métier: {len(app['mtp_answers']['reponses_metier'])} réponses")
                print(f"   Talent: {len(app['mtp_answers']['reponses_talent'])} réponses")
                print(f"   Paradigme: {len(app['mtp_answers']['reponses_paradigme'])} réponses")
            
            print(f"\n📄 Documents uploadés: {app_json.get('message', 'N/A')}")
            return True
            
        else:
            print(f"\n❌ Erreur ({app_response.status_code}):\n")
            print(app_response.text)
            print(f"\n💡 Vérifiez les logs de l'API pour plus de détails")
            return False

if __name__ == "__main__":
    print("\n💡 Assurez-vous que l'API locale est démarrée:")
    print("   uvicorn app.main:app --reload\n")
    
    result = asyncio.run(main())
    
    print("\n" + "="*80)
    if result:
        print("✅ TEST RÉUSSI - Le système MTP fonctionne localement")
    else:
        print("❌ TEST ÉCHOUÉ - Vérifiez les logs de l'API")
    print("="*80 + "\n")

