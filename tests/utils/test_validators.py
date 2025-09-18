"""
Tests pour les validateurs
"""
import pytest
from app.utils.validators import (
    validate_email,
    validate_password,
    validate_phone,
    validate_uuid,
    validate_date,
    validate_url
)


class TestValidators:
    """Tests pour les fonctions de validation."""

    def test_validate_email_success(self):
        """Test validation d'email avec succès."""
        # Arrange
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "test123@test-domain.com"
        ]
        
        # Act & Assert
        for email in valid_emails:
            assert validate_email(email) is True

    def test_validate_email_invalid(self):
        """Test validation d'email invalide."""
        # Arrange
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test..test@example.com",
            "test@.com",
            ""
        ]
        
        # Act & Assert
        for email in invalid_emails:
            assert validate_email(email) is False

    def test_validate_password_success(self):
        """Test validation de mot de passe avec succès."""
        # Arrange
        valid_passwords = [
            "Password123!",
            "MySecure@Pass1",
            "ComplexP@ssw0rd",
            "Test123$"
        ]
        
        # Act & Assert
        for password in valid_passwords:
            assert validate_password(password) is True

    def test_validate_password_invalid(self):
        """Test validation de mot de passe invalide."""
        # Arrange
        invalid_passwords = [
            "password",  # Pas de majuscule, chiffre, caractère spécial
            "PASSWORD",  # Pas de minuscule, chiffre, caractère spécial
            "Password",  # Pas de chiffre, caractère spécial
            "Password123",  # Pas de caractère spécial
            "Pass1!",  # Trop court
            "",  # Vide
            "a" * 129  # Trop long
        ]
        
        # Act & Assert
        for password in invalid_passwords:
            assert validate_password(password) is False

    def test_validate_phone_success(self):
        """Test validation de numéro de téléphone avec succès."""
        # Arrange
        valid_phones = [
            "+33123456789",
            "0123456789",
            "+24101234567",
            "0033123456789"
        ]
        
        # Act & Assert
        for phone in valid_phones:
            assert validate_phone(phone) is True

    def test_validate_phone_invalid(self):
        """Test validation de numéro de téléphone invalide."""
        # Arrange
        invalid_phones = [
            "123",  # Trop court
            "abc123456789",  # Contient des lettres
            "123-456-789",  # Format non supporté
            "",  # Vide
            "12345678901234567890"  # Trop long
        ]
        
        # Act & Assert
        for phone in invalid_phones:
            assert validate_phone(phone) is False

    def test_validate_uuid_success(self):
        """Test validation d'UUID avec succès."""
        # Arrange
        valid_uuids = [
            "123e4567-e89b-12d3-a456-426614174000",
            "00000000-0000-0000-0000-000000000000",
            "ffffffff-ffff-ffff-ffff-ffffffffffff"
        ]
        
        # Act & Assert
        for uuid_str in valid_uuids:
            assert validate_uuid(uuid_str) is True

    def test_validate_uuid_invalid(self):
        """Test validation d'UUID invalide."""
        # Arrange
        invalid_uuids = [
            "invalid-uuid",
            "123e4567-e89b-12d3-a456",
            "123e4567-e89b-12d3-a456-42661417400g",  # Caractère invalide
            "",
            "not-a-uuid-at-all"
        ]
        
        # Act & Assert
        for uuid_str in invalid_uuids:
            assert validate_uuid(uuid_str) is False

    def test_validate_date_success(self):
        """Test validation de date avec succès."""
        # Arrange
        valid_dates = [
            "2024-01-01",
            "2023-12-31",
            "2000-02-29",  # Année bissextile
            "2024-06-15"
        ]
        
        # Act & Assert
        for date_str in valid_dates:
            assert validate_date(date_str) is True

    def test_validate_date_invalid(self):
        """Test validation de date invalide."""
        # Arrange
        invalid_dates = [
            "2024-13-01",  # Mois invalide
            "2024-02-30",  # Jour invalide pour février
            "2023-02-29",  # 29 février en année non bissextile
            "invalid-date",
            "2024/01/01",  # Format invalide
            "",
            "24-01-01"  # Format invalide
        ]
        
        # Act & Assert
        for date_str in invalid_dates:
            assert validate_date(date_str) is False

    def test_validate_url_success(self):
        """Test validation d'URL avec succès."""
        # Arrange
        valid_urls = [
            "https://example.com",
            "http://example.com",
            "https://www.example.com/path",
            "https://example.com:8080/path?param=value",
            "https://subdomain.example.com"
        ]
        
        # Act & Assert
        for url in valid_urls:
            assert validate_url(url) is True

    def test_validate_url_invalid(self):
        """Test validation d'URL invalide."""
        # Arrange
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # Protocole non supporté
            "example.com",  # Pas de protocole
            "",
            "https://",  # Pas de domaine
            "https://.com"  # Domaine invalide
        ]
        
        # Act & Assert
        for url in invalid_urls:
            assert validate_url(url) is False

    def test_validate_email_edge_cases(self):
        """Test cas limites pour la validation d'email."""
        # Arrange
        edge_cases = [
            ("test@example.com", True),
            ("test@example.co.uk", True),
            ("test+tag@example.com", True),
            ("test.name@example.com", True),
            ("test@sub.example.com", True),
            ("test@example", False),  # Pas de TLD
            ("test@.com", False),  # Pas de domaine
            ("@example.com", False),  # Pas de nom d'utilisateur
            ("test@example..com", False),  # Points consécutifs
        ]
        
        # Act & Assert
        for email, expected in edge_cases:
            assert validate_email(email) == expected

    def test_validate_password_edge_cases(self):
        """Test cas limites pour la validation de mot de passe."""
        # Arrange
        edge_cases = [
            ("Password123!", True),
            ("P@ssw0rd", True),  # Minimum requis
            ("Password123", False),  # Pas de caractère spécial
            ("password123!", False),  # Pas de majuscule
            ("PASSWORD123!", False),  # Pas de minuscule
            ("Password!", False),  # Pas de chiffre
            ("Pass1!", False),  # Trop court (6 caractères)
            ("a" * 128 + "!", False),  # Trop long
        ]
        
        # Act & Assert
        for password, expected in edge_cases:
            assert validate_password(password) == expected
