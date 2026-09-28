-- Dev-only setup, run once after schema.sql when the dev database is first created.
-- NOT for production.

-- tbl_users is not in schema.sql yet, so create it here if missing.
CREATE TABLE IF NOT EXISTS tbl_users (
    user_id        SERIAL PRIMARY KEY,
    username       TEXT UNIQUE NOT NULL,
    password_hash  TEXT NOT NULL,
    full_name      TEXT,
    is_admin       BOOLEAN NOT NULL DEFAULT FALSE
);

-- Dev login: username "dev", password "dev" (bcrypt hash made by pgcrypto).
CREATE EXTENSION IF NOT EXISTS pgcrypto;
INSERT INTO tbl_users (username, password_hash, full_name, is_admin)
VALUES ('dev', crypt('dev', gen_salt('bf', 12)), 'Dev User', TRUE)
ON CONFLICT (username) DO NOTHING;

-- Give the dev login access to every project (tbl_user_projects is read at login).
INSERT INTO tbl_user_projects (user_id, project_name)
SELECT u.user_id, p.project_name FROM tbl_users u CROSS JOIN tbl_projects p WHERE u.username = 'dev'
ON CONFLICT DO NOTHING;

-- A small example traceability chain, so search, cards and the graph have something to show.
INSERT INTO tbl_materials (material_id, chemistry, supplier, date_received, quantity_kg, location, availability) VALUES
    ('CAT-NMC-001', 'NMC 811',  'Example supplier', '2026-09-01', 5.0, 'Dry room', 'Available'),
    ('AN-GR-001',   'Graphite', 'Example supplier', '2026-09-01', 3.0, 'Dry room', 'Available')
ON CONFLICT DO NOTHING;

INSERT INTO tbl_coating (coating_id, material_id, project, coating_date, made_by, coat_weight_gsm) VALUES
    ('CAT-NMC-001-C001', 'CAT-NMC-001', 'LEAP', '2026-09-05', 'Dev User', 145),
    ('AN-GR-001-C001',   'AN-GR-001',   'LEAP', '2026-09-05', 'Dev User', 120)
ON CONFLICT DO NOTHING;

INSERT INTO tbl_slp (slp_id, coating_id, project, date_made, made_by, formation_capacity) VALUES
    ('CAT-NMC-001-C001-SLP-01', 'CAT-NMC-001-C001', 'LEAP', '2026-09-08', 'Dev User', 118.9)
ON CONFLICT DO NOTHING;

INSERT INTO tbl_coincell (coincell_id, coating_id, project, date_made, made_by, cell_type) VALUES
    ('CAT-NMC-001-C001-CC01', 'CAT-NMC-001-C001', 'LEAP', '2026-09-08', 'Dev User', 'CR2032 half cell')
ON CONFLICT DO NOTHING;

INSERT INTO tbl_mlp (mlp_id, cat_coating_id, an_coating_id, project, date_made) VALUES
    ('MLP-0001', 'CAT-NMC-001-C001', 'AN-GR-001-C001', 'LEAP', '2026-09-10')
ON CONFLICT DO NOTHING;
