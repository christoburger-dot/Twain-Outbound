#!/usr/bin/env python3
"""Cold email campaign orchestrator.

This script ties together the full pipeline:
1. Load leads from CSV
2. Generate personalized email copy (via Twain API or template)
3. Push leads and campaign to Email Bison

Usage:
    python run_campaign.py --csv data/leads.csv --campaign "My Campaign" --context "We help B2B companies..."

For Twain MCP mode (recommended):
    Run this interactively in Claude Code instead. Tell Claude:
    "Load my leads from data/leads.csv, use Twain to personalize each email,
     then push everything to Email Bison as a campaign called 'My Campaign'"
"""

import argparse
import json
import sys

from src.lead_loader import load_leads
from src.copy_generator import generate_copy_for_leads
from src.emailbison_client import EmailBisonClient


def main():
    parser = argparse.ArgumentParser(description="Cold email campaign pipeline")
    parser.add_argument("--csv", required=True, help="Path to leads CSV file")
    parser.add_argument("--campaign", required=True, help="Campaign name in Email Bison")
    parser.add_argument(
        "--context",
        required=True,
        help="Campaign context / what you're selling (used for copy generation)",
    )
    parser.add_argument(
        "--mode",
        choices=["twain_api", "template"],
        default="template",
        help="Copy generation mode (default: template). Use 'twain_api' for Twain REST API.",
    )
    parser.add_argument(
        "--sender-email-ids",
        type=str,
        default="",
        help="Comma-separated sender email IDs to attach to the campaign",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate copy and print results without pushing to Email Bison",
    )
    args = parser.parse_args()

    # Step 1: Load leads
    print(f"Loading leads from {args.csv}...")
    leads = load_leads(args.csv)
    print(f"  Loaded {len(leads)} leads")

    # Step 2: Generate copy
    print(f"Generating email copy (mode: {args.mode})...")
    leads_with_copy = generate_copy_for_leads(leads, args.context, mode=args.mode)
    print(f"  Generated copy for {len(leads_with_copy)} leads")

    # Preview first lead
    if leads_with_copy:
        first = leads_with_copy[0]
        print(f"\n  Preview (first lead):")
        print(f"  To: {first['email']}")
        print(f"  Subject: {first['subject']}")
        print(f"  Body:\n    {first['body'][:200]}...")

    if args.dry_run:
        print("\n[DRY RUN] Skipping Email Bison push. Results:")
        print(json.dumps(leads_with_copy[:3], indent=2))
        return

    # Step 3: Push to Email Bison
    client = EmailBisonClient()

    # 3a: Create campaign
    print(f"\nCreating campaign '{args.campaign}' in Email Bison...")
    campaign = client.create_campaign(args.campaign)
    campaign_id = campaign.get("id") or campaign.get("data", {}).get("id")
    print(f"  Campaign created: ID {campaign_id}")

    # 3b: Attach sender emails
    if args.sender_email_ids:
        sender_ids = [int(x.strip()) for x in args.sender_email_ids.split(",")]
        print(f"  Attaching sender emails: {sender_ids}")
        client.attach_sender_emails(campaign_id, sender_ids)

    # 3c: Create sequence step with the first lead's copy as template
    # (Email Bison uses templates with merge fields like {{first_name}})
    first_copy = leads_with_copy[0]
    print("  Creating sequence step (email template)...")
    step = client.create_sequence_step(
        campaign_id=campaign_id,
        subject=first_copy["subject"],
        body=first_copy["body"],
        delay_days=0,
    )
    print(f"  Sequence step created: {step}")

    # 3d: Upload leads to campaign
    print(f"  Uploading {len(leads_with_copy)} leads...")
    for i, lead in enumerate(leads_with_copy):
        lead_payload = {
            "email": lead["email"],
            "first_name": lead.get("first_name", ""),
            "last_name": lead.get("last_name", ""),
            "company": lead.get("company", ""),
            "campaign_id": campaign_id,
        }
        try:
            client.create_lead(lead_payload)
            if (i + 1) % 25 == 0:
                print(f"    Uploaded {i + 1}/{len(leads_with_copy)} leads...")
        except Exception as e:
            print(f"    Error uploading lead {lead['email']}: {e}")

    print(f"\nDone! Campaign '{args.campaign}' is ready in Email Bison.")
    print(f"  Campaign ID: {campaign_id}")
    print(f"  Leads uploaded: {len(leads_with_copy)}")
    print(f"\n  Next steps:")
    print(f"  1. Review the campaign in Email Bison dashboard")
    print(f"  2. Verify sender emails are warmed up")
    print(f"  3. Send a test email before launching")
    print(f"  4. Activate the campaign when ready")


if __name__ == "__main__":
    main()
