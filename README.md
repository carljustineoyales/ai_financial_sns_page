# AI Financial SNS Page

Automates a Facebook Page covering the Philippine Stock Exchange (PSE): scrapes
disclosures and market data from PSE Edge, analyzes them with an LLM
(Gemini/Claude), renders graphics, and posts to Facebook.

## Modules

- **Financial report disclosures** ([main.py](main.py)) — scrapes the latest PSE
  Edge financial report disclosure, extracts and analyzes the filing with an
  LLM, generates a caption, and posts it to Facebook.
- **Market movers** ([scraper/market_movers.py](scraper/market_movers.py)) —
  posts end-of-day gainers/losers/most active.
- **Market calendar** ([scraper/market_calendar.py](scraper/market_calendar.py)) —
  refreshes dividends/SROs/meetings/listings for the current month.
- **Market calendar graphic** ([market_calendar_poster.py](market_calendar_poster.py)) —
  posts a graphic of next month's dividend ex-dates, scoped to the PSEi + REIT
  watchlist.
- **Year overview graphic** ([year_overview_poster.py](year_overview_poster.py)) —
  posts a full Jan-Dec dividend payout calendar graphic, scoped to the PSEi +
  REIT watchlist.

Shared watchlist/date-range helpers live in [dividend_tracker.py](dividend_tracker.py).

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
python market_calendar_poster.py         # market calendar graphic
python year_overview_poster.py           # year overview graphic
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
