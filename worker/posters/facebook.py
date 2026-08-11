"""Posts to a Facebook Page's feed via the Graph API."""

import os

import requests

GRAPH_API_VERSION = "v19.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def post_to_page(message):
    page_id = os.environ["FACEBOOK_PAGE_ID"]
    access_token = os.environ["FACEBOOK_ACCESS_TOKEN"]

    response = requests.post(
        f"{GRAPH_API_BASE}/{page_id}/feed",
        data={"message": message, "access_token": access_token},
    )

    body = response.json()
    if "error" in body:
        raise RuntimeError(f"Facebook Graph API error: {body['error']}")
    response.raise_for_status()

    return body["id"]


def post_photo(image_path, caption):
    page_id = os.environ["FACEBOOK_PAGE_ID"]
    access_token = os.environ["FACEBOOK_ACCESS_TOKEN"]

    with open(image_path, "rb") as f:
        response = requests.post(
            f"{GRAPH_API_BASE}/{page_id}/photos",
            data={"caption": caption, "access_token": access_token},
            files={"source": f},
        )

    body = response.json()
    if "error" in body:
        raise RuntimeError(f"Facebook Graph API error: {body['error']}")
    response.raise_for_status()

    return body.get("post_id", body.get("id"))


def update_post(post_id, message):
    access_token = os.environ["FACEBOOK_ACCESS_TOKEN"]

    response = requests.post(
        f"{GRAPH_API_BASE}/{post_id}",
        data={"message": message, "access_token": access_token},
    )

    body = response.json()
    if "error" in body:
        raise RuntimeError(f"Facebook Graph API error: {body['error']}")
    response.raise_for_status()

    return body.get("success", False)
