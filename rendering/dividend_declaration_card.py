"""render_declaration_card: a punchier, single-declaration hero card --
big ticker + type, a colored growth line, the rate as a hero number, and
two date pills. Structurally inspired by a reference competitor card, but
built entirely from this project's own Zapier-style warm-cream palette
(rendering/theme.py) and rounded.pill token (DESIGN.md), not the
reference's photo background or branding.
"""

from PIL import Image, ImageDraw

from .primitives import _draw_watermark_inline, _font, _truncate_to_width
from .theme import (
    BACKGROUND,
    CANVAS_SOFT,
    FOOTER_BOTTOM_MARGIN,
    FOOTER_COLOR,
    FOOTER_LINE_HEIGHT,
    HEIGHT,
    INK,
    INK_SOFT,
    PADDING,
    PRIMARY_ORANGE,
    RADIUS_CARD,
    SECTION_RULE_COLOR,
    SUBTITLE_COLOR,
    TRADING_DOWN,
    TRADING_UP,
    WIDTH,
)

PILL_HEIGHT = 64
PILL_GAP = 16
PILL_GROUP_GAP = 20


def _draw_date_pill(draw, x, y, width, date_text, label_text, date_font, label_font):
    """A dark rounded-9999px pill holding the date, with its label to the
    right -- the same two-part row shape as the reference image's
    ex-date/payment-date rows, in this project's own ink/cream palette
    instead of the reference's coral/cream.
    """
    pill_width = 190
    draw.rounded_rectangle([x, y, x + pill_width, y + PILL_HEIGHT], radius=PILL_HEIGHT / 2, fill=INK)
    date_width = draw.textlength(date_text, font=date_font)
    date_x = x + (pill_width - date_width) / 2
    draw.text((date_x, y + (PILL_HEIGHT - 26) / 2), date_text, font=date_font, fill=BACKGROUND)

    label_x = x + pill_width + 20
    label_width = width - pill_width - 20
    label_text = _truncate_to_width(draw, label_text, label_font, label_width)
    draw.text((label_x, y + (PILL_HEIGHT - 24) / 2), label_text, font=label_font, fill=INK_SOFT)


def render_declaration_card(
    symbol, dividend_type, rate_text, ex_date_text, payment_date_text, growth_pct, footer_lines, output_path
):
    """growth_pct: signed float (e.g. 3.7959) or None to omit the growth
    line entirely (no comparable prior-year declaration was found).
    """
    ticker_font = _font("DejaVuSans-Bold.ttf", 96)
    type_font = _font("DejaVuSans-Bold.ttf", 40)
    growth_font = _font("DejaVuSans-Bold.ttf", 34)
    rate_label_font = _font("DejaVuSans.ttf", 22)
    rate_font = _font("DejaVuSans-Bold.ttf", 56)
    pill_date_font = _font("DejaVuSans-Bold.ttf", 22)
    pill_label_font = _font("DejaVuSans-Bold.ttf", 22)
    footer_font = _font("DejaVuSans.ttf", 15)

    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    # Content height varies (the growth line is optional), so the block is
    # vertically centered in the space above the footer rather than
    # anchored to the top -- otherwise a card with no growth match leaves
    # a large awkward gap before the footer instead of a balanced layout.
    content_height = 100 + 56 + 40 + (56 if growth_pct is not None else 0) + 20 + 160 + 40 + 2 * PILL_HEIGHT + PILL_GAP + PILL_GROUP_GAP
    footer_height = len(footer_lines) * FOOTER_LINE_HEIGHT + 32
    available_height = HEIGHT - PADDING - footer_height - FOOTER_BOTTOM_MARGIN
    y = PADDING + max(0, (available_height - content_height) // 2)

    draw.text((PADDING, y), symbol, font=ticker_font, fill=INK)
    y += 100
    draw.text((PADDING, y), f"{dividend_type.upper()} DIVIDEND DECLARATION", font=type_font, fill=PRIMARY_ORANGE)
    y += 56
    draw.line([(PADDING, y), (WIDTH - PADDING, y)], fill=PRIMARY_ORANGE, width=4)
    y += 40

    if growth_pct is not None:
        direction = "HIGHER" if growth_pct >= 0 else "LOWER"
        color = TRADING_UP if growth_pct >= 0 else TRADING_DOWN
        draw.text(
            (PADDING, y),
            f"{abs(growth_pct):.2f}% {direction} THAN ~1 YEAR AGO",
            font=growth_font,
            fill=color,
        )
        y += 56

    y += 20
    draw.rounded_rectangle([PADDING, y, WIDTH - PADDING, y + 160], radius=RADIUS_CARD, fill=CANVAS_SOFT)
    draw.text((PADDING + 24, y + 24), "DIVIDEND RATE", font=rate_label_font, fill=SUBTITLE_COLOR)
    rate_text_fit = _truncate_to_width(draw, rate_text, rate_font, WIDTH - 2 * PADDING - 48)
    draw.text((PADDING + 24, y + 56), rate_text_fit, font=rate_font, fill=INK)
    y += 160 + 40

    pill_width = WIDTH - 2 * PADDING
    _draw_date_pill(draw, PADDING, y, pill_width, ex_date_text, "Ex-Dividend Date", pill_date_font, pill_label_font)
    y += PILL_HEIGHT + PILL_GAP
    _draw_date_pill(draw, PADDING, y, pill_width, payment_date_text, "Payment Date", pill_date_font, pill_label_font)
    y += PILL_HEIGHT + PILL_GROUP_GAP

    footer_y = HEIGHT - FOOTER_BOTTOM_MARGIN - footer_height
    draw.line([(PADDING, footer_y), (WIDTH - PADDING, footer_y)], fill=SECTION_RULE_COLOR, width=2)
    fy = footer_y + 16
    for line in footer_lines:
        draw.text((PADDING, fy), line, font=footer_font, fill=FOOTER_COLOR)
        fy += FOOTER_LINE_HEIGHT

    _draw_watermark_inline(draw, fy - FOOTER_LINE_HEIGHT)
    image.save(output_path, "PNG")
    return output_path
