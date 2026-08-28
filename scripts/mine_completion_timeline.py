#!/usr/bin/env python3
"""mine_completion_timeline.py — CANONICAL mine-output + water-timeline calculator for TI.
Reports BOTH current active-mine production AND the under-construction completion
timeline, in ACTUAL monthly income (matches the in-game hab-module tooltip).

⚠⚠ WATER IS NOT MINES ALONE. Farm modules cut a hab's life-support water import (~+19
water/mo each); this tool now tracks Farms in the water timeline. But it still does NOT
compute total population life-support, so it can NOT give the absolute net water balance —
trust the in-game water tooltip for that. (Save-verified 2033-03: 20 Farms completing flipped
water −166→+189/mo while the mines were wrongly suspected. See FARM_WATER_OFFSET_MONTH.)

⚠ Use THIS for any mine-output number. `extract_snapshot.py`'s `site.<res>_day` is the
RAW GEOLOGICAL rate and under-reports actual income ~2.5–3.7× (ignores mine tier AND the
global mining bonus). Its raw yields are fine for RANKING (proportional) only.

FORMULA (reproduces the tooltip exactly):
    actual monthly income[res] = site.<res>_day × miningModifier(tier) × K[res]
    miningModifier: Outpost 1.0 / Automated 1.25 / Settlement 1.5 / Colony 2.0
    K[res] = 30.44 × (1.15 ** #Mining<Res>Bonus_tech) × (1 + Σ SpaceMiningBonus_tech + Σ org.miningBonus)

K IS DERIVED FROM THE SAVE at runtime (derive_K_income) — it folds in resource-specific
mining tech, the global additive SpaceMining tech, AND **org space-mining bonuses from
assigned orgs**. So it self-updates when tech is researched OR an org is (re)assigned; no
manual recalibration. Verified 2026-07-02 vs two in-game tooltips (a Ganymede T3 colony
604.4 water/mo, a Callisto T2 settlement 605.3/mo) to <0.1%. The static K_INCOME table is a fallback only.

Reference-campaign 2033-01-28 state: global ×1.46 (0.20 SpaceMining tech + 0.26 from 4 assigned orgs) ×
resource 1.15^n (metals/water/fiss n=2, nobles n=1, volatiles n=0).

Usage:
    python mine_completion_timeline.py <save.json> [--faction <templateName>]
                                       [--resource volatiles]  # headlines the completion-
                                       #   timeline table: its /mo + cumulative columns track
                                       #   THIS resource (default: water). All resources are
                                       #   always computed; --resource only picks what the
                                       #   under-construction table displays. Use --json for all.
                                       [--json]

Notes:
- `completionDate` is the in-game datetime the module finishes construction.
- Yields are the SITE extraction rates; a finished mine must also be `powered`
  to actually produce (and mining-network MC cost is quadratic — see docs/lessons/LESSONS-economy.md E19).
- Default faction comes from config.json ("faction").
"""
import json, gzip, argparse, sys
from collections import defaultdict
from datetime import datetime

FAC_TEMPLATES = {
    'ResistCouncil', 'ExploitCouncil', 'SubmitCouncil', 'AppeaseCouncil',
    'CooperateCouncil', 'DestroyCouncil', 'EscapeCouncil', 'AlienCouncil',
}
DAYS_PER_MONTH = 30.44

# FALLBACK monthly-income factor K[resource] = monthly_income / (site_day × miningModifier).
# ⚠ The script now DERIVES K from the save at runtime via derive_K_income() (folds in mining-bonus
# TECH *and* assigned ORG bonuses, self-updating) — this hard-coded table is only the fallback when
# effects/orgs can't be read. Snapshot values below match the 2033-01-28 derivation exactly.
# Provenance (verified <0.1% vs in-game tooltips):
#   Ganymede base (T3 Colony ×2.0): water 604.4 metals 303.2 vol 94.1 nobles 45.1 fiss 8.3/mo
#   Callisto base (T2 Settlement ×1.5): water 605.3 vol 165.0 nobles 6.0/mo
# Decomposition (2033-01-28): global ×(1 + 0.20 SpaceMining tech + 0.26 assigned-org miningBonus)
# = ×1.46; resource-specific ×1.15^n (metals/water/fiss n=2, nobles n=1, volatiles n=0).
K_INCOME = {
    'metals':    58.78,   # 30.44 × 1.15^2 × 1.46
    'water':     58.77,   # 30.44 × 1.15^2 × 1.46  (T3 colony check: 5.143 × 2.0 × 58.77 = 604.5 ✓)
    'volatiles': 44.43,   # 30.44 × 1.15^0 × 1.46
    'nobles':    51.28,   # 30.44 × 1.15^1 × 1.46
    'fissiles':  59.04,   # 8.3   / (0.070 * 2.0)  -- ~unchanged
}

