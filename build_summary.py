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
    "I built this pipeline to show how I handle sensitive research data: check the quality, "
    "strip out anything that can identify a person, and keep a record of what happened to "
    "every row. It takes in participant records, validates them, de-identifies them, and "
    "exports a clean dataset, with a data-quality report and a full audit log."
)
r.font.size = Pt(9)

# Flow line
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(2)
p.paragraph_format.space_after = Pt(2)
r = p.add_run("Generate, validate, de-identify, export, plus a data-quality report and audit log")
r.bold = True
r.font.size = Pt(9)
r.font.color.rgb = BLUE

# How it works
heading("How it works")
rows = [
    ("Generate", "1,200 fake participant records from a fixed seed, so every run is the same. A few bad rows are mixed in on purpose: missing values, out-of-range labs, duplicate study IDs, bad emails, bad consent flags."),
    ("Validate", "Schema, date-parsing and range checks. Rows that fail a critical check get dropped and counted. Out-of-range lab values get set to null and counted, never kept quietly."),
    ("De-identify", "Names, emails and study IDs get hashed with a salted SHA-256 hash. Phone numbers are dropped. Dates of birth become an age band plus birth year, enrollment dates become just the year. The export has no raw identifiers in it, and the run fails if any identifier column is still there."),
    ("Report & audit", "A data-quality report (JSON and Markdown) and a JSONL audit log, one event per stage. Both hold counts only, never participant values."),
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

# Results table, then one line of detail
heading("What came out of the run (seed 42)")
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
    ("verify_outputs.py runs 21 checks on its own (no identifier columns or raw values in any output, no email pattern, audit log parses as JSONL, hashes are 64-char hex, row counts add up). All 21 pass, and the same seed gives a byte-identical export. Pipeline time 0.05 s (0.54 s wall-clock).", False),
]:
    r = p.add_run(text)
    r.bold = bold
    r.font.size = Pt(9)

# Why it maps
heading("What this shows for the Research Data Engineer role")
for lead, rest in [
    ("Secure pipelines for sensitive data: ", "take in, check, de-identify and export, with row counts tracked at every step."),
    ("De-identification: ", "salted hashing plus generalization, the same techniques used when research datasets get shared without exposing participants."),
    ("Data quality and auditability: ", "a quality report that splits out why each row was dropped, and an audit log fit for a sponsor review, with no participant data inside it."),
    ("Reproducibility: ", "one command runs the whole pipeline from a seed, and a Docker image runs it end to end with no manual steps."),
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
r = p.add_run("Python 3.12, pandas, Docker. Nothing else.   Run it: ")
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
    "All the data is made up. Every record is fake, generated with a fixed seed, so there are no "
    "real people and no real patient data here. This is my own project, not affiliated with, "
    "endorsed by, or built for the University of Southern California. Hashing with a salt is "
    "pseudonymization, not anonymization. This shows the technique; it is not a compliance "
    "certification and does not claim to be one."
)
r.font.size = Pt(8)
r.font.color.rgb = GREY

doc.save("/home/hatch/workspace/your_files/secure-research-data-pipeline/PROJECT_SUMMARY.docx")
print("saved")
