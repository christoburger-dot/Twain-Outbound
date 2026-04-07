"""Generate personalized email copy.

This module supports two modes:
1. Twain MCP (preferred) — used when running inside Claude Code with Twain MCP connected.
   In this mode, Claude calls Twain tools directly during the orchestration conversation.

2. Twain REST API — standalone fallback for running outside Claude Code.
   Requires TWAIN_API_KEY in .env.

When using Claude Code with Twain MCP, you don't call this module directly.
Instead, you tell Claude: "Use Twain to generate a personalized cold email for
this lead: {lead_data}" and Claude will use the MCP tools.

This module provides the REST API fallback and a template-based fallback.
"""

import os
import json
import requests


def generate_copy_via_twain_api(
    lead: dict,
    campaign_context: str,
    twain_api_key: str | None = None,
) -> dict:
    """Call Twain's API to generate personalized email copy for a single lead.

    Returns: {"subject": str, "body": str}

    NOTE: Twain's exact API endpoint and payload format may vary.
    Update the URL and payload below based on your Twain API docs.
    """
    api_key = twain_api_key or os.environ.get("TWAIN_API_KEY")
    if not api_key:
        raise ValueError("TWAIN_API_KEY not set. Provide it in .env or as argument.")

    # TODO: Update this URL and payload based on Twain's actual API docs
    # This is a placeholder based on Twain's known capabilities
    url = "https://api.twain.ai/v1/generate"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "prospect": {
            "email": lead.get("email"),
            "first_name": lead.get("first_name"),
            "last_name": lead.get("last_name"),
            "company": lead.get("company"),
            "title": lead.get("title"),
            "domain": lead.get("domain"),
            "linkedin_url": lead.get("linkedin_url"),
        },
        "campaign_context": campaign_context,
        "output_format": "email",
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    return {
        "subject": data.get("subject", ""),
        "body": data.get("body", data.get("message", "")),
    }


def generate_copy_template(lead: dict, campaign_context: str) -> dict:
    """Simple merge-field template fallback (no API needed).

    Use this for testing or if Twain is unavailable.
    """
    first_name = lead.get("first_name", "there")
    company = lead.get("company", "your company")
    title = lead.get("title", "")

    subject = f"{first_name}, quick question about {company}"
    body = f"""Hi {first_name},

I came across {company} and noticed {f"your work as {title}" if title else "what you're building"}.

{campaign_context}

Would you be open to a quick chat this week?

Best,
{{{{sender_name}}}}"""

    return {"subject": subject, "body": body}


def generate_copy_for_leads(
    leads: list[dict],
    campaign_context: str,
    mode: str = "template",
    twain_api_key: str | None = None,
) -> list[dict]:
    """Generate email copy for a list of leads.

    Args:
        leads: List of lead dicts (from lead_loader)
        campaign_context: Description of what you're selling / campaign goal
        mode: "twain_api" to use Twain REST API, "template" for simple fallback
        twain_api_key: Optional Twain API key override

    Returns:
        List of dicts with lead data + "subject" and "body" fields added
    """
    results = []
    for lead in leads:
        if mode == "twain_api":
            copy = generate_copy_via_twain_api(lead, campaign_context, twain_api_key)
        else:
            copy = generate_copy_template(lead, campaign_context)

        results.append({**lead, **copy})

    return results
