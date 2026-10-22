"""Creating records: the "New material / coating / SLP / coin cell / MLP" forms.

Each record type has a GET (show the form) and a POST (check and save it).
The plain POST /materials, /coatings, ... endpoints are the older JSON versions
that take query parameters; the website itself uses the /new forms.
Templates: new_material.html, new_coating.html, new_slp.html, new_coincell.html, new_mlp.html.
"""

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse

from core.auth import require_login
from core.db import get_connection
from core.templates import templates
from services.coa import CoaError, MAX_COA_BYTES, detect_kind, material_summaries, save_coa
from services.forms import clean_optional_fields, coating_electrode, form_state, insert_record, load_form_options, record_exists

router = APIRouter()


# --- Materials ---------------------------------------------------------------

@router.get("/materials/new", response_class=HTMLResponse)
def new_material_form(request: Request):
    """New material form."""
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("new_material.html", {"request": request})


@router.post("/materials/new", response_class=HTMLResponse)
def submit_material_form(request: Request, material_id: str = Form(...), chemistry: str = Form(...), supplier: str = Form(...),
                         date_received: str = Form(None), quantity_kg: str = Form(None), location: str = Form(None),
                         availability: str = Form(None), notes: str = Form(None),
                         coa: UploadFile = File(None)):
    """Check and save a new material (ID must be uppercase and start with CAT- or AN-).
    An optional COA (.pdf/.docx/.doc) is checked first and attached once the material exists."""
    redirect = require_login(request)
    if redirect:
        return redirect
    required = {"material_id": material_id.strip(), "chemistry": chemistry.strip(), "supplier": supplier.strip()}
    optional = {"date_received": date_received, "quantity_kg": quantity_kg, "location": location,
                "availability": availability, "notes": notes}
    form = form_state(required, optional)
    error = None
    success = None

    material_id = required["material_id"]
    coa_data = coa.file.read(MAX_COA_BYTES + 1) if coa and coa.filename else None
    coa_problem = coa_warning = created = None
    if coa_data is not None:
        try:
            detect_kind(coa.filename, coa_data)       # reject a bad COA before saving anything
        except CoaError as e:
            coa_problem = str(e)

    if coa_problem:
        error = f"COA not accepted: {coa_problem} Nothing was saved."
    elif not all(required.values()):
        error = "Material ID, chemistry and supplier are required."
    elif material_id != material_id.upper():
        error = f"Material ID must be uppercase. Try: {material_id.upper()}"
    elif not (material_id.startswith("CAT-") or material_id.startswith("AN-")):
        error = "Material ID must start with 'CAT-' or 'AN-'."
    else:
        extras, error = clean_optional_fields(optional, numeric_fields={"quantity_kg"})
        if not error:
            error = insert_record("tbl_materials", {**required, **extras})
        if not error:
            success, form = material_id, {}
            if coa_data is not None:
                try:
                    save_coa(material_id, coa.filename, coa_data, request.session.get("full_name"))
                except CoaError as e:
                    coa_warning = f"Material saved, but the COA wasn't: {e}"
            created = material_summaries([material_id])

    return templates.TemplateResponse("new_material.html", {"request": request, "error": error, "success": success,
                                                            "form": form, "created": created, "coa_warning": coa_warning})

@router.post("/materials")
def create_material(material_id: str, chemistry: str, supplier: str):
    """Older JSON endpoint: add a material from query parameters."""
    material_id = material_id.strip()
    chemistry = chemistry.strip()
    supplier = supplier.strip()

    if not material_id or not chemistry or not supplier:
        return {"status": "error", "detail": "All fields are required and cannot be blank."}

    if material_id != material_id.upper():
        return {"status": "error", "detail": f"Material ID must be uppercase. Try: {material_id.upper()}"}

    if not (material_id.startswith("CAT-") or material_id.startswith("AN-")):
        return {"status": "error", "detail": "Material ID must start with 'CAT-' or 'AN-'."}

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO tbl_materials (material_id, chemistry, supplier) VALUES (%s, %s, %s)",
            (material_id, chemistry, supplier)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return {"status": "error", "detail": str(e)}
    cur.close()
    conn.close()
    return {"status": "created", "material_id": material_id}

