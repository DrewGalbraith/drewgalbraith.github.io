#!/usr/bin/env python3
"""
Pipeline: Download all issues of The Contributor (1879-1896), extract text.

Fully scripted via Playwright + Python stdlib. Runs in background.
Checkpoint/resume via pipeline_state.json.
"""
import asyncio, json, re, time
from pathlib import Path
from urllib.request import Request, urlopen

from playwright.async_api import async_playwright

# ── Config ──────────────────────────────────────────────────────────────
RECORD = "e8400534-f7af-41e4-a5aa-0f9866a49cbf"
BASE = "https://catalog.churchofjesuschrist.org"
OUT = Path("/home/agentuser/contributor_issues")
OUT.mkdir(parents=True, exist_ok=True)
STATE = OUT / "pipeline_state.json"
META = OUT / "issues_metadata.json"

COOKIES = {"XSRF-TOKEN":"d59a0cd3-8e24-4570-8042-fd2ae982493a","at_check":"true",
           "TAsessionID":"dfcd6fe3-7cf6-4d0a-b014-105f5cd00079|NEW","notice_behavior":"implied|us"}

def download_pdf(pdf_url: str, path: Path) -> bool:
    req = Request(pdf_url)
    for k, v in COOKIES.items(): req.add_header("Cookie", f"{k}={v}")
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        path.write_bytes(urlopen(req).read())
        return True
    except Exception as e:
        print(f"   DOWNLOAD FAIL: {e}")
        return False

# ── Phase 1: Scrape from browse pages ──────────────────────────────────

async def scrape_all_issues(page) -> list[dict]:
    """Navigate browse pages by clicking buttons, collect all 204 issues."""
    await page.goto(f"{BASE}/record/{RECORD}/0?view=browse", wait_until="load")
    await page.wait_for_function(
        "() => window.__NEXT_REDUX_STORE__?.getState()?.leaf?.results?.leaves?.length > 0",
        timeout=15000
    )
    await asyncio.sleep(2)

    all_issues = []
    total_pages = await page.evaluate(
        "() => window.__NEXT_REDUX_STORE__.getState().leaf.results.meta.totalPages"
    )
    print(f"  {total_pages} browse pages to scrape")

    for pg in range(1, total_pages + 1):
        if pg > 1:
            # Try page number button first
            clicked = await page.evaluate(f"""
                () => {{ const btns = document.querySelectorAll('button');
                for (const b of btns) {{ if (b.textContent.trim() === '{pg}' && !b.disabled) {{ b.click(); return true; }} }}
                return false; }}
            """)
            if not clicked:
                # Click "next page" (empty-text enabled button = SVG icon)
                await page.evaluate("""
                    () => { const btns = document.querySelectorAll('button');
                    for (const b of btns) { if (b.textContent.trim() === '' && !b.disabled) { b.click(); return; } } }
                """)
                await asyncio.sleep(0.5)
                await page.evaluate(f"""
                    () => {{ const btns = document.querySelectorAll('button');
                    for (const b of btns) {{ if (b.textContent.trim() === '{pg}' && !b.disabled) {{ b.click(); return; }} }} }}
                """)

            await asyncio.sleep(0.5)
            try:
                await page.wait_for_function(
                    f"() => window.__NEXT_REDUX_STORE__.getState().leaf.results.meta.current === {pg}",
                    timeout=8000
                )
            except: pass
            await asyncio.sleep(0.5)

        issues = await page.evaluate("""
            () => { const r = [];
            document.querySelectorAll('h4').forEach(h4 => {
                const t = h4.textContent.trim();
                if (!t.includes('(No.')) return;
                const scope = h4.parentElement?.parentElement || h4.parentElement;
                const v = scope?.querySelector('a[href*="/assets/"]');
                const m = v?.href?.match(/assets\\/([a-f0-9-]+)/);
                if (m) r.push({ title: t, assetGuid: m[1] });
            }); return r; }
        """)
        all_issues.extend(issues)
        print(f"  Page {pg}/{total_pages}: {len(issues)} issues")

    print(f"  Total: {len(all_issues)} issues")
    META.write_text(json.dumps(all_issues, indent=2))
    return all_issues

