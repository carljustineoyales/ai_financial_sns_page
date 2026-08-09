"""Builds PSE dividend graphics, scoped to the PSEi + REIT watchlist: a
next-month dividend ex-date calendar card ("month") and a full-year
(Jan-Dec) dividend payout overview card plus per-month detail cards
("year"). No Facebook/posting dependency -- pure data-fetch + rendering.
"""

import calendar
import os
from datetime import date

import rendering as renderer
from dividend_tracker import _parse_pse_date, get_period_range

DISCLAIMER = (
    "We are not financial advisors. This is for educational purposes only. "
    "Do your own research before investing."
)


# ---- Month: next-month dividend ex-date calendar card ----

MONTH_OUTPUT_DIR = os.path.join("output", "market_calendar_cards")
MONTH_HASHTAGS = "#PSE #InvestPH #MarketCalendar"


def get_next_month():
    start, _ = get_period_range("month")
    return start.year, start.month


def get_month_dividend_events(entries, watchlist, symbol_lookup, year, month):
    """Watchlist entries (from get_dividends_and_rights()) whose
    ex_dividend_date falls in year/month, as {"symbol", "ex_date",
    "payment_date"} dicts (dates as date objects), sorted by ex_date.
    """
    events = []
    for entry in entries:
        symbol = symbol_lookup.get(entry["cmpy_id"])
        if not symbol or symbol not in watchlist:
            continue

        ex_date = _parse_pse_date(entry["ex_dividend_date"])
        if not ex_date or ex_date.year != year or ex_date.month != month:
            continue

        events.append({
            "symbol": symbol,
            "ex_date": ex_date,
            "payment_date": _parse_pse_date(entry["payment_date"]),
        })

    events.sort(key=lambda e: e["ex_date"])
    return events


def _group_events_with_status(events, today=None):
    """[(date_label, [(symbol, status), ...]), ...], sorted by date, one
    group per distinct ex-date. status is "PAID" if the payment date is on
    or before today, "EX-DATE PASSED" if only the ex-date has passed, else
    "UPCOMING".
    """
    today = today or date.today()

    groups = {}
    for e in events:
        day_entries = groups.setdefault(e["ex_date"], [])
        # A ticker can have several dividend declarations on the same date
        # (e.g. multiple preferred-share series) -- consolidate to one
        # entry per symbol per date.
        if not any(existing["symbol"] == e["symbol"] for existing in day_entries):
            day_entries.append(e)

    result = []
    for ex_date in sorted(groups):
        label = f"{calendar.month_name[ex_date.month][:3].upper()} {ex_date.day}"
        entries = []
        for e in groups[ex_date]:
            if e["payment_date"] and e["payment_date"] <= today:
                status = "PAID"
            elif ex_date <= today:
                status = "EX-DATE PASSED"
            else:
                status = "UPCOMING"
            entries.append((e["symbol"], status))
        result.append((label, entries))

    return result


def build_month_card(events, year, month, output_path):
    title = f"{calendar.month_name[month].upper()} {year} DIVIDEND CALENDAR"
    subtitle = "PSEi and REIT watchlist"

    groups = _group_events_with_status(events)
    footer_lines = [
        (renderer.STATUS_COLORS["PAID"], "Paid"),
        (renderer.STATUS_COLORS["EX-DATE PASSED"], "Ex-date passed"),
        (renderer.STATUS_COLORS["UPCOMING"], "Upcoming"),
        (None, DISCLAIMER),
    ]

    return renderer.render_dividend_stamp_card(title, subtitle, groups, footer_lines, output_path)


def build_month_caption():
    intro = (
        "Here's next month's ex-dividend dates for PSEi and REIT-listed "
        "stocks."
    )
    return f"{intro}\n\n{DISCLAIMER}\n\n{MONTH_HASHTAGS}"


# ---- Year: full Jan-Dec dividend payout overview + month detail cards ----

YEAR_OUTPUT_DIR = os.path.join("output", "year_overview")
YEAR_HASHTAGS = "#PSE #InvestPH #DividendCalendar"


def year_output_dir(year):
    return os.path.join(YEAR_OUTPUT_DIR, str(year))


def get_current_year_by_month(entries, watchlist, symbol_lookup, year=None):
    """{month (1-12): sorted [symbol, ...]} of watchlist tickers with a
    payment_date falling in year (defaults to the current year).
    """
    year = year or date.today().year

    by_month = {m: set() for m in range(1, 13)}
    for entry in entries:
        symbol = symbol_lookup.get(entry["cmpy_id"])
        if not symbol or symbol not in watchlist:
            continue

        parsed = _parse_pse_date(entry["payment_date"])
        if not parsed or parsed.year != year:
            continue

        by_month[parsed.month].add(symbol)

    return {month: sorted(symbols) for month, symbols in by_month.items()}


def build_year_card(months_data, year, output_path):
    title = f"{year} DIVIDEND PAYOUT CALENDAR"
    subtitle = "PSEi and REIT watchlist"
    footer_lines = [DISCLAIMER]

    return renderer.render_year_overview(year, months_data, title, subtitle, footer_lines, output_path)


def build_month_detail_cards(months_data, year, output_dir):
    """Renders a supplementary "zoomed in" full-ticker-list detail image
    for every month that has at least one dividend payer (months with
    none get no detail image -- there's nothing to zoom into). Returns
    the list of paths generated.
    """
    footer_lines = [DISCLAIMER]
    paths = []

    for month, symbols in months_data.items():
        if not symbols:
            continue

        month_name = calendar.month_name[month]
        title = f"{month_name.upper()} {year} DIVIDEND PAYERS"
        subtitle = "PSEi and REIT watchlist"
        output_path = os.path.join(output_dir, f"{month:02d}-{month_name.lower()}.png")

        renderer.render_ticker_logo_grid(title, subtitle, symbols, footer_lines, output_path)
        paths.append(output_path)

    return paths


def build_year_caption(year):
    intro = f"Here's the {year} dividend payout calendar for PSEi and REIT-listed stocks, month by month."
    return f"{intro}\n\n{DISCLAIMER}\n\n{YEAR_HASHTAGS}"
