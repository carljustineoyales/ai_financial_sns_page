"""Scrapes a PSE Edge financial report PDF, analyzes it with an LLM, and posts
a caption + analysis to the configured Facebook Page.
"""

import json
import logging
import os
import re
import sys
from datetime import date

from dotenv import load_dotenv
from opentelemetry import trace

import llm
from analysis.analyzer import analyze, extract_text, generate_caption
from logging_config import setup_logging
from posters.preview_and_post import preview_and_post_text
from scraper.pse_edge import (
    download_pdf,
    get_latest_financial_reports,
    get_main_document_text,
    get_pdf_attachment,
)
from tracing_config import setup_llm_tracing

OUTPUT_DIR = "output"
CATEGORY = "financial_reports"

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


def _fail(stage, exc):
    logger.error("%s failed: %s", stage, exc)
    sys.exit(1)


HASHTAG_LINE_RE = re.compile(r"\n+((?:#\S+\s*)+)$")


def _split_trailing_hashtags(text):
    match = HASHTAG_LINE_RE.search(text.rstrip())
    if not match:
        return text.rstrip(), ""
    return text[: match.start()].rstrip(), match.group(1).strip()


def main():
    setup_llm_tracing("main")
    setup_logging()
    load_dotenv()

    with tracer.start_as_current_span("main_run"):
        if not any(p.is_available() for p in llm.get_provider_order()):
            logger.error("No LLM provider is configured. Set ANTHROPIC_API_KEY and/or GEMINI_API_KEY in .env.")
            sys.exit(1)

        logger.info("Fetching latest financial report disclosures from PSE Edge...")
        try:
            disclosures, session = get_latest_financial_reports(limit=10)
        except Exception as e:
            _fail("fetching disclosures", e)

        if not disclosures:
            logger.info("No disclosures found.")
            sys.exit(1)

        target = disclosures[0]
        logger.info("Found: %s - %s (%s)", target["company"], target["template_name"], target["announce_datetime"])

        item_dir = os.path.join(
            OUTPUT_DIR, CATEGORY, date.today().isoformat(), target["report_number"]
        )
        os.makedirs(item_dir, exist_ok=True)

        pdf_path = os.path.join(item_dir, "document.pdf")
        try:
            attachment = get_pdf_attachment(target["edge_no"], session=session)
            if attachment:
                file_id, filename = attachment
                logger.info("Attachment: %s", filename)
                if os.path.exists(pdf_path):
                    logger.info("PDF already exists at %s, skipping download.", pdf_path)
                else:
                    download_pdf(file_id, pdf_path, target["edge_no"], session=session)
                    logger.info("Downloaded PDF to %s", pdf_path)
            else:
                logger.info("No attachment for this disclosure.")
        except Exception as e:
            _fail("downloading PDF attachment", e)

        text_path = os.path.join(item_dir, "source_text.txt")
        if os.path.exists(text_path):
            logger.info("Source text already exists at %s, reusing it.", text_path)
            with open(text_path) as f:
                text = f.read()
        else:
            logger.info("Fetching Main Document text...")
            try:
                text, html = get_main_document_text(target["edge_no"], session=session)
                if not text and os.path.exists(pdf_path):
                    logger.info("Main Document had no text, falling back to PDF extraction...")
                    text = extract_text(pdf_path)
                    html = ""
            except Exception as e:
                _fail("fetching source text", e)
            if not text:
                logger.warning("No text available from Main Document or PDF.")
                sys.exit(1)
            with open(text_path, "w") as f:
                f.write(text)
            logger.info("Saved source text (%d characters) to %s", len(text), text_path)
            if html:
                html_path = os.path.join(item_dir, "main_document.html")
                with open(html_path, "w") as f:
                    f.write(html)
                logger.info("Saved main document HTML to %s", html_path)

        output_path = os.path.join(item_dir, "analysis.md")
        if os.path.exists(output_path):
            logger.info("Analysis already exists at %s, skipping analysis.", output_path)
            with open(output_path) as f:
                summary = f.read().split("---\n\n", 1)[1]
        else:
            logger.info("Analyzing...")
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
            logger.info("Saved analysis to %s", output_path)

        logger.info("\n%s\n%s\n%s", "=" * 60, summary, "=" * 60)

        posted_marker = os.path.join(item_dir, "posted.json")
        if os.path.exists(posted_marker):
            with open(posted_marker) as f:
                info = json.load(f)
            logger.info("Already posted (post id: %s), skipping.", info["post_id"])
            return

        logger.info("Generating Facebook caption...")
        try:
            caption = generate_caption(summary, target["company"], target["template_name"])
        except Exception as e:
            _fail("generating Facebook caption", e)
        caption_body, hashtags = _split_trailing_hashtags(caption)
        post_body = f"{caption_body}\n\n{summary}"
        if hashtags:
            post_body += f"\n\n{hashtags}"

        try:
            preview_and_post_text(post_body, posted_marker)
        except Exception as e:
            _fail("posting to Facebook", e)


if __name__ == "__main__":
    main()
