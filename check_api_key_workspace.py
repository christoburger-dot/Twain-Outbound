"""Check which Email Bison workspace an API key belongs to.

Usage:
    python check_api_key_workspace.py <api_token>
    python check_api_key_workspace.py  # uses EMAILBISON_API_TOKEN from .env
"""

import sys
import requests


def check_workspace(token: str, base_url: str = "https://dedi.emailbison.com"):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    # Try common endpoints that reveal workspace/account info
    endpoints = [
        "/api/user",
        "/api/me",
        "/api/workspaces",
        "/api/workspace",
        "/api/account",
        "/api/sender-emails",
    ]

    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            print(f"\n{'='*60}")
            print(f"GET {endpoint} -> {resp.status_code}")
            print(f"{'='*60}")
            if resp.status_code == 200:
                import json
                print(json.dumps(resp.json(), indent=2))
            elif resp.status_code == 401:
                print("Unauthorized - invalid or expired API key")
                return
            else:
                print(resp.text[:500])
        except requests.RequestException as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        api_token = sys.argv[1]
    else:
        try:
            from dotenv import load_dotenv
            import os
            load_dotenv()
            api_token = os.environ.get("EMAILBISON_API_TOKEN", "")
        except ImportError:
            api_token = ""

    if not api_token:
        print("Usage: python check_api_key_workspace.py <api_token>")
        sys.exit(1)

    print(f"Checking workspace for token: {api_token[:10]}...")
    check_workspace(api_token)
