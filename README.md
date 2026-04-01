# YouTube AI Trend Analysis

An automated pipeline that scrapes YouTube for trending AI and automation content, analyzes performance metrics, generates a professional slide deck with charts, and emails it daily to your inbox.

## What It Does

Every day at 6am PT, this system:

1. Searches YouTube for trending AI/automation videos across 8 targeted keywords
2. Collects performance data for 300–400 videos (views, likes, comments, subscriber counts)
3. Analyzes what's working — engagement rates, trending topics, top channels
4. Generates a 9-slide PowerPoint deck with charts and visuals
5. Emails the deck + a full HTML briefing to all recipients

The goal is to give you a daily pulse on what content is performing in the AI niche so you can create videos that people actually want to watch.

---

## Architecture

This project follows the **WAT framework** (Workflows, Agents, Tools):

```
Workflow (SOP)
    └── Agent (Claude) orchestrates
            └── Tools (Python scripts) execute

fetch_youtube_trends.py
    → .tmp/raw_data.csv
        → analyze_trends.py
            → .tmp/analyzed.csv
            → .tmp/insights.json
                → generate_charts.py
                    → .tmp/charts/*.png
                        → create_deck.py
                            → .tmp/ai_trend_report_YYYYMMDD.pptx
                                → send_email.py
                                    → Gmail (to all recipients)
```

---

## Tools

### `tools/fetch_youtube_trends.py`
Hits the YouTube Data API v3 to search for AI/automation videos published in the last 90 days.

- **8 search keywords:** AI automation, AI agents, artificial intelligence tools, LLM workflow automation, ChatGPT automation, AI productivity tools, machine learning tutorial, no code AI automation
- Fetches up to 50 results per keyword, deduplicates across searches
- Batch-fetches video details (views, likes, comments, thumbnails) and channel subscriber counts
- **Quota cost:** ~824 units per run (free tier is 10,000/day)
- **Output:** `.tmp/raw_data.csv`

### `tools/analyze_trends.py`
Transforms raw data into ranked insights.

- Computes `engagement_rate` = (likes + comments) / views × 100
- Computes `views_per_day` = views / days since published
- Ranks videos by views, engagement, and growth velocity
- Extracts most frequent keywords from top video titles
- Builds channel leaderboard and upload activity timeline
- Generates data-driven content recommendations
- **Output:** `.tmp/analyzed.csv` + `.tmp/insights.json`

### `tools/generate_charts.py`
Creates 5 dark-themed chart images using matplotlib.

| Chart | Description |
|-------|-------------|
| `top_videos_views.png` | Top 10 videos by view count |
| `top_videos_engagement.png` | Top 10 videos by engagement rate |
| `trending_keywords.png` | Most frequent words in high-performing titles |
| `channel_leaderboard.png` | Top channels by total views |
| `upload_trend.png` | Upload frequency over last 90 days |

**Output:** `.tmp/charts/`

### `tools/create_deck.py`
Builds a 9-slide PowerPoint deck using python-pptx with a dark professional theme.

| Slide | Content |
|-------|---------|
| 1 | Title — report date, niche, total videos |
| 2 | Executive Summary — stat cards + top video highlight |
| 3 | Top Videos by Views — chart + table |
| 4 | Top Videos by Engagement — chart + table |
| 5 | Trending Keywords — frequency chart |
| 6 | Channel Leaderboard — bar chart + table |
| 7 | Upload Activity — line chart over 90 days |
| 8 | Content Recommendations — data-driven insights |
| 9 | Methodology — keywords, date range, data source |

**Output:** `.tmp/ai_trend_report_YYYYMMDD.pptx`

### `tools/send_email.py`
Sends the report via Gmail SMTP over SSL (port 465).

- Sends a rich **HTML email** with video thumbnails, clickable links, stat cards, keyword badges, and channel table
- Attaches the `.pptx` slide deck
- Supports multiple recipients (comma-separated in `.env`)
- Email addresses are never logged to stdout

---

## Schedule

The pipeline runs automatically every day at **6am PT** via a Claude Code remote agent that clones this repo and executes each tool in sequence.

Manage the schedule at: https://claude.ai/code/scheduled

---

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/chetansehgal9/youtubeAnalysis.git
cd youtubeAnalysis
```

### 2. Install dependencies
```bash
pip3 install google-api-python-client python-dotenv pandas matplotlib seaborn python-pptx certifi
```

### 3. Configure credentials
Copy `.env` and fill in your values:
```
YOUTUBE_API_KEY=       # YouTube Data API v3 key
GMAIL_ADDRESS=         # Gmail address to send from
GMAIL_APP_PASSWORD=    # 16-char Gmail App Password (not your login password)
RECIPIENT_EMAIL=       # Comma-separated recipient list
```

**Getting a YouTube API key:**
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project → Enable "YouTube Data API v3"
3. Credentials → Create API Key

**Getting a Gmail App Password:**
1. Google Account → Security → Enable 2-Step Verification
2. App passwords → Generate → Copy 16-char password

### 4. Run the pipeline
```bash
python3 tools/fetch_youtube_trends.py
python3 tools/analyze_trends.py
python3 tools/generate_charts.py
python3 tools/create_deck.py
python3 tools/send_email.py
```

---

## File Structure

```
.
├── tools/
│   ├── fetch_youtube_trends.py   # YouTube API data collection
│   ├── analyze_trends.py         # Metrics computation and insights
│   ├── generate_charts.py        # Chart image generation
│   ├── create_deck.py            # PowerPoint deck builder
│   └── send_email.py             # HTML email + attachment delivery
├── workflows/
│   └── youtube_trend_report.md   # Full SOP with troubleshooting guide
├── .tmp/                         # Generated files (gitignored)
│   ├── raw_data.csv
│   ├── analyzed.csv
│   ├── insights.json
│   ├── charts/
│   └── ai_trend_report_*.pptx
├── .env                          # Credentials (gitignored, never committed)
├── CLAUDE.md                     # Agent operating instructions (WAT framework)
└── README.md                     # This file
```

---

## Security

- `.env` is gitignored — credentials are never committed to the repo
- SMTP uses `SMTP_SSL` on port 465 with certificate verification via certifi
- No API keys or secrets appear anywhere in the codebase
- Email addresses are not logged to stdout
- All YouTube API calls are server-side only

---

## Customization

**Change search keywords** — edit `SEARCH_KEYWORDS` in `tools/fetch_youtube_trends.py`

**Change the time window** — edit `DAYS_BACK` in `tools/fetch_youtube_trends.py` (default: 90 days)

**Add or remove recipients** — update `RECIPIENT_EMAIL` in `.env` (comma-separated)

**Change the schedule** — update the cron expression at https://claude.ai/code/scheduled
