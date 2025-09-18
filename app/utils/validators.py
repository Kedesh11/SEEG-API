"""
Fonctions de validation
"""
import re
import uuid
from datetime import datetime
from urllib.parse import urlparse


def validate_email(email: str) -> bool:
    """Valide une adresse email."""
    if not email or not isinstance(email, str):
        return False
    
    # Pattern plus strict pour éviter les points consécutifs
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    # Vérifier le pattern de base
    if not re.match(pattern, email):
        return False
    
    # Vérifier qu'il n'y a pas de points consécutifs
    if '..' in email:
        return False
    
    # Vérifier que le domaine ne commence ou ne finit pas par un point
    domain = email.split('@')[1]
    if domain.startswith('.') or domain.endswith('.'):
        return False
    
    return True


def validate_password(password: str) -> bool:
    """Valide un mot de passe (8-128 caractères, majuscule, minuscule, chiffre, caractère spécial)."""
    if not password or not isinstance(password, str):
        return False
    
    if len(password) < 8 or len(password) > 128:
        return False
    
    # Vérifier les critères
    has_upper = bool(re.search(r'[A-Z]', password))
    has_lower = bool(re.search(r'[a-z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
    
    return has_upper and has_lower and has_digit and has_special


def validate_phone(phone: str) -> bool:
    """Valide un numéro de téléphone."""
    if not phone or not isinstance(phone, str):
        return False
    
    # Nettoyer le numéro
    clean_phone = re.sub(r'[^\d+]', '', phone)
    
    # Vérifier les formats acceptés
    patterns = [
        r'^\+\d{10,15}$',  # Format international
        r'^\d{10,15}$',    # Format national
        r'^00\d{10,15}$'   # Format international avec 00
    ]
    
    return any(re.match(pattern, clean_phone) for pattern in patterns)


def validate_uuid(uuid_string: str) -> bool:
    """Valide un UUID."""
    if not uuid_string or not isinstance(uuid_string, str):
        return False
    
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False


def validate_date(date_string: str) -> bool:
    """Valide une date au format YYYY-MM-DD."""
    if not date_string or not isinstance(date_string, str):
        return False
    
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def validate_url(url: str) -> bool:
    """Valide une URL."""
    if not url or not isinstance(url, str):
        return False
    
    try:
        result = urlparse(url)
        # Vérifier que le domaine n'est pas vide et ne contient pas que des points
        if not result.netloc or result.netloc == '.' or result.netloc.startswith('.') or result.netloc.endswith('.'):
            return False
        return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
    except Exception:
        return False
