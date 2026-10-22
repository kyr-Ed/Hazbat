-- BMAC PostgreSQL schema
-- Migrated from the Access backend, same ID convention and relationships,
-- but with FK constraints enforced natively by Postgres.

CREATE TABLE tbl_projects (
    project_name    TEXT PRIMARY KEY,
    active          BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE tbl_materials (
    material_id     TEXT PRIMARY KEY,
    chemistry       TEXT,
    supplier        TEXT,
    date_received   DATE,
    quantity_kg     NUMERIC,
    location        TEXT,
    availability    TEXT,
    notes           TEXT
);

CREATE TABLE tbl_coating (
    coating_id      TEXT PRIMARY KEY,
    material_id     TEXT NOT NULL REFERENCES tbl_materials(material_id),
    project         TEXT REFERENCES tbl_projects(project_name),
    coating_date    DATE,
    made_by         TEXT,
    coat_weight_gsm NUMERIC,
    porosity        NUMERIC,
    notes           TEXT
);

INSERT INTO tbl_projects (project_name, active) VALUES
    ('LEAP', TRUE),
    ('FAST', TRUE),
    ('Shared', TRUE);


CREATE TABLE tbl_slp (
    slp_id              TEXT PRIMARY KEY,
    coating_id           TEXT NOT NULL REFERENCES tbl_coating(coating_id),
    project               TEXT REFERENCES tbl_projects(project_name),
    date_made             DATE,
    made_by               TEXT,
    electrolyte           TEXT,
    formation_capacity    NUMERIC,
    np_ratio              NUMERIC,
    notes                 TEXT
);

CREATE TABLE tbl_coincell (
    coincell_id         TEXT PRIMARY KEY,
    coating_id            TEXT NOT NULL REFERENCES tbl_coating(coating_id),
    project                TEXT REFERENCES tbl_projects(project_name),
    date_made              DATE,
    made_by                TEXT,
    electrolyte            TEXT,
    formation_capacity     NUMERIC,
    cell_type              TEXT,
    gsm                    NUMERIC,
    notes                  TEXT
);

CREATE TABLE tbl_mlp (
    mlp_id              TEXT PRIMARY KEY,
    cat_coating_id       TEXT NOT NULL REFERENCES tbl_coating(coating_id),
    an_coating_id        TEXT NOT NULL REFERENCES tbl_coating(coating_id),
    project               TEXT REFERENCES tbl_projects(project_name),
    date_made             DATE,
    electrolyte           TEXT,
    cell_capacity         NUMERIC,
    ac_area_ratio         NUMERIC
);

CREATE TABLE tbl_users (
    user_id         SERIAL PRIMARY KEY,
    username        TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    full_name       TEXT,
    is_admin        BOOLEAN NOT NULL DEFAULT FALSE
);

-- Which projects each (non-admin) user can see. Read at login.
CREATE TABLE tbl_user_projects (
    user_id         INTEGER NOT NULL REFERENCES tbl_users(user_id) ON DELETE CASCADE,
    project_name    TEXT NOT NULL REFERENCES tbl_projects(project_name),
    PRIMARY KEY (user_id, project_name)
);

-- Uploaded BioLogic .mpr cycling files, linked to a cell record.
CREATE TABLE tbl_cycling_data (
    cycling_id        SERIAL PRIMARY KEY,
    record_id         TEXT NOT NULL,
    filename          TEXT,
    file_path         TEXT NOT NULL,
    num_points        INTEGER,
    max_capacity_mah  NUMERIC,
    num_cycles        INTEGER,
    uploaded_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Certificates of Analysis (COA) attached to a material. Several versions can be
-- kept per material; pages show the newest. Files live in uploads/coa/<material_id>/.
-- preview_path is a PDF copy used for in-browser preview (the original for PDFs,
-- a LibreOffice conversion for Word files; NULL if conversion failed).
CREATE TABLE tbl_material_coa (
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
CREATE INDEX idx_material_coa_material ON tbl_material_coa (material_id, uploaded_at DESC);
