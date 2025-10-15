"""
Service de génération de PDF pour les candidatures
"""
import io
import os
import json
from datetime import datetime
from typing import Optional, Any, Dict, List
from pathlib import Path
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfgen import canvas
import structlog

from app.models.application import Application
from app.utils.json_utils import JSONDataHandler

logger = structlog.get_logger(__name__)


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
        self._setup_styles()
    
    def _safe_json_parse(self, json_string: Any) -> List[Dict]:
        """
        Parse en toute sécurité une chaîne JSON en liste de dictionnaires
        
        Args:
            json_string: Chaîne JSON ou objet déjà parsé
            
        Returns:
            Liste de dictionnaires ou liste vide
        """
        return JSONDataHandler.safe_get_dict_list(json_string)
        
    def _setup_styles(self):
        """Configurer les styles personnalisés"""
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
        application: Any,
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
        logger.info("🚀 Début génération PDF", application_id=getattr(application, 'id', 'N/A'))
        
        # Log des données d'entrée pour diagnostic
        logger.debug("🔍 Données d'entrée PDF", 
                    mtp_answers_type=type(getattr(application, 'mtp_answers', None)).__name__,
                    candidate_id=str(getattr(application, 'candidate_id', 'N/A')),
                    job_offer_id=str(getattr(application, 'job_offer_id', 'N/A')))
        
        try:
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
            
            logger.info("📝 Construction des sections PDF")
            
            # 1. En-tête
            logger.info("🔧 Construction en-tête")
            story.extend(self._build_header(application))
            
            # 2. Informations personnelles
            logger.info("🔧 Construction infos personnelles")
            try:
                story.extend(self._build_personal_info(application))
                logger.debug("✅ Infos personnelles construites avec succès")
            except Exception as e:
                logger.error("❌ Erreur construction infos personnelles", error=str(e))
                raise
            
            # 3. Détails du poste
            logger.info("🔧 Construction détails poste")
            story.extend(self._build_job_details(application))
            
            # 4. Parcours professionnel
            logger.info("🔧 Construction expérience professionnelle")
            story.extend(self._build_professional_experience(application))
            
            # 5. Formation
            logger.info("🔧 Construction formation")
            story.extend(self._build_education(application))
            
            # 6. Compétences
            logger.info("🔧 Construction compétences")
            try:
                story.extend(self._build_skills(application))
                logger.debug("✅ Compétences construites avec succès")
            except Exception as e:
                logger.error("❌ Erreur construction compétences", error=str(e))
                raise
            
            # 7. Réponses MTP
            logger.info("🔧 Construction réponses MTP")
            try:
                story.extend(self._build_mtp_answers(application))
                logger.debug("✅ Réponses MTP construites avec succès")
            except Exception as e:
                logger.error("❌ Erreur construction réponses MTP", error=str(e))
                raise
            
            # 8. Motivation & Disponibilité
            logger.info("🔧 Construction motivation")
            story.extend(self._build_motivation(application))
            
            # 9. Documents joints
            logger.info("🔧 Construction documents joints")
            story.extend(self._build_documents_list(application))
            
            # 10. Entretien (si programmé)
            logger.info("🔧 Construction infos entretien")
            story.extend(self._build_interview_info(application))
            
            # 11. Pied de page
            logger.info("🔧 Construction pied de page")
            story.extend(self._build_footer(application))
        
            # Générer le PDF
            logger.info("📄 Génération finale du PDF")
            doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)

            # Récupérer le contenu
            generated_pdf_bytes = buffer.getvalue()
            buffer.close()

            logger.info("✅ PDF généré avec succès", size_bytes=len(generated_pdf_bytes))
            return generated_pdf_bytes
            
        except Exception as e:
            logger.error("❌ Erreur lors de la génération PDF", error=str(e), error_type=type(e).__name__)
            raise
    
    def _build_header(self, application: Any) -> list:
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
    
    def _build_personal_info(self, application: Any) -> list:
        """Construire la section informations personnelles"""
        elements = []
        
        elements.append(Paragraph("INFORMATIONS PERSONNELLES", self.styles['SectionTitle']))
        elements.append(Spacer(1, 0.3*cm))
        
        user = getattr(application, 'candidate', None)
        profile = getattr(user, 'candidate_profile', None)
        
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
    
    def _build_job_details(self, application: Any) -> list:
        """Construire la section détails du poste"""
        elements = []
        
        elements.append(Paragraph("POSTE VISÉ", self.styles['SectionTitle']))
        elements.append(Spacer(1, 0.3*cm))
        
        job_offer = getattr(application, 'job_offer', None)
        
        if job_offer:
            data = [
                ["Titre du poste", job_offer.title or 'N/A'],
                ["Type de contrat", job_offer.contract_type or 'N/A'],
                ["Localisation", job_offer.location or 'N/A'],
            ]
            
            if hasattr(job_offer, 'date_limite') and job_offer.date_limite:
                data.append(["Date limite de dépôt", job_offer.date_limite.strftime("%d/%m/%Y") if hasattr(job_offer.date_limite, 'strftime') else str(job_offer.date_limite)])
            
            created_at = getattr(application, 'created_at', None)
            created_at_text = str(created_at)
            if created_at is not None and hasattr(created_at, 'strftime'):
                try:
                    created_at_text = created_at.strftime("%d/%m/%Y")  # type: ignore[call-arg]
                except Exception:
                    created_at_text = str(created_at)
            data.append(["Date de candidature", created_at_text])
            status_value = getattr(application, 'status', None)
            status_text = self.STATUS_LABELS.get(status_value, status_value) if status_value is not None else 'N/A'
            data.append(["Statut actuel", str(status_text)])
            
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
    
    def _build_professional_experience(self, application: Any) -> list:
        """Construire la section expérience professionnelle"""
        elements = []
        
        elements.append(Paragraph("EXPÉRIENCE PROFESSIONNELLE", self.styles['SectionTitle']))
        elements.append(Spacer(1, 0.3*cm))
        
        user = getattr(application, 'candidate', None)
        profile = getattr(user, 'candidate_profile', None)
        
        # Affichage des années d'expérience
        years_exp = getattr(profile, 'years_experience', None) if profile else None
        if years_exp:
            elements.append(Paragraph(f"<b>Années d'expérience:</b> {years_exp} ans", self.styles['Normal']))
            elements.append(Spacer(1, 0.3*cm))
        
        # Affichage du poste actuel
        current_pos = getattr(profile, 'current_position', None) if profile else None
        if current_pos:
            elements.append(Paragraph(f"<b>Poste actuel:</b> {current_pos}", self.styles['Normal']))
            elements.append(Spacer(1, 0.3*cm))
        
        # Affichage du département actuel
        current_dept = getattr(profile, 'current_department', None) if profile else None
        if current_dept:
            elements.append(Paragraph(f"<b>Département actuel:</b> {current_dept}", self.styles['Normal']))
            elements.append(Spacer(1, 0.3*cm))
        
        if not any([years_exp, current_pos, current_dept]):
            elements.append(Paragraph("Aucune expérience professionnelle renseignée", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.8*cm))
        
        return elements
    
    def _build_education(self, application: Any) -> list:
        """Construire la section formation"""
        elements = []
        
        elements.append(Paragraph("FORMATION & ÉDUCATION", self.styles['SectionTitle']))
        elements.append(Spacer(1, 0.3*cm))
        
        user = getattr(application, 'candidate', None)
        profile = getattr(user, 'candidate_profile', None)
        
        if profile and hasattr(profile, 'education'):
            education_text = getattr(profile, 'education', None)
            if education_text:
                elements.append(Paragraph(f"<b>Formation:</b> {education_text}", self.styles['Normal']))
                elements.append(Spacer(1, 0.3*cm))
            else:
                elements.append(Paragraph("Aucune formation renseignée", self.styles['Normal']))
        else:
            elements.append(Paragraph("Aucune formation renseignée", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.8*cm))
        
        return elements
    
    def _build_skills(self, application: Any) -> list:
        """Construire la section compétences"""
        elements = []
        
        elements.append(Paragraph("COMPÉTENCES", self.styles['SectionTitle']))
        elements.append(Spacer(1, 0.3*cm))
        
        user = getattr(application, 'candidate', None)
        profile = getattr(user, 'candidate_profile', None)
        
        if profile and hasattr(profile, 'skills'):
            logger.debug("🔍 Traitement des compétences", profile_id=getattr(profile, 'id', 'N/A'))
            skills_raw = getattr(profile, 'skills', None)
            skills = JSONDataHandler.safe_get_dict_list(skills_raw)
            logger.debug("🔍 Skills parsées", skills_count=len(skills))
            
            if skills:
                skill_data = []
                for i, skill in enumerate(skills):
                    try:
                        name = JSONDataHandler.safe_get_dict_value(skill, 'name', 'N/A')
                        level = JSONDataHandler.safe_get_dict_value(skill, 'level', 0)
                        
                        # Validation et conversion sécurisée du niveau
                        if not isinstance(level, (int, float)):
                            level = 0
                        level = max(0, min(100, int(level)))  # Clamp entre 0 et 100
                        
                        # Barre de progression (10 carrés)
                        progress_bar = '█' * int(level / 10) + '░' * (10 - int(level / 10))
                        skill_data.append([f"• {name}", f"{progress_bar} {level}%"])
                        
                    except Exception as e:
                        logger.warning("⚠️ Erreur traitement skill", index=i, error=str(e))
                        continue
                
                if skill_data:
                    try:
                        table = Table(skill_data, colWidths=[8*cm, 9*cm])
                        table.setStyle(TableStyle([
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('TOPPADDING', (0, 0), (-1, -1), 3),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                        ]))
                        
                        elements.append(table)
                    except Exception as e:
                        logger.error("❌ Erreur création tableau compétences", error=str(e))
                        elements.append(Paragraph("Erreur lors de l'affichage des compétences", self.styles['Normal']))
        else:
            elements.append(Paragraph("Aucune compétence renseignée", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.8*cm))
        
        return elements
    
    def _build_mtp_answers(self, application: Any) -> list:
        """Construire la section réponses MTP"""
        elements = []
        
        elements.append(Paragraph("PROFIL MTP (Métier, Talent, Paradigme)", self.styles['SectionTitle']))
        elements.append(Spacer(1, 0.3*cm))
        
        try:
            mtp_raw = getattr(application, 'mtp_answers', None)
            logger.debug("🔍 Traitement réponses MTP", mtp_type=type(mtp_raw).__name__)
            
            mtp_dict = JSONDataHandler.safe_parse_json(mtp_raw, {})
            
            if mtp_dict and isinstance(mtp_dict, dict):
                # Métier
                metier_responses = JSONDataHandler.safe_get_list(mtp_dict.get('metier'), [])
                if metier_responses:
                    elements.append(Paragraph("<b>MÉTIER (Choix prioritaires)</b>", self.styles['Normal']))
                    for i, metier in enumerate(metier_responses[:3], 1):
                        elements.append(Paragraph(f"{i}. {str(metier)}", self.styles['Normal']))
                    elements.append(Spacer(1, 0.3*cm))
                
                # Talent
                talent_responses = JSONDataHandler.safe_get_list(mtp_dict.get('talent'), [])
                if talent_responses:
                    elements.append(Paragraph("<b>TALENT (Atouts principaux)</b>", self.styles['Normal']))
                    for i, talent in enumerate(talent_responses[:3], 1):
                        elements.append(Paragraph(f"{i}. {str(talent)}", self.styles['Normal']))
                    elements.append(Spacer(1, 0.3*cm))
                
                # Paradigme
                paradigme_responses = JSONDataHandler.safe_get_list(mtp_dict.get('paradigme'), [])
                if paradigme_responses:
                    elements.append(Paragraph("<b>PARADIGME (Valeurs & approches)</b>", self.styles['Normal']))
                    for i, paradigme in enumerate(paradigme_responses[:3], 1):
                        elements.append(Paragraph(f"{i}. {str(paradigme)}", self.styles['Normal']))
                    elements.append(Spacer(1, 0.3*cm))
            else:
                logger.debug("🔍 Aucune réponse MTP valide trouvée")
                
        except Exception as e:
            logger.error("❌ Erreur traitement réponses MTP", error=str(e))
            elements.append(Paragraph("Erreur lors de l'affichage des réponses MTP", self.styles['Normal']))
        else:
            elements.append(Paragraph("Aucune réponse MTP renseignée", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.8*cm))
        
        return elements
    
    def _build_motivation(self, application: Any) -> list:
        """Construire la section motivation et disponibilité"""
        elements = []
        
        elements.append(Paragraph("LETTRE DE MOTIVATION", self.styles['SectionTitle']))
        elements.append(Spacer(1, 0.3*cm))
        
        motivation_text = getattr(application, 'cover_letter', None) or getattr(application, 'motivation', None)
        if motivation_text:
            elements.append(Paragraph(motivation_text, self.styles['Normal']))
        else:
            elements.append(Paragraph("Aucune lettre de motivation fournie", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.5*cm))
        
        # Disponibilité et références
        info_data = []
        availability_start = getattr(application, 'availability_start', None)
        if availability_start:
            info_data.append(["Disponibilité", availability_start.strftime("%d/%m/%Y") if hasattr(availability_start, 'strftime') else str(availability_start)])
        reference_contacts = getattr(application, 'reference_contacts', None)
        if reference_contacts:
            info_data.append(["Références", reference_contacts])
        
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
    
    def _build_documents_list(self, application: Any) -> list:
        """Construire la liste des documents joints"""
        elements = []
        
        elements.append(Paragraph("DOCUMENTS JOINTS", self.styles['SectionTitle']))
        elements.append(Spacer(1, 0.3*cm))
        
        # Cette section liste les documents mais ne les inclut pas
        # TODO: Implémenter la récupération de la liste des documents depuis la DB
        elements.append(Paragraph("Liste des documents disponibles dans le système", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.8*cm))
        
        return elements
    
    def _build_interview_info(self, application: Any) -> list:
        """Construire la section entretien (si programmé)"""
        elements = []
        
        interview_date = getattr(application, 'interview_date', None)
        if getattr(application, 'status', None) == 'entretien_programme' and interview_date:
            elements.append(Paragraph("ENTRETIEN PROGRAMMÉ", self.styles['SectionTitle']))
            elements.append(Spacer(1, 0.3*cm))
            
            interview_data = [
                ["📅 Date & Heure", interview_date.strftime("%d/%m/%Y à %H:%M") if hasattr(interview_date, 'strftime') else str(interview_date)],
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
    
    def _build_footer(self, application: Any) -> list:
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
    def get_filename(application: Any) -> str:
        """
        Générer un nom de fichier pour le PDF
        
        Args:
            application: Application
        
        Returns:
            str: Nom de fichier formaté
        """
        user = getattr(application, 'candidate', None)
        job_offer = getattr(application, 'job_offer', None)
        
        parts = ["Candidature"]
        
        if user:
            last_name = getattr(user, 'last_name', None)
            first_name = getattr(user, 'first_name', None)
            if last_name:
                parts.append(str(last_name).replace(' ', '_'))
            if first_name:
                parts.append(str(first_name).replace(' ', '_'))
        
        if job_offer:
            title = getattr(job_offer, 'title', None)
            if title:
                parts.append(str(title).replace(' ', '_'))
        
        return "_".join(parts) + ".pdf"

