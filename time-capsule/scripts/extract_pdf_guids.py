#!/usr/bin/env python3
"""
Extract PDF delivery GUIDs for all issues of The Contributor
from the Church History Catalog asset viewer pages.
"""

import json
import os
import sys
import time
from pathlib import Path

# Unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Use the hermetic playwright from the hermes-agent venv
os.environ["VIRTUAL_ENV"] = "/home/agentuser/.hermes/hermes-agent/venv"
# Use Playwright from the hermes venv
sys.path.insert(0, "/home/agentuser/.hermes/hermes-agent/venv/lib/python3.11/site-packages")

from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

META_PATH = "/home/agentuser/contributor_issues/issues_metadata.json"
OUT_PATH = "/home/agentuser/contributor_issues/pdf_guids.json"

def load_metadata():
    with open(META_PATH) as f:
        return json.load(f)

def load_existing():
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH) as f:
            return json.load(f)
    return {}

def save_progress(data):
    with open(OUT_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  [SAVE] {len(data)}/{TOTAL} entries saved")

def extract_flid(page, asset_guid, title):
    """Navigate to the asset page and extract the flid (PDF delivery GUID)."""
    url = f"https://catalog.churchofjesuschrist.org/assets/{asset_guid}/0/0"
    
    try:
        page.goto(url, wait_until="load", timeout=45000)
    except PwTimeout:
        print(f"  [TIMEOUT] {title} - page load timeout")
        return None
    except Exception as e:
        print(f"  [ERROR] {title} - {e}")
        return None

    # Wait for the page to fully render and the asset viewer to load
    page.wait_for_timeout(3000)

    # Check the page title
    page_title = page.title()
    print(f"  Title: {page_title}")
    
    if "null" in page_title or "Not Found" in page_title or "Record Not Found" in page_title:
        print(f"  [SKIP] {title} - not digitized (title: {page_title})")
        return None

    # Try to extract flid from media-viewer-container
    try:
        flid = page.evaluate("""() => {
            const container = document.getElementById('media-viewer-container');
            if (container) return container.getAttribute('data-test-flid');
            const viewer = document.getElementById('pdf-viewer');
            if (viewer) return viewer.getAttribute('data');
            return null;
        }""")
    except Exception as e:
        print(f"  [ERROR] JS evaluation failed: {e}")
        return None

    return flid


def main():
    global TOTAL
    metadata = load_metadata()
    TOTAL = len(metadata)
    results = load_existing()
    
    print(f"Loaded {TOTAL} issues from metadata")
    print(f"Already processed: {len(results)}")
    
    # Determine which issues still need processing
    pending = []
    for entry in metadata:
        guid = entry["assetGuid"]
        if guid not in results:
            pending.append(entry)
    
    if not pending:
        print("All issues already processed!")
        return
    
    print(f"Pending: {len(pending)} issues")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()
        
        total_pending = len(pending)
        for idx, entry in enumerate(pending):
            title = entry["title"]
            asset_guid = entry["assetGuid"]
            
            print(f"\n[{idx+1}/{total_pending}] {title} ({asset_guid[:8]}...)")
            
            flid = extract_flid(page, asset_guid, title)
            results[asset_guid] = flid
            
            if flid:
                print(f"  [OK] flid={flid}")
            else:
                print(f"  [NULL] not digitized")
            
            # Save every 5 issues or on the last one
            if (idx + 1) % 5 == 0 or idx == total_pending - 1:
                save_progress(results)
            
            # Small delay between requests
            if idx < total_pending - 1:
                time.sleep(1)
        
        browser.close()
    
    # Final save
    save_progress(results)
    
    # Summary
    digitized = sum(1 for v in results.values() if v is not None)
    not_digitized = sum(1 for v in results.values() if v is None)
    print(f"\n{'='*60}")
    print(f"COMPLETE: {len(results)}/{TOTAL} issues processed")
    print(f"  Digitized: {digitized}")
    print(f"  Not digitized: {not_digitized}")
    print(f"  Results saved to: {OUT_PATH}")


if __name__ == "__main__":
    main()
