#!/usr/bin/env python3
"""
Test de validation Pydantic pour ApplicationCreate
"""
import sys
sys.path.insert(0, 'app')

from schemas.application import ApplicationCreate
from uuid import UUID

print("\n" + "="*70)
print("🧪 TEST: Validation Pydantic ApplicationCreate")
print("="*70)

# PDF valide
PDF = "JVBERi0xLjQKJeLjz9MKMyAwIG9iago8PC9UeXBlIC9QYWdlCi9QYXJlbnQgMSAwIFIKL01lZGlhQm94IFswIDAgNjEyIDc5Ml0KPj4KZW5kb2JqCjQgMCBvYmoKPDwvVHlwZSAvRm9udAo+PgplbmRvYmoKMSAwIG9iago8PC9UeXBlIC9QYWdlcwovS2lkcyBbMyAwIFJdCi9Db3VudCAxCj4+CmVuZG9iagoyIDAgb2JqCjw8L1R5cGUgL0NhdGFsb2cKL1BhZ2VzIDEgMCBSCj4+CmVuZG9iagp4cmVmCjAgNQowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAxMTYgMDAwMDAgbiAKMDAwMDAwMDE3MyAwMDAwMCBuIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwODcgMDAwMDAgbiAKdHJhaWxlcgo8PC9TaXplIDUKL1Jvb3QgMiAwIFIKPj4Kc3RhcnR4cmVmCjIyMgolJUVPRgo="

# Données EXACTES du frontend
data = {
    "candidate_id": "93da6d05-74de-4ba6-a807-76513186993f",
    "job_offer_id": "dbf17c25-febc-4d9e-a34e-19c6e1017167",
    "ref_contact": '["8465168468468","6++9+962+95+9"]',
    "ref_entreprise": '["osivgnosibv","osignosibnof"]',
    "ref_fullname": '["soignvosidfgvboib","foidgbfnvbodnfovb"]',
    "ref_mail": '["owdgioiubgfr@gmail.com","sfdogbdsfnb@gmail.com"]',
    "mtp_answers": {
        "reponses_metier": [";penbpdfnb", "pdfobnpdfnb"],
        "reponses_talent": ["oerdfinb", "ergbposdifbn"],
        "reponses_paradigme": ["dpfbmpdfnb", "dspofbnpdfonb"]
    },
    "documents": [
        {"document_type": "cv", "file_name": "cv.pdf", "file_data": PDF},
        {"document_type": "cover_letter", "file_name": "lettre.pdf", "file_data": PDF},
        {"document_type": "diplome", "file_name": "diplome.pdf", "file_data": PDF}
    ]
}

try:
    print("\n📝 Validation des données avec Pydantic...")
    app_create = ApplicationCreate(**data)
    
    print("\n✅ VALIDATION RÉUSSIE !")
    print(f"\n📊 Données après validation:")
    print(f"   candidate_id: {app_create.candidate_id}")
    print(f"   job_offer_id: {app_create.job_offer_id}")
    print(f"   ref_entreprise: {repr(app_create.ref_entreprise)}")
    print(f"   ref_fullname: {repr(app_create.ref_fullname)}")
    print(f"   ref_mail: {repr(app_create.ref_mail)}")
    print(f"   ref_contact: {repr(app_create.ref_contact)}")
    print(f"   documents: {len(app_create.documents)} documents")
    
    print("\n🎉 Le parsing des tableaux JSON fonctionne localement !")
    print(f"   Exemple: tableau JSON → '{app_create.ref_entreprise}'")
    
except Exception as e:
    print(f"\n❌ ERREUR DE VALIDATION PYDANTIC !")
    print(f"   Type: {type(e).__name__}")
    print(f"   Message: {e}")
    import traceback
    traceback.print_exc()
    print("\n💡 C'est ici que se trouve le bug !")

if __name__ == "__main__":
    pass  # Exécution directe du code

