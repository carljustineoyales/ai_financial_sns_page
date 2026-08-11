"""Computes simple financial ratios from raw figures a filing explicitly
stated -- never via the LLM, and never approximating a ratio that needs
data the filing didn't provide (e.g. no gross margin without COGS, no FCF
without CapEx). Every function returns None for a ratio whose required
inputs are missing, rather than guessing.
"""


def _value(field):
    """Pulls the normalized numeric .value out of a {"stated":, "value":}
    extraction field, treating a missing/None field as no value at all.
    """
    if not field:
        return None
    return field.get("value")


def _safe_div(numerator, denominator):
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def compute_derived_metrics(data):
    """{ratio_name: float or None}, computed only from the .value of raw
    fields the filing explicitly stated. ROE/ROA use period-end balances
    (not the average of opening+closing), a simplification since a single
    filing's cover sheet doesn't carry the prior period's full balance
    sheet.
    """
    revenue = _value(data.get("revenue"))
    operating_income = _value(data.get("operating_income"))
    net_income = _value(data.get("net_income"))
    ebitda = _value(data.get("ebitda"))
    total_assets = _value(data.get("total_assets"))
    total_liabilities = _value(data.get("total_liabilities"))
    total_equity = _value(data.get("total_equity"))
    current_assets = _value(data.get("current_assets"))
    current_liabilities = _value(data.get("current_liabilities"))
    interest_expense = _value(data.get("interest_expense"))

    return {
        "operating_margin": _safe_div(operating_income, revenue),
        "net_margin": _safe_div(net_income, revenue),
        "ebitda_margin": _safe_div(ebitda, revenue),
        "current_ratio": _safe_div(current_assets, current_liabilities),
        "debt_to_equity": _safe_div(total_liabilities, total_equity),
        "asset_to_equity": _safe_div(total_assets, total_equity),
        "interest_coverage": _safe_div(operating_income, interest_expense),
        "roe": _safe_div(net_income, total_equity),
        "roa": _safe_div(net_income, total_assets),
        "asset_turnover": _safe_div(revenue, total_assets),
    }


def compute_valuation_metrics(data, last_traded_price):
    """{"eps":, "book_value_per_share":, "pe_ratio":, "pb_ratio":}, each
    None unless shares_outstanding was stated and a live price is
    available. Needs a market price, which never appears in a disclosure
    itself -- callers fetch it separately (e.g. scraper.pse_edge.
    get_stock_data) and pass it in.
    """
    net_income = _value(data.get("net_income"))
    total_equity = _value(data.get("total_equity"))
    shares_outstanding = _value(data.get("shares_outstanding"))

    eps = _safe_div(net_income, shares_outstanding)
    book_value_per_share = _safe_div(total_equity, shares_outstanding)

    return {
        "eps": eps,
        "book_value_per_share": book_value_per_share,
        "pe_ratio": _safe_div(last_traded_price, eps),
        "pb_ratio": _safe_div(last_traded_price, book_value_per_share),
    }
