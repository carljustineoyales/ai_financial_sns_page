"""render_declaration_card: a punchier, single-declaration hero card --
big ticker + type, a colored growth line, the rate as a hero number, and
two date pills. Structurally inspired by a reference competitor card, but
built entirely from this project's own brand palette (rendering/theme.py,
sourced from DESIGN.md) and rounded.pill token, not the reference's photo
background or branding. Rendered from rendering/templates/dividend_declaration_card.html
via html_render.render_card -- see that module for the HTML->PNG pipeline.
"""

from .html_render import render_card
from .primitives import _company_name, _logo_src
from .theme import WATERMARK_TEXT

# Above this length, the rate text drops from the big hero-number size
# to a smaller one (see .rate-value--long in the template) instead of
# overflowing the rate box -- PSE's own rate text ranges from a short
# number ("PhP11.758 per share") to a full verbose preferred-share
# description running 100+ characters.
RATE_HERO_LENGTH_LIMIT = 26


def render_declaration_card(
    symbol, dividend_type, rate_text, ex_date_text, payment_date_text, growth_pct, footer_lines, output_path,
    prior_rate_text=None, security_type=None,
):
    """growth_pct: signed float (e.g. 3.7959) or None to omit the growth
    line entirely (no comparable prior-year declaration was found).
    footer_lines: list of strings, joined into one wrapped paragraph
    (the browser handles wrapping, unlike the old fixed-canvas Pillow
    renderer's manual line-wrap math).
    prior_rate_text: the ~1-year-prior declaration's formatted rate text
    (e.g. "Php61.179 per share, Aug 19, 2025"), shown as a muted subtext
    under the rate box, or None to omit it -- same "no comparable
    prior-year declaration" case growth_pct=None covers.
    security_type: PSE Edge's "Type of Security" for this declaration
    (e.g. "COMMON", "GLOBA", "GLOPA") -- a company can have several
    concurrent instruments under one ticker/logo (common stock plus one
    or more preferred series), so a non-COMMON value is appended to the
    ticker subtitle (e.g. "GLO · GLOBA") to disambiguate which
    instrument this card is about. COMMON itself is the default case and
    never shown -- only preferred series need the extra label.
    """
    growth = None
    if growth_pct is not None:
        direction = "Higher" if growth_pct >= 0 else "Lower"
        growth = {
            "direction_class": "up" if growth_pct >= 0 else "down",
            "text": f"{abs(growth_pct):.2f}% {direction} than ~1 year ago",
        }

    ticker_subtitle = symbol
    if security_type and security_type != "COMMON":
        ticker_subtitle = f"{symbol} · {security_type}"

    context = {
        "eyebrow": f"{dividend_type.upper()} DIVIDEND DECLARATION",
        "symbol": symbol,
        "ticker_subtitle": ticker_subtitle,
        "company_name": _company_name(symbol),
        "logo_src": _logo_src(symbol),
        "growth": growth,
        "rate_text": rate_text,
        "rate_is_long": len(rate_text) > RATE_HERO_LENGTH_LIMIT,
        "prior_rate_text": prior_rate_text,
        "ex_date_text": ex_date_text,
        "payment_date_text": payment_date_text,
        "footer_text": " ".join(footer_lines),
        "watermark": WATERMARK_TEXT,
    }

    return render_card("dividend_declaration_card.html", context, output_path)
