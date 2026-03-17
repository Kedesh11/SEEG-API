"""
Configuration de la base de données.
Respecte le principe de séparation des préoccupations.
"""

from .database import close_mongo_connection, connect_to_mongo, get_db

__all__ = [
    "get_db",
    "connect_to_mongo",
    "close_mongo_connection",
]
