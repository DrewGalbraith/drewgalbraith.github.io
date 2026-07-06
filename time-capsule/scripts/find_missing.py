#!/usr/bin/env python3
import json

# Load issues metadata
with open('/home/agentuser/contributor_issues/issues_metadata.json') as f:
    issues = json.load(f)

# Load existing pdf_guids
with open('/home/agentuser/contributor_issues/pdf_guids.json') as f:
    pdf_guids = json.load(f)

# Load pipeline state (skipped = previously processed)
with open('/home/agentuser/contributor_issues/pipeline_state.json') as f:
    state = json.load(f)

existing_keys = set(pdf_guids.keys())
skipped_set = set(state['skipped'])

print(f"Total issues in metadata: {len(issues)}")
print(f"Entries in pdf_guids.json: {len(pdf_guids)}")
print(f"Entries in skipped list: {len(state['skipped'])}")

# Find assetGuids in issues_metadata that are NOT in pdf_guids
missing = []
for issue in issues:
    guid = issue['assetGuid']
    if guid not in pdf_guids:
        missing.append(issue)
        print(f"MISSING: {issue['title']} -> {guid}")

print(f"\nTotal missing from pdf_guids.json: {len(missing)}")

# Also check skipped list - any in skipped that aren't in pdf_guids?
skipped_not_in_guids = skipped_set - existing_keys
if skipped_not_in_guids:
    print(f"\nSkipped but NOT in pdf_guids ({len(skipped_not_in_guids)}):")
    for guid in sorted(skipped_not_in_guids):
        # Find title
        title = next((i['title'] for i in issues if i['assetGuid'] == guid), 'UNKNOWN')
        print(f"  {title} -> {guid}")

# Any in guids but not in skipped?
guids_not_in_skipped = existing_keys - skipped_set
if guids_not_in_skipped:
    print(f"\nIn pdf_guids but NOT in skipped ({len(guids_not_in_skipped)}):")
    for guid in sorted(guids_not_in_skipped):
        title = next((i['title'] for i in issues if i['assetGuid'] == guid), 'UNKNOWN')
        print(f"  {title} -> {guid}")
