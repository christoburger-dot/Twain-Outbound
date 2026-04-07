"""Load and normalize leads from a CSV file."""

import pandas as pd


REQUIRED_COLUMNS = {"email"}
OPTIONAL_COLUMNS = {
    "first_name", "last_name", "company", "domain",
    "title", "linkedin_url", "phone",
}


def load_leads(csv_path: str) -> list[dict]:
    """Read a CSV and return a list of lead dicts.

    The CSV must have at least an 'email' column.
    All other recognized columns are included if present.
    """
    df = pd.read_csv(csv_path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")

    # Drop rows with no email
    df = df.dropna(subset=["email"])
    df["email"] = df["email"].str.strip().str.lower()

    # Keep only recognized columns that exist
    keep = list((REQUIRED_COLUMNS | OPTIONAL_COLUMNS) & set(df.columns))
    df = df[keep]

    return df.to_dict(orient="records")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.lead_loader <path_to_csv>")
        sys.exit(1)

    leads = load_leads(sys.argv[1])
    print(f"Loaded {len(leads)} leads")
    for lead in leads[:3]:
        print(f"  {lead}")
