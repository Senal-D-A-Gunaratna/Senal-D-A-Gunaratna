#!/usr/bin/env python3
"""
Self-contained GitHub stats SVG generator.
Queries the GitHub GraphQL API directly and renders two SVG cards:
  cards/stats.svg      - stars, commits (last yr), PRs, issues, repos
  cards/top-langs.svg  - language breakdown by bytes across owned repos

No third-party stats service involved, so no more "resource not
accessible" / outage errors from an external Vercel deployment.

Requires: GITHUB_TOKEN env var (repo-scoped default token is fine
for public data queried by login, since we don't use `viewer`).
"""

import os
import sys
import json
import urllib.request

GITHUB_API = "https://api.github.com/graphql"
BG_COLOR = "#151b23"
TEXT_COLOR = "#c9d1d9"
TITLE_COLOR = "#e6edf3"
ICON_COLOR = "#c9d1d9"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LANG_COLORS_PATH = os.path.join(SCRIPT_DIR, "..", "assets", "lang-colors.json")

with open(LANG_COLORS_PATH) as f:
    LANG_COLORS = json.load(f)


def gh_graphql(query, variables, token):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        GITHUB_API,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "stats-gen-script",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    if "errors" in data:
        raise RuntimeError(json.dumps(data["errors"]))
    return data["data"]


def fetch_stats(username, token):
    query = """
    query($login: String!) {
      user(login: $login) {
        repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
          totalCount
          nodes {
            stargazerCount
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges { size node { name color } }
            }
          }
        }
        contributionsCollection {
          totalCommitContributions
          totalPullRequestContributions
          totalIssueContributions
        }
        followers { totalCount }
      }
    }
    """
    data = gh_graphql(query, {"login": username}, token)
    user = data["user"]
    repos = user["repositories"]["nodes"]

    total_stars = sum(r["stargazerCount"] for r in repos)
    total_repos = user["repositories"]["totalCount"]
    commits = user["contributionsCollection"]["totalCommitContributions"]
    prs = user["contributionsCollection"]["totalPullRequestContributions"]
    issues = user["contributionsCollection"]["totalIssueContributions"]
    followers = user["followers"]["totalCount"]

    lang_totals = {}
    for r in repos:
        for edge in r["languages"]["edges"]:
            name = edge["node"]["name"]
            color = edge["node"]["color"] or LANG_COLORS.get(name, "#888888")
            lang_totals.setdefault(name, {"size": 0, "color": color})
            lang_totals[name]["size"] += edge["size"]

    total_size = sum(v["size"] for v in lang_totals.values()) or 1
    langs = sorted(
        (
            {"name": k, "pct": v["size"] / total_size * 100, "color": v["color"]}
            for k, v in lang_totals.items()
        ),
        key=lambda x: -x["pct"],
    )[:8]

    return {
        "stars": total_stars,
        "repos": total_repos,
        "commits": commits,
        "prs": prs,
        "issues": issues,
        "followers": followers,
        "langs": langs,
    }


# Octicon 16px path data (MIT, github/octicons)
ICONS = {
    "star": "M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z",
    "commit": "M11.93 8.5a4.002 4.002 0 01-7.86 0H.75a.75.75 0 010-1.5h3.32a4.002 4.002 0 017.86 0h3.32a.75.75 0 010 1.5zM8 5a3 3 0 100 6 3 3 0 000-6z",
    "issue": "M8 9.5a1.5 1.5 0 100-3 1.5 1.5 0 000 3zM8 0a8 8 0 100 16A8 8 0 008 0zM1.5 8a6.5 6.5 0 1113 0 6.5 6.5 0 01-13 0z",
    "pr": "M1.5 3.25a2.25 2.25 0 113 2.122v5.256a2.251 2.251 0 11-1.5 0V5.372A2.25 2.25 0 011.5 3.25zm5.677-.177L9.573.677A.25.25 0 0110 .854V2.5h1A2.5 2.5 0 0113.5 5v5.628a2.251 2.251 0 11-1.5 0V5a1 1 0 00-1-1h-1v1.646a.25.25 0 01-.427.177L7.177 3.427a.25.25 0 010-.354zM3.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm0 9.5a.75.75 0 100 1.5.75.75 0 000-1.5zm8.25.75a.75.75 0 101.5 0 .75.75 0 00-1.5 0z",
    "repo": "M1.75 0A1.75 1.75 0 000 1.75v12.5C0 15.216.784 16 1.75 16h8.5A1.75 1.75 0 0012 14.25v-.5h1.25a1.75 1.75 0 001.75-1.75v-8.5A1.75 1.75 0 0013.25 1.75H12v-.5A1.75 1.75 0 0010.25 0h-8.5zM1.5 1.75a.25.25 0 01.25-.25h8.5a.25.25 0 01.25.25v12.5a.25.25 0 01-.25.25h-8.5a.25.25 0 01-.25-.25V1.75zm11 1.5h.75a.25.25 0 01.25.25v8.5a.25.25 0 01-.25.25H12v-9z",
    "people": "M10.561 8.073a6.005 6.005 0 013.432 5.142.75.75 0 11-1.498.07 4.5 4.5 0 00-8.99 0 .75.75 0 01-1.498-.07 6.005 6.005 0 013.431-5.142 3.999 3.999 0 115.123 0zM10.5 5a2.5 2.5 0 10-5 0 2.5 2.5 0 005 0z",
    "chart": "M1.5 1.75V13.5h13.75a.75.75 0 010 1.5H.75a.75.75 0 01-.75-.75V1.75a.75.75 0 011.5 0zm14.28 2.53l-5.25 5.25a.75.75 0 01-1.06 0L7 7.06 4.28 9.78a.75.75 0 01-1.06-1.06l3.25-3.25a.75.75 0 011.06 0L10 7.94l4.72-4.72a.75.75 0 111.06 1.06z",
}


