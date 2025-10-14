-- ================================================================================
-- SCRIPT DE MIGRATION SEEG API - À exécuter dans Azure Portal Query Editor
-- ================================================================================
-- Date: 2025-10-14
-- Description: Applique toutes les migrations nécessaires
-- ================================================================================

-- ============================================
-- MIGRATION 1: Ajout de questions_mtp aux job_offers
-- ============================================
DO $$
BEGIN
    -- Ajouter la colonne questions_mtp si elle n'existe pas
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'job_offers' AND column_name = 'questions_mtp'
    ) THEN
        ALTER TABLE job_offers ADD COLUMN questions_mtp JSONB;
        RAISE NOTICE '✅ Colonne questions_mtp ajoutée à job_offers';
    ELSE
        RAISE NOTICE '⏭️  Colonne questions_mtp existe déjà';
    END IF;
    
    -- Convertir JSON en JSONB pour les colonnes existantes
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'job_offers' 
        AND column_name = 'requirements' 
        AND data_type = 'json'
    ) THEN
        ALTER TABLE job_offers 
        ALTER COLUMN requirements TYPE JSONB USING requirements::JSONB;
        RAISE NOTICE '✅ Colonne requirements convertie en JSONB';
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'job_offers' 
        AND column_name = 'benefits' 
        AND data_type = 'json'
    ) THEN
        ALTER TABLE job_offers 
        ALTER COLUMN benefits TYPE JSONB USING benefits::JSONB;
        RAISE NOTICE '✅ Colonne benefits convertie en JSONB';
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'job_offers' 
        AND column_name = 'responsibilities' 
        AND data_type = 'json'
    ) THEN
        ALTER TABLE job_offers 
        ALTER COLUMN responsibilities TYPE JSONB USING responsibilities::JSONB;
        RAISE NOTICE '✅ Colonne responsibilities convertie en JSONB';
    END IF;
END $$;

-- ============================================
-- MIGRATION 2: offer_status (remplace is_internal_only)
-- ============================================
DO $$
BEGIN
    -- Ajouter offer_status si elle n'existe pas
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'job_offers' AND column_name = 'offer_status'
    ) THEN
        ALTER TABLE job_offers ADD COLUMN offer_status VARCHAR(20) DEFAULT 'tous';
        RAISE NOTICE '✅ Colonne offer_status ajoutée';
        
        -- Migrer les données si is_internal_only existe
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'job_offers' AND column_name = 'is_internal_only'
        ) THEN
            UPDATE job_offers 
            SET offer_status = CASE 
                WHEN is_internal_only = true THEN 'interne' 
                ELSE 'externe' 
            END
            WHERE offer_status = 'tous';
            RAISE NOTICE '✅ Données migrées de is_internal_only vers offer_status';
        END IF;
    ELSE
        RAISE NOTICE '⏭️  Colonne offer_status existe déjà';
    END IF;
    
    -- Supprimer is_internal_only si elle existe
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'job_offers' AND column_name = 'is_internal_only'
    ) THEN
        ALTER TABLE job_offers DROP COLUMN is_internal_only;
        RAISE NOTICE '✅ Colonne is_internal_only supprimée';
    ELSE
        RAISE NOTICE '⏭️  Colonne is_internal_only déjà supprimée';
    END IF;
END $$;

-- ============================================
-- MIGRATION 3: Colonnes manquantes dans applications
-- ============================================
DO $$
BEGIN
    -- has_been_manager
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'applications' AND column_name = 'has_been_manager'
    ) THEN
        ALTER TABLE applications ADD COLUMN has_been_manager BOOLEAN DEFAULT FALSE;
        RAISE NOTICE '✅ Colonne has_been_manager ajoutée';
    ELSE
        RAISE NOTICE '⏭️  Colonne has_been_manager existe déjà';
    END IF;
    
    -- ref_entreprise
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'applications' AND column_name = 'ref_entreprise'
    ) THEN
        ALTER TABLE applications ADD COLUMN ref_entreprise VARCHAR(255);
        RAISE NOTICE '✅ Colonne ref_entreprise ajoutée';
    ELSE
        RAISE NOTICE '⏭️  Colonne ref_entreprise existe déjà';
    END IF;
    
    -- ref_fullname
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'applications' AND column_name = 'ref_fullname'
    ) THEN
        ALTER TABLE applications ADD COLUMN ref_fullname VARCHAR(255);
        RAISE NOTICE '✅ Colonne ref_fullname ajoutée';
    ELSE
        RAISE NOTICE '⏭️  Colonne ref_fullname existe déjà';
    END IF;
    
    -- ref_mail
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'applications' AND column_name = 'ref_mail'
    ) THEN
        ALTER TABLE applications ADD COLUMN ref_mail VARCHAR(255);
        RAISE NOTICE '✅ Colonne ref_mail ajoutée';
    ELSE
        RAISE NOTICE '⏭️  Colonne ref_mail existe déjà';
    END IF;
    
    -- ref_contact
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'applications' AND column_name = 'ref_contact'
    ) THEN
        ALTER TABLE applications ADD COLUMN ref_contact VARCHAR(50);
        RAISE NOTICE '✅ Colonne ref_contact ajoutée';
    ELSE
        RAISE NOTICE '⏭️  Colonne ref_contact existe déjà';
    END IF;
    
    -- Convertir mtp_answers en JSONB
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'applications' 
        AND column_name = 'mtp_answers' 
        AND data_type = 'json'
    ) THEN
        ALTER TABLE applications 
        ALTER COLUMN mtp_answers TYPE JSONB USING mtp_answers::JSONB;
        RAISE NOTICE '✅ Colonne mtp_answers convertie en JSONB';
    ELSE
        RAISE NOTICE '⏭️  Colonne mtp_answers déjà en JSONB';
    END IF;
END $$;

-- ============================================
-- MIGRATION 4: Mise à jour alembic_version
-- ============================================
DO $$
BEGIN
    -- Créer la table alembic_version si elle n'existe pas
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alembic_version') THEN
        CREATE TABLE alembic_version (
            version_num VARCHAR(32) NOT NULL,
            CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
        );
        RAISE NOTICE '✅ Table alembic_version créée';
    END IF;
    
    -- Mettre à jour la version
    DELETE FROM alembic_version;
    INSERT INTO alembic_version (version_num) VALUES ('20251013_app_flds');
    RAISE NOTICE '✅ Version alembic mise à jour: 20251013_app_flds';
END $$;

-- ============================================
-- VÉRIFICATION FINALE
-- ============================================
SELECT 
    '✅ MIGRATION TERMINÉE' as statut,
    (SELECT version_num FROM alembic_version) as version_actuelle,
    (SELECT COUNT(*) FROM job_offers) as nb_offres,
    (SELECT COUNT(*) FROM applications) as nb_candidatures;

