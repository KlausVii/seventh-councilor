#!/usr/bin/env python3
"""
General Terra Invicta warship loadout optimizer.

Reads canonical hull, drive, and armor data from game templates. Computes
ΔV / combat acceleration / turn rate for any (hull, drive, armor, tanks,
nose, body, tail) configuration, and provides an optimizer that maximizes
nose armor under defender-doctrine constraints.

Quick start
-----------
    from warship_optimizer import Warship, optimize_armor

    ship = Warship(
        hull='Lancer',
        drive='LodestarFissionLanternx3',
        armor='NanotubeArmor',
        tanks=40,
        nose=40, body=2, tail=6,
    )
    ship.calibrate(measured_wet_t=29313)   # back-solves 'other' mass
    print(ship)
    # Lancer / LodestarFissionLanternx3 / NanotubeArmor / tanks=40 …
    # → ΔV 5.51 kps, 2.30 g, 0.380 deg/s, 29,313 t wet

    for nose, body, tail, dv, gs, t, wet, arm in optimize_armor(ship, min_dv_kps=4.0):
        print(f'  nose {nose}, body {body}, tail {tail}: {arm:,.0f} t armor')

Calibration design
------------------
- **Armor density** is read directly from `TIShipArmorTemplate.json` — exact.
- **Armor geometry** (m³ per thickness point per section) is hull-specific.
  Pre-calibrated for the Lancer (back-solved from a measured shipbuilder
  reading). Other hulls fall back to a length×width formula that's roughly
  correct but not exact. Best practice: calibrate by recording a
  shipbuilder reading once per hull and adding to `HULL_ARMOR_COEFFICIENTS`.
- **Drive thrust / EV / thrustCap** read directly from `TIDriveTemplate.json`.
- **Drive mass** (not in any template) is back-solved per drive family from
  calibration data and stored in `DRIVE_MASS_PER_THRUSTER_T`. Currently
  populated for `LodestarFissionLantern` only; extend as new readings come in.
- **'Other' mass** (hull + reactor + weapons + non-armor utilities + drive)
  is back-solved per ship via `ship.calibrate(measured_wet_t=...)`. Always
  pass a real shipbuilder reading for accurate predictions.
- **Turn rate constant** is currently Lancer-specific. Predictions for other
  hulls will be off until per-hull K is back-solved. Pass a measured
  turn rate to `ship.calibrate_turn(measured_turn_dps)` to fix.
"""
import os
import json
import math
import re
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict, Any

# ============================================================
# Game-template loading
# ============================================================

def _find_templates_dir() -> Optional[str]:
    # Single source of truth for game-data discovery: mirror-first, config-aware.
    from ti_config import find_templates_dir
    p = find_templates_dir()
    return str(p) if p else None


_TEMPLATE_CACHE: Dict[str, Dict[str, Any]] = {}


def _load_template(filename: str) -> Dict[str, Any]:
    """Load a template file once, cache by filename. Returns dict
    keyed by dataName (and friendlyName as alias)."""
    if filename in _TEMPLATE_CACHE:
        return _TEMPLATE_CACHE[filename]
    tdir = _find_templates_dir()
    if not tdir:
        raise FileNotFoundError(
            f'Cannot find {filename}. Game templates not reachable — '
            f'run sync_game_data.py or set game_install_dir in config.json.')
    with open(os.path.join(tdir, filename)) as f:
        entries = json.load(f)
    by_name: Dict[str, Any] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        dn = entry.get('dataName')
        fn = entry.get('friendlyName')
        if dn:
            by_name[dn] = entry
        if fn and fn not in by_name:
            by_name[fn] = entry
    _TEMPLATE_CACHE[filename] = by_name
    return by_name


def hull_template(name: str) -> Dict[str, Any]:
    return _load_template('TIShipHullTemplate.json')[name]


def drive_template(name: str) -> Dict[str, Any]:
    return _load_template('TIDriveTemplate.json')[name]


def armor_template(name: str) -> Dict[str, Any]:
    return _load_template('TIShipArmorTemplate.json')[name]


# ============================================================
# Empirical calibration constants
# ============================================================

# Drive mass per thruster — calibrated against in-game shipbuilder screenshots.
# Each entry is (per-thruster wet mass in tons, calibrated against reactor spec_power_tGW).
# For reactor-powered drives, the total mass includes both drive hardware AND the
# reactor mass needed to power the drive (which scales with reactor tier).
# Use mass_per_thruster_on_reactor() below to adjust for any reactor tier.
#
# **Calibration source for Lodestar (2026-05-31)**: a reference-campaign
# battleship class, 4 screenshots varying only Lodestar thruster count, all on
# Gas Core V (Terawatt II, 3.5 t/GW):
#   x1 wet 28,194 t  →  x2 wet 30,014 t  →  x3 wet 31,834 t  →  x4 wet 33,655 t
#   Per-thruster wet mass: **1,820 t** (consistent across all 4 readings)
#   Construction cost per thruster: 131.5 metals + 19.6 noble + 3.3 fissiles +
#                                    33 vol + 6.5 water (≈ 194 t total resources)
#
# Combat thrust verification (per-thruster × thrustCap / wet_mass × g):
#   x1: predicted 0.795g vs measured 0.796g ✓
#   x4: predicted 2.665g vs measured 2.7g  ✓
#
# A previous baseline-design-derived value of 3,737 t/thruster on Gas Core IV had a
# ~2,000 t/thruster discrepancy that's unaccounted for (possibly radiator
# scaling, possibly armor differences between the user's 3-drive and 6-drive
# baseline-design measurements). The calibration screenshots use controlled variation
# (only thruster count changes), so they're more reliable.
DRIVE_MASS_PER_THRUSTER_T: Dict[str, Tuple[float, float]] = {
    # (per_thruster_wet_t, calibrated_reactor_spec_power_tGW)
    'LodestarFissionLantern': (1820, 3.5),   # calibration BC on Gas Core V (Terawatt II)
    # Template-derived estimate on Gas Core VI + Tin Droplet:
    # req_power 147.059 GW × (1 t/GW + 0.04 × 125 t/GW waste) = 882.4 t.
    # Not yet shipbuilder-calibrated; use for first-pass Firestar comparisons.
    'FirestarFissionLantern': (882.4, 1.0),
    # Template-derived estimate on Gas Core III + Tin Droplet:
    # req_power 13.35 GW × (3 t/GW + 0.05 × 125 t/GW waste) = 123.5 t.
    # This preserves the analyzer's observed GC-III → GC-VI saving of ~160 t
    # on Pharos x6 hulls.
    'PharosDrive':            (123.5, 3.0),
    'NeutronFluxLantern':     (328,  None),   # Poseidon, self-powered (in-game shipbuilder reading)
    # Poseidon TORCH — same NSWR family/hardware as the Lantern (self-powered, thrustCap 2,
    # 13.0 vs 12.9 MN/thruster); only EV differs (1700 vs 66). Mass ESTIMATED from the Lantern
    # reading — not itself shipbuilder-calibrated; re-calibrate from an in-game reading (S8).
    'NeutronFluxTorch':       (328,  None),
}

# Per-thruster construction cost (in tons of resource) for adding/removing
# a single thruster from a drive group. Calibrated from the BC calibration series.
DRIVE_COST_PER_THRUSTER: Dict[str, Dict[str, float]] = {
    'LodestarFissionLantern': {
        'metals':    131.5,   # 100% drive hardware + reactor mats overhead
        'water':       6.5,
        'volatiles':  33.0,
        'noble':      19.6,   # mostly reactor (30% noble) scaled by req power
        'fissiles':    3.3,   # reactor (5% fissiles)
    },
}

