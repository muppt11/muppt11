Paste this as your first message in Claude Code:

---
Read CLAUDE.md and SETUP.md first. This repo is my GitHub profile README repo; get my username
from `git remote -v`. Work through this in order and pause where I need to act:

1. Check `scripts/fonts/JetBrainsMono-Regular.ttf` exists. If not, try to fetch it from the official
   JetBrains Mono release (OFL licensed). If you can't, tell me exactly which file to download and where to put it.
2. `pip install -r requirements.txt`.
3. Run `python scripts/build_stats.py --mock`, validate every SVG in assets/ parses as XML, and confirm the
   font is embedded (no "font not found" warning).
4. Generate my portrait from `source/face_crop.jpg` with the command in CLAUDE.md, and show me how it looks
   (render the text rows to a PNG with PIL if you can't open an SVG). Tune if it's clearly bad, but don't over-fiddle.
5. Ask me for my name, one-line bio, links (site, instagram, linkedin, email), tools, and projects, then fill in
   README.md. Remove every placeholder.
6. Show me `git status`. With my OK, commit everything (source/ must stay untracked) and push.
7. Walk me through creating the optional `STATS_TOKEN` secret, then trigger the `stats` workflow and check it
   succeeded. If it fails, read the logs and fix it.
---
