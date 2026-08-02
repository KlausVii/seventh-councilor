#!/usr/bin/env python3
"""resource_flow.py — "where did my <resource> go?" Aggregates a faction's
resource Transactions by CATEGORY over a time window, so a sudden stockpile
drop can be attributed to its real cause.

The faction's `Transactions` dict (on TIFactionState) is keyed by category name
(e.g. 'ResupplyOperation', 'Construct Hab Module', 'Daily Income', 'Purchase
Org', ...); each value is a list of {Resource, Amount, Date}. This script sums
Amount per category for the requested resource within N days of the save's
current date — exactly the ledger the in-game economy screen summarizes, but
broken out by category and resource so you can see, e.g., that a water crash was
fleet ResupplyOperation (NSWR propellant), not a mining shortfall.

Known big SINK categories: ResupplyOperation / ResupplyAndRepairOperation (ship
propellant refill + repair — water for NSWR/water drives, also other props),
Construct Hab Module (space-build resource backfill — also pays in boost/money),
Purchase Org, Advise, SabotageProject. Known SOURCE: Daily Income (passive
mining/hab/region income), Spoils, Sell Space Resources To Earth, Project
Completion.

Usage:
    python resource_flow.py <save.json> [--faction <templateName>]
        [--resource Water] [--days 45]
    # omit --resource to print a one-line net per resource, then water/boost detail
"""
import json, gzip, argparse, os
from collections import defaultdict
from datetime import datetime

RESOURCES = ['Money', 'Influence', 'Operations', 'Boost', 'Water', 'Volatiles',
             'Metals', 'NobleMetals', 'Fissiles', 'Antimatter', 'Exotics', 'Research']


def load_save(p):
    with open(p, 'rb') as f:
        magic = f.read(2)
    op = gzip.open if magic == b'\x1f\x8b' else open
    with op(p, 'rt', encoding='utf-8-sig') as f:  # BOM: Windows saves
        return json.load(f)


def kv(gs, suf):
    key = next((k for k in gs if k.endswith(suf)), None)
    out = []
    for e in (gs.get(key) or []):
        k = e.get('Key'); kid = k.get('value') if isinstance(k, dict) else k
        out.append((kid, e.get('Value', {})))
    return out


def dt(d):
    return datetime(d['year'], d['month'], d['day'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('save')
    ap.add_argument('--faction', default=None)
    ap.add_argument('--resource', default=None)
    ap.add_argument('--days', type=int, default=45)
    args = ap.parse_args()
    from ti_config import require_faction
    args.faction = require_faction(args.faction)
    save = load_save(args.save)
    gs = save['gamestates']
    now = dt(kv(gs, 'TITimeState')[0][1]['currentDateTime'])
    fac = next(v for _, v in kv(gs, 'TIFactionState') if v.get('templateName') == args.faction)
    tx = fac.get('Transactions', {})
    stock = fac.get('resources', {})
    fleet_water = (fac.get('fleetWetMassDuringHighestShipMaintainence') or {}).get('Water')

    print(f"# Resource flow — {args.faction}, {now:%Y-%m-%d}, last {args.days} days")
    if args.resource:
        resources = [args.resource]
    else:
        # net per resource first
        net = defaultdict(float)
        for cat, entries in tx.items():
            if not isinstance(entries, list):
                continue
            for e in entries:
                if e.get('Date') and 0 <= (now - dt(e['Date'])).days <= args.days:
                    net[e.get('Resource')] += e.get('Amount', 0)
        print("\nNET by resource:")
        for r in RESOURCES:
            if abs(net.get(r, 0)) > 0.5:
                print(f"  {r:<12} {net[r]:>12.1f}   (stock {stock.get(r, 0):.0f})")
        resources = ['Water', 'Boost']  # default detail

    for r in resources:
        agg = defaultdict(float); cnt = defaultdict(int)
        for cat, entries in tx.items():
            if not isinstance(entries, list):
                continue
            for e in entries:
                if e.get('Resource') != r:
                    continue
                d = e.get('Date')
                if d and 0 <= (now - dt(d)).days <= args.days:
                    agg[cat] += e.get('Amount', 0); cnt[cat] += 1
        if not agg:
            continue
        print(f"\n## {r} by category (free stock now: {stock.get(r, 0):.1f}"
              + (f"; fleet propellant load: {fleet_water:,.0f}" if r == 'Water' and fleet_water else "") + ")")
        tot = 0
        for cat, amt in sorted(agg.items(), key=lambda x: x[1]):
            print(f"  {cat:<34} {amt:>12.1f}  ({cnt[cat]} tx)")
            tot += amt
        print(f"  {'NET':<34} {tot:>12.1f}")


if __name__ == '__main__':
    main()
