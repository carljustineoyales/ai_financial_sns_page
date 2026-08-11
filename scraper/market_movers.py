"""Tracks PSE's company directory for listing/delisting changes, and computes
daily top gainers, top losers, and most active stocks across all PSE-listed
companies.

Which symbols are top gainers/losers/most-active comes from PSE's own
pre-computed tables on frames.pse.com.ph's homepage (one request, first-party,
no third-party licensing risk) via get_movers_snapshot(). Those tables only
give symbol/price/change, so the ~30 symbols across all three lists are then
enriched individually via PSE Edge's Stock Data page (companyPage/stockData.do)
to get high/low/market_cap/company name -- far fewer requests than scanning
every listed company.
"""

import json
import logging
import os
import time
from datetime import date

from logging_config import setup_logging
from scraper.pse_edge import new_session, get_company_directory, get_stock_data, get_movers_snapshot

DATA_DIR = "data"
COMPANY_DIRECTORY_CACHE = os.path.join(DATA_DIR, "pse_companies.json")
OUTPUT_DIR = os.path.join("output", "market_movers")

REQUEST_DELAY_SECONDS = 0.5

logger = logging.getLogger(__name__)


def refresh_company_directory(cache_path=COMPANY_DIRECTORY_CACHE):
    new_companies = get_company_directory()
    new_symbols = {c["symbol"] for c in new_companies}

    if os.path.exists(cache_path):
        with open(cache_path) as f:
            old_companies = json.load(f)
        old_symbols = {c["symbol"] for c in old_companies}

        added = new_symbols - old_symbols
        removed = old_symbols - new_symbols
        if added:
            logger.info("New listings detected: %s", sorted(added))
        if removed:
            logger.info("Delistings/removals detected: %s", sorted(removed))
        if not added and not removed:
            logger.info("Company directory unchanged since last check.")
    else:
        logger.info("No previous company directory cache -- saving initial snapshot (%d companies).", len(new_companies))

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(new_companies, f, indent=2)

    return new_companies


def compute_market_movers(companies, top_n=5, delay_seconds=REQUEST_DELAY_SECONDS):
    session = new_session()
    session.get("https://edge.pse.com.ph/companyDirectory/form.do")

    snapshot = get_movers_snapshot(session=session)
    cmpy_id_by_symbol = {c["symbol"]: c.get("cmpy_id") for c in companies}
    company_name_by_symbol = {c["symbol"]: c["company"] for c in companies}

    all_symbols = {
        entry["symbol"]
        for entries in snapshot.values()
        for entry in entries
    }

    enriched = {}
    skipped = []
    symbols = sorted(all_symbols)
    for i, symbol in enumerate(symbols):
        cmpy_id = cmpy_id_by_symbol.get(symbol)
        if not cmpy_id:
            skipped.append(symbol)
            continue

        try:
            data = get_stock_data(cmpy_id, session=session)
        except Exception as e:
            data = None
            skipped.append(f"{symbol} ({e})")

        if data:
            data["symbol"] = symbol
            data["company"] = company_name_by_symbol.get(symbol, symbol)
            enriched[symbol] = data
        else:
            skipped.append(symbol)

        if i < len(symbols) - 1:
            time.sleep(delay_seconds)

    if skipped:
        logger.info("Skipped %d symbols with no trading data today: %s", len(skipped), skipped)

    def _build_list(key):
        entries = []
        for entry in snapshot[key][:top_n]:
            data = enriched.get(entry["symbol"])
            if data:
                entries.append(data)
        return entries

    return {
        "gainers": _build_list("gainers"),
        "losers": _build_list("losers"),
        "most_active": _build_list("most_active"),
    }


def _cache_path(cache_date):
    return os.path.join(OUTPUT_DIR, f"{cache_date.isoformat()}.json")


def get_or_compute_movers(companies, top_n=10, cache_date=None):
    """Reads today's cached movers snapshot if one of the day's scripts
    already computed it (market_movers_poster.py, financial_report_cards.py,
    or this module's own main()); otherwise computes it live and writes the
    cache, so whichever of those scripts runs first "primes" it for the
    others. Keeps all same-day posts referencing the exact same top-10
    lists without requiring any particular run order between them.
    """
    cache_date = cache_date or date.today()
    path = _cache_path(cache_date)

    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)

    movers = compute_market_movers(companies, top_n=top_n)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(path, "w") as f:
        json.dump(movers, f, indent=2)

    return movers


def main():
    setup_logging()

    logger.info("Refreshing company directory...")
    companies = refresh_company_directory()

    logger.info("Computing market movers from PSE's own top-10 snapshot...")
    movers = compute_market_movers(companies, top_n=10)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = _cache_path(date.today())
    with open(output_path, "w") as f:
        json.dump(movers, f, indent=2)

    logger.info("Saved to %s", output_path)
    logger.info("Top gainers:")
    for r in movers["gainers"]:
        logger.info("  %s: %+.2f%% (₱%s)", r["symbol"], r["percent_change"], r["price"])
    logger.info("Top losers:")
    for r in movers["losers"]:
        logger.info("  %s: %+.2f%% (₱%s)", r["symbol"], r["percent_change"], r["price"])
    logger.info("Most active:")
    for r in movers["most_active"]:
        logger.info("  %s: %s shares", r["symbol"], f"{r['volume']:,}")


if __name__ == "__main__":
    main()
