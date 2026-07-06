#!/usr/bin/env python3
"""
Convert Improvement Era issue text files into clean JSON output.

Per-issue JSON with full text, date, volume, issue metadata.
No article splitting — the LLM that queries this data will handle
its own chunking. Skips masthead/cover garbage at the start.

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


def get_body_start(text: str) -> int:
    """Find where actual prose content begins, skipping masthead/cover garbage.
    Heuristic: find the first paragraph with >200 chars that isn't dominated
    by numbers/symbols.
    """
    paras = text.split("\n\n")
    for i, para in enumerate(paras):
        s = para.strip()
        if len(s) < 150:
            continue
        # Count what fraction is non-alpha (symbols, numbers, whitespace)
        alpha = sum(c.isalpha() for c in s)
        if alpha / max(len(s), 1) < 0.3:
            continue  # too much noise, probably cover/masthead
        return "\n\n".join(paras[i:])
    return text


def process_issue(text: str, identifier: str, meta: dict) -> dict:
    date_str = meta.get("date", "")
    volume = meta.get("volume", "")
    issue_number = meta.get("issue_number", "")

    # Skip masthead garbage
    body = get_body_start(text)

    return {
        "date": date_str,
        "source": "The Improvement Era",
        "filename": identifier,
        "volume": volume,
        "number": issue_number,
        "text": body,
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

    for path in paths:
        identifier = path.stem
        if path.stat().st_size == 0:
            print(f"  {path.name}: (empty, skipped)")
            continue

        text = path.read_text(encoding="utf-8", errors="replace")
        meta = all_meta.get(identifier, {})
        issue = process_issue(text, identifier, meta)

        out_path = out_dir / f"{identifier}.json"
        out_path.write_text(json.dumps(issue, indent=2, ensure_ascii=False), encoding="utf-8")
        chars = len(issue["text"])
        print(f"  {path.name}: {chars:,} chars (v{issue['volume']} n{issue['number']} {issue['date']})")

    print(f"\nTotal: {len(paths)} issues → {out_dir}")


if __name__ == "__main__":
    main()
