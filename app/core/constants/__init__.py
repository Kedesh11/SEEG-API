"""
Module des constantes de l'application.
"""
from app.core.constants.mtp_limits import (
    MTPLimits,
    MTP_LIMITS_INTERNAL,
    MTP_LIMITS_EXTERNAL,
    MTP_LIMITS_BY_TYPE,
    get_mtp_limits,
    get_candidate_type_label,
    format_mtp_validation_message
)

__all__ = [
    "MTPLimits",
    "MTP_LIMITS_INTERNAL",
    "MTP_LIMITS_EXTERNAL",
    "MTP_LIMITS_BY_TYPE",
    "get_mtp_limits",
    "get_candidate_type_label",
    "format_mtp_validation_message"
]

