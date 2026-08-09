# AI Financial SNS Page

Automates a Facebook Page covering the Philippine Stock Exchange (PSE): scrapes
disclosures and market data from PSE Edge, analyzes them with an LLM
(Gemini/Claude), renders graphics, and posts to Facebook.

## Modules

- **Financial report disclosures** ([main.py](main.py)) — scrapes the latest PSE
  Edge financial report disclosure, extracts and analyzes the filing with an
  LLM, generates a caption, and posts it to Facebook.
- **Market movers** ([scraper/market_movers.py](scraper/market_movers.py)) —
  computes end-of-day gainers/losers/most active and caches them to `output/`.
- **Market calendar** ([scraper/market_calendar.py](scraper/market_calendar.py)) —
  refreshes dividends/SROs/meetings/listings for the current month.
- **Dividend graphics** ([dividend_graphics.py](dividend_graphics.py) +
  [dividend_posters.py](dividend_posters.py)) — builds and posts dividend
  graphics scoped to the PSEi + REIT watchlist: `month` posts next month's
  dividend ex-date calendar, `year` posts a full Jan-Dec dividend payout
  overview plus per-month detail cards. Graphic generation
  (`dividend_graphics.py`) is separate from posting
  (`dividend_posters.py`, which has the only `posters.facebook` dependency)
  so the cards can be rendered and previewed without a Facebook post ever
  being possible.

Shared watchlist/date-range helpers live in [dividend_tracker.py](dividend_tracker.py).
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

    subgraph MarketData["Market data refresh"]
        M1["scraper/market_movers.py\ngainers / losers / most active"]
        M2["scraper/market_calendar.py\ndividends / SROs / meetings / listings"]
        OUT1[(output/*.json)]
        OUT2[(output/market_calendar/*.json)]
        M1 --> OUT1
        M2 --> OUT2
    end
    PSE --> M1
    PSE --> M2

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

    subgraph Posting["Posting — dividend_posters.py"]
        P1[main_month / main_year]
        P2[preview + confirm prompt]
        P1 --> P2
    end
    PNG --> P1

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
python -m scraper.market_movers          # market movers
python -m scraper.market_calendar        # market calendar data refresh
python dividend_posters.py month         # market calendar graphic
python dividend_posters.py year          # year overview graphic
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
