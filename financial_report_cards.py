"""Posts a "Report Card" to the configured Facebook Page for every company
in today's top 10 gainers/losers/most-active -- a factual breakdown of
whatever figures that company's most recent financial report discloses
(regardless of how old that filing is), plus a few simple ratios computed
from those figures (never estimated by the LLM). Triggered mechanically by
"they're a top mover today", never by whether the figures look good, so
this never functions as a curated "top pick" -- being a top mover is a
factual, rules-based criterion (rank by price/volume), the same category
as the old "they filed a report" trigger, not "looks fundamentally good."

Runs after market close, since gainers/losers/most-active are end-of-day
rankings -- see scripts/crontab.

Deliberately overlaps in coverage with main.py: main.py posts a freeform
narrative about whichever company files next, any disclosure type; this
posts a structured figures table for whichever companies moved the most
today. Both can post about the same filing on the same day, in different
formats -- that's intentional, not a duplicate-post bug.
"""

import json
import os
import sys
from datetime import date

from dotenv import load_dotenv

import llm
import rendering as renderer
from analysis.analyzer import extract_report_card, extract_text, generate_report_card_caption
from analysis.ratios import compute_derived_metrics, compute_valuation_metrics
from dividend_graphics import DISCLAIMER
from dividend_tracker import PSE_REIT_SYMBOLS
from posters.preview_and_post import preview_and_post
from scraper.market_movers import get_or_compute_movers, refresh_company_directory
from scraper.pse_edge import (
    download_pdf,
    get_company_financial_reports,
    get_main_document_text,
    get_pdf_attachment,
    get_stock_data,
    new_session,
)

OUTPUT_DIR = os.path.join("output", "financial_report_cards")
TOP_N = 10

# Row priority: most informative fields first, so if the fixed-canvas
# table card has to truncate, the important rows survive. Each entry is
# (key, label, source) where source is "stated" (raw field, .stated text),
# "stated_only" (REIT-only field, plain string), or "derived" (a computed
# ratio, from ratios.py).
METRIC_ORDER = [
    ("revenue", "Revenue", "stated"),
    ("net_income", "Net Income", "stated"),
    ("operating_income", "Operating Income", "stated"),
    ("net_margin", "Net Margin (derived)", "derived_pct"),
    ("operating_margin", "Operating Margin (derived)", "derived_pct"),
    ("ebitda_margin", "EBITDA Margin (derived)", "derived_pct"),
    ("distributable_income", "Distributable Income", "stated_only"),
    ("leverage_ratio", "Leverage Ratio", "stated_only"),
    ("nav_per_share", "NAV per Share", "stated_only"),
    ("occupancy_rate", "Occupancy Rate", "stated_only"),
    ("current_ratio", "Current Ratio (derived)", "derived_num"),
    ("debt_to_equity", "Debt to Equity (derived)", "derived_num"),
    ("asset_to_equity", "Asset to Equity (derived)", "derived_num"),
    ("interest_coverage", "Interest Coverage (derived)", "derived_num"),
    ("roe", "ROE, period-end (derived)", "derived_pct"),
    ("roa", "ROA, period-end (derived)", "derived_pct"),
    ("asset_turnover", "Asset Turnover (derived)", "derived_num"),
    ("cfo", "Cash Flow from Operations", "stated"),
    ("cfi", "Cash Flow from Investing", "stated"),
    ("cff", "Cash Flow from Financing", "stated"),
    ("dividend_per_share", "Dividend per Share", "stated"),
    ("pe_ratio", "P/E Ratio (derived)", "derived_num"),
    ("pb_ratio", "P/B Ratio (derived)", "derived_num"),
]


def _fail(stage, exc):
    print(f"[financial_report_cards] {stage} failed: {exc}", file=sys.stderr)


