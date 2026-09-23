from fastapi import FastAPI, Request, Form
import psycopg2
import bcrypt
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from HAZbot import ask_ai_for_sql
import pandas as pd
from fastapi import UploadFile, File
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import RedirectResponse
import qrcode
import io
import base64
import os
 
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "dev-secret-change-this-later"))
templates = Jinja2Templates(directory="templates")
def get_connection():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)
    return psycopg2.connect(dbname="bmac", user="hazma", host="localhost")
 
def require_login(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login", status_code=303)
    return None
 
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})
 
@app.get("/materials/new", response_class=HTMLResponse)
def new_material_form(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("new_material.html", {"request": request})
 
@app.post("/materials/new", response_class=HTMLResponse)
def submit_material_form(request: Request, material_id: str = Form(...), chemistry: str = Form(...), supplier: str = Form(...)):
    redirect = require_login(request)
    if redirect:
        return redirect
    material_id = material_id.strip()
    chemistry = chemistry.strip()
    supplier = supplier.strip()
 
    error = None
    success = None
 
    if not material_id or not chemistry or not supplier:
        error = "All fields are required and cannot be blank."
    elif material_id != material_id.upper():
        error = f"Material ID must be uppercase. Try: {material_id.upper()}"
    elif not (material_id.startswith("CAT-") or material_id.startswith("AN-")):
        error = "Material ID must start with 'CAT-' or 'AN-'."
    else:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO tbl_materials (material_id, chemistry, supplier) VALUES (%s, %s, %s)",
                (material_id, chemistry, supplier)
            )
            conn.commit()
            success = material_id
        except Exception as e:
            conn.rollback()
            error = str(e)
        cur.close()
        conn.close()
 
    return templates.TemplateResponse("new_material.html", {"request": request, "error": error, "success": success})
 
@app.post("/materials")
def create_material(material_id: str, chemistry: str, supplier: str):
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
 
@app.post("/coatings")
def create_coating(coating_id: str, material_id: str, project: str, made_by: str):
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
 
@app.get("/coatings/new", response_class=HTMLResponse)
def new_coating_form(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("new_coating.html", {"request": request})
 
 
@app.post("/coatings/new", response_class=HTMLResponse)
def submit_coating_form(request: Request, coating_id: str = Form(...), material_id: str = Form(...), project: str = Form(...), made_by: str = Form(...)):
    redirect = require_login(request)
    if redirect:
        return redirect
    coating_id = coating_id.strip()
    material_id = material_id.strip()
    project = project.strip()
    made_by = made_by.strip()
 
    error = None
    success = None
 
    if not coating_id or not material_id or not project or not made_by:
        error = "All fields are required and cannot be blank."
    elif coating_id != coating_id.upper():
        error = f"Coating ID must be uppercase. Try: {coating_id.upper()}"
    else:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO tbl_coating (coating_id, material_id, project, made_by) VALUES (%s, %s, %s, %s)",
                (coating_id, material_id, project, made_by)
            )
            conn.commit()
            success = coating_id
        except Exception as e:
            conn.rollback()
            error = str(e)
        cur.close()
        conn.close()
 
    return templates.TemplateResponse("new_coating.html", {"request": request, "error": error, "success": success})
 
@app.post("/slp")
def create_slp(slp_id: str, coating_id: str, project: str, made_by: str):
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
 
@app.get("/slp/new", response_class=HTMLResponse)
def new_slp_form(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("new_slp.html", {"request": request})
 
@app.post("/slp/new", response_class=HTMLResponse)
def submit_slp_form(request: Request, slp_id: str = Form(...), coating_id: str = Form(...), project: str = Form(...), made_by: str = Form(...), formation_capacity: str = Form(None)):
    redirect = require_login(request)
    if redirect:
        return redirect
    slp_id = slp_id.strip()
    coating_id = coating_id.strip()
    project = project.strip()
    made_by = made_by.strip()
 
    error = None
    success = None
 
    if not slp_id or not coating_id or not project or not made_by:
        error = "All fields are required and cannot be blank."
    elif slp_id != slp_id.upper():
        error = f"SLP ID must be uppercase. Try: {slp_id.upper()}"
    else:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO tbl_slp (slp_id, coating_id, project, made_by, formation_capacity) VALUES (%s, %s, %s, %s, %s)",
                (slp_id, coating_id, project, made_by, formation_capacity if formation_capacity else None)
            )
            conn.commit()
            success = slp_id
        except Exception as e:
            conn.rollback()
            error = str(e)
        cur.close()
        conn.close()
 
    return templates.TemplateResponse("new_slp.html", {"request": request, "error": error, "success": success})
 
@app.post("/coincell")
def create_coincell(coincell_id: str, coating_id: str, project: str, made_by: str):
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
 
@app.get("/coincell/new", response_class=HTMLResponse)
def new_coincell_form(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("new_coincell.html", {"request": request})
 
 
@app.post("/coincell/new", response_class=HTMLResponse)
def submit_coincell_form(request: Request, coincell_id: str = Form(...), coating_id: str = Form(...), project: str = Form(...), made_by: str = Form(...)):
    redirect = require_login(request)
    if redirect:
        return redirect
    coincell_id = coincell_id.strip()
    coating_id = coating_id.strip()
    project = project.strip()
    made_by = made_by.strip()
 
    error = None
    success = None
 
    if not coincell_id or not coating_id or not project or not made_by:
        error = "All fields are required and cannot be blank."
    elif coincell_id != coincell_id.upper():
        error = f"Coin Cell ID must be uppercase. Try: {coincell_id.upper()}"
    else:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO tbl_coincell (coincell_id, coating_id, project, made_by) VALUES (%s, %s, %s, %s)",
                (coincell_id, coating_id, project, made_by)
            )
            conn.commit()
            success = coincell_id
        except Exception as e:
            conn.rollback()
            error = str(e)
        cur.close()
        conn.close()
 
    return templates.TemplateResponse("new_coincell.html", {"request": request, "error": error, "success": success})
 
