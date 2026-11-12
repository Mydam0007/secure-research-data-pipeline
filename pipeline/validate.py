"""Checks the raw file before anything gets de-identified.

Rows that fail a critical check get dropped (missing study ID, duplicate
study ID, bad consent flag, date of birth that does not parse, or age at
enrollment outside 18-100). Lab values outside a plausible range get set
to null instead. The report only has counts, never participant values.
"""

from __future__ import annotations

import re

import pandas as pd

REQUIRED_COLUMNS = [
    "participant_id",
    "full_name",
    "email",
    "phone",
    "date_of_birth",
    "sex",
    "study_arm",
    "enrollment_date",
    "site",
    "consent_flag",
    "lab_glucose_mg_dl",
    "lab_hba1c_pct",
    "lab_cholesterol_mg_dl",
    "systolic_bp",
    "diastolic_bp",
]

# Plausible clinical ranges. Values outside these are treated as data
# errors, nulled in the export, and counted in the report.
RANGES = {
    "lab_glucose_mg_dl": (50.0, 500.0),
    "lab_hba1c_pct": (3.5, 15.0),
    "lab_cholesterol_mg_dl": (100.0, 400.0),
    "systolic_bp": (70, 220),
    "diastolic_bp": (40, 130),
}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Returns (clean_df, report). clean_df has the bad rows removed and
    the out-of-range lab values set to null. report holds counts only.
    """
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"missing required columns: {missing_cols}")

    report: dict = {
        "rows_in": int(len(df)),
        "checks": [],
        "excluded_rows": 0,
        "exclusion_reasons": {},
        "nulled_values": {},
        "null_counts_before": {c: int(df[c].isna().sum()) for c in df.columns},
    }
    work = df.copy()
    excluded = pd.Series(False, index=work.index)

    def exclude(mask: pd.Series, reason: str) -> None:
        nonlocal excluded
        new = mask & ~excluded
        count = int(new.sum())
        if count:
            report["exclusion_reasons"][reason] = count
            excluded = excluded | new

    # --- Critical checks: row-level exclusion ---
    exclude(work["participant_id"].isna(), "missing_participant_id")

    dup = work["participant_id"].duplicated(keep="first") & work["participant_id"].notna()
    exclude(dup, "duplicate_participant_id")

    bad_consent = ~work["consent_flag"].isin(["Y", "N"])
    exclude(bad_consent, "invalid_consent_flag")

    dob = pd.to_datetime(work["date_of_birth"], errors="coerce")
    exclude(dob.isna(), "unparseable_date_of_birth")

    enroll = pd.to_datetime(work["enrollment_date"], errors="coerce")
    age_years = (enroll - dob).dt.days / 365.25
    bad_age = (age_years < 18) | (age_years > 100)
    exclude(bad_age.fillna(False), "age_out_of_range_18_100")

    # --- Soft checks: null the value, keep the row ---
    # Range-check results are captured here, BEFORE nulling, so the
    # report reflects what was actually found.
    nulled: dict[str, int] = {}
    range_failed: dict[str, int] = {}
    range_passed: dict[str, int] = {}
    for col, (lo, hi) in RANGES.items():
        numeric = pd.to_numeric(work[col], errors="coerce")
        bad = numeric.notna() & ((numeric < lo) | (numeric > hi))
        count = int((bad & ~excluded).sum())
        if count:
            nulled[col] = count
        range_failed[col] = count
        range_passed[col] = int((numeric.between(lo, hi) & ~excluded).sum())
        work.loc[bad, col] = None
    report["nulled_values"] = nulled

    bad_email = ~work["email"].astype(str).str.match(EMAIL_RE, na=False)
    report["checks"].append(
        {
            "name": "email_format",
            "failed": int((bad_email & ~excluded).sum()),
            "passed": int(((~bad_email) & ~excluded).sum()),
        }
    )

    for col, (lo, hi) in RANGES.items():
        report["checks"].append(
            {
                "name": f"{col}_in_range_{lo}_{hi}",
                "failed": range_failed[col],
                "passed": range_passed[col],
            }
        )

    report["checks"].append(
        {
            "name": "duplicate_participant_id",
            "failed": int(report["exclusion_reasons"].get("duplicate_participant_id", 0)),
            "passed": int((~excluded).sum()),
        }
    )

    clean = work.loc[~excluded].copy()
    report["excluded_rows"] = int(excluded.sum())
    report["rows_out"] = int(len(clean))
    report["null_counts_after"] = {c: int(clean[c].isna().sum()) for c in clean.columns}
    return clean, report
