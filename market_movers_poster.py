"""Posts Top 10 Gainers, Top 10 Losers, and Top 10 Most Active graphics to
the configured Facebook Page, market-wide (not scoped to any watchlist --
same full-market, objective-reporting rule as market_movers.py itself and
financial_report_cards.py). Each category is its own post. Captions are
deterministic string templates, not LLM-generated, since this is just
formatted facts with no analysis/judgment involved.

Shares a same-day cached movers snapshot with financial_report_cards.py
via scraper.market_movers.get_or_compute_movers -- whichever of the two
scripts (or scraper/market_movers.py's own cron job) runs first for the
day computes it live and caches it; the rest read that cache, so both
posts reference the exact same top-10 lists without needing a particular
run order.
"""

import os
import sys
from datetime import date

from dotenv import load_dotenv

import rendering as renderer
from assets_logos import ensure_logos
from dividend_graphics import DISCLAIMER
from posters.preview_and_post import preview_and_post
from scraper.market_movers import get_or_compute_movers, refresh_company_directory

OUTPUT_DIR = os.path.join("output", "market_movers_poster")
TOP_N = 10

CATEGORIES = {
    "gainers": {
        "title": "TOP 10 GAINERS",
        "subtitle": "Today's biggest price gains, PSE-wide",
        "value_key": "percent_change",
        "value_label": "% Change",
        "hashtags": "#PSE #InvestPH #PersonalFinanceTracker #TopGainers",
    },
    "losers": {
        "title": "TOP 10 LOSERS",
        "subtitle": "Today's biggest price drops, PSE-wide",
        "value_key": "percent_change",
        "value_label": "% Change",
        "hashtags": "#PSE #InvestPH #PersonalFinanceTracker #TopLosers",
    },
    "most_active": {
        "title": "TOP 10 MOST ACTIVE",
        "subtitle": "Today's highest trading volume, PSE-wide",
        "value_key": "volume",
        "value_label": "Volume",
        "hashtags": "#PSE #InvestPH #PersonalFinanceTracker #MostActive",
    },
}


def _fail(stage, exc):
    print(f"[market_movers_poster] {stage} failed: {exc}", file=sys.stderr)


def _format_value(key, value):
    if key == "percent_change":
        return f"{value:+.2f}%"
    if key == "volume":
        return f"{value:,}"
    return str(value)


def build_movers_card(category, entries, output_path):
    spec = CATEGORIES[category]

    ensure_logos(e["symbol"] for e in entries)

    rows = [
        {
            "symbol": e["symbol"],
            "company": e["company"],
            "price": f"₱{e['price']:.2f}",
            "value": _format_value(spec["value_key"], e[spec["value_key"]]),
        }
        for e in entries
    ]
    columns = [
        ("symbol", "Symbol", 0.15),
        ("company", "Company", 0.45),
        ("price", "Price", 0.15),
        ("value", spec["value_label"], 0.25),
    ]
    footer_lines = [DISCLAIMER]

    return renderer.render_table_card(
        spec["title"], spec["subtitle"], rows, columns, footer_lines, output_path, ticker_column_key="symbol"
    )


def build_movers_caption(category, entries):
    spec = CATEGORIES[category]
    today = date.today().strftime("%B %d, %Y")

    lines = [f"{spec['title']} for {today}:"]
    for e in entries:
        value = _format_value(spec["value_key"], e[spec["value_key"]])
        lines.append(f"{e['symbol']} {value} (₱{e['price']:.2f})")

    body = "\n".join(lines)
    return f"{body}\n\n{DISCLAIMER}\n\n{spec['hashtags']}"


def _process_category(category, entries):
    if not entries:
        print(f"{category}: no data today, skipping.")
        return

    item_dir = os.path.join(OUTPUT_DIR, date.today().isoformat(), category)
    os.makedirs(item_dir, exist_ok=True)

    posted_marker = os.path.join(item_dir, "posted.json")
    if os.path.exists(posted_marker):
        print(f"{category}: already posted, skipping.")
        return

    image_path = os.path.join(item_dir, "card.png")
    build_movers_card(category, entries, image_path)
    print(f"{category}: saved card to {image_path}")

    caption = build_movers_caption(category, entries)
    preview_and_post(image_path, caption, posted_marker)


def main():
    load_dotenv()

    print("Refreshing company directory...")
    companies = refresh_company_directory()

    print("Fetching today's market movers (cached snapshot if one already exists)...")
    try:
        movers = get_or_compute_movers(companies, top_n=TOP_N)
    except Exception as e:
        _fail("computing market movers", e)
        sys.exit(1)

    for category, entries in movers.items():
        _process_category(category, entries)


if __name__ == "__main__":
    main()
