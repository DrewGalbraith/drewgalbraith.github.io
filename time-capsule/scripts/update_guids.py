#!/usr/bin/env python3
"""Add the 14 missing PDF delivery GUIDs to pdf_guids.json"""
import json

path = '/home/agentuser/contributor_issues/pdf_guids.json'

with open(path) as f:
    guids = json.load(f)

# 14 missing entries: assetGuid -> pdfGuid
new_entries = {
    "bc869352-7965-43f7-8f8e-0ae7a0909d4e": "3ecd2dc6-7ef1-45c4-9cb6-87d6d45b2e74",
    "57edf2f8-ade2-48e2-8c02-d8b67e010e36": "3dfac9c5-e5a4-4653-97ee-1270640b6c0d",
    "9b2e59bd-9da1-4706-8465-ed87cc4c5c34": "e287bb96-3728-4522-aaec-b142444a1c0d",
    "1673ae12-deef-4291-ad9f-5f3f83c2defc": "8e79c26b-563e-4480-9717-5ff54ac0a5b3",
    "b8b30d40-b894-4b9d-a8ee-cdf9911b615c": "14d8a7ab-eeda-4aa5-b809-548fdff71fe6",
    "d3058943-df9f-467c-ad04-f53b90f42b50": "9a67331d-8cf3-48d0-bdf2-4754e28fa8c9",
    "37e502ff-31dc-4844-9dcc-817e6ff24705": "1a374fb3-8cbd-4aec-a5f0-a226a631c2bb",
    "d9760d86-f4db-4622-93ab-0b1fe898a47d": "2ec4e466-1236-4543-8c24-bb688eaa5f3e",
    "c9cf527d-64c8-4434-b152-0af9e535ae86": "80565483-a0d8-461f-a757-8e84a85c497f",
    "fb3cdc2e-ed42-45e9-a519-b67212e60417": "ce757f51-3c11-4633-bde2-1e9f95bbed2f",
    "5ea17df5-90be-4fcb-a07f-5d14b3d8877e": "78f34dc8-ec20-430c-b8cb-875b2a76cffe",
    "d760fdc9-683b-449c-9b69-3b3e3baf0494": "92282550-4c25-4d91-9fef-2cad3936f206",
    "b329b76e-e41f-4455-8e20-6ea7dbac6e2a": "ca43e02a-a2ec-4252-91a8-48622b89520c",
    "b03a96b5-ce89-4a8c-bc83-a84e6362a0b5": "d7ef085c-0965-49c1-96de-2723327b01a6",
}

guids.update(new_entries)
print(f"Before: 190 entries")
print(f"Adding: {len(new_entries)} entries")
print(f"After: {len(guids)} entries")

# Verify all 204 issues are covered
with open('/home/agentuser/contributor_issues/issues_metadata.json') as f:
    issues = json.load(f)

all_asset_guids = {i['assetGuid'] for i in issues}
present = set(guids.keys())
missing = all_asset_guids - present
if missing:
    print(f"STILL MISSING ({len(missing)}):")
    for g in sorted(missing):
        title = next((i['title'] for i in issues if i['assetGuid'] == g), '?')
        print(f"  {title} -> {g}")
else:
    print("ALL 204 ISSUES ACCOUNTED FOR!")

with open(path, 'w') as f:
    json.dump(guids, f, indent=2)
print(f"Saved to {path}")