# Per-thruster reactor power demand (GW). Used by mass_per_thruster_on_reactor()
# to adjust the per-thruster mass when swapping reactor tiers.
DRIVE_REQ_POWER_GW_PER_THRUSTER: Dict[str, float] = {
    'LodestarFissionLantern': 186.7,
    'FirestarFissionLantern': 147.059,
    'NeutronFluxLantern':       0.0,   # self-powered
    'NeutronFluxTorch':         0.0,   # self-powered
    'PharosDrive':             13.35,
    'HeliconDrive':             4.0,    # back-solved from x6=24 GW
    'BurnerDrive':              4.3,
    'FissionSpinnerDrive':      0.0,    # placeholder; calibrate when needed
    'LarsDrive':                0.0,
    'TeardropDrive':            0.0,
}

# Backwards-compat shim: legacy code expects a flat per-thruster value.
# Returns the wet-mass calibration as-is (assumes the calibrated reactor tier).
def _legacy_per_thruster_mass(family: str) -> float:
    entry = DRIVE_MASS_PER_THRUSTER_T.get(family)
    if entry is None:
        return None
    if isinstance(entry, tuple):
        return entry[0]
    return entry


def mass_per_thruster_on_reactor(family: str, reactor_spec_power_tGW: float) -> float:
    """**LEGACY** — superseded by `mass_per_thruster_from_first_principles()` below.
    Kept for backward compat. Use the new function for accurate predictions.

    Lodestar on Gas Core V (3.5 t/GW) measures 1,820 t/thruster. On a different
    reactor tier the reactor-contribution scales by (delta_spec_power × req_GW
    per thruster). For self-powered drives (Poseidon), reactor doesn't matter.
    """
    entry = DRIVE_MASS_PER_THRUSTER_T.get(family)
    if entry is None:
        raise ValueError(f"Drive family {family!r} not calibrated.")
    base_t, calibrated_spec = entry if isinstance(entry, tuple) else (entry, None)
    if calibrated_spec is None or reactor_spec_power_tGW is None:
        return base_t   # self-powered drive, reactor doesn't apply
    req_GW = DRIVE_REQ_POWER_GW_PER_THRUSTER.get(family, 0)
    adjustment = (reactor_spec_power_tGW - calibrated_spec) * req_GW
    return base_t + adjustment


# Reactor efficiency by family/tier (from TIPowerPlantTemplate.json).
# Waste heat = req_power × (1 − efficiency). Drives radiator mass scaling.
REACTOR_EFFICIENCY: Dict[str, float] = {
    'GasCoreFissionReactorIII': 0.95,
    'GasCoreFissionReactorIV':  0.93,
    'GasCoreFissionReactorV':   0.95,
    'GasCoreFissionReactorVI':  0.96,
    # Add more as needed
}

# Radiator specific mass: tons per GW of waste heat that needs dissipation.
# Tin Droplet tooltip (Monitor-hull calibration design, 2032-03): 125 t per GW waste.
# Other radiators (Liquid Droplet, Heat Pump Vapor, etc.) will have different values.
RADIATOR_T_PER_GW_WASTE: Dict[str, float] = {
    'TinDroplet': 125.0,
    # Add more radiator types as identified
}

def mass_per_thruster_from_first_principles(
    family: str,
    reactor_spec_power_tGW: float,
    reactor_efficiency: float,
    radiator_t_per_gw_waste: float = 125.0,
) -> float:
    """Per-thruster mass = reactor share + radiator share + drive hardware.

    **WASTE-HEAT MODEL (clarified 2032-06 from in-game readings).** Drive thruster hardware itself
    is 0 t — all per-thruster mass is reactor + radiator. The radiated waste heat that
    sizes the radiator comes from REACTOR + DRIVE jointly:

        radiated_waste_GW = drive_req_power_GW × (1 − reactor_efficiency)

    The DRIVE sets the power demand (`req power` field — 746.8 GW for Lodestar x4, scales
    with thrusters); the REACTOR efficiency sets the waste fraction (4% for the 96%-eff
    GasCoreVI = "Terawatt Gas Core III" display name). 746.8 × 0.04 = 29.9 GW → radiator
    29.9 × 125 = 3,734 t, matching the in-game module tooltip (3.7K t). So:
        reactor_mass  = req_power × reactor_spec_power_tGW        (Terawatt GC III = 1 t/GW)
        radiator_mass = req_power × (1 − reactor_eff) × t_per_GW  (Tin Droplet = 125)
    NOTE the drive's OWN mechanical loss (`req power` − `thrustRating_GW` = 56 GW for x4)
    is carried out by the propellant EXHAUST, NOT radiated — confirmed because radiating
    it would need a ~10,000 t radiator vs the actual 3.7K t. So for fission-thermal drives
    only the reactor-inefficiency heat hits the radiator. Radiator t/GW = 1000/specificPower
    (Tin Droplet specificPower 8 kW/kg → 125 t/GW).

    **Verified 2032-03 against a Monitor-hull calibration design (4 controlled-variation
    drive-count readings) and an older battleship x1-x4 series**:

    For Lodestar Fission Lantern (req_power 186.7 GW/thruster, drive_hw ≈ 0):
    - On GC-VI (1 t/GW, 96% eff) + Tin Droplet: 186.7 + 186.7×0.04×125 = 1,120 t ✓
      (measured Monitor-series delta: 1,120 t exact)
    - On GC-V (3.5 t/GW, 95% eff) + Tin Droplet: 653 + 186.7×0.05×125 = 1,820 t ✓
      (battleship x1-x4 series: 1,820 t per thruster exact)

    Reactor refit from GC-V to GC-VI saves **~700 t per thruster** — much more than
    a reactor-only ~467 t estimate that missed the radiator term.

    **⚠️ BC over-prediction flagged 2032-06 (radiator hypothesis RETRACTED).** On the
    a reference battlecruiser (Terawatt Gas Core III = 1 t/GW, 96% eff) this function predicts
    1,120 t/thruster, but TWO controlled-variation readings (x3/60 = 22,476 t; x4/65 =
    24,096 t) pin the real marginal at **1,035 t/thruster** (other_mass 6,874 t identical
    across both). The decomposition checks out — each added Lodestar thruster on this reactor
    is Δreactor 187 t (186.7 GW × 1 t/GW) + Δradiator 933 t (7.47 GW waste × 125 Tin Droplet)
    = 1,120 t; **radiator is ~83% of the per-thruster mass** (it sizes to total waste heat,
    which scales with thruster count). The radiator IS Tin Droplet at 125 t/GW
    (confirmed from the in-game module tooltip — my earlier "lighter ~114 t/GW radiator" guess
    was WRONG). **The drive thruster hardware itself is 0 t (player-verified): ALL per-thruster mass is
    reactor + radiator.** The reactor term is EXACT — `required_power × spec_power`, this
    Terawatt GC III is 1 t/GW and reads 747 t for 746.8 GW (verified). So the residual **85 t
    gap is isolated to the RADIATOR term**: measured marginal radiator = 1,035 − 186.7 (reactor)
    = 848 t/thruster ⇒ 848/125 = 6.79 GW waste, i.e. effective ~3.64% waste (96.36% eff) vs the
    displayed 96.0% — the radiator sizes to slightly less waste heat than the rounded efficiency
    implies (or some reactor waste is handled by the heat sink, not the radiator). Small, not
    worth chasing on two readings: use the MEASURED 1,035 t for Lodestar-on-Terawatt-GC-III.
    An earlier x4 prediction used the LEGACY reactor-adjust (1,353 t) → 318 t too heavy;
    caught against the in-game 24,096 t.
    """
    req_GW = DRIVE_REQ_POWER_GW_PER_THRUSTER.get(family, 0)
    drive_hw = DRIVE_HARDWARE_T_PER_THRUSTER.get(family, 0)
    reactor_mass = req_GW * reactor_spec_power_tGW
    waste_GW = req_GW * (1 - reactor_efficiency)
    radiator_mass = waste_GW * radiator_t_per_gw_waste
    return drive_hw + reactor_mass + radiator_mass


