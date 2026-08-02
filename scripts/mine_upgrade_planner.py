#!/usr/bin/env python3
"""mine_upgrade_planner.py — rank the player's SURFACE BASES by mining potential and
recommend where to build or upgrade mines toward the L3 (Colony Mining Complex) top yield.

For every player hab that sits on a hab site (= surface base), reports:
  - site raw rates, current mine module (tier / powered / under-construction),
  - CURRENT actual monthly income  = site_day × miningModifier(tier) × K[res]
  - L3 POTENTIAL monthly income    = site_day × 2.0 × K[res]
  - the upgrade DELTA on the focus resources (metals / water / fissiles by default),
  - an upgrade-cost estimate using the per-body RADIATION SURCHARGE table (see the
    docs/mechanics/Hab Build Costs and Radiation.md — high-radiation bodies pay up to ~14× Luna
    on metals; Io/Europa/Mercury/Ganymede are the expensive ones),
  - metals-payback months where the delta itself is metals.

K[res] is DERIVED from the save via mine_completion_timeline.derive_K_income (folds in
mining tech + assigned-org bonuses — self-updating, tooltip-exact; lesson E15/E20).

Costs: the empirical table is the T2→T3 (Settlement→Colony) upgrade cost read from queued
builds in saves. T1→T2 costs are NOT in the table; bases at T1 are flagged "2 steps" and
the shown cost is the T2→T3 leg only (a lower bound). ColonyCore prereq (hab must be T3)
is a minor extra (~27 vol + 27–85 metals) — flagged when the hab is below T3.

MC note: UPGRADING a mine's tier does NOT change the mining-network MC quadratic (it
counts active mines, not tiers). Only a NEW mine adds to it — marginal cost printed.
The quadratic charges only mines beyond the FREE allowance (36 free per the in-game
tooltip, LESSONS-economy E19: 42 active mines = 18 MC = 6²/2):
    network MC = max(0, active − 36)² / 2

Usage:
    python3 mine_upgrade_planner.py <save.json> [--faction <templateName>]
        [--focus metals,water,fissiles] [--top 15] [--json]
"""
import json, argparse, sys, os
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mine_completion_timeline import (load_save, kv_items, deref, parse_dt,
                                      derive_K_income, DAYS_PER_MONTH)

RES = ('metals', 'water', 'fissiles', 'nobles', 'volatiles')
L3_MOD = 2.0
TIER_LABEL = {1.0: 'T1', 1.25: 'T1+', 1.5: 'T2', 2.0: 'T3', 4.0: 'aT3'}

# Empirical T2→T3 mine-upgrade cost (water, volatiles, metals) per body — the radiation
# surcharge table from `docs/mechanics/Hab Build Costs and Radiation.md` (in-save queued builds,
# 2033-05-04). Bodies not listed fall back to the belt/Ceres row, marked '~'.
BODY_COST = {  # body-name substring (lowercase) -> (water, volatiles, metals)
    'luna':     (33.8, 33.8, 267),
    'ceres':    (51.0, 51.0, 412),
    'deimos':   (60.4, 60.4, 477),
    'phobos':   (60.4, 60.4, 477),
    'callisto': (60.8, 60.8, 480),
    'mars':     (62.3, 62.3, 492),
    'ganymede': (69.5, 69.5, 1313),
    'mercury':  (130.9, 130.9, 2300),
    'europa':   (80.9, 80.9, 2500),
    'io':       (99.7, 99.7, 3800),
}
DEFAULT_COST = (51.0, 51.0, 412)   # belt asteroid baseline


def body_cost(body):
    b = (body or '').lower()
    for k, v in BODY_COST.items():
        if k in b:
            return v, True
    return DEFAULT_COST, False


