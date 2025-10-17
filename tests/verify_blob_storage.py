"""
Script de vérification du contenu Azure Blob Storage
Vérifie que les exports ETL sont bien enregistrés
"""
import os
from azure.storage.blob import BlobServiceClient
from datetime import datetime, timezone
import json

def verify_blob_storage():
    """
    Vérifie le contenu du Blob Storage après l'export ETL.
    """
    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "").strip()
    
    if not connection_string:
        print("❌ AZURE_STORAGE_CONNECTION_STRING non définie")
        print("   Définissez-la avec: $env:AZURE_STORAGE_CONNECTION_STRING='...'")
        return
    
    print("\n" + "="*80)
    print("🔍 VÉRIFICATION BLOB STORAGE AZURE")
    print("="*80)
    
    try:
        # Connexion au Blob Storage
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_name = "raw"
        container_client = blob_service_client.get_container_client(container_name)
        
        print(f"\n📦 Container: {container_name}")
        print(f"🔗 Connexion établie avec succès")
        
        # Récupérer la date d'aujourd'hui
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Structures pour organiser les résultats
        dimensions_candidates = []
        dimensions_job_offers = []
        facts_applications = []
        documents = []
        other_files = []
        
        print(f"\n📅 Recherche des fichiers pour la date: {today}")
        print("\n" + "-"*80)
        
        # Lister tous les blobs
        blob_list = container_client.list_blobs()
        total_size = 0
        total_count = 0
        
        for blob in blob_list:
            total_count += 1
            total_size += blob.size
            
            # Catégoriser les blobs
            if f"dimensions/dim_candidates/ingestion_date={today}" in blob.name:
                dimensions_candidates.append({
                    "name": blob.name,
                    "size": blob.size,
                    "created": blob.creation_time
                })
            elif f"dimensions/dim_job_offers/ingestion_date={today}" in blob.name:
                dimensions_job_offers.append({
                    "name": blob.name,
                    "size": blob.size,
                    "created": blob.creation_time
                })
            elif f"facts/fact_applications/ingestion_date={today}" in blob.name:
                facts_applications.append({
                    "name": blob.name,
                    "size": blob.size,
                    "created": blob.creation_time
                })
            elif f"documents/ingestion_date={today}" in blob.name:
                documents.append({
                    "name": blob.name,
                    "size": blob.size,
                    "created": blob.creation_time
                })
            else:
                other_files.append({
                    "name": blob.name,
                    "size": blob.size,
                    "created": blob.creation_time
                })
        
        # Afficher les résultats
        print(f"\n📊 STATISTIQUES GLOBALES:")
        print(f"   Total fichiers: {total_count}")
        print(f"   Taille totale: {total_size / (1024*1024):.2f} MB")
        
        print(f"\n📊 FICHIERS DU JOUR ({today}):")
        print(f"\n   🗂️  DIMENSIONS:")
        print(f"      • dim_candidates: {len(dimensions_candidates)} fichier(s)")
        for item in dimensions_candidates:
            print(f"        - {item['name']}")
            print(f"          Taille: {item['size'] / 1024:.2f} KB | Créé: {item['created']}")
        
        print(f"\n      • dim_job_offers: {len(dimensions_job_offers)} fichier(s)")
        for item in dimensions_job_offers:
            print(f"        - {item['name']}")
            print(f"          Taille: {item['size'] / 1024:.2f} KB | Créé: {item['created']}")
        
        print(f"\n   📈 FACTS:")
        print(f"      • fact_applications: {len(facts_applications)} fichier(s)")
        for item in facts_applications:
            print(f"        - {item['name']}")
            print(f"          Taille: {item['size'] / 1024:.2f} KB | Créé: {item['created']}")
        
        print(f"\n   📄 DOCUMENTS (PDFs):")
        print(f"      • {len(documents)} document(s)")
        for item in documents[:5]:  # Afficher max 5 documents
            print(f"        - {item['name']}")
            print(f"          Taille: {item['size'] / 1024:.2f} KB | Créé: {item['created']}")
        
        if len(documents) > 5:
            print(f"        ... et {len(documents) - 5} autres documents")
        
        if other_files:
            print(f"\n   📁 AUTRES FICHIERS: {len(other_files)}")
        
        # Vérifier le contenu d'un fichier dimension (exemple)
        if dimensions_candidates:
            print(f"\n" + "-"*80)
            print(f"📄 APERÇU DU CONTENU (dim_candidate):")
            print("-"*80)
            
            blob_client = container_client.get_blob_client(dimensions_candidates[0]["name"])
            content = blob_client.download_blob().readall()
            data = json.loads(content)
            
            print(json.dumps(data, indent=2, ensure_ascii=False)[:1000] + "...")
        
        # Vérifier le contenu d'une fact (exemple)
        if facts_applications:
            print(f"\n" + "-"*80)
            print(f"📄 APERÇU DU CONTENU (fact_application):")
            print("-"*80)
            
            blob_client = container_client.get_blob_client(facts_applications[0]["name"])
            content = blob_client.download_blob().readall()
            data = json.loads(content)
            
            print(json.dumps(data, indent=2, ensure_ascii=False)[:1000] + "...")
        
        # Résumé final
        print(f"\n" + "="*80)
        print("✅ VÉRIFICATION TERMINÉE")
        print("="*80)
        
        if dimensions_candidates and dimensions_job_offers and facts_applications:
            print("\n🎉 Architecture Star Schema confirmée:")
            print(f"   ✅ Dimensions candidates: {len(dimensions_candidates)}")
            print(f"   ✅ Dimensions job offers: {len(dimensions_job_offers)}")
            print(f"   ✅ Facts applications: {len(facts_applications)}")
            print(f"   ✅ Documents PDF: {len(documents)}")
            print("\n💾 Tous les fichiers sont bien enregistrés dans Azure Blob Storage!")
        else:
            print("\n⚠️  Attention: Certaines tables Star Schema sont manquantes")
            if not dimensions_candidates:
                print("   ❌ Aucune dimension candidate trouvée")
            if not dimensions_job_offers:
                print("   ❌ Aucune dimension job offer trouvée")
            if not facts_applications:
                print("   ❌ Aucune fact application trouvée")
        
    except Exception as e:
        print(f"\n❌ ERREUR lors de la vérification:")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_blob_storage()

