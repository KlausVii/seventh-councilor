#!/usr/bin/env python3
"""Nation scorecard, two-save diff, and multi-save event scan.

Usage:
    python3 nation_report.py 2026_CHN                      # newest save, full scorecard
    python3 nation_report.py 2026_CHN save.json            # that save, full scorecard
    python3 nation_report.py 2026_CHN before.gz after.gz   # DIFF: every score, before vs after
    python3 nation_report.py 2026_CHN --scan "_2033-5-*"   # scan rows across saves (bisection)
    python3 nation_report.py 2026_CHN --scan "_2033-5-*" --watch 2026_JPN
                                                           # also track a second nation's regions
                                                           # (find the save where an annexation landed)
    python3 nation_report.py 2026_RUS <earlier> <now> --recovery
                                                           # + project research/IP at cohesion
                                                           # recovery (×rest/current) and a
                                                           # months-to-rest ETA (LESSONS-politics C21)

Identify nations by templateName ('2026_USA'...), never displayName — displayName
renames on federation/annexation (see docs/lessons/REFERENCE.md). A displayName is
accepted as a fallback and resolved with a warning.

What it reads (all TINationState, save-verified — see LESSONS-politics C18/C19):
  live scalars   GDP, economyScore, education, democracy, cohesion, unrest, inequality,
                 militaryTechLevel, numNuclearWeapons, spaceFunding_year,
                 baseInvestmentPoints_month (= AVAILABLE monthly IP after penalties, not
                 the GDP base), sustainability, regions, armies, numControlPoints
  history heads  history*[0] (NEWEST-first, LESSONS-process P16): Research, Population,
                 Boost, MissionControl, SpaceFunding
  opinion        publicOpinion (current), per ideology

The scan mode prints one row per save (sorted by save counter) with the columns that
move during wars/annexations — regions, GDP, unrest, cohesion, available IP,
research[0], MC[0] — so you can bisect "when did X happen" the same way
opinion_trajectory.py bisects opinion steps.
"""
import glob
import gzip
import json
import os
import re
import sys

from ti_config import find_save_dir

NATIONS_KEY = "PavonisInteractive.TerraInvicta.TINationState"

SCALARS = [
    ("GDP", "GDP", "money"),
    ("economyScore", "Economy score (= (GDP/1e9)^0.35)", ""),
    ("baseInvestmentPoints_month", "Available IP/month (post-penalty)", ""),
    ("education", "Education", ""),
    ("democracy", "Democracy", ""),
    ("cohesion", "Cohesion", ""),
    ("cohesionRestState_dailyCache", "Cohesion rest state", ""),
    ("unrest", "Unrest", ""),
    ("unrestRestState_dailyCache", "Unrest rest state", ""),
    ("inequality", "Inequality", ""),
    ("militaryTechLevel", "Military tech", ""),
    ("numNuclearWeapons", "Nuclear weapons", "int"),
    ("spaceFunding_year", "Funding (in-game term)", ""),
    ("sustainability", "Sustainability", ""),
    ("numControlPoints", "CP slots", "int"),
]

# history*[0] heads are stored PER-MONTH in the save (REFERENCE § Nation history arrays);
# the game shows monthly figures, so label them /mo — never /day or /yr.
HIST_HEADS = [
    ("historyResearch", "Research/mo [0]"),
    ("historyPopulation", "Population (M) [0]"),
    ("historyBoost", "Boost/mo [0]"),
    ("historyMissionControl", "Mission Control [0]"),
    ("historySpaceFunding", "Funding/mo [0]"),
]


def _income_unit():
    """Player's income unit from config.json — 'month' (default) or 'day'; never 'year'."""
    try:
        from ti_config import CONFIG
        return 'day' if (CONFIG.get('income_display') or 'month').lower().startswith('d') else 'month'
    except Exception:
        return 'month'

IDEOLOGIES = ["Resist", "Exploit", "Escape", "Cooperate", "Appease", "Submit",
              "Destroy", "Undecided"]


from ti_config import load_save  # THE shared loader: gzip magic + BOM, memoized


def counter(path):
    m = re.search(r"save(\d+)", os.path.basename(path))
    return int(m.group(1)) if m else 0


def save_date(path):
    b = os.path.basename(path)
    m = re.search(r"_(\d{4}-\d{1,2}-\d{1,2})", b)
    return m.group(1) if m else b