def mine_rows(gs, fid, K, focus, mine_mod):
    """Per-surface-base mining rows for one faction, sorted by focus-resource delta.

    Returns (rows, n_active_mines). Split out of main() so base_fix_audit.py can
    reuse it on an already-loaded save — a save is 60-90 MB, parse it once.
    """
    sectors = dict(kv_items(gs, 'TISectorState'))
    sector_to_hab = {sid: deref(sv.get('hab')) for sid, sv in sectors.items()}
    habs = dict(kv_items(gs, 'TIHabState'))
    sites = dict(kv_items(gs, 'TIHabSiteState'))
    bodies = {bid: (bv.get('displayName') or bv.get('templateName') or '?')
              for bid, bv in kv_items(gs, 'TISpaceBodyState')}

    # index mine modules by hab; count destroyed rubble slots per hab.
    # NB destroyed modules lose their original templateName (become 'DestroyedModuleNN'),
    # so a base whose mine was blown up looks like it never had one — flag the rubble so
    # "no mine" vs "mine destroyed, not rebuilt" are distinguishable (verified 2026-07-13).
    mines_by_hab = defaultdict(list)
    destroyed_by_hab = defaultdict(int)
    core_building_by_hab = {}          # hid -> ColonyCore completion dt (T2→T3 core in flight)
    for mid, mv in kv_items(gs, 'TIHabModuleState'):
        hid = sector_to_hab.get(deref(mv.get('sector')))
        if hid is None:
            continue
        if mv.get('destroyed'):
            destroyed_by_hab[hid] += 1
            continue
        name = mv.get('templateName') or ''
        if name == 'ColonyCore' and not mv.get('constructionCompleted'):
            core_building_by_hab[hid] = (parse_dt(mv['completionDate'])
                                         if mv.get('completionDate') else None)
        if name in mine_mod:
            mines_by_hab[hid].append(mv)

    rows = []
    n_active_mines = 0
    for hid, hv in habs.items():
        if deref(hv.get('faction')) != fid or not deref(hv.get('habSite')):
            continue
        site = sites.get(deref(hv.get('habSite')), {})
        body = bodies.get(deref(site.get('parentBody')), '?')
        raw = {r: site.get(r + '_day', 0) or 0 for r in RES}
        pot = {r: raw[r] * L3_MOD * K[r] for r in RES}

        mines = mines_by_hab.get(hid, [])
        cur_mod, powered, building, eta, mname = 0.0, None, False, None, None
        for mv in mines:
            mm = mine_mod.get(mv['templateName'], 1)
            if not mv.get('constructionCompleted'):
                building, eta = True, parse_dt(mv['completionDate']) if mv.get('completionDate') else None
                cur_mod = max(cur_mod, mm)   # treat as its post-completion tier
                mname = mv['templateName']
            else:
                cur_mod = max(cur_mod, mm)
                powered = bool(mv.get('powered'))
                mname = mv['templateName']
                if powered:
                    n_active_mines += 1
        cur = {r: raw[r] * cur_mod * K[r] if (cur_mod and (powered or building)) else 0.0
               for r in RES}
        delta = {r: pot[r] - cur[r] for r in RES}
        cost, known = body_cost(body)
        steps = 0 if cur_mod >= 2.0 else (1 if cur_mod >= 1.5 else 2)
        core_eta = core_building_by_hab.get(hid)
        tier = hv.get('tier')
        if cur_mod >= 2.0:
            ready = 'done/in-flight'
        elif tier and tier >= 3:
            ready = 'READY'
        elif hid in core_building_by_hab:
            ready = ('core lands ' + core_eta.strftime('%Y-%m-%d')) if core_eta else 'core building'
        else:
            ready = 'needs ColonyCore'
        rows.append({
            'hab': hv.get('displayName') or '?', 'body': body,
            'ready': ready,
            'destroyed_slots': destroyed_by_hab.get(hid, 0),
            'hab_tier': hv.get('tier'), 'mine': mname, 'mine_mod': cur_mod,
            'powered': powered, 'building': building,
            'eta': eta.isoformat() if eta else None,
            'raw': raw, 'cur': cur, 'pot': pot, 'delta': delta,
            'steps_to_L3': steps, 'cost_t2_t3': cost, 'cost_known': known,
            'focus_pot': sum(pot[r] for r in focus),
            'focus_delta': sum(delta[r] for r in focus),
        })

    rows.sort(key=lambda r: -r['focus_delta'])
    return rows, n_active_mines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('save')
    ap.add_argument('--faction', default=None)
    ap.add_argument('--focus', default='metals,water,fissiles')
    ap.add_argument('--top', type=int, default=15)
    ap.add_argument('--actionable', action='store_true',
                    help='only non-T3 mines with NO upgrade in flight, sorted by payback, '
                         'with readiness (hab tier / ColonyCore status) and a running '
                         'affordability tally vs the metals stockpile')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    from ti_config import require_faction
    args.faction = require_faction(args.faction)
    focus = [r.strip() for r in args.focus.split(',') if r.strip()]

    gs = load_save(args.save)['gamestates']
    now = parse_dt(gs[next(k for k in gs if k.endswith('TITimeState'))][0]
                   ['Value']['currentDateTime'])

    fid, fac = None, None
    for f, v in kv_items(gs, 'TIFactionState'):
        if v.get('templateName') == args.faction:
            fid, fac = f, v
            break
    if fid is None:
        sys.exit(f'faction {args.faction} not found')
    stock = fac.get('resources', {})

    K, kb = derive_K_income(gs, fid)

    here = os.path.dirname(os.path.abspath(__file__))
    from ti_config import find_templates_dir as _ftd
    _tdir = _ftd()
    if not _tdir:
        raise SystemExit('Game templates not found — run scripts/sync_game_data.py '
                         'or set game_install_dir in config.json.')
    mt = json.load(open(os.path.join(str(_tdir), 'TIHabModuleTemplate.json')))
    mine_mod = {m['dataName']: m.get('miningModifier', 1) for m in mt if m.get('mine')}

    rows, n_active_mines = mine_rows(gs, fid, K, focus, mine_mod)


    if args.actionable and not args.json:
        cand = [r for r in rows
                if r['mine'] and not r['building'] and 0 < r['mine_mod'] < 2.0]
        for r in cand:
            dm = r['delta']['metals']
            r['payback'] = (r['cost_t2_t3'][2] / dm) if dm > 1 else float('inf')
        cand.sort(key=lambda r: r['payback'])
        metals = stock.get('Metals', 0)
        print(f'# Actionable mine upgrades (non-T3, nothing in flight) — '
              f'{args.faction} — {now:%Y-%m-%d}')
        print(f'Metals stockpile: {metals:,.0f} · boost {stock.get("Boost",0):,.0f} '
              f'(costs are paid UP FRONT at click; shortfalls backfill on boost)\n')
        hdr = (f"{'Base':26} {'Body':12} {'ΔMet':>6} {'ΔWat':>6} {'ΔVol':>6} {'ΔFis':>6} {'ΔNob':>6} "
               f"{'Cost':>6} {'Payback':>8} {'ΣCost':>7} {'Readiness':18}")
        print(hdr); print('-' * len(hdr))
        run = 0
        for r in cand[:args.top]:
            run += r['cost_t2_t3'][2]
            afford = '' if run <= metals else ' ⚠over stock'
            pb = f"{r['payback']:6.1f}mo" if r['payback'] != float('inf') else '      —'
            print(f"{r['hab'][:26]:26} {r['body'][:12]:12} "
                  f"{r['delta']['metals']:6.0f} {r['delta']['water']:6.0f} "
                  f"{r['delta']['volatiles']:6.0f} {r['delta']['fissiles']:6.1f} "
                  f"{r['delta']['nobles']:6.0f} {r['cost_t2_t3'][2]:6.0f} {pb} "
                  f"{run:7.0f} {r['ready']:18}{afford}")
        print('\nΣCost = cumulative metals if you click top-down; ⚠ = beyond current '
              'stockpile. Sorted by metals payback — water/fissile value is on top of it.')
        return

    if args.json:
        print(json.dumps({'now': now.isoformat(), 'K': K, 'K_breakdown': kb,
                          'active_mines': n_active_mines, 'rows': rows}, indent=2,
                         default=str))
        return

    print(f'# Surface-base mine potential — {args.faction} — {now:%Y-%m-%d}')
    if kb:
        print(f"Mining multiplier from save: global ×{kb['global_mult']} "
              f"(tech +{kb['space_sum']}, orgs +{kb['org_sum']}); "
              f"resource 1.15^n {kb['res_count']}")
    over = max(0, n_active_mines - 36)
    marginal_mc = ((over + 1) ** 2 - over ** 2) / 2
    print(f'Active mines: {n_active_mines} (36 free) → network MC {over**2/2:.0f}; '
          f'a NEW mine adds ≈{marginal_mc:.1f} MC (tier UPGRADES are MC-free)\n')

    def fmt(v):
        return f'{v:7.0f}' if abs(v) >= 100 else f'{v:7.1f}'

    hdr = (f"{'Base':28} {'Body':10} {'Mine':4} {'St':2} "
           f"{'ΔMet/mo':>8} {'ΔWat/mo':>8} {'ΔVol/mo':>8} {'ΔFis/mo':>8} {'ΔNob/mo':>8} "
           f"{'L3Met':>7} {'L3Wat':>7} {'L3Vol':>7} {'L3Fis':>7} {'CostMet':>8} {'Payback':>8}")
    print(hdr)
    print('-' * len(hdr))
    for r in rows[:args.top]:
        tier = TIER_LABEL.get(r['mine_mod'], '—') if r['mine'] else '—'
        st = ('🚧' if r['building'] else
              ('🔌' if r['powered'] is False else ('✓' if r['powered'] else '·')))
        cost_m = r['cost_t2_t3'][2] * (1 if r['steps_to_L3'] <= 1 else 1)  # T2→T3 leg only
        coststr = (f"{cost_m:6.0f}{'' if r['cost_known'] else '~'}"
                   f"{'+2s' if r['steps_to_L3'] == 2 else ''}"
                   if r['steps_to_L3'] else '   —')
        dm = r['delta']['metals']
        payback = f"{cost_m/dm:6.1f}mo" if (dm > 1 and r['steps_to_L3']) else '     —'
        print(f"{r['hab'][:28]:28} {r['body'][:10]:10} {tier:4} {st:2} "
              f"{fmt(r['delta']['metals'])} {fmt(r['delta']['water'])} "
              f"{fmt(r['delta']['volatiles'])} {fmt(r['delta']['fissiles'])} "
              f"{fmt(r['delta']['nobles'])} "
              f"{fmt(r['pot']['metals'])} {fmt(r['pot']['water'])} "
              f"{fmt(r['pot']['volatiles'])} {fmt(r['pot']['fissiles'])} "
              f"{coststr:>8} {payback:>8}")
    print()
    print('St: ✓ powered · 🔌 UNPOWERED · 🚧 under construction · — no mine')
    print('Cost = metals for the T2→T3 leg (radiation surcharge table); '
          '"+2s" = T1 base, needs T1→T2 first (cost shown is the T2→T3 leg only, a floor).')
    print('Hab below tier 3 also needs a ColonyCore first (~27 vol + 27–85 metals — minor).')

    unpowered = [r for r in rows if r['powered'] is False and not r['building']]
    if unpowered:
        print('\n## 🔌 Idle (built but unpowered) mines')
        for r in unpowered:
            print(f"  {r['hab']} ({r['body']}) — {TIER_LABEL.get(r['mine_mod'])} — "
                  f"if powered: {r['cur']['metals']:.0f} met / {r['cur']['water']:.0f} wat "
                  f"/ {r['cur']['volatiles']:.0f} vol / {r['cur']['fissiles']:.1f} fis "
                  f"/ {r['cur']['nobles']:.0f} nob per month "
                  f"(sums use CURRENT tier; delta column already assumes powered)")
    nomine = [r for r in rows if not r['mine']]
    if nomine:
        print('\n## — Surface bases with NO live mine module (build/rebuild candidates)')
        print('   (a NEW/rebuilt mine re-enters the mining-MC quadratic — see marginal above)')
        for r in sorted(nomine, key=lambda x: -x['focus_pot'])[:10]:
            rub = (f" ⚠ {r['destroyed_slots']} DESTROYED slot(s) — mine may have been "
                   f"destroyed, not never-built" if r['destroyed_slots'] else '')
            print(f"  {r['hab']} ({r['body']}, habT{r['hab_tier']}) — L3 potential: "
                  f"{r['pot']['metals']:.0f} met / {r['pot']['water']:.0f} wat / "
                  f"{r['pot']['volatiles']:.0f} vol / {r['pot']['fissiles']:.1f} fis / "
                  f"{r['pot']['nobles']:.0f} nob per month{rub}")
    rubble = [r for r in rows if r['destroyed_slots'] and r['mine']]
    if rubble:
        print('\n## ⚠ Bases with destroyed (rubble) slots but a live/queued mine')
        for r in rubble:
            print(f"  {r['hab']} ({r['body']}) — {r['destroyed_slots']} destroyed slot(s)")


if __name__ == '__main__':
    main()
