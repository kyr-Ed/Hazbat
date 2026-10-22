"""Editing and deleting records (materials, coatings, SLP cells).

Delete is admin only, and fails if other records still link to the one being deleted.
Coin cells and MLPs have no edit page yet.
Templates: edit_material.html, edit_coating.html, edit_slp.html.
"""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from core.auth import require_login
from core.db import get_connection
from core.templates import templates
from services.coa import remove_coa_folder

router = APIRouter()


# --- Materials ---------------------------------------------------------------

@router.get("/materials/{material_id}/edit", response_class=HTMLResponse)
def edit_material_form(request: Request, material_id: str):
    """Edit form for one material."""
    redirect = require_login(request)
    if redirect:
        return redirect

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT material_id, chemistry, supplier, date_received, quantity_kg, location, availability "
        "FROM tbl_materials WHERE material_id = %s", (material_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return HTMLResponse("Material not found.", status_code=404)

    columns = ["material_id", "chemistry", "supplier", "date_received", "quantity_kg", "location", "availability"]
    material = dict(zip(columns, row))
    return templates.TemplateResponse("edit_material.html", {"request": request, "material": material})


@router.post("/materials/{material_id}/edit", response_class=HTMLResponse)
def submit_edit_material(request: Request, material_id: str, chemistry: str = Form(...), supplier: str = Form(...)):
    """Save a material's new chemistry and supplier."""
    redirect = require_login(request)
    if redirect:
        return redirect

    chemistry = chemistry.strip()
    supplier = supplier.strip()
    error = None
    success = None

    if not chemistry or not supplier:
        error = "All fields are required."
    else:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE tbl_materials SET chemistry = %s, supplier = %s WHERE material_id = %s",
                (chemistry, supplier, material_id)
            )
            conn.commit()
            success = "Material updated."
        except Exception as e:
            conn.rollback()
            error = str(e)
        cur.close()
        conn.close()

    material = {"material_id": material_id, "chemistry": chemistry, "supplier": supplier}
    return templates.TemplateResponse("edit_material.html", {"request": request, "material": material, "error": error, "success": success})

@router.post("/materials/{material_id}/delete")
def delete_material(request: Request, material_id: str):
    """Delete a material (admins only; fails if coatings still use it)."""
    redirect = require_login(request)
    if redirect:
        return redirect
    if not request.session.get("is_admin"):
        return HTMLResponse("Admins only.", status_code=403)

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM tbl_materials WHERE material_id = %s", (material_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return HTMLResponse(f"Cannot delete: this material still has linked coatings referencing it. ({str(e)})", status_code=400)

    cur.close()
    conn.close()
    remove_coa_folder(material_id)   # its COA rows went with it (ON DELETE CASCADE); now the files
    return RedirectResponse(url="/inventory/materials", status_code=303)
# --- Coatings ----------------------------------------------------------------

@router.get("/coatings/{coating_id}/edit", response_class=HTMLResponse)
def edit_coating_form(request: Request, coating_id: str):
    """Edit form for one coating."""
    redirect = require_login(request)
    if redirect:
        return redirect

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT coating_id, material_id, project, coating_date, made_by, coat_weight_gsm, porosity "
        "FROM tbl_coating WHERE coating_id = %s", (coating_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return HTMLResponse("Coating not found.", status_code=404)

    columns = ["coating_id", "material_id", "project", "coating_date", "made_by", "coat_weight_gsm", "porosity"]
    coating = dict(zip(columns, row))
    return templates.TemplateResponse("edit_coating.html", {"request": request, "coating": coating})


@router.post("/coatings/{coating_id}/edit", response_class=HTMLResponse)
def submit_edit_coating(request: Request, coating_id: str, made_by: str = Form(...), coat_weight_gsm: str = Form(None), porosity: str = Form(None)):
    """Save a coating's made-by, coat weight and porosity."""
    redirect = require_login(request)
    if redirect:
        return redirect

    made_by = made_by.strip()
    error = None
    success = None

    if not made_by:
        error = "Made By is required."
    else:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE tbl_coating SET made_by = %s, coat_weight_gsm = %s, porosity = %s WHERE coating_id = %s",
                (made_by, coat_weight_gsm if coat_weight_gsm else None, porosity if porosity else None, coating_id)
            )
            conn.commit()
            success = "Coating updated."
        except Exception as e:
            conn.rollback()
            error = str(e)
        cur.close()
        conn.close()

    coating = {"coating_id": coating_id, "made_by": made_by, "coat_weight_gsm": coat_weight_gsm, "porosity": porosity}
    return templates.TemplateResponse("edit_coating.html", {"request": request, "coating": coating, "error": error, "success": success})


@router.post("/coatings/{coating_id}/delete")
def delete_coating(request: Request, coating_id: str):
    """Delete a coating (admins only; fails if cells still use it)."""
    redirect = require_login(request)
    if redirect:
        return redirect
    if not request.session.get("is_admin"):
        return HTMLResponse("Admins only.", status_code=403)

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM tbl_coating WHERE coating_id = %s", (coating_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return HTMLResponse(f"Cannot delete: this coating still has linked cells referencing it. ({str(e)})", status_code=400)

    cur.close()
    conn.close()
    return RedirectResponse(url="/inventory/coatings", status_code=303)

# --- SLP cells ---------------------------------------------------------------

@router.get("/slp/{slp_id}/edit", response_class=HTMLResponse)
def edit_slp_form(request: Request, slp_id: str):
    """Edit form for one SLP cell."""
    redirect = require_login(request)
    if redirect:
        return redirect

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT slp_id, coating_id, project, date_made, made_by, electrolyte, formation_capacity "
        "FROM tbl_slp WHERE slp_id = %s", (slp_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return HTMLResponse("SLP cell not found.", status_code=404)

    columns = ["slp_id", "coating_id", "project", "date_made", "made_by", "electrolyte", "formation_capacity"]
    slp = dict(zip(columns, row))
    return templates.TemplateResponse("edit_slp.html", {"request": request, "slp": slp})


@router.post("/slp/{slp_id}/edit", response_class=HTMLResponse)
def submit_edit_slp(request: Request, slp_id: str, made_by: str = Form(...), electrolyte: str = Form(None), formation_capacity: str = Form(None)):
    """Save an SLP cell's made-by, electrolyte and formation capacity."""
    redirect = require_login(request)
    if redirect:
        return redirect

    made_by = made_by.strip()
    error = None
    success = None

    if not made_by:
        error = "Made By is required."
    else:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE tbl_slp SET made_by = %s, electrolyte = %s, formation_capacity = %s WHERE slp_id = %s",
                (made_by, electrolyte if electrolyte else None, formation_capacity if formation_capacity else None, slp_id)
            )
            conn.commit()
            success = "SLP cell updated."
        except Exception as e:
            conn.rollback()
            error = str(e)
        cur.close()
        conn.close()

    slp = {"slp_id": slp_id, "made_by": made_by, "electrolyte": electrolyte, "formation_capacity": formation_capacity}
    return templates.TemplateResponse("edit_slp.html", {"request": request, "slp": slp, "error": error, "success": success})


@router.post("/slp/{slp_id}/delete")
def delete_slp(request: Request, slp_id: str):
    """Delete an SLP cell (admins only)."""
    redirect = require_login(request)
    if redirect:
        return redirect
    if not request.session.get("is_admin"):
        return HTMLResponse("Admins only.", status_code=403)

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM tbl_slp WHERE slp_id = %s", (slp_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return HTMLResponse(f"Cannot delete: {str(e)}", status_code=400)

    cur.close()
    conn.close()
    return RedirectResponse(url="/inventory/slp", status_code=303)
