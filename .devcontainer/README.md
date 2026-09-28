# Hazbat dev environment

Opens the repo with Python 3.12 and a private PostgreSQL 16 database already set up.
Nothing to install on your own computer when using GitHub Codespaces.

## Start
- **Codespaces:** on GitHub, click **Code → Codespaces → Create codespace on <branch>**.
- **Local (needs Docker Desktop):** VS Code → *Dev Containers: Reopen in Container*.

First start takes ~3–5 minutes (it installs requirements.txt).

## Run the app
```bash
uvicorn main:app --reload --host 0.0.0.0
```
Open the forwarded port 8000 and log in with **dev / dev**.

## What's set up
- Database `bmac` built from `schema.sql`, plus `tbl_users`, a dev login and a small example chain
  (`.devcontainer/db-init/02-dev-seed.sql`). These scripts only run the first time the database is created.
- `DATABASE_URL` and `SESSION_SECRET` are set for you (dev values only).
- SQLTools extension with a "Hazbat dev DB" connection for browsing tables in VS Code.
- HAZbot needs `GEMINI_API_KEY`: add it as a Codespaces secret (GitHub → Settings → Codespaces) or in `.env`.

## Reset the database
Delete the codespace and create a new one, or locally run *Dev Containers: Rebuild Container*
after removing the `pgdata` volume.
