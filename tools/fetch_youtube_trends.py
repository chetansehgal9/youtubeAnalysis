"""
fetch_youtube_trends.py
-----------------------
Searches YouTube Data API v3 for trending AI/automation videos.

Quota cost per run:
  - 8 keyword searches × 100 units = 800 units
  - ~16 videos.list batch calls × 1 unit = ~16 units
  - ~8 channels.list batch calls × 1 unit = ~8 units
  Total: ~824 units (well within 10,000/day free tier)

Output: .tmp/raw_data.csv
"""

import os
import csv
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
if not YOUTUBE_API_KEY:
    print("ERROR: YOUTUBE_API_KEY not set in .env")
    sys.exit(1)

SEARCH_KEYWORDS = [
    "AI automation 2025",
    "AI agents tutorial",
    "artificial intelligence tools",
    "LLM workflow automation",
    "ChatGPT automation",
    "AI productivity tools",
    "machine learning tutorial",
    "no code AI automation",
]

MAX_RESULTS_PER_SEARCH = 50  # YouTube API max per call
DAYS_BACK = 90
OUTPUT_DIR = ".tmp"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "raw_data.csv")

CSV_COLUMNS = [
    "video_id",
    "title",
    "channel_id",
    "channel_title",
    "published_at",
    "days_since_published",
    "view_count",
    "like_count",
    "comment_count",
    "thumbnail_url",
    "subscriber_count",
    "search_keyword",
]


def get_youtube_client():
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def search_videos(youtube, keyword: str, published_after: str) -> list[str]:
    """Returns list of video IDs matching keyword, published after given date."""
    try:
        response = youtube.search().list(
            q=keyword,
            part="id",
            type="video",
            maxResults=MAX_RESULTS_PER_SEARCH,
            publishedAfter=published_after,
            relevanceLanguage="en",
            order="relevance",
        ).execute()
    except HttpError as e:
        print(f"  WARNING: Search failed for '{keyword}': {e}")
        return []

    return [item["id"]["videoId"] for item in response.get("items", [])]


def fetch_video_details(youtube, video_ids: list[str]) -> dict:
    """Batch fetch video stats. Returns dict keyed by video_id."""
    details = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        try:
            response = youtube.videos().list(
                part="snippet,statistics",
                id=",".join(batch),
            ).execute()
        except HttpError as e:
            print(f"  WARNING: videos.list failed: {e}")
            continue

        for item in response.get("items", []):
            vid_id = item["id"]
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            details[vid_id] = {
                "title": snippet.get("title", ""),
                "channel_id": snippet.get("channelId", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt", ""),
                "thumbnail_url": (
                    snippet.get("thumbnails", {})
                    .get("high", {})
                    .get("url", "")
                ),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
            }
    return details


def fetch_channel_subscribers(youtube, channel_ids: list[str]) -> dict:
    """Batch fetch subscriber counts. Returns dict keyed by channel_id."""
    subscribers = {}
    unique_ids = list(set(channel_ids))
    for i in range(0, len(unique_ids), 50):
        batch = unique_ids[i : i + 50]
        try:
            response = youtube.channels().list(
                part="statistics",
                id=",".join(batch),
            ).execute()
        except HttpError as e:
            print(f"  WARNING: channels.list failed: {e}")
            continue

        for item in response.get("items", []):
            ch_id = item["id"]
            subs = item.get("statistics", {}).get("subscriberCount", 0)
            subscribers[ch_id] = int(subs) if subs else 0
    return subscribers


def compute_days_since(published_at: str) -> float:
    """Calculate days between publish date and now."""
    if not published_at:
        return 0.0
    try:
        pub = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return max((now - pub).total_seconds() / 86400, 0.1)
    except ValueError:
        return 0.0


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    youtube = get_youtube_client()

    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
    published_after = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    all_videos: dict[str, dict] = {}  # video_id → row data
    keyword_map: dict[str, str] = {}  # video_id → first keyword that found it

    print(f"Searching YouTube for {len(SEARCH_KEYWORDS)} keywords (last {DAYS_BACK} days)...")
    for keyword in SEARCH_KEYWORDS:
        print(f"  Searching: '{keyword}'")
        video_ids = search_videos(youtube, keyword, published_after)
        print(f"    Found {len(video_ids)} video IDs")
        for vid_id in video_ids:
            if vid_id not in keyword_map:
                keyword_map[vid_id] = keyword

    all_video_ids = list(keyword_map.keys())
    print(f"\nTotal unique videos found: {len(all_video_ids)}")

    print("Fetching video details...")
    video_details = fetch_video_details(youtube, all_video_ids)
    print(f"  Got details for {len(video_details)} videos")

    channel_ids = [v["channel_id"] for v in video_details.values() if v.get("channel_id")]
    print("Fetching channel subscriber counts...")
    channel_subs = fetch_channel_subscribers(youtube, channel_ids)
    print(f"  Got subscriber data for {len(channel_subs)} channels")

    rows = []
    for vid_id, details in video_details.items():
        days_since = compute_days_since(details["published_at"])
        rows.append({
            "video_id": vid_id,
            "title": details["title"],
            "channel_id": details["channel_id"],
            "channel_title": details["channel_title"],
            "published_at": details["published_at"],
            "days_since_published": round(days_since, 1),
            "view_count": details["view_count"],
            "like_count": details["like_count"],
            "comment_count": details["comment_count"],
            "thumbnail_url": details["thumbnail_url"],
            "subscriber_count": channel_subs.get(details["channel_id"], 0),
            "search_keyword": keyword_map.get(vid_id, ""),
        })

    # Sort by view count descending
    rows.sort(key=lambda r: r["view_count"], reverse=True)

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone. {len(rows)} videos saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
