#!/usr/bin/env python3
"""
Pipeline: Download, extract, and reflow The Improvement Era (1897-1970).

Reads all issue identifiers from archive.org, downloads PDFs, extracts text
with PyMuPDF, cleanly reflows columns, and saves per-issue .txt files.

Usage:
    python3 improvement_era_pipeline.py [output_dir]

Output structure:
    {output_dir}/
      improvement_era_text/
        improvementera11unse.txt
        improvementera12unse.txt
        ...
      pipeline_state.json     # for resume support
      identifiers.txt         # all issue IDs
"""

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────────

OUTPUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("ie_data")
TEXT_DIR = OUTPUT_DIR / "improvement_era_text"
STATE_FILE = OUTPUT_DIR / "pipeline_state.json"
ID_FILE = OUTPUT_DIR / "identifiers.txt"
LOG_FILE = OUTPUT_DIR / "pipeline.log"

PDF_BASE = "https://archive.org/download/{id}/{id}.pdf"
MAX_RETRIES = 3
RETRY_DELAY = 5
REQUEST_TIMEOUT = 120
LOG_INTERVAL = 25  # log progress every N issues

# ── Text cleanup patterns (adapted from reflow_text.py with Improvement Era specifics) ──

DEHYPHEN_RE = re.compile(r"(\w{2,})-[\s\n]*(\w{2,})")

# Lines to drop entirely
HEADER_LINES = {
    "THE IMPROVEMENT ERA.",
    "IMPROVEMENT ERA",
    "THE IMPROVEMENT ERA",
    "IMPROVEMENT ERA.",
    "CONTENTS",
    "CONTENTS.",
    "INDEX",
    "INDEX.",
}
PAGE_NUM_RE = re.compile(r"^\s*\d{1,4}\s*$")
PAGE_ORPHAN_RE = re.compile(r"^\d+\s*['•*\"']+\s*$")
SYMBOL_LINE_RE = re.compile(r"^[\s•*\"'˜ˆ¨°©®™±≈<>|/\\,;:!?@#$%^&+=~`_\[\]{}()—–-]+$")
VOL_ISSUE_RE = re.compile(r"^(Vol\.|VOL\.|No\.|No|Volume|VOLUME)\s*\d+.*$", re.IGNORECASE)
SHORT_NOISE_RE = re.compile(r"^[\s\d•·*\"'˜ˆ¨°©®™±≈<>|/\\,;:!?@#$%^&+=~`_\[\]{}()—–-]+\.?\s*$")

# OCR artifacts specific to Improvement Era PDFs
OCR_ARTIFACT_RE = re.compile(r"[^a-zA-Z0-9\s.,;:!?'\"()\-—–/&@#$%+*=<>\[\]{}|\\\u2018\u2019\u201c\u201d\u2013\u2014]")

SENTENCE_END_RE = re.compile(r"[.!?:;—•·]")
ABBREV_RE = re.compile(r"^(Mr|Mrs|Dr|Ms|St|Jr|Sr|vs|etc|vol|pp|pg|eds|Rev|Capt|Gen|Col|Gov|Pres|Sec|Prof|Dept|Ave|Bldg)\b\.?$", re.IGNORECASE)

HEADING_RE = re.compile(r"^[A-Z][A-Z\s.]{2,60}$")
TITLE_CASE_HEADING_RE = re.compile(r"^[A-Z][a-z]+ [A-Z][a-z]+\.?$")

BULLET_RE = re.compile(r"^[—–•·\-*\s]+$")
LIST_ITEM_RE = re.compile(r"^\d+[\.:\)]\s*$")


def log(msg):
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")


def log_error(msg):
    log(f"[ERROR] {msg}")


def download_pdf(identifier, dest_path):
    """Download a PDF from archive.org with retries. Returns True on success."""
    url = PDF_BASE.format(id=identifier)
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; LDS-corpus-builder/1.0)"
            })
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                with open(dest_path, "wb") as f:
                    f.write(resp.read())
            return True
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
    return False


