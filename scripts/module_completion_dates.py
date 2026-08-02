#!/usr/bin/env python3
"""List a faction's under-construction hab modules with completion dates.

Usage:
    python3 module_completion_dates.py [save.json|gz] [--faction X] \
        [--module CommandCenter] [--module OperationsCenter] [--unpowered] [--destroyed]

For each matching under-construction module prints: completion date, hab name,
module, prior module being upgraded (if any), and the MC delta it will add when
it comes online. An upgrade REPLACES the prior module's state in the slot
(single TIHabModuleState, powered=false, prior kept only as
priorModuleTemplateName) — the prior module produces NOTHING while the upgrade
builds, so the delta vs the CURRENT top bar is the FULL new-module MC, not
new-minus-prior (corrected 2026-07-06; verified in the reference campaign).

Without --module filters, prints all under-construction modules grouped by type.

--unpowered switches mode: instead of under-construction modules, lists BUILT
but unpowered modules (constructionCompleted=true, powered=false) of the given
types — these produce nothing while off (lesson E25/E28).
"""
import argparse
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

GAME_DATA = Path(__file__).resolve().parent

# minimal MC table fallback if templates unavailable (matches docs/lessons/REFERENCE.md module table)
MC_FALLBACK = {
    'OperationsCenter': 4, 'CommandCenter': 10,
    'AdministrationNode': 0, 'AdministrationTower': 1, 'AdministrationComplex': 2,
}


def load_save(path):
    raw = open(path, 'rb').read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return json.loads(raw)


def load_mc_table():
    tpl = GAME_DATA / 'templates' / 'TIHabModuleTemplate.json'
    table = dict(MC_FALLBACK)
    if tpl.exists():
        for e in json.load(open(tpl)):
            mc = e.get('missionControl', 0)
            if mc:
                table[e['dataName']] = mc
    return table


def fmt_date(d):
    if isinstance(d, dict):
        return f"{d.get('year')}-{d.get('month'):02d}-{d.get('day'):02d}"
    return str(d)[:10]  # ISO datetime string in save


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('save', nargs='?', default=None,
                    help='save file; omitted = newest save auto-detected')
    ap.add_argument('--faction', default=None)
    ap.add_argument('--module', action='append', default=[])
    ap.add_argument('--unpowered', action='store_true',
                    help='list BUILT but unpowered modules instead')
    ap.add_argument('--destroyed', action='store_true',
                    help='attack forensics: list destroyed module slots with dates')
    args = ap.parse_args()
    if not args.save:
        from ti_config import newest_save
        args.save = newest_save()
        if not args.save:
            raise SystemExit("No save given and none auto-found — pass a save path.")
        print(f"(using newest save: {args.save})")
    from ti_config import require_faction
    args.faction = require_faction(args.faction)

    gs = load_save(args.save)['gamestates']
    factions = gs['PavonisInteractive.TerraInvicta.TIFactionState']
    player = next(f['Value'] for f in factions
                  if f['Value'].get('templateName') == args.faction)
    pid = player['ID']['value']

    habs = {h['Key']['value']: h['Value']
            for h in gs['PavonisInteractive.TerraInvicta.TIHabState']}
    # sector -> hab (modules link via sector ref)
    sectors = {}
    for hid, hv in habs.items():
        for s in hv.get('sectors', []):
            sectors[s['value']] = hv

    mc_table = load_mc_table()
    rows = []
    for m in gs['PavonisInteractive.TerraInvicta.TIHabModuleState']:
        mv = m['Value']
        if args.destroyed:
            if not mv.get('destroyed'):
                continue
        elif args.unpowered:
            if not mv.get('constructionCompleted') or mv.get('powered') \
                    or mv.get('destroyed') or mv.get('decommissioning'):
                continue
        elif mv.get('constructionCompleted'):
            continue
        name = mv.get('templateName') or '(anonymous rubble)'
        if args.module and not args.destroyed and name not in args.module:
            continue
        hab = sectors.get(mv.get('sector', {}).get('value'))
        if hab is None or hab.get('faction', {}).get('value') != pid:
            continue
        prior = mv.get('priorModuleTemplateName') or ''
        # prior module is offline during the upgrade (its state was replaced),
        # so completion adds the FULL new-module MC vs the current top bar
        rows.append({
            'date': fmt_date(mv.get('completionDate', '?')),
            'hab': hab.get('displayName', '?'),
            'module': name,
            'prior': prior,
            'mc_delta': mc_table.get(name, 0),
        })

    rows.sort(key=lambda r: r['date'])
    if not rows:
        print('No matching under-construction modules.')
        return

    by_month = defaultdict(lambda: [0, 0])  # month -> [count, mc]
    print(f"| Completion | Hab | Module | Upgrading from | ΔMC |")
    print(f"|---|---|---|---|---:|")
    total = 0
    for r in rows:
        total += r['mc_delta']
        by_month[r['date'][:7]][0] += 1
        by_month[r['date'][:7]][1] += r['mc_delta']
        print(f"| {r['date']} | {r['hab']} | {r['module']} | "
              f"{r['prior'] or '—'} | {r['mc_delta']:+d} |")
    if args.destroyed:
        print(f"\nTotal: {len(rows)} destroyed slots. Same-date clusters = attacks; "
              f"rubble is anonymous (template name lost).")
    else:
        print(f"\nTotal: {len(rows)} modules, net ΔMC {total:+d} when all complete.")
    print("\nBy month:")
    for mo in sorted(by_month):
        c, mc = by_month[mo]
        print(f"  {mo}: {c} modules, ΔMC {mc:+d}")


if __name__ == '__main__':
    main()
