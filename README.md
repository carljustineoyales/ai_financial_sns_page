# AI Financial SNS Page

Automates a Facebook Page covering the Philippine Stock Exchange (PSE): scrapes
disclosures and market data from PSE Edge, analyzes them with an LLM
(Gemini/Claude), renders graphics, and posts to Facebook.

## Modules

- **Financial report disclosures** ([main.py](main.py)) — scrapes the latest PSE
  Edge financial report disclosure, extracts and analyzes the filing with an
  LLM, generates a caption, and posts it to Facebook.
- **Market movers** ([scraper/market_movers.py](scraper/market_movers.py)) —
  computes end-of-day gainers/losers/most active. No standalone cron entry
  — `market_movers_poster.py` and `financial_report_cards.py` both call
  its `get_or_compute_movers()`, which computes and caches the live
  snapshot itself on a cache miss, so a dedicated "just compute and cache"
  job would be redundant. Still runnable standalone
  (`python -m scraper.market_movers`) for an ad hoc refresh.
- **Market movers poster** ([market_movers_poster.py](market_movers_poster.py)) —
  builds and posts a Top 10 Gainers, Top 10 Losers, and Top 10 Most Active
  graphic (one post each), market-wide. Shares a same-day cached movers
  snapshot with `financial_report_cards.py` via
  `scraper.market_movers.get_or_compute_movers()` — whichever of the two
  scripts runs first for the day computes it live and caches it to
  `output/market_movers/`; the other reads that cache, so both reference
  the exact same top-10 lists without needing a particular run order, and
  the live scrape only happens once per day regardless of which script
  triggers it. Captions are deterministic string templates, not
  LLM-generated — this is just formatted facts, no analysis involved.
- **Market calendar** ([scraper/market_calendar.py](scraper/market_calendar.py)) —
  refreshes dividends/SROs/meetings/listings for the current month.
- **Dividend graphics** ([dividend_graphics.py](dividend_graphics.py)) —
  builds dividend graphics scoped to the PSEi + REIT watchlist: `month`
  builds next month's dividend ex-date calendar card, `year` builds a full
  Jan-Dec dividend payout overview plus per-month detail cards. No
  dependency on `posters.facebook` — cards can be rendered and previewed
  without a Facebook post ever being possible.
- **Dividend posters** ([dividend_posters.py](dividend_posters.py)) — CLI
  (`month`/`year`) that calls into `dividend_graphics.py` to build the card,
  then previews/confirms and posts it to Facebook. The only module with a
  `posters.facebook` dependency for this pipeline.
- **Financial report cards** ([financial_report_cards.py](financial_report_cards.py)) —
  for every company in today's top 10 gainers/losers/most-active (same
  cached snapshot `market_movers_poster.py` uses, via
  `get_or_compute_movers()`), pulls that company's most recent financial report on
  file — regardless of how old it is — and extracts whatever figures the
  filing actually states (revenue, net income, balance sheet, cash flow,
  and — for the 8 PSE REITs only — distributable income, leverage ratio,
  NAV per share, occupancy rate; see the Obsidian vault's Dividend Stock
  Selection Criteria for why REITs get different fields). Computes a few
  simple ratios from those stated figures in Python (never via the LLM —
  margins, current ratio, D/E, ROE/ROA, asset turnover, and P/E/P/B using
  a live price fetch), renders a report-card graphic, and posts it — the
  caption always states the filing's actual announce date, since a top
  mover's most recent report may be from an earlier quarter, not today.
  Triggered mechanically by "they're a top mover today" — a factual,
  rules-based criterion (rank by price/volume), the same category as the
  filing-based trigger this replaced, never selected by whether the
  figures look good. Runs after market close, since gainers/losers/most-
  active are end-of-day rankings. Deliberately overlaps with `main.py`'s
  coverage (narrative vs. structured figures, different trigger) rather
  than replacing it.

Shared watchlist/date-range helpers live in [dividend_tracker.py](dividend_tracker.py).
The `preview_and_post` confirm/post/record flow shared by
[dividend_posters.py](dividend_posters.py),
[market_movers_poster.py](market_movers_poster.py), and
[financial_report_cards.py](financial_report_cards.py) lives in
[posters/preview_and_post.py](posters/preview_and_post.py).
Graphic cards (dividend calendars, year overview) are rendered to PNG via the
[rendering/](rendering/) package (Pillow, DejaVu Sans, deliberately simple
utility graphics rather than polished design) — `theme.py` holds the palette
and layout constants, `primitives.py` holds shared drawing helpers, and each
card type (table, calendar, dividend stamp, year overview, ticker grid) has
its own module. [assets_logos.py](assets_logos.py) downloads/caches company
logos used on those cards into `assets/logos/`.

## Pipeline

