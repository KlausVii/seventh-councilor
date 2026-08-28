#!/usr/bin/env python3
"""boost_analysis.py — diagnose a faction's Boost economy: income (per nation),
ongoing module consumption (flagging the Administration-Tower-outside-LEO trap),
and the (glacial) Launch-Facilities-priority buildout rate.

WHY THIS EXISTS — boost is widely misunderstood (and I got it wrong once):
  * Boost is NOT injected by priority pips. The `LaunchFacilities` ("Boost")
    priority drives a per-region INFRASTRUCTURE buildout that is glacially slow.
    Decompiled (TINationState.OnBoostPriorityComplete / BoostIncrease,
    TIGlobalConfig): each completion needs `priority_BOO = 2` IP and adds only
    `(boostPriorityIncreaseAtEquator 4 − |boostLatitude|/boostLatitudeDivisor 25)
    × spaceResourceToTons 0.1` ≈ 0.22–0.31 boost/YEAR to ONE region. Net: ~1–3
    completions/month from a heavy pip allocation → output creeps up a fraction
    of a boost/month. Building even +20/mo income this way takes DECADES.
  * Latitude matters: equatorial regions (China ~22°, USA ~25°) get a bigger
    increment than high-latitude Russia (~45°). And IP/nation matters (China has
    the most). So pip efficiency ranks CHINA > USA > RUSSIA — Russia is the WORST
    target (fewest IP + worst latitude). A nation's Funding (the in-game term for
    its monthly cash to control-point owners → becomes our Money; internal field
    `spaceFunding_year`) has NOTHING to do with boost output.
  * The real boost problem in the late game is ONGOING MODULE SUPPORT. The big
    sink is Administration modules (Node 1 / Tower 4 / Complex 12 boost/mo). Their
    CP-cap benefit only applies in Earth LEO (`LEOControlPointCapacity`); built
    anywhere else they give only a +`specialRulesValue` Efficiency bonus (+2.5/5/10%
    hab income) for the FULL boost cost — usually a bad trade in a boost crunch.
    Tourism (SpaceHotel 3, SpaceResort 6), Residential, Hospital/Geriatrics also cost boost.
  * The fix for an acute boost deficit is SHUTTING DOWN / not-building boost-hungry
    modules (esp. non-LEO Administration Towers), NOT priority pips.

Usage:
    python boost_analysis.py <save.json> [--faction <templateName>]
"""
import json, gzip, argparse, os, sys
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mine_completion_timeline import derive_K_income
T = lambda f: os.path.join(HERE, 'templates', f)
# decompiled constants (TIGlobalConfig.cs)
BOOST_EQ, BOOST_LAT_DIV, S2T, REQ_IP_BOO = 4.0, 25.0, 0.1, 2.0


from ti_config import load_save  # THE shared loader: gzip magic + BOM, memoized


def kv(gs, suf):
    key = next((k for k in gs if k.endswith(suf)), None)
    out = []
    for e in (gs.get(key) or []):
        k = e.get('Key'); kid = k.get('value') if isinstance(k, dict) else k
        out.append((kid, e.get('Value', {})))
    return out


