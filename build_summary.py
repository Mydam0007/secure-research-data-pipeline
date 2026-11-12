"""Build a one-page project summary DOCX for the USC secure-research-data-pipeline project."""
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BLUE = RGBColor(0x1F, 0x4E, 0x79)
DARK = RGBColor(0x1A, 0x1A, 0x1A)
GREY = RGBColor(0x55, 0x55, 0x55)

doc = Document()
sec = doc.sections[0]
sec.page_width = Inches(8.5)
sec.page_height = Inches(11)
sec.top_margin = Inches(0.4)
sec.bottom_margin = Inches(0.4)
sec.left_margin = Inches(0.6)
sec.right_margin = Inches(0.6)

style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(9)
style.font.color.rgb = DARK
style.paragraph_format.space_after = Pt(2)
style.paragraph_format.space_before = Pt(0)
style.paragraph_format.line_spacing = 1.1


def add_hyperlink(paragraph, url, text):
    part = paragraph.part
    r_id = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)
    run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    rFonts = OxmlElement("w:rFonts")
    rFonts.set(qn("w:ascii"), "Calibri")
    rFonts.set(qn("w:hAnsi"), "Calibri")
    rPr.append(rFonts)
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "18")
    rPr.append(sz)
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "1F4E79")
    rPr.append(color)
    run.append(rPr)
    t = OxmlElement("w:t")
    t.text = text
    run.append(t)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def heading(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(2)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "1F4E79")
    pBdr.append(bottom)
    pPr.append(pBdr)
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(11)
    r.font.color.rgb = BLUE
    return p


def shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def set_cell_text(cell, text, bold=False, size=9, color=DARK):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.space_before = Pt(1)
    r = p.add_run(text)
    r.bold = bold
    r.font.size = Pt(size)
    r.font.color.rgb = color
    return p


def rich_para(cell_or_doc, segments, first_bold=False):
    """segments: list of (text, bold) tuples."""
    p = cell_or_doc.add_paragraph() if hasattr(cell_or_doc, "add_paragraph") and not hasattr(cell_or_doc, "_tc") else cell_or_doc.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    for text, bold in segments:
        r = p.add_run(text)
        r.bold = bold
        r.font.size = Pt(9)
    return p


# Title
p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(1)
r = p.add_run("Secure Research-Data Pipeline")
r.bold = True
r.font.size = Pt(15)
r.font.color.rgb = BLUE

# Contact line
p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(3)
r = p.add_run("Nagaraju Mydam  ·  MS Data Science, Clarkson University (2025)  ·  AI Engineer, SANQUEST Inc.  ·  ")
r.font.size = Pt(9)
r.font.color.rgb = GREY
add_hyperlink(p, "https://github.com/Mydam0007", "github.com/Mydam0007")
r = p.add_run("  ·  ")
r.font.size = Pt(9)
r.font.color.rgb = GREY
add_hyperlink(p, "https://www.linkedin.com/in/nagaraju-mydam-160979259", "linkedin.com/in/nagaraju-mydam-160979259")

# Intro
p = doc.add_paragraph()
r = p.add_run(
    "An end-to-end pipeline that ingests sensitive research-participant records, validates them, "
    "de-identifies them, and exports an analysis-ready dataset — with a data-quality report and a "
    "full audit log at every stage. Built to demonstrate the core practices of research data "
    "engineering for regulated, sensitive data: prove quality, remove identifiers, and leave an "
    "audit trail for every row."
)
r.font.size = Pt(9)

# Flow line
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(2)
p.paragraph_format.space_after = Pt(2)
r = p.add_run("Generate  →  Ingest  →  Validate  →  De-identify  →  Export      +      data-quality report & audit log")
r.bold = True
r.font.size = Pt(9)
r.font.color.rgb = BLUE

# How it works
heading("How it works")
rows = [
    ("Generate", "1,200 synthetic participant records from a fixed seed, so runs are reproducible; a known rate of defects is injected (missing values, out-of-range labs, duplicate study IDs, malformed emails, invalid consent flags)."),
    ("Validate", "Schema, date-parsing and range checks. Rows failing critical checks are excluded and counted; out-of-range lab values are nulled and counted, never silently kept."),
    ("De-identify", "Direct identifiers salted SHA-256 hashed (name, email, study ID); phone dropped entirely. Dates of birth become age bands plus birth year; enrollment dates become enrollment year. The export contains no raw identifiers, and a safety check fails the run if any identifier column remains."),
    ("Report & audit", "Data-quality report (JSON + Markdown) and a JSONL audit log — one event per stage, with row counts and counts only, never participant values."),
]
t = doc.add_table(rows=1, cols=2)
t.style = "Table Grid"
t.alignment = WD_TABLE_ALIGNMENT.CENTER
hdr = t.rows[0].cells
set_cell_text(hdr[0], "Stage", bold=True, color=BLUE)
set_cell_text(hdr[1], "What happens", bold=True, color=BLUE)
shade(hdr[0], "E8EEF4")
shade(hdr[1], "E8EEF4")
for stage, desc in rows:
    cells = t.add_row().cells
    set_cell_text(cells[0], stage, bold=True)
    set_cell_text(cells[1], desc)
