"""Renders simple table-style graphic cards to PNG using Pillow.

Deliberately simple -- these are Facebook utility graphics (dividend
schedules, etc.), not polished design artifacts. Uses DejaVu Sans, which
ships system-wide on this machine, so no font file needs to be bundled.
"""

import calendar as calendar_module
import math
import os

from PIL import Image, ImageDraw, ImageFont

WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

WIDTH = 1080
HEIGHT = 1080
PADDING = 40
ROW_HEIGHT = 50
HEADER_ROW_HEIGHT = 36
MAX_ROW_SCALE = 2.0
TITLE_BLOCK_HEIGHT = 110
FOOTER_LINE_HEIGHT = 28

BACKGROUND = "#ffffff"
TITLE_COLOR = "#0b2545"
SUBTITLE_COLOR = "#4a5568"
HEADER_BG = "#0b2545"
HEADER_TEXT = "#ffffff"
ROW_TEXT = "#1a202c"
ROW_ALT_BG = "#f2f5f9"
RULE_COLOR = "#cbd5e0"
FOOTER_COLOR = "#718096"

FONT_DIR = "/usr/share/fonts/truetype/dejavu"

ASSETS_LOGO_DIR = os.path.join("assets", "logos")


WATERMARK_TEXT = "Curious Neko"
WATERMARK_COLOR = "#a0aec0"
WATERMARK_MARGIN = 16


def _font(name, size):
    return ImageFont.truetype(f"{FONT_DIR}/{name}", size)


def _draw_watermark(draw, width, height):
    font = _font("DejaVuSans.ttf", 14)
    text_width = draw.textlength(WATERMARK_TEXT, font=font)
    x = width - WATERMARK_MARGIN - text_width
    y = height - WATERMARK_MARGIN - 16
    draw.text((x, y), WATERMARK_TEXT, font=font, fill=WATERMARK_COLOR)


def _draw_title_header(draw, title, subtitle, title_font, subtitle_font):
    """Draws the title/subtitle block plus a rule line marking the
    boundary between it and the body content below, so header, body, and
    footer (which already draws its own rule -- see footer_y in each
    render_* function) read as distinct regions instead of blending into
    one undifferentiated canvas. Returns the y where body content starts.
    """
    y = PADDING
    draw.text((PADDING, y), title, font=title_font, fill=TITLE_COLOR)
    y += 44
    draw.text((PADDING, y), subtitle, font=subtitle_font, fill=SUBTITLE_COLOR)

    header_bottom = PADDING + TITLE_BLOCK_HEIGHT
    draw.line([(PADDING, header_bottom - 18), (WIDTH - PADDING, header_bottom - 18)], fill=RULE_COLOR, width=1)
    return header_bottom


def _truncate_to_width(draw, text, font, max_width):
    if draw.textlength(text, font=font) <= max_width:
        return text

    ellipsis = "..."
    truncated = text
    while truncated and draw.textlength(truncated + ellipsis, font=font) > max_width:
        truncated = truncated[:-1]
    return (truncated + ellipsis) if truncated else ellipsis


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

    footer_height = len(footer_lines) * FOOTER_LINE_HEIGHT + 32
    available_row_height = HEIGHT - PADDING - TITLE_BLOCK_HEIGHT - HEADER_ROW_HEIGHT - footer_height - PADDING

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

    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    y = _draw_title_header(draw, title, subtitle, title_font, subtitle_font)

    table_width = WIDTH - 2 * PADDING
    col_x = [PADDING]
    for _, _, width_fraction in columns:
        col_x.append(col_x[-1] + int(table_width * width_fraction))

    col_max_width = [col_x[i + 1] - col_x[i] - 20 for i in range(len(columns))]

    draw.rectangle([PADDING, y, WIDTH - PADDING, y + header_row_height], fill=HEADER_BG)
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

    footer_y = HEIGHT - PADDING - footer_height
    draw.line([(PADDING, footer_y), (WIDTH - PADDING, footer_y)], fill=RULE_COLOR, width=1)
    fy = footer_y + 16
    for line in footer_lines:
        draw.text((PADDING, fy), line, font=footer_font, fill=FOOTER_COLOR)
        fy += FOOTER_LINE_HEIGHT

    _draw_watermark(draw, WIDTH, HEIGHT)
    image.save(output_path, "PNG")
    return output_path


