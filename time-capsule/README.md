# Discourse Dial

Timeline slider + search interface for LDS General Conference talks (1850–present).

## Updating Talk Data

To refresh the data files in `data/unified/`:

1. Run the merge script: `python3 ~/conference-reports/merge-corpus.py`
2. Copy the output: `cp ~/conference-reports/unified/*.json time-capsule/data/unified/`
3. Regenerate the index: run the Python snippet from the corpus root

## Architecture

Pure static site (HTML/CSS/JS) — no build step. Data loads on-demand per year.
Prophet timeline is hardcoded in `app.js`.

## Source Files

- `index.html` — page template (matches site's subpage layout)
- `app.js` — all logic: slider, prophet cards, chat/search, talk detail overlay
- `styles.css` — page-specific styles
- `data/unified/` — per-year JSON files + `index.json` (lightweight metadata)
