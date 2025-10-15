#!/usr/bin/env python3
"""
Test direct du service PDF pour isoler le problème
"""

import asyncio
import sys
import os

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pdf import ApplicationPDFService

async def test_pdf_direct():
    """Test direct du service PDF"""
    print("🔧 Test direct du service PDF")
    print("=" * 40)
    
    try:
        # Créer une application factice pour le test
        class MockApplication:
            def __init__(self):
                self.id = "test-123"
                self.status = "pending"
                self.created_at = "2025-10-14"
                self.mtp_answers = None
                
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
                self.skills = None
                self.years_experience = 5
                self.current_department = "IT"
        
        class MockJobOffer:
            def __init__(self):
                self.title = "Développeur Full Stack"
                self.contract_type = "CDI"
                self.location = "Libreville"
                self.date_limite = "2025-12-31"
                self.recruiter_id = "recruiter-123"
        
        # Créer l'application mock
        application = MockApplication()
        
        # Tester le service PDF
        pdf_service = ApplicationPDFService()
        print("✅ Service PDF créé")
        
        # Générer le PDF
        pdf_content = await pdf_service.generate_application_pdf(application)
        print(f"✅ PDF généré avec succès: {len(pdf_content)} octets")
        
        # Sauvegarder le PDF
        with open("test_direct.pdf", "wb") as f:
            f.write(pdf_content)
        print("✅ PDF sauvegardé: test_direct.pdf")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_pdf_direct())
