#!/usr/bin/env python3
"""drive_upgrade_finder.py — find researchable-soon drive upgrades in two roles:
combat (high combat thrust) and transit/dV (high EV).

The main extractor's drive table only shows RESEARCHED + AVAILABLE-now drives.
This script also surfaces LOCKED drives with their transitive prereq DEBT (how
many un-researched projects/techs gate them) and the effective RP to unlock,
so you can answer "what's the next drive worth racing toward."

Two figures of merit (per docs/lessons/LESSONS-ships.md S1):
  - WARSHIP fom = combat_thrust × √EV   (combat_thrust = cruise × thrustCap)
  - TRANSIT fom = cruise_thrust × √EV    (high-EV low-thrustCap drives)
Combat g cares about RAW combat thrust; dV cares about EV. We report both plus
the role-appropriate fom, and rank candidates by prereq debt (nearest first).

Usage:
    python drive_upgrade_finder.py <save.json> [--faction <templateName>]
        [--combat-baseline LodestarFissionLantern] [--max-debt 6]

Costs shown are template researchCost AND effective (scaled by the configured research rate).
"""
import json, gzip, argparse, sys
from collections import defaultdict

HERE = __import__('os').path.dirname(__import__('os').path.abspath(__file__))
import os
T = lambda f: os.path.join(HERE, 'templates', f)

# Drive friendlyName overrides (templates lag the running game's UI; LESSONS-ships S5).
DRIVE_FRIENDLY_OVERRIDE = {'NeutronFluxLantern': 'Poseidon Lantern',
                           'NeutronFluxTorch': 'Poseidon Torch'}
from ti_config import CONFIG
# e.g. a 200% campaign research rate → effective RP = template/2 (LESSONS-research R5)
RESEARCH_RATE = CONFIG["research_rate_pct"] / 100.0


def load_save(p):
    with open(p, 'rb') as f:
        magic = f.read(2)
    op = gzip.open if magic == b'\x1f\x8b' else open
    # utf-8-sig: newer saves carry a BOM (inside the gz too)
    with op(p, 'rt', encoding='utf-8-sig') as f:
        return json.load(f)


