#!/usr/bin/env python3
"""Fail the build if the styles stray from the Carbon 2x grid.

Rules (carbondesignsystem.com, 2x grid and spacing):
  1. Spacing (margin, padding, gap, top/left/right/bottom ...) must use the --s-* scale,
     0, auto, or a percentage. No raw px/rem.
  2. Box sizes (width, height, min/max-*) in px must be a multiple of 8, or use --s-*, %, vw, vh.
  3. line-height in px must be a multiple of 4 (unitless ratios are not allowed).
  4. Media queries may only switch at Carbon breakpoints: 320, 672, 1056, 1312, 1584
     (max-width: one pixel less).
  5. The --s-* scale itself must be Carbon's: 2 4 8 12 16 24 32 40 48 64 80 96 160.
Checks custom.css and any inline style="" in templates. Run: python3 scripts/check_grid.py
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCALE = [2, 4, 8, 12, 16, 24, 32, 40, 48, 64, 80, 96, 160]
BREAKPOINTS = {320, 672, 1056, 1312, 1584}
SPACING = re.compile(r"^(margin|padding)(-(top|right|bottom|left|inline|block)(-(start|end))?)?$|^(gap|row-gap|column-gap|top|right|bottom|left|inset|scroll-margin-top)$")
SIZING = re.compile(r"^(width|height|min-width|min-height|max-width|max-height|flex-basis)$")
LEN = re.compile(r"(-?\d*\.?\d+)(px|rem|em)\b")
problems = []


def px(num, unit):
    return float(num) * (16 if unit in ("rem", "em") else 1)


def check_decl(prop, val, where):
    prop, val = prop.strip().lower(), val.strip()
    if prop.startswith("--s-"):
        n = int(prop[4:])
        want = f"{SCALE[n - 1]}px"
        if val != want:
            problems.append(f"{where}: {prop} is {val}, Carbon's scale says {want}")
        return
    if prop.startswith("--") and re.fullmatch(r"\d+px", val) and int(val[:-2]) % 8:
        problems.append(f"{where}: {prop} is {val}, not a multiple of 8px")
        return
    stripped = re.sub(r"var\(--s-\d+\)", "", val)
    if SPACING.match(prop):
        for num, unit in LEN.findall(stripped):
            if float(num) != 0:
                problems.append(f"{where}: {prop}: {val} uses a raw size; use var(--s-N) from the Carbon scale")
    elif SIZING.match(prop):
        for num, unit in LEN.findall(stripped):
            v = px(num, unit)
            if v and v % 8:
                problems.append(f"{where}: {prop}: {val} is not a multiple of 8px")
    elif prop == "line-height" and val != "inherit":
        m = re.fullmatch(r"(\d+)px", val)
        if not m or int(m.group(1)) % 4:
            problems.append(f"{where}: line-height: {val} must be px and a multiple of 4")


def check_css(text, where):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"@import[^;]*;", "", text)
    for m in re.finditer(r"@media[^{]*", text):
        for kind, num in re.findall(r"(min|max)-width:\s*(\d+)px", m.group()):
            n = int(num) + (1 if kind == "max" else 0)
            if n not in BREAKPOINTS:
                problems.append(f"{where}: media query {m.group().strip()} is not a Carbon breakpoint {sorted(BREAKPOINTS)}")
    body = re.sub(r"@media[^{]*\{", "", text)
    for decl in re.finditer(r"([a-z-]+)\s*:\s*([^;{}]+)(?=;|})", body):
        # shorthand "font: 600 12px/16px ..." is type, not spacing: skip
        check_decl(decl.group(1), decl.group(2), where)


check_css((ROOT / "custom.css").read_text(), "custom.css")
for pal in sorted((ROOT / "palettes").glob("*.css")):   # palettes carry colours and fonts only
    check_css(pal.read_text(), f"palettes/{pal.name}")
for f in list(ROOT.glob("*.qmd")) + list(ROOT.glob("*.ejs")):
    for style in re.findall(r'style="([^"]*)"', f.read_text()):
        for decl in style.split(";"):
            if ":" in decl:
                check_decl(*decl.split(":", 1), f.name)

if problems:
    print("Carbon 2x grid check FAILED:", file=sys.stderr)
    for p in problems:
        print("  -", p, file=sys.stderr)
    sys.exit(1)
print("grid: custom.css follows the Carbon 2x grid")
