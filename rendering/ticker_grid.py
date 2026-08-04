"""render_ticker_logo_grid: a flat, uncapped near-square logo grid."""

import math

from PIL import Image, ImageDraw

from .primitives import _company_name, _draw_title_header, _draw_watermark_inline, _font, _load_logo, _truncate_to_width, _wrap_to_width
from .theme import (
    BACKGROUND,
    BODY_FOOTER_GAP,
    FOOTER_BOTTOM_MARGIN,
    FOOTER_COLOR,
    FOOTER_LINE_HEIGHT,
    HEIGHT,
    PADDING,
    ROW_ALT_BG,
    ROW_TEXT,
    RULE_COLOR,
    SECTION_RULE_COLOR,
    SUBTITLE_COLOR,
    TITLE_BLOCK_HEIGHT,
    WIDTH,
)


def render_ticker_logo_grid(title, subtitle, symbols, footer_lines, output_path):
    """Renders every symbol in a flat, uncapped logo grid (falling back to
    a bordered placeholder square for any ticker with no cached logo) on
    a fixed WIDTHxHEIGHT (1080x1080) canvas -- a detail/reference image
    for a single month's full ticker list, unlike the capped per-month
    grid in render_year_overview(). Each entry shows its ticker symbol
    underneath (logo-backed entries) or as the placeholder's own content
    (no-logo entries), followed by the full company name (looked up via
    _company_name, truncated to fit) in a smaller line below that. Column count
    is round(sqrt(count)) (a near-square grid), and cell size is derived
    from that column/row count to fill the available canvas area (capped
    at a sane max so a short list doesn't blow up into giant tiles) --
    since rows and columns grow together via sqrt, this fills the space
    properly instead of the awkward single-gap look a fixed small cell
    size with leftover height would produce.
    """
    title_font = _font("DejaVuSans-Bold.ttf", 34)
    subtitle_font = _font("DejaVuSans.ttf", 20)
    fallback_font = _font("DejaVuSans-Bold.ttf", 16)
    ticker_font = _font("DejaVuSans-Bold.ttf", 16)
    company_name_font = _font("DejaVuSans.ttf", 16)
    footer_font = _font("DejaVuSans.ttf", 16)

    col_gap = 16
    row_gap = 16
    label_gap = 8
    label_height = 14
    company_name_gap = 8
    company_name_max_lines = 2
    name_bbox = company_name_font.getbbox("Ag")
    company_name_line_height = (name_bbox[3] - name_bbox[1]) + 2
    company_name_block_height = company_name_line_height * company_name_max_lines
    max_logo_cell = 220

    n = len(symbols)
    cols = n if n <= 2 else round(math.sqrt(n))
    cols = max(1, cols)
    rows = max(1, math.ceil(n / cols))

    footer_height = len(footer_lines) * FOOTER_LINE_HEIGHT + 32
    available_height = HEIGHT - PADDING - TITLE_BLOCK_HEIGHT - footer_height - FOOTER_BOTTOM_MARGIN - BODY_FOOTER_GAP
    available_width = WIDTH - 2 * PADDING

    # Column tracks are equal-width (like CSS grid-template-columns: 1fr
    # 1fr 1fr), spanning the full available width -- not sized to the
    # logo and packed with a small gap. Each item is then centered within
    # its own track (justify-items: center), so tracks stay evenly split
    # regardless of how big any single logo is.
    col_track_width = (available_width - (cols - 1) * col_gap) / cols

    label_block_height = label_gap + label_height + company_name_gap + company_name_block_height
    logo_cell = min(
        col_track_width,
        (available_height - (rows - 1) * row_gap) / rows - label_block_height,
        max_logo_cell,
    ) * 0.7
    logo_cell = max(int(logo_cell), 16)
    row_unit = logo_cell + label_block_height
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
        label_max_width = logo_cell + col_gap
        name_lines = _wrap_to_width(draw, _company_name(symbol), company_name_font, label_max_width, max_lines=company_name_max_lines)

        def _draw_name_lines(name_top):
            for line_idx, line in enumerate(name_lines):
                line_w = draw.textlength(line, font=company_name_font)
                draw.text(
                    (lx + (logo_cell - line_w) / 2, name_top + line_idx * company_name_line_height),
                    line, font=company_name_font, fill=SUBTITLE_COLOR,
                )

        logo = _load_logo(symbol, logo_cell)
        if logo:
            image.paste(logo, (int(lx), int(ly)), logo)
            ticker_text = _truncate_to_width(draw, symbol, ticker_font, label_max_width)
            ticker_w = draw.textlength(ticker_text, font=ticker_font)
            draw.text(
                (lx + (logo_cell - ticker_w) / 2, ly + logo_cell + label_gap),
                ticker_text, font=ticker_font, fill=ROW_TEXT,
            )
            _draw_name_lines(ly + logo_cell + label_gap + label_height + company_name_gap)
        else:
            draw.rounded_rectangle(
                [lx, ly, lx + logo_cell, ly + logo_cell],
                radius=6, fill=ROW_ALT_BG, outline=RULE_COLOR, width=1,
            )
            text = _truncate_to_width(draw, symbol, fallback_font, logo_cell)
            text_w = draw.textlength(text, font=fallback_font)
            draw.text((lx + (logo_cell - text_w) / 2, ly + logo_cell / 2 - 5), text, font=fallback_font, fill=ROW_TEXT)
            _draw_name_lines(ly + logo_cell + label_gap + company_name_gap)

    footer_y = HEIGHT - FOOTER_BOTTOM_MARGIN - footer_height
    draw.line([(PADDING, footer_y), (WIDTH - PADDING, footer_y)], fill=SECTION_RULE_COLOR, width=2)
    fy = footer_y + 16
    for line in footer_lines:
        draw.text((PADDING, fy), line, font=footer_font, fill=FOOTER_COLOR)
        fy += FOOTER_LINE_HEIGHT

    _draw_watermark_inline(draw, fy - FOOTER_LINE_HEIGHT)
    image.save(output_path, "PNG")
    return output_path
