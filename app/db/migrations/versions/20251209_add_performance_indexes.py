"""add_performance_indexes

Revision ID: add_perf_idx_001
Revises: 21bf595b762e
Create Date: 2025-12-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_perf_idx_001'
down_revision = '20251008_internal_external'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Ajoute des indexes pour améliorer les performances des requêtes fréquentes."""
    
    # Helper function to create index safely
    def create_index_if_not_exists(index_name, table_name, columns):
        op.execute(f"""
            CREATE INDEX IF NOT EXISTS {index_name} 
            ON {table_name} ({', '.join(columns)})
        """)
    
    # Indexes sur la table users
    create_index_if_not_exists('idx_users_email', 'users', ['email'])
    create_index_if_not_exists('idx_users_matricule', 'users', ['matricule'])
    create_index_if_not_exists('idx_users_role', 'users', ['role'])
    create_index_if_not_exists('idx_users_is_active', 'users', ['is_active'])
    create_index_if_not_exists('idx_users_created_at', 'users', ['created_at'])
    
    # Indexes sur la table job_offers
    create_index_if_not_exists('idx_job_offers_recruiter_id', 'job_offers', ['recruiter_id'])
    create_index_if_not_exists('idx_job_offers_status', 'job_offers', ['status'])
    create_index_if_not_exists('idx_job_offers_created_at', 'job_offers', ['created_at'])
    create_index_if_not_exists('idx_job_offers_application_deadline', 'job_offers', ['application_deadline'])
    
    # Indexes composés pour les recherches fréquentes
    create_index_if_not_exists('idx_job_offers_status_created', 'job_offers', ['status', 'created_at'])
    
    # Indexes sur la table applications
    create_index_if_not_exists('idx_applications_candidate_id', 'applications', ['candidate_id'])
    create_index_if_not_exists('idx_applications_job_offer_id', 'applications', ['job_offer_id'])
    create_index_if_not_exists('idx_applications_status', 'applications', ['status'])
    create_index_if_not_exists('idx_applications_created_at', 'applications', ['created_at'])
    
    # Indexes composés pour les requêtes complexes
    create_index_if_not_exists('idx_applications_candidate_status', 'applications', ['candidate_id', 'status'])
    create_index_if_not_exists('idx_applications_job_status', 'applications', ['job_offer_id', 'status'])
    
    # Indexes sur la table application_documents
    create_index_if_not_exists('idx_app_docs_application_id', 'application_documents', ['application_id'])
    create_index_if_not_exists('idx_app_docs_document_type', 'application_documents', ['document_type'])
    create_index_if_not_exists('idx_app_docs_uploaded_at', 'application_documents', ['uploaded_at'])
    
    # Indexes sur la table notifications
    create_index_if_not_exists('idx_notifications_user_id', 'notifications', ['user_id'])
    create_index_if_not_exists('idx_notifications_read', 'notifications', ['read'])
    create_index_if_not_exists('idx_notifications_created_at', 'notifications', ['created_at'])
    create_index_if_not_exists('idx_notifications_user_read', 'notifications', ['user_id', 'read'])
    
    # Indexes sur la table interview_slots
    create_index_if_not_exists('idx_interview_slots_application_id', 'interview_slots', ['application_id'])
    create_index_if_not_exists('idx_interview_slots_date', 'interview_slots', ['date'])
    create_index_if_not_exists('idx_interview_slots_status', 'interview_slots', ['status'])
    create_index_if_not_exists('idx_interview_slots_is_available', 'interview_slots', ['is_available'])
    
    # Indexes sur les tables d'évaluation
    create_index_if_not_exists('idx_protocol1_eval_application_id', 'protocol1_evaluations', ['application_id'])
    create_index_if_not_exists('idx_protocol1_eval_evaluator_id', 'protocol1_evaluations', ['evaluator_id'])
    create_index_if_not_exists('idx_protocol1_eval_status', 'protocol1_evaluations', ['status'])
    create_index_if_not_exists('idx_protocol2_eval_application_id', 'protocol2_evaluations', ['application_id'])
    create_index_if_not_exists('idx_protocol2_eval_evaluator_id', 'protocol2_evaluations', ['evaluator_id'])
    create_index_if_not_exists('idx_protocol2_eval_completed', 'protocol2_evaluations', ['completed'])
    
    # Indexes sur la table application_history
    create_index_if_not_exists('idx_app_history_application_id', 'application_history', ['application_id'])
    create_index_if_not_exists('idx_app_history_changed_by', 'application_history', ['changed_by'])
    create_index_if_not_exists('idx_app_history_changed_at', 'application_history', ['changed_at'])


def downgrade() -> None:
    """Supprime les indexes de performance."""
    
    # Suppression des indexes sur application_history
    op.drop_index('idx_app_history_changed_at', 'application_history')
    op.drop_index('idx_app_history_changed_by', 'application_history')
    op.drop_index('idx_app_history_application_id', 'application_history')
    
    # Suppression des indexes sur les tables d'évaluation
    op.drop_index('idx_protocol2_eval_completed', 'protocol2_evaluations')
    op.drop_index('idx_protocol2_eval_evaluator_id', 'protocol2_evaluations')
    op.drop_index('idx_protocol2_eval_application_id', 'protocol2_evaluations')
    
    op.drop_index('idx_protocol1_eval_status', 'protocol1_evaluations')
    op.drop_index('idx_protocol1_eval_evaluator_id', 'protocol1_evaluations')
    op.drop_index('idx_protocol1_eval_application_id', 'protocol1_evaluations')
    
    # Suppression des indexes sur interview_slots
    op.drop_index('idx_interview_slots_is_available', 'interview_slots')
    op.drop_index('idx_interview_slots_status', 'interview_slots')
    op.drop_index('idx_interview_slots_date', 'interview_slots')
    op.drop_index('idx_interview_slots_application_id', 'interview_slots')
    
    # Suppression des indexes sur notifications
    op.drop_index('idx_notifications_user_read', 'notifications')
    op.drop_index('idx_notifications_created_at', 'notifications')
    op.drop_index('idx_notifications_read', 'notifications')
    op.drop_index('idx_notifications_user_id', 'notifications')
    
    # Suppression des indexes sur application_documents
    op.drop_index('idx_app_docs_uploaded_at', 'application_documents')
    op.drop_index('idx_app_docs_document_type', 'application_documents')
    op.drop_index('idx_app_docs_application_id', 'application_documents')
    
    # Suppression des indexes sur applications
    op.drop_index('idx_applications_job_status', 'applications')
    op.drop_index('idx_applications_candidate_status', 'applications')
    op.drop_index('idx_applications_created_at', 'applications')
    op.drop_index('idx_applications_status', 'applications')
    op.drop_index('idx_applications_job_offer_id', 'applications')
    op.drop_index('idx_applications_candidate_id', 'applications')
    
    # Suppression des indexes sur job_offers
    op.drop_index('idx_job_offers_status_created', 'job_offers')
    op.drop_index('idx_job_offers_application_deadline', 'job_offers')
    op.drop_index('idx_job_offers_created_at', 'job_offers')
    op.drop_index('idx_job_offers_status', 'job_offers')
    op.drop_index('idx_job_offers_recruiter_id', 'job_offers')
    
    # Suppression des indexes sur users
    op.drop_index('idx_users_created_at', 'users')
    op.drop_index('idx_users_is_active', 'users')
    op.drop_index('idx_users_role', 'users')
    op.drop_index('idx_users_matricule', 'users')
    op.drop_index('idx_users_email', 'users')
