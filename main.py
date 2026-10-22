"""Hazbat / BMAC traceability database: the web app's entry point.

Start it with:  uvicorn main:app --reload

This file only builds the app. Each feature lives in its own file:
  routers/   the pages and API endpoints (what the browser asks for)
  services/  the logic behind them (database lookups, file parsing)
  core/      settings, database connection, templates and login checks
See CONTRIBUTING.md for where to put new code.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from core.config import SESSION_SECRET
from routers import (auth, bulk_upload, cards, charts, coa, cycling, graph, hazbot, home, inventory, lineage,
                     records, records_edit)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add every router's pages to the app. The order does not matter: no two URLs overlap.
for module in (home, auth, records, records_edit, bulk_upload, inventory, charts, cycling, cards, coa, lineage, graph, hazbot):
    app.include_router(module.router)
