#!/usr/bin/env python3
"""counter_fleet_planner.py — design a screen/fleet to COUNTER a specific enemy fleet.

Given a save and an enemy fleet name, this decomposes that fleet's actual armament into the
three threat channels the PD system treats differently, then sizes the counter:

  1. MISSILES / TORPEDOES  -> killed outright by ANY PD hit (`MissileController.ApplyDamage`).
     Counter = shot COUNT. Cheapest killer is the Point Defense Ion Battery (Charged dispersion
     => `CanOnlyDefensivelyTargetMissiles`, but torpedo bays ARE missiles: they live in
     TIMissileTemplate.json). Sizing = enemy sustained launch rate / PD shot rate.
  2. KINETIC SLUGS (mag/coil/rail) -> NOT killable outright; eroded 10 kg per PD damage point
     (`ProjectileController.ApplyDamage`). ONLY NavalGun-class PD engages them (the 40 mm
     autocannon). Charged-dispersion PD is locked out; lasers chip weakly.
     Sizing = enemy slug MASS rate (kg/s) / per-gun erosion rate (kg/s).
  3. BEAMS (laser / particle) -> uninterceptable. Countered by ARMOR, not PD.
     Plasma bolts are also `isPointDefenseTargetable:false`.

Verified constants (docs/mechanics/Space Combat Math.md §3, code-derived):
  * one hit of any size kills any missile; PD won't fire below 0.15 pts (missiles) / 0.5 (slugs)
  * mag-slug erosion: massDamage_kg += damage_points x 10
  * saturation dedup (max simultaneous engagers per projectile):
        Missile 1 | Magnetic 2 | NavalGun 4 | beam PD UNCAPPED
  * ~20 MJ == 1 damage point (40 mm calibration)

Usage:
    python3 counter_fleet_planner.py <save> --fleet "Victor-72"
    python3 counter_fleet_planner.py <save> --fleet "Victor-72" --screen-hulls 6
"""
import argparse, json, os, sys, glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_snapshot import load_save, kv_items, deref, fac_id_from_field, get_factions
from ti_config import find_templates_dir

P = 'PavonisInteractive.TerraInvicta.'
MJ_PER_DAMAGE_POINT = 20.0     # 40 mm calibration: ~20 MJ == 1 pt
KG_PER_DAMAGE_POINT = 10.0     # ProjectileController.ApplyDamage
SATURATION = {'Missile': 1, 'Magnetic': 2, 'NavalGun': 4, 'Beam': None}   # None = uncapped


def _load(name):
    p = os.path.join(str(find_templates_dir()), name)
    try:
        return {w['dataName']: w for w in json.load(open(p)) if isinstance(w, dict) and w.get('dataName')}
    except Exception:
        return {}


def weapon_tables():
    """dataName -> (channel, template). channel in {missile, slug, beam, plasma}."""
    out = {}
    for fn, ch in (('TIMissileTemplate.json', 'missile'),
                   ('TIMagneticGunTemplate.json', 'slug'),
                   ('TIGunTemplate.json', 'slug'),
                   ('TILaserWeaponTemplate.json', 'beam'),
                   ('TIParticleWeaponTemplate.json', 'beam'),
                   ('TIPlasmaWeaponTemplate.json', 'plasma')):
        for dn, w in _load(fn).items():
            out.setdefault(dn, (ch, w))
    return out


def slug_kg_per_s(w):
    """Sustained inbound slug MASS rate for one mounted weapon."""
    m = w.get('warheadMass_kg') or 0
    salvo = w.get('salvo_shots') or 1
    cd = w.get('cooldown_s') or 0
    return (m * salvo / cd) if (m and cd) else 0.0


def shots_per_s(w):
    salvo = w.get('salvo_shots') or 1
    cd = w.get('cooldown_s') or 0
    return (salvo / cd) if cd else 0.0


def pd_erosion_kg_per_s(w):
    """kg of slug mass a NavalGun-class PD mount strips per second."""
    dmg = w.get('damage_MJ') or 0
    salvo = w.get('salvo_shots') or 1
    cd = w.get('cooldown_s') or 0
    if not (dmg and cd):
        return 0.0
    pts = dmg / MJ_PER_DAMAGE_POINT
    return pts * KG_PER_DAMAGE_POINT * salvo / cd


