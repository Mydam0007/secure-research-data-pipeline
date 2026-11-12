#!/usr/bin/env python3
"""Checks the outputs after a run: no identifier columns or raw values
left in any output file, hashes look right, row counts add up.

Run it from the project root, after a run: python verify_outputs.py
"""

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw" / "participants_raw.csv"
OUT = ROOT / "outputs" / "deidentified_participants.csv"
REPORT = ROOT / "outputs" / "data_quality_report.json"
AUDIT = ROOT / "outputs" / "audit_log.jsonl"

fails: list[str] = []


def check(name: str, cond: bool) -> None:
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


def main() -> int:
    raw = pd.read_csv(RAW)
    out = pd.read_csv(OUT)
    report = json.loads(REPORT.read_text())
    audit_text = AUDIT.read_text()
    audit_lines = audit_text.splitlines()

    outputs_text = "".join(
        (ROOT / "outputs" / p).read_text()
        for p in [
            "deidentified_participants.csv",
            "data_quality_report.json",
            "data_quality_report.md",
            "audit_log.jsonl",
        ]
    )

    # 1. No forbidden columns in export
    forbidden = {"full_name", "email", "phone", "date_of_birth", "enrollment_date", "participant_id"}
    check("no forbidden columns in export", not (forbidden & set(out.columns)))

    # 2. No raw identifier value appears in any output file
    leaked = []
    for col in ["full_name", "email", "phone", "date_of_birth", "participant_id"]:
        for v in raw[col].dropna().astype(str).unique():
            if len(v) >= 4 and v in outputs_text:
                leaked.append((col, v))
    check("no raw identifier value in any output", not leaked)
    if leaked:
        print("  leaked sample:", leaked[:5])

    # 3. No email pattern anywhere in outputs
    check(
        "no email pattern in outputs",
        not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", outputs_text),
    )

    # 4. Audit log structure and content
    events = [json.loads(line) for line in audit_lines]
    check("audit log parses as JSONL, 6 events", len(events) == 6)
    check(
        "audit stages in order",
        [e["stage"] for e in events]
        == ["generate", "ingest", "validate", "deidentify", "export", "report"],
    )
    audit_leaked = [
        v
        for col in ["full_name", "email", "phone", "date_of_birth", "participant_id"]
        for v in raw[col].dropna().astype(str).unique()
        if len(v) >= 4 and v in audit_text
    ]
    check("audit log contains no identifier values", not audit_leaked)

    # 5. Hashes are 64-char hex; pseudonyms unique
    hexre = re.compile(r"^[0-9a-f]{64}$")
    check("participant_hash all 64-hex", out["participant_hash"].astype(str).str.match(hexre).all())
    check("name_hash all 64-hex", out["name_hash"].astype(str).str.match(hexre).all())
    check("participant_hash unique", out["participant_hash"].is_unique)

    # 6. Generalization valid
    check(
        "age_band values valid",
        set(out["age_band"].unique())
        <= {"18-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80-89", "90+"},
    )
    check("birth_year in 1936..2004", out["birth_year"].between(1936, 2004).all())
    check("enrollment_year in 2023..2026", out["enrollment_year"].between(2023, 2026).all())

    # 7. Row counts consistent
    check("rows_out == export rows", report["rows_out"] == len(out))
    check("rows_in == raw rows", report["rows_in"] == len(raw))
    check(
        "excluded reasons sum to excluded_rows",
        sum(report["exclusion_reasons"].values()) == report["excluded_rows"],
    )

    # 8. Exported lab values in range or null
    ranges = {
        "lab_glucose_mg_dl": (50, 500),
        "lab_hba1c_pct": (3.5, 15),
        "lab_cholesterol_mg_dl": (100, 400),
        "systolic_bp": (70, 220),
        "diastolic_bp": (40, 130),
    }
    for col, (lo, hi) in ranges.items():
        s = pd.to_numeric(out[col], errors="coerce")
        check(f"{col} in range or null", bool(((s.isna()) | ((s >= lo) & (s <= hi))).all()))

    print("\nRESULT:", "ALL PASS" if not fails else f"FAILURES: {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