# Pure drive hardware mass per thruster (NOT including reactor or radiator shares).
# Calibrated from data:
#   - Lodestar Fission Lantern: ~0 t (verified 2032-03 — all the per-thruster mass
#     comes from reactor + radiator scaling. Surprising but the math works.)
DRIVE_HARDWARE_T_PER_THRUSTER: Dict[str, float] = {
    'LodestarFissionLantern': 0.0,
    'PharosDrive': 0.0,  # Same pattern verified against a Monitor baseline
}

# **COMBAT G CAP IS BIOLOGICAL, NOT THERMAL** (2032-03 correction).
# Displayed combat g = min(peak_thrust / mass / g, BIOLOGICAL_G_CAP).
# The cap is human crew survivability — researchable upward. At the reference campaign's
# tech (2032-03), the cap is 3.5g. Heat sink modules (e.g. HeavyMoltenSaltHeatSink)
# DO NOT affect this cap. Their function is to store waste heat during combat for
# sustained-burst duration (the Heat Sink Capacity GJ stat) — not peak g.
# Verified across 4 Lodestar variants on a Monitor calibration design (no heat sink):
#   x1 peak 1.59g → displayed 1.6g (no cap)
#   x2 peak 2.95g → displayed 3.0g (no cap)
#   x3 peak 4.12g → displayed 3.5g (CAPPED)
#   x4 peak 5.14g → displayed 3.5g (CAPPED)
BIOLOGICAL_G_CAP_CURRENT_TECH = 4.0  # fallback ONLY — prefer bio_g_cap_from_save()

# The cap is 3.0 + 0.5 per completed raiser (max 5.0). **The project dataNames contain
# HYPHENS** — `Project_High-ThrustErgonomics`, `Project_High-GRecombinants`. Matching without
# the hyphen silently under-reports the cap (2033-10: read 3.5 g when the true cap was 4.0 g,
# because High-ThrustErgonomics was missed). Always derive from the save when you have one.
G_CAP_RAISER_PROJECTS = (
    'Project_High-ThrustErgonomics',
    'Project_AstronautFitnessRegimen',
    'Project_AccelerationPharmaceuticals',
    'Project_High-GRecombinants',
)


def bio_g_cap_from_save(finished_project_names) -> float:
    """Biological combat-g cap = 3.0 + 0.5 x completed raisers (cap 5.0)."""
    done = sum(1 for p in G_CAP_RAISER_PROJECTS if p in set(finished_project_names or ()))
    return min(3.0 + 0.5 * done, 5.0)


# Armor build cost: the in-game "Cost Per Ton" == weightedBuildMaterials x 0.1 (verified against
# the Hybrid Armor tooltip 2033-10: weights .38/.45/.165/.005 -> 0.038 vol / 0.045 met /
# 0.017 nob / 500u exotics per ton). Using the raw weights as per-ton costs over-states armor
# cost 10x and wrongly rules out exotics-bearing armor (Hybrid needs only ~0.5 exotics a ship).
ARMOR_COST_PER_TON_FACTOR = 0.1


def armor_cost(armor_mass_t: float, armor_name: str) -> dict:
    """Resource cost for a given armor mass (tons) -> {resource: units}."""
    w = armor_template(armor_name).get('weightedBuildMaterials') or {}
    return {k: v * ARMOR_COST_PER_TON_FACTOR * armor_mass_t for k, v in w.items()}

# Drive variant cruise thrust per single thruster (MN). Used by the variant
# sweep to compute x1..x6 stats without re-reading templates each time.
# Sourced from TIDriveTemplate.json x1 entries.
DRIVE_CRUISE_THRUST_MN_PER_THRUSTER: Dict[str, float] = {
    'LodestarFissionLantern': 11.0,
    'FirestarFissionLantern': 5.0,
    'NeutronFluxLantern': 12.9,            # Poseidon Lantern
    'NeutronFluxTorch': 13.0,              # Poseidon Torch (same NSWR family; EV 1700)
    'PharosDrive': 0.89,
    'HeliconDrive': 0.02,
    'BurnerDrive': 0.108,
    'FissionSpinnerDrive': 0.539,
    'LarsDrive': 0.099,
    'TeardropDrive': 0.333,
}

# Drive variant thrustCap (combat multiplier). Same across x1..x6 variants.
# **CAVEAT (2032-03)**: this is the NOMINAL thrustCap. **The ACHIEVED combat thrust
# is heat-sink-limited**:
#   - WITH a heat sink module (e.g. HeavyMoltenSaltHeatSink, 1800 GJ): full thrustCap.
#     Verified on battleship x3/x4/x5 readings — combat g matched (cruise × 20) / mass.
#   - WITHOUT a heat sink module (e.g. Monitor patrol boat — only 3 utility slots,
#     no room for one): effective thrustCap drops to roughly **~half** of nominal.
#     *** RETRACTED (LESSONS-ships S11) — the heat-sink thrustCap multiplier is a DEAD
#     THEORY: heat sinks set sustained-burst endurance (GJ), NOT peak g. Kept only as a
#     tombstone; do not resurrect. Use the biological cap above. ***
#     Back-solved from a Monitor reading (Lodestar x2, no heat sink):
#     cruise 22 MN at wet 7,025 t → combat 3.5g (241 MN) → effective cap ≈ 10.95,
#     i.e. **0.55 × nominal 20**.
# To predict combat g realistically on a heat-sink-less hull, multiply the nominal
# thrustCap below by `effective_thrustcap_multiplier(has_heatsink_module)` from
# the helper at the bottom of this module.
DRIVE_THRUST_CAP: Dict[str, int] = {
    'LodestarFissionLantern': 20,
    'FirestarFissionLantern': 22,
    'NeutronFluxLantern': 2,
    'NeutronFluxTorch': 2,                 # transit drive — NOT a warship cap
    'PharosDrive': 16,
    'HeliconDrive': 20,
    'BurnerDrive': 24,
    'FissionSpinnerDrive': 14,
    'LarsDrive': 15,
    'TeardropDrive': 15,
}

# Drive EV (km/s) — same across x1..x6 within a family.
DRIVE_EV_KPS: Dict[str, float] = {
    'LodestarFissionLantern': 31.4,
    'FirestarFissionLantern': 50.0,
    'NeutronFluxLantern': 66.0,
    'NeutronFluxTorch': 1700.0,
    'PharosDrive': 25.5,
    'HeliconDrive': 314.0,
    'BurnerDrive': 69.0,
    'FissionSpinnerDrive': 17.7,
    'LarsDrive': 19.6,
    'TeardropDrive': 19.6,
}

