#!/usr/bin/env python3
"""Operational recon for attacking an alien hab: defenses, ground-assault math,
your marine-capable ships/fleets, local shipyards, and nearby alien fleets.

Usage:
    python3 assault_planner.py <save.json> --target "<alien base displayName>" [--faction <templateName>]

Reports:
  1. Target hab modules: SCV (station space-combat value), defense weapons, power sources.
  2. Ground-defense estimate intact vs after bombarding defense modules
     (marine-rule values; Citadel-class counts once per matching rule — Victory
     Conditions note: assault P = 1 − 0.5 × 0.775^(attacker − defender)).
  3. Specimen-milestone modules present (Griffins / WarDogs / Salamanders carriers).
  4. Your fleets: location, ship count, marine assault value (MarineAssaultUnit 4 /
     Advanced 6 / Elite 8 per module), by design.
  5. Your habs at the target body (shipyard presence).
  6. All alien fleets with location + ship count (threat/response picture).
"""
import json, gzip, argparse, os
from collections import defaultdict

TPL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
MARINE_SHIP_MODULES = {'MarineAssaultUnit': 4, 'AdvancedMarineAssaultUnit': 6, 'EliteMarineAssaultUnit': 8}
MARINE_RULES = {'MarinePlatoon', 'MarineCompany', 'MarineBattalion', 'Griffins', 'WarDogs', 'Salamanders'}
SPECIMEN_RULES = {'Griffins': 'AccessLiveGriffin', 'WarDogs': 'AccessWarDogCorpus', 'Salamanders': 'AccessLiveSalamander'}

def key(k):
    return k['value'] if isinstance(k, dict) else k

from ti_config import load_save  # THE shared loader: gzip magic + BOM, memoized

