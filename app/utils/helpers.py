"""
Fonctions utilitaires
"""
import re
import json
import random
import string
from datetime import datetime, date
from typing import Optional, Union


def format_date(date_obj: Optional[Union[date, datetime]], format_str: str = "%d/%m/%Y") -> Optional[str]:
    """Formate une date."""
    if date_obj is None:
        return None
    
    if isinstance(date_obj, datetime):
        return date_obj.strftime(format_str)
    elif isinstance(date_obj, date):
        return date_obj.strftime(format_str)
    
    return None


def format_datetime(datetime_obj: Optional[datetime], format_str: str = "%d/%m/%Y %H:%M:%S") -> Optional[str]:
    """Formate un datetime."""
    if datetime_obj is None:
        return None
    
    return datetime_obj.strftime(format_str)


def calculate_age(birth_date: Optional[date], current_date: Optional[date] = None) -> Optional[int]:
    """Calcule l'âge en années."""
    if birth_date is None:
        return None
    
    if current_date is None:
        current_date = date.today()
    
    age = current_date.year - birth_date.year
    if current_date.month < birth_date.month or (current_date.month == birth_date.month and current_date.day < birth_date.day):
        age -= 1
    
    return age


def generate_random_string(length: int = 10) -> str:
    """Génère une chaîne aléatoire."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def slugify(text: str) -> str:
    """Convertit un texte en slug."""
    if not text:
        return ""
    
    # Convertir en minuscules
    text = text.lower()
    
    # Remplacer les caractères spéciaux
    text = re.sub(r'[àáâãäå]', 'a', text)
    text = re.sub(r'[èéêë]', 'e', text)
    text = re.sub(r'[ìíîï]', 'i', text)
    text = re.sub(r'[òóôõö]', 'o', text)
    text = re.sub(r'[ùúûü]', 'u', text)
    text = re.sub(r'[ç]', 'c', text)
    text = re.sub(r'[ñ]', 'n', text)
    
    # Remplacer les caractères non alphanumériques par des tirets
    text = re.sub(r'[^a-z0-9]+', '-', text)
    
    # Supprimer les tirets en début et fin
    text = text.strip('-')
    
    return text


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Tronque un texte."""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length] + suffix


def is_valid_json(json_string: str) -> bool:
    """Vérifie si une chaîne est un JSON valide."""
    if not json_string:
        return False
    
    try:
        json.loads(json_string)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def parse_json_safe(json_string: str) -> Optional[dict]:
    """Parse un JSON de manière sécurisée."""
    if not json_string:
        return None
    
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return None


def clean_phone_number(phone: str) -> str:
    """Nettoie un numéro de téléphone."""
    if not phone:
        return ""
    
    # Supprimer tous les caractères sauf les chiffres et le +
    return re.sub(r'[^\d+]', '', phone)


def format_currency(amount: float, currency: str = "€") -> str:
    """Formate un montant en devise."""
    if amount is None:
        return f"0,00 {currency}"
    
    # Formater avec séparateurs de milliers
    formatted = f"{amount:,.2f}".replace(",", " ").replace(".", ",")
    return f"{formatted} {currency}"


def calculate_percentage(part: Union[int, float], total: Union[int, float]) -> float:
    """Calcule un pourcentage."""
    if total == 0:
        return 0.0
    
    return (part / total) * 100


def get_file_extension(filename: str) -> str:
    """Récupère l'extension d'un fichier."""
    if not filename:
        return ""
    
    parts = filename.split('.')
    if len(parts) > 1:
        return parts[-1].lower()
    
    return ""


def is_image_file(filename: str) -> bool:
    """Vérifie si un fichier est une image."""
    if not filename:
        return False
    
    extension = get_file_extension(filename)
    image_extensions = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'}
    
    return extension in image_extensions


def format_file_size(size_bytes: int) -> str:
    """Formate une taille de fichier."""
    if size_bytes < 0:
        return "0 B"
    
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    # Formater différemment selon l'unité
    if unit_index == 0:  # Bytes
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"