```mermaid
flowchart TD
    PSE[(PSE Edge /\nframes.pse.com.ph)]

    subgraph Disclosures["Financial report disclosures — main.py"]
        D1[Fetch latest disclosure + PDF]
        D2[Extract text]
        D3["Analyze with LLM\n(Gemini/Claude)"]
        D4[Generate caption]
        D1 --> D2 --> D3 --> D4
    end
    PSE --> D1

    subgraph MarketData["Market calendar data refresh"]
        M2["scraper/market_calendar.py\ndividends / SROs / meetings / listings"]
        OUT2[(output/market_calendar/*.json)]
        M2 --> OUT2
    end
    PSE --> M2

    SHARED[("scraper.market_movers.get_or_compute_movers()\ncache: output/market_movers/&lt;date&gt;.json\n(no standalone cron -- computed live by\nwhichever of MoversPoster/ReitCards runs first;\npython -m scraper.market_movers still works ad hoc)")]
    PSE --> SHARED

    subgraph MoversPoster["Market movers poster — market_movers_poster.py"]
        MP1["Get today's top-10\ngainers/losers/most-active"]
        MP2["Render 3 table cards\n+ deterministic caption (no LLM)"]
        MP1 --> MP2
    end
    SHARED --> MP1
    MP2 --> MPPNG[(3x Rendered PNG card)]
    MP2 --> MPCAP[3x Caption]

    subgraph ReitCards["Financial report cards — financial_report_cards.py"]
        RC0["Get today's top-10\ngainers/losers/most-active,\nunion + dedup symbols"]
        RC1["Per top mover: fetch their most\nrecent financial report on file,\nany age (get_company_financial_reports)"]
        RC2[Extract text]
        RC3["Extract stated figures with LLM\n(each as {stated, value};\nREIT-only fields when filer is a REIT)"]
        RC6["Compute ratios in Python, not LLM\n(margins, current ratio, D/E, ROE/ROA;\nP/E, P/B via live price fetch)"]
        RC4[Render report-card table image]
        RC5["Generate factual caption\n(states filing date; no buy/sell/consider language)"]
        RC0 --> RC1 --> RC2 --> RC3 --> RC6 --> RC4
        RC6 --> RC5
    end
    SHARED --> RC0
    RC4 --> RCPNG[(Rendered PNG card)]
    RC5 --> RCCAP[Caption]

    subgraph Graphics["Graphic generation — dividend_graphics.py"]
        WL["dividend_tracker.py\nwatchlist + date-range helpers"]
        G1[build_month_card]
        G2[build_year_card /\nbuild_month_detail_cards]
        R["rendering/ package\ntheme + primitives + card renderers"]
        LOGOS[(assets/logos/*.png\nvia assets_logos.py)]
        PNG[(Rendered PNG card)]
        WL --> G1 --> R
        WL --> G2 --> R
        LOGOS --> R
        R --> PNG
    end
    OUT2 --> WL

    subgraph Posting["Posting — dividend_posters.py / market_movers_poster.py / financial_report_cards.py"]
        P1[main_month / main_year /\n_process_category /\n_process_disclosure]
        P2["preview_and_post()\n(posters/preview_and_post.py)"]
        P1 --> P2
    end
    PNG --> P1
    MPPNG --> P1
    MPCAP --> P1
    RCPNG --> P1
    RCCAP --> P1

    FB[(Facebook Page)]
    D4 -- post_to_page --> FB
    P2 -- post_photo --> FB
```

## Setup

```bash
cd /home/cjoyales/personal/ai_financial_sns_page
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER_ORDER` | Comma-separated fallback order, e.g. `gemini,claude` |
| `ANTHROPIC_API_KEY` | Claude API key |
| `GEMINI_API_KEY` | Gemini API key |
| `FACEBOOK_PAGE_ID` | Target Facebook Page ID |
| `FACEBOOK_ACCESS_TOKEN` | Long-lived Page access token |
| `FACEBOOK_APP_ID` / `FACEBOOK_APP_SECRET` | Used only by `scripts/refresh_fb_token.py` |
| `POST_MODE` | `confirm` (preview + `y/N` prompt) or `auto` (post immediately) |

At least one LLM provider key is required for `main.py`. A Facebook Page ID
and access token are required for any script that posts.

## Running

```bash
python main.py                          # financial report disclosures
python -m scraper.market_movers          # market movers (compute + cache only)
python market_movers_poster.py           # market movers, top 10 gainers/losers/most-active (posts)
python -m scraper.market_calendar        # market calendar data refresh
python dividend_posters.py month         # market calendar graphic
python dividend_posters.py year          # year overview graphic
python financial_report_cards.py         # report cards for today's top movers (run after market close)
```

With `POST_MODE=confirm` (default), each script prints a preview and asks
before posting to Facebook. Set `POST_MODE=auto` to post unattended (required
under cron, since there's no terminal to answer the prompt).

Output (downloaded PDFs, extracted text, analysis, rendered images, "posted"
markers to avoid duplicate posts) is written under `output/`, split by
category.

## Facebook access token

Page access tokens expire. To refresh:

```bash
.venv/bin/python scripts/refresh_fb_token.py
```

Generate a short-lived User Access Token via Graph API Explorer first, then
paste it in when prompted; the script exchanges it for a long-lived Page
token and writes it into `.env`.

## Scheduling

[scripts/crontab](scripts/crontab) is a **draft** schedule (not installed
automatically). It runs each script at the appropriate time around PSE
trading hours (9:30am-3:30pm, Asia/Manila) with `POST_MODE=auto` and
`flock` to prevent overlapping runs. Review it, then install with:

```bash
crontab scripts/crontab
```

Check what's currently installed with `crontab -l`.
