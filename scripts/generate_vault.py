#!/usr/bin/env python3
"""Generate the Terra Invicta reference knowledge base (wikilink markdown) from game JSON templates."""
import json
import os
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from ti_config import find_templates_dir, find_localization_dir

ROOT = Path(__file__).resolve().parent.parent / "generated"
_templates_dir = find_templates_dir()
_localization_dir = find_localization_dir()
if _templates_dir is None or _localization_dir is None:
    raise SystemExit(
        "Game templates/localization not found. Run sync_game_data.py first, "
        'or set "game_install_dir" in config.json.'
    )
TEMPLATES = Path(_templates_dir)
LOCAL = Path(_localization_dir)

# ---------- mappings ----------
CATEGORY_DISPLAY = {
    "SocialScience": "Social Science",
    "InformationScience": "Information Science",
    "LifeScience": "Life Science",
    "MilitaryScience": "Military Science",
    "Materials": "Materials",
    "Energy": "Energy",
    "SpaceScience": "Space Science",
    "Xenology": "Xenology",
}
CATEGORY_ICON = {
    "SocialScience": "🏛️",
    "InformationScience": "💻",
    "LifeScience": "🧬",
    "MilitaryScience": "⚔️",
    "Materials": "🔧",
    "Energy": "⚡",
    "SpaceScience": "🚀",
    "Xenology": "👽",
}
FACTION_DISPLAY = {
    "ResistCouncil": "Resistance",
    "ExploitCouncil": "Initiative",
    "SubmitCouncil": "Servants",
    "AppeaseCouncil": "Protectorate",
    "CooperateCouncil": "Academy",
    "DestroyCouncil": "Humanity First",
    "EscapeCouncil": "Project Exodus",
    "AlienCouncil": "Aliens",
}
FACTION_TAGLINE = {
    "Resistance": "Resist — prevent the alien invasion, fight back if needed",
    "Initiative": "Exploit — capitalize on the alien arrival for power and profit",
    "Servants": "Submit — defend the aliens; serve their plan for Earth",
    "Protectorate": "Appease — negotiate surrender to avoid annihilation",
    "Academy": "Cooperate — seek interstellar alliance and uplift",
    "Humanity First": "Destroy — exterminate the aliens and their sympathizers",
    "Project Exodus": "Escape — build a starship and flee the Solar System",
    "Aliens": "The Hydra — the unplayable invading faction",
}

# ---------- helpers ----------
INVALID_FN_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
def sanitize_filename(name: str) -> str:
    name = INVALID_FN_CHARS.sub("-", name).strip().rstrip(".")
    return name or "Unnamed"

def parse_localization(path: Path) -> dict:
    """Parse a TI localization file. Each line: tag=value. Multi-line values continue until next tag."""
    result = {}
    if not path.exists():
        return result
    with open(path, encoding="utf-8") as f:
        text = f.read()
    # Strip BOM
    if text.startswith("﻿"):
        text = text[1:]
    # Strip C-style line comments after //, but only at end of line (not inside strings)
    cur_key = None
    cur_val_lines = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        # Strip trailing // comment (but not URLs)
        cm = re.search(r"\s+//(?!/)(.*)$", line)
        if cm and "://" not in line[:cm.start()]:
            line = line[:cm.start()].rstrip()
        if "=" in line and re.match(r"^[A-Za-z][\w.\-]*=", line):
            if cur_key is not None:
                result[cur_key] = "\n".join(cur_val_lines).rstrip()
            k, _, v = line.partition("=")
            cur_key = k.strip()
            cur_val_lines = [v]
        else:
            if cur_key is not None:
                cur_val_lines.append(line)
    if cur_key is not None:
        result[cur_key] = "\n".join(cur_val_lines).rstrip()
    return result

def clean_html(s: str) -> str:
    if not s:
        return s
    # Convert TI's inline HTML to plain wikilink-style markdown
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"<align=right>(.*?)</?align(?:=left)?>", r"— \1", s, flags=re.IGNORECASE | re.DOTALL)
    s = re.sub(r"<align=[^>]+>", "", s, flags=re.IGNORECASE)
    s = re.sub(r"</align>", "", s, flags=re.IGNORECASE)
    s = re.sub(r"<i>(.*?)</i>", r"*\1*", s, flags=re.IGNORECASE | re.DOTALL)
    s = re.sub(r"<b>(.*?)</b>", r"**\1**", s, flags=re.IGNORECASE | re.DOTALL)
    s = re.sub(r"<color[^>]*>(.*?)</color>", r"\1", s, flags=re.IGNORECASE | re.DOTALL)
    s = re.sub(r"<size[^>]*>(.*?)</size>", r"\1", s, flags=re.IGNORECASE | re.DOTALL)
    s = re.sub(r"<sprite[^>]*/?>", "", s, flags=re.IGNORECASE)
    s = re.sub(r"<[^>]+>", "", s)  # strip any remaining tags
    # TI uses tokens like {resistLeader}, leave them as is — they're flavor text
    s = s.replace(" ", " ")
    return s.strip()

