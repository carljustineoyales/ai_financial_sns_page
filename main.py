"""Scrapes a PSE Edge financial report PDF, analyzes it with an LLM, and posts
a caption + analysis to the configured Facebook Page.
"""

import json
import os
import re
import sys
from datetime import date, datetime, timezone

from dotenv import load_dotenv

import llm
from analysis.analyzer import analyze, extract_text, generate_caption
from posters.facebook import post_to_page
from scraper.pse_edge import (
    download_pdf,
    get_latest_financial_reports,
    get_main_document_text,
    get_pdf_attachment,
)

OUTPUT_DIR = "output"
CATEGORY = "financial_reports"


def _fail(stage, exc):
    print(f"[main] {stage} failed: {exc}", file=sys.stderr)
    sys.exit(1)


HASHTAG_LINE_RE = re.compile(r"\n+((?:#\S+\s*)+)$")


def _split_trailing_hashtags(text):
    match = HASHTAG_LINE_RE.search(text.rstrip())
    if not match:
        return text.rstrip(), ""
    return text[: match.start()].rstrip(), match.group(1).strip()


def main():
    load_dotenv()

    if not any(p.is_available() for p in llm.get_provider_order()):
        print("No LLM provider is configured. Set ANTHROPIC_API_KEY and/or GEMINI_API_KEY in .env.")
        sys.exit(1)

    print("Fetching latest financial report disclosures from PSE Edge...")
    try:
        disclosures, session = get_latest_financial_reports(limit=10)
    except Exception as e:
        _fail("fetching disclosures", e)

    if not disclosures:
        print("No disclosures found.")
        sys.exit(1)

    target = disclosures[0]
    print(f"Found: {target['company']} - {target['template_name']} ({target['announce_datetime']})")

    item_dir = os.path.join(
        OUTPUT_DIR, CATEGORY, date.today().isoformat(), target["report_number"]
    )
    os.makedirs(item_dir, exist_ok=True)

    pdf_path = os.path.join(item_dir, "document.pdf")
    try:
        attachment = get_pdf_attachment(target["edge_no"], session=session)
        if attachment:
            file_id, filename = attachment
            print(f"Attachment: {filename}")
            if os.path.exists(pdf_path):
                print(f"PDF already exists at {pdf_path}, skipping download.")
            else:
                download_pdf(file_id, pdf_path, target["edge_no"], session=session)
                print(f"Downloaded PDF to {pdf_path}")
        else:
            print("No attachment for this disclosure.")
    except Exception as e:
        _fail("downloading PDF attachment", e)

    text_path = os.path.join(item_dir, "source_text.txt")
    if os.path.exists(text_path):
        print(f"Source text already exists at {text_path}, reusing it.")
        with open(text_path) as f:
            text = f.read()
    else:
        print("Fetching Main Document text...")
        try:
            text, html = get_main_document_text(target["edge_no"], session=session)
            if not text and os.path.exists(pdf_path):
                print("Main Document had no text, falling back to PDF extraction...")
                text = extract_text(pdf_path)
                html = ""
        except Exception as e:
            _fail("fetching source text", e)
        if not text:
            print("Warning: no text available from Main Document or PDF.")
            sys.exit(1)
        with open(text_path, "w") as f:
            f.write(text)
        print(f"Saved source text ({len(text)} characters) to {text_path}")
        if html:
            html_path = os.path.join(item_dir, "main_document.html")
            with open(html_path, "w") as f:
                f.write(html)
            print(f"Saved main document HTML to {html_path}")

    output_path = os.path.join(item_dir, "analysis.md")
    if os.path.exists(output_path):
        print(f"Analysis already exists at {output_path}, skipping analysis.")
        with open(output_path) as f:
            summary = f.read().split("---\n\n", 1)[1]
    else:
        print("Analyzing...")
        try:
            summary = analyze(text, target["company"], target["template_name"])
        except Exception as e:
            _fail("running LLM analysis", e)

        with open(output_path, "w") as f:
            f.write(f"# {target['company']} - {target['template_name']}\n\n")
            f.write(f"**Announced:** {target['announce_datetime']}\n")
            f.write(f"**Report Number:** {target['report_number']}\n\n")
            f.write("---\n\n")
            f.write(summary)
        print(f"Saved analysis to {output_path}")

    print()
    print("=" * 60)
    print(summary)
    print("=" * 60)

    posted_marker = os.path.join(item_dir, "posted.json")
    if os.path.exists(posted_marker):
        with open(posted_marker) as f:
            info = json.load(f)
        print(f"\nAlready posted (post id: {info['post_id']}), skipping.")
        return

    print("\nGenerating Facebook caption...")
    try:
        caption = generate_caption(summary, target["company"], target["template_name"])
    except Exception as e:
        _fail("generating Facebook caption", e)
    caption_body, hashtags = _split_trailing_hashtags(caption)
    post_body = f"{caption_body}\n\n{summary}"
    if hashtags:
        post_body += f"\n\n{hashtags}"

    print("\n" + "-" * 60)
    print("POST PREVIEW")
    print("-" * 60)
    print(post_body)
    print("-" * 60)

    post_mode = os.environ.get("POST_MODE", "confirm")
    if post_mode == "confirm":
        answer = input("\nPost this to Facebook? [y/N]: ").strip().lower()
        if answer != "y":
            print("Not posted.")
            return

    print("Posting to Facebook...")
    try:
        post_id = post_to_page(post_body)
    except Exception as e:
        _fail("posting to Facebook", e)
    print(f"Posted. Post id: {post_id}")

    with open(posted_marker, "w") as f:
        json.dump(
            {"post_id": post_id, "posted_at": datetime.now(timezone.utc).isoformat()}, f
        )


if __name__ == "__main__":
    main()
