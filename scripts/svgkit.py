"""Shared helpers for every generated graphic.

* Subsets JetBrains Mono down to only the characters a graphic draws and
  inlines it as base64, so nothing loads from a third party.
* Ligatures are stripped from the subset: JetBrains Mono turns "::" into a
  ligature, which would wreck the heatmap and the portrait grid.
* One <style> block carries light + dark colours (prefers-color-scheme).
"""
from __future__ import annotations

import base64
import html
import io
import logging
import re
import sys
from pathlib import Path

FONT_PATH = Path(__file__).parent / "fonts" / "JetBrainsMono-Regular.ttf"

# JetBrains Mono's advance width is exactly 0.600 em. Layouts below rely on it.
ADV = 0.6

FAMILY = "'JB','JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

THEME = (
    ":root{--fg:#e6edf3;--mut:#7d8590;--line:#30363d;--bar:#c9d1d9;"
    "--l1:#6e7681;--l2:#79c0ff;--l3:#d2a8ff;--l4:#ffa657;"
    "--g1:#8ab4f8;--g2:#f0a868}"
    "@media (prefers-color-scheme:light){:root{--fg:#1f2328;--mut:#656d76;"
    "--line:#d0d7de;--bar:#24292f;--l1:#8c959f;--l2:#0969da;--l3:#8250df;"
    "--l4:#bc4c00;--g1:#0550ae;--g2:#953800}}"
)

BASE = (
    "text{font-family:" + FAMILY + ";font-variant-ligatures:none;"
    "font-feature-settings:'liga' 0,'calt' 0;fill:var(--fg);white-space:pre}"
    ".m{fill:var(--mut)}"
    ".l1{fill:var(--l1)}.l2{fill:var(--l2)}.l3{fill:var(--l3)}.l4{fill:var(--l4)}"
    ".ln{stroke:var(--line);stroke-width:1;fill:none}"
    ".st{stroke:var(--fg);stroke-width:1.5;fill:none}"
    ".ar{fill:var(--fg);opacity:.08}"
    ".bar{fill:var(--bar)}"
)

_warned = False
logging.getLogger("fontTools").setLevel(logging.ERROR)


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def fade(begin: float = 0.0, dur: float = 0.6) -> str:
    """SMIL fade-in. Elements using it start at opacity=0."""
    return (
        f'<animate attributeName="opacity" from="0" to="1" '
        f'begin="{begin:.2f}s" dur="{dur:.2f}s" fill="freeze"/>'
    )


def text(x, y, s, size, cls="", anchor="start", begin=0.0, extra="") -> str:
    c = f' class="{cls}"' if cls else ""
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"{c} '
        f'opacity="0"{extra}>{esc(s)}{fade(begin)}</text>'
    )


def font_face(chars: set[str]) -> str:
    global _warned
    if not FONT_PATH.exists():
        if not _warned:
            print(
                f"warning: {FONT_PATH} not found - falling back to the viewer's "
                "monospace font (widths may differ slightly).",
                file=sys.stderr,
            )
            _warned = True
        return ""
    from fontTools import subset
    from fontTools.ttLib import TTFont

    sample = "".join(sorted(chars | {" "}))
    last = None
    for flavor, mime in (("woff2", "font/woff2"), ("woff", "font/woff")):
        try:
            opts = subset.Options()
            opts.layout_features = []  # no ligatures / contextual alternates
            opts.hinting = False
            opts.desubroutinize = True
            # recalcTimestamp=False keeps head.modified at the font's own date;
            # otherwise every build stamps 'now' and the bytes differ run to run.
            font = TTFont(str(FONT_PATH), recalcTimestamp=False)
            sub = subset.Subsetter(opts)
            sub.populate(text=sample)
            sub.subset(font)
            font.flavor = flavor
            buf = io.BytesIO()
            font.save(buf)
            b64 = base64.b64encode(buf.getvalue()).decode()
            return (
                "@font-face{font-family:'JB';"
                f"src:url(data:{mime};base64,{b64}) format('{flavor}')}}"
            )
        except Exception as e:  # brotli missing -> try plain woff
            last = e
    print(f"warning: could not embed font ({last})", file=sys.stderr)
    return ""


def svg_doc(w: int, h: int, body: str, title: str, css: str = "", defs: str = "") -> str:
    chars = set(html.unescape(re.sub(r"<[^>]+>", "", body)))
    chars = {c for c in chars if not c.isspace()}
    style = font_face(chars) + THEME + BASE + css
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" role="img" aria-label="{esc(title)}">'
        f"<title>{esc(title)}</title><defs>{defs}</defs>"
        f"<style>{style}</style>{body}</svg>\n"
    )
