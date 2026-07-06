# Contributor — extracted text data

Extracted text from all 204 issues of **The Contributor** (1879–1896).

**Source:** https://catalog.churchofjesuschrist.org/record/e8400534-f7af-41e4-a5aa-0f9866a49cbf/0?view=browse

## Contents

| File | Description |
|------|-------------|
| `*.txt` (204 files) | Extracted text from each issue's PDF (~35 MB total) |
| `issues_metadata.json` | All 204 issue titles and asset GUIDs |
| `pdf_guids.json` | Asset GUID → PDF delivery GUID mapping |
| `pipeline_state.json` | Final pipeline state (done + skipped sets) |

## Format

Each `.txt` file is named by issue: `"Year Month (No N).txt"`. The text is
raw PyMuPDF extraction — includes typical PDF artifacts (hyphenated line breaks,
headers/footers, page numbers). Suitable for LLM consumption without heavy cleanup.

## Skipped issues

October 1879 (Vol 1, No 1) — not digitized in the catalog. File is 0 bytes.

## Original source

The digital collection is hosted by the Church History Library at:
https://catalog.churchofjesuschrist.org/record/e8400534-f7af-41e4-a5aa-0f9866a49cbf/0?view=browse

## Reproduction

See `scripts/README.md` for the full pipeline.
