#!/usr/bin/env python3
"""Priority list of OperationsCenter → CommandCenter upgrades to queue next.

Usage:
    python3 cc_upgrade_planner.py [save.json|gz] [--faction X] [--sort days|metals]

Finds every faction hab with a COMPLETED OperationsCenter and no CommandCenter
queued/built, and ranks by SPEED (the MC gain is +10 everywhere, and the metals
cost is the same 400 on most bodies, so time is the discriminator):

  - WHY TIME, NOT COST: the OperationsCenter goes dark at click time (E28), so
    every candidate runs a −4 MC blackout for the whole build. The real price of
    an upgrade is `days × 4` MC-days of lost Mission Control, printed per row.
    A 96-day Callisto upgrade costs 384 MC-days; the same 400 metals at 160 days
    costs 640. Cost-first ranking hides that. `--sort metals` restores the old
    cheapest-first order for a metals-constrained save.

  - est. metals cost: per-body radiation surcharge, CALIBRATED from queued
    CC-upgrade builds (2033-08-05 save): 400 baseline (Earth orbit, Luna, Mars,
    Phobos/Deimos, belt, Ceres, outer-Jovian irregulars), 933 Mercury.
    Io/Europa/Ganymede have no calibration point yet — ESTIMATES from the
    radiation-surcharge curve (`docs/mechanics/Hab Build Costs and Radiation.md`), flagged '~'.
    When a CC is later queued on one of those bodies, read its
    buildCost.resourceCosts and update BODY_METALS below.
  - est. days: upgrade base 160 d × the EXACT construction-speed law,
    calibrated to 5 decimals against 16 `appliedBuildConstructionBonus`
    readings (2033-08-05 save): sort the hab's powered+completed
    construction modules by strength (NanofacturingComplex 0.6,
    Nanofactory 0.75, ConstructionModule 0.9 — read from the template's
    `constructionTimeModifier`); the k-th multiplies time by
    1 − (1−modifier)/k². One NanofacturingComplex alone = ×0.6 → 96 days.
  - flags UNPOWERED OpsCenters (power first: +4 MC free, lesson E28 family).
  - POWER GATE (lesson E34): a CommandCenter draws 300 vs the OperationsCenter's
    100, so the hab needs +200 net power headroom or the finished CC cannot be
    switched on. Each row carries a power verdict from hab_power_audit's ledger:
    'ok' (surplus covers it), 'idle gen' (surplus + idle generator capacity
    covers it — flip a reactor), or 'POWER SHORT n' (needs new generation;
    in-flight generators are listed by hab_power_audit). Solar figures are
    reconstructed estimates — the in-game ☀ readout is truth.
  - INCOMING accelerators: a Nanofactory/NFC/ConstructionModule finishing
    MID-BUILD starts applying its bonus to in-progress construction the
    moment it comes online (verified 2033-08-08). Est-days therefore simulates
    a click at the SAVE DATE with piecewise rates: progress accrues at
    1/(160·bonus(active set)) and the bonus recomputes at each incoming
    module's ETA. Estimates only — the in-game completion date after
    clicking is the truth.
  - REQUIRES TIER 3: a CommandCenter needs a T3 core (ColonyCore/RingCore) —
    verified 2033-08-05 save: every built/queued CC sits on a tier-3 hab
    (reference-campaign correction: one candidate was a T2 station, not upgradeable yet). T2
    candidates sort to the bottom, annotated "needs T3 core" — or, if a T3
    core is already under construction, "T3 core ETA <date>" (just wait,
    then queue). Core upgrades are cheap (~27-85 metals, 45-60 d).

Pacing reminder printed with the list: each click pays the full cost up front
(lesson E24) and any stockpile shortfall backfills from Earth as Boost+Money —
never queue past the current metals buffer.
"""
import argparse
from collections import defaultdict

from extract_snapshot import load_save, kv_items, get_factions, \
    faction_id_by_template
from module_completion_dates import load_mc_table

