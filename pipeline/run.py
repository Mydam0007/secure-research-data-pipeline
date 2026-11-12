"""Runs the whole pipeline: generate, validate, de-identify, export, report.

    python run_pipeline.py
    python run_pipeline.py --rows 2000 --seed 7 --salt my-secret-salt
    python -m pipeline --rows 1200 --seed 42

Outputs go to outputs/: the de-identified CSV, a data-quality report
(JSON and Markdown), and the audit log. The raw file lives in data/raw/
and is made on the first run (or with --regenerate). It never gets
written to outputs/.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from .audit import AuditLog
from .deidentify import FORBIDDEN_COLUMNS, deidentify, get_salt
from .generate import write_raw
from .validate import validate

DEFAULT_ROWS = 1200
DEFAULT_SEED = 42


def _write_markdown_report(report: dict, path: Path) -> None:
    lines = [
        "# Data-quality report (synthetic data)",
        "",
        f"- Rows in: **{report['rows_in']}**",
        f"- Rows out: **{report['rows_out']}**",
        f"- Rows excluded: **{report['excluded_rows']}**",
        "",
        "## Exclusion reasons",
        "",
    ]
    if report["exclusion_reasons"]:
        for reason, count in sorted(report["exclusion_reasons"].items()):
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- none")
    lines += ["", "## Values nulled (out of range)", ""]
    if report["nulled_values"]:
        for col, count in sorted(report["nulled_values"].items()):
            lines.append(f"- {col}: {count}")
    else:
        lines.append("- none")
    lines += ["", "## Checks", ""]
    for check in report["checks"]:
        lines.append(f"- {check['name']}: passed {check['passed']}, failed {check['failed']}")
    lines += [
        "",
        "## Null counts after cleaning",
        "",
    ]
    for col, count in report["null_counts_after"].items():
        if count:
            lines.append(f"- {col}: {count}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(
    rows: int = DEFAULT_ROWS,
    seed: int = DEFAULT_SEED,
    salt: str | None = None,
    raw_path: str = "data/raw/participants_raw.csv",
    out_dir: str = "outputs",
    regenerate: bool = False,
) -> dict:
    """Run the full pipeline and return a summary dict."""
    started = time.perf_counter()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    audit_path = out / "audit_log.jsonl"
    if audit_path.exists():
        audit_path.unlink()  # one log per run; never append across runs
    audit = AuditLog(audit_path)
    salt_value, used_default_salt = get_salt(salt)

    raw = Path(raw_path)
    if regenerate or not raw.exists():
        write_raw(n=rows, seed=seed, path=raw)
        audit.event("generate", rows_in=0, rows_out=rows, seed=seed, regenerated=True)
    else:
        audit.event("generate", rows_in=0, rows_out=rows, seed=seed, regenerated=False)

    df = pd.read_csv(raw)
    audit.event("ingest", rows_in=len(df), rows_out=len(df), source=str(raw))

    clean, report = validate(df)
    audit.event(
        "validate",
        rows_in=report["rows_in"],
        rows_out=report["rows_out"],
        excluded_rows=report["excluded_rows"],
        exclusion_reasons=report["exclusion_reasons"],
        nulled_values=report["nulled_values"],
    )

    deid = deidentify(clean, salt_value)
    leaked = FORBIDDEN_COLUMNS & set(deid.columns)
    if leaked:
        raise RuntimeError(f"de-identified export still contains identifiers: {sorted(leaked)}")
    audit.event(
        "deidentify",
        rows_in=len(clean),
        rows_out=len(deid),
        fields_masked=["full_name", "email", "phone", "participant_id"],
        fields_generalized=["date_of_birth", "enrollment_date"],
        used_default_salt=used_default_salt,
    )

    export_path = out / "deidentified_participants.csv"
    deid.to_csv(export_path, index=False)
    audit.event("export", rows_in=len(deid), rows_out=len(deid), path=str(export_path))

    report_path = out / "data_quality_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    _write_markdown_report(report, out / "data_quality_report.md")
    audit.event("report", rows_in=len(deid), rows_out=len(deid))

    elapsed = time.perf_counter() - started
    summary = {
        "run_id": audit.run_id,
        "rows_in": report["rows_in"],
        "rows_out": report["rows_out"],
        "rows_excluded": report["excluded_rows"],
        "exclusion_reasons": report["exclusion_reasons"],
        "nulled_values": report["nulled_values"],
        "checks": report["checks"],
        "export_path": str(export_path),
        "elapsed_seconds": round(elapsed, 2),
        "used_default_salt": used_default_salt,
    }
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Secure research-data pipeline (synthetic data).")
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS, help="synthetic records to generate")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="random seed (reproducible runs)")
    parser.add_argument("--salt", type=str, default=None, help="hash salt (or PIPELINE_SALT env var)")
    parser.add_argument("--raw", type=str, default="data/raw/participants_raw.csv")
    parser.add_argument("--out-dir", type=str, default="outputs")
    parser.add_argument("--regenerate", action="store_true", help="regenerate the raw synthetic file")
    args = parser.parse_args(argv)

    summary = run(
        rows=args.rows,
        seed=args.seed,
        salt=args.salt,
        raw_path=args.raw,
        out_dir=args.out_dir,
        regenerate=args.regenerate,
    )
    print(f"run_id:            {summary['run_id']}")
    print(f"rows in:           {summary['rows_in']}")
    print(f"rows out:          {summary['rows_out']}")
    print(f"rows excluded:     {summary['rows_excluded']}")
    print(f"exclusions:        {summary['exclusion_reasons']}")
    print(f"nulled values:     {summary['nulled_values']}")
    print(f"export:            {summary['export_path']}")
    print(f"elapsed:           {summary['elapsed_seconds']}s")
    if summary["used_default_salt"]:
        print("warning: using the default development salt. Pass --salt or PIPELINE_SALT")


if __name__ == "__main__":
    main()