CHIP_PADDING_X = 6
CHIP_HEIGHT = 16
LOGO_GAP = 4

_logo_cache = {}


def _load_logo(symbol, size):
    cache_key = (symbol, size)
    if cache_key in _logo_cache:
        return _logo_cache[cache_key]

    path = os.path.join(ASSETS_LOGO_DIR, f"{symbol}.png")
    logo = None
    if os.path.exists(path):
        try:
            source = Image.open(path).convert("RGBA")
            source.thumbnail((size, size), Image.LANCZOS)
            logo = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            offset = ((size - source.width) // 2, (size - source.height) // 2)
            logo.paste(source, offset, source)
        except Exception:
            logo = None

    _logo_cache[cache_key] = logo
    return logo


def _lighten(hex_color, amount=0.82):
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r = int(r + (255 - r) * amount)
    g = int(g + (255 - g) * amount)
    b = int(b + (255 - b) * amount)
    return f"#{r:02x}{g:02x}{b:02x}"


def _draw_chip(image, draw, x, y, text, font, color, symbol=None):
    logo_offset = 0
    if symbol:
        logo = _load_logo(symbol, CHIP_HEIGHT)
        if logo:
            image.paste(logo, (int(x), int(y)), logo)
            logo_offset = CHIP_HEIGHT + LOGO_GAP

    chip_x = x + logo_offset
    bg = _lighten(color)
    text_width = draw.textlength(text, font=font)
    chip_width = text_width + 2 * CHIP_PADDING_X
    draw.rounded_rectangle(
        [chip_x, y, chip_x + chip_width, y + CHIP_HEIGHT],
        radius=CHIP_HEIGHT / 2,
        fill=bg,
    )
    draw.text((chip_x + CHIP_PADDING_X, y), text, font=font, fill=color)
    return logo_offset + chip_width


def render_month_calendar(year, month, events_by_day, title, subtitle, footer_lines, output_path, max_events_per_day=3):
    """Renders a Sun-Sat month grid to a fixed WIDTHxHEIGHT PNG (Facebook's
    recommended feed image size), each day cell showing the day number and
    up to max_events_per_day events (ticker as plain text, event-type code
    as a color-coded rounded chip beside it), with a "+N more" line if
    there are more. events_by_day: {day_of_month (int): [(symbol,
    chip_text, color), ...]}. max_events_per_day is a ceiling -- the actual
    number shown may be lower if the fixed canvas leaves less room (a
    6-week month has less height per cell than a 5-week month).
    """
    title_font = _font("DejaVuSans-Bold.ttf", 34)
    subtitle_font = _font("DejaVuSans.ttf", 20)
    weekday_font = _font("DejaVuSans-Bold.ttf", 16)
    day_num_font = _font("DejaVuSans-Bold.ttf", 18)
    event_font = _font("DejaVuSans.ttf", 13)
    footer_font = _font("DejaVuSans.ttf", 15)

    weeks = calendar_module.Calendar(firstweekday=6).monthdayscalendar(year, month)

    grid_width = WIDTH - 2 * PADDING
    col_width = grid_width // 7
    weekday_header_height = 36
    event_line_height = 17

    footer_height = len(footer_lines) * FOOTER_LINE_HEIGHT + 32
    grid_height = HEIGHT - PADDING - TITLE_BLOCK_HEIGHT - weekday_header_height - footer_height - PADDING
    cell_height = grid_height // len(weeks)

    day_number_height = 26
    max_events_that_fit = max(0, (cell_height - day_number_height - 6) // event_line_height)
    max_events_per_day = min(max_events_per_day, max_events_that_fit)

    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    y = _draw_title_header(draw, title, subtitle, title_font, subtitle_font)

    draw.rectangle([PADDING, y, WIDTH - PADDING, y + weekday_header_height], fill=HEADER_BG)
    for i, label in enumerate(WEEKDAY_LABELS):
        cx = PADDING + i * col_width
        draw.text((cx + 10, y + 8), label, font=weekday_font, fill=HEADER_TEXT)
    y += weekday_header_height

    for week in weeks:
        for i, day in enumerate(week):
            cx = PADDING + i * col_width
            draw.rectangle([cx, y, cx + col_width, y + cell_height], outline=RULE_COLOR, width=1)
            if day == 0:
                continue

            draw.text((cx + 8, y + 6), str(day), font=day_num_font, fill=TITLE_COLOR)

            day_events = events_by_day.get(day, [])
            shown = day_events[:max_events_per_day]
            ey = y + 6 + 22
            for symbol, chip_text, chip_color in shown:
                chip_width = _draw_chip(image, draw, cx + 8, ey, chip_text, event_font, chip_color)
                logo = _load_logo(symbol, CHIP_HEIGHT)
                logo_offset = CHIP_HEIGHT + LOGO_GAP if logo else 0
                if logo:
                    image.paste(logo, (int(cx + 8 + chip_width + 6), int(ey)), logo)
                symbol_x = cx + 8 + chip_width + 6 + logo_offset
                symbol_max_width = col_width - 16 - chip_width - 6 - logo_offset
                symbol_text = _truncate_to_width(draw, symbol, event_font, symbol_max_width)
                draw.text((symbol_x, ey), symbol_text, font=event_font, fill=ROW_TEXT)
                ey += event_line_height

            remaining = len(day_events) - max_events_per_day
            if remaining > 0:
                draw.text((cx + 8, ey), f"+{remaining} more", font=event_font, fill=SUBTITLE_COLOR)
        y += cell_height

    footer_y = HEIGHT - PADDING - footer_height
    draw.line([(PADDING, footer_y), (WIDTH - PADDING, footer_y)], fill=RULE_COLOR, width=1)
    fy = footer_y + 16
    for line in footer_lines:
        draw.text((PADDING, fy), line, font=footer_font, fill=FOOTER_COLOR)
        fy += FOOTER_LINE_HEIGHT

    _draw_watermark(draw, WIDTH, HEIGHT)
    image.save(output_path, "PNG")
    return output_path


STATUS_COLORS = {
    "PAID": "#1baf7a",
    "EX-DATE PASSED": "#eda100",
    "UPCOMING": "#2a78d6",
}


def _dividend_grid_cols(n):
    if n <= 1:
        return 1
    if n <= 9:
        return 2
    return 3


TICKER_LABEL_GAP = 4
TICKER_LABEL_HEIGHT = 15


def _dividend_entries_per_line(card_width, entry_size, entry_gap):
    if card_width < entry_size:
        return 1
    return 1 + (card_width - entry_size) // (entry_size + entry_gap)


def _layout_dividend_entries(entries, logo_size, entry_gap, border_margin, per_line):
    """Lays out (symbol, status) entries into centered rows of `per_line`
    entries each (the last row may have fewer). Each entry is a
    fixed-size bordered logo square (border color per STATUS_COLORS) with
    its ticker symbol printed below. `per_line` is decided once by the
    caller from unscaled base sizes (see _dividend_entries_per_line) so
    the same date-count always groups the same way regardless of how
    much this particular month's fill-to-space scaling grows or shrinks
    logo_size -- only the pixel size changes, not the grouping. Returns
    (placements, content_height) where placements is [(symbol, status,
    rel_x, rel_y), ...] relative to the card's content origin (rel_y is
    the top of the bordered box; the ticker label goes below it). Each
    row is centered horizontally within card_width rather than
    left-aligned.
    """
    entry_size = logo_size + 2 * border_margin
    row_step = entry_size + TICKER_LABEL_GAP + TICKER_LABEL_HEIGHT + 8
    card_width = per_line * entry_size + (per_line - 1) * entry_gap

    lines = [entries[i:i + per_line] for i in range(0, len(entries), per_line)]

    placements = []
    ey = 0
    for i, line in enumerate(lines):
        if i > 0:
            ey += row_step

        line_width = len(line) * entry_size + (len(line) - 1) * entry_gap
        ex = max(0, (card_width - line_width) / 2)
        for symbol, status in line:
            placements.append((symbol, status, ex, ey))
            ex += entry_size + entry_gap

    content_height = (ey if lines else 0) + entry_size + TICKER_LABEL_GAP + TICKER_LABEL_HEIGHT
    return placements, content_height


def render_dividend_stamp_card(title, subtitle, groups, footer_lines, output_path):
    """Renders a fixed WIDTHxHEIGHT (1080x1080) multi-column grid of date
    cards, each listing that date's dividend entries as a logo with a
    colored status border (see STATUS_COLORS; falls back to ticker text
    if no logo is cached). groups: [(date_label, [(symbol, status), ...]),
    ...], already sorted by date. footer_lines: [(color_or_None, text),
    ...] -- color draws a small matching bordered swatch before the text
    (pass color=None, e.g. for a plain disclaimer line, to skip the
    swatch). Column count scales with len(groups) (see
    _dividend_grid_cols); if natural content doesn't fit the fixed
    canvas, logo size and spacing shrink once (not iteratively) rather
    than growing the canvas.
    """
    title_font = _font("DejaVuSans-Bold.ttf", 34)
    subtitle_font = _font("DejaVuSans.ttf", 20)
    date_font = _font("DejaVuSans-Bold.ttf", 18)
    symbol_font = _font("DejaVuSans-Bold.ttf", 15)
    ticker_font = _font("DejaVuSans-Bold.ttf", 12)
    footer_font = _font("DejaVuSans.ttf", 15)

    base_logo_size = 56
    base_entry_gap = 24
    base_border_margin = 6
    card_pad_x = 20
    card_pad_bottom = 16
    card_gap = 12
    col_gap = 12
    header_height = 34

    cols = _dividend_grid_cols(len(groups))
    grid_width = WIDTH - 2 * PADDING - (cols - 1) * col_gap
    col_width = grid_width // cols
    col_width_last = col_width + (grid_width - col_width * cols)  # absorb rounding remainder in the last column
    content_width = col_width - 2 * card_pad_x

    footer_height = len(footer_lines) * FOOTER_LINE_HEIGHT + 32
    available_height = HEIGHT - PADDING - TITLE_BLOCK_HEIGHT - footer_height - PADDING

    # Decide how many entries share a line using unscaled base sizes, so
    # the same date-count groups the same way (e.g. always 3-per-line for
    # a given column width) no matter how this particular month's
    # fill-to-space scaling below grows or shrinks the rendered size --
    # only the pixel size changes, not the grouping.
    base_entry_size = base_logo_size + 2 * base_border_margin
    per_line = _dividend_entries_per_line(content_width, base_entry_size, base_entry_gap)
    per_line_natural_width = per_line * base_entry_size + (per_line - 1) * base_entry_gap

    def _layout_all(logo_size, entry_gap, border_margin):
        cards = []
        for date_label, entries in groups:
            placements, content_height = _layout_dividend_entries(
                entries, logo_size, entry_gap, border_margin, per_line,
            )
            card_height = header_height + content_height + card_pad_bottom
            cards.append((date_label, placements, card_height))

        row_heights = []
        for i in range(0, len(cards), cols):
            row_cards = cards[i:i + cols]
            row_heights.append(max(c[2] for c in row_cards) if row_cards else 0)

        grid_height = sum(row_heights) + max(0, len(row_heights) - 1) * card_gap
        return cards, row_heights, grid_height

    logo_size, entry_gap, border_margin = base_logo_size, base_entry_gap, base_border_margin
    cards, row_heights, grid_height = _layout_all(logo_size, entry_gap, border_margin)

    # Scale once (up or down, not iteratively) so the grid fills the
    # available height instead of leaving a big empty gap below it (or,
    # for a busy month, overflowing it). Also capped so a full per_line
    # row never grows wider than the column's content area -- otherwise
    # scaling up for fill-space could break the grouping decided above.
    min_scale, max_scale = 0.4, 1.6
    width_scale_cap = content_width / per_line_natural_width if per_line_natural_width > 0 else max_scale
    max_scale = min(max_scale, width_scale_cap)
    if groups and grid_height > 0 and available_height > 0:
        scale = min(max(available_height / grid_height, min_scale), max_scale)
        logo_size = max(int(base_logo_size * scale), 20)
        entry_gap = max(int(base_entry_gap * scale), 8)
        border_margin = max(int(base_border_margin * scale), 3)
        cards, row_heights, grid_height = _layout_all(logo_size, entry_gap, border_margin)

        # Stretch remaining slack directly into row heights (not just the
        # gaps between them) so even a single-row month fills the
        # available space instead of leaving one big gap below it. Card
        # content stays its natural size and is vertically centered
        # within the taller row (see the draw loop below).
        if grid_height < available_height:
            extra_per_row = (available_height - grid_height) // len(row_heights)
            row_heights = [h + extra_per_row for h in row_heights]

    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    y = _draw_title_header(draw, title, subtitle, title_font, subtitle_font)

    for row_idx, row_height in enumerate(row_heights):
        row_cards = cards[row_idx * cols:row_idx * cols + cols]
        for col_idx, (date_label, placements, card_height) in enumerate(row_cards):
            cx = PADDING + col_idx * (col_width + col_gap)
            this_col_width = col_width_last if col_idx == cols - 1 else col_width

            draw.rounded_rectangle(
                [cx, y, cx + this_col_width, y + row_height],
                radius=14,
                fill=ROW_ALT_BG,
            )
            label_w = draw.textlength(date_label, font=date_font)
            label_bbox = date_font.getbbox(date_label)
            label_h = label_bbox[3] - label_bbox[1]
            draw.text(
                (cx + (this_col_width - label_w) / 2, y + (header_height - label_h) / 2 - label_bbox[1]),
                date_label, font=date_font, fill=TITLE_COLOR,
            )

            # Center this card's natural-height content within the row's
            # (possibly stretched, see the fill-available-space scaling
            # above) actual height, below the fixed-height header.
            v_offset = max(0, (row_height - card_height) / 2)

            origin_x = cx + card_pad_x
            origin_y = y + header_height + v_offset
            entry_size = logo_size + 2 * border_margin
            for symbol, status, rel_x, rel_y in placements:
                color = STATUS_COLORS.get(status, FOOTER_COLOR)
                bx, by = origin_x + rel_x, origin_y + rel_y
                draw.rounded_rectangle(
                    [bx, by, bx + entry_size, by + entry_size],
                    radius=10, outline=color, width=3,
                )

                lx, ly = bx + border_margin, by + border_margin
                logo = _load_logo(symbol, logo_size)
                if logo:
                    image.paste(logo, (int(lx), int(ly)), logo)
                else:
                    text = _truncate_to_width(draw, symbol, symbol_font, logo_size)
                    text_w = draw.textlength(text, font=symbol_font)
                    draw.text(
                        (lx + (logo_size - text_w) / 2, ly + logo_size / 2 - 8),
                        text, font=symbol_font, fill=ROW_TEXT,
                    )

                ticker_text = _truncate_to_width(draw, symbol, ticker_font, entry_size + 10)
                ticker_w = draw.textlength(ticker_text, font=ticker_font)
                draw.text(
                    (bx + (entry_size - ticker_w) / 2, by + entry_size + TICKER_LABEL_GAP),
                    ticker_text, font=ticker_font, fill=ROW_TEXT,
                )

        y += row_height + card_gap

    footer_y = HEIGHT - PADDING - footer_height
    draw.line([(PADDING, footer_y), (WIDTH - PADDING, footer_y)], fill=RULE_COLOR, width=1)
    fy = footer_y + 16
    swatch_size = 16
    for color, text in footer_lines:
        text_x = PADDING
        if color:
            draw.rounded_rectangle(
                [PADDING, fy + 1, PADDING + swatch_size, fy + 1 + swatch_size],
                radius=4, outline=color, width=2,
            )
            text_x = PADDING + swatch_size + 8
        draw.text((text_x, fy), text, font=footer_font, fill=FOOTER_COLOR)
        fy += FOOTER_LINE_HEIGHT

    _draw_watermark(draw, WIDTH, HEIGHT)
    image.save(output_path, "PNG")
    return output_path


MONTH_LABELS = [
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
]
MAX_LOGOS_PER_MONTH_BOX = 4


def render_year_overview(year, months_data, title, subtitle, footer_lines, output_path):
    """Renders a 3-column x 4-row grid of month boxes (Jan-Dec), each with
    a centered month label and up to MAX_LOGOS_PER_MONTH_BOX ticker logos
    (mini-grid, each with a ticker label underneath, falling back to
    plain ticker text for any ticker with no cached logo) for
    months_data.get(month, []) (1-indexed), with a "+N" note for any
    remainder, or a muted "no entry" icon if the month has none scheduled.
    """
    title_font = _font("DejaVuSans-Bold.ttf", 34)
    subtitle_font = _font("DejaVuSans.ttf", 20)
    month_font = _font("DejaVuSans-Bold.ttf", 16)
    fallback_font = _font("DejaVuSans-Bold.ttf", 10)
    ticker_font = _font("DejaVuSans-Bold.ttf", 10)
    note_font = _font("DejaVuSans.ttf", 13)
    footer_font = _font("DejaVuSans.ttf", 15)

    footer_height = len(footer_lines) * FOOTER_LINE_HEIGHT + 32
    grid_height = HEIGHT - PADDING - TITLE_BLOCK_HEIGHT - footer_height - PADDING
    grid_width = WIDTH - 2 * PADDING

    cols, box_rows = 3, 4
    col_width = grid_width // cols
    row_height = grid_height // box_rows

    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    y = _draw_title_header(draw, title, subtitle, title_font, subtitle_font)

    box_pad = 10
    month_header_height = 30

    grid_top = y
    for month in range(1, 13):
        row, col = divmod(month - 1, cols)
        bx = PADDING + col * col_width
        by = grid_top + row * row_height

        symbols = months_data.get(month, [])

        draw.rectangle([bx, by, bx + col_width, by + row_height], outline=RULE_COLOR, width=1, fill=BACKGROUND)
        month_label = MONTH_LABELS[month - 1]
        month_label_w = draw.textlength(month_label, font=month_font)
        draw.text((bx + (col_width - month_label_w) / 2, by + 7), month_label, font=month_font, fill=TITLE_COLOR)

        # Three explicit vertical zones per box: header (month label,
        # fixed above), footer (the "+N" note, fixed below -- reserved on
        # every month, not just overflowing ones, so the body zone's
        # height -- and therefore logo_cell -- stays identical across all
        # 12 boxes), and body (everything between: the logo grid or the
        # "No payouts scheduled" text, centered in the body zone's own
        # bounds). box_pad separates each zone from its neighbor.
        footer_zone_height = 26
        body_top = by + month_header_height + box_pad
        body_bottom = by + row_height - box_pad - footer_zone_height - box_pad
        body_height = body_bottom - body_top
        body_width = col_width - 2 * box_pad
        content_cx = bx + col_width / 2
        footer_cy = by + row_height - box_pad - footer_zone_height / 2

        if not symbols:
            no_data_text = "No payouts scheduled"
            no_data_w = draw.textlength(no_data_text, font=note_font)
            text_y = body_top + (body_height - FOOTER_LINE_HEIGHT) / 2
            draw.text((content_cx - no_data_w / 2, text_y), no_data_text, font=note_font, fill=SUBTITLE_COLOR)
            continue

        shown_symbols = symbols[:MAX_LOGOS_PER_MONTH_BOX]
        remaining = len(symbols) - len(shown_symbols)
        n_shown = len(shown_symbols)

        # Fixed cell size (sized to fit a 2x2 grid, the densest case at
        # MAX_LOGOS_PER_MONTH_BOX) so a single-logo month doesn't blow its
        # one logo up to fill the whole box -- every month's logos render
        # at the same scale, just with fewer grid cells used. Each row
        # also reserves room for a ticker label under the logo (skipped
        # for text-fallback cells, since the cell's text already is the
        # ticker), so the row unit is logo_cell + label_gap + label_height.
        # col_gap/row_gap are separate (not one shared cell_gap) since the
        # body zone has much more width to spare than height -- a bigger
        # row_gap would shrink logo_cell enough to truncate ticker labels.
        col_gap = 14
        row_gap = 6
        label_gap = 3
        label_height = 11
        logo_cell = int(min(
            (body_width - col_gap) / 2,
            (body_height - row_gap) / 2 - (label_gap + label_height),
        ))
        logo_cell = max(logo_cell, 16)
        row_unit = logo_cell + label_gap + label_height

        grid_cols = min(2, n_shown)
        grid_rows = math.ceil(n_shown / grid_cols)
        grid_w = grid_cols * logo_cell + (grid_cols - 1) * col_gap
        grid_h = grid_rows * row_unit + (grid_rows - 1) * row_gap
        start_x = content_cx - grid_w / 2
        start_y = body_top + (body_height - grid_h) / 2

        for idx, symbol in enumerate(shown_symbols):
            r, c = divmod(idx, grid_cols)
            lx = start_x + c * (logo_cell + col_gap)
            ly = start_y + r * (row_unit + row_gap)
            logo = _load_logo(symbol, logo_cell)
            if logo:
                image.paste(logo, (int(lx), int(ly)), logo)
                ticker_text = _truncate_to_width(draw, symbol, ticker_font, logo_cell)
                ticker_w = draw.textlength(ticker_text, font=ticker_font)
                draw.text(
                    (lx + (logo_cell - ticker_w) / 2, ly + logo_cell + label_gap),
                    ticker_text, font=ticker_font, fill=ROW_TEXT,
                )
            else:
                draw.rounded_rectangle(
                    [lx, ly, lx + logo_cell, ly + logo_cell],
                    radius=6, fill=ROW_ALT_BG, outline=RULE_COLOR, width=1,
                )
                text = _truncate_to_width(draw, symbol, fallback_font, logo_cell)
                text_w = draw.textlength(text, font=fallback_font)
                draw.text((lx + (logo_cell - text_w) / 2, ly + logo_cell / 2 - 5), text, font=fallback_font, fill=ROW_TEXT)

        if remaining > 0:
            note = f"+{remaining}"
            note_w = draw.textlength(note, font=note_font)
            draw.text((content_cx - note_w / 2, footer_cy - FOOTER_LINE_HEIGHT / 2), note, font=note_font, fill=SUBTITLE_COLOR)

    footer_y = HEIGHT - PADDING - footer_height
    draw.line([(PADDING, footer_y), (WIDTH - PADDING, footer_y)], fill=RULE_COLOR, width=1)
    fy = footer_y + 16
    for line in footer_lines:
        draw.text((PADDING, fy), line, font=footer_font, fill=FOOTER_COLOR)
        fy += FOOTER_LINE_HEIGHT

    _draw_watermark(draw, WIDTH, HEIGHT)
    image.save(output_path, "PNG")
    return output_path


def render_ticker_logo_grid(title, subtitle, symbols, footer_lines, output_path):
    """Renders every symbol in a flat, uncapped logo grid (falling back to
    a bordered placeholder square for any ticker with no cached logo) on
    a fixed WIDTHxHEIGHT (1080x1080) canvas -- a detail/reference image
    for a single month's full ticker list, unlike the capped per-month
    grid in render_year_overview(). Each logo-backed entry shows its
    ticker symbol underneath (placeholder cells already show the ticker
    as their content, so they don't get a duplicate label). Column count
    is round(sqrt(count)) (a near-square grid), and cell size is derived
    from that column/row count to fill the available canvas area (capped
    at a sane max so a short list doesn't blow up into giant tiles) --
    since rows and columns grow together via sqrt, this fills the space
    properly instead of the awkward single-gap look a fixed small cell
    size with leftover height would produce.
    """
    title_font = _font("DejaVuSans-Bold.ttf", 34)
    subtitle_font = _font("DejaVuSans.ttf", 20)
    fallback_font = _font("DejaVuSans-Bold.ttf", 10)
    ticker_font = _font("DejaVuSans-Bold.ttf", 12)
    footer_font = _font("DejaVuSans.ttf", 15)

    col_gap = 16
    row_gap = 16
    label_gap = 8
    label_height = 14
    max_logo_cell = 220

    n = len(symbols)
    cols = n if n <= 2 else round(math.sqrt(n))
    cols = max(1, cols)
    rows = max(1, math.ceil(n / cols))

    footer_height = len(footer_lines) * FOOTER_LINE_HEIGHT + 32
    bottom_margin = 16  # breathing room above the footer rule
    available_height = HEIGHT - PADDING - TITLE_BLOCK_HEIGHT - footer_height - PADDING - bottom_margin
    available_width = WIDTH - 2 * PADDING

    # Column tracks are equal-width (like CSS grid-template-columns: 1fr
    # 1fr 1fr), spanning the full available width -- not sized to the
    # logo and packed with a small gap. Each item is then centered within
    # its own track (justify-items: center), so tracks stay evenly split
    # regardless of how big any single logo is.
    col_track_width = (available_width - (cols - 1) * col_gap) / cols

    logo_cell = min(
        col_track_width,
        (available_height - (rows - 1) * row_gap) / rows - (label_gap + label_height),
        max_logo_cell,
    )
    logo_cell = max(int(logo_cell), 16)
    row_unit = logo_cell + label_gap + label_height
    top_margin = 0

    # Row tracks are equal-height (like grid-template-rows: 1fr 1fr),
    # spanning the full available height -- mirrors the equal-width
    # column tracks above -- with each row's content (logo + label)
    # vertically centered within its track (align-items: center) so the
    # grid stretches to fill the space instead of leaving it below.
    row_track_height = (available_height - (rows - 1) * row_gap) / rows

    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    y = _draw_title_header(draw, title, subtitle, title_font, subtitle_font) + top_margin

    for idx, symbol in enumerate(symbols):
        r, c = divmod(idx, cols)
        col_left = PADDING + c * (col_track_width + col_gap)
        lx = col_left + (col_track_width - logo_cell) / 2
        row_top = y + r * (row_track_height + row_gap)
        ly = row_top + (row_track_height - row_unit) / 2
        logo = _load_logo(symbol, logo_cell)
        if logo:
            image.paste(logo, (int(lx), int(ly)), logo)
            ticker_text = _truncate_to_width(draw, symbol, ticker_font, logo_cell)
            ticker_w = draw.textlength(ticker_text, font=ticker_font)
            draw.text(
                (lx + (logo_cell - ticker_w) / 2, ly + logo_cell + label_gap),
                ticker_text, font=ticker_font, fill=ROW_TEXT,
            )
        else:
            draw.rounded_rectangle(
                [lx, ly, lx + logo_cell, ly + logo_cell],
                radius=6, fill=ROW_ALT_BG, outline=RULE_COLOR, width=1,
            )
            text = _truncate_to_width(draw, symbol, fallback_font, logo_cell)
            text_w = draw.textlength(text, font=fallback_font)
            draw.text((lx + (logo_cell - text_w) / 2, ly + logo_cell / 2 - 5), text, font=fallback_font, fill=ROW_TEXT)

    footer_y = HEIGHT - PADDING - footer_height
    draw.line([(PADDING, footer_y), (WIDTH - PADDING, footer_y)], fill=RULE_COLOR, width=1)
    fy = footer_y + 16
    for line in footer_lines:
        draw.text((PADDING, fy), line, font=footer_font, fill=FOOTER_COLOR)
        fy += FOOTER_LINE_HEIGHT

    _draw_watermark(draw, WIDTH, HEIGHT)
    image.save(output_path, "PNG")
    return output_path