def fmt_value(op: str, value) -> str:
    if value is None:
        return ""
    if op == "Multiplicative":
        try:
            v = float(value)
            pct = (v - 1) * 100
            sign = "+" if pct >= 0 else ""
            return f"×{v:g} ({sign}{pct:.1f}%)"
        except Exception:
            return f"×{value}"
    if op == "Additive":
        try:
            v = float(value)
            sign = "+" if v >= 0 else ""
            return f"{sign}{v:g}"
        except Exception:
            return str(value)
    if op == "Set":
        return f"= {value}"
    return f"{op} {value}"

# ---------- load data ----------
print("Loading templates and localizations…")
techs = json.loads((TEMPLATES / "TITechTemplate.json").read_text(encoding="utf-8"))
projects = json.loads((TEMPLATES / "TIProjectTemplate.json").read_text(encoding="utf-8"))
effects_data = json.loads((TEMPLATES / "TIEffectTemplate.json").read_text(encoding="utf-8"))

loc_tech = parse_localization(LOCAL / "TITechTemplate.en")
loc_proj = parse_localization(LOCAL / "TIProjectTemplate.en")
loc_eff = parse_localization(LOCAL / "TIEffectTemplate.en")

# Index effects by dataName
effects_by_name = {e["dataName"]: e for e in effects_data}

# ---------- display names ----------
# Standing convention (2026-07-07; see docs/lessons/LESSONS-research.md): pages, H1 titles,
# and every wikilink use the IN-GAME localized displayName from
# TITechTemplate.en / TIProjectTemplate.en, falling back to the template
# friendlyName when no localization entry exists (~150 names differ).
friendly_lookup = {}  # dataName -> template friendlyName
type_lookup = {}      # dataName -> 'tech' or 'project'
_raw_display = {}
for t in techs:
    friendly_lookup[t["dataName"]] = t["friendlyName"]
    type_lookup[t["dataName"]] = "tech"
    _raw_display[t["dataName"]] = clean_html(
        loc_tech.get(f"TITechTemplate.displayName.{t['dataName']}", "")) or t["friendlyName"]
for p in projects:
    friendly_lookup[p["dataName"]] = p["friendlyName"]
    type_lookup[p["dataName"]] = "project"
    _raw_display[p["dataName"]] = clean_html(
        loc_proj.get(f"TIProjectTemplate.displayName.{p['dataName']}", "")) or p["friendlyName"]

# Distinct entries can share one in-game display name (seven faction "Talent
# Development" projects; Servants/Protectorate both show "Hydra Direct Support
# Network"). Ambiguous names would collide as filenames and wikilinks, so
# those entries keep their unique friendlyName.
_display_counts = Counter(_raw_display.values())
name_lookup = {}  # dataName -> display name (H1, link text, frontmatter name)
for _dn, _disp in _raw_display.items():
    name_lookup[_dn] = friendly_lookup[_dn] if _display_counts[_disp] > 1 else _disp

# Page name = display name sanitized for the filesystem (e.g. "Future Tech:
# Energy" -> "Future Tech- Energy"). Wikilinks must target the page name.
page_lookup = {dn: sanitize_filename(n) for dn, n in name_lookup.items()}
_dupes = sorted({pg for pg, c in Counter(page_lookup.values()).items() if c > 1})
if _dupes:
    raise SystemExit(f"Page-name collisions after localization fallback: {_dupes}")

def link_to(dn: str, table: bool = False) -> str:
    """Wikilink to a tech/project page, aliased when display name ≠ page name."""
    page = page_lookup.get(dn)
    if page is None:
        return f"[[{dn}]]"
    disp = name_lookup[dn]
    if disp != page:
        sep = "\\|" if table else "|"
        return f"[[{page}{sep}{disp}]]"
    return f"[[{page}]]"

def yaml_str(s: str) -> str:
    if re.search(r"[:#\[\]{}&*!|>'\"%@`,]", s) or s != s.strip():
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s

def migrate_legacy(path: Path, legacy: Path):
    """Rename a page keyed on the old friendlyName to its localized name so
    hand-added analysis overlays travel with it."""
    if legacy == path or not legacy.exists():
        return
    if path.exists() and not legacy.samefile(path):
        legacy.unlink()  # already renamed by hand — the old page is stale
    else:
        legacy.rename(path)  # samefile case = case-only rename on APFS

# Reverse map: dataName -> list of dataNames that have it as prereq (for "Unlocks" sections)
unlocks_by_name = defaultdict(list)  # prereq -> [dependents]
for t in techs:
    for pr in (t.get("prereqs") or []):
        unlocks_by_name[pr].append(t["dataName"])
for p in projects:
    for pr in (p.get("prereqs") or []):
        unlocks_by_name[pr].append(p["dataName"])
    alt = p.get("altPrereq0")
    if alt:
        unlocks_by_name[alt].append(p["dataName"])

# ---------- routing: determine where each project goes ----------
def project_route(p):
    """Return (top, sub) folder for a project: ('Faction Research', faction_name) or ('Projects', category)."""
    # factionAlways takes precedence (faction always has access)
    fa = p.get("factionAlways") or []
    if isinstance(fa, str):
        fa = [fa]
    fp = p.get("factionPrereq") or []
    if isinstance(fp, str):
        fp = [fp]
    # "Random" is a sentinel meaning a randomly-selected faction will roll for this project — not faction-locked
    fa = [f for f in fa if f != "Random"]
    fp = [f for f in fp if f != "Random"]
    factions = list(fa) + [f for f in fp if f not in fa]
    # Only route to Faction Research if exactly one faction is named (truly faction-locked).
    # Multi-faction projects are general projects with a coalition; they live under Projects/{Category}.
    if len(factions) == 1:
        return ("Faction Research", FACTION_DISPLAY.get(factions[0], factions[0]), factions)
    return ("Projects", CATEGORY_DISPLAY.get(p["techCategory"], p["techCategory"]), factions)

