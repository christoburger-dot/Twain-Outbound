#!/usr/bin/env python3
"""Audit the 'April NA' EmailBison campaign.

Checks every lead's 'twain2' custom field for the exact verbatim sentence:
  "They run Twain in Clay, Claude, and HubSpot."
in the 4th paragraph of the Step 2 body.

Usage:
  pip install requests python-dotenv
  python3 audit_april_na.py
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.environ.get("EMAILBISON_API_TOKEN")
BASE_URL = os.environ.get("EMAILBISON_BASE_URL", "https://dedi.emailbison.com").rstrip("/")

EXPECTED_SENTENCE = "They run Twain in Clay, Claude, and HubSpot."
CAMPAIGN_NAME = "April NA"
CUSTOM_FIELD = "twain2"

if not API_TOKEN:
    sys.exit("ERROR: Set EMAILBISON_API_TOKEN in your .env file or environment.")

session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
})


def api_get(path, params=None):
    url = f"{BASE_URL}{path}"
    resp = session.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


# ── Step 1: Find the 'April NA' campaign ──────────────────────
print("Fetching campaigns...")
campaigns = api_get("/api/campaigns")

# Handle both list and paginated dict responses
if isinstance(campaigns, dict):
    campaign_list = campaigns.get("data", campaigns.get("campaigns", []))
else:
    campaign_list = campaigns

april_na = None
for c in campaign_list:
    if c.get("name", "").strip().lower() == CAMPAIGN_NAME.lower():
        april_na = c
        break

if not april_na:
    print(f"\nCould not find campaign '{CAMPAIGN_NAME}'. Available campaigns:")
    for c in campaign_list:
        print(f"  - {c.get('name')} (ID: {c.get('id')})")
    sys.exit(1)

campaign_id = april_na["id"]
print(f"Found campaign: '{april_na['name']}' (ID: {campaign_id})")

# ── Step 2: Fetch all leads (with pagination) ─────────────────
print("\nFetching leads...")
all_leads = []
page = 1

while True:
    result = api_get("/api/leads", params={"campaign_id": campaign_id, "page": page, "per_page": 100})

    # Handle both list and paginated dict responses
    if isinstance(result, dict):
        leads_page = result.get("data", result.get("leads", []))
        last_page = result.get("last_page", result.get("meta", {}).get("last_page"))
    else:
        leads_page = result
        last_page = None

    if not leads_page:
        break

    all_leads.extend(leads_page)
    print(f"  Page {page}: fetched {len(leads_page)} leads (total so far: {len(all_leads)})")

    # Stop if we've reached the last page or got fewer than requested
    if last_page and page >= last_page:
        break
    if len(leads_page) < 100:
        break
    page += 1

print(f"\nTotal leads fetched: {len(all_leads)}")

# ── Step 3: Audit each lead's 'twain2' custom field ───────────
mismatched = []
matched = 0

for lead in all_leads:
    email = lead.get("email", "unknown")
    first_name = lead.get("first_name", "")
    last_name = lead.get("last_name", "")
    company = lead.get("company", "")

    # Look for the custom field in various possible locations
    twain2_value = None

    # Check top-level field
    if CUSTOM_FIELD in lead:
        twain2_value = lead[CUSTOM_FIELD]

    # Check nested custom_fields dict
    if twain2_value is None and "custom_fields" in lead:
        cf = lead["custom_fields"]
        if isinstance(cf, dict):
            twain2_value = cf.get(CUSTOM_FIELD)
        elif isinstance(cf, list):
            for f in cf:
                if f.get("name") == CUSTOM_FIELD or f.get("key") == CUSTOM_FIELD:
                    twain2_value = f.get("value")
                    break

    # Check 'fields' dict
    if twain2_value is None and "fields" in lead:
        fields = lead["fields"]
        if isinstance(fields, dict):
            twain2_value = fields.get(CUSTOM_FIELD)

    if twain2_value is None:
        mismatched.append({
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "company": company,
            "issue": "MISSING — 'twain2' custom field not found",
            "actual_value": None,
        })
        continue

    # Check the 4th paragraph for the exact sentence
    twain2_str = str(twain2_value).strip()
    # Split into paragraphs (by double newline or <br> tags or <p> blocks)
    # Handle HTML content
    import re
    # Normalize: replace HTML paragraph/line breaks with newlines
    cleaned = re.sub(r'<br\s*/?>', '\n', twain2_str)
    cleaned = re.sub(r'</p>\s*<p[^>]*>', '\n\n', cleaned)
    cleaned = re.sub(r'<p[^>]*>', '', cleaned)
    cleaned = re.sub(r'</p>', '', cleaned)
    cleaned = re.sub(r'<[^>]+>', '', cleaned)  # strip remaining HTML tags

    # Split into paragraphs (blocks separated by blank lines)
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', cleaned.strip()) if p.strip()]

    # If splitting by double newline yields only 1 block, try single newline
    if len(paragraphs) < 4:
        paragraphs = [p.strip() for p in cleaned.strip().split('\n') if p.strip()]

    if len(paragraphs) < 4:
        mismatched.append({
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "company": company,
            "issue": f"TOO FEW PARAGRAPHS — only {len(paragraphs)} found (need at least 4)",
            "actual_value": twain2_str[:200],
        })
        continue

    fourth_para = paragraphs[3]

    if EXPECTED_SENTENCE in fourth_para:
        matched += 1
    else:
        mismatched.append({
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "company": company,
            "issue": "DIFFERENT TEXT in 4th paragraph",
            "fourth_paragraph": fourth_para[:300],
        })

# ── Step 4: Report ────────────────────────────────────────────
print("\n" + "=" * 70)
print("AUDIT REPORT — April NA Campaign, Step 2, 4th Paragraph")
print(f"Expected sentence: \"{EXPECTED_SENTENCE}\"")
print("=" * 70)
print(f"\nTotal leads:     {len(all_leads)}")
print(f"Matching:        {matched}")
print(f"NOT matching:    {len(mismatched)}")
print()

if mismatched:
    print("-" * 70)
    print("CONTACTS WITHOUT THE EXACT VERBATIM:")
    print("-" * 70)
    for i, m in enumerate(mismatched, 1):
        print(f"\n  {i}. {m['first_name']} {m['last_name']} — {m['email']}")
        print(f"     Company: {m['company']}")
        print(f"     Issue:   {m['issue']}")
        if "fourth_paragraph" in m:
            print(f"     Actual 4th paragraph (first 300 chars):")
            print(f"       \"{m['fourth_paragraph']}\"")
        elif m.get("actual_value"):
            print(f"     Field value (first 200 chars): \"{m['actual_value']}\"")
    print()
else:
    print("All leads have the exact verbatim sentence in the 4th paragraph!")

print("=" * 70)
print("Done.")
