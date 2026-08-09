"""Shared watchlist and date-range utilities used by the poster script
(dividend_posters.py): the PSEi + REIT watchlist (see Finance/Dividend Stock
Selection Criteria in the Obsidian vault and this session's design
discussion for why), a cmpy_id-to-symbol lookup, PSE date parsing, and
month/week range helpers.
"""

import calendar
import json
import os
from datetime import date, datetime, timedelta

from scraper.market_movers import COMPANY_DIRECTORY_CACHE, refresh_company_directory
from scraper.pse_edge import get_psei_constituents

# The 8 REITs listed on PSE Edge as of Aug 2026. Hardcoded rather than
# name-matched against the company directory; update manually if a new
# REIT lists (or one delists).
PSE_REIT_SYMBOLS = {
    "AREIT",
    "CREIT",
    "DDMPR",
    "FILRT",
    "MREIT",
    "PREIT",
    "RCR",
    "VREIT",
}


def get_watchlist_symbols():
    """PSEi constituents union the hardcoded PSE REIT list, the readable
    watchlist used for this project's public dividend-related graphics.
    """
    psei = set(get_psei_constituents())

    return psei | PSE_REIT_SYMBOLS


def _symbol_lookup():
    if os.path.exists(COMPANY_DIRECTORY_CACHE):
        with open(COMPANY_DIRECTORY_CACHE) as f:
            companies = json.load(f)
    else:
        companies = refresh_company_directory()

    return {c["cmpy_id"]: c["symbol"] for c in companies}


def _parse_pse_date(date_str):
    try:
        return datetime.strptime(date_str, "%b %d, %Y").date()
    except (ValueError, TypeError):
        return None


def get_period_range(period, today=None):
    today = today or date.today()

    if period == "week":
        return today, today + timedelta(days=6)

    year, month = today.year, today.month
    if month == 12:
        year, month = year + 1, 1
    else:
        month += 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)
