"""import_seeg_agents_csv

Revision ID: 21bf595b762e
Revises: 20250922_users_matricule_int
Create Date: 2025-09-23 14:47:10.408462

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
import os
import csv
import uuid
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '21bf595b762e'
down_revision = '20250922_users_matricule_int'
branch_labels = None
depends_on = None

CSV_RELATIVE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "..",
)

CSV_PATH = os.path.normpath(
    os.path.join(CSV_RELATIVE_PATH, "data", "agents_seeg.csv")
)


def _iter_agents_from_csv(csv_path: str):
    with open(csv_path, mode="r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row:
                continue
            raw_matricule = (row.get("Matricule") or "").strip()
            nom = (row.get("Nom") or row.get("Nom ") or "").strip()
            prenom = (row.get("Prénom") or "").strip()
            if not raw_matricule or not raw_matricule.isdigit():
                continue
            yield {
                "matricule": int(raw_matricule),
                "nom": nom or None,
                "prenom": prenom or None,
            }


def upgrade() -> None:
    conn = op.get_bind()

    # S’assurer qu’un index unique existe sur matricule pour ON CONFLICT
    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_seeg_agents_matricule ON seeg_agents (matricule)"))

    if not os.path.isfile(CSV_PATH):
        alt_path = os.path.normpath(os.path.join(os.getcwd(), "backend", "data", "agents_seeg.csv"))
        if os.path.isfile(alt_path):
            path = alt_path
        else:
            raise FileNotFoundError(f"Fichier CSV introuvable: {CSV_PATH} ou {alt_path}")
    else:
        path = CSV_PATH

    upsert_stmt = text(
        """
        INSERT INTO seeg_agents (matricule, nom, prenom, id, created_at, updated_at)
        VALUES (:matricule, :nom, :prenom, :id, :created_at, :updated_at)
        ON CONFLICT (matricule)
        DO UPDATE SET nom = EXCLUDED.nom, prenom = EXCLUDED.prenom, updated_at = EXCLUDED.updated_at
        """
    )

    now = datetime.utcnow()
    agents = []
    for a in _iter_agents_from_csv(path):
        agents.append({
            **a,
            "id": uuid.uuid4(),
            "created_at": now,
            "updated_at": now,
        })

    if not agents:
        return

    batch_size = 1000
    for i in range(0, len(agents), batch_size):
        batch = agents[i:i + batch_size]
        conn.execute(upsert_stmt, batch)


def downgrade() -> None:
    conn = op.get_bind()

    paths_to_try = [CSV_PATH, os.path.normpath(os.path.join(os.getcwd(), "backend", "data", "agents_seeg.csv"))]
    csv_found = None
    for p in paths_to_try:
        if os.path.isfile(p):
            csv_found = p
            break
    if not csv_found:
        return

    matricules = [a["matricule"] for a in _iter_agents_from_csv(csv_found)]
    if not matricules:
        return

    chunk = 1000
    for i in range(0, len(matricules), chunk):
        sub = matricules[i:i + chunk]
        placeholders = ",".join([":m" + str(j) for j in range(len(sub))])
        stmt = text(f"DELETE FROM seeg_agents WHERE matricule IN ({placeholders})")
        params = {"m" + str(j): sub[j] for j in range(len(sub))}
        conn.execute(stmt, params)
