#!/usr/bin/env python3
import os
import sys
import json
from api import fetch_langs

BG_COLOR = "#151b23"
TEXT_COLOR = "#c9d1d9"
TITLE_COLOR = "#e6edf3"


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

    langs = fetch_langs(username, token)

    os.makedirs("cards", exist_ok=True)
    with open("cards/top-langs.svg", "w") as f:
        f.write(render_langs_card(langs))

    print(f"Wrote cards/top-langs.svg for {username}")
    print(json.dumps(langs, indent=2))


if __name__ == "__main__":
    main()
