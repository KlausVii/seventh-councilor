#!/usr/bin/env python3
"""capture_target_planner.py — which ENEMY mining hab should my marines take?

Answers "my assault ship is fuelled and loaded, whose mine do I take over?" —
for ANY resource, not just the one the fleet happens to be named after. Ranks
every non-player hab that runs a mine, and ranks it by the three things that
actually decide the operation:

  - TIME TO GET THERE, not distance. Ranking by AU recommended targets 9-11
    months out over an equivalent one 2.7 months away (2033-11-09: the player
    caught it — "46 Hestia is far. 97 Klotho is farther. you didn't seem to have
    checked the time-to-travel"). ETA comes from transfer_eta's burn-coast-burn
    model on straight-line distance; it ignores phasing and launch windows, so it
    is a SCREEN. Calibration vs the in-game planner that same day: 46 Hestia
    10.9mo modelled / 8.9mo actual (+22%), 97 Klotho 11.0 / 11.3 (−3%), ΔV exact.
    **The in-game transfer planner is truth** — verify the shortlist there.
  - CAN I ACTUALLY TAKE IT. Ground defence from the target's marine-rule modules
    (MarinePlatoon / Company / Battalion / Griffins / WarDogs / Salamanders),
    odds P = 1 − 0.5 × 0.775^(attacker − defender) CLAMPED to [0,1], and the
    marine value you must BRING for 89%. Candidates you cannot win today sort
    below ones you can: a 470 vol/mo prize you lose your marines against is not
    a plan (LESSONS-ships S29).
  - WHAT IT COSTS AFTER. The captured mine joins MY network at the quadratic
    margin ((active−36)²/2, E38); a leg that lands with <5 kps left is one-way
    and the ship lives there now; and the owner's navy + hate say whether the
    theft buys a war you can't answer.

Defence numbers are NOT hidden information: the in-game HABS list shows a rival
hab's defence/marine columns even at intel 0.1 (verified 2033-11-09, Leibniz Base
at intel 0.1 displaying 14 / 23). They ARE an under-read — the module sum missed
the real defending force by 3 there — so the tool plans against module_sum + 3
and says so. Site yields are surveyed data the player already holds.

Usage:
    python3 capture_target_planner.py [save] [--fleet "Mine stealer"]
        [--faction X] [--resource volatiles] [--name Pushkin] [--top N]
        [--include-aliens] [--json]
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extract_snapshot import (load_save, kv_items, deref, get_factions,
                              faction_id_by_template, fac_id_from_field,
                              get_game_date, extract_mine_inventory,
                              parse_intel_map)
from mine_completion_timeline import derive_K_income
from transfer_eta import eta_seconds
from ti_config import CONFIG, newest_save, find_templates_dir

AU = 1.496e11
FREE_MINES = 36
RES = ('metals', 'water', 'volatiles', 'nobles', 'fissiles')
MARINE_RULES = {'MarinePlatoon', 'MarineCompany', 'MarineBattalion',
                'Griffins', 'WarDogs', 'Salamanders'}
MARINE_SHIP_MODULES = {'MarineAssaultUnit': 4, 'AdvancedMarineAssaultUnit': 6,
                       'EliteMarineAssaultUnit': 8}
# The in-game HABS list shows a rival hab's defence + marine columns even at intel
# 0.1 (player screenshot, 2033-11-09: Leibniz Base, intel 0.1, list reads 14 / 23),
# so a module-derived defence estimate is NOT hidden information and the old
# intel >= 0.5 gate was hiding numbers the player could read off their own UI.
# What IS still gated: nothing here — but see DEFENCE_UNDER_READ.
#
# CALIBRATION (2033-11-09, ground truth = HABS list + module tooltip): Leibniz Base
# sums to 20 from modules (one MarineCompanyBarracks, tooltip "Combat strength: 20")
# while the list's marine column reads 23 — the module sum under-reads the real
# defending force by ~3 on a tier-3 colony. Single data point, so this is NOT
# modelled as a formula; it is reported as a floor and the "marines needed" column
# is computed off the CONSERVATIVE (higher) figure.
DEFENCE_UNDER_READ = 3


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
    intel = parse_intel_map(pf)

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
        accel = min((s.get('cruiseAcceleration_mps2') or 0) for s in shiplist)
        bid = deref(fv.get('barycenter')) or deref(fv.get('dockedLocation'))
        fleets.append({'name': name, 'marines': marines, 'dv_kps': dv,
                       'accel_mps2': accel, 'pos': ((fv.get('globalPosition') or {}).get('x', 0),
                                                    (fv.get('globalPosition') or {}).get('y', 0),
                                                    (fv.get('globalPosition') or {}).get('z', 0)),
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
    origin = mine_fleet['pos'] if any(mine_fleet['pos']) else \
        body_position(bodies.get(mine_fleet['body_id']))
    # ΔV budget: the planner's own trajectories spend nearly the whole tank on these
    # legs (in-game 2033-11-09: 46 Hestia 51.0 of 52.4 kps), so budget 97.5% like
    # transfer_eta does and REPORT the spend — an arrival with no ΔV left is a
    # one-way trip, which is a real cost, not a footnote.
    dv_budget_mps = mine_fleet['dv_kps'] * 1000 * 0.975

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
        ground = 0
        for m in mods:
            t = mod_tmpl.get(m.get('templateName') or '', {})
            rules = set(t.get('specialRules') or [])
            ground += (t.get('specialRulesValue') or 0) * len(rules & MARINE_RULES)
        # plan against the conservative figure, not the optimistic module sum
        ground_planning = ground + DEFENCE_UNDER_READ

        d_m = math.dist(origin, body_position(body)) if body else None
        d = d_m / AU if d_m is not None else None
        eta_days = dv_spent = None
        if d_m and mine_fleet['accel_mps2'] > 0:
            secs, dv_used, _mode = eta_seconds(d_m, mine_fleet['accel_mps2'], dv_budget_mps)
            eta_days = secs / 86400.0
            dv_spent = dv_used / 1000.0
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
            'ground_defence_planning': ground_planning,
            'marines_for_50pct': ground_planning,
            'marines_for_89pct': ground_planning + 6,
            'mine_tier_modifier': tier_mod,
            'raw_day': raw,
            'income_month_if_mine': {r: round(v, 1) for r, v in income.items() if v > 0.5},
            'feeds_scarce': sorted(scarce & {r for r in RES if income[r] > 0.5}),
            'score': round(score, 1),
            'au_from_fleet': round(d, 2) if d is not None else None,
            'eta_days': round(eta_days) if eta_days else None,
            'eta_months': round(eta_days / 30.44, 1) if eta_days else None,
            'dv_spend_kps': round(dv_spent, 1) if dv_spent else None,
            'dv_left_kps': (round(mine_fleet['dv_kps'] - dv_spent, 1)
                            if dv_spent is not None else None),
            'capture_odds': assault_odds(mine_fleet['marines'], ground_planning),
        })

    if args.name:
        rows = [r for r in rows if args.name.lower() in r['hab'].lower()]
    if args.resource:
        rows.sort(key=lambda r: -r['income_month_if_mine'].get(args.resource, 0))
    else:
        # winnable with the marines actually aboard first, then scarce suppliers,
        # then weighted value — a 470 vol/mo prize you cannot take is not a plan
        # winnable with the marines aboard, then FASTEST — a richer prize 3 months
        # further out is 3 months of income you never collected (and the ETA is what
        # the in-game transfer planner shows, which is what the player compares against)
        rows.sort(key=lambda r: (r['capture_odds'] < 0.5,
                                 r['eta_days'] if r['eta_days'] else 1e9))

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
    print("| # | Target | Owner (navy) | Body | ETA | ΔV spend / left | "
          "Income/mo if mine were mine | Def (plan) | Odds now | Marines 89% |")
    print("|---:|---|---|---|---:|---|---|---:|---:|---:|")
    for i, r in enumerate(rows[:args.top], 1):
        inc = ', '.join(f"{k} {v:g}" for k, v in sorted(
            r['income_month_if_mine'].items(), key=lambda kv: -kv[1])[:3])
        dfc = f"{r['ground_defence']:g}(+{DEFENCE_UNDER_READ})"
        odds = f"{r['capture_odds'] * 100:.0f}%"
        eta = f"{r['eta_months']}mo" if r['eta_months'] else '?'
        dv = (f"{r['dv_spend_kps']}/{r['dv_left_kps']} kps"
              if r['dv_spend_kps'] is not None else '?')
        if r['dv_left_kps'] is not None and r['dv_left_kps'] < 5:
            dv += ' ⚠one-way'
        print(f"| {i} | {r['hab']} | {r['owner']} ({r['owner_ships']} ships) | {r['body']} | "
              f"{eta} | {dv} | {inc} | {dfc} | {odds} | {r['marines_for_89pct']:g} |")
    print(f"\nDef (plan) = module-derived marine strength + {DEFENCE_UNDER_READ} — the module "
          f"sum UNDER-READS the real defending force (2033-11-09 ground truth: Leibniz Base "
          f"computed 20, in-game HABS list 23). **The HABS list defence/marine columns are "
          f"truth — read them before you commit.** 'Marines for 89%' is what you must bring "
          f"to make the assault a near-sure thing.")
    print("\nETA/ΔV use transfer_eta.py's burn-coast-burn model on STRAIGHT-LINE distance from "
          "the fleet's current position. It ignores orbital phasing and launch windows, so it is "
          "a SCREEN, not a plan: measured against the in-game planner on 2033-11-09 it read "
          "46 Hestia 10.9mo vs 8.9mo actual (+22%) and 97 Klotho 11.0mo vs 11.3mo (−3%). "
          "ΔV matched (51.1 modelled vs 51.0/51.9 actual). **The in-game transfer planner is "
          "truth** — check the shortlist there before committing. A leg landing with <5 kps left "
          "is one-way: the ship cannot reposition or come home. "
          "Run `transfer_eta.py --fleet "
          f"\"{f['name']}\" --to \"<body>\"` for burn/coast/burn, and trust the in-game "
          "transfer planner over both. Check the target body for defending FLEETS "
          "(`ops_query.py --theater`) before committing: this tool ranks the PRIZE, "
          "not the space battle.")


if __name__ == '__main__':
    main()