# ---------- writers ----------
def loc(d, *keys, default=""):
    for k in keys:
        if k in d:
            return clean_html(d[k])
    return default

def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

# ---------- hand-curated overlay preservation ----------
# Deep Strategic Review runs annotate generated tech/project pages in place:
# overlay frontmatter fields (analyzed / analysis_score / analysis_tier /
# snapshot_date / re_evaluated* / prev_* / re_eval_reason / …, some with
# multiline list values) and one or more "## Analysis (…)" body sections
# (re-scored pages carry two). Regeneration must carry ALL of these forward,
# never destroy them. Strategy: any frontmatter key the generator does not
# itself emit is treated as an overlay and preserved verbatim; every
# "## Analysis…" H2 section is preserved verbatim, in order, at the end of
# the page (before the data-name footer).
GENERATOR_FM_KEYS = {
    "name", "type", "scope", "category", "research_cost", "data_name",
    "factions", "one_time_globally", "repeatable", "requires_nation",
    "end_game", "aliases", "tags",
}
OVERLAY_SECTION_RE = re.compile(r"^## Analysis\b.*?(?=^## |^---\n\*Data name:)",
                                re.MULTILINE | re.DOTALL)

def extract_overlay_fm_blocks(old_fm: str) -> list:
    """Return frontmatter blocks (key line + indented continuation lines)
    for every key the generator does not emit, in original order."""
    blocks, cur_key, cur = [], None, []
    for line in old_fm.splitlines():
        m = re.match(r"^([A-Za-z_][\w-]*):", line)
        if m:
            if cur_key is not None and cur_key not in GENERATOR_FM_KEYS:
                blocks.append("\n".join(cur))
            cur_key, cur = m.group(1), [line]
        elif cur_key is not None:
            cur.append(line)
    if cur_key is not None and cur_key not in GENERATOR_FM_KEYS:
        blocks.append("\n".join(cur))
    return blocks

def merge_overlays(path: Path, content: str) -> str:
    """Carry hand-added analysis overlays from the existing page into fresh content."""
    if not path.exists():
        return content
    try:
        old = path.read_text(encoding="utf-8")
    except Exception:
        return content
    old_fm = ""
    if old.startswith("---\n"):
        end = old.find("\n---\n", 4)
        if end != -1:
            old_fm = old[4:end]
    fm_blocks = extract_overlay_fm_blocks(old_fm)
    sections = [m.group(0).rstrip() for m in OVERLAY_SECTION_RE.finditer(old)]
    if fm_blocks:
        content = re.sub(r"^tags:$", "\n".join(fm_blocks) + "\ntags:",
                         content, count=1, flags=re.MULTILINE)
    if sections:
        joined = "\n\n".join(sections)
        footer = "\n---\n*Data name:"
        idx = content.rfind(footer)
        if idx != -1:
            content = content[:idx] + "\n" + joined + "\n" + content[idx:]
        else:
            content = content.rstrip() + "\n\n" + joined + "\n"
    return content

def render_prereq_links(prereqs: list, alt: str = None) -> str:
    out = []
    for pr in prereqs or []:
        out.append(f"- {link_to(pr)}")
    if alt:
        out.append(f"- *(OR alternative)* {link_to(alt)}")
    return "\n".join(out) if out else "_None — available from start._"

def humanize_effect_name(data_name: str) -> str:
    s = re.sub(r"^Effect_", "", data_name)
    # Insert spaces before capitals: ManyAliensOnEarth -> Many Aliens On Earth
    s = re.sub(r"_+", " ", s)
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)
    s = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", s)
    # Strip trailing numeric tier (e.g. "02") if any - keeps the readable stem
    return s.strip()

def interpolate_tokens(text: str, value, operation: str, duration_months) -> str:
    """Replace {0}-{13} tokens in effect descriptions with a human-readable value."""
    if not text or value is None:
        return text
    if operation == "Multiplicative":
        try:
            pct = (float(value) - 1) * 100
            sign = "+" if pct >= 0 else ""
            repl = f"{sign}{pct:.1f}%".rstrip("0").rstrip(".") + ("" if "%" in f"{sign}{pct:.1f}" else "")
            # Re-stringify cleanly
            repl = f"{sign}{pct:g}%"
        except Exception:
            repl = str(value)
    elif operation == "Additive":
        try:
            v = float(value)
            sign = "+" if v >= 0 else ""
            repl = f"{sign}{v:g}"
        except Exception:
            repl = str(value)
    else:
        repl = str(value)
    out = re.sub(r"\{([0-9]|1[0-3])\}", repl, text)
    # {months token} → duration if known
    if duration_months and duration_months != -1:
        out = out.replace(repl + " months", f"{duration_months} months", 1)
    return out

