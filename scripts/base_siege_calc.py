#!/usr/bin/env python3
"""Alien-base siege planner — the reactor-farm POWER CASCADE + interception wall.

Code-verified model (`TIHabState.UpdatePowerManagement`, `TISpaceFleetState.FireMission`);
see docs/mechanics/Orbital Bombardment.md § 8. Against a defended alien base you do NOT out-shoot
the battlestations — you starve them of power:

  * Reactor farms (+power each) are NOT combat modules -> no x8 anti-bombardment armor ->
    soft; ONLY beams (lasers) reach them (kinetics/nukes are intercepted).
  * Battlestations/Citadels are `PowerFirst` -> they hold power until supply < combat demand.
    Kill reactor farms and, past the point where supply drops below combat demand, the
    lowest-priority battlestations go DARK: each dark one stops intercepting, stops STO
    return fire, and its armor halves (x8 -> x4). Snowball -> base collapses -> capture.

This script tallies a target base's modules (from a save, or manual counts) and prints the
cascade: powered battlestations vs reactor kills, the falling interception "num", and the
key thresholds (first-dark, half-dark, full-collapse).

Usage:
  python3 base_siege_calc.py --save <save.json|.gz> --base "<alien base displayName>"
  python3 base_siege_calc.py --reactors 6 --battlestations 9 --citadels 2
  [--reactor-power 300] [--bs-power 150] [--citadel-power 60]     # override defaults
  [--defense-dps 21.3]  # AlienT3BaseDefenseLaser = 768 MJ / 36 s ; [--altitude low|med|high]

Defaults are the verified AlienT3 fortress-base values.
Built 2026-07-15 (bombardment mechanics session).
"""
import argparse, gzip, json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Code-verified module power (TIHabModuleTemplate.json): reactor farm +300, battlestation
# -150, citadel -60. Alien T3 base defense laser: 768 MJ / 36 s = 21.3 MJ/s. Interception
# multiplier x60 (habDefensesPDDPSMultiplier); altitude term 1 + (alt_km-200)/200.
DEF = dict(reactor_power=300, bs_power=150, citadel_power=60, defense_dps=768/36,
           pd_mult=60, tier=3)
ALT_KM = {'low': 200, 'med': 400, 'high': 600}

# num2 (attack side) per KINETIC mount = impact_vel_kps^2 * 0.5 * warheadMass_kg / avgCooldown_s
# (`TISpaceFleetState.FireMission`; salvo-adjusted cd = (cd+(salvo-1)*intra)/salvo). Muzzle
# vel used as impact proxy (slightly underestimates — surface fall adds a little). Interception
# ratio = num/num2, rolled per projectile: ratio>=1 => 100% intercepted, ANY leak needs num2>num.
KINETIC_NUM2 = {  # per mount, Mk3 tier
    'spinal_siege_coiler': 547, 'heavy_siege_coiler': 362,
    'heavy_rail_cannon': 133, 'rail_cannon': 73,
}


from ti_config import load_save  # THE shared loader: gzip magic + BOM, memoized


def tally_base(save_path, base_name):
    gs = load_save(save_path)['gamestates']
    def K(k): return k['value'] if isinstance(k, dict) else k
    def states(name): return next((gs[k] for k in gs if k.endswith(name)), [])
    sec2hab, target = {}, None
    for h in states('TIHabState'):
        v = h['Value']
        for s in (v.get('sectors') or []):
            sec2hab[K(s)] = K(h['Key'])
        if v.get('displayName') == base_name:
            target = K(h['Key'])
    if target is None:
        sys.exit(f"base '{base_name}' not found in save")
    from collections import Counter
    c = Counter()
    for m in states('TIHabModuleState'):
        v = m['Value']
        if sec2hab.get(K(v.get('sector'))) == target and v.get('exists') and not v.get('destroyed'):
            c[v.get('templateName')] += 1
    return dict(
        reactors=c.get('AlienFusionReactorFarm', 0),
        battlestations=c.get('AlienBattlestations', 0),
        citadels=c.get('AlienCitadel', 0),
        others=sum(n for t, n in c.items()
                   if t not in ('AlienFusionReactorFarm', 'AlienBattlestations', 'AlienCitadel')),
        raw=dict(c),
    )