# metals for the OC→CC upgrade per body. Calibrated entries are exact reads
# from queued builds; '~' entries are radiation-curve estimates (see docstring).
BODY_METALS = {
    'mercury': (933, ''),
    'ganymede': (750, '~'),
    'europa': (950, '~'),
    'io': (1100, '~'),
}
DEFAULT_METALS = (400, '')          # everything else (calibrated baseline)
UPGRADE_BASE_DAYS = 160
# CommandCenter draws 300, the OperationsCenter it replaces draws 100 (template
# `power`), so completing the upgrade needs this much extra headroom (E34).
CC_NET_POWER = 200
CT_MODS = {}          # templateName -> constructionTimeModifier; filled on first use


def load_construction_modifiers():
    """templateName -> constructionTimeModifier (<1 only), from the template."""
    import json
    from pathlib import Path
    tpl = Path(__file__).resolve().parent / 'templates' / 'TIHabModuleTemplate.json'
    if not tpl.exists():
        # repo ships no game data; before sync_game_data.py runs, use the
        # verified vanilla values (build ~1.0.38)
        return {'NanofacturingComplex': 0.6, 'Nanofactory': 0.75,
                'ConstructionModule': 0.9, 'AlienNanofacturingComplex': 0.5,
                'AlienNanofactory': 0.65, 'AlienAssembler': 0.8}
    out = {}
    for e in json.load(open(tpl)):
        m = e.get('constructionTimeModifier', 1)
        # allowsShipConstruction modules (Shipyard/Spaceworks) speed SHIP
        # builds, not hab modules — a reference-campaign station tooltip (160 d with 2
        # powered Spaceworks) proves they don't count here
        if m and m < 1 and not e.get('allowsShipConstruction'):
            out[e['dataName']] = m
    return out


def est_days_clicked_now(live_mods, incoming, base_days=UPGRADE_BASE_DAYS):
    """Piecewise build simulation from the save date.
    live_mods: list of modifiers active now; incoming: [(days_from_now, mod)].
    Rate = 1/(base·bonus) with bonus recomputed as each module lands."""
    active = list(live_mods)
    t = progress = 0.0
    for eta, mod in sorted(incoming):
        rate = 1.0 / (base_days * build_time_bonus(active))
        dt = max(0.0, eta - t)
        if progress + dt * rate >= 1.0:
            return t + (1.0 - progress) / rate
        progress += dt * rate
        t = eta
        active.append(mod)
    rate = 1.0 / (base_days * build_time_bonus(active))
    return t + (1.0 - progress) / rate


def build_time_bonus(modifiers):
    """EXACT stacking law (verified vs 16 appliedBuildConstructionBonus reads,
    2033-08-05 save): sort modifiers ascending (strongest first); the k-th
    module multiplies time by 1 - (1-m)/k**2."""
    bonus = 1.0
    for k, m in enumerate(sorted(modifiers), 1):
        bonus *= 1 - (1 - m) / k**2
    return bonus


def power_by_hab(gs, fid):
    """hab displayName -> (surplus, idle_generator_capacity) from the shared
    hab_power_audit ledger. Empty dict if the power tool can't run (missing
    templates) — the planner still works, it just can't gate on power."""
    try:
        from hab_power_audit import load_templates, power_ledger
        mod_tmpl, body_tmpl = load_templates()
        return {r['hab']: (r['surplus'], r['idle_generator_capacity'])
                for r in power_ledger(gs, fid, mod_tmpl, body_tmpl, include_all=True)}
    except SystemExit:
        return {}


def power_verdict(power, hab):
    """Can this hab run a finished CommandCenter (+200 net draw)?"""
    if hab not in power:
        return '?'
    surplus, idle = power[hab]
    if surplus >= CC_NET_POWER:
        return 'ok'
    if surplus + idle >= CC_NET_POWER:
        return 'idle gen'
    return f'POWER SHORT {CC_NET_POWER - surplus - idle}'


def body_metals(body):
    b = (body or '').lower()
    for k, v in BODY_METALS.items():
        if k in b:
            return v
    return DEFAULT_METALS


