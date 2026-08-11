"""render_month_calendar: an agenda of the month's dividend event days
(only days with at least one event get a row). Rendered from
rendering/templates/month_calendar_card.html via html_render.render_card."""

import calendar as calendar_module
from datetime import date

from .html_render import render_card
from .primitives import _logo_src
from .theme import INFO, TRADING_DOWN, TRADING_UP, WATERMARK_TEXT

DOW_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# STATUS_COLORS values -> the chip--* modifier class in
# rendering/templates/_shared.css / month_calendar_card.html.
_COLOR_TO_CHIP_CLASS = {
    TRADING_UP: "paid",
    TRADING_DOWN: "passed",
    INFO: "upcoming",
}


def render_month_calendar(year, month, events_by_day, title, subtitle, footer_lines, output_path, max_events_per_day=6):
    """events_by_day: {day_of_month (int): [(symbol, chip_text, color), ...]},
    color one of theme.STATUS_COLORS' values. max_events_per_day caps how
    many events show per day before a "+N more" note.
    """
    days = []
    for day in sorted(events_by_day):
        day_events = events_by_day[day]
        if not day_events:
            continue

        shown = day_events[:max_events_per_day]
        dow = DOW_LABELS[date(year, month, day).weekday()]
        days.append({
            "dow": dow,
            "dom": day,
            "events": [
                {
                    "symbol": symbol,
                    "chip_text": chip_text,
                    "chip_class": _COLOR_TO_CHIP_CLASS.get(color, "neutral"),
                    "logo_src": _logo_src(symbol),
                }
                for symbol, chip_text, color in shown
            ],
            "remaining": len(day_events) - len(shown),
        })

    context = {
        "title": title,
        "subtitle": subtitle,
        "days": days,
        "footer_text": " ".join(footer_lines),
        "watermark": WATERMARK_TEXT,
    }

    return render_card("month_calendar_card.html", context, output_path)
