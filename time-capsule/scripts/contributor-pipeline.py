#!/usr/bin/env python3
"""
Pipeline: Download all 204 issues of *The Contributor* (1879–1896)
from the Church History Catalog and extract text from the PDFs.

The Contributor began in 1879 as the publication for the Mutual Improvement
Associations. From 1889 onward it focused on the Young Men's MIA. It ran
until 1896, replaced the next year by the Improvement Era.

Source: https://catalog.churchofjesuschrist.org/record/e8400534-f7af-41e4-a5aa-0f9866a49cbf/0?view=browse

TWO PHASES:
  1. METADATA & PDF GUID — scrape browse pages to collect issue metadata, then
     extract each issue's PDF delivery GUID from the asset viewer page.
  2. DOWNLOAD & EXTRACT — download each PDF via the delivery API, then extract
     text using PyMuPDF (fitz).

NOTES:
  - The catalog blocks headless Playwright during Phase 1 (bot detection on the
    asset viewer). The Hermes interactive browser works. Run Phase 1 manually
    or use a non-headless/stealth approach.
  - Session cookies expire. You'll need fresh cookies from a browser session.
  - October 1879 (Vol 1, No 1) is NOT digitized — the pipeline skips it gracefully.

Requirements: pip install playwright PyMuPDF  (or `uv pip install ...`)
"""

import asyncio
import json
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen

# ── Config ──────────────────────────────────────────────────────────────

RECORD = "e8400534-f7af-41e4-a5aa-0f9866a49cbf"
BASE = "https://catalog.churchofjesuschrist.org"
OUT = Path("data/contributor")  # relative to repo root / where you run this
OUT.mkdir(parents=True, exist_ok=True)

# ── Fresh cookies ───────────────────────────────────────────────────────
# Get these from an authenticated browser session on catalog.churchofjesuschrist.org.
# Open DevTools → Application → Cookies, copy the values for:
#   XSRF-TOKEN, at_check, TAsessionID
# Paste them below before running. They expire after ~30 min of inactivity.

COOKIES = {
    "XSRF-TOKEN": "PUT_FRESH_TOKEN_HERE",
    "at_check": "true",
    "TAsessionID": "PUT_FRESH_SESSION_ID_HERE|NEW",
}

# ── Helpers ─────────────────────────────────────────────────────────────


def download_pdf(pdf_url: str, path: Path) -> bool:
    """Download a PDF from the catalog delivery API using session cookies."""
    req = Request(pdf_url)
    for k, v in COOKIES.items():
        req.add_header("Cookie", f"{k}={v}")
    req.add_header("User-Agent", "Mozilla/5.0 (X11; Linux x86_64)")
    try:
        path.write_bytes(urlopen(req, timeout=60).read())
        return True
    except Exception as e:
        print(f"   DOWNLOAD FAIL: {e}")
        return False


# ── Phase 1: Scrape browse pages ───────────────────────────────────────
# NOTE: The catalog blocks headless Playwright on asset viewer pages.
# If you can run with a visible browser or the Hermes browser tool, use
# extract_pdf_guids.py instead. The metadata scrape (browse pages) also
# uses Playwright below:

