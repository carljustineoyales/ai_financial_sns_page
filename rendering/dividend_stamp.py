"""render_dividend_stamp_card: a multi-column grid of per-date dividend cards."""

from PIL import Image, ImageDraw

from .primitives import _draw_title_header, _draw_watermark_inline, _font, _load_logo, _truncate_to_width
from .theme import (
    BACKGROUND,
    BODY_FOOTER_GAP,
    FOOTER_BOTTOM_MARGIN,
    FOOTER_COLOR,
    FOOTER_LINE_HEIGHT,
    HEIGHT,
    PADDING,
    RADIUS_CARD,
    ROW_ALT_BG,
    ROW_TEXT,
    SECTION_RULE_COLOR,
    STATUS_COLORS,
    TITLE_BLOCK_HEIGHT,
    TITLE_COLOR,
    WIDTH,
)

TICKER_LABEL_GAP = 4
TICKER_LABEL_HEIGHT = 15


def _dividend_grid_cols(n):
    if n <= 1:
        return 1
    if n <= 9:
        return 2
    return 3


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
    available_height = HEIGHT - PADDING - TITLE_BLOCK_HEIGHT - footer_height - FOOTER_BOTTOM_MARGIN - BODY_FOOTER_GAP

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
                radius=RADIUS_CARD,
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

    footer_y = HEIGHT - FOOTER_BOTTOM_MARGIN - footer_height
    draw.line([(PADDING, footer_y), (WIDTH - PADDING, footer_y)], fill=SECTION_RULE_COLOR, width=2)
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

    _draw_watermark_inline(draw, fy - FOOTER_LINE_HEIGHT)
    image.save(output_path, "PNG")
    return output_path
