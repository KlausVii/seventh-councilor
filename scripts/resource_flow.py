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


from ti_config import load_save  # THE shared loader: gzip magic + BOM, memoized


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
    ap.add_argument('--json', action='store_true')
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

    out = {'faction': args.faction, 'date': f'{now:%Y-%m-%d}', 'window_days': args.days,
           'net_by_resource': [], 'flows': []}
    if not args.json:
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
        if not args.json:
            print("\nNET by resource:")
        for r in RESOURCES:
            if abs(net.get(r, 0)) > 0.5:
                out['net_by_resource'].append({'resource': r, 'net': net[r],
                                               'stock': stock.get(r, 0)})
                if not args.json:
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
        sec = {'resource': r, 'stock': stock.get(r, 0), 'categories': [], 'net': 0.0}
        if r == 'Water' and fleet_water:
            sec['fleet_propellant_load'] = fleet_water
        if not args.json:
            print(f"\n## {r} by category (free stock now: {stock.get(r, 0):.1f}"
                  + (f"; fleet propellant load: {fleet_water:,.0f}" if r == 'Water' and fleet_water else "") + ")")
        tot = 0
        for cat, amt in sorted(agg.items(), key=lambda x: x[1]):
            sec['categories'].append({'category': cat, 'amount': amt, 'transactions': cnt[cat]})
            if not args.json:
                print(f"  {cat:<34} {amt:>12.1f}  ({cnt[cat]} tx)")
            tot += amt
        sec['net'] = tot
        if not args.json:
            print(f"  {'NET':<34} {tot:>12.1f}")
        out['flows'].append(sec)

    if args.json:
        print(json.dumps(out, indent=2, default=str))


if __name__ == '__main__':
    main()