def grade(stats):
    # Rough approximation of the classic ranking curve (S/A/B/C bands),
    # not the exact upstream formula, just a reasonable stand-in.
    score = (
        min(stats["stars"], 500) / 500 * 40
        + min(stats["commits"], 1000) / 1000 * 30
        + min(stats["prs"] + stats["issues"], 200) / 200 * 15
        + min(stats["followers"], 200) / 200 * 15
    )
    if score >= 90:
        return "S", score
    if score >= 75:
        return "A+", score
    if score >= 60:
        return "A", score
    if score >= 45:
        return "A-", score
    if score >= 30:
        return "B+", score
    return "B", score


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
    grade_letter, score = grade(stats)
    ring_r = 55
    ring_cx, ring_cy = width - 90, rows_center_y - 5
    circumference = 2 * 3.14159265 * ring_r
    dash = circumference * (score / 100)
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
        if icon == "people":
            svg.append(
                '  <g transform="translate(16,0) scale(-1,1)">'
                f'    <path d="{ICONS["people"]}" fill="#6e7681" transform="translate(-1,3.2) scale(0.75)"/>'
                f'    <path d="{ICONS["people"]}" fill="{ICON_COLOR}" transform="translate(3.2,0) scale(0.95)"/>'
                "  </g>"
            )
        else:
            svg.append(
                f'  <path d="{ICONS[icon]}" fill="{ICON_COLOR}" transform="scale(1)"/>'
            )
        svg.append(
            f'  <text x="24" y="12" class="stat">{label}:</text>'
            f'  <text x="280" y="12" class="stat" font-weight="600" text-anchor="end">{value:,}</text>'
        )
        svg.append("</g>")
        y += row_h

    # Rank ring, top-right
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


def render_langs_card(langs):
    width = 420
    row_h = 22
    height = 45 + 18 + row_h * len(langs) + 15
    bar_w = width - 50

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        f'  .header {{ font: 600 18px "Segoe UI", Ubuntu, sans-serif; fill: {TITLE_COLOR}; animation: fadeIn 0.8s ease-in-out forwards; }}',
        f'  .lang-name {{ font: 400 15px "Segoe UI", Ubuntu, sans-serif; fill: {TEXT_COLOR}; }}',
        f"  .lang-pct {{ fill: #8b949e; }}",
        f"  .stagger {{ opacity: 0; animation: fadeIn 0.3s ease-in-out forwards; }}",
        f"  @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}",
        "</style>",
        f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="4.5" fill="{BG_COLOR}" stroke="#30363d" stroke-width="1"/>',
        f'<text x="25" y="35" class="header">Most Used Languages</text>',
    ]

    bar_y = 50
    svg.append('<clipPath id="barclip">')
    svg.append(f'  <rect x="25" y="{bar_y}" width="0" height="8" rx="4">')
    svg.append(
        f'    <animate attributeName="width" from="0" to="{bar_w}" dur="1s" fill="freeze"/>'
    )
    svg.append("  </rect>")
    svg.append("</clipPath>")
    svg.append('<g clip-path="url(#barclip)">')
    x = 25
    for lang in langs:
        w = bar_w * lang["pct"] / 100
        svg.append(
            f'<rect x="{x:.1f}" y="{bar_y}" width="{w+1:.1f}" height="8" fill="{lang["color"]}"/>'
        )
        x += w
    svg.append("</g>")

    y0 = bar_y + 30
    for i, lang in enumerate(langs):
        cy = y0 + i * row_h
        delay = (i + 3) * 150
        svg.append(f'<g class="stagger" style="animation-delay: {delay}ms">')
        svg.append(
            f'  <circle cx="30" cy="{cy-4}" r="5" fill="{lang["color"]}"/>'
            f'  <text x="42" y="{cy}" class="lang-name">'
            f'{lang["name"]} <tspan class="lang-pct">{lang["pct"]:.2f}%</tspan></text>'
        )
        svg.append("</g>")

    svg.append("</svg>")
    return "\n".join(svg)


def main():
    username = os.environ.get("GITHUB_REPOSITORY_OWNER") or sys.argv[1]
    token = os.environ["GITHUB_TOKEN"]

    stats = fetch_stats(username, token)

    os.makedirs("cards", exist_ok=True)
    with open("cards/stats.svg", "w") as f:
        f.write(render_stats_card(stats))
    with open("cards/top-langs.svg", "w") as f:
        f.write(render_langs_card(stats["langs"]))

    print(f"Wrote cards/stats.svg and cards/top-langs.svg for {username}")
    print(json.dumps({k: v for k, v in stats.items() if k != "langs"}, indent=2))


if __name__ == "__main__":
    main()