# Hull armor geometry coefficients (m³ per thickness point per section).
# Back-solved from shipbuilder readings:
#     coef = mass_per_point_t * 1000 / armor_density_kgm3
# Add new entries by calibrating one (armor, nose/body/tail mass) reading.
HULL_ARMOR_COEFFICIENTS: Dict[str, Dict[str, float]] = {
    'Lancer': {
        'nose':    64.42,    # 110.8 t/pt @ Nanotube 1720 kg/m³
        'tail':    64.42,
        'lateral': 1_484.30,  # 2553 t/pt @ Nanotube 1720 kg/m³
    },
    'Battleship': {
        # Verified against the calibration-BC x1 baseline (2026-05-31): with Adamantane
        # N91/B5/T10, model predicts armor 15,480 t which gives dry mass
        # 21,168 t — matches measured ΔV 9.0 kps exactly (within 1 t).
        'nose':    39.31,    # 25² × 0.0629
        'tail':    39.31,
        'lateral': 926.6,    # π × 25 × 200 × 0.0590
    },
    # Monitor verified 2032-03 against the in-game Nanotube Armor module tooltip:
    # tooltip displayed nose/tail 43.1 t/pt, lateral 799.1 t/pt,
    # thickness 7.86 cm per point. The W² formula predicted 43.3/797 — off by 0.5%
    # because thickness/pt is the same across sections (NOT 0.0629 nose vs 0.0590
    # lateral as first assumed). True formula: `coef = area_m² × 0.0786 m` for both
    # sections; asymmetry comes from area only.
    # Max armor caps on Monitor (from tooltip): nose 57, lateral 30, tail 57.
    'Monitor': {
        'nose':    25.06,    # 43.1 / 1.72 (Nanotube density / 1000)
        'tail':    25.06,
        'lateral': 464.6,    # 799.1 / 1.72
    },
    # Battlecruiser verified 2032-06 against the in-game Nanotube Armor module
    # tooltip (player screenshot): nose/tail 42.5 t/pt, lateral 1,119 t/pt,
    # thickness 7.86 cm/pt, max nose/tail 80, max lateral 30. Coefs = t/pt / 1.72
    # (Nanotube density). Note the BC has a SMALLER nose/tail per-point than the
    # Monitor (42.5 vs 43.1) but a much larger lateral (1,119 vs 799) — it's a
    # longer, slenderer hull: small end-caps, big cylinder side area. Lateral
    # armor is very expensive here (650 t/pt model), so siege loadouts should pour
    # into nose (cheap at 24.71 t/pt, cap 80) and keep lateral minimal.
    'Battlecruiser': {
        'nose':    24.71,    # 42.5 / 1.72
        'tail':    24.71,
        'lateral': 650.58,   # 1119 / 1.72
    },
    # Dreadnought verified against the in-game Nanotube Armor module
    # tooltip on the calibration dreadnought: nose/tail 134.7 t/pt, lateral 3,072 t/pt,
    # thickness 7.86 cm/pt, max nose/tail 126, max lateral 53. Coefs = t/pt × 1000
    # / 1720 (Nanotube density). Cross-checked: the 126→120 nose + 5→4 lateral
    # trim dropped wet mass 57,847→53,634 t (−4,213 ≈ 6×134.7 + 1×3,072 = −3,880,
    # rest tanks), and full N120/B4/T10 reproduces armor mass 29,799 t exactly.
    'Dreadnought': {
        'nose':    78.31,    # 134.7 / 1.72
        'tail':    78.31,
        'lateral': 1786.05,  # 3072 / 1.72
    },
}

# Fallback for hulls without explicit calibration: derive from hull dimensions.
# **CORRECTED 2032-03**: the in-game Nanotube Armor module tooltip on a
# Monitor reads "Thickness per point: 7.86 cm" as a SINGLE value (no nose/lateral
# distinction). So the formula is:
#     nose_coef    = width²              × 0.0786   (end-cap area × thickness/pt)
#     tail_coef    = width²              × 0.0786
#     lateral_coef = π × width × length  × 0.0786   (cylinder side area × thickness/pt)
# Previous back-solved values (0.0629 nose, 0.0590 lateral) were artifacts of fitting
# Lancer measurements where end-cap and cylinder approximations introduced small
# offsets. The unified 0.0786 m thickness matches the in-game tooltip exactly.
# **BUT**: don't use the formula when you have explicit `HULL_ARMOR_COEFFICIENTS`
# (Monitor / Battleship / Lancer entries above) — those are the canonical values.
# **BEST source**: read the in-game armor module tooltip directly — it shows
# `Mass per nose or tail armor point` and `Mass per lateral armor point` for any
# (hull × armor material) combination. Ask the user to share the tooltip screenshot
# for any new hull you're calibrating.
DEFAULT_NOSE_THICKNESS_M    = 0.0786   # nose/tail (end-cap area × this)
DEFAULT_LATERAL_THICKNESS_M = 0.0786   # lateral (cylinder side area × this)

# ---- Material thickness per armor POINT (added 2033-10-25) --------------------
# CRITICAL: an armor "point" is NOT a fixed thickness across materials. Every
# HULL_ARMOR_COEFFICIENTS entry above was back-solved from a **Nanotube** tooltip
# (7.86 cm/pt), so using it with any other material overstated that material's
# mass per point — and hid the fact that denser-resisting materials buy far MORE
# points for the same hull.
#
#     thickness_cm_per_point = xRayHalfValue_cm / XRayResistance
#
# (i.e. "cm to halve X-ray" ÷ "points to halve X-ray"). Validated three ways:
#   * Nanotube: 19.9 / 2.53 = 7.866 cm/pt — matches the in-game tooltip's 7.86 exactly.
#   * The player's 2033-10-25 Lancer designer screenshot on Adamantane reads max
#     nose/tail **241** vs the Nanotube tooltip cap of 114 → ratio 2.114, and
#     7.866 / (18 / 4.82) = 2.106. Caps are a fixed max THICKNESS per hull.
#   * Same design's wet mass 45,300 t reconciles (Poseidon Torch x6 = 78 MN cruise
#     → 175.6 mg at 45,300 t; ΔV 424 kps @ EV 1700 → 9,993 t propellant = 100 tanks).
NANOTUBE_CM_PER_POINT = 7.866   # the calibration material for every coefficient above


def armor_cm_per_point(armor: str) -> float:
    """Thickness (cm) of one armor point for this material — see note above."""
    t = armor_template(armor)
    xray = next((s['value'] for s in t.get('specialties', [])
                 if s.get('armorSpecialty') == 'XRayResistance'), None)
    if not xray:
        return NANOTUBE_CM_PER_POINT
    return t['xRayHalfValue_cm'] / xray


def armor_point_thickness_factor(armor: str) -> float:
    """Volume-per-point scale vs the Nanotube-calibrated hull coefficients."""
    return armor_cm_per_point(armor) / NANOTUBE_CM_PER_POINT


def armor_max_points(hull_nanotube_cap: float, armor: str) -> float:
    """A hull's max armor points for `armor`, from its Nanotube cap (fixed max cm)."""
    return hull_nanotube_cap / armor_point_thickness_factor(armor)

# Per-hull turn-rate constant: turn_rate (deg/s) = K / m_wet.
# K depends on hull length (moment of inertia) and rotational thruster torque.
# Currently calibrated for Lancer with Vector Thrusters installed.
HULL_K_TURN_WITH_VT: Dict[str, float] = {
    'Lancer': 11_139.0,
    # Calibration Dreadnought (with Vector Thrusters): turn 0.19 deg/s
    # @ 53,634 t wet → K = 10,190.
    'Dreadnought': 10_190.0,
}
HULL_K_TURN_NO_VT: Dict[str, float] = {
    'Lancer': 8_073.0,
    # Bare-hull calibration (no modules, no VT): turn 2.2 deg/s @ 2,880 t → K = 6,336.
    'Dreadnought': 6_336.0,
}

