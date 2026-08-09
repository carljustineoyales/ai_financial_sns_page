"""Builds Top 10 Gainers / Losers / Most Active graphics, market-wide. No
Facebook/posting dependency -- pure rendering + deterministic captions
(no LLM involved, this is just formatted facts).
"""

from datetime import date

import rendering as renderer
from dividend_graphics import DISCLAIMER

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


def _format_value(key, value):
    if key == "percent_change":
        return f"{value:+.2f}%"
    if key == "volume":
        return f"{value:,}"
    return str(value)


def build_movers_card(category, entries, output_path):
    spec = CATEGORIES[category]

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
