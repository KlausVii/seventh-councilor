#!/usr/bin/env python3
"""
Alien (Hydra) factual military-progress timeline across a campaign's saves.

For each target in-game date it locates the matching save file (exact date in
the filename, else nearest within a tolerance), then reports the aliens'
ship count, fleet tonnage (kt), and base count — the factual columns of a
campaign log's "Table A" (alien hate/progress timeline).

Strength proxy = tonnage (kt): TISpaceShipState carries no serialized combat
value (only a `spaceCombatValueDataDirty` flag), so Σ mass is the ground-truth
size metric, consistent with Table F. Player ship/kt reported alongside for the
balance-of-power read.

Usage:
    python3 alien_progress_timeline.py 2029-12 2030-06 ...   # explicit dates
    python3 alien_progress_timeline.py                # dates from a campaign-log md
                                                      # (set TI_CAMPAIGN_LOG to a file
                                                      #  with a "### Table A" section)
    python3 alien_progress_timeline.py --newest       # just the newest save

Player faction comes from config.json; override with --faction <templateName>.
Pass --json for machine-readable output (one JSON document, same columns).

⚠️ Ground truth — includes undetected alien assets. Historical record only.
"""
import sys, os, re, glob, json

if '--help' in sys.argv or '-h' in sys.argv:
    print(__doc__ or 'See the module docstring for usage.')
    raise SystemExit(0)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_snapshot import load_save, get_factions, extract_alien_progress

from ti_config import find_save_dir, require_faction

SAVES = str(find_save_dir() or "")
# Campaign-log markdown with a "### Table A" section listing dates.
# Default: the campaign workspace log (campaign/log.md); override via TI_CAMPAIGN_LOG.
_DEFAULT_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "campaign", "log.md")
MD = os.environ.get("TI_CAMPAIGN_LOG") or (
    _DEFAULT_LOG if os.path.isfile(_DEFAULT_LOG) else None)

DATE_RE = re.compile(r'\w+save\d+_(\d{4})-(\d{1,2})-(\d{1,2})(?:[_\s.]|$)')


def build_index():
    """date(YYYY-MM-DD) -> filepath. Prefer .json over .gz; on ties prefer the
    lexically-largest filename (highest save id / latest write)."""
    idx = {}
    if not SAVES:
        sys.exit('no save dir auto-detected; set "save_dir" in config.json')
    files = glob.glob(os.path.join(SAVES, "*save*"))
    for f in sorted(files):
        b = os.path.basename(f)
        m = DATE_RE.match(b)
        if not m:
            continue
        y, mo, d = (int(x) for x in m.groups())
        key = f"{y:04d}-{mo:02d}-{d:02d}"
        is_json = f.endswith('.json')
        prev = idx.get(key)
        if prev is None:
            idx[key] = f
        else:
            prev_json = prev.endswith('.json')
            # prefer json; then prefer the later-sorted filename
            if (is_json and not prev_json) or (is_json == prev_json and b > os.path.basename(prev)):
                idx[key] = f
    return idx


def to_days(datestr):
    y, m, d = (int(x) for x in datestr.split('-'))
    return y * 372 + m * 31 + d  # rough monotone ordinal, fine for nearest-match


def find_save(idx, target, tol_days=20):
    if target in idx:
        return idx[target], target, 0
    td = to_days(target)
    best = None
    for k, f in idx.items():
        dd = abs(to_days(k) - td)
        if dd <= tol_days and (best is None or dd < best[2]):
            best = (f, k, dd)
    return best if best else (None, None, None)


def table_a_dates():
    dates = []
    in_a = False
    if not MD or not os.path.isfile(MD):
        sys.exit("no dates given: pass YYYY-MM-DD dates or --newest, or point "
                 "TI_CAMPAIGN_LOG at a campaign-log md with a '### Table A' section")
    with open(MD, encoding='utf-8') as fh:
        for line in fh:
            if line.startswith('### Table A'):
                in_a = True
                continue
            if in_a and line.startswith('### '):
                break
            if in_a:
                m = re.match(r'\|\s*(\d{4}-\d{2}-\d{2})\s*\|', line)
                if m:
                    dates.append(m.group(1))
    return dates


def main():
    args = sys.argv[1:]
    faction_cli = None
    if '--faction' in args:
        i = args.index('--faction')
        try:
            faction_cli = args[i + 1]
        except IndexError:
            sys.exit("--faction needs a value (a faction templateName)")
        del args[i:i + 2]
    json_out = '--json' in args
    if json_out:
        args.remove('--json')
    faction = require_faction(faction_cli)
    idx = build_index()
    if args == ['--newest']:
        newest = max(glob.glob(os.path.join(SAVES, "*save*_*.json")), key=os.path.getmtime)
        # resolve to the in-game date in the filename so the normal loop handles it
        m = DATE_RE.match(os.path.basename(newest))
        if not m:
            sys.exit(f"newest save has no parseable date: {newest}")
        y, mo, d = (int(x) for x in m.groups())
        targets = [f"{y:04d}-{mo:02d}-{d:02d}"]
    else:
        targets = args if args else table_a_dates()

    if not json_out:
        print(f"{'target':10s} {'save date':10s} {'Δd':>3s}  {'A.Ships':>7s} {'A.kt':>7s} "
              f"{'A.Base':>6s}  {'P.Ships':>7s} {'P.kt':>7s}")
        print("-" * 72)
    rows = []
    out_rows = []
    for t in targets:
        f, sd, dd = find_save(idx, t)
        if not f:
            if not json_out:
                print(f"{t:10s} {'—':10s}  no save within tolerance")
            rows.append((t, None))
            out_rows.append({'target': t, 'save_date': None,
                             'error': 'no save within tolerance'})
            continue
        data = load_save(f)
        gs = data['gamestates']
        # include_hidden: this is the backward-looking historical record (Table A),
        # the documented legitimate use of full ground truth — not live intel.
        ap = extract_alien_progress(gs, get_factions(gs), faction_template=faction,
                                    include_hidden=True)
        if not json_out:
            print(f"{t:10s} {sd:10s} {dd:>3d}  {ap['alien_ships']:>7d} {ap['alien_kt']:>7.1f} "
                  f"{ap['alien_bases']:>6d}  {ap['player_ships']:>7d} {ap['player_kt']:>7.1f}")
        rows.append((t, ap))
        out_rows.append({'target': t, 'save_date': sd, 'delta_days': dd,
                         'alien_ships': ap['alien_ships'], 'alien_kt': ap['alien_kt'],
                         'alien_bases': ap['alien_bases'],
                         'player_ships': ap['player_ships'], 'player_kt': ap['player_kt']})
    if json_out:
        print(json.dumps({'faction': faction, 'rows': out_rows}, indent=2, default=str))
    return rows


if __name__ == '__main__':
    main()
