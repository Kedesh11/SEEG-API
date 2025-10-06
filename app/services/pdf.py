"""
Service de génération de PDF pour les candidatures
"""
import io
from datetime import datetime
from typing import Optional
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfgen import canvas

from app.models.application import Application


class ApplicationPDFService:
    """Service de génération de PDF pour les candidatures"""
    
    # Mapping des statuts en français
    STATUS_LABELS = {
        'candidature': '🔵 Candidature reçue',
        'incubation': '🟡 En évaluation',
        'embauche': '🟢 Candidat retenu',
        'refuse': '🔴 Candidature refusée',
        'entretien_programme': '📅 Entretien programmé'
    }
    
    def __init__(self, page_format: str = 'A4', language: str = 'fr'):
        """
        Initialiser le service PDF
        
        Args:
            page_format: Format de page ('A4' ou 'Letter')
            language: Langue du document ('fr' ou 'en')
        """
        self.page_format = A4 if page_format == 'A4' else LETTER
        self.language = language
        self.styles = getSampleStyleSheet()
        
        # Styles personnalisés
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1a365d'),
            spaceAfter=12,
            borderWidth=1,
            borderColor=colors.HexColor('#cbd5e0'),
            borderPadding=8,
            backColor=colors.HexColor('#f7fafc')
        ))
        
        self.styles.add(ParagraphStyle(
            name='DocumentTitle',
            parent=self.styles['Title'],
            fontSize=18,
            textColor=colors.HexColor('#1a365d'),
            alignment=TA_CENTER,
            spaceAfter=20
        ))
        
        self.styles.add(ParagraphStyle(
            name='FieldLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#4a5568'),
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='FieldValue',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#1a202c')
        ))
    
    async def generate_application_pdf(
        self, 
        application: Application,
        include_documents: bool = False
    ) -> bytes:
        """
        Génère un PDF complet pour une candidature
        
        Args:
            application: Modèle Application avec toutes les relations chargées
            include_documents: Inclure les documents joints (non implémenté dans cette version)
        
        Returns:
            bytes: Contenu binaire du PDF
        """
        # Créer un buffer en mémoire
        buffer = io.BytesIO()
        
        # Créer le document PDF
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.page_format,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
            title=f"Candidature_{application.id}"
        )
        
        # Construire le contenu
        story = []
        
        # 1. En-tête
        story.extend(self._build_header(application))
        
        # 2. Informations personnelles
        story.extend(self._build_personal_info(application))
        
        # 3. Détails du poste
        story.extend(self._build_job_details(application))
        
        # 4. Parcours professionnel
        story.extend(self._build_professional_experience(application))
        
        # 5. Formation
        story.extend(self._build_education(application))
        
        # 6. Compétences
        story.extend(self._build_skills(application))
        
        # 7. Réponses MTP
        story.extend(self._build_mtp_answers(application))
        
        # 8. Motivation & Disponibilité
        story.extend(self._build_motivation(application))
        
        # 9. Documents joints
        story.extend(self._build_documents_list(application))
        
        # 10. Entretien (si programmé)
        story.extend(self._build_interview_info(application))
        
        # 11. Pied de page
        story.extend(self._build_footer(application))
        
        # Générer le PDF
        doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
        
        # Récupérer le contenu
        pdf_content = buffer.getvalue()
        buffer.close()
        
        return pdf_content
    
    def _build_header(self, application: Application) -> list:
        """Construire l'en-tête du document"""
        elements = []
        
        # Titre principal
        elements.append(Paragraph(
            "DOSSIER DE CANDIDATURE",
            self.styles['DocumentTitle']
        ))
        
        # Ligne séparatrice
        elements.append(Spacer(1, 0.5*cm))
        
        # Informations de référence
        ref_data = [
            [Paragraph("<b>Date de génération:</b>", self.styles['FieldLabel']), 
             Paragraph(datetime.now().strftime("%d/%m/%Y à %H:%M"), self.styles['FieldValue'])],
            [Paragraph("<b>Référence candidature:</b>", self.styles['FieldLabel']), 
             Paragraph(str(application.id), self.styles['FieldValue'])]
        ]
        
        ref_table = Table(ref_data, colWidths=[5*cm, 12*cm])
        ref_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        elements.append(ref_table)
        elements.append(Spacer(1, 1*cm))
        
        return elements
    
    def _build_personal_info(self, application: Application) -> list:
        """Construire la section informations personnelles"""
        elements = []
        
        elements.append(Paragraph("INFORMATIONS PERSONNELLES", self.styles['SectionTitle']))
        elements.append(Spacer(1, 0.3*cm))
        
        user = application.users
        profile = user.candidate_profiles if user and hasattr(user, 'candidate_profiles') else None
        
        if user:
            data = [
                ["Nom complet", f"{user.first_name or ''} {user.last_name or ''}"],
                ["Email", user.email or 'N/A'],
                ["Téléphone", user.phone or 'N/A'],
            ]
            
            if user.date_of_birth:
                data.append(["Date de naissance", user.date_of_birth.strftime("%d/%m/%Y") if hasattr(user.date_of_birth, 'strftime') else str(user.date_of_birth)])
            
            if profile:
                if hasattr(profile, 'gender') and profile.gender:
                    data.append(["Genre", profile.gender])
                if hasattr(profile, 'address') and profile.address:
                    data.append(["Adresse", profile.address])
                if hasattr(profile, 'current_position') and profile.current_position:
                    data.append(["Poste actuel", profile.current_position])
                if hasattr(profile, 'linkedin_profile') and profile.linkedin_profile:
                    data.append(["LinkedIn", profile.linkedin_profile])
                if hasattr(profile, 'portfolio_url') and profile.portfolio_url:
                    data.append(["Portfolio", profile.portfolio_url])
            
            table = Table(data, colWidths=[5*cm, 12*cm])
            table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            
            elements.append(table)
        else:
            elements.append(Paragraph("Informations non disponibles", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.8*cm))
        
        return elements
    
    def _build_job_details(self, application: Application) -> list:
        """Construire la section détails du poste"""
        elements = []
        
        elements.append(Paragraph("POSTE VISÉ", self.styles['SectionTitle']))
        elements.append(Spacer(1, 0.3*cm))
        
        job_offer = application.job_offers
        
        if job_offer:
            data = [
                ["Titre du poste", job_offer.title or 'N/A'],
                ["Type de contrat", job_offer.contract_type or 'N/A'],
                ["Localisation", job_offer.location or 'N/A'],
            ]
            
            if hasattr(job_offer, 'date_limite') and job_offer.date_limite:
                data.append(["Date limite de dépôt", job_offer.date_limite.strftime("%d/%m/%Y") if hasattr(job_offer.date_limite, 'strftime') else str(job_offer.date_limite)])
            
            data.append(["Date de candidature", application.created_at.strftime("%d/%m/%Y") if hasattr(application.created_at, 'strftime') else str(application.created_at)])
            data.append(["Statut actuel", self.STATUS_LABELS.get(application.status, application.status)])
            
            table = Table(data, colWidths=[5*cm, 12*cm])
            table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            
            elements.append(table)
        else:
            elements.append(Paragraph("Informations du poste non disponibles", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.8*cm))
        
        return elements
    
    def _build_professional_experience(self, application: Application) -> list:
        """Construire la section expérience professionnelle"""
        elements = []
        
        elements.append(Paragraph("EXPÉRIENCE PROFESSIONNELLE", self.styles['SectionTitle']))
        elements.append(Spacer(1, 0.3*cm))
        
        user = application.users
        profile = user.candidate_profiles if user and hasattr(user, 'candidate_profiles') else None
        
        if profile and hasattr(profile, 'experiences') and profile.experiences:
            for exp in profile.experiences:
                # Titre du poste
                elements.append(Paragraph(f"<b>{exp.get('title', 'N/A')}</b>", self.styles['Normal']))
                
                # Entreprise et localisation
                company_location = f"{exp.get('company', 'N/A')}"
                if exp.get('location'):
                    company_location += f" • {exp['location']}"
                elements.append(Paragraph(company_location, self.styles['Normal']))
                
                # Dates
                start = exp.get('start_date', '')
                end = exp.get('end_date', 'En cours')
                elements.append(Paragraph(f"{start} - {end}", self.styles['Normal']))
                
                # Description
                if exp.get('description'):
                    elements.append(Spacer(1, 0.2*cm))
                    elements.append(Paragraph(exp['description'], self.styles['Normal']))
                
                elements.append(Spacer(1, 0.5*cm))
        else:
            elements.append(Paragraph("Aucune expérience professionnelle renseignée", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.8*cm))
        
        return elements
    
    def _build_education(self, application: Application) -> list:
        """Construire la section formation"""
        elements = []
        
        elements.append(Paragraph("FORMATION & ÉDUCATION", self.styles['SectionTitle']))
        elements.append(Spacer(1, 0.3*cm))
        
        user = application.users
        profile = user.candidate_profiles if user and hasattr(user, 'candidate_profiles') else None
        
        if profile and hasattr(profile, 'educations') and profile.educations:
            for edu in profile.educations:
                # Diplôme et domaine
                degree_field = f"<b>{edu.get('degree', 'N/A')}</b>"
                if edu.get('field_of_study'):
                    degree_field += f" en {edu['field_of_study']}"
                elements.append(Paragraph(degree_field, self.styles['Normal']))
                
                # Institution
                elements.append(Paragraph(edu.get('institution', 'N/A'), self.styles['Normal']))
                
                # Dates
                start = edu.get('start_date', '')
                end = edu.get('end_date', 'En cours')
                elements.append(Paragraph(f"{start} - {end}", self.styles['Normal']))
                
                elements.append(Spacer(1, 0.5*cm))
        else:
            elements.append(Paragraph("Aucune formation renseignée", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.8*cm))
        
        return elements
    
    def _build_skills(self, application: Application) -> list:
        """Construire la section compétences"""
        elements = []
        
        elements.append(Paragraph("COMPÉTENCES", self.styles['SectionTitle']))
        elements.append(Spacer(1, 0.3*cm))
        
        user = application.users
        profile = user.candidate_profiles if user and hasattr(user, 'candidate_profiles') else None
        
        if profile and hasattr(profile, 'skills') and profile.skills:
            skill_data = []
            for skill in profile.skills:
                name = skill.get('name', 'N/A')
                level = skill.get('level', 0)
                
                # Barre de progression (10 carrés)
                progress_bar = '█' * int(level / 10) + '░' * (10 - int(level / 10))
                skill_data.append([f"• {name}", f"{progress_bar} {level}%"])
            
            if skill_data:
                table = Table(skill_data, colWidths=[8*cm, 9*cm])
                table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]))
                
                elements.append(table)
        else:
            elements.append(Paragraph("Aucune compétence renseignée", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.8*cm))
        
        return elements
    
    def _build_mtp_answers(self, application: Application) -> list:
        """Construire la section réponses MTP"""
        elements = []
        
        elements.append(Paragraph("PROFIL MTP (Métier, Talent, Paradigme)", self.styles['SectionTitle']))
        elements.append(Spacer(1, 0.3*cm))
        
        if application.mtp_answers:
            mtp = application.mtp_answers
            
            # Métier
            if mtp.get('metier'):
                elements.append(Paragraph("<b>MÉTIER (Choix prioritaires)</b>", self.styles['Normal']))
                for i, metier in enumerate(mtp['metier'][:3], 1):
                    elements.append(Paragraph(f"{i}. {metier}", self.styles['Normal']))
                elements.append(Spacer(1, 0.3*cm))
            
            # Talent
            if mtp.get('talent'):
                elements.append(Paragraph("<b>TALENT (Atouts principaux)</b>", self.styles['Normal']))
                for i, talent in enumerate(mtp['talent'][:3], 1):
                    elements.append(Paragraph(f"{i}. {talent}", self.styles['Normal']))
                elements.append(Spacer(1, 0.3*cm))
            
            # Paradigme
            if mtp.get('paradigme'):
                elements.append(Paragraph("<b>PARADIGME (Valeurs & approches)</b>", self.styles['Normal']))
                for i, paradigme in enumerate(mtp['paradigme'][:3], 1):
                    elements.append(Paragraph(f"{i}. {paradigme}", self.styles['Normal']))
                elements.append(Spacer(1, 0.3*cm))
        else:
            elements.append(Paragraph("Aucune réponse MTP renseignée", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.8*cm))
        
        return elements
    
    def _build_motivation(self, application: Application) -> list:
        """Construire la section motivation et disponibilité"""
        elements = []
        
        elements.append(Paragraph("LETTRE DE MOTIVATION", self.styles['SectionTitle']))
        elements.append(Spacer(1, 0.3*cm))
        
        motivation_text = application.cover_letter or application.motivation
        if motivation_text:
            elements.append(Paragraph(motivation_text, self.styles['Normal']))
        else:
            elements.append(Paragraph("Aucune lettre de motivation fournie", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.5*cm))
        
        # Disponibilité et références
        info_data = []
        if application.availability_start:
            info_data.append(["Disponibilité", application.availability_start.strftime("%d/%m/%Y") if hasattr(application.availability_start, 'strftime') else str(application.availability_start)])
        if application.reference_contacts:
            info_data.append(["Références", application.reference_contacts])
        
        if info_data:
            table = Table(info_data, colWidths=[5*cm, 12*cm])
            table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            
            elements.append(table)
        
        elements.append(Spacer(1, 0.8*cm))
        
        return elements
    
    def _build_documents_list(self, application: Application) -> list:
        """Construire la liste des documents joints"""
        elements = []
        
        elements.append(Paragraph("DOCUMENTS JOINTS", self.styles['SectionTitle']))
        elements.append(Spacer(1, 0.3*cm))
        
        # Cette section liste les documents mais ne les inclut pas
        # TODO: Implémenter la récupération de la liste des documents depuis la DB
        elements.append(Paragraph("Liste des documents disponibles dans le système", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.8*cm))
        
        return elements
    
    def _build_interview_info(self, application: Application) -> list:
        """Construire la section entretien (si programmé)"""
        elements = []
        
        if application.status == 'entretien_programme' and application.interview_date:
            elements.append(Paragraph("ENTRETIEN PROGRAMMÉ", self.styles['SectionTitle']))
            elements.append(Spacer(1, 0.3*cm))
            
            interview_data = [
                ["📅 Date & Heure", application.interview_date.strftime("%d/%m/%Y à %H:%M") if hasattr(application.interview_date, 'strftime') else str(application.interview_date)],
                ["📍 Lieu", "Libreville (à confirmer)"],
                ["⏰ Durée", "1h00 (estimée)"],
            ]
            
            table = Table(interview_data, colWidths=[5*cm, 12*cm])
            table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 0.3*cm))
            
            # Instructions
            elements.append(Paragraph("<b>Instructions:</b>", self.styles['Normal']))
            elements.append(Paragraph("• Apporter une pièce d'identité", self.styles['Normal']))
            elements.append(Paragraph("• Arriver 10 minutes en avance", self.styles['Normal']))
            elements.append(Paragraph("• Documents originaux requis", self.styles['Normal']))
            
            elements.append(Spacer(1, 0.8*cm))
        
        return elements
    
    def _build_footer(self, application: Application) -> list:
        """Construire le pied de page"""
        elements = []
        
        elements.append(Spacer(1, 1*cm))
        
        footer_text = f"""
        ─────────────────────────────────────────────────────────────<br/>
        Document généré le {datetime.now().strftime("%d/%m/%Y à %H:%M")}<br/>
        Référence candidature : {application.id}<br/>
        <b>SEEG - Société d'Énergie et d'Eau du Gabon</b><br/>
        ─────────────────────────────────────────────────────────────
        """
        
        footer_style = ParagraphStyle(
            'Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        
        elements.append(Paragraph(footer_text, footer_style))
        
        return elements
    
    def _add_page_number(self, canvas, doc):
        """Ajouter le numéro de page"""
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(doc.pagesize[0] - 2*cm, 1*cm, text)
        canvas.restoreState()
    
    @staticmethod
    def get_filename(application: Application) -> str:
        """
        Générer un nom de fichier pour le PDF
        
        Args:
            application: Application
        
        Returns:
            str: Nom de fichier formaté
        """
        user = application.users
        job_offer = application.job_offers
        
        parts = ["Candidature"]
        
        if user:
            if user.last_name:
                parts.append(user.last_name.replace(' ', '_'))
            if user.first_name:
                parts.append(user.first_name.replace(' ', '_'))
        
        if job_offer and job_offer.title:
            parts.append(job_offer.title.replace(' ', '_'))
        
        return "_".join(parts) + ".pdf"

