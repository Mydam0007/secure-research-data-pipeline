"""Strips identifiers out of a validated frame before export.

Names, emails and study IDs get replaced by a salted SHA-256 hash.
Phone numbers are dropped. Dates of birth become an age band plus birth
year, and enrollment dates become just the year.

The salt comes from --salt or PIPELINE_SALT. If neither is set it falls
back to a dev default and the run gets flagged in the audit log. In real
use the salt would live in a secrets store, not in the code.
"""

from __future__ import annotations

import hashlib
import os

import pandas as pd

DEFAULT_SALT = "dev-salt-change-me"

AGE_BANDS = [
    (18.0, 30.0, "18-29"),
    (30.0, 40.0, "30-39"),
    (40.0, 50.0, "40-49"),
    (50.0, 60.0, "50-59"),
    (60.0, 70.0, "60-69"),
    (70.0, 80.0, "70-79"),
    (80.0, 90.0, "80-89"),
    (90.0, 200.0, "90+"),
]


def get_salt(explicit: str | None = None) -> tuple[str, bool]:
    """Return ``(salt, used_default)``."""
    salt = explicit or os.environ.get("PIPELINE_SALT")
    if salt:
        return salt, False
    return DEFAULT_SALT, True


def _hash(value: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()


def _age_band(age_years: float) -> str:
    if pd.isna(age_years):
        return "unknown"
    for lo, hi, label in AGE_BANDS:
        if lo <= age_years < hi:
            return label
    return "unknown"


def deidentify(df: pd.DataFrame, salt: str) -> pd.DataFrame:
    """Return the de-identified view of a validated frame."""
    work = df.copy()

    dob = pd.to_datetime(work["date_of_birth"], errors="coerce")
    enroll = pd.to_datetime(work["enrollment_date"], errors="coerce")
    age_years = (enroll - dob).dt.days / 365.25

    out = pd.DataFrame(
        {
            "participant_hash": work["participant_id"].astype(str).map(lambda v: _hash(v, salt)),
            "name_hash": work["full_name"].astype(str).map(lambda v: _hash(v, salt)),
            "email_hash": work["email"].astype(str).map(
                lambda v: _hash(v.strip().lower(), salt) if v.strip() else None
            ),
            "age_band": age_years.map(_age_band),
            "birth_year": dob.dt.year,
            "sex": work["sex"],
            "study_arm": work["study_arm"],
            "enrollment_year": enroll.dt.year,
            "site": work["site"],
            "consent_flag": work["consent_flag"],
            "lab_glucose_mg_dl": pd.to_numeric(work["lab_glucose_mg_dl"], errors="coerce"),
            "lab_hba1c_pct": pd.to_numeric(work["lab_hba1c_pct"], errors="coerce"),
            "lab_cholesterol_mg_dl": pd.to_numeric(
                work["lab_cholesterol_mg_dl"], errors="coerce"
            ),
            "systolic_bp": pd.to_numeric(work["systolic_bp"], errors="coerce"),
            "diastolic_bp": pd.to_numeric(work["diastolic_bp"], errors="coerce"),
        }
    )
    return out


# Columns that must never appear in the export. Checked by the runner
# after de-identification as a safety net.
FORBIDDEN_COLUMNS = {
    "full_name",
    "email",
    "phone",
    "date_of_birth",
    "enrollment_date",
    "participant_id",
}
