"""Certificates of Analysis (COA) attached to materials (routers/coa.py).

Accepts .pdf, .docx and .doc. Files are checked by their first bytes (not just the
extension), saved under uploads/coa/<material_id>/ with a random name, and listed in
tbl_material_coa. Word files are converted to PDF with LibreOffice so every COA can be
previewed in the browser; if LibreOffice isn't installed the COA is still stored and
can be downloaded, it just has no preview.

Install the converter on the Linux server with:
    sudo apt install --no-install-recommends libreoffice-writer
"""

import hashlib
import re
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

from core.db import get_connection


COA_DIR = Path("uploads/coa")
MAX_COA_BYTES = 25 * 1024 * 1024        # 25 MB; supplier COAs are normally < 2 MB
CONVERT_TIMEOUT_S = 90
ALLOWED_EXTENSIONS = {".pdf": "pdf", ".docx": "docx", ".doc": "doc"}
KIND_LABELS = {"pdf": "PDF", "docx": "Word", "doc": "Word (97–2003)"}
OLE_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")   # legacy .doc container


class CoaError(ValueError):
    """A COA upload was rejected; the message is shown to the user."""


# --- Checking -----------------------------------------------------------------

def detect_kind(filename: str, data: bytes) -> str:
    """'pdf' / 'docx' / 'doc' if the file is really that type, else raises CoaError."""
    ext = Path(filename or "").suffix.lower()
    kind = ALLOWED_EXTENSIONS.get(ext)
    if not kind:
        raise CoaError("COA must be a .pdf, .docx or .doc file.")
    if not data:
        raise CoaError("That file is empty.")
    if len(data) > MAX_COA_BYTES:
        raise CoaError(f"COA is larger than {MAX_COA_BYTES // (1024 * 1024)} MB.")

    if kind == "pdf" and not data[:1024].lstrip().startswith(b"%PDF-"):
        raise CoaError("That file has a .pdf name but isn't a PDF.")
    if kind == "docx":
        try:
            with zipfile.ZipFile(BytesIO(data)) as z:
                if "word/document.xml" not in z.namelist():
                    raise CoaError("That .docx file isn't a Word document.")
        except zipfile.BadZipFile:
            raise CoaError("That .docx file is damaged or isn't a Word document.")
    if kind == "doc" and not data.startswith(OLE_MAGIC):
        raise CoaError("That .doc file isn't a Word 97–2003 document.")
    return kind


def safe_display_name(filename: str) -> str:
    """Keep the original name for display/download, minus any folder parts or control characters."""
    name = Path((filename or "coa").replace("\\", "/")).name
    name = "".join(ch for ch in name if ch.isprintable()).strip()
    return name[:200] or "coa"


# --- Saving and converting -----------------------------------------------------

def coa_folder(material_id: str) -> Path:
    """uploads/coa/<material_id>/, with anything that isn't safe in a folder name replaced by _."""
    return COA_DIR / (re.sub(r"[^A-Za-z0-9._-]", "_", material_id).strip(".") or "_")


