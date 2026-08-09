"""render_declaration_card: a punchier, single-declaration hero card --
big ticker + type, a colored growth line, the rate as a hero number, and
two date pills. Structurally inspired by a reference competitor card, but
built entirely from this project's own brand palette (rendering/theme.py,
sourced from DESIGN.md) and rounded.pill token, not the reference's photo
background or branding.
"""

from PIL import Image, ImageDraw

from .primitives import _draw_watermark_inline, _font, _truncate_to_width, _wrap_to_width
from .theme import (
    BACKGROUND,
    CANVAS_SOFT,
    FOOTER_BOTTOM_MARGIN,
    FOOTER_COLOR,
    FOOTER_LINE_HEIGHT,
    HAIRLINE,
    HEIGHT,
    INK,
    INK_SOFT,
    MUTE,
    PADDING,
    RADIUS_CARD,
    SECTION_RULE_COLOR,
    TRADING_DOWN,
    TRADING_UP,
    WIDTH,
)

MONO_FONT_FILE = "DejaVuSansMono-Bold.ttf"

PILL_HEIGHT = 64
PILL_GAP = 16
PILL_GROUP_GAP = 20


def _draw_date_pill(draw, x, y, width, date_text, label_text, date_font, label_font):
    """A dark rounded-pill holding the date, with its label to the right
    -- the same two-part row shape as the reference image's ex-date/
    payment-date rows, in this project's own ink/canvas palette instead
    of the reference's coral/cream.
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


def _fit_rate_lines(draw, rate_text, max_width):
    """PSE's own rate text ranges from a short number ("PhP11.758 per
    share") to a full verbose preferred-share description running 100+
    characters. Rather than truncating the long ones with an ellipsis
    (losing the actual rate terms), try the big hero-number size first on
    one line, and only drop to a smaller size + wrap (up to 3 lines) when
    it doesn't fit -- short rates keep the punchy big-number look, long
    ones stay fully readable. Returns (lines, font, line_height).
    """
    hero_font = _font("DejaVuSans-Bold.ttf", 56)
    if draw.textlength(rate_text, font=hero_font) <= max_width:
        return [rate_text], hero_font, 62

    wrap_font = _font("DejaVuSans-Bold.ttf", 30)
    lines = _wrap_to_width(draw, rate_text, wrap_font, max_width, max_lines=3)
    return lines, wrap_font, 36


def render_declaration_card(
    symbol, dividend_type, rate_text, ex_date_text, payment_date_text, growth_pct, footer_lines, output_path
):
    """growth_pct: signed float (e.g. 3.7959) or None to omit the growth
    line entirely (no comparable prior-year declaration was found).
    """
    # DESIGN.md: "the one place color is allowed to exist is the hero...
    # everywhere else, restraint" / "don't fill large surfaces with the
    # accent colors" / "don't add a second decorative system." This card
    # has no hero mesh gradient, so it stays ink-on-white throughout --
    # ACCENT isn't used anywhere here. The "eyebrow" (small uppercase
    # Geist Mono label, DESIGN.md's own pattern for section labels) does
    # the emphasis work color did before.
    eyebrow_font = _font(MONO_FONT_FILE, 22)
    ticker_font = _font("DejaVuSans-Bold.ttf", 96)
    growth_font = _font("DejaVuSans-Bold.ttf", 34)
    rate_label_font = _font(MONO_FONT_FILE, 18)
    pill_date_font = _font("DejaVuSans-Bold.ttf", 22)
    pill_label_font = _font("DejaVuSans-Bold.ttf", 22)
    footer_font = _font("DejaVuSans.ttf", 15)

    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    rate_lines, rate_font, rate_line_height = _fit_rate_lines(draw, rate_text, WIDTH - 2 * PADDING - 48)
    rate_box_height = 24 + 24 + 8 + len(rate_lines) * rate_line_height + 20

    # Content height varies (the growth line is optional, the rate box
    # grows for long/wrapped rate text), so the block is vertically
    # centered in the space above the footer rather than anchored to the
    # top -- otherwise a short card leaves a large awkward gap before the
    # footer instead of a balanced layout.
    content_height = 36 + 100 + 24 + (56 if growth_pct is not None else 0) + 20 + rate_box_height + 40 + 2 * PILL_HEIGHT + PILL_GAP + PILL_GROUP_GAP
    footer_height = len(footer_lines) * FOOTER_LINE_HEIGHT + 32
    available_height = HEIGHT - PADDING - footer_height - FOOTER_BOTTOM_MARGIN
    y = PADDING + max(0, (available_height - content_height) // 2)

    draw.text((PADDING, y), f"{dividend_type.upper()} DIVIDEND DECLARATION", font=eyebrow_font, fill=MUTE)
    y += 36
    draw.text((PADDING, y), symbol, font=ticker_font, fill=INK)
    y += 100
    draw.line([(PADDING, y), (WIDTH - PADDING, y)], fill=HAIRLINE, width=1)
    y += 24

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
    draw.rounded_rectangle([PADDING, y, WIDTH - PADDING, y + rate_box_height], radius=RADIUS_CARD, fill=CANVAS_SOFT)
    draw.text((PADDING + 24, y + 24), "DIVIDEND RATE", font=rate_label_font, fill=MUTE)
    line_y = y + 24 + 24 + 8
    for line in rate_lines:
        draw.text((PADDING + 24, line_y), line, font=rate_font, fill=INK)
        line_y += rate_line_height
    y += rate_box_height + 40

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
