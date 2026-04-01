"""
send_email.py
-------------
Sends the AI trend report slide deck via Gmail SMTP.

Uses Python stdlib only (smtplib + email.mime) — no extra dependencies.

Reads from .env:
  GMAIL_ADDRESS      — sender Gmail address
  GMAIL_APP_PASSWORD — 16-char App Password (NOT your Gmail login password)
  RECIPIENT_EMAIL    — where to deliver the report

Input:  .tmp/ai_trend_report_YYYYMMDD.pptx  (most recent, from create_deck.py)
"""

import glob
import os
import smtplib
import sys
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587  # TLS


def validate_env():
    missing = []
    if not GMAIL_ADDRESS:
        missing.append("GMAIL_ADDRESS")
    if not GMAIL_APP_PASSWORD:
        missing.append("GMAIL_APP_PASSWORD")
    if not RECIPIENT_EMAIL:
        missing.append("RECIPIENT_EMAIL")
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
        print("Add these to your .env file and try again.")
        sys.exit(1)


def find_latest_deck() -> str:
    """Find the most recently created .pptx report in .tmp/."""
    pattern = ".tmp/ai_trend_report_*.pptx"
    files = sorted(glob.glob(pattern), reverse=True)
    if not files:
        print("ERROR: No report found in .tmp/. Run create_deck.py first.")
        sys.exit(1)
    return files[0]


def fmt(n) -> str:
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def load_insights() -> dict:
    import json
    path = ".tmp/insights.json"
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_email(deck_path: str, insights: dict) -> MIMEMultipart:
    date_str = datetime.now().strftime("%B %d, %Y")
    subject = f"🤖 AI YouTube Briefing — {date_str}"

    stats = insights.get("summary_stats", {})
    top_views = insights.get("top_videos_by_views", [])
    top_eng = insights.get("top_videos_by_engagement", [])
    keywords = insights.get("trending_keywords", [])
    channels = insights.get("channel_leaderboard", [])
    recs = insights.get("content_recommendations", [])
    total = insights.get("total_videos", 0)

    # ── Section: header ──────────────────────────────────────────────────────
    lines = [
        f"AI YOUTUBE BRIEFING — {date_str.upper()}",
        "=" * 56,
        f"Analyzed {total:,} videos across {stats.get('total_unique_channels', 0):,} channels "
        f"(last 90 days) | Avg engagement: {stats.get('avg_engagement_rate', 0)}%",
        "",
    ]

    # ── Section: top trending videos ─────────────────────────────────────────
    lines += [
        "WHAT'S TRENDING RIGHT NOW",
        "-" * 56,
        "Top videos by views in the AI & automation niche:",
        "",
    ]
    for i, v in enumerate(top_views[:5], 1):
        url = f"https://youtube.com/watch?v={v['video_id']}"
        days = int(v.get("days_since_published", 0))
        age = f"{days}d ago" if days < 30 else f"{days // 7}w ago"
        lines += [
            f"{i}. {v['title']}",
            f"   {v['channel_title']} · {fmt(v['view_count'])} views · {age}",
            f"   {url}",
            "",
        ]

    # ── Section: most engaging ────────────────────────────────────────────────
    lines += [
        "MOST ENGAGING CONTENT (audience resonance)",
        "-" * 56,
        "These videos have the highest like + comment rate relative to views:",
        "",
    ]
    for i, v in enumerate(top_eng[:5], 1):
        url = f"https://youtube.com/watch?v={v['video_id']}"
        lines += [
            f"{i}. {v['title']}",
            f"   {v['channel_title']} · {v['engagement_rate']}% engagement · {fmt(v['view_count'])} views",
            f"   {url}",
            "",
        ]

    # ── Section: trending keywords ────────────────────────────────────────────
    if keywords:
        top_words = [k["word"] for k in keywords[:10]]
        lines += [
            "TRENDING KEYWORDS IN AI NICHE TITLES",
            "-" * 56,
            "  " + "  ·  ".join(top_words),
            "",
        ]

    # ── Section: top channels ─────────────────────────────────────────────────
    if channels:
        lines += [
            "TOP CHANNELS TO WATCH",
            "-" * 56,
        ]
        for i, c in enumerate(channels[:5], 1):
            lines.append(
                f"{i}. {c['channel_title']} — {fmt(c['total_views'])} views "
                f"across {c['video_count']} videos · {c['avg_engagement']:.1f}% avg engagement"
            )
        lines.append("")

    # ── Section: recommendations ──────────────────────────────────────────────
    if recs:
        lines += [
            "CONTENT RECOMMENDATIONS FOR YOU",
            "-" * 56,
        ]
        for i, rec in enumerate(recs, 1):
            lines.append(f"{i}. {rec}")
        lines.append("")

    # ── Footer ────────────────────────────────────────────────────────────────
    lines += [
        "=" * 56,
        "Full slide deck with charts attached.",
        "Open the .pptx in PowerPoint, Keynote, or Google Slides.",
        "",
        "Sent automatically by the WAT YouTube Trend Analysis pipeline.",
    ]

    body = "\n".join(lines)

    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    # Attach deck
    with open(deck_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    filename = os.path.basename(deck_path)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)

    return msg


def send(msg: MIMEMultipart):
    print(f"Connecting to {SMTP_SERVER}:{SMTP_PORT}...")
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        print(f"Logging in as {GMAIL_ADDRESS}...")
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        print(f"Sending to {RECIPIENT_EMAIL}...")
        server.sendmail(GMAIL_ADDRESS, RECIPIENT_EMAIL, msg.as_string())
    print("Email sent successfully.")


def main():
    validate_env()
    deck_path = find_latest_deck()
    print(f"Report to send: {deck_path}")
    insights = load_insights()
    msg = build_email(deck_path, insights)
    send(msg)


if __name__ == "__main__":
    main()
