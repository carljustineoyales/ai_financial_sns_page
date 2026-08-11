"""Shared preview/confirm/post flow for scripts that post to Facebook
(dividend_posters.py, market_movers_poster.py, financial_report_cards.py --
image+caption; main.py -- text only).
"""

import json
import logging
import os
from datetime import datetime, timezone

from posters.facebook import post_photo, post_to_page

logger = logging.getLogger(__name__)


def preview_and_post(image_path, caption, record_path):
    print("\n" + "-" * 60)
    print("POST PREVIEW")
    print("-" * 60)
    print(f"[image: {image_path}]")
    print(caption)
    print("-" * 60)

    post_mode = os.environ.get("POST_MODE", "confirm")
    if post_mode == "confirm":
        answer = input("\nPost this to Facebook? [y/N]: ").strip().lower()
        if answer != "y":
            logger.info("Not posted.")
            return

    logger.info("Posting to Facebook...")
    post_id = post_photo(image_path, caption)
    logger.info("Posted. Post id: %s", post_id)

    with open(record_path, "w") as f:
        json.dump(
            {
                "post_id": post_id,
                "caption": caption,
                "posted_at": datetime.now(timezone.utc).isoformat(),
            },
            f,
            indent=2,
        )


def preview_and_post_text(message, record_path):
    print("\n" + "-" * 60)
    print("POST PREVIEW")
    print("-" * 60)
    print(message)
    print("-" * 60)

    post_mode = os.environ.get("POST_MODE", "confirm")
    if post_mode == "confirm":
        answer = input("\nPost this to Facebook? [y/N]: ").strip().lower()
        if answer != "y":
            logger.info("Not posted.")
            return

    logger.info("Posting to Facebook...")
    post_id = post_to_page(message)
    logger.info("Posted. Post id: %s", post_id)

    with open(record_path, "w") as f:
        json.dump(
            {"post_id": post_id, "posted_at": datetime.now(timezone.utc).isoformat()}, f
        )
