"""
analyze_trends.py
-----------------
Transforms raw YouTube data into ranked insights and summary statistics.

Input:  .tmp/raw_data.csv  (produced by fetch_youtube_trends.py)
Output: .tmp/analyzed.csv  (enriched with engagement metrics)
        .tmp/insights.json (summary stats used by create_deck.py)
"""

import json
import os
import re
import sys
from collections import Counter
from datetime import datetime

import pandas as pd

INPUT_FILE = ".tmp/raw_data.csv"
OUTPUT_CSV = ".tmp/analyzed.csv"
OUTPUT_JSON = ".tmp/insights.json"

# Words to exclude from keyword frequency analysis
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "be", "as", "it",
    "this", "that", "you", "your", "i", "my", "we", "our", "how", "what",
    "why", "when", "do", "get", "use", "using", "make", "making", "best",
    "new", "top", "most", "more", "vs", "vs.", "&", "|", "-", "2024", "2025",
    "2026", "full", "free", "easy", "simple", "complete", "guide",
}


def load_data() -> pd.DataFrame:
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: {INPUT_FILE} not found. Run fetch_youtube_trends.py first.")
        sys.exit(1)
    df = pd.read_csv(INPUT_FILE)
    if df.empty:
        print("ERROR: raw_data.csv is empty.")
        sys.exit(1)
    return df


def compute_engagement_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["days_since_published"] = pd.to_numeric(df["days_since_published"], errors="coerce").fillna(1)
    df["view_count"] = pd.to_numeric(df["view_count"], errors="coerce").fillna(0).astype(int)
    df["like_count"] = pd.to_numeric(df["like_count"], errors="coerce").fillna(0).astype(int)
    df["comment_count"] = pd.to_numeric(df["comment_count"], errors="coerce").fillna(0).astype(int)
    df["subscriber_count"] = pd.to_numeric(df["subscriber_count"], errors="coerce").fillna(0).astype(int)

    # Engagement rate: (likes + comments) / views * 100
    df["engagement_rate"] = df.apply(
        lambda r: round((r["like_count"] + r["comment_count"]) / r["view_count"] * 100, 2)
        if r["view_count"] > 0 else 0.0,
        axis=1,
    )

    # Views per day since published
    df["views_per_day"] = (df["view_count"] / df["days_since_published"]).round(0).astype(int)

    return df


def segment_by_recency(df: pd.DataFrame) -> dict:
    """Return counts of videos per recency window."""
    return {
        "last_7_days": int((df["days_since_published"] <= 7).sum()),
        "last_30_days": int((df["days_since_published"] <= 30).sum()),
        "last_90_days": int((df["days_since_published"] <= 90).sum()),
    }


def extract_keywords(titles: pd.Series, top_n: int = 20) -> list[dict]:
    """Extract most frequent meaningful words from video titles."""
    all_words = []
    for title in titles:
        words = re.findall(r"\b[a-zA-Z]{3,}\b", str(title).lower())
        all_words.extend([w for w in words if w not in STOP_WORDS])
    counter = Counter(all_words)
    return [{"word": word, "count": count} for word, count in counter.most_common(top_n)]


def channel_leaderboard(df: pd.DataFrame, top_n: int = 10) -> list[dict]:
    """Aggregate views and video count per channel."""
    agg = (
        df.groupby("channel_title")
        .agg(
            total_views=("view_count", "sum"),
            video_count=("video_id", "count"),
            avg_engagement=("engagement_rate", "mean"),
            subscriber_count=("subscriber_count", "first"),
        )
        .reset_index()
        .sort_values("total_views", ascending=False)
        .head(top_n)
    )
    agg["avg_engagement"] = agg["avg_engagement"].round(2)
    return agg.to_dict(orient="records")


