"""Add authentication and profile fields to users table

Revision ID: 20251010_add_user_auth
Revises: 20251010_add_mgr_ref
Create Date: 2025-10-10 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251010_add_user_auth'
down_revision = '20251010_add_mgr_ref'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Ajoute les champs d'authentification et de profil à la table users.
    
    Nouveaux champs:
    - adresse: Adresse complète du candidat
    - candidate_status: Type de candidat ('interne' ou 'externe')
    - statut: Statut du compte ('actif', 'en_attente', 'inactif', 'bloqué', 'archivé')
    - poste_actuel: Poste actuel du candidat (optionnel)
    - annees_experience: Années d'expérience (optionnel)
    - no_seeg_email: Indique si le candidat interne n'a pas d'email @seeg-gabon.com
    
    Modifications:
    - matricule: NOT NULL → NULL (candidats externes n'ont pas de matricule)
    - date_of_birth: TIMESTAMPTZ → DATE (seulement la date, pas l'heure)
    """
    
    # 1. Modifier le type de date_of_birth de TIMESTAMPTZ vers DATE
    # Note: PostgreSQL peut convertir automatiquement si les données sont compatibles
    op.alter_column('users', 'date_of_birth',
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.Date(),
        existing_nullable=True
    )
    
    # 2. Rendre matricule nullable (candidats externes)
    op.alter_column('users', 'matricule',
        existing_type=sa.Integer(),
        nullable=True,
        existing_nullable=False
    )
    
    # 3. Ajouter le champ adresse
    op.add_column('users', sa.Column(
        'adresse',
        sa.Text(),
        nullable=True,
        comment='Adresse complète du candidat'
    ))
    
    # 4. Ajouter le champ candidate_status avec contrainte CHECK
    op.add_column('users', sa.Column(
        'candidate_status',
        sa.String(10),
        nullable=True,
        comment='Type de candidat: interne (employé SEEG) ou externe'
    ))
    op.create_check_constraint(
        'chk_users_candidate_status',
        'users',
        "candidate_status IS NULL OR candidate_status IN ('interne', 'externe')"
    )
    
    # 5. Ajouter le champ statut avec contrainte CHECK et valeur par défaut
    op.add_column('users', sa.Column(
        'statut',
        sa.String(20),
        nullable=False,
        server_default='actif',
        comment='Statut du compte: actif, en_attente, inactif, bloqué, archivé'
    ))
    op.create_check_constraint(
        'chk_users_statut',
        'users',
        "statut IN ('actif', 'en_attente', 'inactif', 'bloqué', 'archivé')"
    )
    
    # 6. Ajouter le champ poste_actuel
    op.add_column('users', sa.Column(
        'poste_actuel',
        sa.Text(),
        nullable=True,
        comment='Poste actuel du candidat (optionnel)'
    ))
    
    # 7. Ajouter le champ annees_experience
    op.add_column('users', sa.Column(
        'annees_experience',
        sa.Integer(),
        nullable=True,
        comment='Années d\'expérience professionnelle du candidat'
    ))
    
    # 8. Ajouter le champ no_seeg_email
    op.add_column('users', sa.Column(
        'no_seeg_email',
        sa.Boolean(),
        nullable=False,
        server_default='false',
        comment='Indique si le candidat interne n\'a pas d\'email @seeg-gabon.com'
    ))
    
    # 8b. Ajouter is_internal_candidate si elle n'existe pas déjà
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='users' AND column_name='is_internal_candidate'
            ) THEN
                ALTER TABLE users ADD COLUMN is_internal_candidate BOOLEAN DEFAULT false NOT NULL;
            END IF;
        END $$;
    """)
    
    # 8c. Ajouter email_verified si elle n'existe pas déjà
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='users' AND column_name='email_verified'
            ) THEN
                ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT false NOT NULL;
            END IF;
        END $$;
    """)
    
    # 8d. Ajouter last_login si elle n'existe pas déjà
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='users' AND column_name='last_login'
            ) THEN
                ALTER TABLE users ADD COLUMN last_login TIMESTAMP WITH TIME ZONE;
            END IF;
        END $$;
    """)
    
    # 8e. Ajouter is_active si elle n'existe pas déjà
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='users' AND column_name='is_active'
            ) THEN
                ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT true NOT NULL;
            END IF;
        END $$;
    """)
    
    # 9. Créer les index pour les performances
    op.create_index(
        'idx_users_statut',
        'users',
        ['statut'],
        unique=False
    )
    
    op.create_index(
        'idx_users_candidate_status',
        'users',
        ['candidate_status'],
        unique=False
    )
    
    # Index partiel sur matricule (seulement les valeurs non NULL)
    op.create_index(
        'idx_users_matricule_not_null',
        'users',
        ['matricule'],
        unique=False,
        postgresql_where=sa.text('matricule IS NOT NULL')
    )
    
    # 10. Mettre à jour la valeur de sexe pour utiliser la contrainte CHECK
    # (Optionnel: ajouter contrainte CHECK si pas déjà présente)
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'chk_users_sexe'
            ) THEN
                ALTER TABLE users ADD CONSTRAINT chk_users_sexe 
                CHECK (sexe IS NULL OR sexe IN ('M', 'F'));
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Supprime les champs ajoutés et restaure les modifications."""
    
    # Supprimer les index
    op.drop_index('idx_users_matricule_not_null', table_name='users')
    op.drop_index('idx_users_candidate_status', table_name='users')
    op.drop_index('idx_users_statut', table_name='users')
    
    # Supprimer les contraintes CHECK
    op.drop_constraint('chk_users_statut', 'users', type_='check')
    op.drop_constraint('chk_users_candidate_status', 'users', type_='check')
    
    # Supprimer les colonnes
    op.drop_column('users', 'no_seeg_email')
    op.drop_column('users', 'annees_experience')
    op.drop_column('users', 'poste_actuel')
    op.drop_column('users', 'statut')
    op.drop_column('users', 'candidate_status')
    op.drop_column('users', 'adresse')
    
    # Restaurer matricule comme NOT NULL
    op.alter_column('users', 'matricule',
        existing_type=sa.Integer(),
        nullable=False,
        existing_nullable=True
    )
    
    # Restaurer date_of_birth comme TIMESTAMPTZ
    op.alter_column('users', 'date_of_birth',
        existing_type=sa.Date(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True
    )

