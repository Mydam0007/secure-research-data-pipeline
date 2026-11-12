# Secure Research-Data Pipeline

I built this to show how I handle sensitive research data: take in messy participant records, check the quality, strip out anything that can identify a person, and keep a record of what happened to every row.

Everything here is synthetic. All 1,200 records are made up by a seeded generator, so there are no real people and no real patient data anywhere in this project. I made it as an independent portfolio project. It is not connected to USC in any way.

## What it does

1. **Generate** a raw file of 1,200 fake participant records (names, emails, dates of birth, lab values, consent flags). A few bad rows are mixed in on purpose: missing values, out-of-range labs, duplicate study IDs, bad emails, bad consent flags.
2. **Validate** the file. Rows with missing study IDs, duplicate study IDs, bad consent flags, or dates of birth that do not parse get dropped. Out-of-range lab values get set to null. Everything is counted.
3. **De-identify** the rest. Names, emails and study IDs get hashed with a salted SHA-256 hash. Phone numbers are dropped. Dates of birth become an age band plus birth year, and enrollment dates become just the year. The export has no raw identifiers in it, and the run fails if any identifier column is still there.
4. **Report and audit.** A data-quality report (JSON and Markdown) and an audit log (JSONL, one event per stage). Both hold counts only, never participant values.

## How to run

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

`--rows` and `--seed` control the fake data. `--salt` (or the `PIPELINE_SALT` environment variable) sets the hash salt. Without one it falls back to a dev default and the run gets flagged in the audit log. In real use the salt would live in a secrets store, not in the code.

With Docker:

```bash
docker build -t secure-research-data-pipeline .
docker run --rm -v "$PWD/outputs:/app/outputs" secure-research-data-pipeline
```

## What came out

Ran with seed 42 on Python 3.12, pandas 2.1.4. Pipeline time 0.05 s, 0.54 s wall-clock. Same seed gives a byte-identical export.

- Rows in: 1,200. Rows out: 1,180.
- 20 rows dropped: 3 missing study ID, 6 duplicate study ID, 6 bad consent flag, 2 dates of birth that did not parse, 3 age outside 18 to 100 at enrollment.
- 124 lab values set to null because they were out of range: glucose 51, HbA1c 31, cholesterol 24, systolic BP 10, diastolic BP 8.
- 4 fields hashed (name, email, phone, study ID), 2 generalized (date of birth to age band plus birth year, enrollment date to year).

`verify_outputs.py` checks the outputs on its own: no identifier columns or raw values in any output file, no email pattern anywhere, the audit log parses as JSONL, hashes are 64-character hex, and the row counts add up. All 21 checks pass.

```bash
python verify_outputs.py
```

After a run, `outputs/` has the de-identified CSV, the data-quality report, and the audit log. The raw file lives in `data/raw/` and never gets written to `outputs/`. Both folders are git-ignored: the raw file looks like real PII even though every record is fake, and the outputs can be rebuilt from the seed.

## Stack

Python 3.12, pandas, Docker. Nothing else.

## A few things worth knowing

- The data is fake and the default salt is for development only. Neither would do for real participant data.
- Hashing with a salt is pseudonymization, not anonymization. With the salt and the source data the hashes can be reversed, which is why the raw file is still treated as sensitive.
- This shows the technique. It is not a compliance certification and does not claim to be one.
