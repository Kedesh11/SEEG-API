-- Script pour corriger la table alembic_version dans Azure
-- Remplacer d150a8fca35c par 20251010_add_updated_at

-- 1. Voir la version actuelle
SELECT * FROM alembic_version;

-- 2. Mettre à jour vers la bonne révision
UPDATE alembic_version 
SET version_num = '20251010_add_updated_at' 
WHERE version_num = 'd150a8fca35c';

-- 3. Si aucune ligne n'a été mise à jour (revision différente), supprimer et insérer
DELETE FROM alembic_version;
INSERT INTO alembic_version (version_num) VALUES ('20251010_add_updated_at');

-- 4. Vérifier le résultat
SELECT * FROM alembic_version;

