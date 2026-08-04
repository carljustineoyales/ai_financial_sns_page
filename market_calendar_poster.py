"""Posts a PSE market calendar graphic (dividend ex-dates only) to the
configured Facebook Page, scoped to the PSEi + REIT watchlist, covering
next month.
"""

import calendar
import json
import os
from datetime import date, datetime, timezone

from dotenv import load_dotenv

import renderer
from assets_logos import ensure_logos
from dividend_tracker import _parse_pse_date, _symbol_lookup, get_period_range, get_watchlist_symbols
from posters.facebook import post_photo
from scraper.pse_edge import get_dividends_and_rights

OUTPUT_DIR = os.path.join("output", "market_calendar_cards")

DISCLAIMER = (
    "We are not financial advisors. This is for educational purposes only. "
    "Do your own research before investing."
)
HASHTAGS = "#PSE #InvestPH #PersonalFinanceTracker #MarketCalendar"


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


def build_card(events, year, month, output_path):
    title = f"{calendar.month_name[month].upper()} {year} DIVIDEND CALENDAR"
    subtitle = "PSEi and REIT watchlist"

    groups = _group_events_with_status(events)
    footer_lines = [
        (renderer.STATUS_COLORS["PAID"], "Paid"),
        (renderer.STATUS_COLORS["EX-DATE PASSED"], "Ex-date passed"),
        (renderer.STATUS_COLORS["UPCOMING"], "Upcoming"),
        (None, DISCLAIMER),
    ]

    ensure_logos(e["symbol"] for e in events)

    return renderer.render_dividend_stamp_card(title, subtitle, groups, footer_lines, output_path)


def build_caption():
    intro = (
        "Here's next month's ex-dividend dates for PSEi and REIT-listed "
        "stocks."
    )
    return f"{intro}\n\n{DISCLAIMER}\n\n{HASHTAGS}"


def main():
    load_dotenv()

    year, month = get_next_month()
    watchlist = get_watchlist_symbols()
    symbol_lookup = _symbol_lookup()

    print(f"Fetching dividend declarations from PSE Edge for {year}-{month:02d}...")
    entries = get_dividends_and_rights()

    events = get_month_dividend_events(entries, watchlist, symbol_lookup, year, month)
    print(f"{len(events)} watchlist dividend events for {year}-{month:02d}.")

    if not events:
        print("Nothing scheduled in this window -- skipping post.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    image_name = f"{year}-{month:02d}"
    image_path = os.path.join(OUTPUT_DIR, f"{image_name}.png")
    build_card(events, year, month, image_path)
    print(f"Saved card to {image_path}")

    caption = build_caption()

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

    record_path = os.path.join(OUTPUT_DIR, f"{image_name}.json")
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


if __name__ == "__main__":
    main()
