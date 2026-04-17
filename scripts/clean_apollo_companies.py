"""Clean the Apollo 1000 Companies CSV to Twain's B2B SaaS ICP.

Filters, de-duplicates, normalizes URLs, and removes any company whose domain
is already in the active "April NA" or "April EU" Email Bison campaigns.
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


SRC = REPO_ROOT / "Twain_Apollo_1000_Companies-Default-view-export-1776435726357.csv"
OUT = REPO_ROOT / "data" / "apollo_1000_companies_cleaned.csv"
EXCLUDE_CAMPAIGNS = ("April NA", "April EU")

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


def _unwrap(payload, keys=("data", "campaigns", "leads")):
    if isinstance(payload, dict):
        for k in keys:
            if k in payload and isinstance(payload[k], list):
                return payload[k]
        return []
    return payload or []


def fetch_campaign_domains(client, name: str):
    campaigns = _unwrap(client.list_campaigns())
    target = next(
        (c for c in campaigns if c.get("name", "").strip().lower() == name.lower()),
        None,
    )
    if not target:
        available = ", ".join(c.get("name", "?") for c in campaigns) or "(none)"
        raise SystemExit(f"Campaign '{name}' not found. Available: {available}")

    campaign_id = target["id"]
    domains: set[str] = set()
    page = 1
    while True:
        result = client.list_leads(campaign_id=campaign_id, page=page, per_page=100)
        leads = _unwrap(result)
        if not leads:
            break
        for lead in leads:
            email = (lead.get("email") or "").strip().lower()
            if "@" in email:
                domains.add(email.split("@", 1)[1])
            d = (lead.get("domain") or "").strip().lower()
            if d:
                domains.add(d)
        if len(leads) < 100:
            break
        page += 1
    return campaign_id, domains


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-bison",
        action="store_true",
        help="Skip the Email Bison exclusion step (use when EMAILBISON_API_TOKEN is not set).",
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

    exclude: set[str] = set()
    per_campaign: dict[str, int] = {}
    skip_bison = args.skip_bison or not os.environ.get("EMAILBISON_API_TOKEN")
    if skip_bison:
        print(
            "WARNING: skipping Email Bison exclusion "
            "(set EMAILBISON_API_TOKEN and rerun without --skip-bison to apply).",
            file=sys.stderr,
        )
    else:
        from src.emailbison_client import EmailBisonClient  # noqa: WPS433

        client = EmailBisonClient()
        for name in EXCLUDE_CAMPAIGNS:
            _, domains = fetch_campaign_domains(client, name)
            per_campaign[name] = len(domains)
            exclude |= domains

    before = len(df)
    df = df[~df["Domain"].isin(exclude)]
    eb_drop = before - len(df)

    OUT.parent.mkdir(exist_ok=True)
    df.to_csv(OUT, index=False)

    print(
        f"{n0} -> {len(df)}  "
        f"(saas:-{saas_drop} rev:-{rev_drop} year:-{year_drop} "
        f"domain:-{domain_drop} bison:-{eb_drop})"
    )
    for name, count in per_campaign.items():
        print(f"  {name}: {count} unique domains in exclusion set")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
