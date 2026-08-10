"""Builds a single dividend-declaration card: rate, ex-dividend date,
payment date, and -- when a comparable prior-year declaration was found --
growth vs. that prior declaration. No Facebook/posting dependency.

The growth comparison is a date-proximity heuristic (closest declaration to
~365 days before this one), not a true same-period-type match -- PSE Edge
doesn't label a declaration's period (no "H1"/"Q2"/"Annual" field anywhere).
Captions phrase it as "around this time last year," not a specific period
label we can't actually confirm.
"""

import rendering as renderer
from dividend_graphics import DISCLAIMER

HASHTAGS = "#PSE #InvestPH #DividendDeclaration"


def _growth_pct(entry, prior_entry):
    if not prior_entry or not prior_entry.get("dividend_rate_value") or not entry.get("dividend_rate_value"):
        return None
    return (entry["dividend_rate_value"] - prior_entry["dividend_rate_value"]) / prior_entry["dividend_rate_value"] * 100


def build_declaration_card(symbol, entry, prior_entry, output_path):
    growth = _growth_pct(entry, prior_entry)
    footer_lines = [DISCLAIMER]

    prior_rate_text = None
    if prior_entry:
        prior_rate_text = f"{_format_rate(prior_entry['dividend_rate'])}, {prior_entry['ex_dividend_date']}"

    return renderer.render_declaration_card(
        symbol,
        entry["dividend_type"],
        _format_rate(entry["dividend_rate"]),
        entry["ex_dividend_date"],
        entry["payment_date"],
        growth,
        footer_lines,
        output_path,
        prior_rate_text=prior_rate_text,
        security_type=entry.get("security_type"),
    )


def _format_rate(rate_text):
    """PSE's own dividend_rate text is wildly inconsistent -- sometimes a
    bare number ("Php25"), sometimes already includes a unit in one of
    several phrasings ("Php25 per common share", "P0.79/Share"), sometimes
    a full verbose description for preferred shares ("Fixed annual rate
    of 6.1179%... using a 30/360 day convention."). Only append "per
    share" when the text doesn't already convey a per-share unit in any
    of its phrasings, to avoid "...per common share per share" or
    "P0.79/Share per share".
    """
    lowered = rate_text.lower()
    if "per" in lowered or "/share" in lowered.replace(" ", ""):
        return rate_text
    return f"{rate_text} per share"


def build_declaration_caption(symbol, entry, prior_entry):
    rate = _format_rate(entry["dividend_rate"]).rstrip(".")
    lines = [
        f"{symbol} declared a {entry['dividend_type'].lower()} dividend of {rate}.",
        f"Ex-dividend date is {entry['ex_dividend_date']}, payable {entry['payment_date']}.",
    ]

    growth = _growth_pct(entry, prior_entry)
    if growth is not None:
        direction = "higher" if growth >= 0 else "lower"
        lines.append(
            f"This is {abs(growth):.2f}% {direction} than its declaration around this time last year "
            f"({_format_rate(prior_entry['dividend_rate'])}, {prior_entry['ex_dividend_date']})."
        )

    body = "\n".join(lines)
    return f"{body}\n\n{DISCLAIMER}\n\n{HASHTAGS}"
