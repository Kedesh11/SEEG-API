"""
Test du flux ETL complet - De la création de candidature à l'export Blob Storage
================================================================================
Ce script teste le pipeline ETL automatique déclenché lors de la soumission d'une candidature.

Flux testé:
1. Création d'une candidature via POST /api/v1/applications/
2. Déclenchement automatique du webhook ETL
3. Export vers Azure Blob Storage (Star Schema)
4. Vérification des fichiers exportés
"""
import asyncio
import httpx
import json
import os
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_APPLICATION_DATA = {
    "candidate_id": "f249d652-e52d-4b55-948d-c962afd61cf0",  # Candidat existant
    "job_offer_id": "1b0f63c6-db77-4ed7-a424-aa2342a4fc43",  # Offre existante
    "reference_contacts": "Test ETL Flow - Contact automatique",
    "has_been_manager": False,
    "ref_entreprise": "SEEG Test",
    "ref_fullname": "Test ETL Flow",
    "ref_mail": "test.etl@seeg.ga",
    "ref_contact": "+241 01 02 03 04",
    "mtp_answers": {
        "reponses_metier": [
            "Test ETL Flow - Réponse métier 1",
            "Test ETL Flow - Réponse métier 2"
        ],
        "reponses_talent": [
            "Test ETL Flow - Réponse talent 1"
        ],
        "reponses_paradigme": [
            "Test ETL Flow - Réponse paradigme 1"
        ]
    },
    "documents": [
        {
            "document_type": "cv",
            "file_name": "test_etl_cv.pdf",
            "file_data": "JVBERi0xLjQKJeLjz9MKMyAwIG9iago8PC9UeXBlIC9QYWdlCi9QYXJlbnQgMSAwIFIKL01lZGlhQm94IFswIDAgNjEyIDc5Ml0KPj4KZW5kb2JqCjQgMCBvYmoKPDwvVHlwZSAvRm9udAo+PgplbmRvYmoKMSAwIG9iago8PC9UeXBlIC9QYWdlcwovS2lkcyBbMyAwIFJdCi9Db3VudCAxCj4+CmVuZG9iagoyIDAgb2JqCjw8L1R5cGUgL0NhdGFsb2cKL1BhZ2VzIDEgMCBSCj4+CmVuZG9iagp4cmVmCjAgNQowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAxMTYgMDAwMDAgbiAKMDAwMDAwMDE3MyAwMDAwMCBuIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwODcgMDAwMDAgbiAKdHJhaWxlcgo8PC9TaXplIDUKL1Jvb3QgMiAwIFIKPj4Kc3RhcnR4cmVmCjIyMgolJUVPRgo="
        },
        {
            "document_type": "cover_letter",
            "file_name": "test_etl_lettre.pdf",
            "file_data": "JVBERi0xLjQKJeLjz9MKMyAwIG9iago8PC9UeXBlIC9QYWdlCi9QYXJlbnQgMSAwIFIKL01lZGlhQm94IFswIDAgNjEyIDc5Ml0KPj4KZW5kb2JqCjQgMCBvYmoKPDwvVHlwZSAvRm9udAo+PgplbmRvYmoKMSAwIG9iago8PC9UeXBlIC9QYWdlcwovS2lkcyBbMyAwIFJdCi9Db3VudCAxCj4+CmVuZG9iagoyIDAgb2JqCjw8L1R5cGUgL0NhdGFsb2cKL1BhZ2VzIDEgMCBSCj4+CmVuZG9iagp4cmVmCjAgNQowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAxMTYgMDAwMDAgbiAKMDAwMDAwMDE3MyAwMDAwMCBuIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwODcgMDAwMDAgbiAKdHJhaWxlcgo8PC9TaXplIDUKL1Jvb3QgMiAwIFIKPj4Kc3RhcnR4cmVmCjIyMgolJUVPRgo="
        },
        {
            "document_type": "diplome",
            "file_name": "test_etl_diplome.pdf",
            "file_data": "JVBERi0xLjQKJeLjz9MKMyAwIG9iago8PC9UeXBlIC9QYWdlCi9QYXJlbnQgMSAwIFIKL01lZGlhQm94IFswIDAgNjEyIDc5Ml0KPj4KZW5kb2JqCjQgMCBvYmoKPDwvVHlwZSAvRm9udAo+PgplbmRvYmoKMSAwIG9iago8PC9UeXBlIC9QYWdlcwovS2lkcyBbMyAwIFJdCi9Db3VudCAxCj4+CmVuZG9iagoyIDAgb2JqCjw8L1R5cGUgL0NhdGFsb2cKL1BhZ2VzIDEgMCBSCj4+CmVuZG9iagp4cmVmCjAgNQowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAxMTYgMDAwMDAgbiAKMDAwMDAwMDE3MyAwMDAwMCBuIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwODcgMDAwMDAgbiAKdHJhaWxlcgo8PC9TaXplIDUKL1Jvb3QgMiAwIFIKPj4Kc3RhcnR4cmVmCjIyMgolJUVPRgo="
        }
    ]
}

