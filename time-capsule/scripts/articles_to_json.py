#!/usr/bin/env python3
"""
Split The Contributor issue text into per-article JSON entries.

How it works:
  1. Find the masthead region ("Vol. X. MONTH, YEAR.") that separates
     TOC/ads from actual article content. Everything before is discarded.
  2. Within the content body, detect article boundaries at ALL-CAPS
     title lines (several heuristics filter out ad/masthead noise).
  3. Sections with the same title are merged (page header repeats).
  4. Author names are extracted from the line immediately after the title.
  5. Each issue → one JSON file.

Usage:
  python3 articles_to_json.py [input_dir] [output_dir]
"""

import json
import re
import sys
from pathlib import Path

MONTHS = {
    "JANUARY": "01", "FEBRUARY": "02", "MARCH": "03", "APRIL": "04",
    "MAY": "05", "JUNE": "06", "JULY": "07", "AUGUST": "08",
    "SEPTEMBER": "09", "OCTOBER": "10", "NOVEMBER": "11", "DECEMBER": "12",
}

MONTH_NAMES = {n.lower(): n for n in MONTHS}


def parse_date(filename: str) -> str:
    m = re.match(r"(\d{4})\s+(\w+)", filename)
    if m:
        month = MONTHS.get(m.group(2).upper())
        if month:
            return f"{m.group(1)}-{month}"
    return filename[:7]


# ── Masthead / content start ────────────────────────────────────────────


def find_content_start(text: str) -> tuple[int, dict]:
    """
    Find where actual article content begins by locating the masthead:
      Vol. X.
      MONTH, YYYY.
      No. N.
    Returns (char_offset, metadata_dict).
    """
    # Pattern: Vol. on its own line, then month/year, then No.
    lines = text.split("\n")
    meta = {}

    for i, line in enumerate(lines):
        s = line.strip()
        # Match "Vol." (possibly with roman numeral)
        vm = re.match(r"^(VOL|Vol)\.?\.?\s*([IVXLCDM]+)", s, re.IGNORECASE)
        if not vm:
            continue

        vol = vm.group(2)
        # Look ahead for month/year and No.
        month_name = None
        year_str = None
        no_str = None

        for j in range(i + 1, min(i + 12, len(lines))):
            ss = lines[j].strip()
            # Month, YYYY
            mm = re.match(r"^(\w+),?\s+(\d{4})", ss)
            if mm and mm.group(1).upper() in MONTHS:
                month_name = mm.group(1).upper()
                year_str = mm.group(2)
                continue
            # No. N  (also matches bare "N." or "N" on its own line)
            nm = re.match(r"^(?:NO|No)\.?\s*(\d+)", ss, re.IGNORECASE)
            if not nm:
                nm = re.match(r"^(\d+)\.?$", ss)
            if nm:
                no_str = nm.group(1)
                continue

        if month_name and year_str:
            meta = {
                "volume": vol,
                "month": month_name.title(),
                "year": year_str,
                "number": no_str or "",
            }
            # Start content just after this masthead block
            content_start = i
            return content_start, meta

    # Fallback: try "CONTENTS FOR MONTH, YEAR."
    for i, line in enumerate(lines):
        cm = re.match(r"CONTENTS FOR (\w+),?\s+(\d{4})", line, re.IGNORECASE)
        if cm and cm.group(1).upper() in MONTHS:
            # Content starts after the contents section
            return i, {"month": cm.group(1).title(), "year": cm.group(2)}

    return 0, {}


# ── Title detection ─────────────────────────────────────────────────────

# A real article title: standalone ALL-CAPS line ending with period
TITLE_RE = re.compile(r"^[A-Z][A-Z .\"'!?,\-:;()&/\d]{3,79}\.$")

SKIP_TITLES = {
    "THE CONTRIBUTOR.", "THE CONTRIBUTOR :",
    "CONTENTS.", "CONTENTS",
    "THE GLORY OF GOD IS INTELLIGENCE.",
    "A MONTHLY MAGAZINE OF HOME LITERATURE.",
    "PAGE.", "PAGE",
}

