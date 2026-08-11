"""render_table_card: title/subtitle header, a table, and footer text.
Rendered from rendering/templates/table_card.html via html_render.render_card."""

from .html_render import render_card
from .primitives import _estimate_footer_line_count, _logo_src
from .theme import (
    BODY_FOOTER_GAP,
    FOOTER_BOTTOM_MARGIN,
    FOOTER_LINE_HEIGHT,
    HEADER_ROW_HEIGHT,
    HEIGHT,
    MAX_ROW_SCALE,
    PADDING,
    ROW_HEIGHT,
    TITLE_BLOCK_HEIGHT,
    WATERMARK_TEXT,
    WIDTH,
)

WATERMARK_RESERVE_PX = 110


def render_table_card(title, subtitle, rows, columns, footer_lines, output_path, ticker_column_key=None):
    """rows: list of dicts keyed by each column's key.
    columns: list of (key, label, width_fraction) tuples; width_fraction
        values should sum to 1.0 across all columns.
    footer_lines: list of strings, joined into one wrapped paragraph (the
        browser wraps it -- see .footer-text in _shared.css).
    ticker_column_key: if set, the column with this key gets a logo icon
        (when available) before its text.
    """
    footer_text = " ".join(footer_lines)
    footer_line_count = _estimate_footer_line_count(footer_text, WIDTH - 2 * PADDING - WATERMARK_RESERVE_PX)
    footer_height = footer_line_count * FOOTER_LINE_HEIGHT + 32
    available_row_height = HEIGHT - PADDING - TITLE_BLOCK_HEIGHT - HEADER_ROW_HEIGHT - footer_height - FOOTER_BOTTOM_MARGIN - BODY_FOOTER_GAP

    max_rows = max(0, available_row_height // ROW_HEIGHT)
    truncated = len(rows) > max_rows
    if truncated:
        shown_rows = rows[: max(0, max_rows - 1)]
        remaining = len(rows) - len(shown_rows)
    else:
        shown_rows = rows
        remaining = 0

    if not truncated and shown_rows:
        scale = min(available_row_height / (len(shown_rows) * ROW_HEIGHT), MAX_ROW_SCALE)
        row_height_px = int(ROW_HEIGHT * scale)
    else:
        row_height_px = ROW_HEIGHT

    columns_ctx = [{"key": key, "label": label, "width_pct": round(width_fraction * 100, 2)} for key, label, width_fraction in columns]

    rows_ctx = []
    for row in shown_rows:
        cells = []
        for key, _, _ in columns:
            is_ticker = key == ticker_column_key
            value = str(row.get(key, ""))
            cells.append({
                "value": value,
                "is_ticker": is_ticker,
                "logo_src": _logo_src(value) if is_ticker else None,
            })
        rows_ctx.append(cells)

    context = {
        "title": title,
        "subtitle": subtitle,
        "columns": columns_ctx,
        "rows": rows_ctx,
        "row_height_px": row_height_px,
        "more_note": f"+{remaining} more" if remaining > 0 else None,
        "footer_text": footer_text,
        "watermark": WATERMARK_TEXT,
    }

    return render_card("table_card.html", context, output_path)
