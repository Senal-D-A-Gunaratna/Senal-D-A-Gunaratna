#!/usr/bin/env python3
import os
import sys
import json
from api import fetch_stats

BG_COLOR = "#151b23"
TEXT_COLOR = "#c9d1d9"
TITLE_COLOR = "#e6edf3"
ICON_COLOR = "#c9d1d9"

ICONS = {
    "star": "M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z",
    "commit": "M11.93 8.5a4.002 4.002 0 01-7.86 0H.75a.75.75 0 010-1.5h3.32a4.002 4.002 0 017.86 0h3.32a.75.75 0 010 1.5zM8 5a3 3 0 100 6 3 3 0 000-6z",
    "issue": "M8 9.5a1.5 1.5 0 100-3 1.5 1.5 0 000 3zM8 0a8 8 0 100 16A8 8 0 008 0zM1.5 8a6.5 6.5 0 1113 0 6.5 6.5 0 01-13 0z",
    "pr": "M1.5 3.25a2.25 2.25 0 113 2.122v5.256a2.251 2.251 0 11-1.5 0V5.372A2.25 2.25 0 011.5 3.25zm5.677-.177L9.573.677A.25.25 0 0110 .854V2.5h1A2.5 2.5 0 0113.5 5v5.628a2.251 2.251 0 11-1.5 0V5a1 1 0 00-1-1h-1v1.646a.25.25 0 01-.427.177L7.177 3.427a.25.25 0 010-.354zM3.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm0 9.5a.75.75 0 100 1.5.75.75 0 000-1.5zm8.25.75a.75.75 0 101.5 0 .75.75 0 00-1.5 0z",
    "repo": "M1.75 0A1.75 1.75 0 000 1.75v12.5C0 15.216.784 16 1.75 16h8.5A1.75 1.75 0 0012 14.25v-.5h1.25a1.75 1.75 0 001.75-1.75v-8.5A1.75 1.75 0 0013.25 1.75H12v-.5A1.75 1.75 0 0010.25 0h-8.5zM1.5 1.75a.25.25 0 01.25-.25h8.5a.25.25 0 01.25.25v12.5a.25.25 0 01-.25.25h-8.5a.25.25 0 01-.25-.25V1.75zm11 1.5h.75a.25.25 0 01.25.25v8.5a.25.25 0 01-.25.25H12v-9z",
    "people": "M2 5.5a3.5 3.5 0 1 1 5.898 2.549 5.508 5.508 0 0 1 3.034 4.084.75.75 0 1 1-1.482.235 4 4 0 0 0-7.9 0 .75.75 0 0 1-1.482-.236A5.507 5.507 0 0 1 3.102 8.05 3.493 3.493 0 0 1 2 5.5ZM11 4a3.001 3.001 0 0 1 2.22 5.018 5.01 5.01 0 0 1 2.56 3.012.749.749 0 0 1-.885.954.752.752 0 0 1-.549-.514 3.507 3.507 0 0 0-2.522-2.372.75.75 0 0 1-.574-.73v-.352a.75.75 0 0 1 .416-.672A1.5 1.5 0 0 0 11 5.5.75.75 0 0 1 11 4Zm-5.5-.5a2 2 0 1 0-.001 3.999A2 2 0 0 0 5.5 3.5Z",
    "chart": "M1.5 1.75V13.5h13.75a.75.75 0 010 1.5H.75a.75.75 0 01-.75-.75V1.75a.75.75 0 011.5 0zm14.28 2.53l-5.25 5.25a.75.75 0 01-1.06 0L7 7.06 4.28 9.78a.75.75 0 01-1.06-1.06l3.25-3.25a.75.75 0 011.06 0L10 7.94l4.72-4.72a.75.75 0 111.06 1.06z",
}


def exponential_cdf(x):
    return 1 - 2 ** -x


def log_normal_cdf(x):
    return x / (1 + x)


def grade(stats, all_commits=False):
    COMMITS_MEDIAN, COMMITS_WEIGHT = (1000 if all_commits else 250), 2
    PRS_MEDIAN, PRS_WEIGHT = 50, 3
    ISSUES_MEDIAN, ISSUES_WEIGHT = 25, 1
    REVIEWS_MEDIAN, REVIEWS_WEIGHT = 2, 1
    STARS_MEDIAN, STARS_WEIGHT = 50, 4
    FOLLOWERS_MEDIAN, FOLLOWERS_WEIGHT = 10, 1

    TOTAL_WEIGHT = (
        COMMITS_WEIGHT
        + PRS_WEIGHT
        + ISSUES_WEIGHT
        + REVIEWS_WEIGHT
        + STARS_WEIGHT
        + FOLLOWERS_WEIGHT
    )

    THRESHOLDS = [1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100]
    LEVELS = ["S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"]

    rank = 1 - (
        COMMITS_WEIGHT * exponential_cdf(stats["commits"] / COMMITS_MEDIAN)
        + PRS_WEIGHT * exponential_cdf(stats["prs"] / PRS_MEDIAN)
        + ISSUES_WEIGHT * exponential_cdf(stats["issues"] / ISSUES_MEDIAN)
        + REVIEWS_WEIGHT * exponential_cdf(stats["reviews"] / REVIEWS_MEDIAN)
        + STARS_WEIGHT * log_normal_cdf(stats["stars"] / STARS_MEDIAN)
        + FOLLOWERS_WEIGHT * log_normal_cdf(stats["followers"] / FOLLOWERS_MEDIAN)
    ) / TOTAL_WEIGHT

    percentile = rank * 100
    level = next(
        LEVELS[i] for i, t in enumerate(THRESHOLDS) if percentile <= t
    )
    return level, percentile


