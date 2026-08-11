"""Exchanges a fresh short-lived Facebook User Access Token (from Graph API
Explorer) for a long-lived Page Access Token, and writes it into .env.

Usage: .venv/bin/python scripts/refresh_fb_token.py
Then paste the short-lived user token when prompted.
"""

import logging
import os
import re
import sys

import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logging_config import setup_logging

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")

logger = logging.getLogger(__name__)


def exchange_for_long_lived_user_token(short_lived_token, app_id, app_secret):
    response = requests.get(
        f"{GRAPH_API_BASE}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_lived_token,
        },
    )
    body = response.json()
    if "error" in body:
        raise RuntimeError(f"Token exchange failed: {body['error']}")
    return body["access_token"]


def get_page_token(long_lived_user_token, page_id):
    response = requests.get(
        f"{GRAPH_API_BASE}/me/accounts",
        params={"access_token": long_lived_user_token},
    )
    body = response.json()
    if "error" in body:
        raise RuntimeError(f"Fetching pages failed: {body['error']}")

    for page in body.get("data", []):
        if page["id"] == page_id:
            return page["access_token"]

    raise RuntimeError(f"Page id {page_id} not found in /me/accounts response: {body}")


def update_env_var(key, value):
    with open(ENV_PATH) as f:
        lines = f.readlines()

    pattern = re.compile(rf"^{re.escape(key)}=.*$")
    replaced = False
    for i, line in enumerate(lines):
        if pattern.match(line.strip()):
            lines[i] = f"{key}={value}\n"
            replaced = True
            break

    if not replaced:
        lines.append(f"{key}={value}\n")

    with open(ENV_PATH, "w") as f:
        f.writelines(lines)


def main():
    setup_logging()
    load_dotenv()

    app_id = os.environ["FACEBOOK_APP_ID"]
    app_secret = os.environ["FACEBOOK_APP_SECRET"]
    page_id = os.environ["FACEBOOK_PAGE_ID"]

    short_lived_token = input(
        "Paste the short-lived User Access Token from Graph API Explorer: "
    ).strip()

    logger.info("Exchanging for a long-lived user token...")
    long_lived_user_token = exchange_for_long_lived_user_token(
        short_lived_token, app_id, app_secret
    )

    logger.info("Fetching long-lived Page token...")
    page_token = get_page_token(long_lived_user_token, page_id)

    update_env_var("FACEBOOK_ACCESS_TOKEN", page_token)
    logger.info("Done. FACEBOOK_ACCESS_TOKEN updated in .env with a long-lived Page token.")


if __name__ == "__main__":
    main()
