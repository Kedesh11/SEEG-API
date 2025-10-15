#!/usr/bin/env python3
"""
Test isolé du service PDF avec données mockées
"""

import asyncio
import sys
import os

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pdf import ApplicationPDFService

class MockApplication:
    def __init__(self):
        self.id = "test-123"
        self.status = "pending"
        self.created_at = "2025-10-14"
        self.mtp_answers = None
        self.candidate_id = "candidate-123"
        self.job_offer_id = "job-123"
        
        # Mock candidate
        self.candidate = MockUser()
        
        # Mock job_offer
        self.job_offer = MockJobOffer()

class MockUser:
    def __init__(self):
        self.first_name = "Test"
        self.last_name = "User"
        self.email = "test@example.com"
        self.phone = "+24100000000"
        self.date_of_birth = None
        self.candidate_profile = MockProfile()

class MockProfile:
    def __init__(self):
        self.gender = "M"
        self.address = "Libreville"
        self.current_position = "Développeur"
        self.linkedin_profile = "https://linkedin.com/test"
        self.portfolio_url = "https://portfolio.com/test"
        self.education = "Master Informatique"
        self.skills = "N/A"  # Chaîne problématique
        self.years_experience = 5
        self.current_department = "IT"

class MockJobOffer:
    def __init__(self):
        self.title = "Développeur Full Stack"
        self.contract_type = "CDI"
        self.location = "Libreville"
        self.date_limite = "2025-12-31"
        self.recruiter_id = "recruiter-123"

async def test_pdf_isolated():
    """Test isolé du service PDF"""
    print("🔧 Test isolé du service PDF")
    print("=" * 40)
    
    try:
        # Créer l'application mock
        application = MockApplication()
        
        # Tester le service PDF
        pdf_service = ApplicationPDFService()
        print("✅ Service PDF créé")
        
        # Générer le PDF
        print("🔧 Génération PDF...")
        pdf_content = await pdf_service.generate_application_pdf(application)
        print(f"✅ PDF généré avec succès: {len(pdf_content)} octets")
        
        # Sauvegarder le PDF
        with open("test_isolated.pdf", "wb") as f:
            f.write(pdf_content)
        print("✅ PDF sauvegardé: test_isolated.pdf")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_pdf_isolated())
