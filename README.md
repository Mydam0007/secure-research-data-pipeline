# Secure Research-Data Pipeline

An end-to-end data pipeline that ingests sensitive research-participant
records, validates them, de-identifies them, and exports an
analysis-ready dataset — with a data-quality report and a full audit log
at every stage.

**All data is synthetic.** Every record is invented by a seeded random
generator: no real people, no real patient data. This is an independent
portfolio project. It is not affiliated with, endorsed by, or built for
the University of Southern California.

## Why this project exists

Research data engineering for sensitive, regulated research comes down
to a small set of repeatable practices: ingest messy data, prove its
quality, remove anything that can identify a person, and leave an audit
trail showing exactly what happened to every row. This project
demonstrates each of those practices in working code, using Python,
pandas, and Docker.

## What it does

```
generate (synthetic raw file) → ingest → validate → de-identify → export
                                              ↓
                                   data-quality report + audit log
```

| Stage | What happens |
|---|---|
| Generate | Creates 1,200 synthetic participant records (study IDs, names, emails, dates of birth, lab values, consent flags) with a fixed seed, so runs are reproducible. A small, known rate of defects is injected: missing values, out-of-range lab results, duplicate study IDs, malformed emails, invalid consent flags. |
| Ingest | Loads the raw CSV and records the row count in the audit log. |
| Validate | Checks the schema, parses dates, and runs data-quality checks. Rows failing critical checks are excluded and counted; out-of-range lab values are set to null and counted. |
| De-identify | Direct identifiers are salted SHA-256 hashed (name, email, study ID) or dropped (phone). Dates of birth become age bands plus birth year; enrollment dates become enrollment year. The export contains no raw identifiers. |
| Export | Writes the de-identified CSV. A safety check fails the run if any identifier column is still present. |
| Report + audit | Writes a data-quality report (JSON and Markdown) and a JSONL audit log — one event per stage, with row counts and counts only, never participant values. |

## How to run

### Locally

```bash
pip install -r requirements.txt
python run_pipeline.py
```

Or as a module:

```bash
python -m pipeline
```

Options:

```bash
python run_pipeline.py --rows 2000 --seed 7 --salt my-secret-salt --regenerate
```

- `--rows` / `--seed` control the synthetic data (used when the raw file is generated).
- `--salt` (or the `PIPELINE_SALT` environment variable) sets the hash salt. Without one, a development default is used and the run is flagged in the audit log. In a real deployment the salt belongs in a secrets store, never in source control.
- `--regenerate` rebuilds the raw file; otherwise the existing raw file is reused, so `--rows` only takes effect on first run or with `--regenerate`.

### With Docker

```bash
docker build -t secure-research-data-pipeline .
docker run --rm -v "$PWD/outputs:/app/outputs" secure-research-data-pipeline
```

To pass a salt into the container:

```bash
docker run --rm -e PIPELINE_SALT=my-secret-salt -v "$PWD/outputs:/app/outputs" secure-research-data-pipeline
```

## Outputs

After a run, `outputs/` contains:

- `deidentified_participants.csv` — 1,180 de-identified rows, 15 columns
- `data_quality_report.json` / `data_quality_report.md` — validation results
- `audit_log.jsonl` — 6 events, one per stage

The raw synthetic file lives in `data/raw/` and is never written to `outputs/`. Both directories are git-ignored: raw files look like real PII even though every record is synthetic, and all outputs are reproducible from the seed.

## Measured results (actual run, seed 42)

Run on Python 3.12 with pandas 2.1.4. Pipeline time **0.05 s**; **0.54 s** wall-clock including interpreter start. Re-running with the same seed produces a byte-identical export.

| Metric | Value |
|---|---|
| Rows in | 1,200 |
| Rows out | 1,180 |
| Rows excluded | 20 |
| Values nulled (out of range) | 124 |
| Fields masked (hashed) | 4 — full name, email, phone, study ID |
| Fields generalized | 2 — date of birth → age band + birth year; enrollment date → year |

Exclusions (20 rows): 3 missing study ID, 6 duplicate study ID,
6 invalid consent flag, 2 unparseable date of birth, 3 age outside
18–100 at enrollment.

