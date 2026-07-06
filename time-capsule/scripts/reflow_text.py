#!/usr/bin/env python3
"""
Re-flow two-column PDF extracted text from The Contributor.

The core problem: PyMuPDF extracts each column line-by-line, producing
fragmented text like:

    In mercantile
    pursuits, the
    proprietor
    of an establishment

...when the actual text is "In mercantile pursuits, the proprietor of an establishment."

This script:
  1. Re-joins lines that clearly belong together (mid-sentence breaks)
  2. Preserves intentional paragraph breaks (blank lines, indented starts)
  3. Then applies the standard cleanups: dehyphenation, header removal, etc.

Strategy:
  - A line that does NOT end with sentence-ending punctuation (.!?:;—)
    AND the next line starts with lowercase → join them.
  - A blank line signals a paragraph break → preserve it.
  - Short lines (1-2 words) that start with lowercase are aggressively joined
    to the previous line.

Usage:
  python3 reflow_text.py [input_dir] [output_dir]

  Default: runs in-place on data/contributor/
  Pass a second path for a safety copy.
"""

import re
import sys
from pathlib import Path

# ── Patterns ────────────────────────────────────────────────────────────

# Dehyphenate: word-\nword → wordword
DEHYPHEN_RE = re.compile(r"(\w{2,})-\n(\w{2,})")

# Running headers to drop
HEADER_LINES = {
    "THE CONTRIBUTOR.",
    "THE CONTRIBUTOR :",
    "CONTENTS.",
    "CONTENTS",
}

# Page number lines
PAGE_NUM_RE = re.compile(r"^\d{1,4}$")
PAGE_ORPHAN_RE = re.compile(r"^\d+\s*['•*\" ]+$")
SYMBOL_LINE_RE = re.compile(r"^[\s•*\"\'˜ˆ¨°©®™±≈<>|/\\,;:!?@#$%^&+=~`_\[\]{}()—–-]+$")
VOL_ISSUE_RE = re.compile(r"^(Vol\.|VOL\.|No\.|No|Volume|VOLUME)\s*\d+.*$", re.IGNORECASE)

# Detect if a line looks like it ends a sentence naturally
SENTENCE_END_RE = re.compile(r"[.!?:;—•·]$")
# Detect if a line is an abbreviation (Mr., Mrs., Dr., etc.)
ABBREV_RE = re.compile(r"^(Mr|Mrs|Dr|Ms|St|Jr|Sr|vs|etc|vol|pp|pg|eds)\.$", re.IGNORECASE)
# Detect "p." or "pp." (page references)
PAGE_REF_RE = re.compile(r"^[Pp]p?\.$")

# Detect if a line looks like a heading (ALL CAPS or Title Case heading)
HEADING_RE = re.compile(r"^[A-Z][A-Z\s]{3,}$")
TITLE_CASE_HEADING_RE = re.compile(r"^[A-Z][a-z]+[. ]*$")

# A line that's just a number with a period or colon (list items like "1.")
LIST_ITEM_RE = re.compile(r"^\d+[\.:\)]\s*$")
# A line that's just a dash or bullet
BULLET_RE = re.compile(r"^[—–•·\-*]\s*$")


def is_heading_line(s: str) -> bool:
    """Check if a line looks like a section heading."""
    if not s:
        return False
    # Short all-caps (2-6 words), possibly with period
    if re.match(r"^[A-Z][A-Z\s.]{2,60}$", s) and "  " not in s:
        return True
    # Title case short lines that are standalone (not part of a sentence)
    if re.match(r"^[A-Z][a-z]+ [A-Z][a-z]+\.?$", s) and len(s) < 40:
        return True
    return False


def should_drop_line(s: str) -> bool:
    """Check if a line should be removed entirely."""
    if not s:
        return False
    if s in HEADER_LINES:
        return True
    if PAGE_NUM_RE.match(s):
        return True
    if PAGE_ORPHAN_RE.match(s):
        return True
    if SYMBOL_LINE_RE.match(s):
        return True
    if VOL_ISSUE_RE.match(s):
        return True
    if BULLET_RE.match(s):
        return True
    return False


