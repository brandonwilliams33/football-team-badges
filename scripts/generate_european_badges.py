#!/usr/bin/env python3
"""Generate local SVG badges and their README entries for European clubs."""

from __future__ import annotations

import html
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
BADGE_DIR = ROOT / "badges" / "european-competitions"
RAW_BASE = (
    "https://raw.githubusercontent.com/brandonwilliams33/"
    "football-team-badges/main/"
)
HEIGHT = 36

LEGACY_ROW = re.compile(
    r"^\| (?P<club>.+?) \| \[!\[(?P<alt>.+?)\]\("
    r"https://img\.shields\.io/badge/.+?\?color=(?P<color>[0-9A-Fa-f]{6})"
    r"&style=for-the-badge\)\]\((?P<url>https?://[^)]+)\) \|$"
)
LOCAL_ROW = re.compile(
    r"^\| (?P<club>.+?) \| \[!\[(?P<alt>.+?)\]\("
    r"(?P<path>badges/european-competitions/[^)]+\.svg)\)\]"
    r"\((?P<url>https?://[^)]+)\) \|"
)


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


def accessible_color(value: str) -> str:
    rgb = [int(value[index : index + 2], 16) for index in (0, 2, 4)]

    def luminance(channel: int) -> float:
        srgb = channel / 255
        linear = srgb / 12.92 if srgb <= 0.04045 else ((srgb + 0.055) / 1.055) ** 2.4
        return linear

    while sum(weight * luminance(channel) for weight, channel in zip((0.2126, 0.7152, 0.0722), rgb)) > 0.179:
        rgb = [round(channel * 0.88) for channel in rgb]
    return "".join(f"{channel:02X}" for channel in rgb)


def render_badge(club: str, color: str) -> str:
    label = club.upper()
    width = max(112, min(360, 32 + len(label) * 8))
    safe_label = html.escape(label)
    title = html.escape(f"{club} text badge")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{HEIGHT}" viewBox="0 0 {width} {HEIGHT}" role="img" '
        f'aria-labelledby="title">\n'
        f'  <title id="title">{title}</title>\n'
        f'  <rect width="{width}" height="{HEIGHT}" rx="3" fill="#{color}"/>\n'
        f'  <text x="50%" y="50%" fill="#FFFFFF" text-anchor="middle" '
        f'dominant-baseline="central" font-family="Arial, Helvetica, sans-serif" '
        f'font-size="12" font-weight="700" letter-spacing="0.6" '
        f'textLength="{width - 20}" lengthAdjust="spacingAndGlyphs">'
        f'{safe_label}</text>\n'
        f'</svg>\n'
    )


def main() -> None:
    lines = README.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index("## European competitions")
    except ValueError as exc:
        raise SystemExit("README.md does not contain the European competitions section") from exc

    league = ""
    output = lines[:start]
    badge_count = 0
    for index, line in enumerate(lines[start:], start=start):
        if line.startswith("### "):
            league = line[4:]
            output.append(line)
            continue

        if line == "| Club | Badge |":
            output.append("| Club | Preview | Copy-paste Markdown |")
            continue

        if line == "| --- | --- |":
            output.append("| --- | --- | --- |")
            continue

        if line.startswith("| ") and (
            "img.shields.io/badge/" in line or "badges/european-competitions/" in line
        ):
            match = LEGACY_ROW.match(line)
            if match:
                data = match.groupdict()
                color = data["color"]
            else:
                match = LOCAL_ROW.match(line)
                if not match:
                    raise SystemExit(f"Could not parse European badge row {index + 1}: {line}")
                data = match.groupdict()
                svg_path = ROOT / data["path"]
                existing_svg = svg_path.read_text(encoding="utf-8")
                color_match = re.search(r'<rect[^>]+fill="#([0-9A-Fa-f]{6})"', existing_svg)
                if not color_match:
                    raise SystemExit(f"Could not read badge color from {svg_path}")
                color = color_match.group(1)

            if not league:
                raise SystemExit(f"Badge row {index + 1} is not under a league heading")
            path = (
                Path("badges")
                / "european-competitions"
                / slugify(league)
                / f"{slugify(data['club'])}.svg"
            )
            color = accessible_color(color)
            target = ROOT / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                render_badge(data["club"], color),
                encoding="utf-8",
            )
            relative_path = path.as_posix()
            raw_url = RAW_BASE + relative_path
            preview = f"[![{data['alt']}]({relative_path})]({data['url']})"
            copy_markdown = f"`[![{data['alt']}]({raw_url})]({data['url']})`"
            output.append(f"| {data['club']} | {preview} | {copy_markdown} |")
            badge_count += 1
            continue

        output.append(line)

    README.write_text("\n".join(output) + "\n", encoding="utf-8")
    print(f"Generated {badge_count} European competition badges.")


if __name__ == "__main__":
    main()
