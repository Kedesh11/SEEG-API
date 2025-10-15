"""
Utilitaires pour la gestion sécurisée des données JSON
"""
import json
import structlog
from typing import Any, Dict, List, Union, Optional

logger = structlog.get_logger(__name__)


class JSONDataHandler:
    """
    Classe utilitaire pour gérer de manière sécurisée les données JSON
    """
    
    @staticmethod
    def safe_parse_json(json_data: Any, default: Optional[Union[Dict, List]] = None) -> Union[Dict, List]:
        """
        Parse en toute sécurité une chaîne JSON ou retourne l'objet tel quel
        
        Args:
            json_data: Données à parser (chaîne JSON, dict, list, ou autre)
            default: Valeur par défaut si le parsing échoue
            
        Returns:
            Données parsées ou valeur par défaut
        """
        if json_data is None:
            logger.debug("🔍 JSON data est None, retour valeur par défaut", default_type=type(default).__name__)
            return default or {}
        
        if isinstance(json_data, (dict, list)):
            logger.debug("🔍 JSON data est déjà parsé", data_type=type(json_data).__name__)
            return json_data
        
        if isinstance(json_data, str):
            # Gérer les cas spéciaux comme "N/A", "null", etc.
            json_data = json_data.strip()
            if json_data.lower() in ['n/a', 'null', 'none', '', 'null']:
                logger.debug("🔍 JSON data est une valeur spéciale", value=json_data)
                return default or {}
            
            logger.debug("🔍 Tentative de parsing JSON string", json_length=len(json_data))
            try:
                parsed = json.loads(json_data)
                logger.debug("🔍 JSON parsé avec succès", parsed_type=type(parsed).__name__)
                return parsed
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("⚠️ Erreur parsing JSON", error=str(e), json_preview=json_data[:100])
                return default or {}
        
        logger.warning("⚠️ Type de données inattendu pour JSON", data_type=type(json_data).__name__)
        return default or {}
    
    @staticmethod
    def safe_get_dict_value(data: Any, key: str, default: Any = None) -> Any:
        """
        Récupère une valeur d'un dictionnaire de manière sécurisée
        
        Args:
            data: Données (dict, str JSON, ou autre)
            key: Clé à récupérer
            default: Valeur par défaut
            
        Returns:
            Valeur ou défaut
        """
        parsed_data = JSONDataHandler.safe_parse_json(data, {})
        
        if isinstance(parsed_data, dict):
            return parsed_data.get(key, default)
        
        logger.warning("⚠️ Données parsées ne sont pas un dict", parsed_type=type(parsed_data).__name__)
        return default
    
    @staticmethod
    def safe_get_list(data: Any, default: Optional[List] = None) -> List:
        """
        Récupère une liste de manière sécurisée
        
        Args:
            data: Données à parser
            default: Liste par défaut
            
        Returns:
            Liste ou liste vide
        """
        parsed_data = JSONDataHandler.safe_parse_json(data, default or [])
        
        if isinstance(parsed_data, list):
            return parsed_data
        elif isinstance(parsed_data, dict):
            # Si c'est un dict, le convertir en liste
            return [parsed_data]
        
        logger.warning("⚠️ Impossible de convertir en liste", parsed_type=type(parsed_data).__name__)
        return default or []
    
    @staticmethod
    def safe_get_dict_list(data: Any, default: Optional[List[Dict]] = None) -> List[Dict]:
        """
        Récupère une liste de dictionnaires de manière sécurisée
        
        Args:
            data: Données à parser
            default: Liste par défaut
            
        Returns:
            Liste de dictionnaires
        """
        parsed_data = JSONDataHandler.safe_parse_json(data, default or [])
        
        if isinstance(parsed_data, list):
            # Filtrer pour ne garder que les dictionnaires
            return [item for item in parsed_data if isinstance(item, dict)]
        elif isinstance(parsed_data, dict):
            return [parsed_data]
        
        logger.warning("⚠️ Impossible de convertir en liste de dicts", parsed_type=type(parsed_data).__name__)
        return default or []
