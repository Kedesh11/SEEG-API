"""
Fixtures pour l'authentification
Fournit des utilisateurs de test avec différents rôles et statuts
"""
import pytest
from datetime import datetime
from typing import Dict, Any


@pytest.fixture
def valid_signup_externe() -> Dict[str, Any]:
    """Données valides pour inscription candidat externe"""
    return {
        "email": f"externe.test.{int(datetime.now().timestamp())}@gmail.com",
        "password": "SecureTest@2025!External",
        "first_name": "Candidat",
        "last_name": "Externe",
        "phone": "+24106223344",
        "date_of_birth": "1992-08-20",
        "sexe": "F",
        "candidate_status": "externe"
    }


@pytest.fixture
def valid_signup_interne_with_seeg_email() -> Dict[str, Any]:
    """Données valides pour inscription candidat interne avec email SEEG"""
    return {
        "email": f"interne.{int(datetime.now().timestamp())}@seeg-gabon.com",
        "password": "SecureTest@2025!Internal",
        "first_name": "Candidat",
        "last_name": "InterneSeeg",
        "phone": "+24106223355",
        "date_of_birth": "1988-03-10",
        "sexe": "M",
        "candidate_status": "interne",
        "matricule": int(datetime.now().timestamp() % 1000000),
        "no_seeg_email": False,
        "adresse": "Libreville, Gabon",
        "poste_actuel": "Ingénieur",
        "annees_experience": 8
    }


@pytest.fixture
def valid_signup_interne_no_seeg_email() -> Dict[str, Any]:
    """Données valides pour inscription candidat interne SANS email SEEG"""
    return {
        "email": f"interne.gmail.{int(datetime.now().timestamp())}@gmail.com",
        "password": "SecureTest@2025!NoSeeg",
        "first_name": "Candidat",
        "last_name": "InterneNoSeeg",
        "phone": "+24106223366",
        "date_of_birth": "1990-05-15",
        "sexe": "M",
        "candidate_status": "interne",
        "matricule": int(datetime.now().timestamp() % 1000000) + 100,
        "no_seeg_email": True,
        "adresse": "Port-Gentil, Gabon",
        "poste_actuel": "Technicien",
        "annees_experience": 5
    }


@pytest.fixture
def invalid_signup_weak_password() -> Dict[str, Any]:
    """Données invalides - mot de passe trop faible"""
    return {
        "email": "test@example.com",
        "password": "weak",  # Trop court
        "first_name": "Test",
        "last_name": "User",
        "phone": "+24106223344",
        "date_of_birth": "1990-05-15",
        "sexe": "M",
        "candidate_status": "externe"
    }


@pytest.fixture
def invalid_signup_missing_matricule() -> Dict[str, Any]:
    """Données invalides - candidat interne sans matricule"""
    return {
        "email": "test@gmail.com",
        "password": "SecureTest@2025!",
        "first_name": "Test",
        "last_name": "NoMatricule",
        "phone": "+24106223344",
        "date_of_birth": "1990-05-15",
        "sexe": "M",
        "candidate_status": "interne",
        "matricule": None,  # Manquant !
        "no_seeg_email": True
    }


@pytest.fixture
def admin_credentials() -> Dict[str, str]:
    """Credentials pour l'administrateur existant en production"""
    return {
        "email": "sevankedesh11@gmail.com",
        "password": "Sevan@Seeg"
    }