# Propellant tank mass — per-tank in tons, all propellants.
DEFAULT_PROP_PER_TANK_T = 100.0  # AUTHORITATIVE — decompiled code.
# **FLIP-FLOP FINALLY CLOSED 2032-06 with decompiled-code evidence: tank = 100 t.**
# `spaceResourceToTons = 0.1`, 1 propellant tank = 10 resource units = 100 t
# (`[code][tpl]`, Mechanics/Drives reference). The earlier "117 t" reading was WRONG — a
# compensating-error artifact: it assumed ΔV uses the template EV (31.4 kps),
# back-solved 117 t/tank to make ΔV fit, and that ALSO happened to reproduce the
# wet-mass deltas. With the TRUE 100 t tank, the wet-mass model closes with ZERO
# residual on both reference-BC readings (x3/60 → FIXED 13,115 t; x4/65 → FIXED 13,116 t)
# AND the radiator comes out to the clean full 4% reactor waste (the recurring
# "85 t residual" was entirely this tank-mass error). See PROP_DELTAV_EV_FACTOR for
# why ΔV needs an effective EV above the template value.
PROP_PER_TANK_BY_PROPELLANT = {}   # tank = 100 t regardless of propellant (decompiled)

# ΔV exhaust velocity — code-verified 2032-06 against build 1.0.32. The ΔV formula is:
#   currentMaxDeltaV_kps = currentEV_kps × Mathf.Log(wetMass_tons / dryMass_tons)
#     (`TISpaceShipState` mass-update method)
# and currentEV / modifiedEV is NOT the raw template EV — it's:
#   modifiedEV_kps = drive.EV_kps × ∏(utility module EVMultiplier)
#     (`TISpaceShipTemplate::get_modifiedEV_kps` — loops utility modules, multiplies
#      by each module's get_EVMultiplier(), then × drive EV_kps)
# The ONLY EVMultiplier utility module is **Liquid Hydrogen Containment**:
#   `TIUtilityModuleTemplate.LiquidHydrogenContainment.specialModuleValue = 1.2`
#   (specialRule = EVMultiplier). So LHC multiplies effective EV by 1.2.
# THIS is the "1.2 factor" — it's the LHC module, NOT a drive property. A design WITHOUT
# LHC has modifiedEV = template EV (factor 1.0) and ~17% less ΔV. The LHC-equipped reference designs
# all carry LHC, which is why they all showed ~1.2. The empirical 1.2 from
# the tank-only sweep == LHC's specialModuleValue exactly.
EV_MULTIPLIER_MODULES = {
    'LiquidHydrogenContainment': 1.2,   # specialModuleValue, decompiled
    # add other EVMultiplier modules here if any are found
}

# Per-hull "OTHER" mass = hull base + reactor module + weapons + utility modules + tank_hw.
# Use as a calibrated starting point for `Warship(other_mass_t=...)` when designing a refit
# from a known reading; the alternative is to .calibrate() against a measured wet mass.
# Keyed by (hull, drive_family, armor_material, role_loadout). All values back-solved from
# in-game shipbuilder screenshots, not theoretical.
HULL_OTHER_MASS_T: Dict[Tuple[str, str, str], float] = {
    # A battleship calibration reading (2032-03): Lodestar x3 GC-V, Nanotube, 50 tanks,
    # N91/B5/T10, Defender modules (TargetingComputer2 + ECM2 + HeavyMoltenSaltHeatSink
    # + SalvageBay + VectorThrusters + LiquidHydrogenContainment). Wet 31,948 t,
    # ΔV 6.4 kps measured; cross-verified at x4 within 1 t.
    # **NEEDS RECALIBRATION** with prop_per_tank=100 (was using 117.8) — when next
    # battleship screenshot comes in, re-derive this constant.
    ('Battleship', 'LodestarFissionLantern', 'NanotubeArmor'): 3_707,

    # Monitor calibration series (2032-03): Lodestar x2 + GC-VI, Nanotube, three armor configs
    # measured (N18/B1/T1, N57/B1/T3, N57/B1/T7) all with 18 tanks. All three
    # match exactly (within 1 t) when OTHER=720 and prop_per_tank=100. So
    # Monitor + Lodestar + Nanotube + TinDroplet OTHER = 720 t.
    # CRITICAL: This is DIFFERENT from Monitor + Pharos (which gave OTHER=720
    # too once re-derived correctly). The earlier value of 847 was wrong because
    # it was derived with prop_per_tank=99.6, which was off; the 100-t tooltip
    # value gives 720 t exact.
    ('Monitor', 'LodestarFissionLantern', 'NanotubeArmor'): 720,
    ('Monitor', 'PharosDrive', 'NanotubeArmor'): 720,

    # Reference siege Dreadnought: Lodestar x6 on Gas Core VI, Nanotube
    # N120/B4/T10, 126 tanks, full siege loadout (8 hull weapons + nose Heavy
    # Particle Lance + HeavyMoltenSaltHeatSink 1800 GJ + targeting/ECM/VT/radiators).
    # Back-solved against measured wet 53,634 t (reproduces 2.5 g combat, 8 kps ΔV,
    # 0.19 deg/s turn). NOTE: this other_mass is small (3,116 t) because the legacy
    # Lodestar drive-mass formula over-attributes mass on a 6-thruster hull and the
    # calibration absorbs the difference here — it predicts armor/tank trades on this
    # design accurately, but re-derive if you change the drive thruster count.
    ('Dreadnought', 'LodestarFissionLantern', 'NanotubeArmor'): 3_116,
}

# **COMBAT THRUST: SUSTAINABLE-CAP MODEL** (2032-03 discovery).
# The displayed in-game `combat acceleration` is NOT just `peak_thrust / mass / g`.
# It's clipped by a sustainable cap that depends on heat dissipation:
#     displayed_combat_g = min(peak_thrust_g, sustainable_cap_g)
# where peak_thrust_g uses nominal cap (Lodestar 20, Pharos 16, etc.) and
# sustainable_cap_g depends on (drive group, heat sink, radiator).
#
# Calibrations from measurements:
#   - WITH HeavyMoltenSaltHeatSink (battleship x3/x4/x5 series):
#     sustainable_cap_g >> peak across design range → display = peak (always).
#     Effective cap = full nominal (Lodestar 20).
#   - WITHOUT heat sink (Monitor, Lodestar x2 + TinDroplet radiator):
#     sustainable_cap_g = 3.5g. Displayed value clamped to 3.5g until wet mass
#     exceeds the cross-over (~12,830 t for Lodestar x2 with cap=20).
#     Above cross-over, displayed reverts to peak-thrust-limited.
#
# Cross-over mass formula:
#     cross_over_t = nominal_combat_thrust_MN × 1000 / (sustainable_cap_g × g)
#     For Lodestar x2 (nominal combat 440 MN) at sus_cap=3.5g:
#     cross_over = 440 × 1000 / (3.5 × 9.81) = 12,830 t
# Implication for design: below the cross-over, ARMOR AND TANKS ARE FREE — they
# don't reduce displayed combat g. Above the cross-over, standard F/m kicks in.
SUSTAINABLE_COMBAT_CAP_G: Dict[Tuple[str, str, bool], float] = {
    # (hull, drive_family, has_heatsink) → sustainable cap in g.
    # `None` means "use peak directly" (heat-sink-equipped, no cap).
    ('Monitor',    'LodestarFissionLantern', False): 3.5,
    ('Battleship', 'LodestarFissionLantern', True):  None,  # cap=full nominal
    # Add more rows as measurements come in. The sustainable cap probably
    # depends on drive count too — needs x1/x3/x4 readings on Monitor to
    # parameterize how it scales.
}

G = 9.81  # m/s² standard gravity