def render_effects(effect_names: list) -> str:
    if not effect_names:
        return "_No direct effects._"
    out = []
    for en in effect_names:
        e = effects_by_name.get(en, {})
        # Try localized display, else humanize the dataName
        loc_disp = loc(loc_eff, f"TIEffectTemplate.displayName.{en}")
        disp = loc_disp if loc_disp else humanize_effect_name(en)
        desc = loc(loc_eff, f"TIEffectTemplate.description.{en}", default="")
        desc = re.sub(r"^\s*-\s*", "", desc)
        op = e.get("operation", "")
        val = e.get("value", None)
        target = e.get("effectTarget", "")
        duration = e.get("effectDuration", "")
        duration_months = e.get("duration_months", -1)
        if desc:
            desc = interpolate_tokens(desc, val, op, duration_months)
        line = f"- **{disp}**"
        if op and val is not None:
            line += f" — {fmt_value(op, val)}"
        if target and target != "SourceFaction":
            line += f"  _(target: {target})_"
        if duration and duration != "permanent":
            line += f"  _(duration: {duration})_"
        if desc:
            line += f"\n  - {desc}"
        out.append(line)
    return "\n".join(out)

def render_unlocks(data_name: str) -> str:
    deps = unlocks_by_name.get(data_name, [])
    if not deps:
        return "_Nothing in the tree depends on this._"
    # Sort: techs first then projects, alphabetical
    deps_sorted = sorted(set(deps), key=lambda d: (type_lookup.get(d, "z"), name_lookup.get(d, d)))
    return "\n".join(f"- {link_to(d)}" for d in deps_sorted)

# ---------- write tech files ----------
print(f"Writing {len(techs)} technology files…")
techs_by_cat = defaultdict(list)
for t in techs:
    techs_by_cat[t["techCategory"]].append(t)
    cat_disp = CATEGORY_DISPLAY[t["techCategory"]]
    folder = ROOT / "Tech Tree" / "Global Research" / cat_disp
    path = folder / (page_lookup[t["dataName"]] + ".md")
    migrate_legacy(path, folder / (sanitize_filename(t["friendlyName"]) + ".md"))

    name = name_lookup[t["dataName"]]
    summary = loc(loc_tech, f"TITechTemplate.summary.{t['dataName']}")
    description = loc(loc_tech, f"TITechTemplate.description.{t['dataName']}")
    quote = loc(loc_tech, f"TITechTemplate.quote.{t['dataName']}")
    cost = t.get("researchCost", 0)
    end_game = t.get("endGameTech", False)

    front = ["---",
             f"name: {yaml_str(name)}",
             "type: technology",
             "scope: global",
             f"category: {cat_disp}",
             f"research_cost: {cost}",
             f"data_name: {t['dataName']}"]
    if end_game:
        front.append("end_game: true")
    if t["friendlyName"] != name:
        front.append("aliases:")
        front.append(f"  - {yaml_str(t['friendlyName'])}")
    front.append("tags:")
    front.append("  - tech/global")
    front.append(f"  - category/{cat_disp.lower().replace(' ', '-')}")
    if end_game:
        front.append("  - tech/end-game")
    front.append("---")
    front_str = "\n".join(front)

    body = [
        front_str,
        "",
        f"# {CATEGORY_ICON.get(t['techCategory'],'')} {name}",
        "",
        f"**Category:** [[_{cat_disp}|{cat_disp}]]   **Cost:** {cost:,} research" + ("   **End-game tech**" if end_game else ""),
        "",
    ]
    if summary:
        body += [f"> {summary}", ""]
    if description:
        body += ["## Description", "", description, ""]
    body += ["## Prerequisites", "", render_prereq_links(t.get("prereqs") or []), ""]
    body += ["## Effects", "", render_effects(t.get("effects") or []), ""]
    body += ["## Unlocks", "", render_unlocks(t["dataName"]), ""]
    if quote:
        body += ["## Quote", "", "> " + quote.replace("\n", "\n> "), ""]
    body += ["---", f"*Data name: `{t['dataName']}`*", ""]

    write_file(path, merge_overlays(path, "\n".join(body)))

