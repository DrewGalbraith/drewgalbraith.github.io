# Improvement Era — extracted text data (1897–1970)

Extracted text from **874 issues** of **The Improvement Era**, the successor to
The Contributor and the primary Church magazine for over 70 years.

**Source:** Internet Archive (`collection:improvementera`)

## Contents

| File | Description |
|------|-------------|
| `*.txt` (874 files) | Reflowed PyMuPDF text extraction (~235 MB total) |
| `pipeline_log.txt` | Full pipeline execution log |

## Coverage

- **Vol 1, No 1** (Nov 1897) — **Vol 73, No 12** (Dec 1970)
- 874 of 879 archive.org identifiers (5 had no downloadable PDF)
- No gaps in the monthly publishing run

## Format

Each `.txt` file is named by its archive.org identifier:
`improvementera{vol}{no}unse.txt`

Text has been:
1. Extracted via PyMuPDF (`page.get_text("text", sort=True)`)
2. Reflowed: column interleaving fixed, dehyphenation, running headers removed
3. OCR artifacts cleaned (`^`, `ˆ`, `˜`, lone underscores, non-printable chars)
4. Cover/masthead garbage stripped

Minor OCR artifacts remain (especially in 1897–1910 volumes) — these are
embedded-PDF extraction imperfections, not full OCR failures. Suitable for
LLM consumption.

## Per-issue JSON

Structured JSON with archive.org metadata is in `../improvement_era_json/`:

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

Date, volume, and issue number come from archive.org's own metadata.

## Reproduction

See `scripts/README.md` for the full pipeline.
