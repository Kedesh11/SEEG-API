"""
Tests unitaires pour la configuration du rate limiting
"""
import pytest
from app.core.rate_limit import limiter, AUTH_LIMITS, SIGNUP_LIMITS, UPLOAD_LIMITS, DEFAULT_LIMITS


def test_rate_limit_constants_defined():
    """Vérifier que toutes les constantes de rate limiting sont définies"""
    assert AUTH_LIMITS is not None
    assert SIGNUP_LIMITS is not None
    assert UPLOAD_LIMITS is not None
    assert DEFAULT_LIMITS is not None


def test_auth_limits_are_strict():
    """Vérifier que les limites d'authentification sont strictes"""
    assert "5/minute" in AUTH_LIMITS or "5/min" in AUTH_LIMITS
    assert "20/hour" in AUTH_LIMITS or "20/h" in AUTH_LIMITS


def test_signup_limits_are_strict():
    """Vérifier que les limites d'inscription sont strictes"""
    assert "3/minute" in SIGNUP_LIMITS or "3/min" in SIGNUP_LIMITS
    assert "10/hour" in SIGNUP_LIMITS or "10/h" in SIGNUP_LIMITS


def test_upload_limits_configured():
    """Vérifier que les limites d'upload sont configurées"""
    assert "10/minute" in UPLOAD_LIMITS or "10/min" in UPLOAD_LIMITS
    assert "50/hour" in UPLOAD_LIMITS or "50/h" in UPLOAD_LIMITS


def test_limiter_instance_exists():
    """Vérifier que l'instance limiter existe"""
    assert limiter is not None
    assert hasattr(limiter, "limit")
    assert callable(limiter.limit)

