"""
Script pour exécuter les migrations Alembic avec le mot de passe contenant des espaces
"""
import os
import sys
from pathlib import Path

# Set environment variables for database connection
os.environ["PGPASSWORD"] = "    "  # 4 espaces
os.environ["DATABASE_URL_SYNC"] = "postgresql://postgres@localhost:5432/recruteur"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres@localhost:5432/recruteur"

# Import and run alembic upgrade
from alembic.config import Config
from alembic import command

# Get the alembic.ini path
alembic_cfg = Config("alembic.ini")

# Override the sqlalchemy.url to use the connection without password in URL
# The PGPASSWORD environment variable will be used by psycopg2
alembic_cfg.set_main_option("sqlalchemy.url", "postgresql://postgres@localhost:5432/recruteur")

print("Exécution des migrations Alembic...")
try:
    command.upgrade(alembic_cfg, "head")
    print("✓ Migrations appliquées avec succès!")
except Exception as e:
    print(f"✗ Erreur lors de l'application des migrations:")
    print(f"  {type(e).__name__}: {e}")
    sys.exit(1)
