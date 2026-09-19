# Setup (10 minutes)

1. **Create the special repo.** On GitHub: New repository, named *exactly* your username
   (e.g. `octocat/octocat`), public, tick "Add a README". Clone it.
2. **Copy this folder's contents into it** (overwrite README.md).
3. **Add the font.** Put `JetBrainsMono-Regular.ttf` in `scripts/fonts/` (see the txt file there).
4. **Make your portrait** (one-off, run locally):
   ```
   pip install -r requirements.txt
   python scripts/make_portrait.py path/to/photo.jpg --bg-cut 0.15
   # dark / flash-lit photo, face already cropped:
   python scripts/make_portrait.py face_crop.jpg --invert --contrast 0.9 --gamma 3.2 --detail 1.3 --cols 100 --oval 0.97
   ```
   Plain wall behind you? `--bg-cut 0.12`-`0.25` blanks it out so you get a head silhouette.
   Tweak `--cols` (detail), `--contrast`, `--gamma`, `--invert` until you like it.
   `--oval` blanks everything outside a head-shaped ellipse; `--detail` boosts local contrast so eyes and lips show.
5. **Optional token** (so private-repo contributions count in the totals): create a
   classic PAT with only `read:user`, add it as repo secret `STATS_TOKEN`
   (Settings -> Secrets and variables -> Actions).
6. **Generate stats.** Either push and let it run (Actions tab -> `stats` -> *Run workflow*),
   or locally: `GH_TOKEN=... python scripts/build_stats.py --login YOURNAME`.
   No token yet? `python scripts/build_stats.py --mock` gives fake data to preview the layout.
7. **Edit README.md** - swap the placeholders (links, about, projects).
8. Commit and push. Your profile page now shows the README.

Notes
- Colours follow the viewer's OS light/dark setting (prefers-color-scheme), so it looks
  right in both. If someone's GitHub theme differs from their OS theme it can mismatch.
- The action commits with the built-in token, and GitHub pauses scheduled workflows after
  60 days without repo activity. Any push (even a README tweak) un-pauses it.
