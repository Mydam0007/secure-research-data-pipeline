"""Makes up the raw data. All 1,200 rows are fake, made with a fixed seed
so every run with the same seed gives the same file.

A few bad rows get mixed in on purpose (missing values, out-of-range lab
results, duplicate study IDs, bad emails, bad consent flags) so the
validation step has something to catch.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

FIRST_NAMES = [
    "Ava", "Liam", "Maya", "Noah", "Zoe", "Ethan", "Ruby", "Owen",
    "Isla", "Lucas", "Nora", "Mason", "Ella", "Logan", "Ivy", "James",
    "Luna", "Henry", "Chloe", "Leo", "Mia", "Jack", "Amara", "Eli",
    "Sofia", "Caleb", "Priya", "Omar", "Tara", "Felix", "Nina", "Hugo",
    "Lena", "Marcus", "Aisha", "Diego", "Kira", "Sam", "Rosa", "Ivan",
    "Mei", "Jonas", "Farah", "Tomas", "Elif", "Ravi", "Greta", "Yusuf",
    "Clara", "Dante",
]

LAST_NAMES = [
    "Anderson", "Patel", "Kim", "Garcia", "Nguyen", "Smith", "Chen",
    "Okafor", "Rossi", "Khan", "Muller", "Santos", "Haddad", "Novak",
    "Tanaka", "Ali", "Brooks", "Fischer", "Dubois", "Costa", "Reyes",
    "Ahmed", "Larsen", "Moreau", "Silva", "Petrov", "Osei", "Lindqvist",
    "Marino", "Kaur", "Weber", "Nakamura", "Ferrara", "Dube", "Kowalski",
    "Vargas", "Haddad", "Osei", "Lindgren", "Barros", "Singh", "Novak",
    "Keller", "Adeyemi", "Berg", "Costa", "Rahman", "Silva", "Park",
]

DOMAINS = ["example.org", "example.com", "example.net", "mail.example.org"]
SITES = ["Site A", "Site B", "Site C", "Site D"]
ARMS = ["Control", "Treatment A", "Treatment B"]

COLUMNS = [
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

ENROLL_START = date(2023, 1, 1)
ENROLL_END = date(2026, 6, 30)


def _random_date(rng: random.Random, start: date, end: date) -> date:
    span = (end - start).days
    return start + timedelta(days=rng.randrange(span + 1))


def generate(n: int = 1200, seed: int = 42) -> pd.DataFrame:
    """Generate ``n`` synthetic research-participant records."""
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        dob = _random_date(rng, date(1936, 1, 1), date(2004, 12, 31))
        enroll = _random_date(rng, ENROLL_START, ENROLL_END)
        rows.append(
            {
                "participant_id": f"P-{100001 + i}",
                "full_name": f"{first} {last}",
                "email": f"{first.lower()}.{last.lower()}{rng.randrange(100)}@{rng.choice(DOMAINS)}",
                "phone": f"+1-555-{rng.randrange(100, 1000):03d}-{rng.randrange(1000, 10000):04d}",
                "date_of_birth": dob.isoformat(),
                "sex": rng.choice(["F", "M"]),
                "study_arm": rng.choice(ARMS),
                "enrollment_date": enroll.isoformat(),
                "site": rng.choice(SITES),
                "consent_flag": "Y" if rng.random() < 0.99 else "N",
                "lab_glucose_mg_dl": round(rng.gauss(110, 30), 1),
                "lab_hba1c_pct": round(rng.gauss(6.0, 1.2), 1),
                "lab_cholesterol_mg_dl": round(rng.gauss(200, 40), 1),
                "systolic_bp": rng.randrange(95, 175),
                "diastolic_bp": rng.randrange(55, 115),
            }
        )

    df = pd.DataFrame(rows, columns=COLUMNS)

    # --- Inject deterministic data-quality defects (seeded) ---
    idx = list(range(n))

    # 2% missing lab values per lab column.
    for col in [
        "lab_glucose_mg_dl",
        "lab_hba1c_pct",
        "lab_cholesterol_mg_dl",
        "systolic_bp",
        "diastolic_bp",
    ]:
        for j in rng.sample(idx, k=max(1, n // 50)):
            df.at[j, col] = None

    # Out-of-range lab values (will be nulled by validation).
    for j in rng.sample(idx, k=18):
        df.at[j, "lab_glucose_mg_dl"] = rng.choice([5.0, 650.0, 920.0])
    for j in rng.sample(idx, k=12):
        df.at[j, "lab_hba1c_pct"] = rng.choice([1.5, 18.0, 22.5])
    for j in rng.sample(idx, k=15):
        df.at[j, "lab_cholesterol_mg_dl"] = rng.choice([-40.0, 640.0, 900.0])
    for j in rng.sample(idx, k=10):
        df.at[j, "systolic_bp"] = rng.choice([45, 260, 310])
    for j in rng.sample(idx, k=8):
        df.at[j, "diastolic_bp"] = rng.choice([15, 180, 210])

    # Duplicate study IDs: 6 rows copy another row's ID (excluded at validation).
    for j in rng.sample(idx[1:], k=6):
        df.at[j, "participant_id"] = df.at[rng.randrange(j), "participant_id"]

    # Missing study IDs: 3 rows.
    for j in rng.sample(idx, k=3):
        df.at[j, "participant_id"] = None

    # Malformed emails: 12 rows.
    for j in rng.sample(idx, k=12):
        df.at[j, "email"] = rng.choice(
            ["not-an-email", "missing-at-sign.example.org", "", "two@@ats.example.com"]
        )

    # Invalid dates of birth: 6 rows (future dates / implausibly old).
    for j in rng.sample(idx, k=6):
        df.at[j, "date_of_birth"] = rng.choice(
            ["2027-05-01", "2028-01-15", "1890-03-22", "not-a-date"]
        )

    # Invalid consent flags: 6 rows.
    for j in rng.sample(idx, k=6):
        df.at[j, "consent_flag"] = rng.choice(["maybe", "", "X"])

    return df


def write_raw(n: int = 1200, seed: int = 42, path: str | Path = "data/raw/participants_raw.csv") -> Path:
    """Generate the raw file and return its path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df = generate(n=n, seed=seed)
    df.to_csv(path, index=False)
    return path