def convert_to_pdf(source: Path):
    """Convert a Word file to PDF next to it with LibreOffice. Returns the PDF path or None."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    # A throwaway LibreOffice profile per conversion, so two uploads at once don't clash.
    with tempfile.TemporaryDirectory(prefix="hazbat-lo-") as profile:
        try:
            subprocess.run(
                [soffice, f"-env:UserInstallation=file://{profile}", "--headless", "--norestore",
                 "--convert-to", "pdf", "--outdir", str(source.parent), str(source)],
                check=True, timeout=CONVERT_TIMEOUT_S, capture_output=True,
            )
        except (subprocess.SubprocessError, OSError):
            return None
    pdf = source.with_suffix(".pdf")
    return pdf if pdf.exists() else None


def save_coa(material_id: str, filename: str, data: bytes, uploaded_by=None) -> dict:
    """Check, store and (for Word files) convert a COA, then log it in tbl_material_coa.
    Returns the new COA as a dict (see coa_dict). Raises CoaError for bad files."""
    kind = detect_kind(filename, data)
    if not material_exists(material_id):
        raise CoaError(f"Material {material_id} doesn't exist.")

    folder = coa_folder(material_id)
    folder.mkdir(parents=True, exist_ok=True)
    stored = folder / f"{uuid.uuid4().hex}.{kind}"
    stored.write_bytes(data)
    preview = stored if kind == "pdf" else convert_to_pdf(stored)

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO tbl_material_coa (material_id, filename, file_kind, file_path, preview_path, "
            "size_bytes, sha256, uploaded_by) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
            "RETURNING " + COA_COLUMNS,
            (material_id, safe_display_name(filename), kind, str(stored), str(preview) if preview else None,
             len(data), hashlib.sha256(data).hexdigest(), uploaded_by),
        )
        row = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        stored.unlink(missing_ok=True)
        if preview and preview != stored:
            preview.unlink(missing_ok=True)
        raise
    finally:
        cur.close()
        conn.close()
    return coa_dict(row)


# --- Reading --------------------------------------------------------------------

COA_COLUMNS = ("coa_id, material_id, filename, file_kind, file_path, preview_path, size_bytes, "
               "uploaded_by, uploaded_at")


def coa_dict(row) -> dict:
    """One tbl_material_coa row as the dict the templates and JSON API use."""
    coa_id, material_id, filename, kind, file_path, preview_path, size, by, at = row
    return {
        "coa_id": coa_id, "material_id": material_id, "filename": filename,
        "kind": kind, "kind_label": KIND_LABELS.get(kind, kind),
        "size_bytes": size, "size_label": human_size(size),
        "uploaded_by": by, "uploaded_at": at.strftime("%d %b %Y, %H:%M") if at else None,
        "has_preview": bool(preview_path),
        "preview_url": f"/coa/{coa_id}/preview" if preview_path else None,
        "download_url": f"/coa/{coa_id}/download",
        "file_path": file_path, "preview_path": preview_path,
    }


def public_coa(coa):
    """coa_dict without the server file paths (for JSON and HTML data attributes)."""
    if not coa:
        return None
    return {k: v for k, v in coa.items() if k not in ("file_path", "preview_path")}


def get_coa(coa_id: int):
    """One COA by ID (None if not found)."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT {COA_COLUMNS} FROM tbl_material_coa WHERE coa_id = %s", (coa_id,))
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()
    return coa_dict(row) if row else None


def list_coas(material_id: str) -> list:
    """Every COA for a material, newest first."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT {COA_COLUMNS} FROM tbl_material_coa WHERE material_id = %s "
                    "ORDER BY uploaded_at DESC, coa_id DESC", (material_id,))
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()
    return [coa_dict(r) for r in rows]


def latest_coas(material_ids) -> dict:
    """{material_id: newest COA dict} for several materials in one query (cards grids)."""
    material_ids = list(material_ids)
    if not material_ids:
        return {}
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT DISTINCT ON (material_id) {COA_COLUMNS} FROM tbl_material_coa "
            "WHERE material_id = ANY(%s) ORDER BY material_id, uploaded_at DESC, coa_id DESC",
            (material_ids,),
        )
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()
    return {r[1]: coa_dict(r) for r in rows}


def material_summaries(material_ids) -> list:
    """Fields shown on the small material cards (bulk upload results, new material page)."""
    material_ids = list(material_ids)
    if not material_ids:
        return []
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT material_id, chemistry, supplier, quantity_kg, date_received, location "
            "FROM tbl_materials WHERE material_id = ANY(%s)", (material_ids,),
        )
        found = {r[0]: r for r in cur.fetchall()}
    finally:
        cur.close()
        conn.close()
    coas = latest_coas(found)
    cards = []
    for material_id in material_ids:            # keep the spreadsheet order
        r = found.get(material_id)
        if r:
            cards.append({"material_id": r[0], "chemistry": r[1], "supplier": r[2], "quantity_kg": r[3],
                          "date_received": r[4], "location": r[5], "coa": public_coa(coas.get(r[0]))})
    return cards


def material_exists(material_id: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM tbl_materials WHERE material_id = %s", (material_id,))
        return cur.fetchone() is not None
    finally:
        cur.close()
        conn.close()


def delete_coa(coa_id: int) -> bool:
    """Remove a COA row and its files. Returns False if it didn't exist."""
    coa = get_coa(coa_id)
    if not coa:
        return False
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM tbl_material_coa WHERE coa_id = %s", (coa_id,))
        conn.commit()
    finally:
        cur.close()
        conn.close()
    for path in {coa["file_path"], coa["preview_path"]} - {None}:
        Path(path).unlink(missing_ok=True)
    return True


def remove_coa_folder(material_id: str):
    """Delete a material's COA files (called after the material itself is deleted)."""
    folder = coa_folder(material_id)
    if folder.is_dir():
        shutil.rmtree(folder, ignore_errors=True)


def human_size(n) -> str:
    if n is None:
        return ""
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n / (1024 * 1024):.1f} MB"