t.columns[0].width = Inches(1.1)
t.columns[1].width = Inches(6.2)

# Measured results — single compact table, then one line of detail
heading("Measured results (actual run, seed 42)")
res = doc.add_table(rows=1, cols=4)
res.style = "Table Grid"
res.alignment = WD_TABLE_ALIGNMENT.CENTER
hdr = res.rows[0].cells
for i, h in enumerate(["Rows in / out", "Rows excluded", "Values nulled", "Fields masked / generalized"]):
    set_cell_text(hdr[i], h, bold=True, color=BLUE)
    shade(hdr[i], "E8EEF4")
vals = res.add_row().cells
for i, v in enumerate(["1,200 / 1,180", "20", "124 (out of range)", "4 hashed · 2 generalized"]):
    set_cell_text(vals[i], v)
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(2)
for text, bold in [
    ("Exclusions (20): ", True),
    ("3 missing study ID, 6 duplicate study ID, 6 invalid consent flag, 2 unparseable date of birth, 3 age outside 18–100.  ", False),
    ("Nulled (124): ", True),
    ("glucose 51, HbA1c 31, cholesterol 24, systolic BP 10, diastolic BP 8.  ", False),
    ("Verification: ", True),
    ("verify_outputs.py runs 21 independent checks (no identifier columns or raw values in any output, no email pattern, audit log parses as JSONL, hashes 64-char hex, row counts reconcile) — all 21 pass; same seed gives a byte-identical export. Pipeline time 0.05 s (0.54 s wall-clock).", False),
]:
    r = p.add_run(text)
    r.bold = bold
    r.font.size = Pt(9)

# Why it maps
heading("Why it maps to the Research Data Engineer role")
for lead, rest in [
    ("Secure pipelines for sensitive data: ", "ingest → validate → de-identify → export, with row counts tracked at every stage."),
    ("De-identification: ", "salted hashing plus generalization — the techniques used for research datasets shared without exposing participants."),
    ("Data quality & auditability: ", "a quality report that separates exclusion reasons by cause, and an audit log suitable for sponsor review — no participant data inside it."),
    ("Reproducibility: ", "one command runs the whole pipeline from a seed; a Docker image runs it end to end with no manual steps."),
]:
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(1)
    r = p.add_run(lead)
    r.bold = True
    r.font.size = Pt(9)
    r2 = p.add_run(rest)
    r2.font.size = Pt(9)

# Stack
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(3)
r = p.add_run("Stack: ")
r.bold = True
r.font.size = Pt(9)
r = p.add_run("Python 3.12, pandas, Docker — nothing else.   Run it: ")
r.font.size = Pt(9)
r = p.add_run("pip install -r requirements.txt && python run_pipeline.py")
r.italic = True
r.font.size = Pt(9)
r = p.add_run("  ·  ")
r.font.size = Pt(9)
r = p.add_run("python verify_outputs.py")
r.italic = True
r.font.size = Pt(9)

# Footer disclaimer
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(3)
pPr = p._p.get_or_add_pPr()
pBdr = OxmlElement("w:pBdr")
top = OxmlElement("w:top")
top.set(qn("w:val"), "single")
top.set(qn("w:sz"), "6")
top.set(qn("w:space"), "4")
top.set(qn("w:color"), "CCCCCC")
pBdr.append(top)
pPr.append(pBdr)
r = p.add_run(
    "All data is synthetic — every record is invented by a seeded generator; no real people, no real patient data. "
    "Independent portfolio project; not affiliated with, endorsed by, or built for the University of Southern California. "
    "Hashing with a salt is pseudonymization, not anonymization. "
    "This project demonstrates techniques; it is not a compliance certification and claims none."
)
r.font.size = Pt(8)
r.font.color.rgb = GREY

doc.save("/home/hatch/workspace/your_files/secure-research-data-pipeline/PROJECT_SUMMARY.docx")
print("saved")