@app.post("/mlp")
def create_mlp(mlp_id: str, cat_coating_id: str, an_coating_id: str, project: str):
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
 
@app.get("/mlp/new", response_class=HTMLResponse)
def new_mlp_form(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("new_mlp.html", {"request": request})
 
 
@app.post("/mlp/new", response_class=HTMLResponse)
def submit_mlp_form(request: Request, mlp_id: str = Form(...), cat_coating_id: str = Form(...), an_coating_id: str = Form(...), project: str = Form(...)):
    redirect = require_login(request)
    if redirect:
        return redirect
    mlp_id = mlp_id.strip()
    cat_coating_id = cat_coating_id.strip()
    an_coating_id = an_coating_id.strip()
    project = project.strip()
 
    error = None
    success = None
 
    if not mlp_id or not cat_coating_id or not an_coating_id or not project:
        error = "All fields are required and cannot be blank."
    elif mlp_id != mlp_id.upper():
        error = f"MLP ID must be uppercase. Try: {mlp_id.upper()}"
    else:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO tbl_mlp (mlp_id, cat_coating_id, an_coating_id, project) VALUES (%s, %s, %s, %s)",
                (mlp_id, cat_coating_id, an_coating_id, project)
            )
            conn.commit()
            success = mlp_id
        except Exception as e:
            conn.rollback()
            error = str(e)
        cur.close()
        conn.close()
 
    return templates.TemplateResponse("new_mlp.html", {"request": request, "error": error, "success": success})
 
@app.get("/directory", response_class=HTMLResponse)
def directory(request: Request, record_id: str = None):
    record = None
    record_type = None
    searched = record_id is not None
 
    if record_id:
        record_type = detect_record_type(record_id)
        conn = get_connection()
        cur = conn.cursor()
 
        if record_type == "material":
            cur.execute(
                "SELECT chemistry, supplier, date_received, quantity_kg, location, availability "
                "FROM tbl_materials WHERE material_id = %s",
                (record_id,)
            )
            columns = ["chemistry", "supplier", "date_received", "quantity_kg", "location", "availability"]
            row = cur.fetchone()
            if row:
                record = dict(zip(columns, row))
                cur.execute("SELECT coating_id FROM tbl_coating WHERE material_id = %s", (record_id,))
                downstream = [f"Coating: {r[0]}" for r in cur.fetchall()]
                record["_chain"] = downstream if downstream else ["No downstream records yet"]
 
        elif record_type == "coating":
            cur.execute(
                "SELECT material_id, project, coating_date, made_by, coat_weight_gsm, porosity "
                "FROM tbl_coating WHERE coating_id = %s",
                (record_id,)
            )
            columns = ["material_id", "project", "coating_date", "made_by", "coat_weight_gsm", "porosity"]
            row = cur.fetchone()
            if row:
                record = dict(zip(columns, row))
 
                cur.execute("SELECT chemistry FROM tbl_materials WHERE material_id = %s", (record["material_id"],))
                mat = cur.fetchone()
                upstream = [f"Material: {record['material_id']} ({mat[0] if mat else '?'})"]
 
                downstream = []
                cur.execute("SELECT slp_id FROM tbl_slp WHERE coating_id = %s", (record_id,))
                downstream += [f"SLP: {r[0]}" for r in cur.fetchall()]
                cur.execute("SELECT coincell_id FROM tbl_coincell WHERE coating_id = %s", (record_id,))
                downstream += [f"CoinCell: {r[0]}" for r in cur.fetchall()]
                cur.execute("SELECT mlp_id FROM tbl_mlp WHERE cat_coating_id = %s OR an_coating_id = %s", (record_id, record_id))
                downstream += [f"MLP: {r[0]}" for r in cur.fetchall()]
 
                record["_chain"] = upstream + (downstream if downstream else ["No downstream records yet"])
 
        elif record_type == "slp":
            cur.execute(
                "SELECT coating_id, project, date_made, made_by, electrolyte, formation_capacity "
                "FROM tbl_slp WHERE slp_id = %s",
                (record_id,)
            )
            columns = ["coating_id", "project", "date_made", "made_by", "electrolyte", "formation_capacity"]
            row = cur.fetchone()
            if row:
                record = dict(zip(columns, row))
                cur.execute("SELECT material_id FROM tbl_coating WHERE coating_id = %s", (record["coating_id"],))
                mat = cur.fetchone()
                record["_chain"] = [f"Coating: {record['coating_id']}", f"Material: {mat[0] if mat else '?'}"]
 
        elif record_type == "coincell":
            cur.execute(
                "SELECT coating_id, project, date_made, made_by, electrolyte, formation_capacity "
                "FROM tbl_coincell WHERE coincell_id = %s",
                (record_id,)
            )
            columns = ["coating_id", "project", "date_made", "made_by", "electrolyte", "formation_capacity"]
            row = cur.fetchone()
            if row:
                record = dict(zip(columns, row))
                cur.execute("SELECT material_id FROM tbl_coating WHERE coating_id = %s", (record["coating_id"],))
                mat = cur.fetchone()
                record["_chain"] = [f"Coating: {record['coating_id']}", f"Material: {mat[0] if mat else '?'}"]
 
        elif record_type == "mlp":
            cur.execute(
                "SELECT cat_coating_id, an_coating_id, project, date_made, cell_capacity "
                "FROM tbl_mlp WHERE mlp_id = %s",
                (record_id,)
            )
            columns = ["cat_coating_id", "an_coating_id", "project", "date_made", "cell_capacity"]
            row = cur.fetchone()
            if row:
                record = dict(zip(columns, row))
                chain = []
                for label, cid in (("Cathode coating", record["cat_coating_id"]), ("Anode coating", record["an_coating_id"])):
                    cur.execute("SELECT material_id FROM tbl_coating WHERE coating_id = %s", (cid,))
                    mat = cur.fetchone()
                    chain.append(f"{label}: {cid} (material: {mat[0] if mat else '?'})")
                record["_chain"] = chain
 
        else:
            columns = []
 
        if record_type and record_type not in ("coating", "material", "slp", "coincell", "mlp"):
            row = cur.fetchone()
            if row:
                record = dict(zip(columns, row))
 
        cur.close()
        conn.close()
 
    return templates.TemplateResponse(
        "search.html",
        {"request": request, "record": record, "record_id": record_id, "record_type": record_type, "searched": searched}
    )
 
