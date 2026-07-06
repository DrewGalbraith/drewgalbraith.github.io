#!/usr/bin/env python3
"""
Split Improvement Era issue text into per-article JSON entries.

Detects article boundaries via ALL-CAPS title lines, with careful filtering
to skip ads, masthead noise, and running page headers. Same approach as
The Contributor splitter, adapted for the IE's format quirks.

Strategy:
  - Masthead/TOC/ads at the start are skipped via content_start detection
  - Page-header repeats ("TITLE. 123") are merged into a single article
  - Ads are filtered by patterns (company names, prices, form fields)
  - Articles shorter than 800 chars are dropped (ad fragments)
  - Authors extracted from "By ..." line after the title

Usage:
    python3 articles_to_json_ie.py [input_dir] [output_dir]
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

DEFAULT_INPUT = "/home/agentuser/ie_data/improvement_era_text"
DEFAULT_OUTPUT = "/home/agentuser/ie_data/improvement_era_json"


def fetch_metadata() -> dict[str, dict]:
    """Fetch all issue metadata from archive.org API."""
    url = ("https://archive.org/advancedsearch.php"
           "?q=collection:improvementera"
           "&fl=identifier,date,volume"
           "&rows=900&page=1&output=json")
    req = urllib.request.Request(url, headers={"User-Agent": "LDS-corpus-builder/2.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())

    meta = {}
    for doc in data["response"]["docs"]:
        ident = doc["identifier"]
        date_str = doc.get("date", "")
        vol_str = doc.get("volume", "")

        year = ""
        month = ""
        date_fmt = ""
        m = re.match(r"(\d{4})-(\d{2})", date_str)
        if m:
            year = m.group(1)
            month = m.group(2)
            date_fmt = f"{year}-{month}"
        else:
            m = re.match(r"(\d{4})", date_str)
            if m:
                year = m.group(1)
                date_fmt = year

        volume = ""
        issue_number = ""
        vm = re.match(r"(\d+)\s*no\.\s*(\d+)", vol_str, re.IGNORECASE)
        if vm:
            volume = str(int(vm.group(1)))
            issue_number = str(int(vm.group(2)))

        meta[ident] = {
            "date": date_fmt,
            "year": year,
            "month": month,
            "volume": volume,
            "issue_number": issue_number,
        }

    return meta


# ── Title detection ─────────────────────────────────────────────────────

MONTHS_UPPER = {"JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
                "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"}

# Base title regex: ALL-CAPS line with minimal length
TITLE_RE = re.compile(r"^[A-Z][A-Z .\"'!,?:;&/\d()—–\-]{3,79}$")

# Page-number suffix: "TITLE. 123" or "TITLE 123"
PAGE_SUFFIX_RE = re.compile(r"^(.*[A-Za-z])[. ]\s*(\d{2,4})$")

TITLES_TO_SKIP = {
    "IMPROVEMENT ERA", "IMPROVEMENT ERA.",
    "THE IMPROVEMENT ERA,", "THE IMPROVEMENT ERA.",
    "CONTENTS", "CONTENTS.", "TABLE OF CONTENTS", "TABLE OF CONTENTS.",
    "INDEX", "INDEX.",
    "THE GLORY OF GOD IS INTELLIGENCE.",
    "PUBLISHED BY THE GENERAL BOARD.",
    "Published Monthly by the General Board",
    "ORGAN OF THE PRIESTHOOD",
    "ORGAN OF YOUNG MEN'S MUTUAL IMPROVEMENT ASSOCIATIONS.",
}

# These are almost always ads, form fields, or masthead noise
BAD_TITLE_PREFIXES = (
    "VOL.", "NO.", "PAGE", "ESTABLISHED", "ENTERED AT",
    "COPYRIGHT", "PRINTED", "PUBLISHED", "DIRECTORS:",
    "CAPITAL", "SURPLUS", "PRESS OF", "PRICE", "SUBSCRIPTION",
    "ADVERTISING", "SEND FOR", "ILLUSTRATED", "CIRCULARS",
    "CLIP AND MAIL", "NAME.", "ADDRESS.", "CITY", "AGENTS",
    "WHEN WRITING TO ADVERTISERS",
    "BOTH PHON", "PHONES",
    "NEW HOPES ARISE",
    "RETURN POSTAGE GUARANTEED",
    "CORRESPONDENCE",
)

BAD_TITLE_PATTERNS = [
    re.compile(r"^[A-Z\s]{25,}$"),                          # very long = masthead
    re.compile(r"[&]"),                                       # "X & Y" = company
    re.compile(r"\bCO\.\b"),                                  # "COMPANY"
    re.compile(r"\b(BRO|BROS)\.?\b"),                         # "BROTHERS"
    re.compile(r"\b(LTD|INC|CORP|LLC|ASSOC|DEPT)\b"),        # corporate suffixes
    re.compile(r"\b(INSURANCE|BANK|TRUST|MORTGAGE|LOAN)\b"),  # financial
    re.compile(r"\b(HOTEL|FURNITURE|LUMBER|HARDWARE|GROCERY|DRY GOODS|MILL|PRESS|PRINTING|TAILOR|CLOTHING|BOOT|SHOE|JEWELRY|DRUG|PHARMACY|RESTAURANT|CAFE|SALOON)\b"),
    re.compile(r"\bPRICE\b.*\bDOLLAR\b", re.IGNORECASE),     # pricing
    re.compile(r"\b(CENTS|DOLLARS?|BARGAI[N ]S?|SALE|DISCOUNT|FREE)\b", re.IGNORECASE),
    re.compile(r"\bPLEASE MENTION\b", re.IGNORECASE),         # ad form letter
    re.compile(r"\bWRITING TO\b", re.IGNORECASE),
    re.compile(r"(MAIL|TELEPHONE|PHONE)\s*(ORDER|NO|NUMBER)", re.IGNORECASE),
    re.compile(r"\bSALT LAKE CITY\b", re.IGNORECASE),
    re.compile(r"\bUTAH\b.*\b(CITY|STREET|AVENUE|MAIN)\b", re.IGNORECASE),
    re.compile(r"\bSTOCK\b.*\bINVESTMENT\b", re.IGNORECASE),
    re.compile(r"\bINVESTMENT\b.*\bSTOCK\b", re.IGNORECASE),
    re.compile(r"^[A-Z]+\s+\d{3,4}\s*$"),                   # "WORD 1234" (page ref)
    re.compile(r"\d{3,}"),                                   # 3+ consecutive digits
    re.compile(r"[)]"),                                       # closing paren = likely ad
    re.compile(r"YOU WILL FIND", re.IGNORECASE),              # ad language
    re.compile(r"\b(ORDER|CATALOG|CATALOGUE)\b", re.IGNORECASE),
    re.compile(r"\b(CLIP|MAIL|COUPON)\b", re.IGNORECASE),
    re.compile(r"\b(FUNERAL|MORTUARY|CEMETERY)\b", re.IGNORECASE),
    re.compile(r"^(PART|SECTION|CHAPTER|LESSON)\s+(FIRST|SECOND|THIRD|FOURTH|FIFTH|[IVXLCDM]+\b)", re.IGNORECASE),
]


def strip_page_number(title: str) -> str:
    """Strip trailing page number like 'TITLE. 123' → 'TITLE.'"""
    m = PAGE_SUFFIX_RE.match(title.strip())
    if m:
        return m.group(1).strip() + "."
    return title.strip()


def is_good_title(line: str) -> str | None:
    """Check if line is a real article title. Returns cleaned title or None."""
    s = line.strip()
    if not s:
        return None
    if s in TITLES_TO_SKIP:
        return None
    if s.split()[0] in MONTHS_UPPER:
        return None  # "MARCH, 1927" etc.
    if not TITLE_RE.match(s):
        return None

    # Strip page number suffix BEFORE checking patterns
    cleaned = strip_page_number(s)

    # Check against the cleaned version (no page number)
    if cleaned.startswith(BAD_TITLE_PREFIXES):
        return None
    for pat in BAD_TITLE_PATTERNS:
        if pat.search(cleaned):
            return None
    if "  " in cleaned:
        return None

    # Require at least 2 words
    words = cleaned.rstrip(".").split()
    if len(words) < 2:
        return None

    # Final sanity: cleaned version must still match TITLE_RE
    if not TITLE_RE.match(cleaned):
        return None

    return cleaned


def extract_author(line: str) -> str | None:
    s = line.strip()
    if not s:
        return None
    # "By Author Name"
    m = re.match(r"^BY\s+([A-Z][a-zA-Z.'\-\s]{2,60})$", s, re.IGNORECASE)
    if m:
        name = m.group(1).strip()
        if name.upper() not in ("SELECTED", "EDITORIAL", "COMPILED", "CONTRIBUTED",
                                  "THE EDITOR", "THE PUBLISHER", "A CONTRIBUTOR"):
            return name
        return None
    # FirstName LastName
    m = re.match(r"^([A-Z][a-zA-Z.'\-]+(?:\s+[A-Z][a-zA-Z.'\-]+){1,3})$", s)
    if m:
        name = m.group(1).strip()
        blacklist = {"SELECTED", "EDITORIAL", "POETRY", "POEMS",
                     "CORRESPONDENCE", "EXCHANGES",
                     "PUBLISHER'S DEPARTMENT", "HOME DEPARTMENT",
                     "EDITOR'S TABLE", "EDITOR'S PAGE",
                     "BOOK NOTICES", "EDITORIAL NOTES",
                     "FROM THE GERMAN", "FROM THE FRENCH",
                     "FROM THE SPANISH", "TRANSLATED", "COMPILED",
                     "ADAPTED", "SELECTED", "CONTRIBUTED",
                     "IMPROVEMENT ERA", "CONTENTS"}
        if name.upper() not in blacklist:
            return name
    return None


# ── Per-issue processing ───────────────────────────────────────────────

def find_content_start(lines: list[str]) -> int:
    """Find the line where real article content begins.
    We start from line 0 — the body-length filter (800+ chars) handles ads.
    """
    return 0


def process_issue(text: str, identifier: str, meta: dict) -> dict:
    date_str = meta.get("date", "")
    volume = meta.get("volume", "")
    issue_number = meta.get("issue_number", "")

    lines = text.split("\n")
    content_start = find_content_start(lines)
    content_lines = lines[content_start:]

    # Find title lines (store cleaned title)
    title_spans = []
    for i, line in enumerate(content_lines):
        title = is_good_title(line)
        if title:
            title_spans.append([i, None, title])

    if not title_spans:
        # No detectable titles — treat whole issue as one article
        body = "\n".join(content_lines).strip()
        return {
            "date": date_str,
            "source": "The Improvement Era",
            "filename": identifier,
            "volume": volume,
            "number": issue_number,
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

    # Merge consecutive same-title segments (running page headers)
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
                candidate = extract_author(s)
                if candidate:
                    author = candidate
                break

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
        "source": "The Improvement Era",
        "filename": identifier,
        "volume": volume,
        "number": issue_number,
        "articles": articles,
    }


def main():
    in_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_INPUT)
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(DEFAULT_OUTPUT)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Fetching metadata from archive.org...")
    all_meta = fetch_metadata()
    print(f"  Metadata for {len(all_meta)} issues loaded")

    paths = sorted(in_dir.glob("*.txt"))
    if not paths:
        print(f"No .txt files found in {in_dir}")
        sys.exit(1)

    total_articles = 0
    for path in paths:
        identifier = path.stem
        if path.stat().st_size == 0:
            print(f"  {path.name}: (empty, skipped)")
            continue

        text = path.read_text(encoding="utf-8", errors="replace")
        meta = all_meta.get(identifier, {})
        issue = process_issue(text, identifier, meta)

        n = len(issue["articles"])
        out_path = out_dir / f"{identifier}.json"
        out_path.write_text(json.dumps(issue, indent=2, ensure_ascii=False), encoding="utf-8")
        total_articles += n
        print(f"  {path.name}: {n} articles")

    print(f"\nTotal: {len(paths)} issues, {total_articles} articles → {out_dir}")


if __name__ == "__main__":
    main()