def find_nation(gs, name):
    by_display = None
    for n in gs[NATIONS_KEY]:
        v = n.get("Value", n)
        if v.get("templateName") == name:
            return v
        if v.get("displayName") == name:
            by_display = v
    if by_display is not None:
        print(f"WARNING: '{name}' matched a displayName, not a templateName "
              f"(templateName: {by_display.get('templateName')}). displayNames rename "
              f"on federation/annexation — prefer the templateName.", file=sys.stderr)
    return by_display


def fmt(v, kind=""):
    if v is None:
        return "-"
    if kind == "int":
        return str(int(v))
    if kind == "money":
        return f"${v/1e12:,.2f}T"
    if isinstance(v, float):
        return f"{v:,.3f}"
    return str(v)


def head(nation, key):
    arr = nation.get(key) or []
    return arr[0] if arr else None  # [0] = NEWEST (P16)


def rows_for(nation):
    rows = []
    u = _income_unit()
    for key, label, kind in SCALARS:
        val = nation.get(key)
        if key == "spaceFunding_year" and isinstance(val, (int, float)):
            # save stores it per-YEAR; show it in the player's unit, never yearly
            val = val / (365.25 if u == "day" else 12.0)
            label = f"Funding{'/day' if u == 'day' else '/mo'} (in-game 'Funding')"
        rows.append((label, val, kind))
    rows.append(("Regions", len(nation.get("regions") or []), "int"))
    rows.append(("Armies", len(nation.get("armies") or []), "int"))
    rows.append(("At war with (nations)", len(nation.get("wars") or []), "int"))
    for key, label in HIST_HEADS:
        rows.append((label, head(nation, key), ""))
    return rows


def report(nation, path):
    print(f"# {nation.get('displayName')} ({nation.get('templateName')}) — "
          f"{os.path.basename(path)}")
    for label, val, kind in rows_for(nation):
        print(f"  {label:34} {fmt(val, kind)}")
    op = nation.get("publicOpinion") or {}
    print("  Public opinion: " + "  ".join(
        f"{i} {op.get(i, 0)*100:.1f}%" for i in IDEOLOGIES if op.get(i, 0) >= 0.005))
    print("\n  NOTE: history heads refresh on their own cadence and can lag a same-day")
    print("  event by one sample; live scalars are current. In-game tooltips are ground")
    print("  truth for any disagreement (LESSONS-process P1, LESSONS-politics C18).")


def diff(nation_a, nation_b, path_a, path_b):
    print(f"# {nation_b.get('displayName')} ({nation_b.get('templateName')}) — "
          f"{save_date(path_a)} vs {save_date(path_b)}")
    print(f"  {'score':34} {'before':>14} {'after':>14} {'change':>12}")
    for (label, va, kind), (_, vb, _) in zip(rows_for(nation_a), rows_for(nation_b)):
        delta = ""
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)) and va != vb:
            d = vb - va
            delta = f"{d:+,.3f}" if isinstance(d, float) else f"{d:+d}"
            if kind == "money":
                delta = f"{d/1e12:+,.2f}T"
        print(f"  {label:34} {fmt(va, kind):>14} {fmt(vb, kind):>14} {delta:>12}")


def _date_delta_days(p0, p1):
    import datetime
    def parse(p):
        try:
            y, m, d = map(int, save_date(p).split("-")); return datetime.date(y, m, d)
        except Exception:
            return None
    a, b = parse(p0), parse(p1)
    return (b - a).days if a and b else None