# ---------- write project files ----------
print(f"Writing {len(projects)} project files…")
projects_by_route = defaultdict(list)  # (top, sub) -> list of (project, factions)
for p in projects:
    top, sub, factions = project_route(p)
    projects_by_route[(top, sub)].append((p, factions))

    folder = ROOT / "Tech Tree" / top / sub
    path = folder / (page_lookup[p["dataName"]] + ".md")
    migrate_legacy(path, folder / (sanitize_filename(p["friendlyName"]) + ".md"))

    name = name_lookup[p["dataName"]]
    cat = p["techCategory"]
    cat_disp = CATEGORY_DISPLAY.get(cat, cat)
    summary = loc(loc_proj, f"TIProjectTemplate.summary.{p['dataName']}")
    description = loc(loc_proj, f"TIProjectTemplate.description.{p['dataName']}")
    quote = loc(loc_proj, f"TIProjectTemplate.quote.{p['dataName']}")
    cost = p.get("researchCost", 0)
    one_time = p.get("oneTimeGlobally", False)
    repeatable = p.get("repeatable", False)
    requires_nation = p.get("requiresNation", "")
    requires_milestone = p.get("requiredMilestone", "")
    requires_obj = p.get("requiredObjectiveName", "")
    init_chance = p.get("initialUnlockChance", 100)
    delta_chance = p.get("deltaUnlockChance", 0)
    max_chance = p.get("maxUnlockChance", 100)
    avail_chance = p.get("factionAvailableChance", 100)
    org_granted = p.get("orgGranted", "")
    resources = p.get("resourcesGranted", []) or []

    factions_disp = [FACTION_DISPLAY.get(f, f) for f in factions]

    front = ["---",
             f"name: {yaml_str(name)}",
             "type: project",
             "scope: " + ("faction" if factions else "general"),
             f"category: {cat_disp}",
             f"research_cost: {cost}",
             f"data_name: {p['dataName']}"]
    if p["friendlyName"] != name:
        front.append("aliases:")
        front.append(f"  - {yaml_str(p['friendlyName'])}")
    if factions_disp:
        front.append("factions:")
        for f in factions_disp:
            front.append(f"  - {f}")
    if one_time:
        front.append("one_time_globally: true")
    if repeatable:
        front.append("repeatable: true")
    if requires_nation:
        front.append(f"requires_nation: {requires_nation}")
    front.append("tags:")
    front.append("  - tech/project")
    front.append(f"  - category/{cat_disp.lower().replace(' ', '-')}")
    if factions_disp:
        for f in factions_disp:
            slug = f.lower().replace(' ', '-')
            front.append(f"  - faction/{slug}")
    if one_time:
        front.append("  - project/one-time")
    if repeatable:
        front.append("  - project/repeatable")
    front.append("---")
    front_str = "\n".join(front)

    body = [front_str, "",
            f"# {CATEGORY_ICON.get(cat,'')} {name}",
            ""]

    meta_bits = [f"**Category:** {cat_disp}"]
    if cost == -1:
        meta_bits.append("**Cost:** _special / triggered_")
    else:
        meta_bits.append(f"**Cost:** {cost:,} research")
    if factions_disp:
        meta_bits.append("**Faction:** " + ", ".join(f"[[_{f}|{f}]]" for f in factions_disp))
    if one_time:
        meta_bits.append("**One-time globally**")
    if repeatable:
        meta_bits.append("**Repeatable**")
    if requires_nation:
        meta_bits.append(f"**Required nation:** `{requires_nation}`")
    body.append("   ".join(meta_bits))
    body.append("")

    if summary:
        body += [f"> {summary}", ""]
    if description:
        body += ["## Description", "", description, ""]

    body += ["## Prerequisites", "", render_prereq_links(p.get("prereqs") or [], p.get("altPrereq0")), ""]

    # Unlock chance / availability
    avail_lines = []
    if avail_chance != 100:
        avail_lines.append(f"- **Faction-available chance:** {avail_chance}% (chance the project is available at all to a given faction)")
    if init_chance != 100 or delta_chance != 0 or max_chance != 100:
        avail_lines.append(f"- **Unlock chance:** starts at {init_chance}% per qualifying month, +{delta_chance}% each tick, up to {max_chance}%")
    if requires_milestone:
        avail_lines.append(f"- **Required milestone:** `{requires_milestone}`")
    if requires_obj:
        avail_lines.append(f"- **Required objective:** `{requires_obj}`")
    if avail_lines:
        body += ["## Availability", "", "\n".join(avail_lines), ""]

    body += ["## Effects", "", render_effects(p.get("effects") or []), ""]

    if org_granted:
        body += ["## Organization Granted", "", f"- `{org_granted}`", ""]
    if resources:
        body += ["## Resources Granted", ""]
        for r in resources:
            if isinstance(r, dict):
                body.append(f"- {r}")
            else:
                body.append(f"- {r}")
        body.append("")

    body += ["## Unlocks", "", render_unlocks(p["dataName"]), ""]
    if quote:
        body += ["## Quote", "", "> " + quote.replace("\n", "\n> "), ""]
    body += ["---", f"*Data name: `{p['dataName']}`*", ""]

    write_file(path, merge_overlays(path, "\n".join(body)))

# ---------- write category MOCs ----------
print("Writing category MOCs…")
def write_category_moc(folder: Path, title: str, intro: str, items: list, kind: str = "tech"):
    """items: list of (friendlyName, cost, summary, dataName)."""
    items_sorted = sorted(items, key=lambda x: (x[1] if x[1] >= 0 else 99999999, x[0]))
    lines = [
        "---",
        f"name: {title}",
        f"type: moc",
        "tags:",
        "  - moc",
        f"  - category/{title.lower().replace(' ', '-')}",
        "---",
        "",
        f"# {title}",
        "",
        intro,
        "",
        f"**{len(items)} entries** in this category.",
        "",
        f"| {'Tech' if kind=='tech' else 'Project'} | Cost | data_name | Summary |",
        "|---|---:|---|---|",
    ]
    for name, cost, summary, dn in items_sorted:
        cost_disp = f"{cost:,}" if cost >= 0 else "_—_"
        snippet = (summary or "").replace("|", "\\|").replace("\n", " ")
        if len(snippet) > 140:
            snippet = snippet[:137] + "…"
        lines.append(f"| {link_to(dn, table=True)} | {cost_disp} | `{dn}` | {snippet} |")
    lines.append("")
    write_file(folder / f"_{title}.md", "\n".join(lines))

