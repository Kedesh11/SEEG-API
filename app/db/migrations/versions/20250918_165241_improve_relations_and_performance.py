"""Improve relations and add performance indexes

Revision ID: improve_relations_perf
Revises: c233e3cf8f4e
Create Date: 2025-09-18 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'improve_relations_perf'
down_revision = 'c233e3cf8f4e'
branch_labels = None
depends_on = None


def upgrade():
    """Améliorer les relations et ajouter des index de performance"""
    
    # 1. Améliorer la table notifications (UUID au lieu d'Integer)
    op.execute("""
        ALTER TABLE notifications 
        DROP CONSTRAINT IF EXISTS notifications_pkey CASCADE;
    """)
    
    op.execute("""
        ALTER TABLE notifications 
        ADD COLUMN IF NOT EXISTS new_id UUID DEFAULT gen_random_uuid();
    """)
    
    op.execute("""
        UPDATE notifications 
        SET new_id = gen_random_uuid() 
        WHERE new_id IS NULL;
    """)
    
    op.execute("""
        ALTER TABLE notifications 
        ALTER COLUMN new_id SET NOT NULL;
    """)
    
    op.execute("""
        ALTER TABLE notifications 
        ADD PRIMARY KEY (new_id);
    """)
    
    op.execute("""
        ALTER TABLE notifications 
        DROP COLUMN IF EXISTS id;
    """)
    
    op.execute("""
        ALTER TABLE notifications 
        RENAME COLUMN new_id TO id;
    """)
    
    # 2. Ajouter des colonnes manquantes
    op.add_column('interview_slots', sa.Column('recruiter_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('interview_slots', sa.Column('meeting_link', sa.String(), nullable=True))
    op.add_column('interview_slots', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('notifications', sa.Column('priority', sa.String(), default='normal'))
    
    # 3. Ajouter des index simples pour les performances
    op.create_index('idx_users_role', 'users', ['role'])
    op.create_index('idx_candidate_profiles_gender', 'candidate_profiles', ['gender'])
    op.create_index('idx_candidate_profiles_experience', 'candidate_profiles', ['years_experience'])
    op.create_index('idx_job_offers_department', 'job_offers', ['department'])
    op.create_index('idx_job_offers_status', 'job_offers', ['status'])
    op.create_index('idx_applications_status', 'applications', ['status'])
    op.create_index('idx_applications_created_at', 'applications', ['created_at'])
    op.create_index('idx_notifications_read', 'notifications', ['read'])
    op.create_index('idx_notifications_type', 'notifications', ['type'])
    op.create_index('idx_interview_slots_date', 'interview_slots', ['date'])
    op.create_index('idx_interview_slots_status', 'interview_slots', ['status'])
    op.create_index('idx_application_documents_type', 'application_documents', ['document_type'])
    
    # 4. Ajouter des index composites pour les requêtes complexes
    op.create_index('idx_applications_candidate_job', 'applications', ['candidate_id', 'job_offer_id'])
    op.create_index('idx_applications_status_created', 'applications', ['status', 'created_at'])
    op.create_index('idx_applications_job_status', 'applications', ['job_offer_id', 'status'])
    op.create_index('idx_job_offers_recruiter_status', 'job_offers', ['recruiter_id', 'status'])
    op.create_index('idx_notifications_user_read', 'notifications', ['user_id', 'read'])
    op.create_index('idx_interview_slots_date_status', 'interview_slots', ['date', 'status'])
    op.create_index('idx_candidate_profiles_gender_experience', 'candidate_profiles', ['gender', 'years_experience'])
    
    # 5. Ajouter des contraintes de clés étrangères manquantes
    op.create_foreign_key('fk_interview_slots_recruiter', 'interview_slots', 'users', ['recruiter_id'], ['id'], ondelete='CASCADE')
    
    # 6. Améliorer les contraintes existantes
    op.create_unique_constraint('uq_applications_candidate_job', 'applications', ['candidate_id', 'job_offer_id'])


def downgrade():
    """Revenir aux relations précédentes"""
    
    # Supprimer les contraintes et index
    op.drop_constraint('uq_applications_candidate_job', 'applications', type_='unique')
    op.drop_constraint('fk_interview_slots_recruiter', 'interview_slots', type_='foreignkey')
    
    # Supprimer les index composites
    op.drop_index('idx_candidate_profiles_gender_experience', 'candidate_profiles')
    op.drop_index('idx_interview_slots_date_status', 'interview_slots')
    op.drop_index('idx_notifications_user_read', 'notifications')
    op.drop_index('idx_job_offers_recruiter_status', 'job_offers')
    op.drop_index('idx_applications_job_status', 'applications')
    op.drop_index('idx_applications_status_created', 'applications')
    op.drop_index('idx_applications_candidate_job', 'applications')
    
    # Supprimer les index simples
    op.drop_index('idx_application_documents_type', 'application_documents')
    op.drop_index('idx_interview_slots_status', 'interview_slots')
    op.drop_index('idx_interview_slots_date', 'interview_slots')
    op.drop_index('idx_notifications_type', 'notifications')
    op.drop_index('idx_notifications_read', 'notifications')
    op.drop_index('idx_applications_created_at', 'applications')
    op.drop_index('idx_applications_status', 'applications')
    op.drop_index('idx_job_offers_status', 'job_offers')
    op.drop_index('idx_job_offers_department', 'job_offers')
    op.drop_index('idx_candidate_profiles_experience', 'candidate_profiles')
    op.drop_index('idx_candidate_profiles_gender', 'candidate_profiles')
    op.drop_index('idx_users_role', 'users')
    
    # Supprimer les colonnes ajoutées
    op.drop_column('notifications', 'priority')
    op.drop_column('interview_slots', 'notes')
    op.drop_column('interview_slots', 'meeting_link')
    op.drop_column('interview_slots', 'recruiter_id')
    
    # Revenir à l'ID Integer pour notifications
    op.execute("""
        ALTER TABLE notifications 
        DROP CONSTRAINT IF EXISTS notifications_pkey CASCADE;
    """)
    
    op.execute("""
        ALTER TABLE notifications 
        ADD COLUMN IF NOT EXISTS old_id SERIAL;
    """)
    
    op.execute("""
        ALTER TABLE notifications 
        ADD PRIMARY KEY (old_id);
    """)
    
    op.execute("""
        ALTER TABLE notifications 
        DROP COLUMN IF EXISTS id;
    """)
    
    op.execute("""
        ALTER TABLE notifications 
        RENAME COLUMN old_id TO id;
    """)
