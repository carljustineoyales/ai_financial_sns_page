"""render_dividend_stamp_card: a grid of per-date dividend cards, each
listing that date's tickers as a status-colored logo tile. Rendered from
rendering/templates/dividend_stamp_card.html via html_render.render_card."""

import math

from .html_render import render_card
from .primitives import _estimate_footer_line_count, _logo_src
from .theme import FOOTER_LINE_HEIGHT, HEIGHT, PADDING, TITLE_BLOCK_HEIGHT, WATERMARK_TEXT, WIDTH

# STATUS_COLORS keys (theme.py) -> the entry-tile--* modifier class in
# rendering/templates/dividend_stamp_card.html.
STATUS_CHIP_CLASS = {
    "PAID": "paid",
    "EX-DATE PASSED": "passed",
    "UPCOMING": "upcoming",
}

COL_GAP = 16
CARD_GAP = 16
CARD_PAD_X = 20
HEADER_HEIGHT = 30
ENTRY_GAP = 20
LABEL_BLOCK_HEIGHT = 34  # gap + ticker line below each entry's logo tile
LEGEND_HEIGHT = 46
BASE_TILE_SIZE = 64
MIN_SCALE = 0.4
MAX_SCALE = 1.6
WATERMARK_RESERVE_PX = 110


def _grid_cols(n):
    if n <= 1:
        return 1
    if n <= 9:
        return 2
    return 3


def _entries_per_row(content_width, tile_size):
    step = tile_size + ENTRY_GAP
    return max(1, int((content_width + ENTRY_GAP) // step))


def _card_height(entry_count, tile_size, per_row):
    rows = math.ceil(entry_count / per_row) if entry_count else 0
    body_height = rows * (tile_size + LABEL_BLOCK_HEIGHT) + max(0, rows - 1) * ENTRY_GAP
    return HEADER_HEIGHT + body_height


def render_dividend_stamp_card(title, subtitle, groups, footer_lines, output_path):
    """groups: [(date_label, [(symbol, status), ...]), ...], already sorted
    by date. Column count scales with len(groups) (see _grid_cols); tile
    size scales once (not iteratively) toward filling the available
    height, shrinking for a busy month or growing for a sparse one --
    mirrors the old Pillow renderer's fill-to-space approach. Entries per
    row is decided once from the unscaled base tile size (per_row_base)
    and the scale range is capped so a full base-sized row never grows
    wider than the column's content area at the chosen scale -- otherwise
    growing the tile size could push actual browser wrapping below
    per_row_base, invalidating the row-count estimate this depends on.
    footer_lines: list of strings, joined into one wrapped paragraph (the
    status legend lives in the template itself, not in footer_lines).
    """
    cols = _grid_cols(len(groups))
    available_width = WIDTH - 2 * PADDING - (cols - 1) * COL_GAP
    col_width = available_width // cols
    content_width = col_width - 2 * CARD_PAD_X

    footer_text = " ".join(footer_lines)
    footer_line_count = _estimate_footer_line_count(footer_text, WIDTH - 2 * PADDING - WATERMARK_RESERVE_PX)
    footer_height = footer_line_count * FOOTER_LINE_HEIGHT + 32
    available_height = HEIGHT - PADDING - TITLE_BLOCK_HEIGHT - LEGEND_HEIGHT - footer_height - PADDING

    per_row_base = _entries_per_row(content_width, BASE_TILE_SIZE)
    natural_row_width = per_row_base * BASE_TILE_SIZE + (per_row_base - 1) * ENTRY_GAP
    width_scale_cap = content_width / natural_row_width if natural_row_width > 0 else MAX_SCALE
    max_scale = min(MAX_SCALE, width_scale_cap)

    tile_size = BASE_TILE_SIZE
    if groups:
        heights = [_card_height(len(entries), BASE_TILE_SIZE, per_row_base) for _, entries in groups]
        row_heights = [max(heights[i:i + cols]) for i in range(0, len(heights), cols)]
        grid_height = sum(row_heights) + max(0, len(row_heights) - 1) * CARD_GAP

        if grid_height > 0 and available_height > 0:
            scale = min(max(available_height / grid_height, MIN_SCALE), max_scale)
            tile_size = max(int(BASE_TILE_SIZE * scale), 20)

    dates = [
        {
            "label": date_label,
            "entries": [
                {
                    "symbol": symbol,
                    "logo_src": _logo_src(symbol),
                    "chip_class": STATUS_CHIP_CLASS.get(status, "neutral"),
                }
                for symbol, status in entries
            ],
        }
        for date_label, entries in groups
    ]

    context = {
        "title": title,
        "subtitle": subtitle,
        "cols": cols,
        "tile_size_px": tile_size,
        "dates": dates,
        "footer_text": footer_text,
        "watermark": WATERMARK_TEXT,
    }

    return render_card("dividend_stamp_card.html", context, output_path)