BAD_PREFIX = (
    "VOL.", "NO.", "PAGE", "ESTABLISHED", "ENTERED AT",
    "COPYRIGHT", "PRINTED", "PUBLISHED", "DIRECTORS:",
    "CAPITAL", "SURPLUS",
)

BAD_PATTERNS = [
    re.compile(r"^[A-Z\s]{25,}$"),                # very long = masthead
    re.compile(r"^[A-Z. ]+(CO\.|BRO\.|& SON|& SONS)\s*\.?$"),  # companies
    re.compile(r"^[A-Z ]+(DEPT|COMPANY|CORPORATION|ASSOCIATION|SOCIETY|BANK|TRUST|INSURANCE)"),
    re.compile(r"^[A-Z ]+ (LUMBER|FURNITURE|HARDWARE|DRY GOODS|GROCERY|MILL|PRESS)"),
    re.compile(r"^(ILLUSTRATED|SEND FOR|PRICE|CENTS|SAMPLES|CIRCULARS)"),
    re.compile(r".*\d{3,}.*"),                    # has 3+ digits in a row
    re.compile(r"^[A-Z .]+\)"),                   # closing paren = ad
    re.compile(r"YOU WILL FIND", re.IGNORECASE),  # ad language
    re.compile(r"\bMAIL ORDERS?\b", re.IGNORECASE),     # mail-order ads
    re.compile(r"\bCATALOG(UE)?\b", re.IGNORECASE),
    re.compile(r"\b(FUNERAL|MORTUARY|CEMETERY)\b", re.IGNORECASE),
    re.compile(r"^(PART|SECTION|CHAPTER|LESSON)\s+(FIRST|SECOND|THIRD|FOURTH|FIFTH|[IVXLCDM]+\b)", re.IGNORECASE),
]


def is_good_title(line: str) -> bool:
    s = line.strip()
    if not s or s in SKIP_TITLES:
        return False
    if not TITLE_RE.match(s):
        return False
    if s.startswith(BAD_PREFIX):
        return False
    for pat in BAD_PATTERNS:
        if pat.match(s):
            return False
    # Must have at least one lowercase-minimum word (real title has a mix)
    # "CONFIDENCE." → all caps, fine. "THE AARONIC PRIESTHOOD." → fine.
    # "F. AUERBACH & BRO." → has &, bad
    if "&" in s:
        return False
    # Must not have newline or consecutive punctuation noise
    if "  " in s:
        return False
    return True


def extract_author(line: str, title: str = "") -> str | None:
    """Check if a line contains a plausible author name."""
    s = line.strip()
    if not s or s == title.strip():
        return None
    # "By Author Name"
    m = re.match(r"^BY\s+([A-Z][a-zA-Z.'\-\s]{2,40})$", s, re.IGNORECASE)
    if m:
        name = m.group(1).strip()
        if name.upper() not in ("SELECTED", "EDITORIAL", "COMPILED", "CONTRIBUTED"):
            return name
        return None
    # Require at least 2 words for a person name (First Last or Initial. Last)
    m = re.match(r"^([A-Z][a-zA-Z.'\-]+(?:\s+[A-Z][a-zA-Z.'\-]+){1,3})$", s)
    if m:
        name = m.group(1).strip()
        words = name.split()
        if 2 <= len(words) <= 4:
            blacklist = {"SELECTED", "EDITORIAL", "EDITORIALS", "POETRY",
                         "POEMS", "CORRESPONDENCE", "EXCHANGES",
                         "PUBLISHER'S DEPARTMENT", "HOME DEPARTMENT",
                         "OUR CABINET", "ANSWERS TO QUERIES",
                         "BOOK NOTICES", "EDITOR'S TABLE",
                         "LITERARY NOTES", "EDITOR'S DEPARTMENT",
                         "EDITOR'S TABLE", "EDUCATION", "EDITORIAL NOTES",
                         "PERSONAL AND IMPERSONAL", "HOME AND FOREIGN",
                         "FROM THE GERMAN", "FROM THE FRENCH",
                         "FROM THE SPANISH", "TRANSLATED", "COMPILED",
                         "ADAPTED", "SELECTED", "CONTRIBUTED",
                         "MONTHLY MAGAZINE", "HOME LITERATURE",
                         "THE CONTRIBUTOR", "CONTENTS"}
            if name.upper() not in blacklist:
                return name
    return None


