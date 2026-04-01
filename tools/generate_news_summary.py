"""
generate_news_summary.py
------------------------
Uses Claude API to synthesize a "Top AI News" briefing from trending video titles.

Reads from .env:
  ANTHROPIC_API_KEY — Anthropic API key

Input:  .tmp/insights.json (from analyze_trends.py)
Output: .tmp/news_summary.txt
"""

import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

INSIGHTS_FILE = ".tmp/insights.json"
OUTPUT_FILE = ".tmp/news_summary.txt"


def load_insights() -> dict:
    if not os.path.exists(INSIGHTS_FILE):
        print(f"ERROR: {INSIGHTS_FILE} not found. Run analyze_trends.py first.")
        sys.exit(1)
    with open(INSIGHTS_FILE, encoding="utf-8") as f:
        return json.load(f)


def build_prompt(insights: dict) -> str:
    top_videos = insights.get("top_videos_by_views", [])[:20]
    top_engaging = insights.get("top_videos_by_engagement", [])[:10]
    keywords = insights.get("trending_keywords", [])[:10]

    video_lines = [
        f'- "{v["title"]}" by {v["channel_title"]} ({v.get("view_count", 0):,} views)'
        for v in top_videos
    ]
    engaging_lines = [
        f'- "{v["title"]}" by {v["channel_title"]} ({v.get("engagement_rate", 0)}% engagement)'
        for v in top_engaging
    ]
    kw_str = ", ".join(k["word"] for k in keywords)

    return f"""You are an AI industry analyst writing a daily briefing for content creators in the AI/automation space.

Based on the most-viewed and most-engaging YouTube videos from the past 90 days in the AI & automation niche, identify the top 5-7 AI news themes and developments that content creators should know about.

TOP VIDEOS BY VIEWS:
{chr(10).join(video_lines)}

MOST ENGAGING VIDEOS:
{chr(10).join(engaging_lines)}

TRENDING KEYWORDS IN TITLES: {kw_str}

Write a "Top AI News & Trends" briefing with 5-7 bullet points. Each bullet should:
- Identify a specific AI development, tool, or trend visible in the data
- Be 1-2 sentences, actionable and insightful for a content creator
- Reference specific tools, models, or companies when clearly evident from the titles

Format as plain bullet points (start each with •). Be concise and specific. No intro text, no conclusion."""


def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("WARNING: ANTHROPIC_API_KEY not set — skipping news summary generation.")
        # Write empty file so send_email.py doesn't fail
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("")
        return

    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic package not installed. Run: pip install anthropic")
        sys.exit(1)

    insights = load_insights()
    print("Generating AI news summary with Claude...")

    client = anthropic.Anthropic(api_key=api_key)
    prompt = build_prompt(insights)

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    summary = ""
    for block in message.content:
        if block.type == "text":
            summary = block.text
            break

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(summary)

    print(f"News summary saved to {OUTPUT_FILE}")
    print(f"\nPreview:\n{summary[:400]}")


if __name__ == "__main__":
    main()