Nulled values (124): glucose 51, HbA1c 31, cholesterol 24,
systolic BP 10, diastolic BP 8. These are out-of-range lab results —
some injected, some from the tails of the generator's distributions —
set to null and counted rather than silently kept.

Validation checks (1,180 retained rows):

| Check | Passed | Failed |
|---|---|---|
| Email format | 1,169 | 11 |
| Glucose in range 50–500 mg/dL | 1,108 | 51 |
| HbA1c in range 3.5–15% | 1,125 | 31 |
| Cholesterol in range 100–400 mg/dL | 1,133 | 24 |
| Systolic BP in range 70–220 | 1,146 | 10 |
| Diastolic BP in range 40–130 | 1,149 | 8 |
| Duplicate study ID | 1,180 | 6 |

Age-band mix in the export: 18–29: 170, 30–39: 186, 40–49: 174,
50–59: 140, 60–69: 165, 70–79: 174, 80–89: 170, 90+: 1.

### Sample export (hashes truncated for display)

```
participant_hash,name_hash,email_hash,age_band,birth_year,sex,study_arm,enrollment_year,site,consent_flag,lab_glucose_mg_dl,lab_hba1c_pct,lab_cholesterol_mg_dl,systolic_bp,diastolic_bp
6dcc5b4b9f937acb…,0a48494e1bb4cd49…,9bee7cfc6123c28e…,80-89,1938,F,Treatment B,2024,Site D,Y,128.2,,158.8,164.0,81.0
26aa763db90c5b77…,9492f3cb606e879e…,f2d1719e725f690a…,30-39,1988,M,Treatment A,2024,Site B,Y,87.0,6.0,181.5,143.0,61.0
```

### Sample audit event

```json
{"details": {"excluded_rows": 20, "exclusion_reasons": {"age_out_of_range_18_100": 3, "duplicate_participant_id": 6, "invalid_consent_flag": 6, "missing_participant_id": 3, "unparseable_date_of_birth": 2}, "nulled_values": {"diastolic_bp": 8, "lab_cholesterol_mg_dl": 24, "lab_glucose_mg_dl": 51, "lab_hba1c_pct": 31, "systolic_bp": 10}}, "rows_in": 1200, "rows_out": 1180, "run_id": "cabf264e-cdf1-48ac-a7fc-b86afabf5ce7", "stage": "validate", "timestamp_utc": "2026-11-12T17:28:30.925248+00:00"}
```

## Verification

`verify_outputs.py` checks the outputs independently: no identifier
columns in the export, no raw identifier value in any output file, no
email pattern anywhere in the outputs, audit log parses as JSONL with
one event per stage, hashes are 64-character hex, age bands and years
are valid, and row counts reconcile with the report.

```bash
python verify_outputs.py
# RESULT: ALL PASS  (21 checks)
```

## How this maps to the Research Data Engineer role

| Responsibility in the role | What this project does |
|---|---|
| Design and manage secure data pipelines for ingestion, transformation, de-identification, and export of sensitive research datasets | The full pipeline: ingest → validate → de-identify → export, with row counts tracked at every stage |
| De-identification of sensitive datasets | Salted SHA-256 hashing of direct identifiers; generalization of dates to age bands and years; phone numbers dropped entirely |
| Data-quality validation and reporting | Schema checks, range checks, format checks, duplicate detection; JSON + Markdown quality report with exact counts |
| Documentation and auditability for sponsor reviews | JSONL audit log recording every stage with timestamps and row counts, containing no participant data |
| Automate data-processing and research workflows | One command runs the whole pipeline reproducibly from a seed; Docker image runs it end to end with no manual steps |
| Data architecture and data modeling | Explicit input schema, explicit de-identified output schema, and a validation layer that enforces both |
| Root-cause analysis of recurring data issues | The report separates exclusion reasons and nulled values by cause, so the same failure mode is visible run after run |

## Stack

Python 3.12, pandas, Docker. Nothing else.

## Notes and limits

- The data is synthetic and the salt default is for development only.
  Neither is suitable for real participant data without a proper secrets
  store, access controls, and review.
- Hashing with a salt is pseudonymization, not anonymization: with the
  salt and the source data, hashes can be reversed. The pipeline treats
  the raw file as sensitive for exactly that reason — it is never
  written to `outputs/` and is git-ignored.
- This project demonstrates techniques; it is not a compliance
  certification and does not claim any.