def detect_record_type(record_id: str) -> str:
    rid = record_id.upper()
    if "-SLP-" in rid:
        return "slp"
    if "MLP-" in rid:
        return "mlp"
    if "-CC" in rid:
        return "coincell"
    if "-C0" in rid or "-C1" in rid:
        return "coating"
    if rid.startswith("CAT") or rid.startswith("AN"):
        return "material"
    return None
 
@app.get("/inventory/materials", response_class=HTMLResponse)
def inventory_materials(request: Request):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT material_id, chemistry, supplier, date_received, quantity_kg, location, availability "
        "FROM tbl_materials ORDER BY material_id"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
 
    columns = ["Material ID", "Chemistry", "Supplier", "Date Received", "Quantity (kg)", "Location", "Availability"]
    return templates.TemplateResponse(
        "inventory.html",
        {"request": request, "title": "Materials", "columns": columns, "rows": rows,
         "new_url": "/materials/new", "bulk_url": "/materials/bulk-upload"}
    )
 
@app.get("/inventory/coatings", response_class=HTMLResponse)
def inventory_coatings(request: Request):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT coating_id, material_id, project, coating_date, made_by, coat_weight_gsm, porosity "
        "FROM tbl_coating ORDER BY coating_id"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    columns = ["Coating ID", "Material ID", "Project", "Coating Date", "Made By", "GSM", "Porosity"]
    return templates.TemplateResponse(
        "inventory.html",
        {"request": request, "title": "Coatings", "columns": columns, "rows": rows,
         "new_url": "/coatings/new", "bulk_url": "/coatings/bulk-upload"}
    )
 
 
@app.get("/inventory/slp", response_class=HTMLResponse)
def inventory_slp(request: Request):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT slp_id, coating_id, project, date_made, made_by, electrolyte, formation_capacity "
        "FROM tbl_slp ORDER BY slp_id"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    columns = ["SLP ID", "Coating ID", "Project", "Date Made", "Made By", "Electrolyte", "Formation Capacity"]
    return templates.TemplateResponse(
        "inventory.html",
        {"request": request, "title": "SLP Cells", "columns": columns, "rows": rows,
         "new_url": "/slp/new", "bulk_url": "/slp/bulk-upload"}
    )
 
@app.get("/inventory/coincell", response_class=HTMLResponse)
def inventory_coincell(request: Request):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT coincell_id, coating_id, project, date_made, made_by, electrolyte, formation_capacity "
        "FROM tbl_coincell ORDER BY coincell_id"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    columns = ["Coin Cell ID", "Coating ID", "Project", "Date Made", "Made By", "Electrolyte", "Formation Capacity"]
    return templates.TemplateResponse(
        "inventory.html",
        {"request": request, "title": "Coin Cells", "columns": columns, "rows": rows,
         "new_url": "/coincell/new", "bulk_url": "/coincell/bulk-upload"}
    )
 
 
@app.get("/inventory/mlp", response_class=HTMLResponse)
def inventory_mlp(request: Request):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT mlp_id, cat_coating_id, an_coating_id, project, date_made, cell_capacity "
        "FROM tbl_mlp ORDER BY mlp_id"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    columns = ["MLP ID", "Cathode Coating", "Anode Coating", "Project", "Date Made", "Cell Capacity"]
    return templates.TemplateResponse(
        "inventory.html",
        {"request": request, "title": "MLP Cells", "columns": columns, "rows": rows,
         "new_url": "/mlp/new", "bulk_url": "/mlp/bulk-upload"}
    )
 
@app.get("/api/chart/formation-capacity")
def chart_formation_capacity():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT slp_id, formation_capacity FROM tbl_slp WHERE formation_capacity IS NOT NULL ORDER BY slp_id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
 
    labels = [r[0] for r in rows]
    values = [float(r[1]) for r in rows]
    return JSONResponse({"labels": labels, "values": values})
 
@app.get("/chart", response_class=HTMLResponse)
def chart_page(request: Request):
    return templates.TemplateResponse("chart.html", {"request": request})
 
