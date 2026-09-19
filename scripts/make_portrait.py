#!/usr/bin/env python3
"""Turn a photo into assets/ascii.svg (a grid of characters on a fixed pitch).

    python scripts/make_portrait.py photo.jpg
    python scripts/make_portrait.py photo.jpg --cols 120 --bg-cut 0.18

Run this by hand whenever you want a new portrait; it is not part of the
daily action.

Tips
  --bg-cut   Blank out pixels close to the photo's background colour (measured
             from the corners). Works best with a plain wall behind you.
             Try 0.12-0.25. 0 disables it.
  --invert   Flip the ramp (bright pixels become dense). Use if your photo is
             a light subject on a dark background.
  --contrast Punch up mid-tones. 1.0 = untouched.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageOps

from svgkit import ADV, esc, svg_doc

# quiet -> loud
RAMP = " .:-=+*#%@"
LINE_H = 1.0  # line height as a multiple of font size


def to_lines(img: Image.Image, cols: int, invert: bool, bg_cut: float,
             contrast: float, gamma: float, oval: float = 0.0,
             detail: float = 0.0) -> list[str]:
    img = ImageOps.exif_transpose(img).convert("RGB")
    w, h = img.size
    rows = max(1, round(h / w * cols * ADV / LINE_H))
    small = img.resize((cols, rows), Image.LANCZOS)

    gray = ImageOps.autocontrast(small.convert("L"), cutoff=1)
    if detail > 0:
        # local contrast: add back (pixel - neighbourhood average) so eyes, lips,
        # nose and hair strands separate even when the whole face is evenly lit
        blur = gray.filter(ImageFilter.GaussianBlur(max(1.0, cols / 14)))
        gp0, bp0 = gray.load(), blur.load()
        boosted = Image.new("L", gray.size)
        bo = boosted.load()
        for y in range(rows):
            for x in range(cols):
                v = gp0[x, y] + detail * 2.2 * (gp0[x, y] - bp0[x, y])
                bo[x, y] = int(min(255, max(0, v)))
        gray = boosted

    mask = None
    if bg_cut > 0:
        px = small.load()
        k = max(2, cols // 30)
        corners = []
        for cx in (0, cols - k):
            for cy in (0, rows - k):
                cells = [px[x, y] for x in range(cx, cx + k) for y in range(cy, cy + k)]
                corners.append(tuple(sum(c[i] for c in cells) / len(cells) for i in range(3)))
        bg = tuple(sorted(c[i] for c in corners)[len(corners) // 2] for i in range(3))
        dist = Image.new("L", small.size)
        dp = dist.load()
        for y in range(rows):
            for x in range(cols):
                p = px[x, y]
                d = sum((p[i] - bg[i]) ** 2 for i in range(3)) ** 0.5 / (3 ** 0.5 * 255)
                dp[x, y] = 255 if d > bg_cut else 0
        mask = dist.filter(ImageFilter.MedianFilter(3))

    if oval > 0:
        # keep only a soft-edged ellipse (head shape); oval = radius scale, ~1.0 fits the frame
        em = Image.new("L", small.size, 0)
        ep = em.load()
        cx, cy = (cols - 1) / 2, (rows - 1) / 2
        rx, ry = cols / 2 * oval, rows / 2 * oval
        for y in range(rows):
            for x in range(cols):
                ep[x, y] = 255 if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1 else 0
        mask = em if mask is None else ImageChops.multiply(mask, em)

    gp = gray.load()
    mp = mask.load() if mask else None
    lines = []
    for y in range(rows):
        row = []
        for x in range(cols):
            v = gp[x, y] / 255
            d = v if invert else 1 - v
            d = min(1.0, max(0.0, (d - 0.5) * contrast + 0.5)) ** gamma
            idx = int(d * (len(RAMP) - 1) + 0.5)
            if mp is not None and mp[x, y] == 0:
                idx = 0
            row.append(RAMP[idx])
        lines.append("".join(row))
    return lines


def render(lines: list[str], font_size: float) -> str:
    cw = ADV * font_size
    lh = LINE_H * font_size
    cols = max(len(l) for l in lines)
    w, h = round(cols * cw), round(len(lines) * lh)

    out = []
    for i, line in enumerate(lines):
        stripped = line.strip(" ")
        if not stripped:
            continue
        lead = len(line) - len(line.lstrip(" "))
        x = round(lead * cw, 2)
        y = round((i + 1) * lh - lh * 0.2, 2)
        # textLength pins the pitch even if the viewer's font is a bit off.
        out.append(
            f'<text x="{x}" y="{y}" textLength="{round(len(stripped) * cw, 2)}" '
            f'lengthAdjust="spacing" opacity="0">{esc(stripped)}'
            f'<animate attributeName="opacity" from="0" to="1" '
            f'begin="{i * 0.025:.3f}s" dur="0.5s" fill="freeze"/></text>'
        )
    css = f"text{{font-size:{font_size}px;fill:url(#g)}}"
    defs = (
        f'<linearGradient id="g" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{w}" y2="{h}">'
        '<stop offset="0" style="stop-color:var(--g1)"/>'
        '<stop offset="1" style="stop-color:var(--g2)"/></linearGradient>'
    )
    return svg_doc(w, h, "".join(out), "ASCII portrait", css=css, defs=defs)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photo")
    ap.add_argument("-o", "--out", default=str(Path(__file__).parent.parent / "assets" / "ascii.svg"))
    ap.add_argument("--cols", type=int, default=110, help="characters per row (detail)")
    ap.add_argument("--font-size", type=float, default=8.0)
    ap.add_argument("--invert", action="store_true")
    ap.add_argument("--bg-cut", type=float, default=0.0)
    ap.add_argument("--oval", type=float, default=0.0,
                    help="blank everything outside a head-shaped ellipse (try 0.9-1.0)")
    ap.add_argument("--detail", type=float, default=0.0,
                    help="local-contrast boost for faces (0-1.5; try 0.8)")
    ap.add_argument("--contrast", type=float, default=1.35)
    ap.add_argument("--gamma", type=float, default=0.9)
    a = ap.parse_args()

    lines = to_lines(Image.open(a.photo), a.cols, a.invert, a.bg_cut, a.contrast, a.gamma, a.oval, a.detail)
    svg = render(lines, a.font_size)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(f"wrote {out} ({len(svg) / 1024:.0f} KB, {a.cols}x{len(lines)} chars)")


if __name__ == "__main__":
    main()