def collect_candidates(gs, fid, save_date, sort='days'):
    """Every OC→CC upgrade candidate for one faction, ranked.

    Returns (candidates, unpowered_opscenter_names). Split out of main() so
    base_fix_audit.py can reuse it on an already-loaded save (a save is 60-90 MB —
    never parse it twice in one report).
    """
    global CT_MODS
    if not CT_MODS:
        CT_MODS = load_construction_modifiers()
    import datetime
    habs = {k: v for k, v in kv_items(gs, 'PavonisInteractive.TerraInvicta.TIHabState')}
    sites = {k: v for k, v in kv_items(gs, 'PavonisInteractive.TerraInvicta.TIHabSiteState')}
    orbits = {k: v for k, v in kv_items(gs, 'PavonisInteractive.TerraInvicta.TIOrbitState')}
    bodies = {k: v for k, v in kv_items(gs, 'PavonisInteractive.TerraInvicta.TISpaceBodyState')}
    sec2hab = {}
    for hv in habs.values():
        for s in hv.get('sectors', []):
            sec2hab[s['value']] = hv

    def location(hv):
        sv = sites.get((hv.get('habSite') or {}).get('value'))
        if sv:
            b = bodies.get((sv.get('parentBody') or {}).get('value'))
            return (b or {}).get('displayName', '?'), 'base'
        ov = orbits.get((hv.get('orbitState') or {}).get('value'))
        if ov:
            b = bodies.get((ov.get('barycenter') or {}).get('value'))
            return f"orbit {(b or {}).get('displayName', '?')}", 'station'
        return '?', 'station'

    mods_by_hab = defaultdict(list)
    for _, mv in kv_items(gs, 'PavonisInteractive.TerraInvicta.TIHabModuleState'):
        hab = sec2hab.get((mv.get('sector') or {}).get('value'))
        if hab is not None:
            mods_by_hab[id(hab)].append((hab, mv))

    power = power_by_hab(gs, fid)
    cands, unpowered = [], []
    for entries in mods_by_hab.values():
        hab = entries[0][0]
        if (hab.get('faction') or {}).get('value') != fid:
            continue
        mods = [mv for _, mv in entries]
        if any(m.get('templateName') == 'CommandCenter' for m in mods):
            continue
        ocs = [m for m in mods if m.get('templateName') == 'OperationsCenter'
               and m.get('constructionCompleted') and not m.get('destroyed')]
        if not ocs:
            continue
        tier = hab.get('tier')
        t3core_eta = next((str(m.get('completionDate'))[:10] for m in mods
                           if m.get('templateName') in ('ColonyCore', 'RingCore')
                           and not m.get('constructionCompleted')
                           and not m.get('destroyed')), None)
        cmods = sorted(CT_MODS[m.get('templateName')] for m in mods
                       if m.get('templateName') in CT_MODS
                       and m.get('constructionCompleted') and m.get('powered'))
        nano = len(cmods)
        incoming = []
        for m in mods:
            if m.get('templateName') in CT_MODS and not m.get('constructionCompleted') \
                    and not m.get('destroyed'):
                try:
                    eta = datetime.date.fromisoformat(str(m.get('completionDate'))[:10])
                except ValueError:
                    continue
                incoming.append(((eta - save_date).days, CT_MODS[m.get('templateName')],
                                 m.get('templateName'), eta))
        loc, kind = location(hab)
        metals, approx = body_metals(loc)
        name = str(hab.get('displayName'))
        if not ocs[0].get('powered'):
            unpowered.append(name)
        cands.append({'hab': name, 'loc': loc, 'nano': nano,
                      'metals': metals, 'approx': approx,
                      'days': round(est_days_clicked_now(
                          cmods, [(e[0], e[1]) for e in incoming])),
                      'incoming': ', '.join(
                          f"{t.replace('NanofacturingComplex', 'NFC').replace('Nanofactory', 'NF').replace('ConstructionModule', 'CM')} {eta}"
                          for _, _, t, eta in sorted(incoming)),
                      'oc_powered': bool(ocs[0].get('powered')),
                      'power': power_verdict(power, name),
                      'tier': tier, 't3core_eta': t3core_eta})

    # T3-ready first; then T2-with-core-in-flight; T2-needs-core last. Within a
    # tier group, power-ready before power-short (a CC you can't switch on is
    # 400 metals of nothing, E34), then SPEED — the OpsCenter is dark for the
    # whole build (E28), so days are what the upgrade actually costs.
    # --sort metals restores cheapest-first for a metals-constrained save.
    rank = ((lambda c: (c['metals'], c['days'])) if sort == 'metals'
            else (lambda c: (c['days'], c['metals'])))
    cands.sort(key=lambda c: (0 if c['tier'] >= 3 else (1 if c['t3core_eta'] else 2),
                              c['power'].startswith('POWER SHORT'),
                              *rank(c), c['hab']))
    return cands, unpowered


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('save', nargs='?', default=None,
                    help='save file; omitted = newest save auto-detected')
    ap.add_argument('--faction', default=None)
    ap.add_argument('--sort', choices=('days', 'metals'), default='days',
                    help="ranking key within each tier/power group: 'days' "
                         "(default — minimises the −4 MC blackout while the "
                         "OpsCenter is dark, E28) or 'metals' (cheapest first)")
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
    from extract_snapshot import get_game_date
    import datetime
    gd = get_game_date(gs)
    save_date = datetime.date.fromisoformat(gd[0] if isinstance(gd, tuple) else str(gd)[:10])
    factions = get_factions(gs)
    fid = faction_id_by_template(factions, args.faction)
    cands, unpowered = collect_candidates(gs, fid, save_date, sort=args.sort)

    print(f"{len(cands)} OC→CC candidates (each +10 MC; +6 net vs pre-click "
          f"since the OC goes offline at click time, lesson E28)\n")
    if unpowered:
        print(f"⚡ POWER FIRST — unpowered OpsCenters (+4 MC each, free): "
              f"{', '.join(unpowered)}\n")
    why = ("the OpsCenter is dark for the whole build, so every day costs −4 MC (E28)"
           if args.sort == 'days' else "--sort days to minimise the MC blackout instead")
    key_name = 'BUILD TIME' if args.sort == 'days' else 'METALS COST'
    print(f"Ranked by {key_name} within each tier/power group — {why}.\n")
    print("| # | Hab | Body | Constr mods | Incoming (applies mid-build) | Est days "
          "| MC-days dark | Est metals | Power (+200 net) |")
    print("|---:|---|---|---:|---|---:|---:|---:|---|")
    total = 0
    for i, c in enumerate(cands, 1):
        total += c['metals']
        flag = '' if c['oc_powered'] else ' ⚡OC off'
        if c['tier'] < 3:
            flag += (f" 🔒T3 core ETA {c['t3core_eta']}" if c['t3core_eta']
                     else ' 🔒needs T3 core first')
        print(f"| {i} | {c['hab']}{flag} | {c['loc']} | {c['nano']} "
              f"| {c['incoming'] or '—'} | {c['days']} | {c['days'] * 4} "
              f"| {c['approx']}{c['metals']} | {c['power']} |")
    short = sum(1 for c in cands if c['power'].startswith('POWER SHORT'))
    print(f"\nTotal if all queued: ~{total:,} metals for +{len(cands) * 10} MC cap.")
    print("Pace to the metals buffer — full cost is paid at click time (E24); "
          "a shortfall backfills from Earth as Boost+Money.")
    if short:
        print(f"⚡ {short} candidate(s) can't run the finished CC on current generation "
              f"(POWER SHORT) — build/queue a reactor there first, or spend the metals "
              f"elsewhere. 'idle gen' rows just need a reactor switched on. Solar output "
              f"is a reconstructed estimate; the in-game ☀ readout is truth.")


if __name__ == '__main__':
    main()
