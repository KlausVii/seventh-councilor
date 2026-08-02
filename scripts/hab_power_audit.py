#!/usr/bin/env python3
"""hab_power_audit.py — per-hab POWER ledger: generation vs draw, idle generators,
and powerable-now verdicts for every built-but-unpowered module.

Answers: "do I have unpowered mines / research campuses / Ops Centers I could power
back on RIGHT NOW?", "which habs can absorb a Command Center's +200 net draw?",
"is this hab short on power, and would switching its idle reactors on fix it?"

For every player hab, computes:
  - GENERATION from powered+completed generators. Solar modules use the reconstructed
    solar law (docs/mechanics/Hab Power and Solar Output.md): natural multiplier =
    dayFraction x atmosphereFactor x (1 AU / a)^2 for surface sites (validated vs
    in-game readouts on Mars/Mercury/Io), horizon-shadow variant for orbits. Solar
    MIRROR bonus is NOT modeled (not reconstructible from the save) — habs at
    mirror-equipped bodies are flagged and real output is HIGHER than shown.
  - DRAW from powered+completed consumers (flat template power).
  - IDLE generator capacity (completed, powered=false — instant to switch on).
  - Every built-but-unpowered consumer, with a verdict:
      POWER ON NOW           surplus alone covers it
      SWITCH IDLE GEN(S) ON  surplus + idle generator capacity covers it
      SHORT by N             needs new generation (in-flight generators listed)
    …each annotated with the module's `supportMaterials_month` upkeep, because
    "can I power it" and "should I power it" are different questions (E37):
    an AdministrationTower is +1 MC for 4 boost/month, a CommandCenter's
    +10 MC costs no boost at all, and a Farm has no upkeep whatsoever.
  - Generators still under construction (sequencing: safe to click a consumer that
    finishes after the reactor lands — check ETAs with module_completion_dates.py).

Ground truth: the in-game site ☀ readout and each module's Generator line. Solar
figures here are estimates — exact for validated atmosphere classes, low for
mirror-equipped bases (flagged).

Usage:
    python3 hab_power_audit.py [save.json|.gz] [--faction <templateName>]
        [--module Mine --module ResearchCampus] [--all] [--json]

    --module X   only show unpowered modules whose templateName contains X
                 (case-insensitive; repeatable). Default: all unpowered modules.
    --all        include habs with no unpowered modules (full power ledger).
    --json       machine-readable output.
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mine_completion_timeline import load_save, kv_items, deref
from ti_config import CONFIG, newest_save, find_templates_dir

AU_M = 149_597_870_700.0
SOLAR_RULE = 'Solar_Power_Variable_Output'
# docs/mechanics/Hab Power and Solar Output.md — None/Trace/Thin validated in-game;
# Standard/Thick/Dense extrapolated (confirm vs the site's ☀ readout before trusting).
ATMOS_FACTOR = {None: 1.0, 'None': 1.0, 'Trace': 1.0, 'Thin': 0.75,
                'Standard': 0.5, 'Medium': 0.5, 'Thick': 0.25, 'Dense': 0.0}
MIRROR_MODULES = ('SolarMirror', 'SolarMirrorArray', 'AutomatedSolarMirror')


def load_templates():
    tdir = find_templates_dir()
    if tdir is None:
        raise SystemExit("scripts/templates/ missing — run sync_game_data.py first")
    mods = {t['dataName']: t for t in
            json.load(open(os.path.join(str(tdir), 'TIHabModuleTemplate.json'),
                           encoding='utf-8'))}
    bodies = {t['dataName']: t for t in
              json.load(open(os.path.join(str(tdir), 'TISpaceBodyTemplate.json'),
                             encoding='utf-8'))}
    return mods, bodies


def sun_ancestor(body, bodies_by_id):
    """Walk barycenters up to the Sun-orbiting ancestor (moons -> their planet)."""
    cur = body
    for _ in range(6):
        bc = cur.get('barycenter')
        parent = bodies_by_id.get(deref(bc)) if bc else None
        if parent is None or parent.get('displayName') == 'Sol':
            return cur
        cur = parent
    return cur


def sun_sma_au(body, bodies_by_id, body_tmpl):
    anc = sun_ancestor(body, bodies_by_id)
    t = body_tmpl.get(anc.get('templateName') or '')
    if t and t.get('semiMajorAxis_AU'):
        return t['semiMajorAxis_AU']
    gp = anc.get('globalPosition') or {}
    r = math.sqrt(gp.get('x', 0) ** 2 + gp.get('y', 0) ** 2 + gp.get('z', 0) ** 2)
    return (r / AU_M) if r else 1.0


def natural_solar_multiplier(hab, site, body, orbit, bodies_by_id, body_tmpl):
    """Reconstruct solarMultiplier (NOT in the save). Estimate — see the mechanics doc."""
    if body is None:
        return 0.0
    a = sun_sma_au(body, bodies_by_id, body_tmpl)
    inv_r2 = 1.0 / (a * a) if a else 0.0
    bt = body_tmpl.get(body.get('templateName') or '', {})
    if site is not None:                      # surface base
        frac = 0.5
        lat = site.get('latitude') or 0.0
        bc = body.get('barycenter')
        parent = bodies_by_id.get(deref(bc)) if bc else None
        sun_orbiting = parent is not None and parent.get('displayName') == 'Sol'
        if sun_orbiting and bt.get('tilt_Deg', 90) < 5 and abs(lat) > 85:
            frac = 0.5 + abs(lat) / 360.0     # polar near-constant illumination (estimate)
        return frac * ATMOS_FACTOR.get(bt.get('atmosphere'), 1.0) * inv_r2
    if orbit is not None:                     # station: horizon-shadow variant (estimate)
        sma_km = orbit.get('semiMajorAxis_km') or orbit.get('semiMajorAxis') or 0
        radius = bt.get('equatorialRadius_km', 0)
        if sma_km and radius:
            return (1 - math.atan(radius / sma_km) / math.pi) * inv_r2
    return inv_r2


def support_cost(tname, mod_tmpl):
    """`supportMaterials_month` for a module, non-zero entries only.

    The ONGOING cost of flipping a module on. Always show this next to a
    power-on verdict: 'powerable' is a power question, 'worth powering' is a
    support-materials question, and the two have different answers (lesson
    E37 — an Administration Tower is +1 MC for 4 boost/month, while a
    CommandCenter's +10 MC costs no boost at all)."""
    sm = (mod_tmpl.get(tname, {}) or {}).get('supportMaterials_month') or {}
    return {k: v for k, v in sm.items() if v}


def power_ledger(gs, fac_id, mod_tmpl, body_tmpl, filters=(), include_all=False):
    """Per-hab power rows for one faction. Shared by this tool's CLI and by
    cc_upgrade_planner.py (a CommandCenter's +200 net draw needs headroom)."""
    filters = [f.lower() for f in filters]
    habs = dict(kv_items(gs, 'TIHabState'))
    sites = dict(kv_items(gs, 'TIHabSiteState'))
    bodies = dict(kv_items(gs, 'TISpaceBodyState'))
    orbits = dict(kv_items(gs, 'TIOrbitState'))

    sec2hab = {}
    for hid, h in habs.items():
        for s in (h.get('sectors') or []):
            sec2hab[deref(s)] = hid

    habmods, free_slots = {}, {}
    for _, m in kv_items(gs, 'TIHabModuleState'):
        if m.get('archived') or m.get('destroyed') or not m.get('exists'):
            continue
        hid = sec2hab.get(deref(m.get('sector'))) if m.get('sector') else None
        if hid is None:
            continue
        if not m.get('templateName'):
            free_slots[hid] = free_slots.get(hid, 0) + 1
            continue
        habmods.setdefault(hid, []).append(m)

    # bodies with own mirror stations -> solar output on bases there is UNDER-estimated
    mirror_bodies = set()
    for hid, ms in habmods.items():
        h = habs[hid]
        if deref(h.get('faction')) != fac_id or h.get('habSite'):
            continue
        ob = orbits.get(deref(h.get('orbitState'))) if h.get('orbitState') else None
        body_id = deref(ob.get('barycenter')) if ob and ob.get('barycenter') else None
        if body_id is None:
            continue
        for m in ms:
            if m['templateName'] in MIRROR_MODULES and m.get('constructionCompleted') \
                    and m.get('powered'):
                mirror_bodies.add(body_id)

    rows = []
    for hid, ms in sorted(habmods.items(), key=lambda kv: habs[kv[0]]['displayName'] or ''):
        h = habs[hid]
        if deref(h.get('faction')) != fac_id:
            continue
        site = sites.get(deref(h.get('habSite'))) if h.get('habSite') else None
        orbit = orbits.get(deref(h.get('orbitState'))) if h.get('orbitState') else None
        body = None
        if site is not None:
            body = bodies.get(deref(site.get('parentBody')))
        elif orbit is not None and orbit.get('barycenter'):
            body = bodies.get(deref(orbit.get('barycenter')))

        def out_power(tname):
            t = mod_tmpl.get(tname, {})
            p = t.get('power', 0) or 0
            if p > 0 and SOLAR_RULE in (t.get('specialRules') or []):
                mult = natural_solar_multiplier(h, site, body, orbit, bodies, body_tmpl)
                return min(round(p * mult), 8 * p), True
            return p, False

        gen = draw = idle_gen = 0
        solar_est = False
        unpowered, building_gens = [], []
        for m in ms:
            p, is_solar = out_power(m['templateName'])
            if not m.get('constructionCompleted'):
                if p > 0:
                    building_gens.append(m['templateName'])
                continue
            solar_est = solar_est or (is_solar and m.get('powered'))
            if m.get('powered'):
                if p >= 0:
                    gen += p
                else:
                    draw += -p
            elif p > 0:
                idle_gen += p
            else:
                unpowered.append((m['templateName'], -p))

        surplus = gen - draw
        shown = [u for u in unpowered
                 if not filters or any(f in u[0].lower() for f in filters)]
        if not shown and not include_all:
            continue
        verdicts = []
        for tname, need in sorted(shown, key=lambda x: -x[1]):
            if surplus >= need:
                v = 'POWER ON NOW'
            elif surplus + idle_gen >= need:
                v = 'SWITCH IDLE GEN(S) ON'
            else:
                v = f'SHORT by {need - surplus - idle_gen}'
                if building_gens:
                    v += f" (in-flight: {', '.join(sorted(set(building_gens)))})"
            verdicts.append({'module': tname, 'draw': need, 'verdict': v,
                             'support_month': support_cost(tname, mod_tmpl)})
        rows.append({
            'hab': h['displayName'], 'type': h.get('habType'), 'tier': h.get('tier'),
            'body': (body or {}).get('displayName'),
            'generation': gen, 'draw': draw, 'surplus': surplus,
            'idle_generator_capacity': idle_gen, 'free_slots': free_slots.get(hid, 0),
            'solar_estimated': solar_est,
            'mirrors_at_body': body is not None and deref(body.get('ID')) in mirror_bodies
                               and site is not None,
            'generators_building': sorted(set(building_gens)),
            'unpowered': verdicts,
        })
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('save', nargs='?', help='save file (default: newest)')
    ap.add_argument('--faction', default=CONFIG.get('faction'))
    ap.add_argument('--module', action='append', default=[],
                    help='filter unpowered modules by templateName substring (repeatable)')
    ap.add_argument('--all', action='store_true',
                    help='include habs with no unpowered modules')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()

    path = args.save or newest_save()
    if not path:
        raise SystemExit("no save found — pass a path or set save_dir in config.json")
    if not args.faction:
        raise SystemExit("faction unknown — set it in config.json or pass --faction")

    mod_tmpl, body_tmpl = load_templates()
    gs = load_save(path)['gamestates']
    fac_id = next((fid for fid, f in kv_items(gs, 'TIFactionState')
                   if f.get('templateName') == args.faction), None)
    if fac_id is None:
        raise SystemExit(f"faction {args.faction!r} not found in save")

    rows = power_ledger(gs, fac_id, mod_tmpl, body_tmpl,
                        filters=args.module, include_all=args.all)

    if args.json:
        print(json.dumps(rows, indent=1))
        return
    if not rows:
        print("No unpowered modules matched on any of your habs. (--all for full ledger)")
        return
    for r in rows:
        flags = []
        if r['solar_estimated']:
            flags.append('solar output ESTIMATED — UI is truth')
        if r['mirrors_at_body']:
            flags.append('mirror stations at body — real output HIGHER')
        head = (f"{r['hab']} ({r['type']} T{r['tier']}, {r['body'] or 'deep space'}) — "
                f"gen {r['generation']}, draw {r['draw']}, surplus {r['surplus']:+}"
                f", idle gens {r['idle_generator_capacity']}")
        print(head + (('  [' + '; '.join(flags) + ']') if flags else ''))
        if r['generators_building']:
            print(f"    building now: {', '.join(r['generators_building'])}")
        for v in r['unpowered']:
            sm = v.get('support_month') or {}
            cost = ('  [upkeep/mo: '
                    + ', '.join(f"{k} {g:g}" for k, g in sm.items()) + ']') if sm else \
                   '  [no upkeep]'
            print(f"    {v['module']:<28} needs {v['draw']:<5} {v['verdict']}{cost}")
        print()


if __name__ == '__main__':
    main()
