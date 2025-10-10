"""
Constantes pour les limites des questions MTP (Métier, Talent, Paradigme)
selon le type de candidat (interne ou externe).
"""
from typing import Dict, NamedTuple


class MTPLimits(NamedTuple):
    """Structure pour les limites de questions MTP."""
    metier: int
    talent: int
    paradigme: int
    
    @property
    def total(self) -> int:
        """Retourne le nombre total de questions autorisées."""
        return self.metier + self.talent + self.paradigme
    
    def __str__(self) -> str:
        """Représentation textuelle des limites."""
        return f"Métier: {self.metier}, Talent: {self.talent}, Paradigme: {self.paradigme} (Total: {self.total})"


# ============================================================================
# LIMITES MTP PAR TYPE DE CANDIDAT
# ============================================================================

# Limites pour les candidats INTERNES (employés SEEG avec matricule)
MTP_LIMITS_INTERNAL = MTPLimits(
    metier=7,      # 7 questions Métier max
    talent=3,      # 3 questions Talent max
    paradigme=3    # 3 questions Paradigme max
)  # Total: 13 questions

# Limites pour les candidats EXTERNES (sans matricule)
MTP_LIMITS_EXTERNAL = MTPLimits(
    metier=3,      # 3 questions Métier max
    talent=3,      # 3 questions Talent max
    paradigme=3    # 3 questions Paradigme max
)  # Total: 9 questions

# Mapping type de candidat → limites
MTP_LIMITS_BY_TYPE: Dict[str, MTPLimits] = {
    "interne": MTP_LIMITS_INTERNAL,
    "externe": MTP_LIMITS_EXTERNAL
}


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def get_mtp_limits(is_internal_candidate: bool) -> MTPLimits:
    """
    Retourne les limites MTP selon le type de candidat.
    
    Args:
        is_internal_candidate: True si candidat interne, False si externe
        
    Returns:
        MTPLimits: Les limites de questions MTP applicables
        
    Example:
        >>> limits = get_mtp_limits(True)  # Candidat interne
        >>> print(limits.metier)  # 7
        >>> print(limits.total)   # 13
    """
    return MTP_LIMITS_INTERNAL if is_internal_candidate else MTP_LIMITS_EXTERNAL


def get_candidate_type_label(is_internal_candidate: bool) -> str:
    """
    Retourne le label du type de candidat.
    
    Args:
        is_internal_candidate: True si candidat interne, False si externe
        
    Returns:
        str: "interne" ou "externe"
    """
    return "interne" if is_internal_candidate else "externe"


def format_mtp_validation_message(
    is_internal_candidate: bool,
    metier_count: int,
    talent_count: int,
    paradigme_count: int
) -> str:
    """
    Formate un message d'erreur détaillé pour le dépassement des limites MTP.
    
    Args:
        is_internal_candidate: Type de candidat
        metier_count: Nombre de questions Métier fournies
        talent_count: Nombre de questions Talent fournies
        paradigme_count: Nombre de questions Paradigme fournies
        
    Returns:
        str: Message d'erreur formaté
    """
    limits = get_mtp_limits(is_internal_candidate)
    candidate_type = get_candidate_type_label(is_internal_candidate)
    total_provided = metier_count + talent_count + paradigme_count
    
    errors = []
    
    if metier_count > limits.metier:
        errors.append(f"Métier: {metier_count}/{limits.metier}")
    if talent_count > limits.talent:
        errors.append(f"Talent: {talent_count}/{limits.talent}")
    if paradigme_count > limits.paradigme:
        errors.append(f"Paradigme: {paradigme_count}/{limits.paradigme}")
    
    if not errors:
        return f"Nombre total de questions dépassé pour candidat {candidate_type}: {total_provided}/{limits.total}"
    
    error_detail = ", ".join(errors)
    return (
        f"Nombre maximum de questions MTP dépassé pour candidat {candidate_type}. "
        f"Limites: {limits}. "
        f"Reçu: Métier={metier_count}, Talent={talent_count}, Paradigme={paradigme_count} (Total: {total_provided}). "
        f"Dépassements: {error_detail}"
    )

