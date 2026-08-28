#!/usr/bin/env python3
"""fusion_ladder_planner.py — score fusion reactor+drive PAIRS, not drives alone.

Implements LESSONS-research R20: a fusion global's value is the best PAIR its
ladder produces, judged on three axes —

  1. PER-MASS combat thrust: combat MN / (reactor mass + radiator mass) per
     thruster (LESSONS-ships S14). Reactor lines differ wildly in t/GW and
     efficiency; a "weaker" drive on a lighter, cleaner reactor can beat a
     "stronger" drive per ton of propulsion stack.
  2. PER-HULL absolute thrust: hulls cap at 6 thrusters, so capitals need big
     per-thruster numbers regardless of mass efficiency.
  3. UNLOCK ODDS (LESSONS-research R11): the drive project's
     `factionAvailableChance` can be under 100% — a lifetime lottery, not a
     delay — and its monthly roll is capped by `maxUnlockChance`. A cheap
     second ladder is insurance against a 25%-never linchpin.

Also reported per pair: He3 fuel dependence (mining infrastructure the pair
drags in), propellant, cooling, and the remaining research cost split into
globals vs projects (prereq closure vs YOUR save's completed sets, with
globals already in a research slot discounted — you're paying those anyway).

Usage:
    python fusion_ladder_planner.py <save.json|save.gz> [--faction X]
        [--baseline Project_LodestarFissionLantern] [--radiator-tgw N]
        [--families ICF,Tokamak,ZPinch,Hybrid,Mirror,Electrostatic] [--all]

Costs shown are effective in-game RP (template scaled by the configured
research rate, LESSONS-research R5). Per-shot damage/DPS is not this tool's
job — see the generated Ship Modules tables for weapons.
"""
import json, gzip, argparse, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
T = lambda f: os.path.join(HERE, 'templates', f)

# Drive friendlyName overrides (templates lag the running game's UI; LESSONS-ships S5).
DRIVE_FRIENDLY_OVERRIDE = {'NeutronFluxLantern': 'Poseidon Lantern',
                           'NeutronFluxTorch': 'Poseidon Torch'}

from ti_config import CONFIG
RESEARCH_RATE = CONFIG["research_rate_pct"] / 100.0

FAMILY_ALIASES = {
    'ICF': 'Inertial_Confinement_Fusion',
    'Tokamak': 'Toroid_Magnetic_Confinement_Fusion',
    'ZPinch': 'Z_Pinch_Fusion',
    'Hybrid': 'Hybrid_Confinement_Fusion',
    'Mirror': 'Mirrored_Magnetic_Confinement_Fusion',
    'Electrostatic': 'Electrostatic_Confinement_Fusion',
    'NSWR': 'NuclearSaltWater',
}


from ti_config import load_save  # THE shared loader: gzip magic + BOM, memoized


def kv(gs, suf):
    key = next((k for k in gs if k.endswith(suf)), None)
    out = []
    for e in (gs.get(key) or []):
        k = e.get('Key'); kid = k.get('value') if isinstance(k, dict) else k
        out.append((kid, e.get('Value', {})))
    return out


