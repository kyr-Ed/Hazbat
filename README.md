# BMAC By HazBAT — Battery Materials & Cells Traceability




Developed by the **Battery Materials & Cells Group**, WMG, University of Warwick.

BMAC is a full-chain traceability database for battery research labs. It tracks every step from raw electrode powder through coating, cell assembly, and electrochemical testing, with every relationship enforced at the database level.

---

## What it does

- **Records** materials, coatings, SLP cells, coin cells, and MLP cells in a relational PostgreSQL database
- **Enforces traceability** — every cell links back to its coating, every coating links back to its material
- **Visualises** the full manufacturing graph interactively, with multi-dimensional filtering and path highlighting
- **Generates lineage & passport cards** per cell, including EU Battery Regulation DPP scaffold fields 
- **Plots cycling data** from BioLogic `.mpr` files: capacity fade, coulombic efficiency, and voltage vs. capacity curves
- **Exports** any table to CSV or Excel

---

## Data hierarchy

```
tbl_materials
    └── tbl_coating
        └──tbl_cell 
        e.g ├── tbl_slp        (single-layer pouch)
            ├── tbl_coincell   (coin cell, e.g. CR2032 half cell)
            ├── tbl_mlp        (multi-layer pouch — two coatings: cathode + anode)
            └── etc.
```

---

---

## Features

### Lineage & passport card
Page for every component showing:
- Full manufacturing traceability chain (material → coating → cell → formation → testing)
- Capacity fade chart and voltage vs. areal capacity curves
- EU Battery Regulation sections: supply chain due diligence, material inputs, recycled content targets, circularity
- Print-to-PDF layout
- JSON export for downstream processing

### Bulk upload
CSV or Excel upload for all five record types. Column names are case-insensitive.

### Certificates of Analysis (COA)
Every material card has a **+ COA** button at the top right, on the New Material page, after a bulk upload and on the material's own card. It takes `.pdf`, `.docx` or `.doc` (up to 25 MB); drop a file on a card, or drop several on the bulk results page and they are matched to cards by the material ID in the file name. Clicking **COA** opens an in-browser preview with download, replace and remove. Word files are converted to PDF for the preview with LibreOffice:

```bash
sudo apt install --no-install-recommends libreoffice-writer   # Word preview (optional)
psql "$DATABASE_URL" -f migrations/001_material_coa.sql       # existing databases only
```
Files are stored in `uploads/coa/<material_id>/` (git-ignored, include it in backups). COAs need a login to view.

### Traceability graph
A full `vis.js` force-directed network of every record and their relationships. Clicking any node highlights its complete upstream (ancestors) and downstream (descendants) path with a pulsing edge animation, and opens a quick-view side panel showing key fields, and QR code.

### Cycling data viewer
Upload a BioLogic `.mpr` file and attach it to any cell record. The graph page and lineage card then show:
- Discharge capacity per cycle (capacity fade)
- Coulombic efficiency per cycle
- Voltage vs. capacity curves, selectable by cycle, normalised by electrode area

---

## ID conventions

BMAC uses human-readable hierarchical IDs that encode provenance directly:

```
CAT-NMC-001             ← cathode material, NMC chemistry, batch 001
CAT-NMC-001-C001        ← first coating of that material
CAT-NMC-001-C001-CC01   ← first coin cell from that coating
CAT-NMC-001-C001-SLP-01 ← first SLP from that coating
```


Prefix conventions:
- `CAT-` — cathode material
- `AN-` — anode material

- `SLP-` — single-layer pouch cell
- `CC-` — coin cell
- `MLP-` — multi-layer pouch cell

---

## Uploading cycling data

1. Navigate to **Tables → Upload Cycling Data**
2. Enter the record ID of the cell the file belongs to (e.g. `CAT-NMC-001-C001-CC01`)
3. Upload a BioLogic `.mpr` file

Once uploaded, the cell's card page, lineage card, and the graph quick-view panel will all show:
- Capacity fade chart (discharge capacity per cycle)
- Coulombic efficiency per cycle
- Voltage vs. capacity curves, selectable by cycle number

Cycling data can also be explored directly from the graph page without navigating away.

---