# --- Coatings ----------------------------------------------------------------

@router.post("/coatings")
def create_coating(coating_id: str, material_id: str, project: str, made_by: str):
    """Older JSON endpoint: add a coating from query parameters."""
    coating_id = coating_id.strip()
    material_id = material_id.strip()
    project = project.strip()
    made_by = made_by.strip()

    if not coating_id or not material_id or not project or not made_by:
        return {"status": "error", "detail": "All fields are required and cannot be blank."}

    if coating_id != coating_id.upper():
        return {"status": "error", "detail": f"Coating ID must be uppercase. Try: {coating_id.upper()}"}

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO tbl_coating (coating_id, material_id, project, made_by) VALUES (%s, %s, %s, %s)",
            (coating_id, material_id, project, made_by)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return {"status": "error", "detail": str(e)}
    cur.close()
    conn.close()
    return {"status": "created", "coating_id": coating_id}

@router.get("/coatings/new", response_class=HTMLResponse)
def new_coating_form(request: Request):
    """New coating form."""
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("new_coating.html", {"request": request, **load_form_options()})


@router.post("/coatings/new", response_class=HTMLResponse)
def submit_coating_form(request: Request, coating_id: str = Form(...), material_id: str = Form(...), project: str = Form(...), made_by: str = Form(...),
                        coating_date: str = Form(None), coat_weight_gsm: str = Form(None), porosity: str = Form(None), notes: str = Form(None)):
    """Check and save a new coating (its material must already exist)."""
    redirect = require_login(request)
    if redirect:
        return redirect
    required = {"coating_id": coating_id.strip(), "material_id": material_id.strip(), "project": project.strip(), "made_by": made_by.strip()}
    optional = {"coating_date": coating_date, "coat_weight_gsm": coat_weight_gsm, "porosity": porosity, "notes": notes}
    form = form_state(required, optional)
    error = None
    success = None

    coating_id = required["coating_id"]
    if not all(required.values()):
        error = "Coating ID, material ID, project and made by are required."
    elif coating_id != coating_id.upper():
        error = f"Coating ID must be uppercase. Try: {coating_id.upper()}"
    elif not record_exists("tbl_materials", "material_id", required["material_id"]):
        error = f"Material {required['material_id']} doesn't exist yet. Pick one from the list or create it first."
    else:
        extras, error = clean_optional_fields(optional, numeric_fields={"coat_weight_gsm", "porosity"})
        if not error:
            error = insert_record("tbl_coating", {**required, **extras})
        if not error:
            success, form = coating_id, {}

    return templates.TemplateResponse("new_coating.html", {"request": request, "error": error, "success": success, "form": form, **load_form_options()})

# --- SLP cells ---------------------------------------------------------------

@router.post("/slp")
def create_slp(slp_id: str, coating_id: str, project: str, made_by: str):
    """Older JSON endpoint: add an SLP cell from query parameters."""
    slp_id = slp_id.strip()
    coating_id = coating_id.strip()
    project = project.strip()
    made_by = made_by.strip()

    if not slp_id or not coating_id or not project or not made_by:
        return {"status": "error", "detail": "All fields are required and cannot be blank."}

    if slp_id != slp_id.upper():
        return {"status": "error", "detail": f"SLP ID must be uppercase. Try: {slp_id.upper()}"}

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO tbl_slp (slp_id, coating_id, project, made_by) VALUES (%s, %s, %s, %s)",
            (slp_id, coating_id, project, made_by)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return {"status": "error", "detail": str(e)}
    cur.close()
    conn.close()
    return {"status": "created", "slp_id": slp_id}

