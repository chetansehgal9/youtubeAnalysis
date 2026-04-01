# Workflow: YouTube AI Niche Trend Report

## Objective
Search YouTube for trending AI/automation videos, analyze performance metrics, generate a professional slide deck with charts, and email it to the recipient.

## Required Inputs
- YouTube Data API v3 key (in `.env` as `YOUTUBE_API_KEY`)
- Gmail address and App Password (in `.env` as `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`)
- Recipient email (in `.env` as `RECIPIENT_EMAIL`)

## First-time Setup

### 1. YouTube API Key
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or select an existing one)
3. Navigate to **APIs & Services → Library**
4. Search for "YouTube Data API v3" → Enable it
5. Go to **APIs & Services → Credentials → Create Credentials → API Key**
6. Copy the key into `.env` as `YOUTUBE_API_KEY=...`

### 2. Gmail App Password
1. Go to your Google Account → **Security**
2. Enable **2-Step Verification** (required for App Passwords)
3. Search for "App passwords" in Google Account settings
4. Generate a new App Password for "Mail"
5. Copy the 16-character password into `.env` as `GMAIL_APP_PASSWORD=...`
   - ⚠️ This is NOT your Gmail login password

### 3. Install Python Dependencies
```bash
pip install google-api-python-client python-dotenv pandas matplotlib seaborn python-pptx
```

## Execution

Run tools in this exact order from the project root:

```bash
# Step 1: Fetch YouTube data (~1-2 min, makes API calls)
python tools/fetch_youtube_trends.py

# Step 2: Analyze and compute metrics (<10 sec)
python tools/analyze_trends.py

# Step 3: Generate chart images (<15 sec)
python tools/generate_charts.py

# Step 4: Build the slide deck (<15 sec)
python tools/create_deck.py

# Step 5: Email the deck (<10 sec)
python tools/send_email.py
```

## Expected Outputs

| Step | Output file(s) |
|------|---------------|
| fetch | `.tmp/raw_data.csv` — raw video data (title, views, likes, comments, channel, etc.) |
| analyze | `.tmp/analyzed.csv` — enriched with engagement_rate, views_per_day, ranks |
| analyze | `.tmp/insights.json` — summary stats and top lists used by subsequent tools |
| generate_charts | `.tmp/charts/top_videos_views.png` |
| | `.tmp/charts/top_videos_engagement.png` |
| | `.tmp/charts/trending_keywords.png` |
| | `.tmp/charts/channel_leaderboard.png` |
| | `.tmp/charts/upload_trend.png` |
| create_deck | `.tmp/ai_trend_report_YYYYMMDD.pptx` |
| send_email | Email delivered to `RECIPIENT_EMAIL` |

## Slide Deck Contents

1. **Title** — Report title, date, niche, total videos analyzed
2. **Executive Summary** — 4 stat cards + top video highlight + recency breakdown
3. **Top Videos by Views** — Chart + table of top 10
4. **Top Videos by Engagement** — Chart + table (engagement = (likes+comments)/views)
5. **Trending Keywords** — Most frequent words in high-performing titles
6. **Channel Leaderboard** — Top channels by total views in analyzed set
7. **Upload Activity** — Videos published per week over last 90 days
8. **Content Recommendations** — Data-driven insights from the dataset
9. **Methodology** — Search keywords, date range, data source

## API Quota

**Free tier: 10,000 units/day** (resets at midnight Pacific time)

Per run:
- 8 keyword searches × 100 units = 800 units
- ~16 videos.list calls × 1 unit = ~16 units
- ~8 channels.list calls × 1 unit = ~8 units
- **Total per run: ~824 units** (~8% of daily quota)

Safe to run multiple times per day if needed.

## Troubleshooting

### `quotaExceeded` error during fetch
- You've hit the 10,000 unit/day limit
- Wait until midnight Pacific time for quota to reset
- Reduce `SEARCH_KEYWORDS` list in `fetch_youtube_trends.py` to use fewer searches

### `raw_data.csv is empty`
- Check that `YOUTUBE_API_KEY` is set correctly in `.env`
- Verify the key has YouTube Data API v3 enabled in Google Cloud Console
- Check quota is not exhausted

### `SMTPAuthenticationError` during email send
- `GMAIL_APP_PASSWORD` is wrong or expired — regenerate it
- Make sure 2-Step Verification is still enabled on the Gmail account
- Use an App Password, not your regular Gmail password

### Charts missing from deck
- Run `generate_charts.py` before `create_deck.py`
- Check `.tmp/charts/` directory exists and contains PNG files

### Deck opens blank / corrupted
- Re-run `create_deck.py` — `python-pptx` writes atomically
- Ensure `python-pptx` is installed: `pip install python-pptx`

## Customization

**Change search keywords** — edit `SEARCH_KEYWORDS` in `tools/fetch_youtube_trends.py`

**Change time window** — edit `DAYS_BACK` in `tools/fetch_youtube_trends.py` (default: 90 days)

**Add more videos per search** — `MAX_RESULTS_PER_SEARCH` is capped at 50 by the YouTube API

**Change recipient** — update `RECIPIENT_EMAIL` in `.env`

## Improvement Log

_Update this section when you discover issues, rate limits, or better approaches._

- Initial version: 8 keywords, 90-day window, 5 charts, 9 slides, Gmail SMTP.
