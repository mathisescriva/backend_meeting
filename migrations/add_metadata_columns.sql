-- Ajout des colonnes de métadonnées à la table meetings
-- SQLite ne prend pas en charge IF NOT EXISTS pour ALTER TABLE
ALTER TABLE meetings ADD COLUMN duration_seconds INTEGER;
ALTER TABLE meetings ADD COLUMN speakers_count INTEGER;