async def test_complete_etl_flow():
    """
    Test du flux ETL complet depuis la création de candidature.
    """
    print("\n" + "="*80)
    print("🧪 TEST FLUX ETL COMPLET - Création → Export Blob Storage")
    print("="*80)
    
    # Vérifier les prérequis
    print("\n📋 Vérification des prérequis...")
    
    # 1. Vérifier que l'API est démarrée
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/health")
            if response.status_code == 200:
                print("✅ API démarrée et accessible")
            else:
                print(f"❌ API non accessible: {response.status_code}")
                return
    except Exception as e:
        print(f"❌ Erreur connexion API: {e}")
        return
    
    # 2. Vérifier les variables d'environnement ETL
    if not os.environ.get("AZURE_STORAGE_CONNECTION_STRING"):
        print("❌ AZURE_STORAGE_CONNECTION_STRING non définie")
        print("   Chargez la config ETL: .\\load_etl_env.ps1")
        return
    else:
        print("✅ Configuration ETL chargée")
    
    print("\n🚀 Démarrage du test...")
    
    # Étape 1: Créer une candidature (déclenche automatiquement l'ETL)
    print("\n" + "-"*60)
    print("📝 ÉTAPE 1: Création de candidature")
    print("-"*60)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Note: En production, il faudrait un token d'authentification
            # Pour le test, on utilise l'endpoint de test ou on mock l'auth
            response = await client.post(
                f"{API_BASE_URL}/api/v1/applications/",
                json=TEST_APPLICATION_DATA,
                headers={
                    "Content-Type": "application/json",
                    # "Authorization": "Bearer YOUR_TOKEN"  # En production
                }
            )
            
            if response.status_code == 201:
                result = response.json()
                application_id = result["data"]["id"]
                print(f"✅ Candidature créée avec succès")
                print(f"   ID: {application_id}")
                print(f"   Message: {result['message']}")
                
                # Attendre un peu pour que l'ETL se déclenche
                print("\n⏳ Attente du déclenchement ETL (5 secondes)...")
                await asyncio.sleep(5)
                
                # Étape 2: Vérifier que l'ETL a été déclenché
                print("\n" + "-"*60)
                print("🔄 ÉTAPE 2: Vérification du déclenchement ETL")
                print("-"*60)
                
                # Vérifier les logs ou appeler directement le webhook pour tester
                webhook_response = await client.post(
                    f"{API_BASE_URL}/api/v1/webhooks/application-submitted",
                    json={
                        "application_id": application_id,
                        "last_watermark": None
                    },
                    headers={
                        "X-Webhook-Token": os.environ.get("WEBHOOK_SECRET", "test-secret-key")
                    }
                )
                
                if webhook_response.status_code == 202:
                    webhook_result = webhook_response.json()
                    print("✅ Webhook ETL déclenché avec succès")
                    print(f"   Message: {webhook_result['message']}")
                    print(f"   Exporté vers Blob: {webhook_result['data']['exported_to_blob']}")
                    
                    # Étape 3: Vérifier les fichiers dans Blob Storage
                    print("\n" + "-"*60)
                    print("💾 ÉTAPE 3: Vérification Blob Storage")
                    print("-"*60)
                    
                    # Lancer le script de vérification
                    import subprocess
                    result = subprocess.run(
                        ["python", "verify_blob_storage.py"],
                        capture_output=True,
                        text=True,
                        cwd="."
                    )
                    
                    if result.returncode == 0:
                        print("✅ Vérification Blob Storage réussie")
                        print("\n📊 Résumé de l'export:")
                        # Extraire les infos importantes du output
                        output_lines = result.stdout.split('\n')
                        for line in output_lines:
                            if "dim_candidates:" in line or "dim_job_offers:" in line or "fact_applications:" in line or "Documents:" in line:
                                print(f"   {line.strip()}")
                    else:
                        print("❌ Erreur lors de la vérification Blob Storage")
                        print(f"   Erreur: {result.stderr}")
                
                else:
                    print(f"❌ Erreur webhook ETL: {webhook_response.status_code}")
                    print(f"   Réponse: {webhook_response.text}")
            
            else:
                print(f"❌ Erreur création candidature: {response.status_code}")
                print(f"   Réponse: {response.text}")
    
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("🏁 TEST TERMINÉ")
    print("="*80)

if __name__ == "__main__":
    print("💡 Prérequis:")
    print("   1. API locale démarrée: uvicorn app.main:app --reload")
    print("   2. Configuration ETL chargée: .\\load_etl_env.ps1")
    print("   3. Base de données accessible")
    
    asyncio.run(test_complete_etl_flow())