def main():
    ap = argparse.ArgumentParser(description='Size a counter-fleet against a specific enemy fleet.')
    ap.add_argument('save')
    ap.add_argument('--fleet', required=True, help='enemy fleet displayName, e.g. "Victor-72"')
    ap.add_argument('--faction', default=None, help='your faction templateName')
    ap.add_argument('--screen-hulls', type=int, default=0, help='how many screen ships you plan to build')
    ap.add_argument('--pd-ion', default='PointDefenseIonBattery')
    ap.add_argument('--pd-gun', default='40mmAutocannon')
    a = ap.parse_args()

    from ti_config import require_faction
    me = require_faction(a.faction)
    gs = load_save(a.save)['gamestates']
    facs = get_factions(gs)
    WT = weapon_tables()

    fleet = None
    for fid, fv in kv_items(gs, P + 'TISpaceFleetState'):
        if (fv.get('displayName') or '') == a.fleet:
            fleet = fv
            break
    if fleet is None:
        sys.exit(f'Fleet {a.fleet!r} not found in {a.save}')
    owner = fac_id_from_field(fleet.get('faction'))
    designs = {d['dataName']: d for d in (facs.get(owner, {}).get('shipDesigns') or [])}
    ships = dict(kv_items(gs, P + 'TISpaceShipState'))

    def wl(d, k):
        return [(e if isinstance(e, str) else (e.get('moduleName') or e.get('templateName')))
                for e in (d.get(k) or [])]

    print(f'# Counter-fleet plan vs {a.fleet}  ({facs.get(owner,{}).get("templateName")})')
    n_ships = len(fleet.get('ships') or [])
    print(f'Enemy: {n_ships} ships\n')

    miss_rate = 0.0; miss_bays = 0
    slug_kg = 0.0;  slug_mounts = 0
    beams = 0; enemy_pd = 0
    per_ship = []
    for sref in (fleet.get('ships') or []):
        sv = ships.get(deref(sref))
        if not sv:
            continue
        d = designs.get(sv.get('templateName'), {})
        ws = wl(d, 'noseWeaponTemplateEntries') + wl(d, 'hullWeaponTemplateEntries')
        row = {'name': sv.get('displayName'), 'cls': d.get('_displayName') or sv.get('templateName'),
               'missile': 0, 'slug': 0, 'beam': 0, 'pd': 0}
        for x in ws:
            ch, w = WT.get(x, (None, {}))
            if 'PointDefense' in x:
                enemy_pd += 1; row['pd'] += 1; continue
            if ch == 'missile':
                miss_bays += 1; row['missile'] += 1
                miss_rate += shots_per_s(w)
            elif ch == 'slug':
                slug_mounts += 1; row['slug'] += 1
                slug_kg += slug_kg_per_s(w)
            elif ch in ('beam', 'plasma'):
                beams += 1; row['beam'] += 1
        per_ship.append(row)

    print(f"{'ship':22} {'class':28} {'msl':>4} {'slug':>5} {'beam':>5} {'PD':>3}")
    for r in per_ship:
        print(f"{str(r['name'])[:22]:22} {str(r['cls'])[:28]:28} {r['missile']:4} {r['slug']:5} {r['beam']:5} {r['pd']:3}")

    print(f"\n## Threat channels")
    print(f"  1. MISSILES/TORPEDOES : {miss_bays} bays -> {miss_rate:.2f} launches/s sustained")
    print(f"  2. KINETIC SLUGS      : {slug_mounts} mounts -> {slug_kg:.1f} kg/s inbound mass")
    print(f"  3. BEAMS (armor only) : {beams} mounts  |  their PD mounts: {enemy_pd}")

    ion = WT.get(a.pd_ion, (None, {}))[1]
    gun = WT.get(a.pd_gun, (None, {}))[1]
    ion_rate = shots_per_s(ion)           # kills/s (any hit kills a missile)
    gun_rate = pd_erosion_kg_per_s(gun)   # kg/s eroded

    print(f"\n## Counter sizing")
    if ion_rate:
        need_ion = miss_rate / ion_rate
        print(f"  {a.pd_ion}: {ion_rate:.3f} kills/s each (1 shot / {ion.get('cooldown_s')}s, any hit kills)")
        print(f"    -> need >= {need_ion:.1f} mounts to match sustained launch rate "
              f"(round UP; add margin for misses/geometry)")
    if gun_rate:
        need_gun = slug_kg / gun_rate if gun_rate else 0
        print(f"  {a.pd_gun}: {gun_rate:.1f} kg/s eroded each "
              f"({gun.get('salvo_shots')} shells / {gun.get('cooldown_s')}s)")
        print(f"    -> need >= {need_gun:.1f} mounts to fully neutralise the slug stream")
        print(f"    (erosion is PROPORTIONAL - partial coverage still cuts damage linearly;")
        print(f"     NavalGun saturation caps at {SATURATION['NavalGun']} engagers per projectile)")
    if a.screen_hulls and ion_rate and gun_rate:
        ni = max(1, round(miss_rate / ion_rate + 0.5)); ng = max(1, round(slug_kg / gun_rate + 0.5))
        print(f"\n## Spread over {a.screen_hulls} screen hulls")
        print(f"  total needed: ~{ni} Ion + ~{ng} autocannon")
        print(f"  per hull    : {ni/a.screen_hulls:.1f} Ion + {ng/a.screen_hulls:.1f} autocannon "
              f"-> round to {max(1,-(-ni//a.screen_hulls))} + {max(1,-(-ng//a.screen_hulls))}")
    print("\nNotes: beams/plasma cannot be intercepted - counter with ARMOR "
          "(match the plate to their damage type). Their low PD count is YOUR missile opening.")


if __name__ == '__main__':
    main()