def kv(gs, suf):
    key = next((k for k in gs if k.endswith(suf)), None)
    out = []
    for e in (gs.get(key) or []):
        k = e.get('Key'); kid = k.get('value') if isinstance(k, dict) else k
        out.append((kid, e.get('Value', {})))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('save')
    ap.add_argument('--faction', default=None)
    ap.add_argument('--combat-baseline', default='Project_LodestarFissionLantern')
    ap.add_argument('--max-debt', type=int, default=8)
    args = ap.parse_args()
    from ti_config import require_faction
    args.faction = require_faction(args.faction)

    save = load_save(args.save)
    gs = save['gamestates']
    drives = json.load(open(T('TIDriveTemplate.json')))
    proj = {p['dataName']: p for p in json.load(open(T('TIProjectTemplate.json')))}
    tech = {t['dataName']: t for t in json.load(open(T('TITechTemplate.json')))}

    fac = next(v for _, v in kv(gs, 'TIFactionState')
               if v.get('templateName') == args.faction)
    fin_proj = set(fac.get('finishedProjectNames') or [])
    avail = set(fac.get('availableProjectNames') or [])
    fin_tech = set(kv(gs, 'TIGlobalResearchState')[0][1].get('finishedTechsNames') or [])
    done = fin_proj | fin_tech

    def fr(n):
        return (proj.get(n) or tech.get(n) or {}).get('friendlyName', n)

    def prereqs(n):
        node = proj.get(n) or tech.get(n)
        if not node:
            return []
        pr = node.get('prereqs') or node.get('requiredTechs') or []
        return [(p.get('dataName') or p.get('name')) if isinstance(p, dict) else p for p in pr]

    def debt(n, seen=None):
        if seen is None:
            seen = set()
        miss = []
        for p in prereqs(n):
            if not p or p in done or p in seen:
                continue
            seen.add(p); miss.append(p); miss += debt(p, seen)
        return miss

    def cost(n):
        return (proj.get(n) or tech.get(n) or {}).get('researchCost', 0) or 0

    # collapse drive variants → per-project best combat & EV; keep cruise of the
    # max-combat variant (that's the x6) and the drive friendly base name.
    fam = defaultdict(lambda: {'ev': 0, 'combat': 0, 'cruise': 0, 'cap': 0,
                               'cool': '?', 'reac': '?', 'cls': '?', 'name': None})
    for d in drives:
        pj = d.get('requiredProjectName')
        if not pj:
            continue
        cruise = (d.get('thrust_N', 0) or 0); cap = d.get('thrustCap', 1) or 1
        ev = d.get('EV_kps') or 0
        f = fam[pj]
        f['ev'] = max(f['ev'], ev)
        if cruise * cap > f['combat']:
            f['combat'] = cruise * cap; f['cruise'] = cruise; f['cap'] = cap
        f['cool'] = d.get('cooling') or '?'; f['reac'] = d.get('requiredPowerPlant') or '?'
        f['cls'] = d.get('driveClassification') or '?'
        base = d.get('friendlyName', pj)
        for k, v in DRIVE_FRIENDLY_OVERRIDE.items():
            if (d.get('dataName') or '').startswith(k):
                base = v + ' (NeutronFlux)'
        # strip trailing " x1".." x6"
        f['name'] = base.rsplit(' x', 1)[0]

    base_combat = fam.get(args.combat_baseline, {}).get('combat', 0)
    import math
    rows = []
    for pj, f in fam.items():
        if f['cls'] == 'Chemical':
            continue
        status = 'RESEARCHED' if pj in fin_proj else ('AVAILABLE' if pj in avail else 'LOCKED')
        miss = [] if status != 'LOCKED' else debt(pj)
        eff_rp = (sum(cost(m) for m in miss) + cost(pj)) / RESEARCH_RATE
        rows.append({
            'pj': pj, 'name': f['name'], 'status': status, 'debt': len(miss),
            'miss': miss, 'eff_rp': eff_rp,
            'combat_MN': f['combat'] / 1e6, 'cruise_MN': f['cruise'] / 1e6,
            'ev': f['ev'], 'cap': f['cap'], 'cool': f['cool'], 'cls': f['cls'],
            'fom_combat': (f['combat'] / 1e6) * math.sqrt(max(f['ev'], 1)),
            'fom_transit': (f['cruise'] / 1e6) * math.sqrt(max(f['ev'], 1)),
        })

    def show(r, role):
        fom = r['fom_combat'] if role == 'combat' else r['fom_transit']
        st = r['status'] if r['status'] != 'LOCKED' else f"debt {r['debt']}"
        print(f"  {r['name']:<26.26} {r['cls']:<16.16} EV{r['ev']:>6.0f} "
              f"combat{r['combat_MN']:>7.0f}MN cruise{r['cruise_MN']:>6.1f}MN cap{r['cap']:>3} "
              f"{r['cool']:<5} fom{fom:>9.0f}  [{st}, ~{r['eff_rp']:.0f} eff RP]")

    print(f"# Drive upgrade finder — {args.faction}")
    print(f"Combat baseline (Lodestar) = {base_combat/1e6:.0f} MN combat thrust.\n")

    print("## 1) COMBAT candidates — higher combat thrust than Lodestar, nearest first")
    print("   (raw combat thrust is what sets combat g; fom = combat×√EV)")
    cc = [r for r in rows if r['combat_MN'] > base_combat / 1e6 and r['status'] != 'RESEARCHED'
          and 'Alien' not in r['pj']]
    for r in sorted(cc, key=lambda x: (x['debt'], -x['combat_MN'])):
        show(r, 'combat')
    print("\n   Fusion LANTERNS that beat Lodestar by FoM (more EV, LESS raw thrust):")
    fl = [r for r in rows if r['fom_combat'] > base_combat/1e6*math.sqrt(31.4)
          and r['combat_MN'] <= base_combat/1e6 and r['status'] != 'RESEARCHED'
          and 'Alien' not in r['pj'] and r['debt'] <= args.max_debt+4]
    for r in sorted(fl, key=lambda x: x['debt'])[:6]:
        show(r, 'combat')

    print("\n## 2) TRANSIT / dV candidates — higher EV than Helicon(314)/Poseidon(66), nearest first")
    dc = [r for r in rows if r['ev'] > 314 and r['status'] != 'RESEARCHED'
          and 'Alien' not in r['pj'] and r['debt'] <= args.max_debt]
    for r in sorted(dc, key=lambda x: (x['debt'], -x['ev'])):
        show(r, 'transit')

    print("\n## 3) ALL un-researched fusion/NSWR drives by remaining RP (UNFILTERED)")
    print("   (the baseline filters above HIDE mid-tier drives — a 2026-07-08 review caught")
    print("   Triton Nova/Torus missing; 'soonest' questions must use THIS section)")
    af = [r for r in rows if r['status'] != 'RESEARCHED' and 'Alien' not in r['pj']
          and r.get('cls') in ('Fusion_Thermal', 'NuclearSaltWater')]
    for r in sorted(af, key=lambda x: x['eff_rp'])[:25]:
        show(r, 'transit')

    print("\n## Shared gateway techs (unlock multiple of the above at once):")
    gate = defaultdict(int)
    near = [r for r in rows if r['status'] == 'LOCKED' and r['debt'] <= args.max_debt
            and (r['ev'] > 314 or r['combat_MN'] > base_combat/1e6)]
    for r in near:
        for m in r['miss']:
            gate[m] += 1
    for m, n in sorted(gate.items(), key=lambda x: -x[1]):
        if n >= 2:
            print(f"  {fr(m):<42} unlocks {n} candidates  (~{cost(m)/RESEARCH_RATE:.0f} eff RP)")


if __name__ == '__main__':
    main()
