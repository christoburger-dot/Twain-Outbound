"""Email Bison REST API client.

Docs: https://docs.emailbison.com/get-started/introduction
API Reference: https://dedi.emailbison.com/api/reference

Authentication: Bearer token created at Settings -> Developer API -> New API Token.
"""

import time
import requests

from .config import EMAILBISON_API_TOKEN, EMAILBISON_BASE_URL


class EmailBisonClient:
    def __init__(self):
        self.base_url = EMAILBISON_BASE_URL.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {EMAILBISON_API_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}{path}"
        resp = self.session.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    # ── Campaigns ──────────────────────────────────────────────

    def list_campaigns(self) -> list[dict]:
        return self._request("GET", "/api/campaigns")

    def get_campaign(self, campaign_id: int) -> dict:
        return self._request("GET", f"/api/campaigns/{campaign_id}")

    def create_campaign(self, name: str, **kwargs) -> dict:
        """Create a new campaign.

        kwargs can include any additional fields the API supports
        (e.g., daily_limit, timezone, etc.)
        """
        payload = {"name": name, **kwargs}
        return self._request("POST", "/api/campaigns", json=payload)

    def update_campaign(self, campaign_id: int, **kwargs) -> dict:
        return self._request("PATCH", f"/api/campaigns/{campaign_id}", json=kwargs)

    def pause_campaign(self, campaign_id: int) -> dict:
        return self._request("POST", f"/api/campaigns/{campaign_id}/pause")

    def attach_sender_emails(self, campaign_id: int, sender_email_ids: list[int]) -> dict:
        return self._request(
            "POST",
            f"/api/campaigns/{campaign_id}/attach-sender-emails",
            json={"sender_email_ids": sender_email_ids},
        )

    # ── Sequence Steps ─────────────────────────────────────────

    def list_sequence_steps(self, campaign_id: int) -> list[dict]:
        return self._request("GET", f"/api/campaigns/{campaign_id}/sequence-steps")

    def create_sequence_step(
        self,
        campaign_id: int,
        subject: str,
        body: str,
        delay_days: int = 0,
        step_type: str = "email",
        **kwargs,
    ) -> dict:
        """Add a sequence step (email) to a campaign."""
        payload = {
            "campaign_id": campaign_id,
            "subject": subject,
            "body": body,
            "delay_days": delay_days,
            "type": step_type,
            **kwargs,
        }
        return self._request("POST", "/api/campaigns/sequence-steps", json=payload)

    def send_test_email(self, sequence_step_id: int) -> dict:
        return self._request(
            "POST", f"/api/campaigns/sequence-steps/{sequence_step_id}/send-test"
        )

    # ── Leads ──────────────────────────────────────────────────

    def list_leads(self, **params) -> list[dict]:
        return self._request("GET", "/api/leads", params=params)

    def create_lead(self, lead_data: dict) -> dict:
        return self._request("POST", "/api/leads", json=lead_data)

    def update_lead(self, lead_id: int, lead_data: dict) -> dict:
        return self._request("PUT", f"/api/leads/{lead_id}", json=lead_data)

    def create_leads_batch(self, leads: list[dict], delay: float = 0.2) -> list[dict]:
        """Create multiple leads with a small delay to respect rate limits."""
        results = []
        for lead in leads:
            result = self.create_lead(lead)
            results.append(result)
            time.sleep(delay)
        return results

    # ── Sender Emails ──────────────────────────────────────────

    def list_sender_emails(self) -> list[dict]:
        return self._request("GET", "/api/sender-emails")

    # ── Tags ───────────────────────────────────────────────────

    def list_tags(self) -> list[dict]:
        return self._request("GET", "/api/tags")

    def attach_tags_to_leads(self, tag_ids: list[int], lead_ids: list[int]) -> dict:
        return self._request(
            "POST",
            "/api/tags/attach-to-leads",
            json={"tag_ids": tag_ids, "lead_ids": lead_ids},
        )

    # ── Replies ────────────────────────────────────────────────

    def list_replies(self, **params) -> list[dict]:
        return self._request("GET", "/api/replies", params=params)