# Global research category MOCs
for cat, ts in techs_by_cat.items():
    cat_disp = CATEGORY_DISPLAY[cat]
    items = []
    for t in ts:
        s = loc(loc_tech, f"TITechTemplate.summary.{t['dataName']}")
        items.append((name_lookup[t["dataName"]], t.get("researchCost", 0), s, t["dataName"]))
    intro = f"{CATEGORY_ICON.get(cat,'')} **{cat_disp}** — global research technologies in the {cat_disp.lower()} branch."
    write_category_moc(ROOT / "Tech Tree" / "Global Research" / cat_disp, cat_disp, intro, items, kind="tech")

# Project category MOCs (general projects)
projects_by_cat_general = defaultdict(list)
for p in projects:
    top, sub, factions = project_route(p)
    if top == "Projects":
        s = loc(loc_proj, f"TIProjectTemplate.summary.{p['dataName']}")
        faction_names = [FACTION_DISPLAY.get(f, f) for f in factions]
        projects_by_cat_general[sub].append((name_lookup[p["dataName"]], p.get("researchCost", 0), s, p["dataName"], faction_names))

for cat_disp, items in projects_by_cat_general.items():
    intro = f"**{cat_disp}** — projects in this folder are open to any faction or available to a coalition of multiple factions. Projects locked to a single faction live under [[_Faction Research|Faction Research]]."
    # Sort: open-to-all first, multi-faction next, then by cost
    items_sorted = sorted(items, key=lambda x: (1 if x[4] else 0, x[1] if x[1] >= 0 else 99999999, x[0]))
    title = f"Projects — {cat_disp}"
    n_open = sum(1 for x in items if not x[4])
    n_multi = len(items) - n_open
    lines = [
        "---",
        f"name: {title}",
        f"type: moc",
        "tags:",
        "  - moc",
        f"  - category/{cat_disp.lower().replace(' ', '-')}",
        "  - tech/project",
        "---",
        "",
        f"# {title}",
        "",
        intro,
        "",
        f"**{n_open} open** + **{n_multi} multi-faction** = {len(items)} entries.",
        "",
        "| Project | Cost | data_name | Available to | Summary |",
        "|---|---:|---|---|---|",
    ]
    for name, cost, summary, dn, faction_names in items_sorted:
        cost_disp = f"{cost:,}" if cost >= 0 else "_—_"
        snippet = (summary or "").replace("|", "\\|").replace("\n", " ")
        if len(snippet) > 140:
            snippet = snippet[:137] + "…"
        avail = "Any faction" if not faction_names else ", ".join(f"[[_{f}\\|{f}]]" for f in faction_names)
        lines.append(f"| {link_to(dn, table=True)} | {cost_disp} | `{dn}` | {avail} | {snippet} |")
    lines.append("")
    write_file(ROOT / "Tech Tree" / "Projects" / cat_disp / f"_Projects - {cat_disp}.md", "\n".join(lines))

# Faction MOCs — include exclusive (top == Faction Research) and shared (multi-faction)
projects_by_faction = defaultdict(list)
for p in projects:
    top, sub, factions = project_route(p)
    if not factions:
        continue
    s = loc(loc_proj, f"TIProjectTemplate.summary.{p['dataName']}")
    exclusive = (len(factions) == 1)
    for fac_id in factions:
        fac = FACTION_DISPLAY.get(fac_id, fac_id)
        # Other factions sharing this project
        others = [FACTION_DISPLAY.get(x, x) for x in factions if x != fac_id]
        projects_by_faction[fac].append((name_lookup[p["dataName"]], p.get("researchCost", 0), s, p["techCategory"], p["dataName"], exclusive, others))

for fac, items in projects_by_faction.items():
    # Exclusive (truly faction-locked) first, then shared, both sorted by category then cost
    items_sorted = sorted(items, key=lambda x: (0 if x[5] else 1, x[3], x[1] if x[1] >= 0 else 99999999, x[0]))
    n_exclusive = sum(1 for x in items if x[5])
    n_shared = len(items) - n_exclusive
    lines = [
        "---",
        f"name: {fac}",
        "type: moc",
        "tags:",
        "  - moc",
        f"  - faction/{fac.lower().replace(' ', '-')}",
        "---",
        "",
        f"# {fac}",
        "",
        f"_{FACTION_TAGLINE.get(fac, '')}._",
        "",
        f"**{n_exclusive} exclusive** + **{n_shared} shared** = {len(items)} projects available to {fac}.",
        "",
        "Exclusive projects live in this folder. Shared projects (also available to other factions) live under [[_Projects|Projects]] in their category folder; this table cross-links to them.",
        "",
        "| Scope | Project | Category | Cost | data_name | Shared with | Summary |",
        "|---|---|---|---:|---|---|---|",
    ]
    for name, cost, summary, cat, dn, exclusive, others in items_sorted:
        cost_disp = f"{cost:,}" if cost >= 0 else "_—_"
        snippet = (summary or "").replace("|", "\\|").replace("\n", " ")
        if len(snippet) > 100:
            snippet = snippet[:97] + "…"
        scope = "**Exclusive**" if exclusive else "Shared"
        shared_with = "—" if exclusive else ", ".join(f"[[_{f}\\|{f}]]" for f in others)
        lines.append(f"| {scope} | {link_to(dn, table=True)} | {CATEGORY_DISPLAY.get(cat, cat)} | {cost_disp} | `{dn}` | {shared_with} | {snippet} |")
    lines.append("")
    write_file(ROOT / "Tech Tree" / "Faction Research" / fac / f"_{fac}.md", "\n".join(lines))

