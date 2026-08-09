"""Shared preview/confirm/post flow for scripts that post an image+caption
card to Facebook (dividend_posters.py, financial_report_cards.py).
"""

import json
import os
from datetime import datetime, timezone

from posters.facebook import post_photo


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
            print("Not posted.")
            return

    print("Posting to Facebook...")
    post_id = post_photo(image_path, caption)
    print(f"Posted. Post id: {post_id}")

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
