"""Fetches PSE's Market Calendar (dividends, SROs, warrants, meetings,
listings) for a given month and saves it to output/market_calendar/.
"""

import json
import logging
import os
import sys
from datetime import date

from logging_config import setup_logging
from scraper.pse_edge import get_market_calendar

OUTPUT_DIR = os.path.join("output", "market_calendar")

logger = logging.getLogger(__name__)


def main():
    setup_logging()

    today = date.today()
    year = int(sys.argv[1]) if len(sys.argv) > 1 else today.year
    month = int(sys.argv[2]) if len(sys.argv) > 2 else today.month

    logger.info("Fetching PSE Market Calendar for %s-%02d...", year, month)
    events = get_market_calendar(year, month)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"{year}-{month:02d}.json")
    with open(output_path, "w") as f:
        json.dump(events, f, indent=2)

    logger.info("Saved %d events to %s", len(events), output_path)
    by_type = {}
    for e in events:
        by_type[e["event_type"]] = by_type.get(e["event_type"], 0) + 1
    for event_type, count in sorted(by_type.items()):
        logger.info("  %s: %d", event_type, count)


if __name__ == "__main__":
    main()
