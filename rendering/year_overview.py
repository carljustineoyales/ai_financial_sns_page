"""render_year_overview: a 3x4 grid of month boxes with ticker logos.
Rendered from rendering/templates/year_overview_card.html via html_render.render_card."""

from .html_render import render_card
from .primitives import _logo_src
from .theme import WATERMARK_TEXT

MONTH_LABELS = [
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
]
MAX_LOGOS_PER_MONTH_BOX = 4


def render_year_overview(year, months_data, title, subtitle, footer_lines, output_path):
    """Renders a 3-column x 4-row grid of month boxes (Jan-Dec), each with
    a centered month label and up to MAX_LOGOS_PER_MONTH_BOX ticker logos
    for months_data.get(month, []) (1-indexed), with a "+N" note for any
    remainder, or a muted "no entry" message if the month has none
    scheduled.
    """
    months = []
    for month in range(1, 13):
        symbols = months_data.get(month, [])
        shown = symbols[:MAX_LOGOS_PER_MONTH_BOX]
        remaining = len(symbols) - len(shown)
        months.append({
            "label": MONTH_LABELS[month - 1],
            "entries": [{"symbol": symbol, "logo_src": _logo_src(symbol)} for symbol in shown],
            "remaining": remaining,
        })

    context = {
        "title": title,
        "subtitle": subtitle,
        "months": months,
        "footer_text": " ".join(footer_lines),
        "watermark": WATERMARK_TEXT,
    }

    return render_card("year_overview_card.html", context, output_path)