# ---------- top-level MOCs ----------
print("Writing top-level MOCs…")

# Global Research MOC
gr_lines = [
    "---", "name: Global Research", "type: moc", "tags:", "  - moc", "  - tech/global", "---",
    "",
    "# Global Research",
    "",
    "**Technologies** are pure-science research that all of humanity benefits from. They are voted on for the three shared global research slots — when a slot completes, the faction that contributed the most research to it picks the next entry in that slot. Every faction can see and benefit from completed technologies.",
    "",
    f"There are **{len(techs)} technologies** across seven categories.",
    "",
    "| Category | Count | Index |",
    "|---|---:|---|",
]
for cat in ["SocialScience", "InformationScience", "LifeScience", "MilitaryScience", "Materials", "Energy", "SpaceScience"]:
    cat_disp = CATEGORY_DISPLAY[cat]
    n = len(techs_by_cat.get(cat, []))
    gr_lines.append(f"| {CATEGORY_ICON[cat]} {cat_disp} | {n} | [[_{cat_disp}|Open index]] |")
gr_lines += ["", "## Starting research (2026 scenario)",
             "The 2026 campaign begins with three global research slots already running:",
             f"- {link_to('WeAreNotAlone')}",
             f"- {link_to('Skywatch')}",
             f"- {link_to('MissionToSpace')}",
             "",
             "(See [[Research System]] for the full mechanics.)",
             ""]
write_file(ROOT / "Tech Tree" / "Global Research" / "_Global Research.md", "\n".join(gr_lines))

# Projects MOC
proj_lines = [
    "---", "name: Projects", "type: moc", "tags:", "  - moc", "  - tech/project", "---",
    "",
    "# Projects (general)",
    "",
    "**Projects** are applied research — engineering and development to put theory into practice. Unlike technologies, projects are researched in a faction's private research slot and benefit only that faction. They unlock new modules, ships, organisations, country options, and political effects.",
    "",
    "This index lists projects available to **any faction**. Faction-locked projects live under [[_Faction Research|Faction Research]].",
    "",
    f"**{sum(len(v) for v in projects_by_cat_general.values())} general projects** across the categories below.",
    "",
    "| Category | Count | Index |",
    "|---|---:|---|",
]
for cat_disp, items in sorted(projects_by_cat_general.items()):
    proj_lines.append(f"| {cat_disp} | {len(items)} | [[_Projects - {cat_disp}|Open index]] |")
proj_lines.append("")
write_file(ROOT / "Tech Tree" / "Projects" / "_Projects.md", "\n".join(proj_lines))

# Faction Research MOC
fr_lines = [
    "---", "name: Faction Research", "type: moc", "tags:", "  - moc", "  - tech/project", "---",
    "",
    "# Faction Research",
    "",
    "Projects gated to specific factions. A project is listed here if it has a `factionPrereq` (only that faction can ever research it) or `factionAlways` (that faction always has access regardless of unlock rolls).",
    "",
    "| Faction | Tagline | Projects | Index |",
    "|---|---|---:|---|",
]
for fac in ["Resistance", "Initiative", "Servants", "Protectorate", "Academy", "Humanity First", "Project Exodus", "Aliens"]:
    n = len(projects_by_faction.get(fac, []))
    fr_lines.append(f"| **{fac}** | {FACTION_TAGLINE[fac]} | {n} | [[_{fac}|Open index]] |")
fr_lines.append("")
write_file(ROOT / "Tech Tree" / "Faction Research" / "_Faction Research.md", "\n".join(fr_lines))

# Tech Tree MOC
tt_lines = [
    "---", "name: Tech Tree", "type: moc", "tags:", "  - moc", "---",
    "",
    "# Terra Invicta — Tech Tree",
    "",
    f"_Compiled from game data version present in the official 1.0 templates (Jan 2026 release)._",
    "",
    "Terra Invicta divides research into two parallel tracks:",
    "",
    f"- **[[_Global Research|Global Research]]** — {len(techs)} pure-science technologies. Three shared slots that all factions vote on.",
    f"- **Projects** — {len(projects)} applied-engineering projects, researched privately by each faction.",
    f"   - **[[_Projects|General projects]]** — available to any faction (faction picks from rolling unlock chances).",
    f"   - **[[_Faction Research|Faction-locked projects]]** — gated to one or more specific factions.",
    "",
    "See [[Research System]] for how the slots, voting, unlocks, and prerequisites actually work in play.",
    "",
    "## Quick links",
    "",
    "### By global category",
]
for cat in ["SocialScience", "InformationScience", "LifeScience", "MilitaryScience", "Materials", "Energy", "SpaceScience"]:
    cat_disp = CATEGORY_DISPLAY[cat]
    tt_lines.append(f"- {CATEGORY_ICON[cat]} [[_{cat_disp}|{cat_disp}]] ({len(techs_by_cat.get(cat,[]))} techs)")
tt_lines += ["", "### By faction"]
for fac in ["Resistance", "Initiative", "Servants", "Protectorate", "Academy", "Humanity First", "Project Exodus", "Aliens"]:
    n = len(projects_by_faction.get(fac, []))
    tt_lines.append(f"- [[_{fac}|{fac}]] — {n} faction projects")
tt_lines.append("")
write_file(ROOT / "Tech Tree" / "_Tech Tree.md", "\n".join(tt_lines))