# ── Main ────────────────────────────────────────────────────────────────


def process_issue(text: str, filename: str) -> dict:
    date_str = parse_date(filename)

    # Find where content starts (skip TOC/ads)
    content_line, meta = find_content_start(text)
    lines = text.split("\n")

    # Only search titles in content area
    content_lines = lines[content_line:]

    # Find title lines within content
    title_spans = []
    for i, line in enumerate(content_lines):
        if is_good_title(line):
            title_spans.append([i, None, line.strip()])

    if not title_spans:
        body = "\n".join(content_lines).strip()
        return {
            "date": date_str,
            "source": "The Contributor",
            "filename": filename,
            "volume": meta.get("volume", ""),
            "number": meta.get("number", ""),
            "articles": [{
                "title": "Untitled",
                "author": None,
                "date": date_str,
                "text": body or text.strip(),
            }],
        }

    # Fill end indices
    for idx in range(len(title_spans)):
        if idx + 1 < len(title_spans):
            title_spans[idx][1] = title_spans[idx + 1][0]
        else:
            title_spans[idx][1] = len(content_lines)

    # Merge same-title consecutive segments (page headers)
    merged = []
    for start, end, title in title_spans:
        if merged and merged[-1][2] == title:
            merged[-1][1] = end
        else:
            merged.append([start, end, title])

    # Build articles
    articles = []
    for start_line, end_line, title in merged:
        body_raw = "\n".join(content_lines[start_line + 1:end_line])
        body = body_raw.strip()

        if len(body) < 800:
            continue

        # Extract author from first non-blank line after title
        author = None
        for j in range(start_line + 1, min(start_line + 5, end_line)):
            s = content_lines[j].strip()
            if s:
                candidate = extract_author(s, title)
                if candidate:
                    author = candidate
                    break
                break  # first non-blank is body text if not author

        articles.append({
            "title": title,
            "author": author,
            "date": date_str,
            "text": body,
        })

    if not articles:
        body = "\n".join(content_lines).strip()
        articles.append({
            "title": "Untitled",
            "author": None,
            "date": date_str,
            "text": body,
        })

    return {
        "date": date_str,
        "source": "The Contributor",
        "filename": filename,
        "volume": meta.get("volume", ""),
        "number": meta.get("number", ""),
        "articles": articles,
    }


def main():
    if len(sys.argv) > 1:
        in_dir = Path(sys.argv[1])
    else:
        in_dir = Path("data/contributor")

    if len(sys.argv) > 2:
        out_dir = Path(sys.argv[2])
    else:
        out_dir = in_dir.parent / "contributor_json"

    out_dir.mkdir(parents=True, exist_ok=True)

    paths = sorted(in_dir.glob("*.txt"))
    if not paths:
        print(f"No .txt files found in {in_dir}")
        sys.exit(1)

    total = 0
    for path in paths:
        if path.stat().st_size == 0:
            print(f"  {path.name}: (empty, skipped)")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        issue = process_issue(text, path.name)
        n = len(issue["articles"])
        out_path = out_dir / path.with_suffix(".json").name
        out_path.write_text(json.dumps(issue, indent=2, ensure_ascii=False), encoding="utf-8")
        total += n
        print(f"  {path.name}: {n} articles")

    print(f"\nTotal: {len(paths)} issues, {total} articles → {out_dir}")


if __name__ == "__main__":
    main()
