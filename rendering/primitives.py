"""Shared drawing helpers used by every card renderer in this package."""

import json
import os

from PIL import Image, ImageFont

from .theme import (
    ASSETS_LOGO_DIR,
    CHIP_HEIGHT,
    CHIP_PADDING_X,
    CHIP_TINT_BASE,
    COMPANY_DIRECTORY_CACHE,
    FONT_DIR,
    LOGO_GAP,
    PADDING,
    SECTION_RULE_COLOR,
    SUBTITLE_COLOR,
    TITLE_BLOCK_HEIGHT,
    TITLE_COLOR,
    WATERMARK_COLOR,
    WATERMARK_TEXT,
    WIDTH,
)


def _font(name, size):
    return ImageFont.truetype(f"{FONT_DIR}/{name}", size)


def _draw_watermark_inline(draw, y):
    """Draws the watermark right-aligned on the same row as the footer's
    last text line (at the given y), rather than on its own row below the
    footer -- keeps the whole footer block to one line's worth of height
    instead of two.
    """
    font = _font("DejaVuSans.ttf", 14)
    text_width = draw.textlength(WATERMARK_TEXT, font=font)
    x = WIDTH - PADDING - text_width
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
    draw.line([(PADDING, header_bottom - 18), (WIDTH - PADDING, header_bottom - 18)], fill=SECTION_RULE_COLOR, width=2)
    return header_bottom


def _truncate_to_width(draw, text, font, max_width):
    if draw.textlength(text, font=font) <= max_width:
        return text

    ellipsis = "..."
    truncated = text
    while truncated and draw.textlength(truncated + ellipsis, font=font) > max_width:
        truncated = truncated[:-1]
    return (truncated + ellipsis) if truncated else ellipsis


def _wrap_to_width(draw, text, font, max_width, max_lines=2):
    """Word-wraps text into up to max_lines lines that each fit max_width.
    No word is ever dropped or ellipsis-truncated: if words are still left
    over once max_lines is reached, they're all appended to the final
    line instead, even if that makes it wider than max_width -- the full
    name always stays visible, just possibly overflowing its cell rather
    than losing words.
    """
    words = text.split()
    lines = []
    current = ""
    i = 0
    while i < len(words) and len(lines) < max_lines:
        word = words[i]
        candidate = f"{current} {word}".strip()
        if not current or draw.textlength(candidate, font=font) <= max_width:
            current = candidate
            i += 1
        else:
            lines.append(current)
            current = ""
    if current:
        lines.append(current)

    if i < len(words) and lines:
        lines[-1] = f"{lines[-1]} {' '.join(words[i:])}"

    return lines


_logo_cache = {}

# Generous for an icon-sized company logo (2000x2000), well under Pillow's
# own 89M-pixel DecompressionBombWarning threshold -- catches an
# oversized/corrupted download before Pillow's own safety check would.
MAX_LOGO_SOURCE_PIXELS = 4_000_000


def _load_logo(symbol, size):
    cache_key = (symbol, size)
    if cache_key in _logo_cache:
        return _logo_cache[cache_key]

    path = os.path.join(ASSETS_LOGO_DIR, f"{symbol}.png")
    logo = None
    if os.path.exists(path):
        try:
            source = Image.open(path)
            if source.width * source.height <= MAX_LOGO_SOURCE_PIXELS:
                source = source.convert("RGBA")
                source.thumbnail((size, size), Image.LANCZOS)
                logo = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                offset = ((size - source.width) // 2, (size - source.height) // 2)
                logo.paste(source, offset, source)
        except Exception:
            logo = None

    _logo_cache[cache_key] = logo
    return logo


def _tint_chip(hex_color, amount=0.82, base=CHIP_TINT_BASE):
    """Blends hex_color toward `base` -- the current theme's own chip
    surface tone (a dark elevated surface in dark mode, a soft-light
    surface in light mode) -- so status chips read as a tinted pill that
    matches the canvas instead of a fixed pastel meant for one mode only.
    """
    hex_color = hex_color.lstrip("#")
    base = base.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    br, bg, bb = int(base[0:2], 16), int(base[2:4], 16), int(base[4:6], 16)
    r = int(r + (br - r) * amount)
    g = int(g + (bg - g) * amount)
    b = int(b + (bb - b) * amount)
    return f"#{r:02x}{g:02x}{b:02x}"


def _draw_chip(image, draw, x, y, text, font, color, symbol=None):
    logo_offset = 0
    if symbol:
        logo = _load_logo(symbol, CHIP_HEIGHT)
        if logo:
            image.paste(logo, (int(x), int(y)), logo)
            logo_offset = CHIP_HEIGHT + LOGO_GAP

    chip_x = x + logo_offset
    bg = _tint_chip(color)
    text_width = draw.textlength(text, font=font)
    chip_width = text_width + 2 * CHIP_PADDING_X
    draw.rounded_rectangle(
        [chip_x, y, chip_x + chip_width, y + CHIP_HEIGHT],
        radius=CHIP_HEIGHT / 2,
        fill=bg,
    )
    draw.text((chip_x + CHIP_PADDING_X, y), text, font=font, fill=color)
    return logo_offset + chip_width


_company_name_cache = None


def _company_name(symbol):
    """Full company name for a ticker symbol, from the cached PSE company
    directory (see scraper/market_movers.py, which maintains this cache).
    Falls back to the symbol itself if the cache is missing or the symbol
    isn't found in it.
    """
    global _company_name_cache
    if _company_name_cache is None:
        _company_name_cache = {}
        if os.path.exists(COMPANY_DIRECTORY_CACHE):
            with open(COMPANY_DIRECTORY_CACHE) as f:
                companies = json.load(f)
            _company_name_cache = {c["symbol"]: c["company"] for c in companies}

    return _company_name_cache.get(symbol, symbol)