def render_stats_card(stats):
    rows = [
        ("star", "Total Stars", stats["stars"]),
        ("commit", "Total Commits", stats["commits"]),
        ("pr", "Total PRs", stats["prs"]),
        ("issue", "Total Issues", stats["issues"]),
        ("repo", "Total Repos", stats["repos"]),
        ("people", "Followers", stats["followers"]),
    ]
    row_h = 25
    width = 495
    first_row_y = 70
    rows_center_y = first_row_y - 2 + (row_h * (len(rows) - 1)) / 2
    height = first_row_y - 14 + row_h * len(rows) + 12
    grade_letter, percentile = grade(stats)
    ring_fill_pct = 100 - percentile
    ring_r = 55
    ring_cx, ring_cy = width - 90, rows_center_y - 5
    circumference = 2 * 3.14159265 * ring_r
    dash = circumference * (ring_fill_pct / 100)
    end_offset = circumference - dash

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        f'  .header {{ font: 600 18px "Segoe UI", Ubuntu, sans-serif; fill: {TITLE_COLOR}; animation: fadeIn 0.8s ease-in-out forwards; }}',
        f'  .stat {{ font: 600 15px "Segoe UI", Ubuntu, sans-serif; fill: {TEXT_COLOR}; }}',
        f"  .stagger {{ opacity: 0; animation: fadeIn 0.3s ease-in-out forwards; }}",
        f"  .rank-ring {{ fill: none; stroke: #30363d; stroke-width: 6; }}",
        f"  .rank-circle {{ fill: none; stroke: {TITLE_COLOR}; stroke-width: 6; stroke-linecap: round; animation: drawIn 1s ease-in-out forwards; }}",
        f'  .rank-text {{ font: 700 24px "Segoe UI", Ubuntu, sans-serif; fill: {TITLE_COLOR}; text-anchor: middle; animation: fadeIn 0.8s ease-in-out forwards; }}',
        f"  @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}",
        f"  @keyframes drawIn {{ from {{ stroke-dashoffset: {circumference:.1f}; }} to {{ stroke-dashoffset: {end_offset:.1f}; }} }}",
        "</style>",
        f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="4.5" fill="{BG_COLOR}" stroke="#30363d" stroke-width="1"/>',
        f'<g transform="translate(25, 20)">',
        f'  <path d="{ICONS["chart"]}" fill="{TITLE_COLOR}" transform="scale(1)"/>',
        f'  <text x="24" y="14" class="header">GitHub Stats</text>',
        f"</g>",
    ]

    y = 70
    for i, (icon, label, value) in enumerate(rows):
        delay = (i + 3) * 150
        svg.append(
            f'<g class="stagger" style="animation-delay: {delay}ms" transform="translate(25, {y-14})">'
        )
        svg.append(
            f'  <path d="{ICONS[icon]}" fill="{ICON_COLOR}" transform="scale(1)"/>'
        )
        svg.append(
            f'  <text x="24" y="12" class="stat">{label}:</text>'
            f'  <text x="280" y="12" class="stat" font-weight="600" text-anchor="end">{value:,}</text>'
        )
        svg.append("</g>")
        y += row_h

    svg.append(
        f'<circle cx="{ring_cx}" cy="{ring_cy}" r="{ring_r}" class="rank-ring"/>'
    )
    svg.append(
        f'<circle cx="{ring_cx}" cy="{ring_cy}" r="{ring_r}" '
        f'stroke-dasharray="{circumference:.1f}" '
        f'transform="rotate(-90 {ring_cx} {ring_cy})" class="rank-circle"/>'
    )
    svg.append(
        f'<text x="{ring_cx}" y="{ring_cy+7}" class="rank-text">{grade_letter}</text>'
    )

    svg.append("</svg>")
    return "\n".join(svg)


def main():
    username = os.environ.get("GITHUB_REPOSITORY_OWNER") or sys.argv[1]
    token = os.environ["GITHUB_TOKEN"]

    stats = fetch_stats(username, token)

    os.makedirs("cards", exist_ok=True)
    with open("cards/stats.svg", "w") as f:
        f.write(render_stats_card(stats))

    print(f"Wrote cards/stats.svg for {username}")
    print(json.dumps({k: v for k, v in stats.items() if k != "langs"}, indent=2))


if __name__ == "__main__":
    main()
