"""render_table_card: title/subtitle header, a table, and footer text."""

from PIL import Image, ImageDraw

from .primitives import _draw_title_header, _draw_watermark_inline, _font, _load_logo, _truncate_to_width, _watermark_reserve_width, _wrap_footer_lines
from .theme import (
    BACKGROUND,
    BODY_FOOTER_GAP,
    FOOTER_BOTTOM_MARGIN,
    FOOTER_COLOR,
    FOOTER_LINE_HEIGHT,
    HEADER_BG,
    HEADER_ROW_HEIGHT,
    HEADER_TEXT,
    HEIGHT,
    LOGO_GAP,
    MAX_ROW_SCALE,
    PADDING,
    ROW_ALT_BG,
    ROW_HEIGHT,
    ROW_TEXT,
    SECTION_RULE_COLOR,
    SUBTITLE_COLOR,
    TITLE_BLOCK_HEIGHT,
    WIDTH,
)


def render_table_card(title, subtitle, rows, columns, footer_lines, output_path, ticker_column_key=None):
    """Renders a title/subtitle header, a table, and footer text to a fixed
    WIDTHxHEIGHT PNG (Facebook's recommended feed image size).

    rows: list of dicts keyed by each column's key.
    columns: list of (key, label, width_fraction) tuples; width_fraction
        values should sum to 1.0 across all columns.
    footer_lines: list of strings, one per line, drawn above the bottom of
        the canvas. If more rows are passed than fit the fixed canvas,
        the extra rows are dropped and a "+N more" note is added above the
        footer instead of overflowing.
    ticker_column_key: if set, the column with this key gets a logo icon
        (when available) drawn before its text.
    """
    title_font = _font("DejaVuSans-Bold.ttf", 34)
    subtitle_font = _font("DejaVuSans.ttf", 20)
    footer_font = _font("DejaVuSans.ttf", 15)
    note_font = _font("DejaVuSans.ttf", 15)

    # Created early (rather than where every other renderer creates it,
    # right before drawing starts) because computing footer_height needs
    # draw.textlength() to wrap any footer line too long to fit --
    # otherwise a long disclaimer would overflow the fixed-canvas footer.
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    footer_lines = _wrap_footer_lines(draw, footer_lines, footer_font, WIDTH - 2 * PADDING - _watermark_reserve_width(draw))
    footer_height = len(footer_lines) * FOOTER_LINE_HEIGHT + 32
    available_row_height = HEIGHT - PADDING - TITLE_BLOCK_HEIGHT - HEADER_ROW_HEIGHT - footer_height - FOOTER_BOTTOM_MARGIN - BODY_FOOTER_GAP

    max_rows = max(0, available_row_height // ROW_HEIGHT)
    truncated = len(rows) > max_rows
    if truncated:
        shown_rows = rows[: max(0, max_rows - 1)]
        remaining = len(rows) - len(shown_rows)
    else:
        shown_rows = rows
        remaining = 0

    # When there's room to spare (few rows on the fixed canvas), scale row
    # *height* up to fill the available space instead of leaving a large
    # empty gap above the footer -- capped so a 1-row card doesn't blow up
    # to an absurdly tall row. Font size deliberately stays fixed: growing
    # it would shrink how much text fits inside the already-narrow fixed
    # column widths (verified -- scaling font too caused heavy truncation
    # like "Tic..." / "Thirty Cen...").
    if not truncated and shown_rows:
        scale = min(available_row_height / (len(shown_rows) * ROW_HEIGHT), MAX_ROW_SCALE)
    else:
        scale = 1.0

    row_height = int(ROW_HEIGHT * scale)
    header_row_height = HEADER_ROW_HEIGHT
    header_font = _font("DejaVuSans-Bold.ttf", 16)
    row_font = _font("DejaVuSans.ttf", 18)
    text_line_height = 22
    header_text_y_offset = (header_row_height - text_line_height) // 2
    row_text_y_offset = (row_height - text_line_height) // 2

    y = _draw_title_header(draw, title, subtitle, title_font, subtitle_font)

    table_width = WIDTH - 2 * PADDING
    col_x = [PADDING]
    for _, _, width_fraction in columns:
        col_x.append(col_x[-1] + int(table_width * width_fraction))

    col_max_width = [col_x[i + 1] - col_x[i] - 20 for i in range(len(columns))]

    draw.rounded_rectangle([PADDING, y, WIDTH - PADDING, y + header_row_height], radius=8, fill=HEADER_BG)
    for i, (key, label, _) in enumerate(columns):
        text = _truncate_to_width(draw, label, header_font, col_max_width[i])
        draw.text((col_x[i] + 12, y + header_text_y_offset), text, font=header_font, fill=HEADER_TEXT)
    y += header_row_height

    for i, row in enumerate(shown_rows):
        if i % 2 == 1:
            draw.rectangle([PADDING, y, WIDTH - PADDING, y + row_height], fill=ROW_ALT_BG)
        for j, (key, _, _) in enumerate(columns):
            cell_x = col_x[j] + 12
            cell_max_width = col_max_width[j]
            value = str(row.get(key, ""))

            logo_offset = 0
            if key == ticker_column_key:
                logo_size = min(row_height - 8, 24)
                logo = _load_logo(value, logo_size)
                if logo:
                    image.paste(logo, (cell_x, y + (row_height - logo_size) // 2), logo)
                    logo_offset = logo_size + LOGO_GAP

            text = _truncate_to_width(draw, value, row_font, cell_max_width - logo_offset)
            draw.text((cell_x + logo_offset, y + row_text_y_offset), text, font=row_font, fill=ROW_TEXT)
        y += row_height

    if remaining > 0:
        draw.text((PADDING, y + 14), f"+{remaining} more", font=note_font, fill=SUBTITLE_COLOR)

    footer_y = HEIGHT - FOOTER_BOTTOM_MARGIN - footer_height
    draw.line([(PADDING, footer_y), (WIDTH - PADDING, footer_y)], fill=SECTION_RULE_COLOR, width=2)
    fy = footer_y + 16
    for line in footer_lines:
        draw.text((PADDING, fy), line, font=footer_font, fill=FOOTER_COLOR)
        fy += FOOTER_LINE_HEIGHT

    _draw_watermark_inline(draw, fy - FOOTER_LINE_HEIGHT)
    image.save(output_path, "PNG")
    return output_path