@app.get("/materials/bulk-upload", response_class=HTMLResponse)
def bulk_upload_form(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("bulk_upload.html", {"request": request})
 
 
@app.post("/materials/bulk-upload", response_class=HTMLResponse)
async def bulk_upload_materials(request: Request, file: UploadFile = File(...)):
    redirect = require_login(request)
    if redirect:
        return redirect
    contents = await file.read()
 
    if file.filename.endswith(".csv"):
        df = pd.read_csv(pd.io.common.BytesIO(contents))
    else:
        df = pd.read_excel(pd.io.common.BytesIO(contents))
 
    success = []
    failed = []
 
    conn = get_connection()
    cur = conn.cursor()
 
    for i, row in df.iterrows():
        row_num = i + 2  # +2 accounts for the header row and 0-indexing
 
        material_id = str(row.get("material_id", "")).strip()
        chemistry = str(row.get("chemistry", "")).strip()
        supplier = str(row.get("supplier", "")).strip()
 
        if not material_id or not chemistry or not supplier or material_id == "nan":
            failed.append({"row": row_num, "reason": "Missing required field(s)."})
            continue
 
        if material_id != material_id.upper():
            failed.append({"row": row_num, "reason": f"'{material_id}' is not uppercase."})
            continue
 
        if not (material_id.startswith("CAT-") or material_id.startswith("AN-")):
            failed.append({"row": row_num, "reason": f"'{material_id}' must start with CAT- or AN-."})
            continue
 
        try:
            cur.execute(
                "INSERT INTO tbl_materials (material_id, chemistry, supplier) VALUES (%s, %s, %s)",
                (material_id, chemistry, supplier)
            )
            conn.commit()
            success.append(material_id)
        except Exception as e:
            conn.rollback()
            failed.append({"row": row_num, "reason": str(e)})
 
    cur.close()
    conn.close()
 
    return templates.TemplateResponse(
        "bulk_upload.html",
        {"request": request, "results": {"success": success, "failed": failed}}
    )
 
@app.get("/coatings/bulk-upload", response_class=HTMLResponse)
def bulk_upload_coating_form(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("bulk_upload_coating.html", {"request": request})
 
 
@app.post("/coatings/bulk-upload", response_class=HTMLResponse)
async def bulk_upload_coatings(request: Request, file: UploadFile = File(...)):
    redirect = require_login(request)
    if redirect:
        return redirect
    contents = await file.read()
 
    if file.filename.endswith(".csv"):
        df = pd.read_csv(pd.io.common.BytesIO(contents))
    else:
        df = pd.read_excel(pd.io.common.BytesIO(contents))
 
    success = []
    failed = []
 
    conn = get_connection()
    cur = conn.cursor()
 
    for i, row in df.iterrows():
        row_num = i + 2
 
        coating_id = str(row.get("coating_id", "")).strip()
        material_id = str(row.get("material_id", "")).strip()
        project = str(row.get("project", "")).strip()
        made_by = str(row.get("made_by", "")).strip()
 
        if not coating_id or not material_id or not project or not made_by or coating_id == "nan":
            failed.append({"row": row_num, "reason": "Missing required field(s)."})
            continue
 
        if coating_id != coating_id.upper():
            failed.append({"row": row_num, "reason": f"'{coating_id}' is not uppercase."})
            continue
 
        try:
            cur.execute(
                "INSERT INTO tbl_coating (coating_id, material_id, project, made_by) VALUES (%s, %s, %s, %s)",
                (coating_id, material_id, project, made_by)
            )
            conn.commit()
            success.append(coating_id)
        except Exception as e:
            conn.rollback()
            failed.append({"row": row_num, "reason": str(e)})
 
    cur.close()
    conn.close()
 
    return templates.TemplateResponse(
        "bulk_upload_coating.html",
        {"request": request, "results": {"success": success, "failed": failed}}
    )
 
@app.get("/slp/bulk-upload", response_class=HTMLResponse)
def bulk_upload_slp_form(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("bulk_upload_slp.html", {"request": request})
 
 
@app.post("/slp/bulk-upload", response_class=HTMLResponse)
async def bulk_upload_slp(request: Request, file: UploadFile = File(...)):
    redirect = require_login(request)
    if redirect:
        return redirect
    contents = await file.read()
    df = pd.read_csv(pd.io.common.BytesIO(contents)) if file.filename.endswith(".csv") else pd.read_excel(pd.io.common.BytesIO(contents))
 
    success = []
    failed = []
    conn = get_connection()
    cur = conn.cursor()
 
    for i, row in df.iterrows():
        row_num = i + 2
        slp_id = str(row.get("slp_id", "")).strip()
        coating_id = str(row.get("coating_id", "")).strip()
        project = str(row.get("project", "")).strip()
        made_by = str(row.get("made_by", "")).strip()
        fc_raw = row.get("formation_capacity", None)
        try:
            formation_capacity = None if pd.isna(fc_raw) else float(fc_raw)
        except (ValueError, TypeError):
            failed.append({"row": row_num, "reason": f"'{fc_raw}' is not a valid number for formation_capacity."})
            continue
 
        if not slp_id or not coating_id or not project or not made_by or slp_id == "nan":
            failed.append({"row": row_num, "reason": "Missing required field(s)."})
            continue
        if slp_id != slp_id.upper():
            failed.append({"row": row_num, "reason": f"'{slp_id}' is not uppercase."})
            continue
 
        try:
            cur.execute(
                "INSERT INTO tbl_slp (slp_id, coating_id, project, made_by, formation_capacity) VALUES (%s, %s, %s, %s, %s)",
                (slp_id, coating_id, project, made_by, formation_capacity)
            )
            conn.commit()
            success.append(slp_id)
        except Exception as e:
            conn.rollback()
            failed.append({"row": row_num, "reason": str(e)})
 
    cur.close()
    conn.close()
    return templates.TemplateResponse("bulk_upload_slp.html", {"request": request, "results": {"success": success, "failed": failed}})

@app.get("/coincell/bulk-upload", response_class=HTMLResponse)
def bulk_upload_coincell_form(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("bulk_upload_coincell.html", {"request": request})
 
@app.post("/coincell/bulk-upload", response_class=HTMLResponse)
async def bulk_upload_coincell(request: Request, file: UploadFile = File(...)):
    redirect = require_login(request)
    if redirect:
        return redirect
    contents = await file.read()
    df = pd.read_csv(pd.io.common.BytesIO(contents)) if file.filename.endswith(".csv") else pd.read_excel(pd.io.common.BytesIO(contents))

    success = []
    failed = []
    conn = get_connection()
    cur = conn.cursor()

    for i, row in df.iterrows():
        row_num = i + 2
        coincell_id = str(row.get("coincell_id", "")).strip()
        coating_id = str(row.get("coating_id", "")).strip()
        project = str(row.get("project", "")).strip()
        made_by = str(row.get("made_by", "")).strip()
        notes = str(row.get("Notes", "")).strip()
        if notes == "nan":
            notes = None

        gsm_raw = row.get("GSM", None)
        try:
            gsm = None if pd.isna(gsm_raw) else float(gsm_raw)
        except (ValueError, TypeError):
            failed.append({"row": row_num, "reason": f"'{gsm_raw}' is not a valid number for GSM."})
            continue

        if not coincell_id or not coating_id or not project or not made_by or coincell_id == "nan":
            failed.append({"row": row_num, "reason": "Missing required field(s)."})
            continue
        if coincell_id != coincell_id.upper():
            failed.append({"row": row_num, "reason": f"'{coincell_id}' is not uppercase."})
            continue

        try:
            cur.execute(
                "INSERT INTO tbl_coincell (coincell_id, coating_id, project, made_by, gsm, notes) VALUES (%s, %s, %s, %s, %s, %s)",
                (coincell_id, coating_id, project, made_by, gsm, notes)
            )
            conn.commit()
            success.append(coincell_id)
        except Exception as e:
            conn.rollback()
            failed.append({"row": row_num, "reason": str(e)})

    cur.close()
    conn.close()
    return templates.TemplateResponse("bulk_upload_coincell.html", {"request": request, "results": {"success": success, "failed": failed}})

@app.get("/mlp/bulk-upload", response_class=HTMLResponse)
def bulk_upload_mlp_form(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("bulk_upload_mlp.html", {"request": request})
 
 
@app.post("/mlp/bulk-upload", response_class=HTMLResponse)
async def bulk_upload_mlp(request: Request, file: UploadFile = File(...)):
    redirect = require_login(request)
    if redirect:
        return redirect
    contents = await file.read()
    df = pd.read_csv(pd.io.common.BytesIO(contents)) if file.filename.endswith(".csv") else pd.read_excel(pd.io.common.BytesIO(contents))
 
    success = []
    failed = []
    conn = get_connection()
    cur = conn.cursor()
 
    for i, row in df.iterrows():
        row_num = i + 2
        mlp_id = str(row.get("mlp_id", "")).strip()
        cat_coating_id = str(row.get("cat_coating_id", "")).strip()
        an_coating_id = str(row.get("an_coating_id", "")).strip()
        project = str(row.get("project", "")).strip()
 
        if not mlp_id or not cat_coating_id or not an_coating_id or not project or mlp_id == "nan":
            failed.append({"row": row_num, "reason": "Missing required field(s)."})
            continue
        if mlp_id != mlp_id.upper():
            failed.append({"row": row_num, "reason": f"'{mlp_id}' is not uppercase."})
            continue
 
        try:
            cur.execute(
                "INSERT INTO tbl_mlp (mlp_id, cat_coating_id, an_coating_id, project) VALUES (%s, %s, %s, %s)",
                (mlp_id, cat_coating_id, an_coating_id, project)
            )
            conn.commit()
            success.append(mlp_id)
        except Exception as e:
            conn.rollback()
            failed.append({"row": row_num, "reason": str(e)})
 
    cur.close()
    conn.close()
    return templates.TemplateResponse("bulk_upload_mlp.html", {"request": request, "results": {"success": success, "failed": failed}})
 
@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})
 
 
@app.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, password_hash, full_name, is_admin FROM tbl_users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()
 
    if not user or not bcrypt.checkpw(password.encode(), user[1].encode()):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password."})
 
    request.session["user_id"] = user[0]
    request.session["full_name"] = user[2]
    request.session["is_admin"] = user[3]
 
    return RedirectResponse(url="/", status_code=303)
 
 
@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)
@app.get("/card/{record_id}", response_class=HTMLResponse)
def view_card(request: Request, record_id: str):
    record_type = detect_record_type(record_id)
    if not record_type:
        return HTMLResponse("Unrecognised ID format.", status_code=404)

    # Generate the QR code for THIS card's own URL
    card_url = f"{BASE_URL}/card/{record_id}"
    qr_img = qrcode.make(card_url)
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    qr_base64 = base64.b64encode(buf.getvalue()).decode()

    conn = get_connection()
    cur = conn.cursor()

    record = None
    chain = []

    if record_type == "material":
        cur.execute(
            "SELECT chemistry, supplier, date_received, quantity_kg, location, availability "
            "FROM tbl_materials WHERE material_id = %s", (record_id,)
        )
        row = cur.fetchone()
        if row:
            columns = ["Chemistry", "Supplier", "Date Received", "Quantity (kg)", "Location", "Availability"]
            record = dict(zip(columns, row))
            cur.execute("SELECT coating_id FROM tbl_coating WHERE material_id = %s", (record_id,))
            chain += [f"Coating: {r[0]}" for r in cur.fetchall()]

    elif record_type == "coating":
        cur.execute(
            "SELECT material_id, project, coating_date, made_by, coat_weight_gsm, porosity "
            "FROM tbl_coating WHERE coating_id = %s", (record_id,)
        )
        row = cur.fetchone()
        if row:
            columns = ["Material ID", "Project", "Coating Date", "Made By", "GSM", "Porosity"]
            record = dict(zip(columns, row))
            cur.execute("SELECT slp_id FROM tbl_slp WHERE coating_id = %s", (record_id,))
            chain += [f"SLP: {r[0]}" for r in cur.fetchall()]
            cur.execute("SELECT coincell_id FROM tbl_coincell WHERE coating_id = %s", (record_id,))
            chain += [f"CoinCell: {r[0]}" for r in cur.fetchall()]
            cur.execute("SELECT mlp_id FROM tbl_mlp WHERE cat_coating_id = %s OR an_coating_id = %s", (record_id, record_id))
            chain += [f"MLP: {r[0]}" for r in cur.fetchall()]

    elif record_type == "slp":
        cur.execute(
            "SELECT coating_id, project, date_made, made_by, electrolyte, formation_capacity "
            "FROM tbl_slp WHERE slp_id = %s", (record_id,)
        )
        row = cur.fetchone()
        if row:
            columns = ["Coating ID", "Project", "Date Made", "Made By", "Electrolyte", "Formation Capacity"]
            record = dict(zip(columns, row))
            chain.append(f"Coating: {record['Coating ID']}")

    elif record_type == "coincell":
        cur.execute("SELECT coating_id, project, date_made, made_by, electrolyte, formation_capacity, gsm, notes FROM tbl_coincell WHERE coincell_id = %s", (record_id,))
        row = cur.fetchone()
        if row:
            columns = ["Coating ID", "Project", "Date Made", "Made By", "Electrolyte", "Formation Capacity", "GSM", "Notes"]
            record = dict(zip(columns, [str(v) if v is not None else "N/A" for v in row]))
            chain = [f"Coating: {record['Coating ID']}"]

    elif record_type == "mlp":
        cur.execute(
            "SELECT cat_coating_id, an_coating_id, project, date_made, cell_capacity "
            "FROM tbl_mlp WHERE mlp_id = %s", (record_id,)
        )
        row = cur.fetchone()
        if row:
            columns = ["Cathode Coating", "Anode Coating", "Project", "Date Made", "Cell Capacity"]
            record = dict(zip(columns, row))
            chain.append(f"Cathode: {record['Cathode Coating']}")
            chain.append(f"Anode: {record['Anode Coating']}")

    cur.close()
    conn.close()

    if not record:
        return HTMLResponse("Record not found.", status_code=404)

    return templates.TemplateResponse(
        "card.html",
        {"request": request, "record_id": record_id, "record_type": record_type,
         "record": record, "chain": chain, "qr_base64": qr_base64}
    )
@app.get("/api/card/{record_id}")
def card_data(record_id: str):
    record_type = detect_record_type(record_id)
    if not record_type:
        return JSONResponse({"error": "Unrecognised ID format"}, status_code=404)

    conn = get_connection()
    cur = conn.cursor()
    record = None
    chain = []

    if record_type == "material":
        cur.execute("SELECT chemistry, supplier, date_received, quantity_kg, location, availability FROM tbl_materials WHERE material_id = %s", (record_id,))
        row = cur.fetchone()
        if row:
            columns = ["Chemistry", "Supplier", "Date Received", "Quantity (kg)", "Location", "Availability"]
            record = dict(zip(columns, [str(v) if v is not None else "N/A" for v in row]))
            cur.execute("SELECT coating_id FROM tbl_coating WHERE material_id = %s", (record_id,))
            chain = [f"Coating: {r[0]}" for r in cur.fetchall()]

    elif record_type == "coating":
        cur.execute("SELECT material_id, project, coating_date, made_by, coat_weight_gsm, porosity FROM tbl_coating WHERE coating_id = %s", (record_id,))
        row = cur.fetchone()
        if row:
            columns = ["Material ID", "Project", "Coating Date", "Made By", "GSM", "Porosity"]
            record = dict(zip(columns, [str(v) if v is not None else "N/A" for v in row]))
            cur.execute("SELECT slp_id FROM tbl_slp WHERE coating_id = %s", (record_id,))
            chain += [f"SLP: {r[0]}" for r in cur.fetchall()]
            cur.execute("SELECT coincell_id FROM tbl_coincell WHERE coating_id = %s", (record_id,))
            chain += [f"CoinCell: {r[0]}" for r in cur.fetchall()]
            cur.execute("SELECT mlp_id FROM tbl_mlp WHERE cat_coating_id = %s OR an_coating_id = %s", (record_id, record_id))
            chain += [f"MLP: {r[0]}" for r in cur.fetchall()]

    elif record_type == "slp":
        cur.execute("SELECT coating_id, project, date_made, made_by, electrolyte, formation_capacity FROM tbl_slp WHERE slp_id = %s", (record_id,))
        row = cur.fetchone()
        if row:
            columns = ["Coating ID", "Project", "Date Made", "Made By", "Electrolyte", "Formation Capacity"]
            record = dict(zip(columns, [str(v) if v is not None else "N/A" for v in row]))
            chain = [f"Coating: {record['Coating ID']}"]

    elif record_type == "coincell":
        cur.execute("SELECT coating_id, project, date_made, made_by, electrolyte, formation_capacity, gsm, notes FROM tbl_coincell WHERE coincell_id = %s", (record_id,))
        row = cur.fetchone()
        if row:
            columns = ["Coating ID", "Project", "Date Made", "Made By", "Electrolyte", "Formation Capacity", "GSM", "Notes"]
            record = dict(zip(columns, [str(v) if v is not None else "N/A" for v in row]))
            chain = [f"Coating: {record['Coating ID']}"]

    elif record_type == "mlp":
        cur.execute("SELECT cat_coating_id, an_coating_id, project, date_made, cell_capacity FROM tbl_mlp WHERE mlp_id = %s", (record_id,))
        row = cur.fetchone()
        if row:
            columns = ["Cathode Coating", "Anode Coating", "Project", "Date Made", "Cell Capacity"]
            record = dict(zip(columns, [str(v) if v is not None else "N/A" for v in row]))
            chain = [f"Cathode: {record['Cathode Coating']}", f"Anode: {record['Anode Coating']}"]

    cur.close()
    conn.close()

    if not record:
        return JSONResponse({"error": "Record not found"}, status_code=404)

    return JSONResponse({"record_id": record_id, "record_type": record_type, "record": record, "chain": chain})

    # Generate the QR code for THIS card's own URL
    card_url = f"{BASE_URL}/card/{record_id}"
    qr_img = qrcode.make(card_url)
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    qr_base64 = base64.b64encode(buf.getvalue()).decode()

    # Reuse the same lookup logic as /directory
    conn = get_connection()
    cur = conn.cursor()

    record = None
    chain = []

    if record_type == "coating":
        cur.execute(
            "SELECT material_id, project, coating_date, made_by, coat_weight_gsm, porosity "
            "FROM tbl_coating WHERE coating_id = %s", (record_id,)
        )
        row = cur.fetchone()
        if row:
            columns = ["Material ID", "Project", "Coating Date", "Made By", "GSM", "Porosity"]
            record = dict(zip(columns, row))
            cur.execute("SELECT slp_id FROM tbl_slp WHERE coating_id = %s", (record_id,))
            chain += [f"SLP: {r[0]}" for r in cur.fetchall()]
            cur.execute("SELECT coincell_id FROM tbl_coincell WHERE coating_id = %s", (record_id,))
            chain += [f"CoinCell: {r[0]}" for r in cur.fetchall()]
            cur.execute("SELECT mlp_id FROM tbl_mlp WHERE cat_coating_id = %s OR an_coating_id = %s", (record_id, record_id))
            chain += [f"MLP: {r[0]}" for r in cur.fetchall()]

    elif record_type == "material":
        cur.execute(
            "SELECT chemistry, supplier, date_received, quantity_kg, location, availability "
            "FROM tbl_materials WHERE material_id = %s", (record_id,)
        )
    elif record_type == "slp":
        cur.execute(
            "SELECT coating_id, project, date_made, made_by, electrolyte, formation_capacity "
            "FROM tbl_slp WHERE slp_id = %s", (record_id,)
        )
        row = cur.fetchone()
        if row:
            columns = ["Coating ID", "Project", "Date Made", "Made By", "Electrolyte", "Formation Capacity"]
            record = dict(zip(columns, row))
            chain.append(f"Coating: {record['Coating ID']}")

    elif record_type == "coincell":
        cur.execute(
            "SELECT coating_id, project, date_made, made_by, electrolyte, formation_capacity "
            "FROM tbl_coincell WHERE coincell_id = %s", (record_id,)
        )
        row = cur.fetchone()
        if row:
            columns = ["Coating ID", "Project", "Date Made", "Made By", "Electrolyte", "Formation Capacity"]
            record = dict(zip(columns, row))
            chain.append(f"Coating: {record['Coating ID']}")

    elif record_type == "mlp":
        cur.execute(
            "SELECT cat_coating_id, an_coating_id, project, date_made, cell_capacity "
            "FROM tbl_mlp WHERE mlp_id = %s", (record_id,)
        )
        row = cur.fetchone()
        if row:
            columns = ["Cathode Coating", "Anode Coating", "Project", "Date Made", "Cell Capacity"]
            record = dict(zip(columns, row))
            chain.append(f"Cathode: {record['Cathode Coating']}")
            chain.append(f"Anode: {record['Anode Coating']}")
        
        row = cur.fetchone()
        if row:
            columns = ["Chemistry", "Supplier", "Date Received", "Quantity (kg)", "Location", "Availability"]
            record = dict(zip(columns, row))
            cur.execute("SELECT coating_id FROM tbl_coating WHERE material_id = %s", (record_id,))
            chain += [f"Coating: {r[0]}" for r in cur.fetchall()]

    cur.close()
    conn.close()

    if not record:
        return HTMLResponse("Record not found.", status_code=404)

    return templates.TemplateResponse(
        "card.html",
        {"request": request, "record_id": record_id, "record_type": record_type,
         "record": record, "chain": chain, "qr_base64": qr_base64}
    )

@app.get("/api/chart/gsm-by-coating")
def chart_gsm():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT coating_id, coat_weight_gsm FROM tbl_coating WHERE coat_weight_gsm IS NOT NULL ORDER BY coating_id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return JSONResponse({"labels": [r[0] for r in rows], "values": [float(r[1]) for r in rows]})


@app.get("/api/chart/records-per-table")
def chart_records_per_table():
    conn = get_connection()
    cur = conn.cursor()
    counts = {}
    for label, table in [("Materials", "tbl_materials"), ("Coatings", "tbl_coating"),
                          ("SLP", "tbl_slp"), ("Coin Cells", "tbl_coincell"), ("MLP", "tbl_mlp")]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        counts[label] = cur.fetchone()[0]
    cur.close()
    conn.close()
    return JSONResponse({"labels": list(counts.keys()), "values": list(counts.values())})


@app.get("/api/graph")
def traceability_graph():
    conn = get_connection()
    cur = conn.cursor()

    nodes = []
    edges = []
    seen_projects = set()

    def add_project_node(project_name):
        if project_name and project_name not in seen_projects:
            nodes.append({"id": f"PROJECT-{project_name}", "label": project_name, "group": "project"})
            seen_projects.add(project_name)

    cur.execute("SELECT material_id, chemistry FROM tbl_materials")
    for mat_id, chem in cur.fetchall():
        nodes.append({"id": mat_id, "label": mat_id, "group": "material", "title": chem or ""})

    cur.execute("SELECT coating_id, material_id, project FROM tbl_coating")
    for coat_id, mat_id, project in cur.fetchall():
        nodes.append({"id": coat_id, "label": coat_id, "group": "coating"})
        edges.append({"from": mat_id, "to": coat_id})
        add_project_node(project)
        if project:
            edges.append({"from": coat_id, "to": f"PROJECT-{project}", "dashes": True})

    cur.execute("SELECT slp_id, coating_id, project FROM tbl_slp")
    for slp_id, coat_id, project in cur.fetchall():
        nodes.append({"id": slp_id, "label": slp_id, "group": "slp"})
        edges.append({"from": coat_id, "to": slp_id})
        add_project_node(project)
        if project:
            edges.append({"from": slp_id, "to": f"PROJECT-{project}", "dashes": True})

    cur.execute("SELECT coincell_id, coating_id, project FROM tbl_coincell")
    for cc_id, coat_id, project in cur.fetchall():
        nodes.append({"id": cc_id, "label": cc_id, "group": "coincell"})
        edges.append({"from": coat_id, "to": cc_id})
        add_project_node(project)
        if project:
            edges.append({"from": cc_id, "to": f"PROJECT-{project}", "dashes": True})

    cur.execute("SELECT mlp_id, cat_coating_id, an_coating_id, project FROM tbl_mlp")
    for mlp_id, cat_id, an_id, project in cur.fetchall():
        nodes.append({"id": mlp_id, "label": mlp_id, "group": "mlp"})
        edges.append({"from": cat_id, "to": mlp_id})
        edges.append({"from": an_id, "to": mlp_id})
        add_project_node(project)
        if project:
            edges.append({"from": mlp_id, "to": f"PROJECT-{project}", "dashes": True})

    cur.close()
    conn.close()
    return JSONResponse({"nodes": nodes, "edges": edges})

@app.get("/graph", response_class=HTMLResponse)
def graph_page(request: Request):
    return templates.TemplateResponse("graph.html", {"request": request})

@app.get("/api/chart/coatings-over-time")
def chart_coatings_over_time():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT coating_date, COUNT(*) 
        FROM tbl_coating 
        WHERE coating_date IS NOT NULL 
        GROUP BY coating_date 
        ORDER BY coating_date
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return JSONResponse({"labels": [str(r[0]) for r in rows], "values": [r[1] for r in rows]})

@app.get("/HAZbot", response_class=HTMLResponse)
def HAZbot_page(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("HAZbot.html", {"request": request})


@app.post("/api/HAZbot/ask")
def HAZbot_ask(request: Request, question: str = Form(...)):
    raw = ask_ai_for_sql(question)

    if raw.startswith("ERROR"):
        return JSONResponse({"error": raw}, status_code=502)

    sql_part, insight_part = "", ""
    for line in raw.splitlines():
        if line.strip().upper().startswith("SQL:"):
            sql_part = line.split(":", 1)[1].strip()
        elif line.strip().upper().startswith("INSIGHT:"):
            insight_part = line.split(":", 1)[1].strip()

    if not sql_part:
        return JSONResponse({"error": f"Couldn't parse AI response: {raw}"}, status_code=502)

    if not sql_part.upper().startswith("SELECT"):
        return JSONResponse({"error": "Generated query was not a SELECT statement — blocked for safety."}, status_code=400)

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql_part)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        results = [dict(zip(columns, [str(v) if v is not None else None for v in row])) for row in rows]
    except Exception as e:
        cur.close()
        conn.close()
        return JSONResponse({"error": f"SQL execution failed: {str(e)}", "sql": sql_part}, status_code=400)

    cur.close()
    conn.close()

    return JSONResponse({"sql": sql_part, "insight": insight_part, "columns": columns, "results": results})