@router.get("/slp/new", response_class=HTMLResponse)
def new_slp_form(request: Request):
    """New SLP cell form."""
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("new_slp.html", {"request": request, **load_form_options()})

@router.post("/slp/new", response_class=HTMLResponse)
def submit_slp_form(request: Request, slp_id: str = Form(...), coating_id: str = Form(...), project: str = Form(...), made_by: str = Form(...),
                    formation_capacity: str = Form(None), date_made: str = Form(None), electrolyte: str = Form(None),
                    np_ratio: str = Form(None), notes: str = Form(None)):
    """Check and save a new SLP cell (its coating must already exist)."""
    redirect = require_login(request)
    if redirect:
        return redirect
    required = {"slp_id": slp_id.strip(), "coating_id": coating_id.strip(), "project": project.strip(), "made_by": made_by.strip()}
    optional = {"date_made": date_made, "electrolyte": electrolyte, "formation_capacity": formation_capacity,
                "np_ratio": np_ratio, "notes": notes}
    form = form_state(required, optional)
    error = None
    success = None

    slp_id = required["slp_id"]
    if not all(required.values()):
        error = "SLP ID, coating ID, project and made by are required."
    elif slp_id != slp_id.upper():
        error = f"SLP ID must be uppercase. Try: {slp_id.upper()}"
    elif not record_exists("tbl_coating", "coating_id", required["coating_id"]):
        error = f"Coating {required['coating_id']} doesn't exist yet. Pick one from the list or create it first."
    else:
        extras, error = clean_optional_fields(optional, numeric_fields={"formation_capacity", "np_ratio"})
        if not error:
            error = insert_record("tbl_slp", {**required, **extras})
        if not error:
            success, form = slp_id, {}

    return templates.TemplateResponse("new_slp.html", {"request": request, "error": error, "success": success, "form": form, **load_form_options()})

# --- Coin cells --------------------------------------------------------------

@router.post("/coincell")
def create_coincell(coincell_id: str, coating_id: str, project: str, made_by: str):
    """Older JSON endpoint: add a coin cell from query parameters."""
    coincell_id = coincell_id.strip()
    coating_id = coating_id.strip()
    project = project.strip()
    made_by = made_by.strip()

    if not coincell_id or not coating_id or not project or not made_by:
        return {"status": "error", "detail": "All fields are required and cannot be blank."}

    if coincell_id != coincell_id.upper():
        return {"status": "error", "detail": f"CoinCell ID must be uppercase. Try: {coincell_id.upper()}"}

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO tbl_coincell (coincell_id, coating_id, project, made_by) VALUES (%s, %s, %s, %s)",
            (coincell_id, coating_id, project, made_by)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return {"status": "error", "detail": str(e)}
    cur.close()
    conn.close()
    return {"status": "created", "coincell_id": coincell_id}

@router.get("/coincell/new", response_class=HTMLResponse)
def new_coincell_form(request: Request):
    """New coin cell form."""
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("new_coincell.html", {"request": request, **load_form_options()})


@router.post("/coincell/new", response_class=HTMLResponse)
def submit_coincell_form(request: Request, coincell_id: str = Form(...), coating_id: str = Form(...), project: str = Form(...), made_by: str = Form(...),
                         date_made: str = Form(None), electrolyte: str = Form(None), formation_capacity: str = Form(None),
                         cell_type: str = Form(None), gsm: str = Form(None), notes: str = Form(None)):
    """Check and save a new coin cell (its coating must already exist)."""
    redirect = require_login(request)
    if redirect:
        return redirect
    required = {"coincell_id": coincell_id.strip(), "coating_id": coating_id.strip(), "project": project.strip(), "made_by": made_by.strip()}
    optional = {"date_made": date_made, "electrolyte": electrolyte, "formation_capacity": formation_capacity,
                "cell_type": cell_type, "gsm": gsm, "notes": notes}
    form = form_state(required, optional)
    error = None
    success = None

    coincell_id = required["coincell_id"]
    if not all(required.values()):
        error = "Coin cell ID, coating ID, project and made by are required."
    elif coincell_id != coincell_id.upper():
        error = f"Coin Cell ID must be uppercase. Try: {coincell_id.upper()}"
    elif not record_exists("tbl_coating", "coating_id", required["coating_id"]):
        error = f"Coating {required['coating_id']} doesn't exist yet. Pick one from the list or create it first."
    else:
        extras, error = clean_optional_fields(optional, numeric_fields={"formation_capacity", "gsm"})
        if not error:
            error = insert_record("tbl_coincell", {**required, **extras})
        if not error:
            success, form = coincell_id, {}

    return templates.TemplateResponse("new_coincell.html", {"request": request, "error": error, "success": success, "form": form, **load_form_options()})

