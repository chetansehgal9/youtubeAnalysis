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


def age_label(days: float) -> str:
    d = int(days)
    if d < 1:
        return "today"
    if d == 1:
        return "yesterday"
    if d < 30:
        return f"{d}d ago"
    return f"{d // 7}w ago"


def build_html(insights: dict, date_str: str) -> str:
    stats = insights.get("summary_stats", {})
    top_views = insights.get("top_videos_by_views", [])
    top_eng = insights.get("top_videos_by_engagement", [])
    keywords = insights.get("trending_keywords", [])
    channels = insights.get("channel_leaderboard", [])
    recs = insights.get("content_recommendations", [])
    total = insights.get("total_videos", 0)

    def section_header(title: str, color: str) -> str:
        return f"""
        <tr><td style="padding:28px 32px 8px">
          <div style="display:flex;align-items:center;gap:10px">
            <div style="width:4px;height:22px;background:{color};border-radius:2px;display:inline-block;vertical-align:middle"></div>
            <span style="font-size:13px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:{color};vertical-align:middle">&nbsp;{title}</span>
          </div>
          <hr style="border:none;border-top:1px solid #e8eaf0;margin:10px 0 0">
        </td></tr>"""

    def video_card(v: dict, show_engagement: bool = False) -> str:
        url = f"https://youtube.com/watch?v={v['video_id']}"
        thumb = v.get("thumbnail_url", "")
        days = v.get("days_since_published", 0)
        age = age_label(days)
        metric = (
            f"<span style='color:#2ecc71;font-weight:600'>{v.get('engagement_rate', 0)}% engagement</span> &middot; {fmt(v['view_count'])} views"
            if show_engagement
            else f"<span style='color:#4f8ef7;font-weight:600'>{fmt(v['view_count'])} views</span>"
        )
        thumb_html = (
            f'<td style="width:120px;padding:0 12px 0 0;vertical-align:top">'
            f'<a href="{url}"><img src="{thumb}" width="120" height="68" style="border-radius:6px;display:block;object-fit:cover" alt="thumbnail"></a>'
            f'</td>'
            if thumb else ""
        )
        return f"""
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:14px">
          <tr>
            {thumb_html}
            <td style="vertical-align:top">
              <a href="{url}" style="font-size:14px;font-weight:600;color:#1a1a2e;text-decoration:none;line-height:1.4;display:block">{v['title']}</a>
              <div style="margin-top:5px;font-size:12px;color:#666">
                {v['channel_title']} &middot; {metric} &middot; <span style="color:#999">{age}</span>
              </div>
            </td>
          </tr>
        </table>"""

    # Stat cards
    stat_cards_html = "".join([
        f"""<td style="width:25%;padding:0 6px">
          <div style="background:#f7f8fc;border-radius:10px;padding:16px 12px;text-align:center;border-top:3px solid {color}">
            <div style="font-size:24px;font-weight:800;color:#1a1a2e">{value}</div>
            <div style="font-size:11px;color:#888;margin-top:4px;letter-spacing:0.5px">{label}</div>
          </div>
        </td>"""
        for label, value, color in [
            ("Videos Analyzed", f"{total:,}", "#4f8ef7"),
            ("Channels", f"{stats.get('total_unique_channels', 0):,}", "#2ecc71"),
            ("Avg Views", fmt(stats.get("avg_views", 0)), "#9b59b6"),
            ("Avg Engagement", f"{stats.get('avg_engagement_rate', 0)}%", "#e67e22"),
        ]
    ])

    # Trending keywords badges
    keyword_badges = "".join([
        f'<span style="display:inline-block;background:#eef2ff;color:#4f8ef7;border-radius:20px;padding:5px 13px;margin:4px;font-size:12px;font-weight:600">{k["word"]}</span>'
        for k in keywords[:12]
    ])

    # Top channels rows
    channel_rows = "".join([
        f"""<tr style="background:{'#f7f8fc' if i % 2 == 0 else '#fff'}">
          <td style="padding:10px 12px;font-size:13px;font-weight:600;color:#1a1a2e">{i}. {c['channel_title']}</td>
          <td style="padding:10px 12px;font-size:13px;color:#4f8ef7;font-weight:600;text-align:right">{fmt(c['total_views'])}</td>
          <td style="padding:10px 12px;font-size:13px;color:#666;text-align:right">{c['video_count']} videos</td>
          <td style="padding:10px 12px;font-size:13px;color:#2ecc71;font-weight:600;text-align:right">{c['avg_engagement']:.1f}%</td>
        </tr>"""
        for i, c in enumerate(channels[:5], 1)
    ])

    # Recommendations
    rec_items = "".join([
        f"""<tr>
          <td style="padding:4px 0 12px">
            <table cellpadding="0" cellspacing="0"><tr>
              <td style="width:28px;height:28px;background:#fff3e0;border-radius:50%;text-align:center;vertical-align:middle;font-size:12px;font-weight:800;color:#e67e22;flex-shrink:0">{i}</td>
              <td style="padding-left:12px;font-size:13px;color:#333;line-height:1.5">{rec}</td>
            </tr></table>
          </td>
        </tr>"""
        for i, rec in enumerate(recs, 1)
    ])

    trending_cards = "".join(video_card(v) for v in top_views[:5])
    engaging_cards = "".join(video_card(v, show_engagement=True) for v in top_eng[:5])

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f0f2f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f2f8;padding:24px 0">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0" style="max-width:620px;width:100%">

  <!-- Header -->
  <tr><td style="background:linear-gradient(135deg,#0f0f23 0%,#1a1a3e 100%);border-radius:14px 14px 0 0;padding:32px 32px 28px">
    <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#4f8ef7;font-weight:700">AI &amp; Automation Niche</div>
    <div style="font-size:28px;font-weight:800;color:#fff;margin:6px 0 4px;line-height:1.2">YouTube Trend Briefing</div>
    <div style="font-size:14px;color:#9090b0">{date_str} &nbsp;&middot;&nbsp; Last 90 days</div>
  </td></tr>

  <!-- Body -->
  <tr><td style="background:#fff;border-radius:0 0 14px 14px">

    <!-- Stat cards -->
    <tr><td style="padding:24px 26px 20px">
      <table width="100%" cellpadding="0" cellspacing="0"><tr>{stat_cards_html}</tr></table>
    </td></tr>

    <!-- Trending videos -->
    {section_header("🔥 What's Trending Right Now", "#e74c3c")}
    <tr><td style="padding:16px 32px 4px">
      <p style="margin:0 0 16px;font-size:13px;color:#666">Top videos by views in the AI &amp; automation niche:</p>
      {trending_cards}
    </td></tr>

    <!-- Most engaging -->
    {section_header("💬 Most Engaging Content", "#2ecc71")}
    <tr><td style="padding:16px 32px 4px">
      <p style="margin:0 0 16px;font-size:13px;color:#666">Highest like + comment rate relative to views — what's truly resonating:</p>
      {engaging_cards}
    </td></tr>

    <!-- Keywords -->
    {section_header("🏷️ Trending Keywords in Titles", "#4f8ef7")}
    <tr><td style="padding:16px 32px 20px">
      {keyword_badges}
    </td></tr>

    <!-- Top channels -->
    {section_header("📺 Top Channels to Watch", "#9b59b6")}
    <tr><td style="padding:16px 32px 20px">
      <table width="100%" cellpadding="0" cellspacing="0" style="border-radius:8px;overflow:hidden;border:1px solid #e8eaf0">
        <tr style="background:#1a1a3e">
          <th style="padding:10px 12px;font-size:11px;color:#9090b0;text-align:left;font-weight:600;letter-spacing:0.5px">CHANNEL</th>
          <th style="padding:10px 12px;font-size:11px;color:#9090b0;text-align:right;font-weight:600;letter-spacing:0.5px">TOTAL VIEWS</th>
          <th style="padding:10px 12px;font-size:11px;color:#9090b0;text-align:right;font-weight:600;letter-spacing:0.5px">VIDEOS</th>
          <th style="padding:10px 12px;font-size:11px;color:#9090b0;text-align:right;font-weight:600;letter-spacing:0.5px">AVG ENG.</th>
        </tr>
        {channel_rows}
      </table>
    </td></tr>

    <!-- Recommendations -->
    {section_header("💡 Content Recommendations", "#e67e22")}
    <tr><td style="padding:16px 32px 24px">
      <table width="100%" cellpadding="0" cellspacing="0">{rec_items}</table>
    </td></tr>

    <!-- Footer -->
    <tr><td style="background:#f7f8fc;border-radius:0 0 14px 14px;padding:20px 32px;border-top:1px solid #e8eaf0">
      <p style="margin:0;font-size:12px;color:#999;line-height:1.6">
        📎 Full slide deck with charts attached — open in PowerPoint, Keynote, or Google Slides.<br>
        Sent automatically by the WAT YouTube Trend Analysis pipeline.
      </p>
    </td></tr>

  </td></tr>
