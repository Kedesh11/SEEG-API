#!/usr/bin/env python3
"""
Test du Webhook ETL vers Blob Storage
Teste l'export temps réel d'une candidature vers Azure Blob Storage
"""
import asyncio
import httpx
import os

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "test-secret-key")

async def test_webhook_etl():
    """Teste le webhook ETL temps réel"""
    
    print("\n" + "="*80)
    print("🧪 TEST WEBHOOK ETL - Export Temps Réel vers Blob Storage")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=60.0, base_url=BASE_URL) as client:
        
        # Utiliser un application_id existant de la base de données locale
        # (trouvé avec check_applications.py)
        application_id = "724f8672-e3a4-4fa1-9856-06ac455bf518"  # Candidature la plus récente
        
        print(f"\n📋 Déclenchement du webhook ETL...")
        print(f"   Application ID: {application_id}")
        print(f"   Webhook Secret: {WEBHOOK_SECRET}")
        
        # Appeler le webhook
        headers = {
            "X-Webhook-Token": WEBHOOK_SECRET,
            "Content-Type": "application/json"
        }
        
        payload = {
            "application_id": application_id,
            "last_watermark": "2025-10-17T00:00:00Z"
        }
        
        response = await client.post(
            "/webhooks/application-submitted",
            json=payload,
            headers=headers
        )
        
        print(f"\n📊 RÉSULTAT: HTTP {response.status_code}")
        print("="*80)
        
        if response.status_code == 202:
            data = response.json()
            print("\n✅ ✅ ✅ SUCCÈS ! ✅ ✅ ✅\n")
            print(f"Message: {data.get('message')}")
            
            export_data = data.get('data', {})
            print(f"\nExported to Blob: {export_data.get('exported_to_blob')}")
            print(f"Application ID: {export_data.get('application_id')}")
            
            # Tables exportées (Star Schema)
            tables = export_data.get('tables_exported', {})
            if tables:
                print("\n📊 TABLES EXPORTÉES (Star Schema):")
                print(f"   - dim_candidates: {tables.get('dim_candidates')}")
                print(f"   - dim_job_offers: {tables.get('dim_job_offers')}")
                print(f"   - fact_applications: {tables.get('fact_applications')}")
            
            print(f"\n📄 Documents: {export_data.get('documents_count')} PDFs")
            print(f"💾 Taille totale: {export_data.get('total_size_mb')} MB")
            print(f"\n🎉 Export ETL Data Warehouse réussi !")
            return True
        elif response.status_code == 401:
            print("\n❌ Non autorisé:")
            print(response.text)
            print("\n💡 Vérifiez que WEBHOOK_SECRET est correctement défini")
            return False
        elif response.status_code == 404:
            print("\n❌ Candidature introuvable:")
            print(response.text)
            print(f"\n💡 L'application_id '{application_id}' n'existe peut-être pas")
            return False
        elif response.status_code == 500:
            print("\n❌ Erreur serveur:")
            print(response.text)
            print("\n💡 Vérifiez les logs de l'API pour plus de détails")
            return False
        else:
            print(f"\n❌ Erreur inattendue: {response.status_code}")
            print(response.text)
            return False

if __name__ == "__main__":
    print("\n💡 Prérequis:")
    print("   1. API locale démarrée: uvicorn app.main:app --reload")
    print("   2. Variable d'environnement:")
    print("      $env:AZURE_STORAGE_CONNECTION_STRING=\"DefaultEndpointsProtocol=...\"")
    print("      $env:WEBHOOK_SECRET=\"test-secret-key\"\n")
    
    result = asyncio.run(test_webhook_etl())
    
    print("\n" + "="*80)
    if result:
        print("✅ TEST RÉUSSI - Webhook ETL fonctionne")
        print("\n💡 Vérifiez dans Azure Storage:")
        print("   Container: raw")
        print("   Dimensions:")
        print("     - dimensions/dim_candidates/ingestion_date=YYYY-MM-DD/{candidate_id}.json")
        print("     - dimensions/dim_job_offers/ingestion_date=YYYY-MM-DD/{job_offer_id}.json")
        print("   Facts:")
        print("     - facts/fact_applications/ingestion_date=YYYY-MM-DD/{application_id}.json")
        print("   Documents:")
        print("     - documents/ingestion_date=YYYY-MM-DD/{application_id}/{doc_type}_{filename}.pdf")
    else:
        print("❌ TEST ÉCHOUÉ - Vérifiez les logs")
    print("="*80 + "\n")

