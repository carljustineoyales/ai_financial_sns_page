"""Posts a "Report Card" to the configured Facebook Page whenever any PSE
REIT files a financial report disclosure -- a factual breakdown of whatever
figures that specific filing discloses (revenue, net income, distributable
income, leverage ratio, NAV per share, occupancy rate). Triggered
mechanically by "a REIT filed", never by whether the figures look good, so
this never functions as a curated "top pick" -- every REIT gets the same
treatment every time they file.
"""

import json
import os
import sys
from datetime import date

from dotenv import load_dotenv

import llm
import rendering as renderer
from analysis.analyzer import extract_report_card, extract_text, generate_report_card_caption
from dividend_graphics import DISCLAIMER
from dividend_tracker import PSE_REIT_SYMBOLS
from posters.preview_and_post import preview_and_post
from scraper.market_movers import COMPANY_DIRECTORY_CACHE, refresh_company_directory
from scraper.pse_edge import download_pdf, get_latest_financial_reports, get_main_document_text, get_pdf_attachment

OUTPUT_DIR = os.path.join("output", "reit_report_cards")

FIELD_LABELS = {
    "revenue": "Revenue",
    "net_income": "Net Income",
    "distributable_income": "Distributable Income",
    "distribution_per_share": "Distribution per Share",
    "leverage_ratio": "Leverage Ratio",
    "nav_per_share": "NAV per Share",
    "occupancy_rate": "Occupancy Rate",
}


def _fail(stage, exc):
    print(f"[reit_report_cards] {stage} failed: {exc}", file=sys.stderr)


def _reit_symbol_by_company_name():
    """{company name: symbol} restricted to the 8 PSE REITs, for matching
    against get_latest_financial_reports()'s free-text company field (which
    carries no cmpy_id, unlike the dividend calendar's data source).
    """
    if os.path.exists(COMPANY_DIRECTORY_CACHE):
        with open(COMPANY_DIRECTORY_CACHE) as f:
            companies = json.load(f)
    else:
        companies = refresh_company_directory()

    return {c["company"]: c["symbol"] for c in companies if c["symbol"] in PSE_REIT_SYMBOLS}


def get_recent_reit_disclosures(limit=10):
    """Recent financial report disclosures whose issuer is one of the 8 PSE
    REITs, as (disclosure, symbol) pairs. Purely mechanical filter -- every
    REIT filing qualifies, none are excluded by how the figures look.
    """
    reit_by_name = _reit_symbol_by_company_name()
    disclosures, session = get_latest_financial_reports(limit=limit)

    matches = []
    for disclosure in disclosures:
        symbol = reit_by_name.get(disclosure["company"])
        if symbol:
            matches.append((disclosure, symbol))

    return matches, session


def _figures_text(data):
    lines = []
    for key, label in FIELD_LABELS.items():
        value = data.get(key)
        if value:
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


def build_report_card(symbol, template_name, data, output_path):
    period = data.get("period") or "unspecified period"
    title = f"{symbol} REPORT CARD"
    subtitle = f"{template_name} — {period}"

    rows = [
        {"metric": label, "value": data[key]}
        for key, label in FIELD_LABELS.items()
        if data.get(key)
    ]
    columns = [("metric", "Metric", 0.55), ("value", "Value", 0.45)]
    footer_lines = [DISCLAIMER]

    return renderer.render_table_card(title, subtitle, rows, columns, footer_lines, output_path)


def _process_disclosure(disclosure, symbol, session):
    item_dir = os.path.join(OUTPUT_DIR, date.today().isoformat(), disclosure["report_number"])
    os.makedirs(item_dir, exist_ok=True)

    posted_marker = os.path.join(item_dir, "posted.json")
    if os.path.exists(posted_marker):
        print(f"{symbol}: already posted, skipping.")
        return

    print(f"{symbol}: {disclosure['template_name']} ({disclosure['announce_datetime']})")

    pdf_path = os.path.join(item_dir, "document.pdf")
    try:
        attachment = get_pdf_attachment(disclosure["edge_no"], session=session)
        if attachment:
            file_id, filename = attachment
            if not os.path.exists(pdf_path):
                download_pdf(file_id, pdf_path, disclosure["edge_no"], session=session)
    except Exception as e:
        _fail(f"{symbol}: downloading PDF attachment", e)
        return

    text_path = os.path.join(item_dir, "source_text.txt")
    if os.path.exists(text_path):
        with open(text_path) as f:
            text = f.read()
    else:
        try:
            text, html = get_main_document_text(disclosure["edge_no"], session=session)
            if not text and os.path.exists(pdf_path):
                text = extract_text(pdf_path)
        except Exception as e:
            _fail(f"{symbol}: fetching source text", e)
            return
        if not text:
            print(f"{symbol}: no text available from Main Document or PDF, skipping.")
            return
        with open(text_path, "w") as f:
            f.write(text)

    data_path = os.path.join(item_dir, "extracted.json")
    if os.path.exists(data_path):
        with open(data_path) as f:
            data = json.load(f)
    else:
        print(f"{symbol}: extracting report card figures...")
        try:
            data = extract_report_card(text, disclosure["company"], disclosure["template_name"])
        except Exception as e:
            _fail(f"{symbol}: extracting report card figures", e)
            return
        with open(data_path, "w") as f:
            json.dump(data, f, indent=2)

    if not any(data.get(key) for key in FIELD_LABELS):
        print(f"{symbol}: no report-card figures found in this filing, skipping post.")
        return

    image_path = os.path.join(item_dir, "card.png")
    build_report_card(symbol, disclosure["template_name"], data, image_path)
    print(f"{symbol}: saved card to {image_path}")

    figures_text = _figures_text(data)
    try:
        caption = generate_report_card_caption(symbol, data.get("period"), figures_text)
    except Exception as e:
        _fail(f"{symbol}: generating caption", e)
        return

    preview_and_post(image_path, caption, posted_marker)


def main():
    load_dotenv()

    if not any(p.is_available() for p in llm.get_provider_order()):
        print("No LLM provider is configured. Set ANTHROPIC_API_KEY and/or GEMINI_API_KEY in .env.")
        sys.exit(1)

    print("Fetching recent financial report disclosures from PSE Edge...")
    try:
        matches, session = get_recent_reit_disclosures(limit=10)
    except Exception as e:
        _fail("fetching disclosures", e)
        sys.exit(1)

    if not matches:
        print("No recent REIT financial report disclosures found.")
        return

    for disclosure, symbol in matches:
        _process_disclosure(disclosure, symbol, session)


if __name__ == "__main__":
    main()
