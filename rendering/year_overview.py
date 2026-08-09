"""render_year_overview: a 3x4 grid of month boxes with ticker logos."""

from PIL import Image, ImageDraw

from .primitives import _draw_title_header, _draw_watermark_inline, _font, _load_logo, _truncate_to_width, _watermark_reserve_width, _wrap_footer_lines
from .theme import (
    BACKGROUND,
    BODY_FOOTER_GAP,
    FOOTER_BOTTOM_MARGIN,
    FOOTER_COLOR,
    FOOTER_LINE_HEIGHT,
    HEIGHT,
    MUTE,
    PADDING,
    ROW_ALT_BG,
    ROW_TEXT,
    SECTION_RULE_COLOR,
    SUBTITLE_COLOR,
    TITLE_BLOCK_HEIGHT,
    TITLE_COLOR,
    WIDTH,
)

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

    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    footer_lines = _wrap_footer_lines(draw, footer_lines, footer_font, WIDTH - 2 * PADDING - _watermark_reserve_width(draw))
    footer_height = len(footer_lines) * FOOTER_LINE_HEIGHT + 32
    grid_height = HEIGHT - PADDING - TITLE_BLOCK_HEIGHT - footer_height - FOOTER_BOTTOM_MARGIN - BODY_FOOTER_GAP
    grid_width = WIDTH - 2 * PADDING

    cols, box_rows = 3, 4
    col_width = grid_width // cols
    row_height = grid_height // box_rows

    y = _draw_title_header(draw, title, subtitle, title_font, subtitle_font)

    box_pad = 10
    month_header_height = 30

    grid_top = y
    for month in range(1, 13):
        row, col = divmod(month - 1, cols)
        bx = PADDING + col * col_width
        by = grid_top + row * row_height

        symbols = months_data.get(month, [])

        # Alternating checkerboard fill (not just a shared background for
        # every cell) plus a visibly-toned MUTE border, not the generic
        # hairline -- with all 12 cells otherwise identical, the grid
        # lines were the only thing separating one month's tickers from
        # the next, and DESIGN.md's hairline (#ebebeb) is too faint against
        # this fill to read as a real boundary. This is a genuinely
        # functional data grid, not a decorative divider, so it needs
        # real contrast the same way TRADING_UP/DOWN needed a real
        # green/red exception.
        cell_fill = ROW_ALT_BG if (row + col) % 2 == 0 else BACKGROUND
        draw.rectangle([bx, by, bx + col_width, by + row_height], outline=MUTE, width=1, fill=cell_fill)
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

        # Fixed cell size (sized to fit a single row of MAX_LOGOS_PER_MONTH_BOX,
        # the densest case) so a single-logo month doesn't blow its one logo
        # up to fill the whole box -- every month's logos render at the same
        # scale, just with fewer grid cells used. The label under each logo
        # (skipped for text-fallback cells, since the cell's text already is
        # the ticker) makes the row unit logo_cell + label_gap + label_height.
        col_gap = 8
        row_gap = 6
        label_gap = 3
        label_height = 11
        logo_cell = int(min(
            (body_width - (MAX_LOGOS_PER_MONTH_BOX - 1) * col_gap) / MAX_LOGOS_PER_MONTH_BOX,
            body_height - (label_gap + label_height),
        ))
        logo_cell = max(logo_cell, 16)
        row_unit = logo_cell + label_gap + label_height

        grid_cols = n_shown
        grid_rows = 1
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
                # Label width allowance is wider than the (now smaller)
                # logo cell itself, using half the column gap on each side
                # as slack -- otherwise shrinking the logo starves the
                # ticker label and every symbol past 3 characters truncates.
                label_max_width = logo_cell + col_gap
                ticker_text = _truncate_to_width(draw, symbol, ticker_font, label_max_width)
                ticker_w = draw.textlength(ticker_text, font=ticker_font)
                draw.text(
                    (lx + (logo_cell - ticker_w) / 2, ly + logo_cell + label_gap),
                    ticker_text, font=ticker_font, fill=ROW_TEXT,
                )
            else:
                draw.rounded_rectangle(
                    [lx, ly, lx + logo_cell, ly + logo_cell],
                    radius=6, fill=BACKGROUND, outline=MUTE, width=1,
                )
                text = _truncate_to_width(draw, symbol, fallback_font, logo_cell)
                text_w = draw.textlength(text, font=fallback_font)
                draw.text((lx + (logo_cell - text_w) / 2, ly + logo_cell / 2 - 5), text, font=fallback_font, fill=ROW_TEXT)

        if remaining > 0:
            note = f"+{remaining}"
            note_w = draw.textlength(note, font=note_font)
            draw.text((content_cx - note_w / 2, footer_cy - FOOTER_LINE_HEIGHT / 2), note, font=note_font, fill=SUBTITLE_COLOR)

    footer_y = HEIGHT - FOOTER_BOTTOM_MARGIN - footer_height
    draw.line([(PADDING, footer_y), (WIDTH - PADDING, footer_y)], fill=SECTION_RULE_COLOR, width=2)
    fy = footer_y + 16
    for line in footer_lines:
        draw.text((PADDING, fy), line, font=footer_font, fill=FOOTER_COLOR)
        fy += FOOTER_LINE_HEIGHT

    _draw_watermark_inline(draw, fy - FOOTER_LINE_HEIGHT)
    image.save(output_path, "PNG")
    return output_path