# Heat-sink-aware combat thrust correction.
# Empirically observed: without a heat sink module, achievable combat thrust is
# ~0.55 × nominal (Lodestar's 20 thrustCap → effective 11 on Monitor without
# heat sink). Heat sink modules known to enable full thrustCap include
# HeavyMoltenSaltHeatSink (1800 GJ on Battleship). Smaller heat sinks likely
# scale proportionally; this is a coarse model until more calibration data lands.
EFFECTIVE_THRUSTCAP_NO_HEATSINK = 0.55  # multiplier vs nominal
EFFECTIVE_THRUSTCAP_WITH_HEATSINK = 1.0  # full nominal
HEATSINK_MODULES = {
    'HeavyMoltenSaltHeatSink',
    'MoltenSaltHeatSink',  # if T2 exists
    # Add more heat-sink module dataNames as they're identified.
}

def effective_thrustcap_multiplier(modules) -> float:
    """Return the thrustCap multiplier given a list of utility module dataNames.
    `modules` can be any iterable of module template names installed on the ship.
    """
    if any(m in HEATSINK_MODULES for m in (modules or [])):
        return EFFECTIVE_THRUSTCAP_WITH_HEATSINK
    return EFFECTIVE_THRUSTCAP_NO_HEATSINK


# ============================================================
# Helpers
# ============================================================

def _drive_family(drive_name: str) -> str:
    """`LodestarFissionLanternx3` → `LodestarFissionLantern`."""
    m = re.match(r'(.+?)x\d+$', drive_name)
    return m.group(1) if m else drive_name


def _drive_thruster_count(drive_name: str) -> int:
    m = re.search(r'x(\d+)$', drive_name)
    return int(m.group(1)) if m else 1


# ============================================================
# Warship — configuration + physics
# ============================================================

@dataclass
class Warship:
    """A configurable Terra Invicta warship.

    All values are read from game templates except `other_mass_t` (which
    represents hull + reactor + weapons + non-armor utilities) and a few
    calibration constants. Call `.calibrate(measured_wet_t=...)` after
    construction to back-solve `other_mass_t` from a real shipbuilder reading.
    """
    hull: str
    drive: str
    armor: str
    tanks: int = 0
    nose: int = 0
    body: int = 0
    tail: int = 0
    with_vt: bool = True
    prop_per_tank_t: float = DEFAULT_PROP_PER_TANK_T
    # Effective-EV multiplier from installed EVMultiplier utility modules (decompiled:
    # modifiedEV = drive.EV_kps × ∏ module EVMultiplier). Liquid Hydrogen Containment = 1.2.
    # Set to 1.2 if the design carries LHC; 1.0 otherwise. Default 1.0 (no LHC).
    ev_multiplier: float = 1.0
    other_mass_t: Optional[float] = None  # set via .calibrate()
    # Reactor's specificPower_tGW — Gas Core III=3, IV=10, V=3.5, VI=1.
    # Defaults to the per-thruster calibration reactor (no adjustment).
    # Set explicitly to predict mass on a different reactor tier.
    reactor_spec_power_tGW: Optional[float] = None

    # --- template lookups ---
    def hull_data(self) -> Dict[str, Any]:
        return hull_template(self.hull)

    def drive_data(self) -> Dict[str, Any]:
        return drive_template(self.drive)

    def armor_data(self) -> Dict[str, Any]:
        return armor_template(self.armor)

    def armor_density_kgm3(self) -> float:
        return self.armor_data()['density_kgm3']

    # --- armor geometry & mass ---
    def armor_coefficients(self) -> Dict[str, float]:
        """Returns m³ per armor point for nose / tail / lateral, for THIS material.

        Hull coefficients are Nanotube-calibrated; scale them by the material's
        cm-per-point (see `armor_point_thickness_factor`) or non-Nanotube designs
        come out ~2× too heavy per point.
        """
        f = armor_point_thickness_factor(self.armor)
        if self.hull in HULL_ARMOR_COEFFICIENTS:
            base = HULL_ARMOR_COEFFICIENTS[self.hull]
        else:
            # Fallback: derive from hull dimensions
            hd = self.hull_data()
            L = hd.get('length_m', 0)
            W = hd.get('width_m', 0)
            if not (L and W):
                raise ValueError(
                    f"Hull {self.hull!r} has no calibrated armor coefficients "
                    f"and no length/width in template. Add an entry to "
                    f"HULL_ARMOR_COEFFICIENTS after taking a shipbuilder reading.")
            base = {
                'nose':    W * W * DEFAULT_NOSE_THICKNESS_M,
                'tail':    W * W * DEFAULT_NOSE_THICKNESS_M,
                'lateral': math.pi * W * L * DEFAULT_LATERAL_THICKNESS_M,
            }
        return {k: v * f for k, v in base.items()}

    def armor_mass_t(self) -> float:
        c = self.armor_coefficients()
        d = self.armor_density_kgm3()
        volume_m3 = (self.nose * c['nose']
                     + self.body * c['lateral']
                     + self.tail * c['tail'])
        return volume_m3 * d / 1000   # kg → tons

    # --- drive mass ---
    def drive_mass_t(self) -> float:
        family = _drive_family(self.drive)
        n_thr = _drive_thruster_count(self.drive)
        if family not in DRIVE_MASS_PER_THRUSTER_T:
            raise ValueError(
                f"Drive family {family!r} not calibrated. Add a (mass, reactor_spec) "
                f"tuple to DRIVE_MASS_PER_THRUSTER_T, or back-solve from two "
                f"shipbuilder readings differing only in drive thruster count.")
        if self.reactor_spec_power_tGW is None:
            # Use the calibration reactor's value (no adjustment)
            per_thruster = _legacy_per_thruster_mass(family)
        else:
            per_thruster = mass_per_thruster_on_reactor(family, self.reactor_spec_power_tGW)
        return per_thruster * n_thr

    # --- propellant ---
    def propellant_mass_t(self) -> float:
        return self.tanks * self.effective_prop_per_tank_t()

    def effective_prop_per_tank_t(self) -> float:
        """Per-tank propellant mass. If the caller left prop_per_tank_t at the
        generic default, resolve it from the drive's propellant type via
        PROP_PER_TANK_BY_PROPELLANT (currently empty: 100 t/tank is
        code-authoritative for all propellants; the old 117 t hydrogen reading
        was a compensating error — the real effect is the LHC ×1.2 EV
        multiplier). An explicit non-default value always wins."""
        if self.prop_per_tank_t != DEFAULT_PROP_PER_TANK_T:
            return self.prop_per_tank_t
        propellant = self.drive_data().get('propellant')
        return PROP_PER_TANK_BY_PROPELLANT.get(propellant, DEFAULT_PROP_PER_TANK_T)

    # --- mass aggregates ---
    def dry_mass_t(self) -> float:
        """Everything except propellant. Requires .calibrate() first
        for accurate results; falls back to hull mass alone otherwise."""
        if self.other_mass_t is None:
            # Crude fallback: just hull base + drive + armor
            other = self.hull_data().get('mass_tons', 0)
        else:
            other = self.other_mass_t
        return other + self.drive_mass_t() + self.armor_mass_t()

    def wet_mass_t(self) -> float:
        return self.dry_mass_t() + self.propellant_mass_t()

    # --- calibration ---
    def calibrate(self, measured_wet_t: float) -> None:
        """Back-solve `other_mass_t` so wet_mass matches the shipbuilder reading.

        After this, `other_mass_t` = hull + reactor + weapons + non-armor
        utilities, and subsequent variations (different armor, tanks, etc.)
        will be predicted accurately as long as the rest of the loadout
        (weapons, utilities) stays the same.
        """
        residual = (measured_wet_t
                    - self.drive_mass_t()
                    - self.armor_mass_t()
                    - self.propellant_mass_t())
        self.other_mass_t = residual

    # --- physics ---
    def delta_v_kps(self) -> float:
        wet, dry = self.wet_mass_t(), self.dry_mass_t()
        if wet <= dry:
            return 0.0
        # Decompiled: maxDeltaV = modifiedEV × Log(wet/dry), where
        # modifiedEV = drive.EV_kps × ∏(utility-module EVMultiplier). The only
        # EVMultiplier module is Liquid Hydrogen Containment (×1.2). Set
        # self.ev_multiplier = 1.2 when LHC is installed (default 1.0).
        ev = self.drive_data().get('EV_kps', 0) * self.ev_multiplier
        return ev * math.log(wet / dry)

    def combat_thrust_n(self) -> float:
        dd = self.drive_data()
        return dd.get('thrust_N', 0) * dd.get('thrustCap', 1)

    def combat_accel_g(self) -> float:
        return (self.combat_thrust_n() / (self.wet_mass_t() * 1000)) / G

    def turn_rate_dps(self) -> float:
        table = HULL_K_TURN_WITH_VT if self.with_vt else HULL_K_TURN_NO_VT
        k = table.get(self.hull)
        if k is None:
            raise ValueError(
                f"Hull {self.hull!r} has no calibrated turn-rate constant. "
                f"Add to HULL_K_TURN_WITH_VT after recording shipbuilder turn rate.")
        return k / self.wet_mass_t()

    def metrics(self) -> Dict[str, float]:
        return {
            'dv_kps':       self.delta_v_kps(),
            'accel_g':      self.combat_accel_g(),
            'turn_dps':     self.turn_rate_dps(),
            'wet_t':        self.wet_mass_t(),
            'dry_t':        self.dry_mass_t(),
            'armor_t':      self.armor_mass_t(),
            'propellant_t': self.propellant_mass_t(),
            'drive_t':      self.drive_mass_t(),
            'other_t':      self.other_mass_t or 0.0,
        }

    def __repr__(self) -> str:
        try:
            m = self.metrics()
            return (f"Warship({self.hull}, {self.drive}, {self.armor}, "
                    f"tanks={self.tanks}, nose={self.nose}, body={self.body}, "
                    f"tail={self.tail}) → ΔV {m['dv_kps']:.2f} kps, "
                    f"{m['accel_g']:.2f} g, {m['turn_dps']:.3f} deg/s, "
                    f"{m['wet_t']:,.0f} t wet, {m['armor_t']:,.0f} t armor")
        except Exception as ex:
            return (f"Warship({self.hull}, {self.drive}, {self.armor}, "
                    f"tanks={self.tanks}, nose={self.nose}, body={self.body}, "
                    f"tail={self.tail}) [uncalibrated: {ex.__class__.__name__}]")