def deref(f):
    return f.get('value') if isinstance(f, dict) else f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('save')
    ap.add_argument('--faction', default=None)
    args = ap.parse_args()
    from ti_config import require_faction
    args.faction = require_faction(args.faction)
    save = load_save(args.save)
    gs = save['gamestates']
    mt = {m['dataName']: m for m in json.load(open(T('TIHabModuleTemplate.json')))}
    boost_up = {dn: (m.get('supportMaterials_month') or {}).get('boost', 0)
                for dn, m in mt.items() if (m.get('supportMaterials_month') or {}).get('boost', 0)}

    fac_id = next(fid for fid, v in kv(gs, 'TIFactionState') if v.get('templateName') == args.faction)
    fac = next(v for _, v in kv(gs, 'TIFactionState') if v.get('templateName') == args.faction)
    nations = {nid: nv for nid, nv in kv(gs, 'TINationState')}
    cps = kv(gs, 'TIControlPoint')
    sectors = dict(kv(gs, 'TISectorState'))
    sec2hab = {sid: deref(sv.get('hab')) for sid, sv in sectors.items()}
    habs = dict(kv(gs, 'TIHabState'))
    sites = dict(kv(gs, 'TIHabSiteState'))
    bodies = {bid: (bv.get('displayName') or bv.get('templateName') or '?')
              for bid, bv in kv(gs, 'TISpaceBodyState')}

    print(f"# Boost analysis — {args.faction}")
    print(f"Boost stockpile: {fac.get('resources', {}).get('Boost', 0):.1f}\n")

    # --- income from nations (per-CP equal share) ---
    fac_cp, tot_cp = Counter(), Counter()
    for _, cv in cps:
        nid = deref(cv.get('nation')); tot_cp[nid] += 1
        if deref(cv.get('faction')) == fac_id:
            fac_cp[nid] += 1
    print("## Gross boost income from nations")
    gross = 0
    for nid in sorted(fac_cp, key=lambda n: -(nations.get(n, {}).get('historyBoost', [0])[0] or 0) * fac_cp[n] / max(tot_cp[n], 1)):
        nv = nations.get(nid, {})
        nb = nv.get('historyBoost', [0])[0] or 0
        contrib = nb * fac_cp[nid] / tot_cp[nid] if tot_cp[nid] else 0
        gross += contrib
        if contrib > 0.05:
            print(f"  {nv.get('templateName', nid):<14} CPs {fac_cp[nid]}/{tot_cp[nid]}  "
                  f"nation {nb:5.1f}/mo  IP {nv.get('baseInvestmentPoints_month', 0):4.1f}  → +{contrib:5.1f}/mo")
    print(f"  TOTAL gross from nations: {gross:.1f}/mo  (+ orgs, see report ledger)\n")

    # --- ongoing module consumption, with Admin LEO-vs-not split ---
    print("## Ongoing boost consumption (powered modules)")
    powered = Counter(); building = Counter()
    admin_loc = defaultdict(lambda: Counter())  # template -> {('LEO'/'non-LEO', status): n}
    for _, mv in kv(gs, 'TIHabModuleState'):
        name = mv.get('templateName') or ''
        if name not in boost_up:
            continue
        hid = sec2hab.get(deref(mv.get('sector'))); hv = habs.get(hid)
        if not hv or deref(hv.get('faction')) != fac_id:
            continue
        done = bool(mv.get('constructionCompleted')); pwr = bool(mv.get('powered'))
        site = sites.get(deref(hv.get('habSite')), {})
        body = bodies.get(deref(site.get('parentBody')), None)
        # Earth-LEO heuristic: no parent body (orbital station) => LEO/orbital
        leo = 'LEO/orbital' if body in (None, '?') else 'non-LEO'
        status = 'powered' if (done and pwr) else ('building' if not done else 'off')
        if status == 'powered':
            powered[name] += 1
        elif status == 'building':
            building[name] += 1
        if 'Administration' in name:
            admin_loc[name][(leo, status)] += 1

    tot_p = 0
    for dn in sorted(boost_up, key=lambda d: -boost_up[d] * powered[d]):
        if powered[dn] + building[dn] == 0:
            continue
        pb = powered[dn] * boost_up[dn]; tot_p += pb
        print(f"  {dn:<22} {boost_up[dn]} boost/mo × {powered[dn]:2} powered = {pb:5.1f}/mo "
              f"({building[dn]} building → +{building[dn]*boost_up[dn]:.0f}/mo later)")
    print(f"  TOTAL powered boost consumption: {tot_p:.1f}/mo\n")

    # --- Administration LEO vs non-LEO (the trap) ---
    print("## Administration modules: LEO (give CP cap) vs non-LEO (NO CP cap, only +Efficiency)")
    for dn, locs in admin_loc.items():
        srv = mt[dn].get('specialRulesValue', 0)
        for (leo, status), n in sorted(locs.items()):
            note = f"+{srv*100:.1f}% hab income only" if leo == 'non-LEO' else f"+{mt[dn].get('controlPointCapacity')} CP cap"
            print(f"  {dn:<22} {leo:<12} {status:<9} ×{n:2}  ({n*boost_up[dn]:.0f} boost/mo; {note})")
    # actionable: non-LEO powered admin towers reclaimable
    reclaim = sum(n * boost_up[dn] for dn, locs in admin_loc.items()
                  for (leo, status), n in locs.items() if leo == 'non-LEO' and status == 'powered')
    avoid = sum(n * boost_up[dn] for dn, locs in admin_loc.items()
                for (leo, status), n in locs.items() if leo == 'non-LEO' and status == 'building')
    print(f"\n  >> Power down non-LEO Administration modules → reclaim {reclaim:.0f} boost/mo NOW")
    print(f"  >> Cancel non-LEO Administration modules under construction → avoid {avoid:.0f} boost/mo later")

    # --- per-hab Efficiency value: 5% of hab GROSS mining income (ground truth: TIHabState.cs:3364-3523,
    #     ×(1+specialRulesValue) on gross income of metals/nobles/water/vol/fissiles/money/research; powered only).
    #     Flag DEAD towers (mine not producing yet → +5% × ~0 = zero benefit → power down first). ---
    K, _kb = derive_K_income(gs, fac_id)  # per-resource K from THIS save (tech + org bonuses)
    mine_mod = {dn: m.get('miningModifier', 1) for dn, m in mt.items() if m.get('mine')}
    # build hab->modules
    hab_mods = defaultdict(list)
    for _, mv in kv(gs, 'TIHabModuleState'):
        hab_mods[deref(sectors.get(deref(mv.get('sector')), {}).get('hab'))].append(mv)
    print("\n## Non-LEO Admin Towers ranked by ACTUAL +5% benefit (power down lowest first)")
    print(f"  {'Hab':<24}{'Body':<14}{'metals/mo':>10}{'+5% metals':>11}{'verdict':>22}")
    admin_rows = []
    for _, mv in kv(gs, 'TIHabModuleState'):
        if mv.get('templateName') != 'AdministrationTower':
            continue
        if not (mv.get('constructionCompleted') and mv.get('powered')):
            continue
        hid = deref(sectors.get(deref(mv.get('sector')), {}).get('hab')); hv = habs.get(hid)
        if not hv or deref(hv.get('faction')) != fac_id:
            continue
        site = sites.get(deref(hv.get('habSite')), {})
        body = bodies.get(deref(site.get('parentBody')), None)
        if body in (None, '?'):
            continue
        metals = 0.0
        for m2 in hab_mods.get(hid, []):
            nm = m2.get('templateName')
            if nm in mine_mod and m2.get('constructionCompleted') and m2.get('powered'):
                metals += (site.get('metals_day', 0) or 0) * mine_mod[nm] * K['metals']
        admin_rows.append((hv.get('displayName'), body, metals))
    for hab, body, metals in sorted(admin_rows, key=lambda r: r[2]):
        verdict = 'DEAD — mine not live' if metals < 1 else f'{0.05*metals:.0f} metals/4 boost'
        print(f"  {hab:<24.24}{body:<14.14}{metals:>10.0f}{0.05*metals:>11.1f}{verdict:>22}")
    dead = sum(1 for _, _, m in admin_rows if m < 1)
    print(f"\n  {dead} of {len(admin_rows)} live non-LEO Towers produce ZERO benefit (mine still building) "
          f"= {dead*4} boost/mo wasted for nothing → power those down first.")

    print("\n## Priority-pip buildout (why it is NOT the fix)")
    print(f"  Each LaunchFacilities cycle = {REQ_IP_BOO:.0f} IP, adds (4 − |lat|/25)×0.1 ≈ 0.22–0.31 boost/YEAR to 1 region.")
    print(f"  ~1–3 completions/mo from heavy pips → fractions of a boost/mo gained per month. DECADES to matter.")
    print(f"  If you must: rank YOUR nations by IP/month × low |latitude| — e.g. among the majors, CHINA > USA > RUSSIA (Russia worst: fewest IP + highest latitude).")


if __name__ == '__main__':
    main()
