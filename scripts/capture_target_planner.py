#!/usr/bin/env python3
"""capture_target_planner.py — which ENEMY mining hab should my marines take?

Answers "my assault ship is fuelled and loaded, whose mine do I take over?" —
for ANY resource, not just the one the fleet happens to be named after. Ranks
every non-player hab that runs a mine by what the CAPTURED SITE would pay ME,
weighted by MY current scarcity, then gates each candidate on:

  - GROUND DEFENCE — marine-rule values on the target's modules (MarinePlatoon /
    Company / Battalion / Griffins / WarDogs / Salamanders), same table
    assault_planner.py uses. Assault odds use the Victory-Conditions formula
    P = 1 − 0.5 × 0.775^(attacker − defender).
  - ΔV — straight-line distance and the fleet's usable ΔV. Coarse: run
    `transfer_eta.py --fleet "<name>" --to "<body>"` for the real burn/coast/burn
    number, and the in-game transfer planner is truth over both.
  - MC — a captured mine joins MY mining network and pays the SAME quadratic
    margin a new one would ((active−36)²/2, E38). A capture is not free MC.

🕶️ SPOILER GUARD: a rival hab's module list is hidden until you have intel on
it. Targets with intel 0 are listed with their PUBLIC facts only (owner, body,
site yields — the site is surveyed data you already hold) and their defences
shown as `??` with a "scout first" verdict. Never quote a defence number the
in-game UI wouldn't show you.

Usage:
    python3 capture_target_planner.py [save] [--fleet "Fissile getter"]
        [--faction X] [--resource volatiles] [--top N] [--include-aliens] [--json]
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extract_snapshot import (load_save, kv_items, deref, get_factions,
                              faction_id_by_template, fac_id_from_field,
                              get_game_date, extract_mine_inventory)
from mine_completion_timeline import derive_K_income
from ti_config import CONFIG, newest_save, find_templates_dir

AU = 1.496e11
FREE_MINES = 36
RES = ('metals', 'water', 'volatiles', 'nobles', 'fissiles')
MARINE_RULES = {'MarinePlatoon', 'MarineCompany', 'MarineBattalion',
                'Griffins', 'WarDogs', 'Salamanders'}
MARINE_SHIP_MODULES = {'MarineAssaultUnit': 4, 'AdvancedMarineAssaultUnit': 6,
                       'EliteMarineAssaultUnit': 8}
# Rival-hab intel is graded (observed levels: 0.1 / 0.3 / 0.5 / 0.75 / 1.0). Only
# report a module-derived defence number at or above this level; below it the save
# still HAS the modules but the in-game UI does not show them to you.
INTEL_SEES_MODULES = 0.5


def assault_odds(attacker, defender):
    """Victory-Conditions ground-assault formula (see assault_planner.py),
    clamped to [0,1] — the raw expression runs hugely negative once the
    defender out-numbers the attacker, which is a 0% capture, not −8000%."""
    return max(0.0, min(1.0, 1 - 0.5 * (0.775 ** (attacker - defender))))


def network_mc(active):
    return max(0, active - FREE_MINES) ** 2 / 2.0


def load_module_templates():
    tdir = find_templates_dir()
    if not tdir:
        raise SystemExit("scripts/templates/ missing — run sync_game_data.py first")
    return {t['dataName']: t for t in json.load(
        open(os.path.join(str(tdir), 'TIHabModuleTemplate.json'), encoding='utf-8'))}


def body_position(body):
    gp = (body or {}).get('globalPosition') or {}
    return (gp.get('x', 0.0), gp.get('y', 0.0), gp.get('z', 0.0))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('save', nargs='?', help='save file (default: newest)')
    ap.add_argument('--faction', default=CONFIG.get('faction'))
    ap.add_argument('--fleet', default=None,
                    help='assaulting fleet name (default: your best marine fleet)')
    ap.add_argument('--resource', choices=RES, default=None,
                    help='rank by one resource instead of scarcity-weighted value')
    ap.add_argument('--top', type=int, default=12)
    ap.add_argument('--name', default=None,
                    help='only targets whose hab name contains this (case-insensitive)')
    ap.add_argument('--include-aliens', action='store_true',
                    help='include alien habs (default: rival human factions only)')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()

    path = args.save or newest_save()
    if not path:
        raise SystemExit("no save found — pass a path or set save_dir in config.json")
    if not args.json:
        print(f"(save: {path})")

    gs = load_save(path)['gamestates']
    gd = get_game_date(gs)
    date_str = gd[0] if isinstance(gd, tuple) else str(gd)[:10]
    factions = get_factions(gs)
    fid = faction_id_by_template(factions, args.faction)
    if fid is None:
        raise SystemExit(f"faction {args.faction!r} not found in save")
    alien_fid = next((k for k, v in factions.items()
                      if v.get('templateName') == 'AlienCouncil'), None)

    mod_tmpl = load_module_templates()
    mine_names = {n for n, t in mod_tmpl.items() if t.get('mine')}
    K, _ = derive_K_income(gs, fid)

    # my scarcity picture — same weighting the mine portfolio uses
    my_mines = extract_mine_inventory(gs, fid)
    weights = my_mines['weights_used']
    scarce = set(my_mines.get('scarce') or [])
    n_active = len(my_mines['active'])
    mc_per_capture = network_mc(n_active + 1) - network_mc(n_active)

    # intel map: (stateType, id) -> level
    pf = factions.get(fid, {})
    intel = {}
    for e in (pf.get('intel') or []):
        k = e.get('Key') or {}
        intel[((k.get('$type') or '').split('.')[-1], k.get('value'))] = e.get('Value', 0)

    # Retaliation picture: mutual hate + the owner's navy. Taking a mine is an act
    # of war against a faction that may or may not be able to answer — a defenceless
    # base belonging to a fleet-heavy faction is a trap, not a bargain.
    player_hate = {e['Key']['value']: e['Value']
                   for e in (pf.get('factionHate') or []) if isinstance(e, dict)}
    navy = {}
    for _, fv in kv_items(gs, 'PavonisInteractive.TerraInvicta.TISpaceFleetState'):
        ofid = fac_id_from_field(fv.get('faction'))
        if ofid is None:
            continue
        navy[ofid] = navy.get(ofid, 0) + len([s_ for s_ in (fv.get('ships') or [])])

    habs = dict(kv_items(gs, 'PavonisInteractive.TerraInvicta.TIHabState'))
    sites = dict(kv_items(gs, 'PavonisInteractive.TerraInvicta.TIHabSiteState'))
    bodies = dict(kv_items(gs, 'PavonisInteractive.TerraInvicta.TISpaceBodyState'))
    orbits = dict(kv_items(gs, 'PavonisInteractive.TerraInvicta.TIOrbitState'))
    ships = dict(kv_items(gs, 'PavonisInteractive.TerraInvicta.TISpaceShipState'))

    sec2hab = {}
    for hid, hv in habs.items():
        for s in (hv.get('sectors') or []):
            sec2hab[deref(s)] = hid
    mods_by_hab = {}
    for _, mv in kv_items(gs, 'PavonisInteractive.TerraInvicta.TIHabModuleState'):
        if mv.get('destroyed') or mv.get('archived'):
            continue
        hid = sec2hab.get(deref(mv.get('sector')))
        if hid is not None:
            mods_by_hab.setdefault(hid, []).append(mv)

    # ---- my assaulting fleet ----------------------------------------------
    # A TISpaceShipState carries no module list — marine capacity lives in the
    # faction's ship DESIGN (moduleTemplateEntries), same as assault_planner.py.
    designs = {d['dataName']: d for d in (pf.get('shipDesigns') or [])}

    def ship_marines(sv):
        d = designs.get(sv.get('templateName'), {})
        return sum(MARINE_SHIP_MODULES.get(e.get('moduleName'), 0)
                   for e in (d.get('moduleTemplateEntries') or []))

    fleets = []
    for flid, fv in kv_items(gs, 'PavonisInteractive.TerraInvicta.TISpaceFleetState'):
        if fac_id_from_field(fv.get('faction')) != fid:
            continue
        shiplist = [ships.get(deref(s), {}) for s in (fv.get('ships') or [])]
        if not shiplist:
            continue
        name = None
        for e in (fv.get('displayNameByFaction') or []):
            k = e.get('Key')
            if (k.get('value') if isinstance(k, dict) else k) == fid and e.get('Value'):
                name = e['Value']
        name = name or fv.get('displayName') or '(unnamed)'
        marines = sum(ship_marines(s) for s in shiplist)
        dv = min((s.get('currentDeltaV_kps') or 0) for s in shiplist)
        bid = deref(fv.get('barycenter')) or deref(fv.get('dockedLocation'))
        fleets.append({'name': name, 'marines': marines, 'dv_kps': dv,
                       'body_id': bid, 'ships': len(shiplist),
                       'in_transit': bool((fv.get('trajectory') or {}).get('destination'))})
    if args.fleet:
        mine_fleet = next((f for f in fleets if args.fleet.lower() in f['name'].lower()), None)
        if not mine_fleet:
            raise SystemExit(f"fleet {args.fleet!r} not found — have: "
                             + ', '.join(sorted(f['name'] for f in fleets)))
    else:
        mine_fleet = max(fleets, key=lambda f: (f['marines'], f['dv_kps']), default=None)
    if mine_fleet is None:
        raise SystemExit("no fleets found")
    origin = body_position(bodies.get(mine_fleet['body_id']))

    # ---- enemy mining habs -------------------------------------------------
    rows = []
    for hid, hv in habs.items():
        hfid = fac_id_from_field(hv.get('faction'))
        if hfid == fid or hfid is None:
            continue
        if hfid == alien_fid and not args.include_aliens:
            continue
        mods = mods_by_hab.get(hid, [])
        mines = [m for m in mods if m.get('templateName') in mine_names
                 and m.get('constructionCompleted')]
        if not mines:
            continue
        site = sites.get(deref(hv.get('habSite'))) or {}
        if not site:
            continue                       # station: no mine site to capture
        body = bodies.get(deref(site.get('parentBody'))) or {}
        raw = {r: site.get(r + '_day', 0) or 0 for r in RES}
        # what the site would pay ME: my mining multipliers, at the mine's tier
        tier_mod = max((mod_tmpl.get(m['templateName'], {}).get('miningModifier', 1)
                        for m in mines), default=1)
        income = {r: raw[r] * tier_mod * K[r] for r in RES}
        score = sum(raw[r] * weights.get(r, 1) for r in RES)

        iv = intel.get(('TIHabState', hid), 0) or 0
        if iv >= INTEL_SEES_MODULES:
            ground = 0
            for m in mods:
                t = mod_tmpl.get(m.get('templateName') or '', {})
                rules = set(t.get('specialRules') or [])
                ground += (t.get('specialRulesValue') or 0) * len(rules & MARINE_RULES)
        else:
            ground = None                  # hidden until scouted — do NOT guess

        d = math.dist(origin, body_position(body)) / AU if body else None
        their_hate = {e['Key']['value']: e['Value']
                      for e in (factions.get(hfid, {}).get('factionHate') or [])
                      if isinstance(e, dict)}.get(fid, 0)
        rows.append({
            'hab': hv.get('displayName') or '?',
            'owner_ships': navy.get(hfid, 0),
            'my_hate_of_owner': round(player_hate.get(hfid, 0), 1),
            'owner_hate_of_me': round(their_hate, 1),
            'owner': (factions.get(hfid, {}).get('displayName')
                      or factions.get(hfid, {}).get('templateName') or '?'),
            'body': body.get('displayName') or '?',
            'tier': hv.get('tier'),
            'intel': iv,
            'ground_defence': ground,
            'mine_tier_modifier': tier_mod,
            'raw_day': raw,
            'income_month_if_mine': {r: round(v, 1) for r, v in income.items() if v > 0.5},
            'feeds_scarce': sorted(scarce & {r for r in RES if income[r] > 0.5}),
            'score': round(score, 1),
            'au_from_fleet': round(d, 2) if d is not None else None,
            'capture_odds': (assault_odds(mine_fleet['marines'], ground)
                             if ground is not None else None),
        })

    if args.name:
        rows = [r for r in rows if args.name.lower() in r['hab'].lower()]
    if args.resource:
        rows.sort(key=lambda r: -r['income_month_if_mine'].get(args.resource, 0))
    else:
        # scarce-resource suppliers first, then weighted score
        rows.sort(key=lambda r: (not r['feeds_scarce'], -r['score']))

    out = {'save': path, 'date': date_str, 'fleet': mine_fleet,
           'my_scarce': sorted(scarce), 'mc_per_captured_mine': round(mc_per_capture, 1),
           'targets': rows}
    if args.json:
        print(json.dumps(out, indent=1, default=str))
        return

    f = mine_fleet
    print(f"\n# Capture-target planner — {args.faction} — {date_str}\n")
    print(f"Assaulting fleet: **{f['name']}** — {f['ships']} ship(s), "
          f"marine value **{f['marines']}**, ΔV {f['dv_kps']:.1f} kps"
          + (" ⚠ IN TRANSIT" if f['in_transit'] else "") + ".")
    print(f"My scarce resources: {', '.join(out['my_scarce']) or 'none'}. "
          f"Every captured mine adds **{out['mc_per_captured_mine']} MC** to my mining "
          f"network (quadratic, E38) — a capture is not free.\n")
    if not rows:
        print("No enemy mining bases found (stations have no mine site to take).")
        return
    print("| # | Target | Owner (navy) | Body | AU | Income/mo if mine were mine "
          "| Intel | Def | Odds | Their hate |")
    print("|---:|---|---|---|---:|---|---:|---:|---:|---:|")
    for i, r in enumerate(rows[:args.top], 1):
        inc = ', '.join(f"{k} {v:g}" for k, v in sorted(
            r['income_month_if_mine'].items(), key=lambda kv: -kv[1])[:3])
        dfc = '??' if r['ground_defence'] is None else r['ground_defence']
        odds = ('scout first' if r['capture_odds'] is None
                else f"{r['capture_odds'] * 100:.0f}%")
        print(f"| {i} | {r['hab']} | {r['owner']} ({r['owner_ships']} ships) | {r['body']} | "
              f"{r['au_from_fleet'] if r['au_from_fleet'] is not None else '?'} | {inc} "
              f"| {r['intel']:.2g} | {dfc} | {odds} | {r['owner_hate_of_me']:g} |")
    hidden = sum(1 for r in rows if r['ground_defence'] is None)
    if hidden:
        print(f"\n🕶️ {hidden} target(s) show `??` defences — you have no intel on that hab, "
              f"so the game hides its modules. Run InvestigateHab / send a councilor before "
              f"committing marines; the odds column is deliberately blank, not zero.")
    print("\nAU is straight-line at save time — run `transfer_eta.py --fleet "
          f"\"{f['name']}\" --to \"<body>\"` for burn/coast/burn, and trust the in-game "
          "transfer planner over both. Check the target body for defending FLEETS "
          "(`ops_query.py --theater`) before committing: this tool ranks the PRIZE, "
          "not the space battle.")


if __name__ == '__main__':
    main()