# WATER IS NOT MINES ALONE. Farm modules produce no template income but grow food for
# ~600 pop locally, which CUTS that hab's life-support water import. Net effect on the
# faction water balance ≈ +19 water/month per Farm. CALIBRATED 2026-07-04 from the
# 2033-02-28 → 03-01 save pair: 20 Farms completing swung net water −166 → +189/mo
# (+355), net of concurrent consumer completions (−26) ⇒ +19.1 water/Farm. This is a
# LIFE-SUPPORT OFFSET, not production. Ignoring Farms (as this script originally did)
# badly misreads water — it made us project a 3-week "water crisis" that the game solved
# on 03-01 when 20 Farms finished. Re-derive if it drifts (compare two adjacent saves).
FARM_MODULES = {'Farm'}
FARM_WATER_OFFSET_MONTH = 19.1


# THE loader lives in ti_config (gzip magic + BOM handling + per-process
# memoization); re-exported here because several analyzers import it from us.
from ti_config import load_save  # noqa: F401


def kv_items(gs, key_suffix):
    key = next((k for k in gs if k.endswith(key_suffix)), None)
    if key is None:
        return []
    out = []
    for entry in gs[key]:
        k = entry.get('Key')
        kid = k.get('value') if isinstance(k, dict) else k
        out.append((kid, entry.get('Value', {})))
    return out


def deref(field):
    if isinstance(field, dict):
        return field.get('value')
    return field


def fac_id_from_field(field):
    return deref(field)


def parse_dt(s):
    if isinstance(s, dict):
        return datetime(s['year'], s['month'], s['day'],
                        s.get('hour', 0), s.get('minute', 0), int(s.get('second', 0)))
    # ISO string like '2032-11-11T08:14:32.348'
    return datetime.fromisoformat(s.split('.')[0])


# Resource-specific mining-bonus effect names. Each such tech effect = ×1.15 on that
# resource. Volatiles has no resource-specific bonus (only the global one applies).
RES_BONUS_EFFECT = {
    'metals': 'MiningMetalsBonus', 'water': 'MiningWaterBonus',
    'nobles': 'MiningNoblesBonus', 'volatiles': 'MiningVolatilesBonus',
    'fissiles': 'MiningFissilesBonus',
}
RESOURCE_BONUS_STEP = 1.15   # each Mining<Res>Bonus tech multiplies that resource ×1.15

# Short, right-justified column labels for the completion-timeline table (per --resource).
RES_LABEL = {'metals': 'Metal', 'water': 'Water', 'volatiles': 'Vol',
             'nobles': 'Nobles', 'fissiles': 'Fiss'}