# ============================================================
# Optimizer
# ============================================================

def optimize_armor(ship: Warship,
                   min_dv_kps: float = 4.0,
                   min_combat_g: float = 2.0,
                   min_turn_dps: float = 0.30,
                   body_range: Tuple[int, int] = (1, 3),
                   tail_range: Tuple[int, int] = (1, 3),
                   nose_max: int = 200,
                   ) -> List[Tuple[int, int, int, float, float, float, float, float]]:
    """Maximize nose armor under constraints. Holds drives, tanks fixed.

    Returns: list of (nose, body, tail, dv, accel_g, turn, wet_t, armor_t),
    sorted by nose thickness descending.
    """
    if ship.other_mass_t is None:
        raise ValueError("Calibrate ship first: ship.calibrate(measured_wet_t=...)")
    orig = (ship.nose, ship.body, ship.tail)
    results = []
    try:
        for body in range(body_range[0], body_range[1] + 1):
            for tail in range(tail_range[0], tail_range[1] + 1):
                # Binary search for max feasible nose
                lo, hi = 0, nose_max
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    ship.nose, ship.body, ship.tail = mid, body, tail
                    if (ship.delta_v_kps() >= min_dv_kps
                            and ship.combat_accel_g() >= min_combat_g
                            and ship.turn_rate_dps() >= min_turn_dps):
                        lo = mid
                    else:
                        hi = mid - 1
                if lo > 0:
                    ship.nose, ship.body, ship.tail = lo, body, tail
                    results.append((lo, body, tail,
                                    ship.delta_v_kps(),
                                    ship.combat_accel_g(),
                                    ship.turn_rate_dps(),
                                    ship.wet_mass_t(),
                                    ship.armor_mass_t()))
    finally:
        ship.nose, ship.body, ship.tail = orig
    results.sort(key=lambda r: -r[0])
    return results


def compare(*ships: Warship) -> None:
    """Pretty-print metrics across several configurations."""
    print(f'{"config":54s} {"ΔV":>6s} {"accel":>6s} {"turn":>6s} {"wet":>9s} {"armor":>9s}')
    print('-' * 96)
    for s in ships:
        m = s.metrics()
        label = (f"{s.hull}/{s.drive[-8:]}/{s.armor[:8]} "
                 f"tk={s.tanks} N{s.nose}/B{s.body}/T{s.tail}")[:54]
        print(f'{label:54s} {m["dv_kps"]:>5.2f}  {m["accel_g"]:>5.2f}g '
              f'{m["turn_dps"]:>5.3f}  {m["wet_t"]:>7,.0f}t {m["armor_t"]:>7,.0f}t')


def variant_sweep(ship: Warship,
                  drive_family: Optional[str] = None,
                  variants: List[int] = None) -> List[Dict[str, Any]]:
    """Sweep drive-variant choice (x1..x6) holding all other ship config constant.

    Holds hull / armor / tanks / utilities fixed. Substitutes the drive variant
    name (e.g. `LodestarFissionLanternx1`..`x6`) and recomputes ΔV, combat
    accel, turn rate, wet mass for each. The 'other_mass_t' calibration must
    already be set (call .calibrate() on the baseline first).

    Returns: list of dicts, one per variant, with keys:
      n_thrusters, drive_name, cruise_MN, combat_MN, ev_kps, accel_g,
      turn_dps, dv_kps, wet_t, drive_mass_t
    """
    if ship.other_mass_t is None:
        raise ValueError("Calibrate baseline ship first: ship.calibrate(measured_wet_t=...)")
    if variants is None:
        variants = [1, 2, 3, 4, 5, 6]
    # Resolve drive family
    if drive_family is None:
        drive_family = _drive_family(ship.drive)
    if drive_family not in DRIVE_MASS_PER_THRUSTER_T:
        raise ValueError(
            f"Drive family {drive_family!r} has no per-thruster mass calibration. "
            f"Known: {sorted(DRIVE_MASS_PER_THRUSTER_T)}")

    # The current ship's drive count is what 'other_mass_t' was calibrated against.
    # When swapping the drive variant, the drive_mass component changes; other_mass
    # is the constant non-drive non-armor non-propellant base.
    original_drive = ship.drive
    results = []
    try:
        for n in variants:
            ship.drive = f"{drive_family}x{n}"
            turn_dps = None
            try:
                turn_dps = ship.turn_rate_dps()
            except ValueError:
                pass
            cruise_mn = DRIVE_CRUISE_THRUST_MN_PER_THRUSTER[drive_family] * n
            cap = DRIVE_THRUST_CAP[drive_family]
            results.append({
                'n_thrusters': n,
                'drive_name': ship.drive,
                'cruise_MN':  cruise_mn,
                'combat_MN':  cruise_mn * cap,
                'ev_kps':     DRIVE_EV_KPS[drive_family],
                'accel_g':    ship.combat_accel_g(),
                'turn_dps':   turn_dps,
                'dv_kps':     ship.delta_v_kps(),
                'wet_t':      ship.wet_mass_t(),
                'drive_mass_t': ship.drive_mass_t() if hasattr(ship, 'drive_mass_t') else 0,
            })
    finally:
        ship.drive = original_drive
    return results


