#!/usr/bin/env python3
"""tech_contributions.py — who is winning each global-tech race, and research-windfall
forensics ("how did faction X gain thousands of points on one tech overnight?").

Give it two or more saves (any order; they're sorted by in-game date). For every global
tech in progress (or just --tech), it prints per-faction contributions per save and the
deltas between consecutive saves. Any interval where a faction's gain RATE exceeds
--jump-threshold (RP per day) is flagged as a WINDFALL, and the tool then greps that faction's `Transactions` ledger for
non-"Daily Income" Research entries in the window — the transaction CATEGORY names the
mechanic (e.g. "Steal Project"; see LESSONS-research R24 for that mission's exact payout:
project copy + 10 × the daily-research gap, landing ×(1 + category bonus) via the thief's
research weights).

Also answers the quieter question: who is top contributor on each slot — i.e. who controls
what gets queued next when the tech completes.

Usage:
    python3 tech_contributions.py <save1> <save2> [...] [--tech Ultracapacitors]
        [--jump-threshold 300] [--json]

With a single save it prints the current standings only (no deltas).
"""
import json, argparse, sys, os
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mine_completion_timeline import load_save, kv_items, parse_dt


def faction_names(gs):
    return {f: v.get('templateName') for f, v in kv_items(gs, 'TIFactionState')}


def tech_progress(gs):
    grs = gs[next(k for k in gs if k.endswith('TIGlobalResearchState'))][0]['Value']
    out = {}
    for t in grs.get('techProgress') or []:
        contrib = {}
        for e in t.get('factionContributions') or []:
            k = e['Key']['value'] if isinstance(e['Key'], dict) else e['Key']
            contrib[k] = e['Value']
        out[t['techTemplateName']] = {'total': t.get('accumulatedResearch', 0),
                                      'contrib': contrib}
    return out


def research_windfalls(gs, fid, d0, d1):
    """Non-daily-income Research transactions for faction fid with d0 < date <= d1."""
    for f, v in kv_items(gs, 'TIFactionState'):
        if f != fid:
            continue
        for cat, lst in (v.get('Transactions') or {}).items():
            if cat == 'Daily Income' or not isinstance(lst, list):
                continue
            for e in lst:
                if not (isinstance(e, dict) and e.get('Resource') == 'Research'):
                    continue
                dt = e.get('Date')
                try:
                    when = parse_dt(dt)
                except Exception:
                    continue
                if d0 < when <= d1:
                    yield cat, e.get('Amount'), when
    return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('saves', nargs='+')
    ap.add_argument('--tech', default=None, help='limit to one tech templateName (substring ok)')
    ap.add_argument('--jump-threshold', type=float, default=300.0,
                    help='flag intervals where a faction gains more than this per DAY')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()

    snaps = []
    for p in args.saves:
        gs = load_save(p)['gamestates']
        now = parse_dt(gs[next(k for k in gs if k.endswith('TITimeState'))][0]
                       ['Value']['currentDateTime'])
        snaps.append({'path': p, 'now': now, 'gs': gs})
    snaps.sort(key=lambda s: s['now'])
    names = faction_names(snaps[-1]['gs'])

    progs = [tech_progress(s['gs']) for s in snaps]
    techs = sorted(set().union(*[set(p) for p in progs]))
    if args.tech:
        techs = [t for t in techs if args.tech.lower() in t.lower()]
        if not techs:
            sys.exit(f'no in-progress tech matches {args.tech!r}')

    report = []
    for tech in techs:
        rows, windfalls = [], []
        for i, (s, pr) in enumerate(zip(snaps, progs)):
            entry = pr.get(tech)
            if entry is None:
                continue
            rows.append({'date': s['now'], 'total': entry['total'],
                         'contrib': entry['contrib']})
        for i in range(1, len(rows)):
            for fid, v in rows[i]['contrib'].items():
                d = v - rows[i - 1]['contrib'].get(fid, 0)
                days = max(1, (rows[i]['date'] - rows[i - 1]['date']).days)
                if d / days >= args.jump_threshold:
                    evid = list(research_windfalls(snaps[-1]['gs'], fid,
                                                   rows[i - 1]['date'], rows[i]['date']))
                    windfalls.append({'faction': names.get(fid, fid), 'delta': d,
                                      'window_days': days,
                                      'from': rows[i - 1]['date'], 'to': rows[i]['date'],
                                      'transactions': evid})
        if rows:
            leader = max(rows[-1]['contrib'], key=lambda f: rows[-1]['contrib'][f])
            report.append({'tech': tech, 'rows': rows, 'windfalls': windfalls,
                           'leader': names.get(leader, leader)})

    if args.json:
        def enc(o):
            from datetime import datetime
            return o.isoformat() if isinstance(o, __import__('datetime').datetime) else str(o)
        print(json.dumps(report, indent=2, default=enc))
        return

    multi = len(snaps) > 1
    for r in report:
        last = r['rows'][-1]
        print(f"\n# {r['tech']} — total {last['total']:,.0f} — "
              f"leader: {r['leader']} (controls the next queue pick)")
        for row in r['rows']:
            cs = '  '.join(f"{names.get(f, f)} {v:,.0f}"
                           for f, v in sorted(row['contrib'].items(),
                                              key=lambda kv: -kv[1]))
            print(f"  {row['date']:%Y-%m-%d}: {cs}")
        for w in r['windfalls']:
            print(f"  ⚡ WINDFALL: {w['faction']} +{w['delta']:,.0f} in {w['window_days']}d "
                  f"({w['from']:%m-%d} → {w['to']:%m-%d})")
            if w['transactions']:
                for cat, amt, when in w['transactions']:
                    print(f"     ledger: \"{cat}\" +{amt:,.0f} Research on {when:%Y-%m-%d %H:%M}")
            elif multi:
                print('     no ledger entry found in the newest save — the windfall may be '
                      'ordinary income (check their weights) or the TX aged out of the ledger')
    if not report:
        print('No global techs in progress matched.')


if __name__ == '__main__':
    main()
