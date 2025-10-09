"""add_performance_indexes

Revision ID: add_perf_idx_001
Revises: 21bf595b762e
Create Date: 2025-12-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_perf_idx_001'
down_revision = '21bf595b762e'
branch_labels = None
depends_on = None

# Désactiver les transactions DDL pour cette migration
disable_ddl_transaction = True


def upgrade() -> None:
    """Ajoute des indexes pour améliorer les performances des requêtes fréquentes."""
    
    # Indexes sur la table users
    try:
        op.create_index('idx_users_email', 'users', ['email'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_users_matricule', 'users', ['matricule'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_users_role', 'users', ['role'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_users_is_active', 'users', ['is_active'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_users_created_at', 'users', ['created_at'])
    except Exception:
        pass
    
    # Indexes sur la table job_offers
    try:
        op.create_index('idx_job_offers_recruiter_id', 'job_offers', ['recruiter_id'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_job_offers_status', 'job_offers', ['status'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_job_offers_created_at', 'job_offers', ['created_at'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_job_offers_application_deadline', 'job_offers', ['application_deadline'])
    except Exception:
        pass
    
    # Indexes composés pour les recherches fréquentes
    try:
        op.create_index('idx_job_offers_status_created', 'job_offers', ['status', 'created_at'])
    except Exception:
        pass
    
    # Indexes sur la table applications
    try:
        op.create_index('idx_applications_candidate_id', 'applications', ['candidate_id'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_applications_job_offer_id', 'applications', ['job_offer_id'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_applications_status', 'applications', ['status'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_applications_created_at', 'applications', ['created_at'])
    except Exception:
        pass
    
    # Indexes composés pour les requêtes complexes
    try:
        op.create_index('idx_applications_candidate_status', 'applications', ['candidate_id', 'status'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_applications_job_status', 'applications', ['job_offer_id', 'status'])
    except Exception:
        pass
    
    # Indexes sur la table application_documents
    try:
        op.create_index('idx_app_docs_application_id', 'application_documents', ['application_id'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_app_docs_document_type', 'application_documents', ['document_type'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_app_docs_uploaded_at', 'application_documents', ['uploaded_at'])
    except Exception:
        pass
    
    # Indexes sur la table notifications
    try:
        op.create_index('idx_notifications_user_id', 'notifications', ['user_id'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_notifications_read', 'notifications', ['read'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_notifications_created_at', 'notifications', ['created_at'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_notifications_user_read', 'notifications', ['user_id', 'read'])
    except Exception:
        pass
    
    # Indexes sur la table interview_slots
    try:
        op.create_index('idx_interview_slots_application_id', 'interview_slots', ['application_id'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_interview_slots_date', 'interview_slots', ['date'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_interview_slots_status', 'interview_slots', ['status'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_interview_slots_is_available', 'interview_slots', ['is_available'])
    except Exception:
        pass
    
    # Indexes sur les tables d'évaluation
    try:
        op.create_index('idx_protocol1_eval_application_id', 'protocol1_evaluations', ['application_id'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_protocol1_eval_evaluator_id', 'protocol1_evaluations', ['evaluator_id'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_protocol1_eval_status', 'protocol1_evaluations', ['status'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_protocol2_eval_application_id', 'protocol2_evaluations', ['application_id'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_protocol2_eval_evaluator_id', 'protocol2_evaluations', ['evaluator_id'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_protocol2_eval_completed', 'protocol2_evaluations', ['completed'])
    except Exception:
        pass
    
    # Indexes sur la table application_history
    try:
        op.create_index('idx_app_history_application_id', 'application_history', ['application_id'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_app_history_changed_by', 'application_history', ['changed_by'])
    except Exception:
        pass
    
    try:
        op.create_index('idx_app_history_changed_at', 'application_history', ['changed_at'])
    except Exception:
        pass


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
