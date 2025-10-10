"""
Module de validation centralisé pour l'application SEEG-API.

Ce module fournit des validateurs réutilisables pour différents types de données
et implémente des règles de validation robustes.
"""
import re
import base64
import binascii
import os
from typing import Any, Optional
from datetime import datetime, date
from pydantic import validator, field_validator, BaseModel, EmailStr, Field
from email_validator import validate_email, EmailNotValidError

# Import optionnel de magic pour Windows
magic: Any | None = None
try:
    import magic as _magic
    MAGIC_AVAILABLE = True
    magic = _magic  # assure une référence typée même si l'import échoue
except (ImportError, OSError) as e:
    MAGIC_AVAILABLE = False
    print(f"Warning: python-magic non disponible - Validation MIME désactivée ({e})")

class ValidationError(Exception):
    """Exception personnalisée pour les erreurs de validation."""
    pass

class Validators:
    """Classe de validateurs réutilisables."""

    @staticmethod
    def validate_password(password: str, min_length: int = 12) -> str:
        """
        Validation robuste des mots de passe.
        
        Règles:
        - Longueur minimale configurable
        - Au moins une majuscule
        - Au moins une minuscule
        - Au moins un chiffre
        - Au moins un caractère spécial
        """
        if len(password) < min_length:
            raise ValueError(f"Le mot de passe doit contenir au moins {min_length} caractères")
        
        if not re.search(r'[A-Z]', password):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule")
        
        if not re.search(r'[a-z]', password):
            raise ValueError("Le mot de passe doit contenir au moins une minuscule")
        
        if not re.search(r'\d', password):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\'`~]', password):
            raise ValueError("Le mot de passe doit contenir au moins un caractère spécial")
        
        return password

    @staticmethod
    def validate_email(email: str) -> str:
        """
        Validation robuste des emails avec email-validator.
        
        Vérifie la syntaxe et normalise l'email.
        """
        try:
            # Valide et normalise l'email
            # Désactiver la vérification de délivrabilité pour accepter les domaines de test (e.g. example.com)
            valid = validate_email(email, check_deliverability=False)
            return valid.email
        except EmailNotValidError as e:
            # Lever ValueError pour que Pydantic retourne 422 au lieu d'un 500
            raise ValueError(str(e))

    @staticmethod
    def validate_pdf(file_data: str, max_size_mb: int = 10) -> str:
        """
        Validation avancée des fichiers PDF.
        
        Vérifie:
        - Encodage base64 valide
        - Magic number PDF
        - Taille maximale
        - Type MIME
        """
        try:
            # Décoder base64
            decoded = base64.b64decode(file_data)
            
            # Vérifier la taille
            if len(decoded) > max_size_mb * 1024 * 1024:
                raise ValueError(f"Le fichier PDF ne doit pas dépasser {max_size_mb} Mo")
            
            # Vérifier le magic number PDF
            if not decoded.startswith(b'%PDF'):
                raise ValueError("Le fichier n'est pas un PDF valide")
            
            # Vérifier le type MIME avec python-magic (si disponible)
            if MAGIC_AVAILABLE and magic is not None:
                try:
                    mime = magic.from_buffer(decoded, mime=True)
                    if mime != 'application/pdf':
                        raise ValueError("Le type MIME n'est pas un PDF")
                except Exception as e:
                    # Si magic échoue, on continue avec la vérification du magic number uniquement
                    print(f"Warning: Validation MIME échouée, on utilise uniquement le magic number - {e}")
            
            return file_data
        
        except binascii.Error:
            raise ValueError("Données base64 invalides")
        except Exception as e:
            raise ValueError(f"Erreur de validation PDF: {str(e)}")

    @staticmethod
    def validate_date_of_birth(birth_date: date, min_age: int = 18, max_age: int = 100) -> date:
        """
        Validation de la date de naissance.
        
        Vérifie:
        - Âge minimum
        - Âge maximum
        """
        today = datetime.now().date()
        age = (today - birth_date).days / 365.25
        
        if age < min_age:
            raise ValueError(f"Vous devez avoir au moins {min_age} ans")
        
        if age > max_age:
            raise ValueError(f"Date de naissance invalide (âge max: {max_age} ans)")
        
        return birth_date

    @staticmethod
    def sanitize_input(input_str: str) -> str:
        """
        Sanitization de base des entrées utilisateur.
        
        Supprime ou échappe les caractères potentiellement dangereux.
        """
        # Supprimer les caractères de contrôle
        sanitized = re.sub(r'[\x00-\x1F\x7F]', '', input_str)
        
        # Échapper les caractères HTML
        html_escape_table = {
            "&": "&amp;",
            '"': "&quot;",
            "'": "&apos;",
            ">": "&gt;",
            "<": "&lt;",
        }
        return "".join(html_escape_table.get(c, c) for c in sanitized)

# Décorateurs de validation réutilisables
def validate_password_field(min_length: int = 12):
    """Décorateur pour valider un champ de mot de passe."""
    def decorator(v):
        return Validators.validate_password(v, min_length)
    return field_validator('password')(decorator)

def validate_email_field():
    """Décorateur pour valider un champ email."""
    def decorator(v):
        return Validators.validate_email(v)
    return field_validator('email')(decorator)

def validate_pdf_field(max_size_mb: int = 10):
    """Décorateur pour valider un champ de fichier PDF."""
    def decorator(v):
        return Validators.validate_pdf(v, max_size_mb)
    return field_validator('file_data')(decorator)
