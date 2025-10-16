-- Description: Création de la table email_logs pour le tracking des emails envoyés
-- Depends: 

-- Création de la table email_logs
CREATE TABLE IF NOT EXISTS email_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID,
    "to" VARCHAR(255) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    html TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    provider_message_id VARCHAR(255),
    sent_at TIMESTAMP WITH TIME ZONE NOT NULL,
    email_metadata JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_email_logs_application 
        FOREIGN KEY (application_id) 
        REFERENCES applications(id) 
        ON DELETE SET NULL
);

-- Création des index pour optimiser les recherches
CREATE INDEX IF NOT EXISTS idx_email_logs_application ON email_logs(application_id);
CREATE INDEX IF NOT EXISTS idx_email_logs_category ON email_logs(category);
CREATE INDEX IF NOT EXISTS idx_email_logs_sent_at ON email_logs(sent_at);
CREATE INDEX IF NOT EXISTS idx_email_logs_to ON email_logs("to");

-- Commentaires pour la documentation
COMMENT ON TABLE email_logs IS 'Historique des emails envoyés par le système';
COMMENT ON COLUMN email_logs.application_id IS 'Référence optionnelle vers une candidature';
COMMENT ON COLUMN email_logs."to" IS 'Adresse email du destinataire';
COMMENT ON COLUMN email_logs.subject IS 'Sujet de l''email';
COMMENT ON COLUMN email_logs.html IS 'Contenu HTML de l''email';
COMMENT ON COLUMN email_logs.category IS 'Catégorie de l''email (welcome, interview, rejection, etc.)';
COMMENT ON COLUMN email_logs.provider_message_id IS 'ID du message retourné par le fournisseur d''email';
COMMENT ON COLUMN email_logs.sent_at IS 'Date et heure d''envoi de l''email';
COMMENT ON COLUMN email_logs.email_metadata IS 'Métadonnées supplémentaires au format JSON';