def load_tpl(name):
    with open(T(name), encoding='utf-8-sig') as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('save')
    ap.add_argument('--faction', default=None)
    ap.add_argument('--baseline', default='Project_LodestarFissionLantern',
                    help='researched drive project to print as the reference row')
    ap.add_argument('--radiator-tgw', type=float, default=None,
                    help='override radiator mass in t per GW of waste heat '
                         '(default: best radiator your faction has researched)')
    ap.add_argument('--families', default='ICF,Tokamak,ZPinch,Hybrid',
                    help='comma list of reactor families to walk '
                         f'({", ".join(FAMILY_ALIASES)})')
    ap.add_argument('--all', action='store_true',
                    help='include every drive of the walked families, even '
                         'clearly-dominated low rungs')
    ap.add_argument('--json', action='store_true', help='machine-readable output')
    args = ap.parse_args()
    from ti_config import require_faction
    args.faction = require_faction(args.faction)

    save = load_save(args.save)
    gs = save['gamestates']
    drives = load_tpl('TIDriveTemplate.json')
    plants = {p['dataName']: p for p in load_tpl('TIPowerPlantTemplate.json')}
    radiators = load_tpl('TIRadiatorTemplate.json')
    proj = {p['dataName']: p for p in load_tpl('TIProjectTemplate.json')}
    tech = {t['dataName']: t for t in load_tpl('TITechTemplate.json')}

    fac = next(v for _, v in kv(gs, 'TIFactionState')
               if v.get('templateName') == args.faction)
    fin_proj = set(fac.get('finishedProjectNames') or [])
    grs = kv(gs, 'TIGlobalResearchState')[0][1]
    fin_tech = set(grs.get('finishedTechsNames') or [])
    done = fin_proj | fin_tech

    # Globals currently in a research slot: their cost is being paid regardless,
    # so remaining-cost figures discount them (reported separately).
    in_slot = set()
    for entry in (grs.get('techProgress') or []):
        name = None
        if isinstance(entry, dict):
            name = entry.get('techTemplateName') or entry.get('templateName')
            if not name and isinstance(entry.get('Key'), dict):
                name = entry['Key'].get('value')
        elif isinstance(entry, str):
            name = entry
        if name and name in tech and name not in fin_tech:
            in_slot.add(name)

    # Radiator: best (lightest per GW waste) the faction has researched.
    rad_tgw, rad_name = args.radiator_tgw, 'override'
    if rad_tgw is None:
        best = None
        for r in radiators:
            sp = r.get('specificPower_2s_KWkg')
            if not sp:
                continue
            req = r.get('requiredProjectName')
            if req and req not in fin_proj:
                continue
            tgw = 1000.0 / sp
            if best is None or tgw < best[0]:
                best = (tgw, r.get('friendlyName', r['dataName']))
        rad_tgw, rad_name = best if best else (125.0, 'Tin Droplet (assumed)')

    def cost(n):
        return (proj.get(n) or tech.get(n) or {}).get('researchCost', 0) or 0

    def closure(name, acc):
        """Uncompleted prereqs, recursively. altPrereq0 substitutes for the
        first prereq when it is already completed."""
        if name in done or name in acc:
            return
        acc.add(name)
        node = tech.get(name) or proj.get(name)
        if not node:
            return
        prereqs = [p for p in (node.get('prereqs') or []) if p]
        alt = node.get('altPrereq0')
        for i, p in enumerate(prereqs):
            if alt and alt in done and i == 0:
                continue
            closure(p, acc)

    wanted = set()
    drive_classes = {d.get('requiredPowerPlant') for d in drives}
    for f in args.families.split(','):
        f = f.strip()
        cls = FAMILY_ALIASES.get(f, f)
        if cls not in drive_classes:
            sys.exit(f'family {f!r} -> powerplant class {cls!r} matches no drive '
                     f'in TIDriveTemplate.json; valid classes: '
                     f'{", ".join(sorted(c for c in drive_classes if c))}')
        wanted.add(cls)

    # One row per drive project: use the x1 variant for per-thruster numbers.
    by_proj = {}
    for d in drives:
        pj = d.get('requiredProjectName')
        if not pj or d.get('requiredPowerPlant') not in wanted:
            continue
        if d.get('thrusters') != 1 and pj in by_proj:
            continue
        if d.get('thrusters') == 1 or pj not in by_proj:
            by_proj[pj] = d

    # Baseline row (any family) for reference.
    base_d = next((d for d in drives if d.get('requiredProjectName') == args.baseline
                   and d.get('thrusters') == 1), None)

    def pair_row(d, pj):
        acc = set()
        closure(pj, acc)
        glob_missing = sorted((a for a in acc if a in tech), key=cost, reverse=True)
        proj_missing = sorted((a for a in acc if a in proj), key=cost, reverse=True)
        glob_rp = sum(cost(a) for a in glob_missing) / RESEARCH_RATE
        glob_rp_beyond = sum(cost(a) for a in glob_missing if a not in in_slot) / RESEARCH_RATE
        proj_rp = sum(cost(a) for a in proj_missing) / RESEARCH_RATE
        fam = d.get('requiredPowerPlant')
        # Reactor rung the pair runs on: highest-tier rung named in the closure,
        # else the best rung of the family already researched.
        rung = None
        rx_in_closure = [a.replace('Project_', '') for a in proj_missing
                         if a.replace('Project_', '') in plants]
        if rx_in_closure:
            rung = max(rx_in_closure, key=lambda r: plants[r].get('maxOutput_GW', 0))
        else:
            fam_done = [p for p in plants.values() if p.get('powerPlantClass') == fam
                        and p.get('specificPower_tGW') is not None
                        and (f"Project_{p['dataName']}" in fin_proj
                             or not p.get('requiredProjectName'))]
            if fam_done:
                # lightest researched rung of the family (t/GW, then efficiency)
                rung = min(fam_done, key=lambda r: (r.get('specificPower_tGW', 99),
                                                    -(r.get('efficiency') or 0)))['dataName']
        req_gw = float(str(d.get('req power', 0) or 0).replace(',', ''))
        rx_t = wh_t = None
        if rung and req_gw:
            r = plants[rung]
            rx_t = req_gw * (r.get('specificPower_tGW') or 0)
            wh_t = req_gw * (1 - (r.get('efficiency') or 1)) * rad_tgw
        combat = (d.get('thrust_N', 0) or 0) * (d.get('thrustCap', 1) or 1) / 1e6
        stack = (rx_t + wh_t) if rx_t is not None else None
        unlock = proj.get(pj, {})
        flags = []
        # unlock-odds flags only matter while the drive is still unresearched
        if pj not in fin_proj:
            if unlock.get('factionAvailableChance', 100) < 100:
                flags.append(f"avail {unlock['factionAvailableChance']}% (can be NEVER)")
            if unlock.get('maxUnlockChance', 100) < 100:
                flags.append(f"roll ≤{unlock['maxUnlockChance']}%/mo")
        if d.get('helium3Fuel'):
            flags.append('He3-fueled (fissile share -> 0 with an active He3 Mine)')
        if d.get('boronFuel'):
            flags.append('needs boron')
        if d.get('cooling') == 'Calc':
            flags.append('open-cycle radiators (combat-vulnerable)')
        base = d.get('friendlyName', pj)
        for k, v in DRIVE_FRIENDLY_OVERRIDE.items():
            if (d.get('dataName') or '').startswith(k):
                base = v
        # propellant per TANK in absolute resource units (1 tank = 100 t = 10 units;
        # LESSONS-ships S20/S23 — players budget refuels in units, not % mixes)
        _abbr = {'water': 'wat', 'volatiles': 'vol', 'fissiles': 'FIS',
                 'metals': 'met', 'nobleMetals': 'nob', 'antimatter': 'am'}
        mix = d.get('perTankPropellantMaterials') or {}
        tank = '+'.join(f"{v * 10:g}{_abbr.get(k, k[:3])}"
                        for k, v in sorted(mix.items(), key=lambda kv: -kv[1]))
        return {
            'name': base.rsplit(' x', 1)[0], 'fam': fam, 'rung': rung,
            'combat': combat, 'ev': d.get('EV_kps') or 0, 'tank': tank or '?',
            'stack': stack, 'mnpt': (combat / stack) if stack else None,
            'glob_rp': glob_rp, 'glob_beyond': glob_rp_beyond, 'proj_rp': proj_rp,
            'glob_missing': glob_missing, 'proj_missing': proj_missing,
            'flags': flags, 'researched': pj in fin_proj,
        }

    rows = [pair_row(d, pj) for pj, d in sorted(by_proj.items())]
    # drop alien-derived drives: gated on Alien Master Project loot, not the
    # research tree this tool plans for
    rows = [r for r in rows
            if not any('AlienMasterProject' in m for m in r['proj_missing'])
            and 'Alien' not in r['name']]
    if not args.all:
        # keep the interesting ones: researched, or best-of-family per fuel tier
        # is hard to define generically — default filter is just "combat ≥ 10 MN
        # or EV ≥ 1000" to drop the clearly-dominated bottom rungs.
        rows = [r for r in rows if r['combat'] >= 10 or r['ev'] >= 1000]
    rows.sort(key=lambda r: (r['glob_beyond'] + r['proj_rp']))
    base_row = pair_row(base_d, args.baseline) if base_d else None

    if args.json:
        payload = {
            'faction': args.faction,
            'radiator': {'name': rad_name, 't_per_gw_waste': rad_tgw},
            'research_rate_pct': CONFIG['research_rate_pct'],
            'in_slot_globals': sorted(in_slot),
            'baseline': base_row,
            'pairs': [r for r in rows if not r['researched']],
        }
        print(json.dumps(payload, indent=2, default=str))
        return

    print(f"# Fusion reactor+drive pair planner — {args.faction}")
    print(f"Radiator assumption: {rad_name} ({rad_tgw:.1f} t per GW of waste heat). "
          f"Effective RP = template × 100/{CONFIG['research_rate_pct']}.")
    if in_slot:
        print(f"Globals already in a research slot (discounted in 'globals left'): "
              f"{', '.join(sorted(in_slot))}")
    print()
    hdr = (f"{'pair (drive @ reactor rung)':44s} {'cbt x1':>7s} {'EV':>6s} "
           f"{'stack t':>8s} {'MN/t':>6s} {'globals':>8s} {'projects':>8s} "
           f"{'per-tank units':>18s}  flags")
    print(hdr)

    def show(r, mark=''):
        st = f"{r['stack']:8.0f}" if r['stack'] is not None else '       ?'
        mn = f"{r['mnpt']:6.3f}" if r['mnpt'] is not None else '     ?'
        nm = f"{r['name']} @ {r['rung'] or '?'}"
        print(f"{nm:44.44s} {r['combat']:7.1f} {r['ev']:6.0f} {st} {mn} "
              f"{r['glob_beyond']:8,.0f} {r['proj_rp']:8,.0f} {r['tank']:>18s}  "
              f"{'; '.join(r['flags'])}{mark}")

    if base_row:
        show(base_row, '  ← baseline')
    for r in rows:
        if r['researched']:
            continue
        show(r)

    print("\n## Closure detail (what each pair still needs)")
    for r in rows:
        if r['researched']:
            continue
        print(f"\n{r['name']}:")
        print(f"  globals: {', '.join(r['glob_missing']) or 'none'}")
        print(f"  projects: {', '.join(r['proj_missing']) or 'none'}")

    print("\nReading the table (LESSONS-research R20): MN/t compares mass-efficiency "
          "across ladders; 'cbt x1' × up-to-6 thrusters is the per-hull ceiling; "
          "avail/roll flags are lottery odds, not delays. First-generation fusion "
          "lanterns typically LOSE to the baseline fission lantern per ton — early "
          "fusion buys exhaust velocity (reach), not combat.")


if __name__ == '__main__':
    main()
