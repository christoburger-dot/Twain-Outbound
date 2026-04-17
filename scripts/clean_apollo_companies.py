"""Clean the Apollo 1000 Companies CSV to Twain's B2B SaaS ICP.

Filters, de-duplicates, normalizes URLs, and removes any company whose domain
appears in the "April NA" or "April EU" outbound contact CSVs
(or, as a fallback, in the corresponding live Email Bison campaigns).
"""

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


SRC = REPO_ROOT / "Twain_Apollo_1000_Companies-Default-view-export-1776435726357.csv"
OUT = REPO_ROOT / "data" / "apollo_1000_companies_cleaned.csv"
EXCLUSION_CSVS = {
    "April NA": REPO_ROOT / "USA April Outbound.csv",
    "April EU": REPO_ROOT / "EU April Outbound.csv",
}
CONTACT_COMPANY_COLUMN = "Company"

REVENUE_MIN = 10_000_000
REVENUE_MAX = 500_000_000
FOUNDED_MIN = 2005


def normalize_url(u):
    if pd.isna(u) or not str(u).strip():
        return ""
    u = str(u).strip().rstrip("/")
    if u.startswith("http://"):
        u = "https://" + u[len("http://"):]
    return u


def normalize_name(s) -> str:
    """Lowercase and strip all non-alphanumerics (matches 'Orum 🥇' to 'orum')."""
    if pd.isna(s):
        return ""
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())


def names_from_contacts_csv(path: Path) -> set[str]:
    df = pd.read_csv(path)
    df.columns = [c.strip().lstrip("\ufeff") for c in df.columns]
    if CONTACT_COMPANY_COLUMN not in df.columns:
        raise SystemExit(
            f"{path.name} has no '{CONTACT_COMPANY_COLUMN}' column (cols: {list(df.columns)})"
        )
    return {n for n in df[CONTACT_COMPANY_COLUMN].map(normalize_name) if n}


def build_exclusion_set():
    per_source: dict[str, int] = {}
    exclude: set[str] = set()
    missing_csvs = [name for name, p in EXCLUSION_CSVS.items() if not p.exists()]
    if missing_csvs:
        raise SystemExit(
            f"Missing exclusion CSVs: {missing_csvs}. "
            f"Expected files: {[str(p) for p in EXCLUSION_CSVS.values()]}"
        )
    for name, path in EXCLUSION_CSVS.items():
        names = names_from_contacts_csv(path)
        per_source[f"{name} ({path.name})"] = len(names)
        exclude |= names
    return exclude, per_source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-exclusion",
        action="store_true",
        help="Skip the April NA/EU exclusion step.",
    )
    args = parser.parse_args()

    df = pd.read_csv(SRC)
    n0 = len(df)
    df = df.drop(columns=["New Column"], errors="ignore")

    before = len(df)
    df = df[df["SaaS Status & Reason"].astype(str).str.strip().str.lower() == "true"]
    saas_drop = before - len(df)

    before = len(df)
    df["Revenue (USD)"] = pd.to_numeric(df["Revenue (USD)"], errors="coerce")
    df = df[df["Revenue (USD)"].between(REVENUE_MIN, REVENUE_MAX)]
    rev_drop = before - len(df)

    before = len(df)
    df["Founded Year"] = pd.to_numeric(df["Founded Year"], errors="coerce")
    df = df[df["Founded Year"] >= FOUNDED_MIN]
    year_drop = before - len(df)

    before = len(df)
    domain_clean = df["Domain"].astype(str).str.strip()
    df = df[domain_clean.ne("") & domain_clean.ne("nan") & df["Domain"].notna()]
    domain_drop = before - len(df)

    df["Domain"] = df["Domain"].astype(str).str.strip().str.lower()
    df = df.drop_duplicates(subset=["Domain"], keep="first")

    for col in ("Website", "LinkedIn URL"):
        if col in df.columns:
            df[col] = df[col].map(normalize_url)

    if args.skip_exclusion:
        exclude, per_source = set(), {}
        print("Skipping April NA/EU exclusion (--skip-exclusion).", file=sys.stderr)
    else:
        exclude, per_source = build_exclusion_set()

    before = len(df)
    apollo_name_key = df["Company Name"].map(normalize_name)
    df = df[~apollo_name_key.isin(exclude)]
    exclude_drop = before - len(df)

    OUT.parent.mkdir(exist_ok=True)
    df.to_csv(OUT, index=False)

    print(
        f"{n0} -> {len(df)}  "
        f"(saas:-{saas_drop} rev:-{rev_drop} year:-{year_drop} "
        f"domain:-{domain_drop} exclusion:-{exclude_drop})"
    )
    for src, count in per_source.items():
        print(f"  {src}: {count} unique domains in exclusion set")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