def upload_trend(df: pd.DataFrame) -> list[dict]:
    """Count uploads per week bucket over last 90 days."""
    df2 = df[df["days_since_published"] <= 90].copy()
    df2["week_bucket"] = (df2["days_since_published"] // 7).astype(int)
    counts = (
        df2.groupby("week_bucket")
        .size()
        .reset_index(name="upload_count")
        .sort_values("week_bucket")
    )
    # Label weeks as "X weeks ago"
    result = []
    for _, row in counts.iterrows():
        bucket = int(row["week_bucket"])
        label = "This week" if bucket == 0 else f"{bucket}w ago"
        result.append({"label": label, "upload_count": int(row["upload_count"])})
    return result


def content_recommendations(df: pd.DataFrame, keywords: list[dict]) -> list[str]:
    """Derive data-driven content recommendations."""
    recs = []

    # Check if tutorial videos outperform
    tutorial_mask = df["title"].str.lower().str.contains("tutorial|how to|guide|step", na=False)
    if tutorial_mask.sum() >= 5:
        tutorial_avg = df[tutorial_mask]["engagement_rate"].mean()
        non_tutorial_avg = df[~tutorial_mask]["engagement_rate"].mean()
        if tutorial_avg > non_tutorial_avg * 1.1:
            recs.append(
                f"Tutorial/how-to videos get {tutorial_avg / max(non_tutorial_avg, 0.01):.1f}× "
                "higher engagement — prioritize step-by-step format"
            )

    # Top keyword insight
    if keywords:
        top_words = [k["word"] for k in keywords[:5]]
        recs.append(f"Top title keywords: {', '.join(top_words)} — use these in your titles")

    # Top channel insight
    top_channel = df.sort_values("view_count", ascending=False).iloc[0]
    recs.append(
        f"Most-viewed channel: {top_channel['channel_title']} "
        f"({top_channel['view_count']:,} views on top video) — analyze their format"
    )

    # Recency insight
    recent = df[df["days_since_published"] <= 30]
    if not recent.empty:
        avg_views_recent = int(recent["view_count"].mean())
        recs.append(
            f"Videos from last 30 days average {avg_views_recent:,} views — "
            "publishing frequently keeps you relevant"
        )

    # High engagement but lower views = underrated content angle
    high_eng = df[df["engagement_rate"] > df["engagement_rate"].quantile(0.9)]
    if not high_eng.empty:
        sample = high_eng.sort_values("engagement_rate", ascending=False).iloc[0]
        recs.append(
            f"Highest engagement video: \"{sample['title'][:60]}...\" "
            f"({sample['engagement_rate']}% engagement rate) — study this format"
        )

    return recs


def main():
    df = load_data()
    print(f"Loaded {len(df)} videos from {INPUT_FILE}")

    df = compute_engagement_metrics(df)

    # Rank columns
    df["rank_by_views"] = df["view_count"].rank(ascending=False, method="min").astype(int)
    df["rank_by_engagement"] = df["engagement_rate"].rank(ascending=False, method="min").astype(int)
    df["rank_by_growth"] = df["views_per_day"].rank(ascending=False, method="min").astype(int)

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Enriched data saved to {OUTPUT_CSV}")

    # Build insights summary
    keywords = extract_keywords(df["title"])
    channels = channel_leaderboard(df)
    upload_data = upload_trend(df)
    recency = segment_by_recency(df)
    recs = content_recommendations(df, keywords)

    top10_views = (
        df.sort_values("view_count", ascending=False)
        .head(10)[["video_id", "title", "channel_title", "view_count", "like_count", "comment_count", "engagement_rate", "days_since_published", "thumbnail_url"]]
        .to_dict(orient="records")
    )
    top10_engagement = (
        df[df["view_count"] >= 1000]
        .sort_values("engagement_rate", ascending=False)
        .head(10)[["video_id", "title", "channel_title", "view_count", "engagement_rate", "days_since_published"]]
        .to_dict(orient="records")
    )

    insights = {
        "generated_at": datetime.now().isoformat(),
        "total_videos": len(df),
        "recency_segments": recency,
        "summary_stats": {
            "avg_views": int(df["view_count"].mean()),
            "median_views": int(df["view_count"].median()),
            "avg_engagement_rate": round(float(df["engagement_rate"].mean()), 2),
            "max_views": int(df["view_count"].max()),
            "total_unique_channels": int(df["channel_title"].nunique()),
        },
        "top_videos_by_views": top10_views,
        "top_videos_by_engagement": top10_engagement,
        "trending_keywords": keywords,
        "channel_leaderboard": channels,
        "upload_trend": upload_data,
        "content_recommendations": recs,
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(insights, f, indent=2, ensure_ascii=False)

    print(f"Insights saved to {OUTPUT_JSON}")
    print(f"\nSummary:")
    print(f"  Total videos analyzed: {len(df)}")
    print(f"  Avg views: {insights['summary_stats']['avg_views']:,}")
    print(f"  Avg engagement rate: {insights['summary_stats']['avg_engagement_rate']}%")
    print(f"  Unique channels: {insights['summary_stats']['total_unique_channels']}")


if __name__ == "__main__":
    main()