# Research System overview
rs = """---
name: Research System
type: reference
tags:
  - mechanics
  - reference
---

# Research System

Terra Invicta has **two distinct research tracks** running in parallel.

## Global Research (Technologies)

- Pure science. Once a technology completes, **all factions** benefit from its effects.
- There are **three global research slots**. Every faction can pour research into any of the three slots simultaneously.
- When a slot finishes, the faction that contributed the **most** research to that slot **picks the next technology** to fill it. (If you are losing the race, you can deny a slot to a rival but you cannot pick what they queue.)
- The 2026 scenario starts with three slots already running: [[We Are Not Alone]], [[Skywatch]], and [[Mission To Space]].
- Categories: 🏛️ Social Science · 💻 Information Science · 🧬 Life Science · ⚔️ Military Science · 🔧 Materials · ⚡ Energy · 🚀 Space Science.

## Projects (Applied Research)

- Applied engineering. Each faction researches projects in its **own private slot**; only the researching faction gets the effect.
- Projects don't appear automatically. Each project has an **availability roll** (`factionAvailableChance`) and a per-month **unlock roll** (starts at `initialUnlockChance`, climbs by `deltaUnlockChance` each tick up to `maxUnlockChance`) — usually contingent on prerequisite techs/projects, milestones, or world conditions being met.
- Many projects are **one-time globally** — only the first faction to research them gets the effect (the rest cannot research them again).
- A few projects are **repeatable** — you can stack the effect.
- Some projects are **faction-restricted**: either always available to a specific faction (`factionAlways`) or only available to a specific faction (`factionPrereq`).
- Projects can grant: passive faction effects, exploration unlocks (planets and Lagrange points), new ship modules / weapons / hulls, **organizations** (cards equipped on councilors), end-game victory milestones, and country-specific political opportunities.

## Prerequisites

- Most entries list one or more **prereqs** that all must be completed.
- Some projects also have a single **alternate prereq** (`altPrereq0`) — completing _either_ the main set _or_ the alt unlocks the project.
- A handful of projects gate on a **required milestone** (a campaign event, e.g. "Aliens have arrived") or **objective** (a specific in-game investigation).
- Country projects gate on `requiresNation` — only available if you control or influence that nation.

## Reading these notes

Each entry has:
- A **summary** (one-line in-game blurb).
- A **description** (full in-game text).
- **Prerequisites** as `[[wikilinks]]` to other entries.
- **Effects** with operation (Additive / Multiplicative / Set), value, and target.
- **Unlocks** — every other entry that has _this_ as a prerequisite (computed from the data, so the chain works in both directions).
- A **quote** when the game provides one.
- The internal `dataName` for cross-referencing with mods or save files.

## Faction → in-game ID

The data files use council enum names. Translation:

| Display | Data ID | Stance |
|---|---|---|
| Resistance | `ResistCouncil` | Resist |
| Initiative | `ExploitCouncil` | Exploit |
| Servants | `SubmitCouncil` | Submit |
| Protectorate | `AppeaseCouncil` | Appease |
| Academy | `CooperateCouncil` | Cooperate |
| Humanity First | `DestroyCouncil` | Destroy |
| Project Exodus | `EscapeCouncil` | Escape |
| Aliens (Hydra) | `AlienCouncil` | (NPC) |
"""
write_file(ROOT / "Research System.md", rs)

# Knowledge-base home page
# NOTE: if you hand-edit the generated _Home.md, mirror the edit here or it
# will be lost on the next regen.
home = f"""---
name: Terra Invicta
type: home
tags:
  - moc
updated: {date.today().isoformat()}
---

# Terra Invicta — Knowledge Base

A reference knowledge base for **Terra Invicta** (Pavonis Interactive / Hooded Horse — full release January 2026), generated from the game's own template files. Use these notes for tech-tree planning, faction-research lookups, and chasing prerequisite chains.

## Start here

- [[_Tech Tree|Tech Tree (overview)]]
- [[Research System]] — how slots, unlock rolls, and prerequisites actually work
- [[_Global Research|Global Research]] — {len(techs)} pure-science technologies
- [[_Projects|Projects]] — {sum(len(v) for v in projects_by_cat_general.values())} general (any-faction) applied projects
- [[_Faction Research|Faction Research]] — faction-locked projects

## Faction quick links

- [[_Resistance|Resistance]] · [[_Initiative|Initiative]] · [[_Servants|Servants]] · [[_Protectorate|Protectorate]]
- [[_Academy|Academy]] · [[_Humanity First|Humanity First]] · [[_Project Exodus|Project Exodus]] · [[_Aliens|Aliens]]


## Ship Modules

- [[_Ship Modules|Ship Modules reference]] — comparison tables for every weapon, drive, hull, armor, etc.

## Source

Game JSON templates extracted from `TITechTemplate.json`, `TIProjectTemplate.json`, `TIEffectTemplate.json` and the matching English localization files, mirrored from the local game install by `scripts/sync_game_data.py` (which also prints an install-vs-mirror drift report).

Counts: **{len(techs)} technologies + {len(projects)} projects** = {len(techs)+len(projects)} entries.
"""
write_file(ROOT / "_Home.md", home)

print("Done.")
print(f"Total files: techs={len(techs)} projects={len(projects)}")
