#!/usr/bin/env python3
"""fetch_ladder.py — reusable fetch ladders for Terra Invicta research agents.

Encodes the four source-specific fetch ladders (official Hooded Horse wiki,
Reddit, Steam, GitHub). Each fetcher walks its ladder rung by rung and returns
as soon as a rung yields usable content.

Every fetcher returns a dict:
    {"content": <str or None>, "method": <str>}
where method is the rung that worked (e.g. "mediawiki-api-parse", "wayback",
"archive-today", "old-reddit", "reddit-json", "pullpush", "curl-ua", "gh-cli")
or "unavailable" if every rung failed.

Usage:
    import sys
    sys.path.insert(0, "/path/to/this/scripts/folder")  # if importing from elsewhere
    from fetch_ladder import fetch_wiki, fetch_reddit, fetch_steam, fetch_github

    r = fetch_wiki("https://hoodedhorse.com/wiki/Terra_Invicta/Victory")
    if r["content"] is None:
        print("unavailable")
    else:
        print(r["method"], len(r["content"]))

CLI:
    python3 fetch_ladder.py wiki   <url>
    python3 fetch_ladder.py reddit <url>
    python3 fetch_ladder.py steam  <url>
    python3 fetch_ladder.py github <owner/repo path-or-api-query>

Notes:
- These ladders use each site's own published endpoints. They deliberately do NOT
  attempt to defeat bot protection: if every rung is blocked the fetcher reports
  "unavailable", and the caller must say the source was unreachable rather than
  fall back on an unverified recollection (docs/reaching-walled-sources.md).
- Wiki ladder: (1) MediaWiki API parse / raw action, (2) Wayback Machine,
  (3) archive.today.
- Reddit ladder: (1) old.reddit.com, (2) append .json, (3) pullpush.io API.
- Steam ladder: (1) plain curl, (2) curl with a browser UA.
- GitHub ladder: gh CLI (authenticated) only.
- Content sanity check: a rung "works" only if it returns >500 bytes that don't
  look like a challenge/block page.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse

# Windows cp1252 console: this script writes FETCHED WEB CONTENT to stdout,
# which is guaranteed to contain non-cp1252 characters sooner or later — and it
# imports no ti_config, so the central reconfigure never runs here.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


BLOCK_MARKERS = (
    "Just a moment...", "cf-challenge", "Attention Required! | Cloudflare",
    "Verifying you are human", "Enable JavaScript and cookies to continue",
)


def _run(cmd, timeout=90):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.stdout
    except Exception:
        return ""


def _ok(text, min_len=500):
    if not text or len(text) < min_len:
        return False
    return not any(m in text for m in BLOCK_MARKERS)


def _curl(url, ua=None, timeout=60, extra=None):
    cmd = ["curl", "-sL", "--max-time", str(timeout), "--compressed"]
    if ua:
        cmd += ["-A", ua]
    if extra:
        cmd += extra
    cmd.append(url)
    return _run(cmd, timeout=timeout + 10)


def _strip_html(html):
    """Crude HTML -> text for claim extraction (keeps wiki body readable)."""
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.I)
    html = re.sub(r"<[^>]+>", "\n", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html


# ---------------------------------------------------------------- wiki ladder

def _wiki_api_base(url):
    """Derive candidate api.php bases for a hoodedhorse wiki page URL."""
    # https://hoodedhorse.com/wiki/Terra_Invicta/Victory ->
    #   https://hoodedhorse.com/wiki/Terra_Invicta/api.php  (per-wiki farm)
    # also try root /w/api.php and /api.php variants.
    parsed = urllib.parse.urlparse(url)
    bases = []
    m = re.match(r"^/wiki/([^/]+)/(.+)$", parsed.path)
    if m:
        game, page = m.group(1), m.group(2)
        root = f"{parsed.scheme}://{parsed.netloc}"
        bases.append((f"{root}/wiki/{game}/api.php", page))
        bases.append((f"{root}/w/api.php", f"{game}/{page}"))
        bases.append((f"{root}/api.php", f"{game}/{page}"))
    return bases


def fetch_wiki(url):
    """Hooded Horse official wiki ladder. Returns {content, method}."""
    # Rung 1: MediaWiki API (the wiki's own published interface)
    for base, page in _wiki_api_base(url):
        q = urllib.parse.urlencode({
            "action": "parse", "page": page, "format": "json",
            "prop": "wikitext", "redirects": 1})
        out = _curl(f"{base}?{q}", ua=UA)
        if out:
            try:
                data = json.loads(out)
                wt = data["parse"]["wikitext"]["*"]
                if _ok(wt, min_len=100):
                    return {"content": wt, "method": "mediawiki-api-parse"}
            except Exception:
                pass
        # action=raw variant
        idx = base.rsplit("/api.php", 1)[0] + "/index.php"
        out = _curl(f"{idx}?{urllib.parse.urlencode({'title': page, 'action': 'raw'})}", ua=UA)
        if _ok(out, min_len=100) and "<html" not in out[:200].lower():
            return {"content": out, "method": "mediawiki-action-raw"}
    # Rung 2: Wayback Machine
    out = _curl(f"https://web.archive.org/web/2024/{url}", ua=UA, timeout=90)
    if _ok(out):
        return {"content": out, "method": "wayback"}
    avail = _curl("https://archive.org/wayback/available?url=" + urllib.parse.quote(url, safe=""), ua=UA)
    try:
        snap = json.loads(avail)["archived_snapshots"]["closest"]["url"]
        out = _curl(snap, ua=UA, timeout=90)
        if _ok(out):
            return {"content": out, "method": "wayback"}
    except Exception:
        pass
    # Rung 3: archive.today
    for host in ("archive.ph", "archive.today"):
        out = _curl(f"https://{host}/newest/{url}", ua=UA, timeout=90)
        if _ok(out):
            return {"content": out, "method": "archive-today"}
    return {"content": None, "method": "unavailable"}


# -------------------------------------------------------------- reddit ladder

def fetch_reddit(url):
    """Reddit ladder. Accepts any reddit.com URL. Returns {content, method}."""
    old = re.sub(r"https?://(www\.|old\.)?reddit\.com", "https://old.reddit.com", url)
    # Rung 1: old.reddit.com HTML
    out = _curl(old, ua=UA)
    if _ok(out):
        return {"content": out, "method": "old-reddit"}
    # Rung 2: .json
    ju = old.split("?")[0].rstrip("/") + ".json"
    sep = "&" if "?" in url else "?"
    if "search" in url:
        ju = url.replace("www.reddit.com", "old.reddit.com") + sep + "raw_json=1"
    out = _curl(ju, ua=UA)
    if out:
        try:
            json.loads(out)
            if _ok(out, min_len=200):
                return {"content": out, "method": "reddit-json"}
        except Exception:
            pass
    # Rung 3: pullpush.io
    m = re.search(r"/comments/([a-z0-9]+)", url)
    if m:
        link_id = m.group(1)
        sub = _curl(f"https://api.pullpush.io/reddit/search/submission/?ids={link_id}", ua=UA)
        com = _curl(f"https://api.pullpush.io/reddit/search/comment/?link_id={link_id}&size=100", ua=UA)
        merged = (sub or "") + "\n" + (com or "")
        if _ok(merged, min_len=300):
            return {"content": merged, "method": "pullpush"}
    return {"content": None, "method": "unavailable"}


# --------------------------------------------------------------- steam ladder

def fetch_steam(url):
    """Steam community/store ladder. Returns {content, method}."""
    out = _curl(url)
    if _ok(out):
        return {"content": out, "method": "curl-plain"}
    out = _curl(url, ua=UA, extra=["-H", "Accept-Language: en-US,en;q=0.9"])
    if _ok(out):
        return {"content": out, "method": "curl-ua"}
    return {"content": None, "method": "unavailable"}


# -------------------------------------------------------------- github ladder

def fetch_github(spec):
    """GitHub via authenticated gh CLI.

    spec: either an 'api <endpoint>' string (e.g. 'api repos/x/y/contents/z')
    or a raw URL (converted to gh api call when possible).
    Returns {content, method}.
    """
    if spec.startswith("http"):
        m = re.match(r"https?://github\.com/([^/]+)/([^/]+)/(?:blob|tree)/([^/]+)/(.*)", spec)
        if m:
            o, r, ref, path = m.groups()
            spec = f"repos/{o}/{r}/contents/{urllib.parse.quote(path)}?ref={ref}"
        else:
            out = _curl(spec, ua=UA)
            if _ok(out):
                return {"content": out, "method": "curl-ua"}
            return {"content": None, "method": "unavailable"}
    out = _run(["gh", "api", spec, "-H", "Accept: application/vnd.github.raw"], timeout=60)
    if _ok(out, min_len=50):
        return {"content": out, "method": "gh-cli"}
    return {"content": None, "method": "unavailable"}


def strip_html(html):
    """Public helper: crude HTML to text."""
    return _strip_html(html)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    kind, target = sys.argv[1], sys.argv[2]
    fn = {"wiki": fetch_wiki, "reddit": fetch_reddit,
          "steam": fetch_steam, "github": fetch_github}[kind]
    res = fn(target)
    print(f"METHOD: {res['method']}", file=sys.stderr)
    if res["content"]:
        sys.stdout.write(res["content"])
