"""Builds the report-card graphic for a single company's financial figures
(stated + derived ratios). No Facebook/posting dependency, no LLM call --
pure rendering from already-extracted/computed data.
"""

import rendering as renderer
from dividend_graphics import DISCLAIMER

# Row priority: most informative fields first, so if the fixed-canvas
# table card has to truncate, the important rows survive. Each entry is
# (key, label, source) where source is "stated" (raw field, .stated text),
# "stated_only" (REIT-only field, plain string), or "derived" (a computed
# ratio, from analysis/ratios.py).
METRIC_ORDER = [
    ("revenue", "Revenue", "stated"),
    ("net_income", "Net Income", "stated"),
    ("operating_income", "Operating Income", "stated"),
    ("net_margin", "Net Margin (derived)", "derived_pct"),
    ("operating_margin", "Operating Margin (derived)", "derived_pct"),
    ("ebitda_margin", "EBITDA Margin (derived)", "derived_pct"),
    ("distributable_income", "Distributable Income", "stated_only"),
    ("leverage_ratio", "Leverage Ratio", "stated_only"),
    ("nav_per_share", "NAV per Share", "stated_only"),
    ("occupancy_rate", "Occupancy Rate", "stated_only"),
    ("current_ratio", "Current Ratio (derived)", "derived_num"),
    ("debt_to_equity", "Debt to Equity (derived)", "derived_num"),
    ("asset_to_equity", "Asset to Equity (derived)", "derived_num"),
    ("interest_coverage", "Interest Coverage (derived)", "derived_num"),
    ("roe", "ROE, period-end (derived)", "derived_pct"),
    ("roa", "ROA, period-end (derived)", "derived_pct"),
    ("asset_turnover", "Asset Turnover (derived)", "derived_num"),
    ("cfo", "Cash Flow from Operations", "stated"),
    ("cfi", "Cash Flow from Investing", "stated"),
    ("cff", "Cash Flow from Financing", "stated"),
    ("dividend_per_share", "Dividend per Share", "stated"),
    ("pe_ratio", "P/E Ratio (derived)", "derived_num"),
    ("pb_ratio", "P/B Ratio (derived)", "derived_num"),
]


def _format_pct(value):
    return f"{value * 100:.1f}%"


def _format_num(value):
    return f"{value:.2f}"


def report_rows(data, computed, valuation):
    rows = []
    for key, label, source in METRIC_ORDER:
        if source in ("stated", "stated_only"):
            field = data.get(key)
            value = field.get("stated") if field else None
        elif source == "derived_pct":
            raw = computed.get(key, valuation.get(key) if valuation else None)
            value = _format_pct(raw) if raw is not None else None
        elif source == "derived_num":
            raw = computed.get(key, valuation.get(key) if valuation else None)
            value = _format_num(raw) if raw is not None else None
        else:
            value = None

        if value:
            rows.append({"metric": label, "value": value})

    return rows


def build_report_card(symbol, template_name, data, computed, valuation, output_path):
    period = data.get("period") or "unspecified period"
    title = f"{symbol} REPORT CARD"
    subtitle = f"{template_name} — {period}"

    rows = report_rows(data, computed, valuation)
    columns = [("metric", "Metric", 0.55), ("value", "Value", 0.45)]
    footer_lines = [DISCLAIMER]

    return renderer.render_table_card(title, subtitle, rows, columns, footer_lines, output_path)


def figures_text(data, computed, valuation):
    rows = report_rows(data, computed, valuation)
    return "\n".join(f"{row['metric']}: {row['value']}" for row in rows)
