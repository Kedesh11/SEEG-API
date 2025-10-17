#!/usr/bin/env python3
"""
Test final de la route POST /applications/ en production
Avec les données EXACTES du frontend
"""
import asyncio
import httpx

BASE_URL = "https://seeg-backend-api.azurewebsites.net/api/v1"
PDF = "JVBERi0xLjQKJeLjz9MKMyAwIG9iago8PC9UeXBlIC9QYWdlCi9QYXJlbnQgMSAwIFIKL01lZGlhQm94IFswIDAgNjEyIDc5Ml0KPj4KZW5kb2JqCjQgMCBvYmoKPDwvVHlwZSAvRm9udAo+PgplbmRvYmoKMSAwIG9iago8PC9UeXBlIC9QYWdlcwovS2lkcyBbMyAwIFJdCi9Db3VudCAxCj4+CmVuZG9iagoyIDAgb2JqCjw8L1R5cGUgL0NhdGFsb2cKL1BhZ2VzIDEgMCBSCj4+CmVuZG9iagp4cmVmCjAgNQowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAxMTYgMDAwMDAgbiAKMDAwMDAwMDE3MyAwMDAwMCBuIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwODcgMDAwMDAgbiAKdHJhaWxlcgo8PC9TaXplIDUKL1Jvb3QgMiAwIFIKPj4Kc3RhcnR4cmVmCjIyMgolJUVPRgo="

async def main():
    async with httpx.AsyncClient(timeout=60.0, base_url=BASE_URL) as client:
        print("\n" + "="*80)
        print("🧪 TEST PRODUCTION - POST /applications/ avec tableaux JSON")
        print("="*80)
        
        # Login admin (qui peut poster pour n'importe quel candidat)
        print("\n[1/2] Connexion admin...")
        login = await client.post("/auth/login", data={
            "username": "sevankedesh11@gmail.com",
            "password": "Sevan@Seeg"
        })
        
        if login.status_code != 200:
            print(f"❌ Login failed: {login.status_code}")
            return False
        
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Admin connecté")
        
        # Soumission avec données EXACTES du frontend
        print("\n[2/2] Soumission candidature...")
        print("\n📋 Données envoyées (format frontend):")
        print(f"   candidate_id: 93da6d05-74de-4ba6-a807-76513186993f")
        print(f"   job_offer_id: dbf17c25-febc-4d9e-a34e-19c6e1017167")
        print(f"   ref_entreprise: '['osivgnosibv','osignosibnof']'")
        print(f"   ref_fullname: '['soignvosidfgvboib','foidgbfnvbodnfovb']'")
        print(f"   mtp_answers: 2 métier, 2 talent, 2 paradigme")
        print(f"   documents: 3 (cv, cover_letter, diplome)")
        
        app_data = {
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
        
        response = await client.post("/applications/", json=app_data, headers=headers)
        
        print(f"\n📊 RÉSULTAT: HTTP {response.status_code}")
        print("="*80)
        
        if response.status_code == 201:
            data = response.json()
            print("\n✅ ✅ ✅ SUCCÈS ! ✅ ✅ ✅\n")
            print(f"Application ID: {data['data']['id']}")
            print(f"Message: {data['message']}")
            print(f"\n🎉 Le parsing des tableaux JSON fonctionne en production !")
            print(f"   ref_entreprise: osivgnosibv, osignosibnof")
            print(f"   ref_fullname: soignvosidfgvboib, foidgbfnvbodnfovb")
            print(f"   ref_mail: owdgioiubgfr@gmail.com, sfdogbdsfnb@gmail.com")
            print(f"   ref_contact: 8465168468468, 6++9+962+95+9")
            return True
            
        elif response.status_code == 400:
            print(f"\n⚠️  Erreur de validation (400):\n")
            print(response.text)
            print(f"\n💡 Causes possibles:")
            print(f"   - Candidature déjà existante")
            print(f"   - Validation MTP échouée")
            print(f"   - Documents invalides")
            return False
            
        elif response.status_code == 500:
            print(f"\n❌ Erreur serveur (500):\n")
            print(response.text)
            print(f"\n💡 Le déploiement n'a peut-être pas encore pris effet.")
            print(f"   Attendez 2-3 minutes et relancez:")
            print(f"   python test_production_candidature.py")
            return False
            
        else:
            print(f"\n❌ Erreur inattendue: {response.status_code}\n")
            print(response.text)
            return False

if __name__ == "__main__":
    result = asyncio.run(main())
    print("\n" + "="*80)
    if result:
        print("✅ TEST RÉUSSI - La route fonctionne correctement")
    else:
        print("❌ TEST ÉCHOUÉ - Vérifiez le déploiement ou les logs Azure")
    print("="*80 + "\n")

