#!/usr/bin/env python3
"""Build the public Signal Bench page (index.html).

Run by .github/workflows/refresh.yml, hourly and on every push of index.html.

1. Makes sure the page has the website-only additions (home-screen icon/meta
   tags and the warning banner). These live between <!--sb:inject--> markers,
   so a fresh copy of the Claude artifact's HTML can be dropped in as
   index.html and this script re-adds them automatically.
2. Swaps the latest dashboard_payload.json from Google Drive into the page.

Never builds, guesses or carries forward signal data: if the download is
missing or malformed, the data block is left exactly as it was.
"""
import json
import re
import sys
import urllib.request

DRIVE_ID = "1I3bim2jEEsyA4zA4bQcK0KIgBiHRmt0W"  # Trading Signal System/data/dashboard_payload.json
URL = f"https://drive.google.com/uc?export=download&id={DRIVE_ID}"
PAGE = "index.html"
REQUIRED = ("asof", "today", "slots", "sum", "bench", "positions", "buys", "sells", "scorecard")
ARTIFACT = "https://claude.ai/code/artifact/d33a14d7-b5a9-4894-ba01-4f53b5b56c86"

HEAD = (
    '<!--sb:inject--><title>The Signal Bench</title>'
    '<meta name="robots" content="noindex,nofollow">'
    '<meta name="apple-mobile-web-app-capable" content="yes">'
    '<meta name="mobile-web-app-capable" content="yes">'
    '<meta name="apple-mobile-web-app-title" content="Signal Bench">'
    '<meta name="apple-mobile-web-app-status-bar-style" content="default">'
    '<meta name="theme-color" content="#F6F7F5">'
    '<link rel="apple-touch-icon" href="apple-touch-icon.png">'
    '<link rel="icon" type="image/png" href="apple-touch-icon.png"><!--/sb:inject-->'
)

BANNER = """<!--sb:inject--><div id="sbWarn" role="alert" hidden style="padding:10px 16px;font:600 13px/1.45 -apple-system,BlinkMacSystemFont,sans-serif;background:#F8E6E3;color:#A33A2C;border-bottom:1px solid #A33A2C"></div>
<script>
(function(){
  var msgs = [];
  function show(m){
    if (msgs.indexOf(m) >= 0) return;
    msgs.push(m);
    var el = document.getElementById("sbWarn");
    if (!el) return;
    el.innerHTML = msgs.map(function(x){ return "<div>" + x + "</div>"; }).join("");
    el.hidden = false;
  }
  window.addEventListener("error", function(){
    show('Heads up: this page hit an error showing today\\'s data, so its design is probably behind the Claude artifact. Ask Claude to "sync the Signal Bench website." Until then, use the <a href="__ARTIFACT__" style="color:inherit">artifact</a>.');
  });
  document.addEventListener("DOMContentLoaded", function(){
    try {
      var d = JSON.parse(document.getElementById("payload").textContent);
      var days = Math.floor((Date.now() - new Date(d.asof + "T00:00:00")) / 86400000);
      if (days > 4) show("Heads up: this data is from " + d.asof + " (" + days + " days old). The Mac's 5 AM job may have stopped.");
    } catch (e) {
      show("Heads up: this page couldn't read its data.");
    }
  });
})();
</script><!--/sb:inject-->""".replace("__ARTIFACT__", ARTIFACT)


def add_injections(page: str) -> str:
    # one-time cleanup of the unmarked head tags from the first version of the site
    legacy = HEAD[len("<!--sb:inject-->"):-len("<!--/sb:inject-->")]
    if legacy in page and "<!--sb:inject--><title>" not in page:
        page = page.replace(legacy, "", 1)
    if "<!--sb:inject--><title>" not in page:
        m = re.search(r"<meta charset=[^>]*>", page)
        if not m:
            sys.exit("No <meta charset> tag found; refusing to guess where the head is")
        page = page[: m.end()] + HEAD + page[m.end():]
    if 'id="sbWarn"' not in page:
        i = page.find("<body>")
        if i < 0:
            sys.exit("No <body> tag found")
        i += len("<body>")
        page = page[:i] + BANNER + page[i:]
    return page


def swap_payload(page: str) -> str:
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "signal-bench-refresh"})
        raw = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
        data = json.loads(raw)
    except Exception as e:  # leave the old data in place, fail the run so GitHub emails
        print(f"::error::Could not load payload from Drive: {e}")
        return None
    missing = [k for k in REQUIRED if k not in data]
    if missing:
        print(f"::error::Payload missing keys: {missing}")
        return None
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    pat = re.compile(r'(<script type="application/json" id="payload">)(.*?)(</script>)', re.S)
    if len(pat.findall(page)) != 1:
        sys.exit("Could not find exactly one payload block in index.html")
    print(f"Payload as of {data['asof']}")
    return pat.sub(lambda m: m.group(1) + blob + m.group(3), page)


page = open(PAGE, encoding="utf-8").read()
page = add_injections(page)
new = swap_payload(page)
ok = new is not None
open(PAGE, "w", encoding="utf-8").write(new if ok else page)
sys.exit(0 if ok else 1)
