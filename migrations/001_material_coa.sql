-- Adds COA attachments to an existing Hazbat database (new databases get this from schema.sql).
-- Run once:  psql "$DATABASE_URL" -f migrations/001_material_coa.sql
CREATE TABLE IF NOT EXISTS tbl_material_coa (
    coa_id          SERIAL PRIMARY KEY,
    material_id     TEXT NOT NULL REFERENCES tbl_materials(material_id) ON DELETE CASCADE,
    filename        TEXT NOT NULL,
    file_kind       TEXT NOT NULL CHECK (file_kind IN ('pdf', 'docx', 'doc')),
    file_path       TEXT NOT NULL,
    preview_path    TEXT,
    size_bytes      INTEGER NOT NULL,
    sha256          TEXT NOT NULL,
    uploaded_by     TEXT,
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_material_coa_material ON tbl_material_coa (material_id, uploaded_at DESC);
