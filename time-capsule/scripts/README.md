# Scripts — LDS Magazine Text Pipeline

Scripts for downloading LDS magazines from the Church History Catalog and extracting text.

## The Contributor (1879–1896)

Source: https://catalog.churchofjesuschrist.org/record/e8400534-f7af-41e4-a5aa-0f9866a49cbf/0?view=browse

~204 monthly issues across 17 volumes.

### Pipeline overview

**Phase 1 — Metadata + PDF GUID extraction**
- `extract_pdf_guids.py` — navigate browse pages + asset viewer pages using Playwright.
- `update_guids.py` — manual patch script for remaining entries (used to fill gaps from bot-detection timeouts).
- `find_missing.py` — diagnostic to cross-reference GUIDs vs metadata.

⚠️ **Bot detection:** The catalog blocks headless Playwright on the asset viewer pages.
For bulk extraction, use the Hermes browser tool (which runs in a visible browser)
to open each asset viewer page and extract the PDF delivery GUID from the
`<object id="pdf-viewer">` element's `data` attribute.

Output: `data/contributor/issues_metadata.json` and `data/contributor/pdf_guids.json`

**Phase 2 — Download + text extraction**
- `download_pdfs.py` — curl-based bulk download using session cookies, then extract
  text with PyMuPDF (fitz). Includes checkpoint/resume via `download_state.json`.
  **Does not need Playwright** — only works if `pdf_guids.json` is already populated.

Output: `data/contributor/*.txt` (204 files, ~35 MB total)

### Pre-requisites

```
pip install playwright PyMuPDF
playwright install chromium
```

### Fresh session cookies

The Church History Catalog delivery API requires session cookies. Get them from
an authenticated browser session on catalog.churchofjesuschrist.org:

1. Open DevTools → Application → Cookies → https://catalog.churchofjesuschrist.org
2. Copy values for: `XSRF-TOKEN`, `at_check`, `TAsessionID`
3. Paste them into the `COOKIES` dict at the top of `download_pdfs.py` or `contributor-pipeline.py`

Cookies expire after ~30 minutes of inactivity. If downloads start failing, refresh them.

### Tracing the actual production run

The production run used:
1. Hermes browser tool (visible browser) to open 204 asset viewer pages and extract PDF GUIDs
2. `update_guids.py` to patch 14 remaining entries
3. `download_pdfs.py` to download all 204 PDFs and extract text (~5 min for downloads)

All 204 issues had digitized PDFs. October 1879 (Vol 1, No 1) is not digitized
— the recorded text file is 0 bytes.

---

## The Improvement Era (1897–1970)

Source: Internet Archive (`collection: improvementera`)

882+ issues across 73 volumes. Succeeded The Contributor in 1897 and ran until
1970 when it was replaced by The Ensign.

### Pipeline overview

**`improvement_era_pipeline.py`** — one script, three stages:
1. Fetch all 879 identifiers from the archive.org search API
2. Download each PDF via direct curl (no auth, no Playwright)
3. Extract text with PyMuPDF (`sort=True`) and reflow columns

Key features:
- **Resume support** via `pipeline_state.json` (safe to Ctrl+C and restart)
- **No Playwright** — archive.org serves plain PDFs at predictable URLs
- **No cookies** — archive.org doesn't require session auth for downloads
- **Low disk** — deletes each PDF after extraction (~3-11 MB per file)

**`articles_to_json_ie.py`** — converts per-issue `.txt` files to per-issue
`.json` files with metadata from the archive.org API:

```json
{
  "date": "1933-05",
  "source": "The Improvement Era",
  "filename": "improvementera3607unse",
  "volume": "36",
  "number": "7",
  "text": "...full issue body text..."
}
```

### Results

| Metric | Value |
|--------|-------|
| Issues processed | 874 / 879 (4 with no PDFs) |
| Total text | 244 MB / 244M chars |
| Avg per issue | ~279K chars |
| Runtime | ~118 min (sequential) |

### Identifier naming

Archive.org identifiers for this collection follow an inconsistent pattern:
- `improvementera0401unse` — most common: `{vol:02d}{no:02d}` (vol 4 onward)
- `improvementera11unse` — early years: `{vol}{no}` (vol 1-3)
- `improvementera10010unse` — issue ≥10 in some volumes: `{vol:02d}{no:02d}d`
- `improvementera33unse` — single-issue volumes (no PDFs exist)

The pipeline handles all variants automatically via the archive.org API.

### Pre-requisites

```
pip install PyMuPDF
```
