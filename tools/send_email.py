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


def load_insights_summary() -> str:
    """Load key stats from insights.json for the email body."""
    import json
    insights_path = ".tmp/insights.json"
    if not os.path.exists(insights_path):
        return ""
    with open(insights_path, encoding="utf-8") as f:
        data = json.load(f)
    stats = data.get("summary_stats", {})
    top_videos = data.get("top_videos_by_views", [])
    top_channels = data.get("channel_leaderboard", [])

    def fmt(n):
        n = int(n)
        return f"{n / 1_000_000:.1f}M" if n >= 1_000_000 else f"{n / 1_000:.0f}K" if n >= 1_000 else str(n)

    lines = [
        f"• Videos analyzed: {data.get('total_videos', 'N/A'):,}",
        f"• Unique channels: {stats.get('total_unique_channels', 'N/A'):,}",
        f"• Average views: {fmt(stats.get('avg_views', 0))}",
        f"• Average engagement rate: {stats.get('avg_engagement_rate', 'N/A')}%",
    ]
    if top_videos:
        tv = top_videos[0]
        lines.append(f"• Most viewed: \"{tv['title'][:70]}\" — {fmt(tv['view_count'])} views")
    if top_channels:
        tc = top_channels[0]
        lines.append(f"• Top channel: {tc['channel_title']} ({fmt(tc['total_views'])} total views)")

    return "\n".join(lines)


def build_email(deck_path: str, summary: str) -> MIMEMultipart:
    date_str = datetime.now().strftime("%B %d, %Y")
    subject = f"AI YouTube Trend Report — {date_str}"

    body = f"""Hi,

Your AI YouTube Trend Report for {date_str} is attached.

Quick summary:
{summary}

The full slide deck includes:
  • Top 10 videos by views and engagement rate
  • Trending keywords in AI niche titles
  • Top channels leaderboard
  • Upload activity over the last 90 days
  • Data-driven content recommendations

Open the attached .pptx in PowerPoint, Keynote, or Google Slides.

—
Sent automatically by the WAT YouTube Trend Analysis pipeline.
"""

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
    summary = load_insights_summary()
    msg = build_email(deck_path, summary)
    send(msg)


if __name__ == "__main__":
    main()
