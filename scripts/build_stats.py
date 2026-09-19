#!/usr/bin/env python3
"""Generate the stat graphics from the GitHub GraphQL API.

    GH_TOKEN=ghp_xxx python scripts/build_stats.py --login yourname
    python scripts/build_stats.py --mock          # offline preview, fake data

Output is deterministic (no timestamps), so the workflow only commits when
your numbers actually change.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import urllib.request
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from svgkit import ADV, esc, fade, svg_doc, text

HEADINGS = ["about", "stack", "projects", "stats", "about this page"]
CONTENT_W = 640  # width of the README column the graphics are designed for

# ---------------------------------------------------------------- data ----

QUERY = """
query($login:String!, $after:String){
  user(login:$login){
    contributionsCollection{
      contributionCalendar{
        totalContributions
        weeks{ contributionDays{ date contributionCount weekday } }
      }
    }
    repositories(first:100, after:$after, ownerAffiliations:OWNER, isFork:false, privacy:PUBLIC){
      pageInfo{ hasNextPage endCursor }
      nodes{
        primaryLanguage{ name }
        languages(first:20, orderBy:{field:SIZE, direction:DESC}){ edges{ size node{ name } } }
      }
    }
  }
}
"""


@dataclass
class Day:
    d: date
    n: int
    wd: int  # 0 = Sunday


@dataclass
class Data:
    total: int
    weeks: list[list[Day]]
    lang_bytes: Counter
    lang_repos: Counter

    @property
    def days(self) -> list[Day]:
        return [d for w in self.weeks for d in w]


def gql(token: str, variables: dict) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={
            "Authorization": f"bearer {token}",
            "User-Agent": "profile-readme-stats",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]


def fetch(login: str, token: str) -> Data:
    after, first = None, None
    lang_bytes, lang_repos = Counter(), Counter()
    while True:
        user = gql(token, {"login": login, "after": after})
        first = first or user["contributionsCollection"]["contributionCalendar"]
        repos = user["repositories"]
        for repo in repos["nodes"]:
            if repo["primaryLanguage"]:
                lang_repos[repo["primaryLanguage"]["name"].lower()] += 1
            for e in repo["languages"]["edges"]:
                lang_bytes[e["node"]["name"].lower()] += e["size"]
        if not repos["pageInfo"]["hasNextPage"]:
            break
        after = repos["pageInfo"]["endCursor"]
    weeks = [
        [Day(date.fromisoformat(d["date"]), d["contributionCount"], d["weekday"])
         for d in w["contributionDays"]]
        for w in first["weeks"]
    ]
    return Data(first["totalContributions"], weeks, lang_bytes, lang_repos)


def mock() -> Data:
    rnd = random.Random(7)
    today = date.today()
    start = today - timedelta(days=364)
    start -= timedelta(days=(start.weekday() + 1) % 7)  # back to Sunday
    weeks, cur, day = [], [], start
    while day <= today:
        burst = 1.0 if (day.month in (1, 2, 5)) else 0.25
        n = rnd.choice([0, 0, 0, 1, 2, 4, 8, 15]) if rnd.random() < burst * 0.5 else 0
        cur.append(Day(day, n, (day.weekday() + 1) % 7))
        if len(cur) == 7:
            weeks.append(cur)
            cur = []
        day += timedelta(days=1)
    if cur:
        weeks.append(cur)
    total = sum(d.n for w in weeks for d in w)
    lb = Counter({"python": 600, "typescript": 210, "javascript": 80, "rust": 60, "liquid": 40})
    lr = Counter({"python": 7, "typescript": 3, "liquid": 1, "rust": 1})
    return Data(total, weeks, lb, lr)


# ------------------------------------------------------------- metrics ----

def streaks(days: list[Day]):
    longest, longest_range, run, run_start = 0, None, 0, None
    for i, d in enumerate(days):
        if d.n > 0:
            if run == 0:
                run_start = d.d
            run += 1
            if run >= longest:
                longest, longest_range = run, (run_start, d.d)
        else:
            run = 0
    # current streak: today may not be finished, so a blank today doesn't break it
    idx = len(days) - 1
    if idx >= 0 and days[idx].n == 0:
        idx -= 1
    cur, cur_start, cur_end = 0, None, None
    while idx >= 0 and days[idx].n > 0:
        cur_end = cur_end or days[idx].d
        cur_start = days[idx].d
        cur += 1
        idx -= 1
    return cur, ((cur_start, cur_end) if cur else None), longest, longest_range


def fmt_day(d: date) -> str:
    return f"{d:%b} {d.day}".lower()


def fmt_range(r) -> str:
    return "—" if not r else f"{fmt_day(r[0])} - {fmt_day(r[1])}"


def level_thresholds(counts: list[int]):
    nz = sorted(c for c in counts if c > 0)
    if not nz:
        return (1, 2, 3)

    def q(p):
        return nz[min(len(nz) - 1, max(0, int(round(p * len(nz) + 0.5)) - 1))]

    return q(0.25), q(0.5), q(0.75)


# ------------------------------------------------------------- graphics ---

def sparkline(values, x0, x1, y_top, y_bot, begin):
    n = len(values)
    mx = max(values) or 1
    pts = [
        (x0 + (x1 - x0) * i / max(1, n - 1), y_bot - (v / mx) * (y_bot - y_top))
        for i, v in enumerate(values)
    ]
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(1, n - 1):
        mx_, my_ = (pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2
        d += f" Q{pts[i][0]:.1f},{pts[i][1]:.1f} {mx_:.1f},{my_:.1f}"
    d += f" L{pts[-1][0]:.1f},{pts[-1][1]:.1f}"
    area = d + f" L{x1:.1f},{y_bot:.1f} L{x0:.1f},{y_bot:.1f} Z"
    end = pts[-1]
    return (
        f'<path class="ar" d="{area}" opacity="0">{fade(begin + 0.8, 0.8)}</path>'
        f'<path class="st" d="{d}" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1">'
        f'<animate attributeName="stroke-dashoffset" from="1" to="0" begin="{begin}s" '
        f'dur="1.6s" fill="freeze"/></path>'
        f'<circle cx="{end[0]:.1f}" cy="{end[1]:.1f}" r="2.5" class="bar" opacity="0">{fade(begin + 1.5, 0.3)}</circle>'
    )


def hero(d: Data) -> str:
    W, H = 480, 140
    week_sums = [sum(x.n for x in w) for w in d.weeks]
    active = sum(1 for x in d.days if x.n > 0)
    best = max(week_sums) if week_sums else 0
    body = "".join([
        text(0, 56, f"{d.total:,}", 56),
        text(2, 76, "contributions in the last year", 10, "m", begin=0.2),
        text(W, 24, f"{active}", 20, anchor="end", begin=0.1),
        text(W, 38, "active days", 9, "m", anchor="end", begin=0.2),
        text(W, 68, f"{best}", 20, anchor="end", begin=0.3),
        text(W, 82, "best week", 9, "m", anchor="end", begin=0.4),
        sparkline(week_sums, 0, W - 4, 96, 130, 0.3),
    ])
    return svg_doc(W, H, body, f"{d.total} contributions in the last year")


def streak_card(d: Data) -> str:
    W, H = 480, 100
    cur, cur_r, lon, lon_r = streaks(d.days)
    body = "".join([
        text(0, 42, f"{cur}", 40),
        text(2, 62, "current streak", 10, "m", begin=0.15),
        text(2, 78, fmt_range(cur_r), 9, "m", begin=0.25),
        f'<line class="ln" x1="240" x2="240" y1="8" y2="88"/>',
        text(270, 42, f"{lon}", 40, begin=0.1),
        text(272, 62, "longest streak", 10, "m", begin=0.25),
        text(272, 78, fmt_range(lon_r), 9, "m", begin=0.35),
    ])
    return svg_doc(W, H, body, f"Current streak {cur} days, longest {lon} days")


def lang_col(x, title, rows, fmt, col_w, begin):
    out = [text(x, 10, title, 9, "m", begin=begin, extra=' letter-spacing="1.5"')]
    top = max((v for _, v in rows), default=1) or 1
    bar_x, bar_max = x + 96, col_w - 96 - 40
    for i, (name, v) in enumerate(rows):
        y = 36 + i * 22
        b = begin + 0.1 + i * 0.08
        w = max(3, bar_max * v / top)
        out.append(text(x, y, name, 11, begin=b))
        out.append(
            f'<rect class="bar" x="{bar_x}" y="{y - 8}" width="0" height="7">'
            f'<animate attributeName="width" from="0" to="{w:.1f}" begin="{b}s" dur="0.9s" fill="freeze"/></rect>'
        )
        out.append(text(x + col_w, y, fmt(v), 11, "m", anchor="end", begin=b))
    return "".join(out)


def langs(d: Data) -> str:
    total = sum(d.lang_bytes.values()) or 1
    by_bytes = [(k, v / total * 100) for k, v in d.lang_bytes.most_common(5)]
    by_repos = d.lang_repos.most_common(5)
    W, col = 620, 270
    n = max(len(by_bytes), len(by_repos), 1)
    H = 36 + n * 22
    body = lang_col(0, "BY BYTES", by_bytes, lambda v: f"{round(v)}%", col, 0.0) + \
        lang_col(W - col, "BY REPOS", by_repos, lambda v: f"{v}", col, 0.15)
    return svg_doc(W, H, body, "Top languages by bytes and by repository count")


def year(d: Data) -> str:
    fs, cw = 8, 8 * ADV
    pitch, x0, y0, rowh = cw * 2.4, 30, 54, 11
    ncols = len(d.weeks)
    W = round(x0 + ncols * pitch + 4)
    H = y0 + 7 * rowh + 22
    counts = [x.n for x in d.days]
    t1, t2, t3 = level_thresholds(counts)
    glyph = {1: ":", 2: "+", 3: "#", 4: "@"}

    def level(n):
        return 0 if n == 0 else 1 if n <= t1 else 2 if n <= t2 else 3 if n <= t3 else 4

    active = sum(1 for c in counts if c > 0)
    out = [
        text(0, 10, "THE YEAR", 8, "m", extra=' letter-spacing="1.5"'),
        text(0, 26, f"{active} of {len(counts)} days had a contribution", 10, "m", begin=0.1),
        f'<text x="{W}" y="26" font-size="9" text-anchor="end" class="m" opacity="0">less : '
        f'<tspan class="l2">+</tspan> <tspan class="l3">#</tspan> <tspan class="l4">@</tspan>  more'
        f'{fade(0.2)}</text>',
    ]
    for r, lab in ((1, "mon"), (3, "wed"), (5, "fri")):
        out.append(text(0, y0 + r * rowh + 7, lab, 8, "m", begin=0.1))

    last_m, last_c = None, -9
    for c, week in enumerate(d.weeks):
        m = week[0].d.month
        if m != last_m and c - last_c >= 3:
            out.append(text(round(x0 + c * pitch, 1), y0 + 7 * rowh + 12, f"{week[0].d:%b}".lower(), 8, "m", begin=0.3))
            last_m, last_c = m, c
        for day in week:
            lv = level(day.n)
            if not lv:
                continue
            g = glyph[lv]
            cls = "l1" if lv == 1 else f"l{lv}"
            out.append(
                f'<text x="{x0 + c * pitch:.1f}" y="{y0 + day.wd * rowh + 8}" font-size="{fs}" '
                f'class="{cls}" opacity="0">{g}{g}{fade(0.3 + c * 0.025, 0.4)}</text>'
            )
    return svg_doc(W, H, "".join(out), f"{active} of {len(counts)} days had a contribution")


def heading(label: str) -> str:
    fs, H = 15, 28
    tw = round(len(label) * ADV * fs)
    body = (
        f'<text x="0" y="19" font-size="{fs}" style="font-weight:700" opacity="0">{esc(label)}{fade(0, 0.5)}</text>'
        f'<line class="ln" x1="{tw + 14}" x2="{CONTENT_W}" y1="13.5" y2="13.5"/>'
    )
    return svg_doc(CONTENT_W, H, body, label)


# ---------------------------------------------------------------- main ----

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", default=os.environ.get("GITHUB_REPOSITORY_OWNER"))
    ap.add_argument("--mock", action="store_true", help="fake data, no network")
    ap.add_argument("--out", default=str(Path(__file__).parent.parent / "assets"))
    a = ap.parse_args()

    if a.mock:
        data = mock()
    else:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not (a.login and token):
            raise SystemExit("need --login and GH_TOKEN (or use --mock)")
        data = fetch(a.login, token)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "hero.svg": hero(data),
        "streak.svg": streak_card(data),
        "langs.svg": langs(data),
        "year.svg": year(data),
    }
    for h in HEADINGS:
        files[f"h-{h.replace(' ', '-')}.svg"] = heading(h)
    for name, svg in files.items():
        p = out / name
        if not p.exists() or p.read_text(encoding="utf-8") != svg:
            p.write_text(svg, encoding="utf-8")
            print("wrote", p)


if __name__ == "__main__":
    main()