</table>
</td></tr>
</table>
</body></html>"""


def build_plain(insights: dict, date_str: str) -> str:
    stats = insights.get("summary_stats", {})
    top_views = insights.get("top_videos_by_views", [])
    top_eng = insights.get("top_videos_by_engagement", [])
    keywords = insights.get("trending_keywords", [])
    channels = insights.get("channel_leaderboard", [])
    recs = insights.get("content_recommendations", [])
    total = insights.get("total_videos", 0)

    lines = [
        f"AI YOUTUBE BRIEFING — {date_str.upper()}",
        "=" * 56,
        f"{total:,} videos · {stats.get('total_unique_channels', 0):,} channels · {stats.get('avg_engagement_rate', 0)}% avg engagement",
        "",
        "TRENDING VIDEOS", "-" * 40,
    ]
    for i, v in enumerate(top_views[:5], 1):
        days = int(v.get("days_since_published", 0))
        lines += [f"{i}. {v['title']}", f"   {v['channel_title']} · {fmt(v['view_count'])} views · {days}d ago",
                  f"   https://youtube.com/watch?v={v['video_id']}", ""]

    lines += ["MOST ENGAGING", "-" * 40]
    for i, v in enumerate(top_eng[:5], 1):
        lines += [f"{i}. {v['title']}", f"   {v['engagement_rate']}% engagement · {fmt(v['view_count'])} views",
                  f"   https://youtube.com/watch?v={v['video_id']}", ""]

    if keywords:
        lines += ["TRENDING KEYWORDS", "-" * 40, "  ·  ".join(k["word"] for k in keywords[:10]), ""]

    if channels:
        lines += ["TOP CHANNELS", "-" * 40]
        for i, c in enumerate(channels[:5], 1):
            lines.append(f"{i}. {c['channel_title']} — {fmt(c['total_views'])} views")
        lines.append("")

    if recs:
        lines += ["RECOMMENDATIONS", "-" * 40]
        for i, rec in enumerate(recs, 1):
            lines.append(f"{i}. {rec}")
        lines.append("")

    lines += ["=" * 56, "Slide deck attached. Open in PowerPoint, Keynote, or Google Slides.",
              "Sent by the WAT YouTube Trend Analysis pipeline."]
    return "\n".join(lines)


def build_email(deck_path: str, insights: dict) -> MIMEMultipart:
    date_str = datetime.now().strftime("%B %d, %Y")
    subject = f"🤖 AI YouTube Briefing — {date_str}"

    recipients = [r.strip() for r in RECIPIENT_EMAIL.split(",")]

    # Outer container: mixed (for attachment)
    msg = MIMEMultipart("mixed")
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    # Inner alternative: plain + html
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(build_plain(insights, date_str), "plain", "utf-8"))
    alt.attach(MIMEText(build_html(insights, date_str), "html", "utf-8"))
    msg.attach(alt)

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
        recipients = [r.strip() for r in RECIPIENT_EMAIL.split(",")]
        print(f"Sending to {', '.join(recipients)}...")
        server.sendmail(GMAIL_ADDRESS, recipients, msg.as_string())
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