# ── Phase 2: Process each issue ────────────────────────────────────────

async def process_issues(page, issues: list[dict]) -> tuple:
    state = set()
    skipped = set()
    if STATE.exists():
        data = json.loads(STATE.read_text())
        state = set(data.get("done", []))
        skipped = set(data.get("skipped", []))
        print(f"  Resume: {len(state)} done, {len(skipped)} skipped")

    pending = [i for i in issues if i["assetGuid"] not in state]
    print(f"  Pending: {len(pending)} issues\n")

    for idx, issue in enumerate(pending):
        guid = issue["assetGuid"]
        title = issue["title"]
        print(f"[{idx+1}/{len(pending)}] {title}", flush=True)

        # Navigate to viewer
        await page.goto(f"{BASE}/assets/{guid}/0/0", wait_until="domcontentloaded")
        page_title = await page.title()
        if "Not Found" in page_title or "null" in page_title:
            print(f"  SKIP: not-digitized ({page_title})")
            skipped.add(guid)
            STATE.write_text(json.dumps({"done": sorted(state), "skipped": sorted(skipped)}, indent=2))
            continue

        # Extract PDF delivery GUID
        pdf_guid = None
        try:
            await page.wait_for_selector("#pdf-viewer", timeout=20000)
            pdf_guid = await page.evaluate("""
                () => {
                    const obj = document.getElementById('pdf-viewer');
                    const d = obj?.getAttribute('data') || '';
                    const m = d.match(/delivery\\/([a-f0-9-]+)/);
                    if (m) return m[1];
                    const c = document.getElementById('media-viewer-container');
                    return c?.getAttribute('data-test-flid') || null;
                }
            """)
        except: pass

        if not pdf_guid:
            print(f"  SKIP: no-pdf")
            skipped.add(guid)
            STATE.write_text(json.dumps({"done": sorted(state), "skipped": sorted(skipped)}, indent=2))
            continue

        # Download
        safe = re.sub(r'[^a-zA-Z0-9 ()-]', '', title).strip() or guid[:12]
        pdf_path = OUT / f"{safe}.pdf"
        if not pdf_path.exists():
            ok = download_pdf(f"{BASE}/api/delivery/{pdf_guid}?op=ORIGINAL", pdf_path)
            if not ok:
                print(f"  FAIL: download")
                continue
        print(f"  PDF: {pdf_path.stat().st_size / 1024:.0f} KB")

        # Extract text
        txt_path = pdf_path.with_suffix(".txt")
        if not txt_path.exists():
            try:
                import fitz
                doc = fitz.open(str(pdf_path))
                txt_path.write_text("\n".join(p.get_text() for p in doc))
                chars = sum(len(p.get_text()) for p in doc)
                print(f"  Text: {doc.page_count}p, {chars}c")
                doc.close()
            except Exception as e:
                print(f"  Text error: {e}")

        state.add(guid)
        STATE.write_text(json.dumps({"done": sorted(state), "skipped": sorted(skipped)}, indent=2))
        await asyncio.sleep(0.2)

    return sorted(state), sorted(skipped)

# ── Main ────────────────────────────────────────────────────────────────

async def main():
    t0 = time.time()
    print("=" * 55)
    print("THE CONTRIBUTOR DOWNLOAD PIPELINE")
    print("=" * 55)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0")
        await context.add_cookies([
            {"name":k,"value":v,"domain":".churchofjesuschrist.org","path":"/"}
            for k,v in COOKIES.items()
        ])
        page = await context.new_page()

        print("\nPhase 1: Scraping browse pages...")
        issues = await scrape_all_issues(page)

        print(f"\nPhase 2: Processing {len(issues)} issues...")
        done, skipped = await process_issues(page, issues)
        await browser.close()

    elapsed = time.time() - t0
    print(f"\n{'='*55}")
    print(f"DONE in {elapsed/60:.1f} min")
    print(f"Downloaded: {len(done)}/{len(issues)}")
    print(f"Skipped:    {len(skipped)}")
    print(f"Output:     {OUT}")
    print(f"{'='*55}")

if __name__ == "__main__":
    asyncio.run(main())