async def scrape_all_issues(page) -> list[dict]:
    """
    Navigate browse pages by clicking pagination buttons,
    collecting all issue asset GUIDs and titles.
    """
    await page.goto(f"{BASE}/record/{RECORD}/0?view=browse", wait_until="load")
    await page.wait_for_function(
        "() => window.__NEXT_REDUX_STORE__?.getState()?.leaf?.results?.leaves?.length > 0",
        timeout=15000,
    )
    await asyncio.sleep(2)

    all_issues = []
    total_pages = await page.evaluate(
        "() => window.__NEXT_REDUX_STORE__.getState().leaf.results.meta.totalPages"
    )
    print(f"  {total_pages} browse pages to scrape")

    for pg in range(1, total_pages + 1):
        if pg > 1:
            clicked = await page.evaluate(
                f"""
                () => {{ const btns = document.querySelectorAll('button');
                for (const b of btns) {{ if (b.textContent.trim() === '{pg}' && !b.disabled) {{ b.click(); return true; }} }}
                return false; }}
            """
            )
            if not clicked:
                # Click "next page" (empty-text enabled button = SVG icon)
                await page.evaluate(
                    """
                    () => { const btns = document.querySelectorAll('button');
                    for (const b of btns) { if (b.textContent.trim() === '' && !b.disabled) { b.click(); return; } } }
                """
                )
                await asyncio.sleep(0.5)
                await page.evaluate(
                    f"""
                    () => {{ const btns = document.querySelectorAll('button');
                    for (const b of btns) {{ if (b.textContent.trim() === '{pg}' && !b.disabled) {{ b.click(); return; }} }} }}
                """
                )

            await asyncio.sleep(0.5)
            try:
                await page.wait_for_function(
                    f"() => window.__NEXT_REDUX_STORE__.getState().leaf.results.meta.current === {pg}",
                    timeout=8000,
                )
            except Exception:
                pass
            await asyncio.sleep(0.5)

        issues = await page.evaluate(
            """
            () => { const r = [];
            document.querySelectorAll('h4').forEach(h4 => {
                const t = h4.textContent.trim();
                if (!t.includes('(No.')) return;
                const scope = h4.parentElement?.parentElement || h4.parentElement;
                const v = scope?.querySelector('a[href*="/assets/"]');
                const m = v?.href?.match(/assets\\/([a-f0-9-]+)/);
                if (m) r.push({ title: t, assetGuid: m[1] });
            }); return r; }
        """
        )
        all_issues.extend(issues)
        print(f"  Page {pg}/{total_pages}: {len(issues)} issues")

    print(f"  Total: {len(all_issues)} issues")
    return all_issues


async def extract_pdf_guids(page, issues: list[dict]) -> dict:
    """
    For each issue, navigate to its asset viewer page and extract the
    PDF delivery GUID from the <object id="pdf-viewer"> element.
    """
    results = {}
    for idx, issue in enumerate(issues):
        guid = issue["assetGuid"]
        title = issue["title"]
        print(f"  [{idx+1}/{len(issues)}] {title}", end="", flush=True)

        await page.goto(f"{BASE}/assets/{guid}/0/0", wait_until="domcontentloaded")
        page_title = await page.title()
        if "Not Found" in page_title or "null" in page_title:
            print(" — SKIP (not digitized)")
            results[guid] = None
            continue

        pdf_guid = None
        try:
            await page.wait_for_selector("#pdf-viewer", timeout=20000)
            pdf_guid = await page.evaluate(
                """
                () => {
                    const obj = document.getElementById('pdf-viewer');
                    const d = obj?.getAttribute('data') || '';
                    const m = d.match(/delivery\\/([a-f0-9-]+)/);
                    if (m) return m[1];
                    const c = document.getElementById('media-viewer-container');
                    return c?.getAttribute('data-test-flid') || null;
                }
            """
            )
        except Exception:
            pass

        if pdf_guid:
            print(f" — OK (pdf_guid={pdf_guid[:8]}...)")
            results[guid] = pdf_guid
        else:
            print(" — SKIP (no PDF)")
            results[guid] = None

        await asyncio.sleep(0.5)

    return results


# ── Phase 2: Download & extract text ────────────────────────────────────


