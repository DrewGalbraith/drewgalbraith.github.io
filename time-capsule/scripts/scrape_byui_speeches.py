#!/usr/bin/env python3
"""
Scrape BYU-Idaho speech transcriptions from the public speech archive.

Search URL pattern:
  https://www.byui.edu/speeches/search?q=&f0=YEAR&p=PAGE

Usage:
  python scrape_byui_speeches.py
  python scrape_byui_speeches.py --start-year 2010 --end-year 2016
  python scrape_byui_speeches.py --delay 2.0 --output ../data/byui-speeches.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.byui.edu/speeches"
SEARCH_URL = f"{BASE_URL}/search"
USER_AGENT = "BYUI-Speech-Scraper/1.0 (personal research; respectful crawl)"
DEFAULT_START_YEAR = 1969
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "data" / "byui-speeches.json"
DEFAULT_STATE = Path(__file__).resolve().parent.parent / "data" / ".byui-scraper-state.json"
SOURCE_ID = "byu-speeches"


def parse_args() -> argparse.Namespace:
    current_year = datetime.now().year
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--start-year",
        type=int,
        default=DEFAULT_START_YEAR,
        help=f"First year to scrape (default: {DEFAULT_START_YEAR})",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=current_year,
        help=f"Last year to scrape (default: {current_year})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Seconds to wait between HTTP requests (default: 0.5)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to output JSON file",
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_STATE,
        help="Path to resume state file",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore saved state and start fresh",
    )
    parser.add_argument(
        "--max-speeches",
        type=int,
        default=0,
        help="Stop after this many speeches with text (0 = no limit, for testing)",
    )
    parser.add_argument(
        "--test-url",
        type=str,
        default="",
        help="Fetch one speech URL, print extracted text, and exit",
    )
    return parser.parse_args()


def normalize_paragraph(text: str) -> str:
    text = re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()
    return text.strip("\"'“”‘’").strip()


def find_transcript_root(soup: BeautifulSoup) -> Any | None:
    """Locate the main transcript container within the speech article."""
    scopes = [
        soup.select_one(".DevotionalPage-articleContainer"),
        soup.select_one("article.DevotionalPage-mainContent"),
        soup.select_one("article"),
    ]

    best: Any | None = None
    best_len = 0

    for scope in scopes:
        if not scope:
            continue

        article_body = scope.select_one(".DevotionalPage-articleBody")
        if article_body:
            candidates = article_body.select(
                ".RichTextArticleBody-body, .RichTextArticleBody, .RichTextBody"
            )
            for candidate in candidates:
                length = len(candidate.get_text(strip=True))
                if length > best_len:
                    best = candidate
                    best_len = length

            body_text_len = len(article_body.get_text(strip=True))
            if body_text_len > best_len:
                best = article_body
                best_len = body_text_len

    if best_len >= 100:
        return best

    for selector in (".RichTextArticleBody-body", ".RichTextArticleBody"):
        candidate = soup.select_one(selector)
        if candidate:
            length = len(candidate.get_text(strip=True))
            if length > best_len:
                best = candidate
                best_len = length

    return best if best_len >= 100 else None


def extract_paragraphs(body_el: Any) -> list[str]:
    paragraphs: list[str] = []

    for node in body_el.find_all(["p", "h2", "h3", "h4", "blockquote", "li"]):
        text = normalize_paragraph(node.get_text(" ", strip=True))
        if text:
            paragraphs.append(text)

    if paragraphs:
        return paragraphs

    for chunk in re.split(r"\n\s*\n", body_el.get_text("\n", strip=True)):
        text = normalize_paragraph(chunk)
        if len(text) > 20:
            paragraphs.append(text)

    if paragraphs:
        return paragraphs

    for line in body_el.get_text("\n", strip=True).split("\n"):
        text = normalize_paragraph(line)
        if len(text) > 20:
            paragraphs.append(text)

    return paragraphs


class ByuiSpeechScraper:
    def __init__(self, delay: float) -> None:
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def _sleep(self) -> None:
        time.sleep(self.delay)

    def fetch(self, url: str) -> str:
        self._sleep()
        response = self.session.get(url, timeout=60)
        response.raise_for_status()
        return response.text

    def search_page_url(self, year: int, page: int = 1) -> str:
        params = {"q": "", "f0": str(year)}
        if page > 1:
            params["p"] = str(page)
        query = "&".join(f"{key}={value}" for key, value in params.items())
        return f"{SEARCH_URL}?{query}"

    def parse_search_cards(self, html: str) -> list[dict[str, str]]:
        soup = BeautifulSoup(html, "html.parser")
        cards: list[dict[str, str]] = []

        for card in soup.select(".PromoSpeechCard"):
            title_link = card.select_one(".PromoSpeechCard-title a[href]")
            if not title_link:
                continue

            href = title_link.get("href", "").strip()
            if not href:
                continue

            url = urljoin(BASE_URL + "/", href)
            category_el = card.select_one(".PromoSpeechCard-category")
            author_el = card.select_one(".PromoSpeechCard-authorName")
            date_el = card.select_one(".PromoSpeechCard-date")

            cards.append(
                {
                    "url": normalize_url(url),
                    "title": title_link.get_text(strip=True),
                    "category": category_el.get_text(strip=True) if category_el else "",
                    "speaker": author_el.get_text(strip=True) if author_el else "",
                    "date": date_el.get_text(strip=True) if date_el else "",
                }
            )

        return cards

    def has_next_page(self, html: str, current_page: int) -> bool:
        soup = BeautifulSoup(html, "html.parser")
        next_link = soup.select_one(".Pagination-nextPage a[href]")
        if not next_link:
            return False
        href = next_link.get("href", "")
        match = re.search(r"[?&]p=(\d+)", href)
        if match:
            return int(match.group(1)) > current_page
        return bool(href)

    def collect_year_urls(self, year: int) -> list[dict[str, str]]:
        seen: set[str] = set()
        results: list[dict[str, str]] = []
        page = 1

        while True:
            url = self.search_page_url(year, page)
            print(f"  search {year} page {page}: {url}", flush=True)
            html = self.fetch(url)
            cards = self.parse_search_cards(html)

            if not cards and page == 1:
                print(f"  no results for {year}", flush=True)
                break

            for card in cards:
                if card["url"] not in seen:
                    seen.add(card["url"])
                    card["search_year"] = str(year)
                    results.append(card)

            if not self.has_next_page(html, page):
                break
            page += 1

        print(f"  found {len(results)} speech links for {year}", flush=True)
        return results

    def extract_transcript(self, html: str) -> tuple[list[str], dict[str, str]]:
        soup = BeautifulSoup(html, "html.parser")
        metadata: dict[str, str] = {}

        title_el = soup.select_one(".DevotionalPage-headline")
        author_el = soup.select_one(".DevotionalPage-authorName")
        date_el = soup.select_one(".DevotionalPage-speechDate")
        position_el = soup.select_one(".DevotionalPage-authorPosition")

        if title_el:
            metadata["title"] = title_el.get_text(strip=True)
        if author_el:
            metadata["speaker"] = author_el.get_text(strip=True)
        if date_el:
            metadata["date"] = date_el.get_text(strip=True)
        if position_el:
            metadata["speaker_position"] = position_el.get_text(strip=True)

        og_published = soup.find("meta", property="article:published_time")
        if og_published and og_published.get("content"):
            metadata["published_iso"] = og_published["content"]

        section = soup.find("meta", property="article:section")
        if section and section.get("content"):
            metadata["category"] = section["content"]

        description = soup.find("meta", attrs={"name": "description"})
        if description and description.get("content"):
            metadata["description"] = description["content"].strip()

        body_el = find_transcript_root(soup)
        if not body_el:
            return [], metadata

        paragraphs = extract_paragraphs(body_el)
        return paragraphs, metadata


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def is_valid_speech_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc not in ("www.byui.edu", "byui.edu"):
        return False
    path = parsed.path
    if not path.startswith("/speeches/"):
        return False
    if "https:" in path or "http:" in path:
        return False
    return True


def speech_year(date_iso: str | None, search_year: str) -> str:
    if date_iso and len(date_iso) >= 4:
        return date_iso[:4]
    return search_year


def build_speech_entry(
    url: str,
    body_paras: list[str],
    page_meta: dict[str, str],
    card: dict[str, str],
    search_year: str,
) -> dict[str, Any]:
    date_iso = page_meta.get("published_iso", "")
    return {
        "title": page_meta.get("title") or card.get("title", ""),
        "speaker": page_meta.get("speaker") or card.get("speaker", ""),
        "year": speech_year(date_iso or None, search_year),
        "date": date_iso,
        "type": page_meta.get("category") or card.get("category", ""),
        "description": page_meta.get("description", ""),
        "body": "\n\n".join(body_paras),
        "body_paras": body_paras,
        "source": SOURCE_ID,
        "url": url,
    }


def load_state(state_file: Path) -> dict[str, Any]:
    if not state_file.exists():
        return {"visited_urls": [], "speeches": []}
    with state_file.open(encoding="utf-8") as handle:
        return json.load(handle)


def save_state(state_file: Path, state: dict[str, Any]) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with state_file.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def write_output(output_file: Path, speeches: list[dict[str, Any]]) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as handle:
        json.dump(speeches, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def main() -> int:
    args = parse_args()
    if args.test_url:
        scraper = ByuiSpeechScraper(delay=0)
        print(f"Testing: {args.test_url}", flush=True)
        html = scraper.session.get(args.test_url, headers={"User-Agent": USER_AGENT}, timeout=60).text
        paragraphs, metadata = scraper.extract_transcript(html)
        print(f"title: {metadata.get('title', '')}", flush=True)
        print(f"speaker: {metadata.get('speaker', '')}", flush=True)
        print(f"paragraphs: {len(paragraphs)}", flush=True)
        if paragraphs:
            print("\n--- first 3 paragraphs ---", flush=True)
            for index, paragraph in enumerate(paragraphs[:3], start=1):
                print(f"\n[{index}] {paragraph}", flush=True)
        else:
            print("no transcript text found", flush=True)
            return 1
        return 0

    if args.start_year > args.end_year:
        print("start-year must be <= end-year", file=sys.stderr)
        return 1

    scraper = ByuiSpeechScraper(delay=args.delay)

    if args.no_resume:
        state: dict[str, Any] = {"visited_urls": [], "speeches": []}
    else:
        state = load_state(args.state_file)

    visited: set[str] = set(state.get("visited_urls", []))
    speeches: list[dict[str, Any]] = list(state.get("speeches", []))
    saved_with_text = len(speeches)

    print(
        f"Scraping BYU-Idaho speeches {args.start_year}-{args.end_year} "
        f"(delay={args.delay}s, resume={not args.no_resume})",
        flush=True,
    )
    if visited:
        print(f"Resuming: {len(visited)} URLs visited, {saved_with_text} speeches saved", flush=True)

    for year in range(args.start_year, args.end_year + 1):
        print(f"\nYear {year}", flush=True)
        try:
            cards = scraper.collect_year_urls(year)
        except requests.RequestException as exc:
            print(f"  search failed for {year}: {exc}", file=sys.stderr, flush=True)
            save_state(args.state_file, {"visited_urls": sorted(visited), "speeches": speeches})
            return 1

        for card in cards:
            url = card["url"]
            if url in visited:
                continue
            if not is_valid_speech_url(url):
                print(f"  skip invalid url: {url}", flush=True)
                visited.add(url)
                save_state(args.state_file, {"visited_urls": sorted(visited), "speeches": speeches})
                continue

            print(f"  speech: {url}", flush=True)
            try:
                html = scraper.fetch(url)
            except requests.RequestException as exc:
                print(f"    fetch failed: {exc}", file=sys.stderr, flush=True)
                visited.add(url)
                save_state(args.state_file, {"visited_urls": sorted(visited), "speeches": speeches})
                continue

            body, page_meta = scraper.extract_transcript(html)
            visited.add(url)

            if not body:
                print("    no transcript text, skipping", flush=True)
                save_state(args.state_file, {"visited_urls": sorted(visited), "speeches": speeches})
                continue

            entry = build_speech_entry(
                url,
                body,
                page_meta,
                card,
                card.get("search_year", str(year)),
            )

            speeches.append(entry)
            saved_with_text += 1
            print(f"    saved ({len(body)} paragraphs)", flush=True)
            write_output(args.output, speeches)
            save_state(args.state_file, {"visited_urls": sorted(visited), "speeches": speeches})

            if args.max_speeches and saved_with_text >= args.max_speeches:
                print(f"\nReached --max-speeches={args.max_speeches}, stopping.", flush=True)
                print(f"Output: {args.output} ({saved_with_text} speeches)", flush=True)
                return 0

    write_output(args.output, speeches)
    save_state(args.state_file, {"visited_urls": sorted(visited), "speeches": speeches})
    print(f"\nDone. {saved_with_text} speeches with text -> {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