def fleet_name(v, my_fid):
    """Player fleet names live in displayNameByFaction (per-faction map); displayName is
    often empty and rivals see procedural Romeo-names (save-verified 2026-07)."""
    for e in (v.get('displayNameByFaction') or []):
        if key(e.get('Key')) == my_fid and e.get('Value'):
            return e['Value']
    return v.get('displayName') or '(unnamed)'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('save')
    ap.add_argument('--target', required=True)
    ap.add_argument('--faction', default=None)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    from ti_config import require_faction
    args.faction = require_faction(args.faction)
    say = (lambda *a, **kw: None) if args.json else print

    gs = load_save(args.save)['gamestates']
    hab_tpl = {t['dataName']: t for t in json.load(open(os.path.join(TPL_DIR, 'TIHabModuleTemplate.json')))}

    habs = {key(h['Key']): h['Value'] for h in gs['PavonisInteractive.TerraInvicta.TIHabState']}
    mods = [m['Value'] for m in gs['PavonisInteractive.TerraInvicta.TIHabModuleState']]
    facs = {key(f['Key']): f['Value'] for f in gs['PavonisInteractive.TerraInvicta.TIFactionState']}
    fac_name = {k: v.get('templateName') for k, v in facs.items()}
    my_fid = [k for k, v in fac_name.items() if v == args.faction][0]
    alien_fid = [k for k, v in fac_name.items() if v == 'AlienCouncil'][0]
    me = facs[my_fid]

    sec2hab = {}
    for hid, h in habs.items():
        for s in (h.get('sectors') or []):
            sec2hab[key(s)] = hid

    # hab site -> body name (via TIHabSiteState -> parent body displayName)
    sites = {key(s['Key']): s['Value'] for s in gs.get('PavonisInteractive.TerraInvicta.TIHabSiteState', [])}
    bodies = {}
    for cls in ('TINaturalSpaceObjectState', 'TISpaceBodyState'):
        for b in gs.get(f'PavonisInteractive.TerraInvicta.{cls}', []) or []:
            bodies[key(b['Key'])] = b['Value'].get('displayName')

    def hab_body(h):
        site = sites.get(key(h.get('habSite')))
        if not site:
            return '(orbital/unknown)'
        for f in ('parentBody', 'spaceBody', 'naturalSpaceObject'):
            if site.get(f) is not None:
                return bodies.get(key(site[f]), '(unknown)')
        return '(unknown)'

    tgt_id = tgt = None
    for hid, h in habs.items():
        if h.get('displayName') == args.target:
            tgt_id, tgt = hid, h
    if not tgt:
        if args.json:
            raise SystemExit(f'target "{args.target}" not found')
        print(f'target "{args.target}" not found'); return
    body = hab_body(tgt)
    out = {'target': {'name': args.target, 'body': body, 'tier': tgt.get('tier'),
                      'owner': fac_name.get(key(tgt.get('faction')))},
           'target_modules': [], 'specimen_milestones': [], 'your_fleets': [],
           'your_habs_at_body': [], 'alien_fleets': []}
    say(f"# Assault recon: {args.target} — {body}, tier {tgt.get('tier')}, "
        f"owner {fac_name.get(key(tgt.get('faction')))}\n")

    say('## Target modules')
    scv = 0.0
    ground_intact = (tgt.get('tier') or 0)
    ground_after = (tgt.get('tier') or 0)
    specimens = defaultdict(list)
    power_mods, defense_mods = [], []
    for m in mods:
        if sec2hab.get(key(m.get('sector'))) != tgt_id or not m.get('exists') or m.get('destroyed'):
            continue
        tn = m.get('templateName')
        t = hab_tpl.get(tn, {})
        rules = set(t.get('specialRules') or [])
        mscv = m.get('_spaceCombatValue') or 0
        if m.get('powered'):
            scv += mscv
        marine_val = (t.get('specialRulesValue') or 0) * len(rules & MARINE_RULES)
        ground_intact += marine_val
        is_core = 'Core' in tn
        if is_core:
            ground_after += marine_val  # core survives until capture
        if mscv > 0:
            defense_mods.append(tn)
        if 'Reactor' in tn or 'Pile' in tn or 'Solar' in tn:
            power_mods.append(tn)
        for r in rules & set(SPECIMEN_RULES):
            specimens[SPECIMEN_RULES[r]].append(tn)
        flag = ' ⚔SCV' if mscv > 0 else (' ⚡pwr' if ('Reactor' in tn or 'Pile' in tn) else '')
        out['target_modules'].append({'module': tn, 'scv': mscv,
                                      'marine_defense': marine_val})
        say(f"  {tn:30} SCV={mscv:>9,.0f}  marineDef={marine_val:>3}{flag}")
    out['station_scv_active'] = scv
    out['ground_defense_intact'] = ground_intact
    out['ground_defense_after_bombardment'] = ground_after
    say(f"\nStation SCV (active): {scv:,.0f}")
    say(f"Ground defense INTACT: ~{ground_intact:.0f} (+ command-adviser/effect multipliers)")
    say(f"Ground defense after destroying non-core defense/barracks modules: ~{ground_after:.0f}")
    say(f"P(assault success) = 1 − 0.5 × 0.775^(attacker − defender): "
        f"+9 over → 95%, +18 over → 99.5%")
    say('\nSpecimen milestones carried by this hab:')
    for ms, srcs in specimens.items():
        out['specimen_milestones'].append({'milestone': ms, 'count': len(srcs),
                                           'modules': sorted(set(srcs))})
        say(f"  {ms}: {len(srcs)} module(s) — {', '.join(sorted(set(srcs)))}")

    # player fleets + marine values
    ships = {key(s['Key']): s['Value'] for s in gs['PavonisInteractive.TerraInvicta.TISpaceShipState']}
    design = {d['dataName']: d for d in me.get('shipDesigns', [])}

    def ship_marines(s):
        d = design.get(s.get('templateName'), {})
        v = 0
        for e in (d.get('moduleTemplateEntries') or []):
            v += MARINE_SHIP_MODULES.get(e.get('moduleName'), 0)
        return v, d.get('_displayName', s.get('templateName'))

    say('\n## Your fleets (marine value = Σ MarineAssaultUnit 4/6/8)')
    for f in gs['PavonisInteractive.TerraInvicta.TISpaceFleetState']:
        v = f['Value']
        if key(v.get('faction')) != my_fid:
            continue
        sl = [ships[key(s)] for s in v.get('ships', []) if key(s) in ships]
        if not sl:
            continue
        mar = 0
        classes = defaultdict(int)
        for s in sl:
            mv, cls = ship_marines(s)
            mar += mv
            classes[cls] += 1
        loc = fleet_name(v, my_fid)
        comp = ', '.join(f'{c}×{n}' for c, n in sorted(classes.items(), key=lambda x: -x[1])[:6])
        out['your_fleets'].append({'fleet': loc, 'ships': len(sl), 'marine_value': mar,
                                   'composition': dict(classes)})
        say(f"  {loc:24} ships={len(sl):3} marineValue={mar:3}  [{comp}]")

    say(f'\n## Your habs at {body}')
    for hid, h in habs.items():
        if key(h.get('faction')) == my_fid and hab_body(h) == body:
            yard = []
            for m in mods:
                if sec2hab.get(key(m.get('sector'))) == hid and m.get('exists') and not m.get('destroyed'):
                    if any(x in (m.get('templateName') or '') for x in ('Shipyard', 'Spacedock', 'Spaceworks')):
                        yard.append(m.get('templateName') + ('' if m.get('constructionCompleted') else ' (building)'))
            out['your_habs_at_body'].append({'hab': h.get('displayName'),
                                             'tier': h.get('tier'), 'shipyards': yard})
            say(f"  {h.get('displayName'):30} T{h.get('tier')}  shipyards: {', '.join(yard) or '—'}")

    say('\n## Alien fleets (response picture)')
    rows = []
    for f in gs['PavonisInteractive.TerraInvicta.TISpaceFleetState']:
        v = f['Value']
        if key(v.get('faction')) != alien_fid:
            continue
        n = len(v.get('ships', []))
        if n:
            rows.append((v.get('displayName'), n))
    for name, n in sorted(rows, key=lambda x: -x[1]):
        out['alien_fleets'].append({'fleet': name, 'ships': n})
        say(f"  {name}: {n} ships")

    if args.json:
        print(json.dumps(out, indent=2, default=str))

if __name__ == '__main__':
    main()