def download_and_extract(issues_meta: list[dict], pdf_guids: dict) -> tuple:
    """
    Download each PDF (via curl with cookies) and extract text with PyMuPDF.
    Checkpoint/resume via download_state.json.
    """
    import fitz  # PyMuPDF

    state_path = OUT / "download_state.json"

    # Build name map
    title_map = {i["assetGuid"]: i["title"] for i in issues_meta}
    items = {
        g: {"title": title_map.get(g, g[:12]), "pdfGuid": p}
        for g, p in pdf_guids.items()
        if p  # skip None (not digitized)
    }

    # Load state
    if state_path.exists():
        done = set(json.loads(state_path.read_text()).get("done", []))
    else:
        done = set()

    pending = {k: v for k, v in items.items() if k not in done}
    print(
        f"Total: {len(items)}, Already done: {len(done)}, Pending: {len(pending)}"
    )

    t0 = time.time()
    for idx, (asset_guid, info) in enumerate(pending.items()):
        title = info["title"]
        pdf_guid = info["pdfGuid"]
        safe = re.sub(r"[^a-zA-Z0-9 ()-]", "", title).strip() or asset_guid[:12]
        pdf_path = OUT / f"{safe}.pdf"
        txt_path = pdf_path.with_suffix(".txt")

        # Download
        if not pdf_path.exists():
            url = f"{BASE}/api/delivery/{pdf_guid}?op=ORIGINAL"
            ok = download_pdf(url, pdf_path)
            if not ok:
                print(f"  [{idx+1}/{len(pending)}] FAIL download: {title}")
                continue

        pdf_size = pdf_path.stat().st_size

        # Extract text
        txt_chars = 0
        if not txt_path.exists():
            try:
                doc = fitz.open(str(pdf_path))
                pages_text = [p.get_text() for p in doc]
                txt_path.write_text("\n".join(pages_text))
                txt_chars = sum(len(t) for t in pages_text)
                doc.close()
            except Exception as e:
                print(f"  Text error: {e}")

        done.add(asset_guid)
        state_path.write_text(json.dumps({"done": sorted(done)}, indent=2))

        elapsed = time.time() - t0
        rate = (idx + 1) / elapsed * 60
        eta = (len(pending) - idx - 1) / rate if rate > 0 else 0
        print(
            f"  [{idx+1}/{len(pending)}] {title} — {pdf_size/1024:.0f} KB"
            + (f", {txt_chars}c" if txt_chars else ""),
            end="",
            flush=True,
        )

    elapsed = time.time() - t0
    print(f"\n\nDONE in {elapsed/60:.1f} min. {len(done)}/{len(items)} issues.")
    return sorted(done)


# ── Main ────────────────────────────────────────────────────────────────


async def main():
    import sys

    print("=" * 60)
    print("THE CONTRIBUTOR DOWNLOAD PIPELINE (1879–1896)")
    print("=" * 60)

    # ── Parse args ──────────────────────────────────────────────────────
    skip_phase1 = "--skip-phase1" in sys.argv
    phase_only = None
    for a in sys.argv:
        if a.startswith("--phase="):
            phase_only = a.split("=")[1]

    # ── Phase 1: Scrape & PDF GUID extraction ───────────────────────────
    if not skip_phase1 and phase_only in (None, "1"):
        print("\nPhase 1: Scraping browse pages...")
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            )
            await context.add_cookies(
                [
                    {"name": k, "value": v, "domain": ".churchofjesuschrist.org", "path": "/"}
                    for k, v in COOKIES.items()
                ]
            )
            page = await context.new_page()

            issues = await scrape_all_issues(page)
            (OUT / "issues_metadata.json").write_text(json.dumps(issues, indent=2))
            print(f"  Saved {len(issues)} issues to issues_metadata.json")

            print("\nPhase 1b: Extracting PDF delivery GUIDs...")
            pdf_guids = await extract_pdf_guids(page, issues)
            (OUT / "pdf_guids.json").write_text(json.dumps(pdf_guids, indent=2))

            digitized = sum(1 for v in pdf_guids.values() if v)
            print(f"  Digitized: {digitized}, Skipped: {len(pdf_guids) - digitized}")
            await browser.close()

    # ── Phase 2: Download & text extraction ─────────────────────────────
    if phase_only in (None, "2"):
        print("\nPhase 2: Downloading PDFs and extracting text...")
        issues_meta = json.loads((OUT / "issues_metadata.json").read_text())
        pdf_guids = json.loads((OUT / "pdf_guids.json").read_text())
        done = download_and_extract(issues_meta, pdf_guids)
        print(f"  Done: {len(done)} issues")

    print(f"\n{'='*60}")
    print("Pipeline complete.")
    print(f"Output directory: {OUT.resolve()}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
