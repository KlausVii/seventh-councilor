# Reaching walled sources (the official wiki, Reddit, Steam)

Many of these docs cite the official wiki (`wiki.hoodedhorse.com`) and Reddit
threads. Both sit behind bot-protection that blocks a plain `curl` and the
default fetch tools (HTTP 403 / "Just a moment…" / "You've been blocked by
network security").

**Use the interfaces these sites publish for programmatic access, and don't try
to defeat their bot protection.** In practice that means the wiki's MediaWiki
JSON API, or the Internet Archive. If neither reaches the thing you need, the
rule from CLAUDE.md § Authoritative sources applies: **say the source was
unreachable — never state a mechanic from model memory to paper over it.**

---

## 1. MediaWiki `api.php` (best for the wiki)

The wiki is MediaWiki, and its JSON API is a documented public interface.
Prefer it over scraping rendered HTML even when the HTML is reachable: it
returns complete, clean content and paginates reliably, where rendered HTML can
silently truncate long tables or lazy-loaded sections.

```
# Wikitext for one page:
https://wiki.hoodedhorse.com/api.php?action=parse&page=Terra_Invicta/Aliens&format=json&prop=wikitext

# Full-text search:
https://wiki.hoodedhorse.com/api.php?action=query&list=search&srsearch=hate&format=json

# List every page (enumerate a category/namespace — for "list ALL X" tasks):
https://wiki.hoodedhorse.com/api.php?action=query&list=allpages&aplimit=500&format=json
```

`action=parse&prop=wikitext` gives you raw wiki markup — usually easier to read
a numeric constant out of than the styled HTML. For any "list every X" task,
drive it off `allpages`/`categorymembers` rather than scraped page links, so you
don't silently drop entries.

Be a polite client: request serially rather than in parallel, and cache what you
fetch so re-running an analysis doesn't re-hit the origin.

## 2. Wayback fallback

When the live origin is unreachable, the Internet Archive usually has a recent
snapshot:

```
https://web.archive.org/web/2/https://wiki.hoodedhorse.com/Terra_Invicta/Victory
```

The `/web/2/` prefix redirects to the newest capture. Note the snapshot date and
treat it as potentially patch-stale — a wiki constant from an old capture may
predate the build the player is on.

## 3. When you can't reach it at all

Some sources will simply be unreachable — Reddit in particular hard-blocks a lot
of non-residential egress, and no client-side change fixes that. When it happens:

- Fall back to Wayback, or to a copy you saved earlier.
- Record **which sources you could and couldn't reach**, so a later reader
  doesn't mistake "unreachable" for "doesn't exist."
- Don't present an unverified recollection as a sourced mechanic. An explicit
  "unverified — source unreachable" is worth more than a confident number that
  turns out to be wrong at the table.
