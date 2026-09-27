#!/usr/bin/env python3
"""Swap the latest dashboard_payload.json (from Google Drive) into index.html.

Run by .github/workflows/refresh.yml. Never builds, guesses or carries forward
signal data: if the download is missing or malformed, it exits non-zero and
the page is left exactly as it was.
"""
import json
import re
import sys
import urllib.request

DRIVE_ID = "1I3bim2jEEsyA4zA4bQcK0KIgBiHRmt0W"  # Trading Signal System/data/dashboard_payload.json
URL = f"https://drive.google.com/uc?export=download&id={DRIVE_ID}"
PAGE = "index.html"
REQUIRED = ("asof", "today", "slots", "sum", "bench", "positions", "buys", "sells", "scorecard")

req = urllib.request.Request(URL, headers={"User-Agent": "signal-bench-refresh"})
raw = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    sys.exit("Drive did not return JSON (is the file still shared 'Anyone with the link'?)")
missing = [k for k in REQUIRED if k not in data]
if missing:
    sys.exit(f"Payload missing keys: {missing}")

blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
page = open(PAGE, encoding="utf-8").read()
pat = re.compile(r'(<script type="application/json" id="payload">)(.*?)(</script>)', re.S)
if len(pat.findall(page)) != 1:
    sys.exit("Could not find exactly one payload block in index.html")
old = json.loads(pat.search(page).group(2))
if old.get("asof") == data["asof"] and old == data:
    print(f"No change (asof {data['asof']}).")
    sys.exit(0)
page = pat.sub(lambda m: m.group(1) + blob + m.group(3), page)
open(PAGE, "w", encoding="utf-8").write(page)
print(f"Updated: asof {old.get('asof')} -> {data['asof']}")
