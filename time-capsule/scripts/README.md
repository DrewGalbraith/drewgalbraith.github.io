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
