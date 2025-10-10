-- Corriger la version alembic
UPDATE alembic_version SET version_num = '20251010_add_updated_at';
SELECT version_num FROM alembic_version;