def recovery(nat_now, path_now, nat_prior=None, path_prior=None):
    """Project research & IP once cohesion recovers to its rest state, and (with an earlier
    post-event save) estimate WHEN. Research/IP scale ~linearly with cohesion (LESSONS-politics
    C21): value_at_rest ≈ current × (rest / current_cohesion)."""
    coh = nat_now.get("cohesion"); rest = nat_now.get("cohesionRestState_dailyCache")
    print("\n## Recovery projection — research & IP scale ~linearly with cohesion (C21)")
    if coh is None or rest is None or coh <= 0:
        print("  cohesion / cohesionRestState_dailyCache unavailable — cannot project."); return
    factor = rest / coh
    research = head(nat_now, "historyResearch") or 0.0   # per-month (P16)
    ip = nat_now.get("baseInvestmentPoints_month") or 0.0
    gap = rest - coh
    if gap > 0.01:
        print(f"  cohesion {coh:.2f} → rest {rest:.2f}  (gap +{gap:.2f}, ×{factor:.2f} headroom)")
        print(f"  Research/mo: {research:,.0f} → ~{research*factor:,.0f}  (+{research*(factor-1):,.0f})")
        print(f"  IP/mo:       {ip:,.1f} → ~{ip*factor:,.1f}  (+{ip*(factor-1):,.1f})")
    elif gap < -0.01:
        print(f"  cohesion {coh:.2f} is ABOVE rest {rest:.2f} (gap {gap:.2f}) — expect DECAY toward rest;")
        print(f"  research/IP would fall ~×{factor:.2f} if it settles there (no recovery upside).")
    else:
        print(f"  cohesion {coh:.2f} ≈ rest {rest:.2f} — already settled; no material change expected.")
    if nat_prior is not None and gap > 0.01:
        coh0 = nat_prior.get("cohesion"); dd = _date_delta_days(path_prior, path_now)
        if coh0 is not None and dd and dd > 0:
            rate = (coh - coh0) / dd
            if rate > 1e-4:
                print(f"  timing: cohesion +{rate*30.44:.2f}/mo ({save_date(path_prior)}→{save_date(path_now)}, "
                      f"{dd}d) → ~{gap/rate/30.44:.1f} months to rest (rough; annexation penalty decay may "
                      f"speed the early part, Unity pips shorten it)")
            else:
                print(f"  timing: cohesion not rising between those saves (Δ{coh-coh0:+.2f}) — give two "
                      f"POST-event saves to estimate the recovery rate.")
    elif gap > 0.01:
        print("  timing: run `nation_report <nation> <earlier-post-event> <now> --recovery` to estimate when.")
    print("  [estimate — linearity inferred from the IP model + flat-through-crash research; in-game is truth]")


def scan(name, paths, watch=None):
    cols = f"{'date':>10} {'file#':>7} {'regions':>7} {'GDP $T':>8} {'unrest':>7} " \
           f"{'cohesn':>7} {'IP/mo':>7} {'res[0]':>8} {'MC[0]':>6}"
    if watch:
        cols += f" {watch + ' regions':>14}"
    print(cols)
    for p in sorted(paths, key=counter):
        gs = load_save(p)["gamestates"]
        nat = find_nation(gs, name)
        if nat is None:
            print(f"{save_date(p):>10} — nation {name} not found")
            continue
        row = (f"{save_date(p):>10} {counter(p) % 10**7:>7} "
               f"{len(nat.get('regions') or []):>7} "
               f"{(nat.get('GDP') or 0)/1e12:>8.2f} "
               f"{nat.get('unrest', 0):>7.2f} {nat.get('cohesion', 0):>7.2f} "
               f"{nat.get('baseInvestmentPoints_month', 0):>7.1f} "
               f"{head(nat, 'historyResearch') or 0:>8.1f} "
               f"{head(nat, 'historyMissionControl') or 0:>6.0f}")
        if watch:
            w = find_nation(gs, watch)
            row += f" {len(w.get('regions') or []) if w else '-':>14}"
        print(row)


def main(argv):
    if "-h" in argv or "--help" in argv or len(argv) < 1:
        print(__doc__)
        return 0 if argv else 1
    name = argv[0]
    rest = argv[1:]
    recov = False
    if "--recovery" in rest:
        recov = True
        rest = [x for x in rest if x != "--recovery"]
    watch = None
    if "--watch" in rest:
        i = rest.index("--watch")
        watch = rest[i + 1]
        rest = rest[:i] + rest[i + 2:]
    if rest and rest[0] == "--scan":
        save_dir = find_save_dir()
        if not save_dir:
            raise SystemExit("No save dir found — set save_dir in config.json.")
        paths = glob.glob(str(save_dir) + "/*" + rest[1] + "*")
        if not paths:
            raise SystemExit(f"No saves match {rest[1]!r} in {save_dir}")
        scan(name, paths, watch)
        return 0
    if not rest:
        from ti_config import newest_save
        p = newest_save()
        if not p:
            raise SystemExit("No saves found — set save_dir in config.json.")
        rest = [str(p)]
    if len(rest) == 1:
        gs = load_save(rest[0])["gamestates"]
        nat = find_nation(gs, name)
        if nat is None:
            raise SystemExit(f"Nation {name!r} not found in {rest[0]}")
        report(nat, rest[0])
        if recov:
            recovery(nat, rest[0])
    elif len(rest) == 2:
        a, b = (load_save(p)["gamestates"] for p in rest)
        na, nb = find_nation(a, name), find_nation(b, name)
        if na is None or nb is None:
            raise SystemExit(f"Nation {name!r} missing from one of the saves")
        diff(na, nb, rest[0], rest[1])
        if recov:
            recovery(nb, rest[1], na, rest[0])
    else:
        scan(name, rest, watch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
