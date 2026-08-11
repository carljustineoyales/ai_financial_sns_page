"""render_ticker_logo_grid: a flat, uncapped near-square logo grid.
Rendered from rendering/templates/ticker_grid_card.html via html_render.render_card."""

import math

from .html_render import render_card
from .primitives import _company_name, _estimate_footer_line_count, _logo_src
from .theme import FOOTER_LINE_HEIGHT, HEIGHT, PADDING, TITLE_BLOCK_HEIGHT, WATERMARK_TEXT, WIDTH

# Reserved vertical room per grid cell for its ticker + 2-line company-name
# label below the logo (gap + ~20px ticker line + gap + 2*~21px name
# lines) -- subtracted from each row's share of the available height so
# the logo itself, not the label, gets sized to fit.
LABEL_BLOCK_HEIGHT = 78
GRID_GAP = 16
MAX_LOGO_SIZE = 220
WATERMARK_RESERVE_PX = 110


def render_ticker_logo_grid(title, subtitle, symbols, footer_lines, output_path):
    """Renders every symbol in a flat, uncapped logo grid (falling back to
    a bordered placeholder square for any ticker with no cached logo) --
    a detail/reference image for a single month's full ticker list,
    unlike the capped per-month grid in render_year_overview(). Column
    count is round(sqrt(count)) (a near-square grid); logo size shrinks
    to fit the fixed 1080x1080 canvas as the list grows.
    """
    n = len(symbols)
    cols = n if n <= 2 else round(math.sqrt(n))
    cols = max(1, cols)
    rows = max(1, math.ceil(n / cols))

    footer_text = " ".join(footer_lines)
    footer_line_count = _estimate_footer_line_count(footer_text, WIDTH - 2 * PADDING - WATERMARK_RESERVE_PX)
    footer_height = footer_line_count * FOOTER_LINE_HEIGHT + 32
    available_width = WIDTH - 2 * PADDING
    available_height = HEIGHT - PADDING - TITLE_BLOCK_HEIGHT - footer_height - PADDING

    col_track_width = (available_width - (cols - 1) * GRID_GAP) / cols
    row_track_height = (available_height - (rows - 1) * GRID_GAP) / rows
    logo_size_px = max(16, int(min(col_track_width, row_track_height - LABEL_BLOCK_HEIGHT, MAX_LOGO_SIZE)))

    entries = [
        {"symbol": symbol, "company_name": _company_name(symbol), "logo_src": _logo_src(symbol)}
        for symbol in symbols
    ]

    context = {
        "title": title,
        "subtitle": subtitle,
        "cols": cols,
        "logo_size_px": logo_size_px,
        "entries": entries,
        "footer_text": footer_text,
        "watermark": WATERMARK_TEXT,
    }

    return render_card("ticker_grid_card.html", context, output_path)