def derive_K_income(gs, faction_id, verbose=False):
    """Derive the per-resource monthly-income factor K[res] from the SAVE, folding in
    every mining-bonus source the game applies, so the numbers stay correct without
    manual recalibration:

      K[res] = DAYS_PER_MONTH
               × RESOURCE_BONUS_STEP ** (count of Mining<Res>Bonus tech effects)   # resource-specific
               × (1 + Σ SpaceMiningBonus tech values + Σ org.miningBonus of ASSIGNED orgs)  # global (incl. ORGS)

    Verified 2026-07-02 to reproduce the in-game hab tooltips EXACTLY:
      water: 1.15**2 × (1 + 0.20 tech + 0.26 org) = 1.9309 → K 58.77 → T3 colony 604.4/mo ✓
    Includes ORG space-mining bonuses (the reference campaign had 4 assigned orgs = +0.26 in the 2033-01-28 save:
    Org_KS4431 0.09, Org_KS4482 0.06, 2× RandomSpaceMining12 0.05+0.06) — these are captured
    automatically here, unlike the old hard-coded K which silently went stale on org reassignment.

    Falls back to the static K_INCOME (below) if effects/orgs can't be read.
    """
    es_list = gs.get(next((k for k in gs if k.endswith('TIEffectsState')), ''), [])
    if not es_list:
        return dict(K_INCOME), None
    fx = None
    for fe in es_list[0].get('Value', {}).get('factionEffectsNames', []):
        if (fe.get('Key') or {}).get('value') == faction_id:
            fx = fe.get('Value', {}) or {}
            break
    if fx is None:
        return dict(K_INCOME), None

    # resource-specific tech bonus counts
    res_count = {r: len(fx.get(RES_BONUS_EFFECT[r], []) or []) for r in RES_BONUS_EFFECT}
    # global additive: SpaceMiningBonus tech (Effect_SpaceMiningBonusN = +N%)
    space_sum = 0.0
    for e in fx.get('SpaceMiningBonus', []) or []:
        digits = ''.join(c for c in str(e) if c.isdigit())
        if digits:
            space_sum += int(digits) / 100.0
    # global additive: ORG miningBonus over orgs ASSIGNED to this faction's councilors
    councilor_ids = {cid for cid, cv in kv_items(gs, 'TICouncilorState')
                     if fac_id_from_field(cv.get('faction')) == faction_id}
    org_sum = 0.0
    for _oid, ov in kv_items(gs, 'TIOrgState'):
        ac = ov.get('assignedCouncilor')
        ac = deref(ac) if isinstance(ac, dict) else ac
        if ac in councilor_ids:
            org_sum += ov.get('miningBonus', 0) or 0

    global_mult = 1.0 + space_sum + org_sum
    K = {r: DAYS_PER_MONTH * (RESOURCE_BONUS_STEP ** res_count[r]) * global_mult
         for r in RES_BONUS_EFFECT}
    breakdown = {'res_count': res_count, 'space_sum': round(space_sum, 3),
                 'org_sum': round(org_sum, 3), 'global_mult': round(global_mult, 4)}
    if verbose:
        print(f"# Mining multiplier DERIVED from save (tech + assigned orgs):", file=sys.stderr)
        print(f"#   resource-bonus tech counts: {res_count}", file=sys.stderr)
        print(f"#   SpaceMiningBonus tech +{space_sum:.2f}, org miningBonus +{org_sum:.2f} "
              f"→ global ×{global_mult:.3f}", file=sys.stderr)
        print(f"#   K = {({r: round(v,2) for r,v in K.items()})}", file=sys.stderr)
    return K, breakdown


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('save')
    ap.add_argument('--faction', default=None)
    ap.add_argument('--resource', default=None,
                    help="resource the completion-timeline table headlines (its /mo + "
                         "cumulative columns); default water. All resources are always computed.")
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    from ti_config import require_faction
    args.faction = require_faction(args.faction)

    # Which resource the under-construction table headlines. Default water for backward
    # compatibility (the table always showed a water column). Every resource is still
    # computed per-row and emitted in --json; --resource only picks the table's columns.
    res = (args.resource or 'water').lower()
    if res not in RES_BONUS_EFFECT:
        print(f"--resource must be one of {sorted(RES_BONUS_EFFECT)}", file=sys.stderr)
        sys.exit(1)
    secondary = 'metals' if res != 'metals' else 'water'   # context column (avoid a dup)

    save = load_save(args.save)
    gs = save['gamestates']

    # current in-game date
    ts = dict(kv_items(gs, 'TITimeState'))
    now = None
    for _, v in [(None, v) for v in [gs[next(k for k in gs if k.endswith('TITimeState'))][0]['Value']]]:
        now = parse_dt(v['currentDateTime'])

    # faction id for the requested template
    faction_id = None
    for fid, fv in kv_items(gs, 'TIFactionState'):
        if fv.get('templateName') == args.faction:
            faction_id = fid
            break
    if faction_id is None:
        print(f"Faction {args.faction} not found", file=sys.stderr)
        sys.exit(1)

    # which module templates are mines
    tmpl_path = None
    # we don't strictly need the template file; mines are identified by site yields,
    # but to match extract_snapshot we use the template `mine` flag if available.
    mine_names = None
    # fall back to known set
    fallback = {'OutpostMiningComplex', 'AutomatedMiningComplex', 'MiningComplex',
                'OutpostMine', 'Mine', 'CrustalMine', 'SubsurfaceMine'}

    sectors = dict(kv_items(gs, 'TISectorState'))
    sector_to_hab = {sid: deref(sv.get('hab')) for sid, sv in sectors.items()}
    habs = dict(kv_items(gs, 'TIHabState'))
    sites = dict(kv_items(gs, 'TIHabSiteState'))
    bodies = {bid: (bv.get('displayName') or bv.get('templateName') or '?')
              for bid, bv in kv_items(gs, 'TISpaceBodyState')}

    # try template file to get the authoritative mine flag + per-tier miningModifier
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    mining_modifier = {}   # dataName -> miningModifier (tier factor)
    for cand in [os.path.join(here, 'templates', 'TIHabModuleTemplate.json')]:
        if os.path.exists(cand):
            try:
                mt = json.load(open(cand))
                mine_names = {m['dataName'] for m in mt if m.get('mine')}
                mining_modifier = {m['dataName']: m.get('miningModifier', 1)
                                   for m in mt if m.get('mine')}
            except Exception:
                pass
    if not mine_names:
        mine_names = fallback

    # DERIVE the per-resource K from the save (tech + assigned-org mining bonuses) — self-updating,
    # so org reassignment / new mining tech is captured without manual recalibration. Falls back to
    # the static K_INCOME table if effects can't be read.
    K, K_breakdown = derive_K_income(gs, faction_id, verbose=False)

    rows = []                                    # under-construction mines + farms
    active_totals = defaultdict(float)           # currently powered mines — monthly income
    active_count = 0
    active_farm_count = 0                         # powered Farms (water life-support offset)
    active_farm_water = 0.0
    for mid, mv in kv_items(gs, 'TIHabModuleState'):
        name = mv.get('templateName') or ''
        is_mine = name in mine_names
        is_farm = name in FARM_MODULES
        if not (is_mine or is_farm):
            continue
        sid = deref(mv.get('sector'))
        hid = sector_to_hab.get(sid)
        if hid not in habs:
            continue
        hv = habs[hid]
        if fac_id_from_field(hv.get('faction')) != faction_id:
            continue
        site = sites.get(deref(hv.get('habSite')), {})
        body = bodies.get(deref(site.get('parentBody')), '(orbital)')
        hab_name = hv.get('displayName') or hv.get('templateName') or '?'
        comp = mv.get('completionDate')
        eta = parse_dt(comp) if comp else None

        if is_farm:
            # Farm: water life-support OFFSET only (no metals/other production)
            if mv.get('constructionCompleted'):
                if mv.get('powered'):
                    active_farm_count += 1
                    active_farm_water += FARM_WATER_OFFSET_MONTH
                continue
            rows.append({'hab': hab_name, 'body': body, 'eta': eta, 'tier': 'Farm',
                         'module': 'Farm', 'water': FARM_WATER_OFFSET_MONTH,
                         'metals': 0.0, 'volatiles': 0.0, 'nobles': 0.0, 'fissiles': 0.0})
            continue

        # mine: actual monthly income = site_day × tier modifier × derived global factor
        mm = mining_modifier.get(name, 1)
        inc = {r: (site.get(r + '_day', 0) or 0) * mm * K[r] for r in K}
        if mv.get('constructionCompleted'):
            if mv.get('powered'):
                active_count += 1
                for r in K:
                    active_totals[r] += inc[r]
            continue
        rows.append({
            'hab': hab_name, 'body': body, 'eta': eta, 'tier': mm, 'module': name,
            **inc,  # metals/water/volatiles/nobles/fissiles = monthly income
        })

    rows.sort(key=lambda r: (r['eta'] or datetime.max))

    tot = defaultdict(float)
    for r in rows:
        for k in K:
            tot[k] += r[k]

    if args.json:
        out = []
        for r in rows:
            rr = dict(r)
            rr['eta'] = r['eta'].isoformat() if r['eta'] else None
            rr['days_out'] = (r['eta'] - now).days if r['eta'] else None
            out.append(rr)
        print(json.dumps({'now': now.isoformat(),
                          'K_income': K, 'K_breakdown': K_breakdown,
                          'active_count': active_count,
                          'active_monthly_income': dict(active_totals),
                          'active_farm_count': active_farm_count,
                          'active_farm_water_offset': round(active_farm_water, 1),
                          'under_construction_monthly_income': dict(tot),
                          'rows': out}, indent=2))
        return

    RES = ('metals', 'nobles', 'water', 'volatiles', 'fissiles')
    TIER = {1: 'T1', 1.25: 'T1+', 1.5: 'T2', 2: 'T3'}
    print(f"# Mine output & completion timeline — {args.faction}")
    print(f"Current in-game date: {now:%Y-%m-%d}")
    print(f"Income = ACTUAL monthly income = site_day × tier modifier × mining multiplier.")
    if K_breakdown:
        b = K_breakdown
        print(f"Mining multiplier DERIVED from save: global ×{b['global_mult']} "
              f"(1 + {b['space_sum']} SpaceMining tech + {b['org_sum']} assigned-org bonus) "
              f"× resource-specific 1.15^n {b['res_count']}.")
        print(f"K/resource = {({r: round(v,1) for r,v in K.items()})}")
    print()

    # --- CURRENT active production ---
    print(f"## CURRENT active mines — {active_count} powered — monthly income (÷30.44 for /day)"
          f"  [◄ = --resource {res}, headlined below]")
    for k in RES:
        marker = '  ◄' if k == res else ''
        print(f"  {k:<10} {active_totals[k]:9.1f}/month  "
              f"({active_totals[k]/DAYS_PER_MONTH:6.1f}/day){marker}")
    print(f"  + {active_farm_count} powered Farms → water life-support OFFSET "
          f"+{active_farm_water:.0f}/month (+{active_farm_water/DAYS_PER_MONTH:.1f}/day)")
    print()
    print("  ⚠ WATER BALANCE IS NOT MINES ALONE. Net water = mine production + Farm life-support")
    print("    offset − total population life-support − module support. This tool shows mine")
    print("    production and Farm offsets (the construction-driven DELTAS); it does NOT compute")
    print("    total life-support, so it can't give the absolute net — TRUST THE IN-GAME WATER")
    print("    TOOLTIP for that. (2033-03 lesson: 20 Farms completing flipped water −166→+189/mo;")
    print("    the mines had nothing to do with it.)")
    print()

    # --- Under-construction timeline ---
    # Primary column tracks the selected resource; `secondary` is a context column
    # (metals, or water when metals is selected). Cumulative accumulates the selected one.
    res_label, sec_label = RES_LABEL[res], RES_LABEL[secondary]
    n_farm_rows = sum(1 for r in rows if r['module'] == 'Farm')
    print(f"## {len(rows)-n_farm_rows} mines + {n_farm_rows} farms UNDER CONSTRUCTION — "
          f"{res} completion timeline")
    if res == 'water':
        print(f"   (Farm row = +{FARM_WATER_OFFSET_MONTH:.0f}/mo water life-support offset; "
              f"mine row = actual production)\n")
    else:
        print(f"   (Farm rows produce water only — 0 {res}; mine row = actual production)\n")
    hdr = (f"{'Completes':<12} {'+days':>6}  {'Hab':<26} {'Body':<16} {'Tier':>4} "
           f"{res_label+'/mo':>9} {sec_label+'/mo':>9}  {'cum'+res_label+'/mo':>12}")
    print(hdr)
    print('-' * len(hdr))
    cum = 0.0
    for r in rows:
        cum += r[res]
        days_out = (r['eta'] - now).days if r['eta'] else None
        print(f"{r['eta']:%Y-%m-%d}   {days_out:>6}  {r['hab']:<26.26} {r['body']:<16.16} "
              f"{TIER.get(r['tier'], r['tier']):>4} {r[res]:>9.1f} {r[secondary]:>9.1f}  {cum:>12.1f}")

    print("\n## Totals when ALL under-construction complete — monthly income (and resulting total)")
    for k in RES:
        cur, inc = active_totals[k], tot[k]
        marker = '  ◄' if k == res else ''
        print(f"  {k:<10} current {cur:8.1f} + incoming {inc:8.1f} = {cur+inc:8.1f}/month "
              f"({(cur+inc)/DAYS_PER_MONTH:6.1f}/day){marker}")
    last = rows[-1]['eta'] if rows and rows[-1]['eta'] else None
    first = rows[0]['eta'] if rows and rows[0]['eta'] else None
    if first and last:
        print(f"\nFirst comes online {first:%Y-%m-%d} (+{(first-now).days}d), "
              f"last {last:%Y-%m-%d} (+{(last-now).days}d).")


if __name__ == '__main__':
    main()