def extract_text(pdf_path):
    """Extract text from PDF using PyMuPDF."""
    try:
        import fitz
    except ImportError:
        log_error("PyMuPDF (fitz) not installed. Run: pip install PyMuPDF")
        return ""

    doc = fitz.open(pdf_path)
    text_pages = []
    for page in doc:
        txt = page.get_text("text", sort=True)
        text_pages.append(txt)
    doc.close()
    return "\n".join(text_pages)


def clean_ocr_artifacts(text):
    """Remove common OCR artifacts specific to these magazine PDFs."""
    # Remove caret/circumflex artifacts (common in vol 1-30 issues)
    text = re.sub(r'[\^ˆ]', '', text)
    # Remove lone underscores
    text = re.sub(r'_\s*', ' ', text)
    # Remove tilde artifacts
    text = re.sub(r'[˜~]', '', text)
    # Remove other non-printable / weird chars
    text = OCR_ARTIFACT_RE.sub('', text)
    # Collapse multiple spaces
    text = re.sub(r' +', ' ', text)
    return text


def should_drop_line(s):
    """Check if a line should be removed entirely."""
    if not s.strip():
        return False
    s_stripped = s.strip()
    if s_stripped in HEADER_LINES:
        return True
    if PAGE_NUM_RE.match(s_stripped):
        return True
    if PAGE_ORPHAN_RE.match(s_stripped):
        return True
    if SYMBOL_LINE_RE.match(s_stripped):
        return True
    if VOL_ISSUE_RE.match(s_stripped):
        return True
    if BULLET_RE.match(s_stripped):
        return True
    if SHORT_NOISE_RE.match(s_stripped) and len(s_stripped) < 5:
        return True
    return False


def is_heading_line(s):
    """Check if a line looks like a section heading."""
    if not s.strip():
        return False
    s_stripped = s.strip()
    if HEADING_RE.match(s_stripped) and "  " not in s_stripped:
        return True
    if TITLE_CASE_HEADING_RE.match(s_stripped) and len(s_stripped) < 40:
        return True
    return False


def reflow_text(text):
    """Re-flow paragraph text and apply cleanups."""
    # Step 0: Clean OCR artifacts first
    text = clean_ocr_artifacts(text)

    # Step 1: Dehyphenate
    text = DEHYPHEN_RE.sub(r"\1\2", text)

    lines = text.split("\n")

    # Step 2: Filter out header/noise lines
    meaningful = []
    for line in lines:
        s = line.strip()
        if should_drop_line(s):
            continue
        meaningful.append(line)

    # Step 3: Re-flow lines into paragraphs
    paragraphs = []
    current_para = []
    prev_was_blank = True

    for line in meaningful:
        s = line.strip()

        if not s:
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
            prev_was_blank = True
            continue

        if prev_was_blank and is_heading_line(s):
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
            paragraphs.append(s)
            prev_was_blank = False
            continue

        if current_para:
            prev_line = current_para[-1].strip()

            if SENTENCE_END_RE.search(prev_line) and len(prev_line) > 10:
                paragraphs.append(" ".join(current_para))
                current_para = [s]
            elif ABBREV_RE.match(prev_line):
                current_para.append(s)
            elif s and s[0].isupper() and len(s) > 3 and not s[0].isdigit():
                if len(prev_line) < 30 and not prev_line.endswith((".", "!", "?")):
                    current_para.append(s)
                elif LIST_ITEM_RE.match(s):
                    paragraphs.append(" ".join(current_para))
                    current_para = [s]
                else:
                    paragraphs.append(" ".join(current_para))
                    current_para = [s]
            else:
                current_para.append(s)
        else:
            current_para.append(s)

        prev_was_blank = False

    if current_para:
        paragraphs.append(" ".join(current_para))

    # Step 4: Clean up each paragraph
    cleaned = []
    for para in paragraphs:
        para = re.sub(r" +", " ", para)
        para = re.sub(r"\s+([,;:.!?])", r"\1", para)
        para = re.sub(r'(["\'„]) ', r"\1", para)
        para = para.replace(" —", "—").replace("— ", "—")
        # Remove leading/trailing whitespace
        para = para.strip()
        if para:
            cleaned.append(para)

    return "\n\n".join(cleaned)