def get_top_mover_disclosures():
    """Today's top gainers/losers/most-active (deduped, market-wide, via
    scraper.market_movers.get_or_compute_movers -- shares a same-day
    cached snapshot with market_movers_poster.py so both posts reference
    the exact same top-10 lists), each paired with their most recent
    financial report disclosure regardless of how old it is
    (scraper.pse_edge.get_company_financial_reports) -- as (disclosure,
    company_info) pairs. Purely mechanical filter -- every top mover
    qualifies, none excluded by how the figures look; a mover with no
    financial report on file at all is skipped.
    """
    companies = refresh_company_directory()
    cmpy_id_by_symbol = {c["symbol"]: c.get("cmpy_id") for c in companies}

    movers = get_or_compute_movers(companies, top_n=TOP_N)
    symbols = sorted({entry["symbol"] for entries in movers.values() for entry in entries})

    session = new_session()
    matches = []
    for symbol in symbols:
        cmpy_id = cmpy_id_by_symbol.get(symbol)
        if not cmpy_id:
            print(f"{symbol}: no cmpy_id in company directory, skipping.")
            continue

        reports = get_company_financial_reports(cmpy_id, session=session)
        if not reports:
            print(f"{symbol}: no financial report on file, skipping.")
            continue

        info = {
            "symbol": symbol,
            "cmpy_id": cmpy_id,
            "is_reit": symbol in PSE_REIT_SYMBOLS,
        }
        matches.append((reports[0], info))

    return matches, session


def _format_pct(value):
    return f"{value * 100:.1f}%"


def _format_num(value):
    return f"{value:.2f}"


def _report_rows(data, computed, valuation):
    rows = []
    for key, label, source in METRIC_ORDER:
        if source in ("stated", "stated_only"):
            field = data.get(key)
            value = field.get("stated") if field else None
        elif source == "derived_pct":
            raw = computed.get(key, valuation.get(key) if valuation else None)
            value = _format_pct(raw) if raw is not None else None
        elif source == "derived_num":
            raw = computed.get(key, valuation.get(key) if valuation else None)
            value = _format_num(raw) if raw is not None else None
        else:
            value = None

        if value:
            rows.append({"metric": label, "value": value})

    return rows


def build_report_card(symbol, template_name, data, computed, valuation, output_path):
    period = data.get("period") or "unspecified period"
    title = f"{symbol} REPORT CARD"
    subtitle = f"{template_name} — {period}"

    rows = _report_rows(data, computed, valuation)
    columns = [("metric", "Metric", 0.55), ("value", "Value", 0.45)]
    footer_lines = [DISCLAIMER]

    return renderer.render_table_card(title, subtitle, rows, columns, footer_lines, output_path)


def _figures_text(data, computed, valuation):
    rows = _report_rows(data, computed, valuation)
    return "\n".join(f"{row['metric']}: {row['value']}" for row in rows)


def _process_disclosure(disclosure, info, session):
    symbol = info["symbol"]
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
        if not info["is_reit"]:
            for key in ("distributable_income", "leverage_ratio", "nav_per_share", "occupancy_rate"):
                data[key] = None
        with open(data_path, "w") as f:
            json.dump(data, f, indent=2)

    computed = compute_derived_metrics(data)

    valuation = {}
    if info["cmpy_id"]:
        try:
            stock_data = get_stock_data(info["cmpy_id"])
            if stock_data and stock_data.get("price"):
                valuation = compute_valuation_metrics(data, stock_data["price"])
        except Exception as e:
            _fail(f"{symbol}: fetching current price for valuation ratios", e)

    rows = _report_rows(data, computed, valuation)
    if not rows:
        print(f"{symbol}: no report-card figures found in this filing, skipping post.")
        return

    image_path = os.path.join(item_dir, "card.png")
    build_report_card(symbol, disclosure["template_name"], data, computed, valuation, image_path)
    print(f"{symbol}: saved card to {image_path}")

    figures_text = _figures_text(data, computed, valuation)
    try:
        caption = generate_report_card_caption(
            symbol, data.get("period"), figures_text, disclosure["announce_datetime"]
        )
    except Exception as e:
        _fail(f"{symbol}: generating caption", e)
        return

    preview_and_post(image_path, caption, posted_marker)


def main():
    load_dotenv()

    if not any(p.is_available() for p in llm.get_provider_order()):
        print("No LLM provider is configured. Set ANTHROPIC_API_KEY and/or GEMINI_API_KEY in .env.")
        sys.exit(1)

    print("Fetching today's top movers and their most recent financial reports...")
    try:
        matches, session = get_top_mover_disclosures()
    except Exception as e:
        _fail("fetching top movers / disclosures", e)
        sys.exit(1)

    if not matches:
        print("No top movers with a financial report on file today.")
        return

    for disclosure, info in matches:
        _process_disclosure(disclosure, info, session)


if __name__ == "__main__":
    main()