def reflow_text(text: str) -> str:
    """Re-flow paragraph text and apply cleanups."""

    # Step 0: Dehyphenate first (before line-level processing)
    text = DEHYPHEN_RE.sub(r"\1\2", text)

    lines = text.split("\n")

    # Step 1: Filter out header/noise lines and collect meaningful lines
    meaningful = []
    for line in lines:
        s = line.strip()
        if should_drop_line(s):
            continue
        meaningful.append(line)

    # Step 2: Re-flow lines into paragraphs
    # The strategy:
    #   Walk through lines. If a line does NOT end a thought and the next
    #   line is a continuation, join them with a space.
    #   A blank line is always a hard paragraph break.

    paragraphs = []
    current_para = []
    prev_was_blank = True  # start fresh

    for line in meaningful:
        s = line.strip()

        if not s:
            # Blank line = paragraph break
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
            prev_was_blank = True
            continue

        if prev_was_blank and is_heading_line(s):
            # New heading — flush previous paragraph, start new one
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
            paragraphs.append(s)
            prev_was_blank = False
            continue

        # Determine if this line should join with the previous one
        if current_para:
            prev_line = current_para[-1].strip()

            # Check if previous line ends a sentence naturally
            if SENTENCE_END_RE.search(prev_line):
                # Hard break — previous sentence is complete
                paragraphs.append(" ".join(current_para))
                current_para = [s]
            elif ABBREV_RE.match(prev_line) or PAGE_REF_RE.match(prev_line):
                # Abbreviation — join (don't break after "Mr." etc.)
                current_para.append(s)
            elif s[0].isupper() and len(s) > 3 and not s[0].isdigit():
                # Next line starts with capital and isn't a short throwaway
                # Could be a new sentence — check if it's likely continuance
                if len(prev_line) < 30 and not prev_line.endswith((".", "!", "?")):
                    # Short previous line + no sentence end = continuance
                    current_para.append(s)
                elif LIST_ITEM_RE.match(s):
                    # Numbered list item — paragraph break
                    paragraphs.append(" ".join(current_para))
                    current_para = [s]
                else:
                    # Likely a new sentence — paragraph break
                    paragraphs.append(" ".join(current_para))
                    current_para = [s]
            else:
                # Next line starts lowercase — definitely a continuation
                current_para.append(s)
        else:
            current_para.append(s)

        prev_was_blank = False

    # Flush last paragraph
    if current_para:
        paragraphs.append(" ".join(current_para))

    # Step 3: Clean up each paragraph
    cleaned = []
    for para in paragraphs:
        # Remove extra spaces within the paragraph
        para = re.sub(r" +", " ", para)
        # Remove space before punctuation
        para = re.sub(r"\s+([,;:.!?])", r"\1", para)
        # Remove space after opening quotes
        para = re.sub(r'("|\'|„) ', r"\1", para)
        # Clean up space around em-dashes
        para = para.replace(" —", "—").replace("— ", "—")
        cleaned.append(para)

    return "\n\n".join(cleaned)


def main():
    if len(sys.argv) > 1:
        in_dir = Path(sys.argv[1])
    else:
        in_dir = Path("data/contributor")

    if len(sys.argv) > 2:
        out_dir = Path(sys.argv[2])
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = in_dir

    txt_files = sorted(in_dir.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in {in_dir}")
        sys.exit(1)

    total_before = 0
    total_after = 0

    for path in txt_files:
        before = path.read_text(encoding="utf-8", errors="replace")
        if not before.strip():
            print(f"  {path.name}: (empty, skipped)")
            continue

        total_before += len(before)
        after = reflow_text(before)
        total_after += len(after)

        if out_dir == in_dir:
            path.write_text(after, encoding="utf-8")
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / path.name).write_text(after, encoding="utf-8")

        saved = len(before) - len(after)
        pct = saved / len(before) * 100 if before else 0
        print(f"  {path.name}: {saved:>7,} chars removed ({pct:.0f}%)  "
              f"{len(before):,} → {len(after):,}")

    print(f"\nTotal: {total_before:,} → {total_after:,} chars "
          f"({total_before - total_after:,} removed)")


if __name__ == "__main__":
    main()