def get_identifiers():
    """Get list of all Improvement Era issue identifiers from archive.org API."""
    log("Fetching identifiers from archive.org API...")
    url = ("https://archive.org/advancedsearch.php"
           "?q=collection:improvementera"
           "&fl=identifier"
           "&rows=900"
           "&page=1"
           "&output=json")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        ids = sorted(d["identifier"] for d in data["response"]["docs"])
        log(f"Found {len(ids)} identifiers")
        return ids
    except Exception as e:
        log_error(f"Failed to fetch identifiers: {e}")
        sys.exit(1)


def load_state():
    """Load pipeline state for resume support."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"completed": [], "failed": [], "in_progress": None}


def save_state(state):
    """Save pipeline state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def main():
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Get identifiers
    ids = get_identifiers()

    # Save identifier list
    with open(ID_FILE, "w") as f:
        for i in ids:
            f.write(i + "\n")

    # Load state
    state = load_state()
    completed = set(state["completed"])
    failed = set(state["failed"])

    log(f"Total issues: {len(ids)}")
    log(f"Already completed: {len(completed)}")
    log(f"Previously failed: {len(failed)}")
    log(f"Remaining: {len(ids) - len(completed) - len(failed)}")

    start_time = time.time()
    processed_count = 0

    for idx, identifier in enumerate(ids):
        if identifier in completed or identifier in failed:
            continue

        state["in_progress"] = identifier

        txt_path = TEXT_DIR / f"{identifier}.txt"

        # ── Download PDF ──
        pdf_path = OUTPUT_DIR / f"{identifier}.pdf"
        log(f"[{idx+1}/{len(ids)}] Downloading {identifier}...")

        if not download_pdf(identifier, pdf_path):
            log_error(f"Failed to download {identifier}")
            failed.add(identifier)
            state["failed"] = list(failed)
            state["in_progress"] = None
            save_state(state)
            continue

        # ── Extract text ──
        log(f"  Extracting text...")
        raw_text = extract_text(pdf_path)
        if not raw_text.strip():
            log_error(f"Empty text for {identifier}, skipping")
            failed.add(identifier)
            os.remove(pdf_path)
            state["failed"] = list(failed)
            state["in_progress"] = None
            save_state(state)
            continue

        # ── Reflow ──
        cleaned_text = reflow_text(raw_text)

        # ── Save ──
        txt_path.write_text(cleaned_text, encoding="utf-8")

        # ── Delete PDF to save space ──
        os.remove(pdf_path)

        # ── Update state ──
        completed.add(identifier)
        state["completed"] = list(completed)
        state["failed"] = list(failed)
        state["in_progress"] = None
        save_state(state)
        processed_count += 1

        chars = len(cleaned_text)
        log(f"  ✓ {chars:,} chars saved to {txt_path.name}")

        # Log progress summary periodically
        if processed_count > 0 and processed_count % LOG_INTERVAL == 0:
            elapsed = time.time() - start_time
            rate = processed_count / (elapsed / 60)
            remain = len(ids) - len(completed) - len(failed)
            eta = remain / rate if rate > 0 else 0
            log(f"\n{'─'*50}")
            log(f"Progress: {len(completed)}/{len(ids)} completed, "
                f"{len(failed)} failed, {remain} remaining")
            log(f"Rate: {rate:.1f} issues/min | ETA: {eta:.0f} min")
            log(f"{'─'*50}\n")

    # Final summary
    elapsed = time.time() - start_time
    log(f"\n{'='*50}")
    log(f"Pipeline complete!")
    log(f"  Total: {len(ids)} issues")
    log(f"  Completed: {len(completed)}")
    log(f"  Failed: {len(failed)}")
    log(f"  Time: {elapsed:.0f}s ({elapsed/60:.1f} min)")
    log(f"  Output: {TEXT_DIR}")
    log(f"{'='*50}")


if __name__ == "__main__":
    main()
