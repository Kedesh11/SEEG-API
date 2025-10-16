-- Rollback: Suppression de la table email_logs

-- Supprimer les index (au cas où)
DROP INDEX IF EXISTS idx_email_logs_application;
DROP INDEX IF EXISTS idx_email_logs_category;
DROP INDEX IF EXISTS idx_email_logs_sent_at;
DROP INDEX IF EXISTS idx_email_logs_to;

-- Supprimer la table
DROP TABLE IF EXISTS email_logs CASCADE;

