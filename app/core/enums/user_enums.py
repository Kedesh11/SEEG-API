"""
Enums pour l'application One HCM SEEG
"""
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    RECRUITER = "recruiter"
    CANDIDATE = "candidate"
    OBSERVER = "observer"

    @classmethod
    def get_admin_roles(cls):
        return [cls.ADMIN, cls.RECRUITER]

    @classmethod
    def get_public_roles(cls):
        return [cls.CANDIDATE]

class UserGender(str, Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "Autre"

__all__ = ["UserRole", "UserGender"] 