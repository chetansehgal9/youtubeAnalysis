"""
generate_charts.py
------------------
Generates chart PNG images from insights data for use in the slide deck.

Input:  .tmp/insights.json  (produced by analyze_trends.py)
Output: .tmp/charts/*.png   (5 chart images)
"""

import json
import os
import sys
import textwrap

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

INPUT_FILE = ".tmp/insights.json"
OUTPUT_DIR = ".tmp/charts"

# Color palette
BG_COLOR = "#0f0f23"
SURFACE_COLOR = "#1a1a3e"
ACCENT_BLUE = "#4f8ef7"
ACCENT_PURPLE = "#9b59b6"
ACCENT_GREEN = "#2ecc71"
ACCENT_ORANGE = "#e67e22"
TEXT_COLOR = "#e8e8f0"
MUTED_TEXT = "#9090b0"

CHART_STYLE = {
    "figure.facecolor": BG_COLOR,
    "axes.facecolor": SURFACE_COLOR,
    "axes.edgecolor": MUTED_TEXT,
    "axes.labelcolor": TEXT_COLOR,
    "axes.titlecolor": TEXT_COLOR,
    "xtick.color": MUTED_TEXT,
    "ytick.color": TEXT_COLOR,
    "text.color": TEXT_COLOR,
    "grid.color": "#2a2a4a",
    "grid.alpha": 0.6,
}


def load_insights() -> dict:
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: {INPUT_FILE} not found. Run analyze_trends.py first.")
        sys.exit(1)
    with open(INPUT_FILE, encoding="utf-8") as f:
        return json.load(f)


def apply_style():
    plt.rcParams.update(CHART_STYLE)
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.size"] = 11


def shorten_title(title: str, max_len: int = 45) -> str:
    return title if len(title) <= max_len else title[:max_len].rstrip() + "…"


def format_views(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def chart_top_videos_by_views(insights: dict, out_path: str):
    videos = insights["top_videos_by_views"][:10]
    labels = [shorten_title(v["title"]) for v in videos][::-1]
    values = [v["view_count"] for v in videos][::-1]
    colors = [ACCENT_BLUE] * len(labels)

    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.barh(labels, values, color=colors, height=0.65, edgecolor="none")

    # Value labels on bars
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() * 1.01,
            bar.get_y() + bar.get_height() / 2,
            format_views(val),
            va="center",
            ha="left",
            fontsize=10,
            color=TEXT_COLOR,
        )

    ax.set_xlabel("View Count", labelpad=10)
    ax.set_title("Top 10 Videos by Views", fontsize=16, fontweight="bold", pad=16)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: format_views(int(x))))
    ax.grid(axis="x", linestyle="--")
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout(pad=1.5)
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close()
    print(f"  Saved: {out_path}")


def chart_top_videos_by_engagement(insights: dict, out_path: str):
    videos = insights["top_videos_by_engagement"][:10]
    if not videos:
        print("  SKIP: No engagement data available")
        return
    labels = [shorten_title(v["title"]) for v in videos][::-1]
    values = [v["engagement_rate"] for v in videos][::-1]

    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.barh(labels, values, color=ACCENT_GREEN, height=0.65, edgecolor="none")

    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() * 1.01,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.1f}%",
            va="center",
            ha="left",
            fontsize=10,
            color=TEXT_COLOR,
        )

    ax.set_xlabel("Engagement Rate (%)", labelpad=10)
    ax.set_title("Top 10 Videos by Engagement Rate", fontsize=16, fontweight="bold", pad=16)
    ax.grid(axis="x", linestyle="--")
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout(pad=1.5)
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close()
    print(f"  Saved: {out_path}")


def chart_trending_keywords(insights: dict, out_path: str):
    keywords = insights["trending_keywords"][:15]
    if not keywords:
        print("  SKIP: No keyword data available")
        return
    labels = [k["word"] for k in keywords][::-1]
    values = [k["count"] for k in keywords][::-1]

    # Color gradient by rank
    cmap = plt.get_cmap("plasma")
    colors = [cmap(i / len(labels)) for i in range(len(labels))]

    fig, ax = plt.subplots(figsize=(11, 7))
    bars = ax.barh(labels, values, color=colors, height=0.65, edgecolor="none")

    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() * 1.01,
            bar.get_y() + bar.get_height() / 2,
            str(val),
            va="center",
            ha="left",
            fontsize=10,
            color=TEXT_COLOR,
        )

    ax.set_xlabel("Frequency in Top Video Titles", labelpad=10)
    ax.set_title("Trending Keywords in AI Niche Titles", fontsize=16, fontweight="bold", pad=16)
    ax.grid(axis="x", linestyle="--")
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout(pad=1.5)
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close()
    print(f"  Saved: {out_path}")


def chart_channel_leaderboard(insights: dict, out_path: str):
    channels = insights["channel_leaderboard"][:10]
    if not channels:
        print("  SKIP: No channel data available")
        return
    labels = [shorten_title(c["channel_title"], 30) for c in channels][::-1]
    values = [c["total_views"] for c in channels][::-1]
    counts = [c["video_count"] for c in channels][::-1]

    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.barh(labels, values, color=ACCENT_PURPLE, height=0.65, edgecolor="none")

    for bar, val, cnt in zip(bars, values, counts):
        ax.text(
            bar.get_width() * 1.01,
            bar.get_y() + bar.get_height() / 2,
            f"{format_views(val)} ({cnt} videos)",
            va="center",
            ha="left",
            fontsize=9,
            color=TEXT_COLOR,
        )

    ax.set_xlabel("Total Views (from analyzed videos)", labelpad=10)
    ax.set_title("Top Channels by Total Views", fontsize=16, fontweight="bold", pad=16)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: format_views(int(x))))
    ax.grid(axis="x", linestyle="--")
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout(pad=1.5)
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close()
    print(f"  Saved: {out_path}")


def chart_upload_trend(insights: dict, out_path: str):
    trend_data = insights["upload_trend"]
    if not trend_data:
        print("  SKIP: No upload trend data available")
        return

    labels = [d["label"] for d in trend_data]
    values = [d["upload_count"] for d in trend_data]

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.fill_between(range(len(labels)), values, alpha=0.3, color=ACCENT_ORANGE)
    ax.plot(range(len(labels)), values, color=ACCENT_ORANGE, linewidth=2.5, marker="o", markersize=6)

    for i, (label, val) in enumerate(zip(labels, values)):
        ax.annotate(
            str(val),
            (i, val),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=9,
            color=TEXT_COLOR,
        )

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("Number of Videos Published", labelpad=10)
    ax.set_title("Upload Activity Over Last 90 Days", fontsize=16, fontweight="bold", pad=16)
    ax.grid(axis="y", linestyle="--")
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout(pad=1.5)
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close()
    print(f"  Saved: {out_path}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    apply_style()

    insights = load_insights()
    print(f"Generating charts from {INPUT_FILE}...")

    chart_top_videos_by_views(insights, os.path.join(OUTPUT_DIR, "top_videos_views.png"))
    chart_top_videos_by_engagement(insights, os.path.join(OUTPUT_DIR, "top_videos_engagement.png"))
    chart_trending_keywords(insights, os.path.join(OUTPUT_DIR, "trending_keywords.png"))
    chart_channel_leaderboard(insights, os.path.join(OUTPUT_DIR, "channel_leaderboard.png"))
    chart_upload_trend(insights, os.path.join(OUTPUT_DIR, "upload_trend.png"))

    print(f"\nDone. Charts saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
