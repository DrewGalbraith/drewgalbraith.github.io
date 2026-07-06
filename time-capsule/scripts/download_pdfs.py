#!/usr/bin/env python3
"""
Download all 204 Contributor PDFs + extract text.
Uses curl with session cookies (no browser needed).
"""
import json, re, time
from pathlib import Path
from urllib.request import Request, urlopen

OUT = Path("/home/agentuser/contributor_issues")
STATE = OUT / "download_state.json"

# Fresh cookies
BASE_URL = "https://catalog.churchofjesuschrist.org/api/delivery"
COOKIE_VALS = "XSRF-TOKEN=9d3e216e-4e69-47fd-8200-ed20edebcbdb; at_check=true; TAsessionID=4e4e427e-ff16-492b-8483-ea088733fa3a|NEW"

def fetch(url):
    req = Request(url)
    req.add_header("Cookie", COOKIE_VALS)
    req.add_header("User-Agent", "Mozilla/5.0 (X11; Linux x86_64)")
    return urlopen(req, timeout=60).read()

# Load data
guids = json.loads((OUT / "pdf_guids.json").read_text())
meta = json.loads((OUT / "issues_metadata.json").read_text())
title_map = {i["assetGuid"]: i["title"] for i in meta}

# Build name map: assetGuid -> { title, pdfGuid }
items = {g: {"title": title_map.get(g, g[:12]), "pdfGuid": p} for g, p in guids.items() if p}

# Load state
if STATE.exists():
    done = set(json.loads(STATE.read_text()).get("done", []))
else:
    done = set()

pending = {k: v for k, v in items.items() if k not in done}
print(f"Total: {len(items)}, Already done: {len(done)}, Pending: {len(pending)}")

t0 = time.time()
for idx, (asset_guid, info) in enumerate(pending.items()):
    title = info["title"]
    pdf_guid = info["pdfGuid"]
    safe = re.sub(r'[^a-zA-Z0-9 ()-]', '', title).strip() or asset_guid[:12]
    pdf_path = OUT / f"{safe}.pdf"
    txt_path = pdf_path.with_suffix(".txt")

    # Download
    if not pdf_path.exists():
        try:
            url = f"{BASE_URL}/{pdf_guid}?op=ORIGINAL"
            data = fetch(url)
            pdf_path.write_bytes(data)
        except Exception as e:
            print(f"[{idx+1}/{len(pending)}] FAIL download {title}: {e}")
            continue

    pdf_size = pdf_path.stat().st_size

    # Extract text
    txt_chars = 0
    if not txt_path.exists():
        try:
            import fitz
            doc = fitz.open(str(pdf_path))
            pages_text = [p.get_text() for p in doc]
            txt_path.write_text("\n".join(pages_text))
            txt_chars = sum(len(t) for t in pages_text)
            doc.close()
        except Exception as e:
            print(f"  Text error: {e}")

    done.add(asset_guid)
    STATE.write_text(json.dumps({"done": sorted(done)}, indent=2))

    elapsed = time.time() - t0
    rate = (idx + 1) / elapsed * 60
    eta = (len(pending) - idx - 1) / rate if rate > 0 else 0
    print(f"[{idx+1}/{len(pending)}] {title} — {pdf_size/1024:.0f} KB" +
          (f", {txt_chars}c" if txt_chars else ""))

elapsed = time.time() - t0
print(f"\nDONE in {elapsed/60:.1f} min. {len(done)}/{len(items)} issues.")
