"""
Tests pour la soumission de candidature avec références au format JSON
Teste spécifiquement le parsing des tableaux JSON dans les champs ref_*
"""
import pytest
from httpx import AsyncClient
from typing import Dict, Any, Callable
import base64


@pytest.fixture
def valid_cv_base64() -> str:
    """Retourne un PDF valide encodé en base64"""
    return "JVBERi0xLjQKJeLjz9MKMyAwIG9iago8PC9UeXBlIC9QYWdlCi9QYXJlbnQgMSAwIFIKL01lZGlhQm94IFswIDAgNjEyIDc5Ml0KPj4KZW5kb2JqCjQgMCBvYmoKPDwvVHlwZSAvRm9udAo+PgplbmRvYmoKMSAwIG9iago8PC9UeXBlIC9QYWdlcwovS2lkcyBbMyAwIFJdCi9Db3VudCAxCj4+CmVuZG9iagoyIDAgb2JqCjw8L1R5cGUgL0NhdGFsb2cKL1BhZ2VzIDEgMCBSCj4+CmVuZG9iagp4cmVmCjAgNQowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAxMTYgMDAwMDAgbiAKMDAwMDAwMDE3MyAwMDAwMCBuIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwODcgMDAwMDAgbiAKdHJhaWxlcgo8PC9TaXplIDUKL1Jvb3QgMiAwIFIKPj4Kc3RhcnR4cmVmCjIyMgolJUVPRgo="