# --- MLP cells ---------------------------------------------------------------

@router.post("/mlp")
def create_mlp(mlp_id: str, cat_coating_id: str, an_coating_id: str, project: str):
    """Older JSON endpoint: add an MLP cell from query parameters."""
    mlp_id = mlp_id.strip()
    cat_coating_id = cat_coating_id.strip()
    an_coating_id = an_coating_id.strip()
    project = project.strip()

    if not mlp_id or not cat_coating_id or not an_coating_id or not project:
        return {"status": "error", "detail": "All fields are required and cannot be blank."}

    if mlp_id != mlp_id.upper():
        return {"status": "error", "detail": f"MLP ID must be uppercase. Try: {mlp_id.upper()}"}

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO tbl_mlp (mlp_id, cat_coating_id, an_coating_id, project) VALUES (%s, %s, %s, %s)",
            (mlp_id, cat_coating_id, an_coating_id, project)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return {"status": "error", "detail": str(e)}
    cur.close()
    conn.close()
    return {"status": "created", "mlp_id": mlp_id}

@router.get("/mlp/new", response_class=HTMLResponse)
def new_mlp_form(request: Request):
    """New MLP cell form."""
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("new_mlp.html", {"request": request, **load_form_options()})


@router.post("/mlp/new", response_class=HTMLResponse)
def submit_mlp_form(request: Request, mlp_id: str = Form(...), cat_coating_id: str = Form(...), an_coating_id: str = Form(...), project: str = Form(...),
                    date_made: str = Form(None), electrolyte: str = Form(None), cell_capacity: str = Form(None),
                    ac_area_ratio: str = Form(None)):
    """Check and save a new MLP cell (needs one cathode and one anode coating)."""
    redirect = require_login(request)
    if redirect:
        return redirect
    required = {"mlp_id": mlp_id.strip(), "cat_coating_id": cat_coating_id.strip(), "an_coating_id": an_coating_id.strip(), "project": project.strip()}
    optional = {"date_made": date_made, "electrolyte": electrolyte, "cell_capacity": cell_capacity, "ac_area_ratio": ac_area_ratio}
    form = form_state(required, optional)
    error = None
    success = None

    mlp_id = required["mlp_id"]
    if not all(required.values()):
        error = "MLP ID, both coating IDs and project are required."
    elif mlp_id != mlp_id.upper():
        error = f"MLP ID must be uppercase. Try: {mlp_id.upper()}"
    elif coating_electrode(required["cat_coating_id"]) != "cathode":
        error = f"{required['cat_coating_id']} isn't an existing cathode (CAT-) coating."
    elif coating_electrode(required["an_coating_id"]) != "anode":
        error = f"{required['an_coating_id']} isn't an existing anode (AN-) coating."
    else:
        extras, error = clean_optional_fields(optional, numeric_fields={"cell_capacity", "ac_area_ratio"})
        if not error:
            error = insert_record("tbl_mlp", {**required, **extras})
        if not error:
            success, form = mlp_id, {}

    return templates.TemplateResponse("new_mlp.html", {"request": request, "error": error, "success": success, "form": form, **load_form_options()})
