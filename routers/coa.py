"""Certificates of Analysis (COA) for materials: upload, list, preview, download, remove.

POST   /materials/{id}/coa   upload a .pdf/.docx/.doc (the card's "+ COA" button, JSON reply)
GET    /materials/{id}/coa   every COA for a material, newest first (JSON)
GET    /coa/{coa_id}/preview PDF shown inline in the preview window (Word files are pre-converted)
GET    /coa/{coa_id}/download the original file
DELETE /coa/{coa_id}         remove a COA (the newest remaining one is shown instead)

All of these need a login: COAs can contain supplier-confidential data.
Storage and checks are in services/coa.py.
"""

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse

from core.auth import require_login
from services.coa import (MAX_COA_BYTES, CoaError, delete_coa, get_coa, list_coas, public_coa,
                          save_coa)

router = APIRouter()


def _not_logged_in(request: Request):
    """JSON endpoints answer 401 instead of redirecting to /login."""
    if not request.session.get("user_id"):
        return JSONResponse({"error": "Please log in again."}, status_code=401)
    return None


def _file_response(path: str, filename: str, media_type: str, inline: bool):
    disposition = "inline" if inline else "attachment"
    # RFC 6266 / 5987: an ASCII fallback plus the real (UTF-8) name
    ascii_name = filename.encode("ascii", "replace").decode().replace('"', "'")
    headers = {
        "Content-Disposition": f"{disposition}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}",
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, max-age=300",
    }
    return FileResponse(path, media_type=media_type, headers=headers)


@router.post("/materials/{material_id}/coa")
async def upload_coa(request: Request, material_id: str, file: UploadFile = File(...)):
    """Attach a COA to a material. Replies with the new COA so the card can update itself."""
    denied = _not_logged_in(request)
    if denied:
        return denied
    data = await file.read(MAX_COA_BYTES + 1)
    try:
        # Word -> PDF conversion can take a few seconds, so keep it off the event loop
        coa = await run_in_threadpool(save_coa, material_id, file.filename, data,
                                      request.session.get("full_name"))
    except CoaError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    return JSONResponse({"coa": public_coa(coa)}, status_code=201)


@router.get("/materials/{material_id}/coa")
def material_coas(request: Request, material_id: str):
    """All COAs for a material, newest first."""
    denied = _not_logged_in(request)
    if denied:
        return denied
    return JSONResponse({"material_id": material_id,
                         "coas": [public_coa(c) for c in list_coas(material_id)]})


@router.get("/coa/{coa_id}/preview")
def preview_coa(request: Request, coa_id: int):
    """The COA as a PDF, shown inside the preview window."""
    redirect = require_login(request)
    if redirect:
        return redirect
    coa = get_coa(coa_id)
    if not coa or not coa["preview_path"] or not Path(coa["preview_path"]).exists():
        return JSONResponse({"error": "No preview for this COA."}, status_code=404)
    return _file_response(coa["preview_path"], Path(coa["filename"]).stem + ".pdf",
                          "application/pdf", inline=True)


@router.get("/coa/{coa_id}/download")
def download_coa(request: Request, coa_id: int):
    """The original file exactly as it was uploaded."""
    redirect = require_login(request)
    if redirect:
        return redirect
    coa = get_coa(coa_id)
    if not coa or not Path(coa["file_path"]).exists():
        return JSONResponse({"error": "COA not found."}, status_code=404)
    media = {"pdf": "application/pdf", "doc": "application/msword",
             "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}[coa["kind"]]
    return _file_response(coa["file_path"], coa["filename"], media, inline=False)


@router.delete("/coa/{coa_id}")
def remove_coa(request: Request, coa_id: int):
    """Remove a COA. Replies with the material's newest remaining COA (or null)."""
    denied = _not_logged_in(request)
    if denied:
        return denied
    coa = get_coa(coa_id)
    if not coa or not delete_coa(coa_id):
        return JSONResponse({"error": "COA not found."}, status_code=404)
    remaining = list_coas(coa["material_id"])
    return JSONResponse({"coa": public_coa(remaining[0]) if remaining else None})