class TestApplicationWithJSONRefs:
    """Tests pour la soumission de candidature avec références JSON"""
    
    @pytest.mark.asyncio
    async def test_create_application_with_json_array_refs_success(
        self,
        http_client: AsyncClient,
        valid_signup_externe: Dict[str, Any],
        authenticated_client_factory: Callable,
        valid_cv_base64: str
    ):
        """
        Scénario: Candidat externe soumet une candidature avec références au format JSON array
        Attendu: 201 Created, les tableaux JSON sont parsés et combinés
        
        Ce test reproduit exactement le format envoyé par le frontend :
        - ref_entreprise: '["entreprise1","entreprise2"]'
        - ref_fullname: '["nom1","nom2"]'
        - etc.
        """
        # 1. Créer un candidat externe
        signup_response = await http_client.post("/auth/signup", json=valid_signup_externe)
        assert signup_response.status_code == 201
        candidate_id = signup_response.json()["id"]
        
        # 2. Authentifier le candidat
        auth_client, user = await authenticated_client_factory(
            valid_signup_externe["email"],
            valid_signup_externe["password"]
        )
        
        # 3. Créer une offre d'emploi (nécessaire pour la candidature)
        admin_client, admin_user = await authenticated_client_factory(
            "sevankedesh11@gmail.com",
            "Sevan@Seeg"
        )
        
        job_offer_data = {
            "title": "Ingénieur DevOps",
            "description": "Poste d'ingénieur DevOps expérimenté",
            "location": "Libreville",
            "contract_type": "CDI",
            "salary_min": 800000,
            "salary_max": 1500000,
            "requirements": ["Docker", "Kubernetes", "CI/CD"],
            "responsibilities": ["Automatisation", "Déploiements"],
            "benefits": ["Mutuelle", "Formation continue"],
            "status": "active",
            "application_deadline": "2025-12-31T23:59:59Z",
            "questions_mtp": {
                "questions_metier": ["Question métier 1", "Question métier 2"],
                "questions_talent": ["Question talent 1"],
                "questions_paradigme": ["Question paradigme 1"]
            }
        }
        
        job_response = await admin_client.post("/jobs/", json=job_offer_data)
        assert job_response.status_code == 201
        job_offer_id = job_response.json()["id"]
        
        # 4. Préparer les données de candidature avec tableaux JSON (comme le frontend)
        application_data = {
            "candidate_id": candidate_id,
            "job_offer_id": job_offer_id,
            # Format EXACT envoyé par le frontend : tableaux JSON stringifiés
            "ref_entreprise": '["Entreprise ABC","Entreprise XYZ"]',
            "ref_fullname": '["Jean Dupont","Marie Martin"]',
            "ref_mail": '["jean.dupont@abc.com","marie.martin@xyz.com"]',
            "ref_contact": '["06 12 34 56 78","07 98 76 54 32"]',
            "mtp_answers": {
                "reponses_metier": ["Réponse métier 1", "Réponse métier 2"],
                "reponses_talent": ["Réponse talent 1"],
                "reponses_paradigme": ["Réponse paradigme 1"]
            },
            "documents": [
                {
                    "document_type": "cv",
                    "file_name": "cv_test.pdf",
                    "file_data": valid_cv_base64
                },
                {
                    "document_type": "cover_letter",
                    "file_name": "lettre_test.pdf",
                    "file_data": valid_cv_base64
                },
                {
                    "document_type": "diplome",
                    "file_name": "diplome_test.pdf",
                    "file_data": valid_cv_base64
                }
            ]
        }
        
        # 5. Soumettre la candidature
        response = await auth_client.post("/applications/", json=application_data)
        
        # 6. Assertions
        print(f"\n📤 Réponse candidature: {response.status_code}")
        if response.status_code != 201:
            print(f"❌ Erreur: {response.text}")
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        response_data = response.json()
        assert response_data["success"] is True
        assert "3 document(s) uploadé(s)" in response_data["message"]
        assert response_data["data"]["candidate_id"] == candidate_id
        assert response_data["data"]["job_offer_id"] == job_offer_id
        
        print(f"✅ Candidature créée avec succès: {response_data['data']['id']}")
        
        await auth_client.aclose()
        await admin_client.aclose()
    
    @pytest.mark.asyncio
    async def test_create_application_with_empty_json_array_refs_success(
        self,
        http_client: AsyncClient,
        valid_signup_externe: Dict[str, Any],
        authenticated_client_factory: Callable,
        valid_cv_base64: str
    ):
        """
        Scénario: Candidat soumet avec tableaux vides "[]" (doit être converti en None)
        Attendu: 201 Created, les tableaux vides sont ignorés
        """
        # 1. Créer et authentifier un candidat
        signup_response = await http_client.post("/auth/signup", json=valid_signup_externe)
        assert signup_response.status_code == 201
        candidate_id = signup_response.json()["id"]
        
        auth_client, user = await authenticated_client_factory(
            valid_signup_externe["email"],
            valid_signup_externe["password"]
        )
        
        # 2. Récupérer une offre existante
        admin_client, admin_user = await authenticated_client_factory(
            "sevankedesh11@gmail.com",
            "Sevan@Seeg"
        )
        
        jobs_response = await admin_client.get("/jobs/")
        assert jobs_response.status_code == 200
        jobs = jobs_response.json()
        
        if not jobs:
            pytest.skip("Aucune offre disponible")
        
        job_offer_id = jobs[0]["id"]
        
        # 3. Soumettre avec tableaux vides (cas où le candidat n'a pas de références)
        application_data = {
            "candidate_id": candidate_id,
            "job_offer_id": job_offer_id,
            "ref_entreprise": "[]",  # Tableau vide
            "ref_fullname": "[]",
            "ref_mail": "[]",
            "ref_contact": "[]",
            "documents": [
                {
                    "document_type": "cv",
                    "file_name": "cv_test.pdf",
                    "file_data": valid_cv_base64
                },
                {
                    "document_type": "cover_letter",
                    "file_name": "lettre_test.pdf",
                    "file_data": valid_cv_base64
                },
                {
                    "document_type": "diplome",
                    "file_name": "diplome_test.pdf",
                    "file_data": valid_cv_base64
                }
            ]
        }
        
        # 4. Vérifier que ça passe sans erreur
        response = await auth_client.post("/applications/", json=application_data)
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        print(f"✅ Candidature avec tableaux vides créée avec succès")
        
        await auth_client.aclose()
        await admin_client.aclose()
    
    @pytest.mark.asyncio
    async def test_create_application_with_mixed_refs_format_success(
        self,
        http_client: AsyncClient,
        valid_signup_externe: Dict[str, Any],
        authenticated_client_factory: Callable,
        valid_cv_base64: str
    ):
        """
        Scénario: Mix de formats (tableau JSON + chaîne simple)
        Attendu: 201 Created, chaque format est géré correctement
        """
        signup_response = await http_client.post("/auth/signup", json=valid_signup_externe)
        assert signup_response.status_code == 201
        candidate_id = signup_response.json()["id"]
        
        auth_client, user = await authenticated_client_factory(
            valid_signup_externe["email"],
            valid_signup_externe["password"]
        )
        
        admin_client, admin_user = await authenticated_client_factory(
            "sevankedesh11@gmail.com",
            "Sevan@Seeg"
        )
        
        jobs_response = await admin_client.get("/jobs/")
        jobs = jobs_response.json()
        
        if not jobs:
            pytest.skip("Aucune offre disponible")
        
        job_offer_id = jobs[0]["id"]
        
        # Mix de formats
        application_data = {
            "candidate_id": candidate_id,
            "job_offer_id": job_offer_id,
            "ref_entreprise": '["Entreprise A","Entreprise B"]',  # Tableau JSON
            "ref_fullname": "Jean Dupont",  # Chaîne simple (ancien format)
            "ref_mail": "jean@example.com",  # Chaîne simple
            "ref_contact": "[]",  # Tableau vide
            "documents": [
                {
                    "document_type": "cv",
                    "file_name": "cv_test.pdf",
                    "file_data": valid_cv_base64
                },
                {
                    "document_type": "cover_letter",
                    "file_name": "lettre_test.pdf",
                    "file_data": valid_cv_base64
                },
                {
                    "document_type": "diplome",
                    "file_name": "diplome_test.pdf",
                    "file_data": valid_cv_base64
                }
            ]
        }
        
        response = await auth_client.post("/applications/", json=application_data)
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        print(f"✅ Candidature avec formats mixtes créée avec succès")
        
        await auth_client.aclose()
        await admin_client.aclose()

