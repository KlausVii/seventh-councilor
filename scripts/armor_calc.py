#!/usr/bin/env python3
"""Armor calculations for Terra Invicta ship design.

Verified against the decompiled combat model (`TISpaceShipState.AbsorbAndApplyArmorDamage`
+ `TILaserWeaponTemplate.ModifyArmorValueForLaserShot`), see
[[Mechanics/Space Combat Math]] 2.5b and [[Mechanics/Orbital Bombardment]] 8:

    laser:   through = max(0, incoming * LaserMod   - points^1.5 * rangeFactor)
    kinetic: through = max(0, incoming * KineticMod - points)          # FLAT, not ^1.5

Per-point BLOCKING uses only the point count (^1.5 for laser, flat for kinetic); a
material's ONLY per-point edge is its Resistance specialty (LaserResistance/KineticsResistance
= GetSpecialtyModifiers = product of matching specialty values, default 1.0). So the
point-equivalence between two materials, at the penetration-immunity threshold, is:

    laser:   points_B = points_A * (mod_B / mod_A) ** (2/3)   # ^1.5 block -> exponent 2/3
    kinetic: points_B = points_A * (mod_B / mod_A)            # flat block -> exponent 1

e.g. 80 Nanotube (LaserMod 1.0) vs Hybrid (0.75): 80*(0.75)^(2/3) = 66 Hybrid; and
80 Hybrid = 80*(1/0.75)^(2/3) = 97 Nanotube-equivalent. (The naive x1.25 -> 100/64 is a
~3% approximation; the true factor is 1.211 because the 25% is on DAMAGE and armor is ^1.5.)
Caveat: the threshold metric is exact at zero-penetration; in the high-penetration regime the
laser Resistance multiplier helps MORE, so the resisting material needs even fewer points.

Siege-nose sizing: to multiply the armor BLOCK by N, points scale as N^(exp_inv) where
exp_inv = 2/3 for laser (block ~ points^1.5), 1 for kinetic (block ~ points). Mass and
exotics need the hull-specific mass-per-point (read from the in-game designer) and the
armor's exotics-per-ton.

Usage:
  python3 armor_calc.py equiv --from NanotubeArmor --to HybridArmor --points 80 [--channel laser|kinetic]
  python3 armor_calc.py sizing --armor HybridArmor --base-points 80 --mass-per-point 17 [--exotics-per-ton 0.0005] [--max 252]
  python3 armor_calc.py list

Each subcommand takes --json for machine-readable output.

Templates: reads `templates/TIShipArmorTemplate.json` next to this script (tolerant JSON).
Built 2026-07-15 (bombardment/armor mechanics session).
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, 'templates', 'TIShipArmorTemplate.json')

SPECIALTY = {'laser': 'LaserResistance', 'kinetic': 'KineticsResistance'}
BLOCK_INV_EXP = {'laser': 2.0 / 3.0, 'kinetic': 1.0}   # points ∝ block^exp_inv
BLOCK_EXP = {'laser': 1.5, 'kinetic': 1.0}             # block ∝ points^exp


def load_armor():
    raw = open(TEMPLATE, encoding='utf-8-sig').read()
    data = json.loads(re.sub(r',\s*([}\]])', r'\1', raw))
    return {a['dataName']: a for a in data}


def resist_mod(armor, channel):
    """GetSpecialtyModifiers(spec) = product of matching specialty values (default 1.0).
    Lower value = better resistance (it multiplies incoming damage)."""
    spec = SPECIALTY[channel]
    mod = 1.0
    for s in armor.get('specialties', []):
        if s.get('armorSpecialty') == spec:
            mod *= s.get('value', 1.0)
    return mod


NANOTUBE_CM_PER_POINT = 7.866   # = 19.9 / 2.53; matches the in-game tooltip's 7.86


def cm_per_point(armor):
    """Thickness of ONE armor point for this material (see module docstring)."""
    xray = next((s['value'] for s in armor.get('specialties', [])
                 if s.get('armorSpecialty') == 'XRayResistance'), None)
    if not xray:
        return NANOTUBE_CM_PER_POINT
    return armor['xRayHalfValue_cm'] / xray


def points_per_ton_index(armor):
    """Relative points bought per ton on any given hull section (Nanotube = 1.0).

    mass/point ∝ cm_per_point × density, so points/ton ∝ 1 / (cm_per_point × density).
    Hull-independent because the hull's area cancels.
    """
    ref = NANOTUBE_CM_PER_POINT * 1720.0
    return ref / (cm_per_point(armor) * armor['density_kgm3'])


def cmd_list(armors, as_json=False):
    if as_json:
        rows = [{'armor': name,
                 'laser_mod': resist_mod(a, 'laser'),
                 'kinetic_mod': resist_mod(a, 'kinetic'),
                 'density_kgm3': a.get('density_kgm3'),
                 'xray_half_cm': a.get('xRayHalfValue_cm'),
                 'baryonic_half_cm': a.get('baryonicHalfValue_cm'),
                 'cm_per_point': cm_per_point(a),
                 'points_per_ton_index': points_per_ton_index(a),
                 'cap_multiplier': NANOTUBE_CM_PER_POINT / cm_per_point(a)}
                for name, a in armors.items()]
        print(json.dumps({'armors': rows}, indent=2, default=str))
        return
    print(f"{'armor':22s} {'LaserMod':>9s} {'KineticMod':>11s} {'density':>8s} "
          f"{'X-ray½cm':>9s} {'baryon½cm':>10s} {'cm/pt':>7s} {'pts/t':>7s} {'cap×':>6s}")
    for name, a in armors.items():
        cpp = cm_per_point(a)
        print(f"{name:22s} {resist_mod(a,'laser'):>9.3f} {resist_mod(a,'kinetic'):>11.3f} "
              f"{str(a.get('density_kgm3','?')):>8s} {str(a.get('xRayHalfValue_cm','?')):>9s} "
              f"{str(a.get('baryonicHalfValue_cm','?')):>10s} {cpp:>7.3f} "
              f"{points_per_ton_index(a):>7.2f} {NANOTUBE_CM_PER_POINT / cpp:>6.2f}")
    print("\nMod < 1.0 = that material resists that channel (Hybrid laser 0.75, "
          "Adamantane kinetic 0.75). Mod is a DAMAGE multiplier.")
    print("cm/pt = thickness of one armor point = xRayHalfValue_cm / XRayResistance "
          "(Nanotube 7.866 == tooltip 7.86).")
    print("pts/t = points bought per ton relative to Nanotube (hull-independent); "
          "cap× = multiplier on a hull's NANOTUBE max-point cap (caps are a fixed max "
          "THICKNESS).")
    print("Laser block is points^1.5, so cheap points matter more than the resist mod: "
          "maxed Adamantane blocks ~3x maxed Nanotube on the same hull.")


def cmd_equiv(armors, a_from, a_to, points, channel, as_json=False):
    A, B = armors[a_from], armors[a_to]
    ma, mb = resist_mod(A, channel), resist_mod(B, channel)
    exp = BLOCK_INV_EXP[channel]
    pts_b = points * (mb / ma) ** exp
    ppt_a, ppt_b = points_per_ton_index(A), points_per_ton_index(B)
    pts_same_mass = points * ppt_b / ppt_a
    blk = BLOCK_EXP[channel]
    eff = (pts_same_mass / points) ** blk * (ma / mb)
    cap_factor = (NANOTUBE_CM_PER_POINT / cm_per_point(B)) \
        / (NANOTUBE_CM_PER_POINT / cm_per_point(A))
    if as_json:
        payload = {
            'channel': channel,
            'from': {'armor': a_from, 'mod': ma, 'points': points},
            'to': {'armor': a_to, 'mod': mb, 'points': pts_b},
            'point_equivalence': {'factor': (mb / ma) ** exp, 'exponent': exp,
                                  'metric': 'immunity-threshold'},
            'equal_mass': {'to_points_same_mass': pts_same_mass,
                           'points_per_ton_ratio': ppt_b / ppt_a,
                           'protection_per_ton': eff,
                           'hull_cap_factor': cap_factor},
        }
        print(json.dumps(payload, indent=2, default=str))
        return
    print(f"=== {channel} armor point-equivalence (immunity-threshold metric) ===")
    print(f"{points:g} {a_from} (mod {ma:.3f})  =  {pts_b:.1f} {a_to} (mod {mb:.3f})")
    print(f"  factor on points = (mod_to/mod_from)^{exp:.3f} = "
          f"({mb:.3f}/{ma:.3f})^{exp:.3f} = {(mb/ma)**exp:.3f}")
    if channel == 'laser':
        naive = points * (mb / ma)   # the "x1.25/÷1.25 on points" approximation
        print(f"  (naive linear-on-points approx would give {naive:.1f}; "
              f"true factor uses the ^1.5 -> ^(2/3) exponent)")
    print("  Caveat: exact at the zero-penetration threshold; in the high-penetration "
          "regime the resisting material needs even FEWER points.")
    # Equal-MASS comparison — the equivalence above answers "how many points do I need?",
    # which hides the fact that the same hull section buys a different NUMBER of points per
    # ton for each material (points are a material-specific thickness).
    print(f"\n=== equal-MASS comparison (what the same tonnage actually buys) ===")
    print(f"the tonnage of {points:g} {a_from} points buys {pts_same_mass:.1f} {a_to} points "
          f"({ppt_b/ppt_a:.2f}x the points per ton)")
    print(f"  -> effective protection per ton: {eff:.2f}x "
          f"(block ~ points^{blk:g}, times the {ma:.3f}/{mb:.3f} damage-mod ratio)")
    print(f"  NOTE: also raises the hull cap by {NANOTUBE_CM_PER_POINT/cm_per_point(B) / (NANOTUBE_CM_PER_POINT/cm_per_point(A)):.2f}x "
          f"(caps are a fixed max thickness) — check the cap, not just the mass.")


def cmd_sizing(armors, name, base, mass_per_point, exotics_per_ton, max_pts, channel,
               as_json=False):
    A = armors[name]
    mod = resist_mod(A, channel)
    exp_inv, exp = BLOCK_INV_EXP[channel], BLOCK_EXP[channel]
    targets = [1.0, 1.5, 2.0, 3.0, 4.0, 5.0]
    rows = []
    for N in targets:
        pts = base * (N ** exp_inv)
        if pts > max_pts:
            continue
        rows.append((pts, N))
    # always show the material's max
    rows.append((max_pts, (max_pts / base) ** exp))
    if as_json:
        payload = {
            'armor': name, 'channel': channel, 'resist_mod': mod,
            'mass_per_point_t': mass_per_point, 'exotics_per_ton': exotics_per_ton,
            'base_points': base, 'max_points': max_pts, 'block_exponent': exp,
            'rows': [{'points': pts, 'block_multiplier': N,
                      'mass_t': pts * mass_per_point,
                      'exotics': pts * mass_per_point * exotics_per_ton}
                     for pts, N in rows],
        }
        print(json.dumps(payload, indent=2, default=str))
        return
    print(f"=== {name} siege-nose sizing ({channel} block vs {base:g}-point baseline) ===")
    print(f"resist mod {mod:.3f} | mass/point {mass_per_point:g} t | "
          f"exotics/ton {exotics_per_ton:g} (block ∝ points^{exp:g})")
    print(f"{'points':>7s} {'block×':>7s} {'mass_t':>9s} {'exotics':>8s}")
    for pts, N in rows:
        mass = pts * mass_per_point
        exotics = mass * exotics_per_ton
        print(f"{pts:>7.0f} {N:>6.2f}× {mass:>9.0f} {exotics:>8.2f}")
    print(f"\nTo multiply the block by N: points = {base:g} * N^{exp_inv:.3f}. "
          f"Max nose for {name} = {max_pts:g}.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    l = sub.add_parser('list')
    l.add_argument('--json', action='store_true', help='machine-readable output')
    e = sub.add_parser('equiv')
    e.add_argument('--json', action='store_true', help='machine-readable output')
    e.add_argument('--from', dest='a_from', required=True)
    e.add_argument('--to', dest='a_to', required=True)
    e.add_argument('--points', type=float, required=True)
    e.add_argument('--channel', choices=['laser', 'kinetic'], default='laser')
    s = sub.add_parser('sizing')
    s.add_argument('--json', action='store_true', help='machine-readable output')
    s.add_argument('--armor', required=True)
    s.add_argument('--base-points', type=float, default=80)
    s.add_argument('--mass-per-point', type=float, default=None,
                   help='hull-specific t/pt. Omit and pass --hull to derive it from '
                        'warship_optimizer (preferred); override only from a designer reading.')
    s.add_argument('--hull', default=None,
                   help="derive --mass-per-point and --max from this hull (e.g. Battlecruiser, "
                        "Lancer) using warship_optimizer's calibrated coefficients + caps")
    s.add_argument('--section', choices=['nose', 'tail', 'lateral'], default='nose')
    s.add_argument('--exotics-per-ton', type=float, default=0.0005,
                   help='0.0005 for Hybrid (verified 0.68 exotics / 1357 t); 0 for non-exotic armor')
    s.add_argument('--channel', choices=['laser', 'kinetic'], default='laser')
    s.add_argument('--max', dest='max_pts', type=float, default=None,
                   help='max points for this hull+material; derived when --hull is given')
    args = ap.parse_args()

    if args.cmd == 'sizing':
        if args.hull:
            # Nanotube-calibrated caps (LESSONS-ships S12); scaled by material cm/pt here.
            NANOTUBE_CAPS = {'Lancer': (114, 48), 'Battleship': (91, 38), 'Monitor': (57, 30),
                             'Battlecruiser': (80, 30), 'Dreadnought': (126, 53)}
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import warship_optimizer as _w
            armors_tmp = load_armor()
            if args.hull not in _w.HULL_ARMOR_COEFFICIENTS:
                ap.error(f"no calibrated coefficients for hull {args.hull!r}; "
                         f"known: {', '.join(sorted(_w.HULL_ARMOR_COEFFICIENTS))}")
            coef = _w.HULL_ARMOR_COEFFICIENTS[args.hull][args.section]
            a = armors_tmp[args.armor]
            f = cm_per_point(a) / NANOTUBE_CM_PER_POINT
            derived = coef * f * a['density_kgm3'] / 1000.0
            if args.mass_per_point is None:
                args.mass_per_point = derived
            if args.max_pts is None and args.hull in NANOTUBE_CAPS:
                nt_cap = NANOTUBE_CAPS[args.hull][1 if args.section == 'lateral' else 0]
                args.max_pts = round(nt_cap / f)
            if not args.json:
                print(f"[{args.hull} {args.section} / {args.armor}] derived "
                      f"{derived:.1f} t/pt, max {args.max_pts:g} pts "
                      f"(cm/pt {cm_per_point(a):.3f} vs Nanotube {NANOTUBE_CM_PER_POINT})")
        if args.mass_per_point is None:
            ap.error('sizing needs --mass-per-point or --hull')
        if args.max_pts is None:
            ap.error('sizing needs --max or a --hull with a known cap')

    armors = load_armor()
    if args.cmd == 'list':
        cmd_list(armors, as_json=args.json)
    elif args.cmd == 'equiv':
        for n in (args.a_from, args.a_to):
            if n not in armors:
                sys.exit(f"unknown armor '{n}' — run `armor_calc.py list`")
        cmd_equiv(armors, args.a_from, args.a_to, args.points, args.channel,
                  as_json=args.json)
    elif args.cmd == 'sizing':
        if args.armor not in armors:
            sys.exit(f"unknown armor '{args.armor}' — run `armor_calc.py list`")
        cmd_sizing(armors, args.armor, args.base_points, args.mass_per_point,
                   args.exotics_per_ton, args.max_pts, args.channel,
                   as_json=args.json)


if __name__ == '__main__':
    main()
