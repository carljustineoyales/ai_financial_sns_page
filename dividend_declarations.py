"""Posts a card to the configured Facebook Page for any PSE-listed
company's dividend declaration whose ex-dividend date is coming up within
EX_DATE_WINDOW_DAYS -- rate, ex-dividend date, payment date, and (when a
comparable declaration from ~1 year prior is found) growth vs. that prior
declaration. Triggered mechanically, market-wide, never selected by
whether the rate looks good -- same full-market, objective-reporting rule
as every other poster in this project. Card/caption generation lives in
dividend_declaration_graphics.py; this module handles data-fetch
orchestration, prior-year matching, preview/confirm, and posting.

The market-wide feed (get_dividends_and_rights) has no "announced"
timestamp and returns every *currently active* declaration -- live-tested
at 543 entries spanning months into the future -- so the ex-date window is
what bounds this to a manageable, actionable-soon set rather than posting
hundreds of cards on first run. Idempotency is keyed by edge_no: once a
declaration enters the window and gets posted, it's marked and won't
repost on later runs even while its ex-date is still within the window.
"""

import logging
import os
import sys
from datetime import date, datetime

from dotenv import load_dotenv

import dividend_declaration_graphics as graphics
from logging_config import setup_logging
from posters.preview_and_post import preview_and_post
from scraper.market_movers import refresh_company_directory
from scraper.pse_edge import get_company_dividends, get_dividends_and_rights

OUTPUT_DIR = os.path.join("output", "dividend_declarations")
PRIOR_YEAR_TOLERANCE_DAYS = 60
EX_DATE_WINDOW_DAYS = 14

logger = logging.getLogger(__name__)


def _fail(stage, exc):
    logger.error("%s failed: %s", stage, exc)


def get_new_declarations(window_days=EX_DATE_WINDOW_DAYS):
    """Currently active market-wide dividend declarations
    (get_dividends_and_rights, unchanged) whose ex-dividend date falls
    within the next window_days -- paired with the resolved symbol, as
    (declaration, symbol) pairs. The market-wide feed returns *every*
    currently active declaration with no "announced" timestamp to filter
    by (unlike the financial-report disclosures feed) -- live-tested at
    543 entries spanning months into the future, so without this window
    the first run would post hundreds of cards at once. Bounding to
    "ex-date coming up soon" is a mechanical, market-wide filter (not
    curation by whether the rate looks good), consistent with this
    project's other triggers. Declarations already posted (posted.json
    under their edge_no) are filtered out by _process_declaration itself,
    not here.
    """
    companies = refresh_company_directory()
    symbol_by_cmpy_id = {c["cmpy_id"]: c["symbol"] for c in companies if c.get("cmpy_id")}

    declarations = get_dividends_and_rights()
    today = date.today()

    matches = []
    for declaration in declarations:
        symbol = symbol_by_cmpy_id.get(declaration["cmpy_id"])
        if not symbol:
            logger.info("%s: no matching symbol in company directory, skipping.", declaration["company"])
            continue

        try:
            ex_date = datetime.strptime(declaration["ex_dividend_date"], "%b %d, %Y").date()
        except (ValueError, TypeError):
            continue

        days_until = (ex_date - today).days
        if not (0 <= days_until <= window_days):
            continue

        matches.append((declaration, symbol))

    return matches


def _find_prior_year_entry(entries, target_edge_no, target_date):
    best, best_diff = None, None
    for e in entries:
        if e["edge_no"] == target_edge_no:
            continue
        try:
            e_date = datetime.strptime(e["ex_dividend_date"], "%b %d, %Y").date()
        except (ValueError, TypeError):
            continue

        days_back = (target_date - e_date).days
        diff = abs(days_back - 365)
        if diff <= PRIOR_YEAR_TOLERANCE_DAYS and (best_diff is None or diff < best_diff):
            best, best_diff = e, diff

    return best


def _process_declaration(declaration, symbol):
    edge_no = declaration["edge_no"]
    if not edge_no:
        logger.info("%s: declaration has no edge_no, skipping.", symbol)
        return

    item_dir = os.path.join(OUTPUT_DIR, date.today().isoformat(), edge_no)
    os.makedirs(item_dir, exist_ok=True)

    posted_marker = os.path.join(item_dir, "posted.json")
    if os.path.exists(posted_marker):
        logger.info("%s: already posted, skipping.", symbol)
        return

    logger.info("%s: %s dividend, ex-date %s", symbol, declaration["dividend_type"], declaration["ex_dividend_date"])

    try:
        history = get_company_dividends(declaration["cmpy_id"])
    except Exception as e:
        _fail(f"{symbol}: fetching dividend history", e)
        return

    entry = next((e for e in history if e["edge_no"] == edge_no), None)
    if not entry:
        logger.info("%s: declaration not found in its own history list (edge_no mismatch), skipping.", symbol)
        return

    try:
        target_date = datetime.strptime(entry["ex_dividend_date"], "%b %d, %Y").date()
        prior_entry = _find_prior_year_entry(history, edge_no, target_date)
    except (ValueError, TypeError):
        prior_entry = None

    image_path = os.path.join(item_dir, "card.png")
    graphics.build_declaration_card(symbol, entry, prior_entry, image_path)
    logger.info("%s: saved card to %s", symbol, image_path)

    caption = graphics.build_declaration_caption(symbol, entry, prior_entry)
    preview_and_post(image_path, caption, posted_marker)


def main():
    setup_logging()
    load_dotenv()

    logger.info("Fetching current dividend declarations from PSE Edge...")
    try:
        matches = get_new_declarations()
    except Exception as e:
        _fail("fetching declarations", e)
        sys.exit(1)

    if not matches:
        logger.info("No dividend declarations found.")
        return

    for declaration, symbol in matches:
        _process_declaration(declaration, symbol)


if __name__ == "__main__":
    main()
