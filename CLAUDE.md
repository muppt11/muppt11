# Project: GitHub profile README (generated graphics)

This repo is my special profile repo (`<username>/<username>`), so README.md renders on my
GitHub profile. Every graphic is a generated SVG - nothing is embedded from a third party.

## Layout
- `README.md` - profile page. Section headings and all graphics are `<img>` tags pointing at `assets/`.
- `scripts/svgkit.py` - shared helpers: subsets + inlines JetBrains Mono as base64, light/dark theme CSS, SVG wrapper.
- `scripts/make_portrait.py` - photo -> `assets/ascii.svg` (character-ramp portrait). Run by hand, not in CI.
- `scripts/build_stats.py` - GitHub GraphQL -> `assets/{hero,streak,langs,year}.svg` + `assets/h-*.svg` headings.
- `.github/workflows/stats.yml` - runs build_stats.py daily, commits `assets/` only if it changed.
- `scripts/fonts/JetBrainsMono-Regular.ttf` - REQUIRED, must be committed (CI embeds it). Not in the kit; see fonts/README.txt.
- `source/` - my raw photo. Gitignored on purpose. Never commit it.

## Commands
```
pip install -r requirements.txt
python scripts/build_stats.py --mock                     # offline preview, fake data
GH_TOKEN=... python scripts/build_stats.py --login NAME  # real data
python scripts/make_portrait.py source/face_crop.jpg --invert --contrast 0.9 --gamma 1.4 --detail 0.8 --cols 140 --oval 0.95
```
Portrait flags: `--cols` detail, `--invert` bright=dense, `--gamma/--contrast` tone, `--detail` local
contrast (eyes/lips), `--oval` blank outside a head-shaped ellipse, `--bg-cut` blank the background colour.

## Hard constraints - do not break these
- Output must be DETERMINISTIC: no timestamps, no random values. The workflow commits only on real diffs.
- Nothing loads from a third party: no remote images, fonts, scripts. Font is base64 inlined.
- GitHub strips scripts and CSS from README markup, so styling lives INSIDE the SVGs. Animation is SMIL only.
- JetBrains Mono advance width is exactly 0.600 em (ADV in svgkit.py); layouts depend on it. Ligatures are
  stripped from the font subset so `::` in the heatmap and portrait doesn't merge.
- Colours come from CSS variables in svgkit.THEME (light + dark via prefers-color-scheme). Use classes, not
  `var()` in presentation attributes.
- Every SVG must parse as XML. Validate after changes: `python -c "import glob,xml.etree.ElementTree as E;[E.parse(f) for f in glob.glob('assets/*.svg')]"`
- Language stats cover public repos only.

## Working style
- Ask before pushing, and before touching anything under `.github/`.
- There is no SVG renderer in some environments; to eyeball a portrait, render its text rows with PIL, or open the SVG in a browser.
- Don't use `--bg-cut` on face_crop.jpg: it samples all four corners, but the bottom two are shoulders
  (lum ~110) not background (lum ~10), so the median lands on the hair (~60) and blanks the hair.
- Keep gamma near 1.0. High gamma crushes the hair band to blank and leaves the face as one solid slab.
- The portrait source is a small, dark, flash-lit photo, so results are blobby. A brighter, closer, front-lit photo would help; don't over-tune.
