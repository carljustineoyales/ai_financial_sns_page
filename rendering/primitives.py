"""Shared helpers used by every card renderer in this package. _font,
_draw_title_header, _draw_watermark_inline, _watermark_reserve_width,
_truncate_to_width, _load_logo, and _wrap_footer_lines_with_swatch are
Pillow drawing helpers kept only for dividend_stamp.py, the one renderer
still Pillow-based (it has no rendering/templates/*.html counterpart).
Every other renderer in this package is HTML/Playwright-based (see
html_render.py) and uses _logo_src/_company_name/_estimate_footer_line_count
instead.
"""

import json
import os
import warnings

from PIL import Image, ImageFont

from .theme import (
    ASSETS_LOGO_DIR,
    COMPANY_DIRECTORY_CACHE,
    FONT_DIR,
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


def _watermark_reserve_width(draw):
    """Pixel width to subtract from a footer line's available wrap width
    so no line -- not just a short one-liner, a long disclaimer can wrap
    to several lines -- ever runs into the watermark sharing the last
    line's row (see _draw_watermark_inline). Applied to every wrapped
    line, not just the last, since which line ends up last isn't known
    until after wrapping.
    """
    font = _font("DejaVuSans.ttf", 14)
    return draw.textlength(WATERMARK_TEXT, font=font) + 16


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


def _wrap_footer_lines_with_swatch(draw, footer_lines, font, max_width, max_lines_per_entry=8):
    """Same wrapping behavior as _wrap_footer_lines, for
    render_dividend_stamp_card's (color, text) tuple footer_lines --
    a wrapped entry's color swatch is drawn once, on its first line only.
    """
    wrapped = []
    for color, text in footer_lines:
        if draw.textlength(text, font=font) <= max_width:
            wrapped.append((color, text))
        else:
            lines = _wrap_to_width(draw, text, font, max_width, max_lines=max_lines_per_entry)
            for i, line in enumerate(lines):
                wrapped.append((color if i == 0 else None, line))
    return wrapped


_logo_cache = {}

# Generous for an icon-sized company logo (2000x2000), well under Pillow's
# own 89M-pixel DecompressionBombWarning threshold. Pillow fires its own
# warning as a side effect of Image.open() itself (as soon as it reads the
# file's declared dimensions from the header), before any code here gets a
# chance to compare against this cap -- so opening has to happen inside a
# warnings suppression block, not just be followed by a size check.
MAX_LOGO_SOURCE_PIXELS = 4_000_000


def _open_image_no_bomb_warning(path):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", Image.DecompressionBombWarning)
        return Image.open(path)


def _load_logo(symbol, size):
    cache_key = (symbol, size)
    if cache_key in _logo_cache:
        return _logo_cache[cache_key]

    path = os.path.join(ASSETS_LOGO_DIR, f"{symbol}.png")
    logo = None
    if os.path.exists(path):
        try:
            source = _open_image_no_bomb_warning(path)
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


def _estimate_footer_line_count(text, width_px, font_px=15, avg_char_width_ratio=0.52):
    """Rough line count for wrapped footer text at width_px, used only to
    budget how many rows/items a variable-length card body can show
    before it'd push the footer past the fixed 1080px canvas -- the
    browser does the actual wrapping (see rendering/templates/_shared.css
    .footer-text), so this only needs to be a reasonable estimate, not
    pixel-exact.
    """
    chars_per_line = max(1, int(width_px / (font_px * avg_char_width_ratio)))
    return max(1, -(-len(text) // chars_per_line))


def _logo_src(symbol):
    """Path to symbol's cached logo, relative to a rendered template's
    temp file location (rendering/templates/<tmpfile>.html), or None if
    no logo is cached -- callers' templates fall back to plain
    ticker/symbol text in that case, same graceful-absence behavior the
    old Pillow renderers had via _load_logo returning None.
    """
    path = os.path.join(ASSETS_LOGO_DIR, f"{symbol}.png")
    if not os.path.exists(path):
        return None
    return os.path.join("..", "..", path)


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