def print_variant_sweep(ship: Warship, drive_family: Optional[str] = None) -> None:
    """Print a formatted x1..x6 variant comparison table for the given ship."""
    if drive_family is None:
        drive_family = _drive_family(ship.drive)
    rows = variant_sweep(ship, drive_family=drive_family)
    print(f"\nVariant sweep — {drive_family} on {ship.hull} "
          f"(armor: N{ship.nose}/B{ship.body}/T{ship.tail}, {ship.tanks} tanks)")
    print(f"  {'Variant':>8s}  {'Cruise MN':>10s}  {'Combat MN':>10s}  {'EV':>5s}  "
          f"{'ΔV':>5s}  {'Accel':>7s}  {'Turn':>6s}  {'Wet t':>7s}")
    print('  ' + '-' * 80)
    for r in rows:
        turn_txt = f"{r['turn_dps']:.3f}" if r['turn_dps'] is not None else 'n/a'
        print(f"  {('x'+str(r['n_thrusters'])):>8s}  "
              f"{r['cruise_MN']:>9.1f}   {r['combat_MN']:>9.1f}  {r['ev_kps']:>5.1f}  "
              f"{r['dv_kps']:>5.2f}  {r['accel_g']:>5.2f}g  "
              f"{turn_txt:>5s}  "
              f"{r['wet_t']:>7,.0f}")


# ============================================================
# Demo / CLI
# ============================================================

def _demo_baseline() -> None:
    """Reproduce the original baseline-design analysis with the new general code."""
    print("=== Calibration check: reference-campaign measured baseline design ===")
    ship = Warship(
        hull='Lancer',
        drive='LodestarFissionLanternx3',
        armor='NanotubeArmor',
        tanks=40,
        nose=40, body=2, tail=6,
    )
    ship.calibrate(measured_wet_t=29_313)
    print(f"  Measured: ΔV 5.51, accel 2.30 g, turn 0.380 deg/s, wet 29,313 t")
    m = ship.metrics()
    print(f"  Computed: ΔV {m['dv_kps']:.2f}, accel {m['accel_g']:.2f} g, "
          f"turn {m['turn_dps']:.3f} deg/s, wet {m['wet_t']:,.0f} t")
    print(f"  → calibrated other_mass_t = {ship.other_mass_t:,.0f} t "
          f"(hull + reactor + weapons + non-armor utility)")

    print("\n=== Variations on the baseline (same loadout, different armor allocation) ===")
    current = Warship(hull='Lancer', drive='LodestarFissionLanternx3',
                      armor='NanotubeArmor', tanks=40, nose=40, body=2, tail=6,
                      other_mass_t=ship.other_mass_t)
    conservative = Warship(hull='Lancer', drive='LodestarFissionLanternx3',
                           armor='NanotubeArmor', tanks=40, nose=70, body=2, tail=1,
                           other_mass_t=ship.other_mass_t)
    aggressive = Warship(hull='Lancer', drive='LodestarFissionLanternx3',
                         armor='NanotubeArmor', tanks=40, nose=85, body=2, tail=1,
                         other_mass_t=ship.other_mass_t)
    compare(current, conservative, aggressive)

    print("\n=== Optimizer: max nose given 2.0 g / 4.0 kps / 0.30 deg/s ===")
    results = optimize_armor(ship, min_dv_kps=4.0, min_combat_g=2.0, min_turn_dps=0.30)
    print(f"  {'body':>4} {'tail':>4} {'max nose':>9}  {'armor':>9}  ΔV    accel  turn")
    seen_body = set()
    for r in results:
        nose, body, tail, dv, gs, turn, wet, arm = r
        if body in seen_body: continue
        seen_body.add(body)
        print(f"  {body:>4} {tail:>4} {nose:>9}  {arm:>7,.0f}t  "
              f"{dv:.2f}  {gs:.2f}  {turn:.3f}")

    print("\n=== Armor material comparison (same loadout, swap material) ===")
    materials = ['FoamedMetalArmor', 'NanotubeArmor', 'AdamantaneArmor', 'HybridArmor']
    variants = []
    for mat in materials:
        v = Warship(hull='Lancer', drive='LodestarFissionLanternx3',
                    armor=mat, tanks=40, nose=70, body=2, tail=1,
                    other_mass_t=ship.other_mass_t)
        variants.append(v)
    compare(*variants)

    # Drive-variant sweep — explicitly show all 6 Lodestar variants for the
    # the baseline so the user can pick the right thruster count.
    print_variant_sweep(ship, drive_family='LodestarFissionLantern')


def _demo_calibration_bc() -> None:
    """Verify the battleship-series (2026-05-31) screenshot calibration.

    All 4 screenshots: Battleship hull, Lodestar drive (variant changing),
    70 tanks, armor N91/B5/T10, on Gas Core V (Terawatt II) reactor.
    """
    print("\n=== Battleship-series calibration check (4 screenshots, only Lodestar count varies) ===")
    measured = {
        1: {'wet_t': 28194, 'combat_g': 0.796, 'dv_kps': 9.0,  'turn_dps2': 0.49},
        2: {'wet_t': 30014, 'combat_g': 1.5,   'dv_kps': 8.3,  'turn_dps2': 0.46},
        3: {'wet_t': 31834, 'combat_g': 2.1,   'dv_kps': 7.8,  'turn_dps2': 0.43},
        4: {'wet_t': 33655, 'combat_g': 2.7,   'dv_kps': 7.3,  'turn_dps2': 0.41},
    }
    # Calibrate other_mass_t against the x1 baseline (Gas Core V)
    baseline = Warship(
        hull='Battleship', drive='LodestarFissionLanternx1',
        armor='AdamantaneArmor',  # placeholder; real is what the user has
        tanks=70, nose=91, body=5, tail=10,
        reactor_spec_power_tGW=3.5,   # Gas Core V (Terawatt II)
    )
    try:
        baseline.calibrate(measured_wet_t=measured[1]['wet_t'])
    except Exception as e:
        print(f"  (calibration skipped — {e})")
        return
    print(f"  Baseline x1 measured wet {measured[1]['wet_t']:,} t → "
          f"other_mass_t = {baseline.other_mass_t:,.0f} t")
    print(f"  {'Variant':>7s}  {'Predicted wet (t)':>17s}  {'Measured wet (t)':>16s}  "
          f"{'Δwet':>6s}  {'Pred combat g':>13s}  {'Meas combat g':>13s}")
    for x in range(1, 5):
        ship = Warship(hull='Battleship', drive=f'LodestarFissionLanternx{x}',
                       armor='AdamantaneArmor', tanks=70, nose=91, body=5, tail=10,
                       other_mass_t=baseline.other_mass_t,
                       reactor_spec_power_tGW=3.5)
        # Skip turn metric (Battleship not calibrated for K_turn yet).
        wet = ship.wet_mass_t()
        # Combat g = (n_thrusters × cruise_MN × thrust_cap) / wet × g
        n = x
        cruise_mn = DRIVE_CRUISE_THRUST_MN_PER_THRUSTER['LodestarFissionLantern'] * n
        cap = DRIVE_THRUST_CAP['LodestarFissionLantern']
        combat_g = (cruise_mn * cap * 1e6) / (wet * 1000 * 9.81)
        delta = wet - measured[x]['wet_t']
        print(f"  x{x:>6}  {wet:>17,.0f}  {measured[x]['wet_t']:>16,}  "
              f"{delta:>+6,.0f}  {combat_g:>13.3f}  {measured[x]['combat_g']:>13.3f}")


if __name__ == '__main__':
    _demo_baseline()
    _demo_calibration_bc()