def cascade(reactors, battlestations, citadels, p, kinetic_num2=0):
    supply0 = reactors * p['reactor_power']
    combat_demand = battlestations * p['bs_power'] + citadels * p['citadel_power']
    alt_mult = 1 + (p['altitude_km'] - 200) / 200
    print(f"=== POWER CASCADE — {reactors} reactor farms, {battlestations} battlestations, "
          f"{citadels} citadels ===")
    print(f"supply {supply0} (={reactors}x{p['reactor_power']}) | combat demand {combat_demand} "
          f"(bs {battlestations}x{p['bs_power']} + cit {citadels}x{p['citadel_power']})")
    print(f"interception num = powered_bs x tier {p['tier']} x defenseDPS {p['defense_dps']:.1f} "
          f"x {p['pd_mult']} x altitude {alt_mult:.1f} (alt {p['altitude_km']} km)\n")
    leak_col = f" {'kinetics leak?':>16s}" if kinetic_num2 else ""
    print(f"{'reactors killed':>15s} {'supply':>7s} {'bs powered':>11s} {'bs dark':>8s} "
          f"{'interception num':>17s}{leak_col}")
    first_dark = half_dark = full = kin_leak = None
    for k in range(reactors + 1):
        supply = (reactors - k) * p['reactor_power']
        # battlestations are highest PowerFirst priority -> claim power first
        bs_pow = min(battlestations, supply // p['bs_power'])
        bs_dark = battlestations - bs_pow
        num = bs_pow * p['tier'] * p['defense_dps'] * p['pd_mult'] * alt_mult
        leak = ""
        if kinetic_num2:
            if num == 0:
                leak = " ALL (base dark)"
            elif kinetic_num2 > num:
                leak = f" YES ({(1-num/kinetic_num2)*100:.0f}% land)"
            else:
                leak = " no (num2<=num)"
            if kin_leak is None and (num == 0 or kinetic_num2 > num):
                kin_leak = k
        print(f"{k:>15d} {supply:>7d} {bs_pow:>11d} {bs_dark:>8d} {num:>17,.0f}{leak}")
        if first_dark is None and bs_dark >= 1:
            first_dark = k
        if half_dark is None and bs_dark >= battlestations / 2:
            half_dark = k
        if full is None and bs_pow == 0:
            full = k
    print(f"\nThresholds: first battlestation dark at {first_dark} reactor kills; "
          f"half dark at {half_dark}; full collapse at {full}.")
    print("Each dark battlestation: -1 interception source, -1 STO beam/cycle (fleet survives "
          "longer), armor x8->x4. Snowball accelerates past the first-dark point.")
    if kinetic_num2:
        need_full = math.ceil(num0 / KINETIC_NUM2['spinal_siege_coiler']) if (num0 := battlestations*p['tier']*p['defense_dps']*p['pd_mult']*alt_mult) else 0
        print(f"\nKinetic num2 = {kinetic_num2:,.0f}. Kinetics leak only when num2 > num "
              f"(interception is a hard wall until then — ratio>=1 = 100% intercepted).")
        print(f"  -> your kinetics start landing at {kin_leak} reactor kills. To leak vs the "
              f"FULLY powered base ({num0:,.0f}) you'd need ~{need_full} Spinal Siege Coiler Mk3 "
              f"mounts (547 each) — infeasible. Kinetics are a FINISHER after lasers de-power, "
              f"not an opener.")
    print("DOCTRINE: 720cm+ Green Arc (or UV Phaser) LASERS vs the reactor farms (only beams "
          "reach them) — Hybrid armor + ECM3 siege hulls (armor_calc.py), LOW orbit. Kinetics "
          "(incl. siege coilers) are intercepted vs a powered base; carrying them there also "
          "RAISES the ship's bombardmentValue -> draws MORE STO fire for zero gain. Siege "
          "coilers' real value is the FLEET war (nose-breakers). Mk3>>Mk2>>Mk1; Spinal>Heavy.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--save')
    ap.add_argument('--base', help='target base displayName (required with --save)')
    ap.add_argument('--reactors', type=int)
    ap.add_argument('--battlestations', type=int)
    ap.add_argument('--citadels', type=int, default=0)
    ap.add_argument('--reactor-power', type=int, default=DEF['reactor_power'])
    ap.add_argument('--bs-power', type=int, default=DEF['bs_power'])
    ap.add_argument('--citadel-power', type=int, default=DEF['citadel_power'])
    ap.add_argument('--defense-dps', type=float, default=DEF['defense_dps'])
    ap.add_argument('--altitude', choices=['low', 'med', 'high'], default='low')
    ap.add_argument('--spinal-siege-coiler-mk3', type=int, default=0, dest='spinal',
                    help='count of Spinal Siege Coiler Mk3 mounts (num2 547 each) to test kinetic leak')
    ap.add_argument('--heavy-siege-coiler-mk3', type=int, default=0, dest='heavy',
                    help='count of Heavy Siege Coiler Mk3 mounts (num2 362 each)')
    args = ap.parse_args()

    if args.save:
        if not args.base:
            sys.exit("--base <displayName> is required with --save")
        t = tally_base(args.save, args.base)
        print(f"[{args.base}] modules: {t['raw']}\n")
        reactors, bs, cit = t['reactors'], t['battlestations'], t['citadels']
    elif args.reactors is not None and args.battlestations is not None:
        reactors, bs, cit = args.reactors, args.battlestations, args.citadels
    else:
        sys.exit("provide either --save (+--base) or --reactors and --battlestations")

    p = dict(reactor_power=args.reactor_power, bs_power=args.bs_power,
             citadel_power=args.citadel_power, defense_dps=args.defense_dps,
             pd_mult=DEF['pd_mult'], tier=DEF['tier'], altitude_km=ALT_KM[args.altitude])
    kinetic_num2 = (args.spinal * KINETIC_NUM2['spinal_siege_coiler']
                    + args.heavy * KINETIC_NUM2['heavy_siege_coiler'])
    cascade(reactors, bs, cit, p, kinetic_num2)


if __name__ == '__main__':
    main()
