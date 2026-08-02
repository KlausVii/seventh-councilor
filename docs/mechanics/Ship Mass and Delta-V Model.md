---
title: Ship Mass and Delta-V Model
game_version: 1.0.32 decompile (build 22085164; decompile repo brackets 1.0.30–1.0.33); lessons re-verified through 1.0.38+
---

# Ship Mass and Delta-V Model

Code-verified, campaign-independent model for how Terra Invicta computes a ship's **wet mass,
dry mass, ΔV, combat acceleration, and per-component masses** (reactor / radiator / drive /
armor / tanks). Derived 2026-06 from the decompiled C# (see Evidence) and validated to the
ton/tenth-kps against in-game shipbuilder readings. This is the math behind
`scripts/warship_optimizer.py` — read this to reason; run the optimizer to compute.

> **Evidence.** `[code]` = decompiled C#, primary source the community decompilation at
> **`Armandox33/Terra-Invicta-AI-Assistant`** on GitHub, path
> `TI Assembly Project/Assembly-CSharp/…` (clean `.cs` per class — cited by symbol only, never
> copied here; repo vintage ~1.0.30–1.0.33). Cross-checked against the installed build (1.0.32)
> to confirm the repo hasn't drifted. `[tpl]` = template JSON,
> `[save]`/`[ship]` = shipbuilder reading. **Re-verify after any patch.**

## 1. Total mass

```
wet_mass = dry_mass + propellant
dry_mass = hull_base + reactor + radiator + drive_hardware + armor + weapons + utility_modules + tank_hardware
```

In `warship_optimizer.py` everything thruster-independent (hull + weapons + utilities + the
non-drive remainder) is back-solved into a single `other_mass_t` via `.calibrate(measured_wet_t)`;
the per-thruster (reactor+radiator) and per-tank pieces are modeled explicitly below.

## 2. Propellant tanks — **100 t each** `[code][tpl]`

`spaceResourceToTons = 0.1`; **1 propellant tank = 10 resource units = 100 t** of propellant,
regardless of propellant type. Verified by a clean tank-only sweep (a reference battlecruiser, no-PD variant Block 6,
identical weapons): 65 / 66 / 67 tanks → 24,191 / 24,291 / 24,391 t = exactly +100 t/tank `[ship]`.

> **Flip-flop history (resolved):** earlier reverse-engineering produced "117 t/tank" — a
> *compensating-error artifact* (it assumed ΔV uses the raw template EV, then back-solved 117 t
> to fit, which also matched wet-mass deltas). The decompiled `spaceResourceToTons = 0.1` plus
> the clean sweep settle it at **100 t**. The real fix was the EV multiplier in §6, not the tank.

## 3. Drive hardware — **0 t** for thermal drives `[code][tpl]`

The drive thruster itself has `flatMass_tons = 0` (Lodestar verified). **All** per-thruster mass
comes from the reactor + radiator it requires. `DRIVE_HARDWARE_T_PER_THRUSTER` ≈ 0 for Lodestar.

## 4. Reactor mass `[code][tpl]`

```
reactor_mass = required_power_GW × reactor.specificPower_tGW
```
`required_power` is the drive's `req power` field (scales linearly with thruster count).
Reactor `specificPower_tGW` and `efficiency` from `TIPowerPlantTemplate.json`:

| Reactor (dataName) | In-game display | spec t/GW | efficiency | maxOutput GW |
|---|---|---:|---:|---:|
| GasCoreFissionReactorIII | Gas Core Fission Reactor III | 3.0 | 0.95 | 150 |
| GasCoreFissionReactorIV | — | 10.0 | 0.93 | 1650 |
| GasCoreFissionReactorV | Gas Core Fission Reactor V | 3.5 | 0.95 | 1650 |
| **GasCoreFissionReactorVI** | **"Terawatt Gas Core Fission Reactor III"** | **1.0** | **0.96** | 1650 |

⚠️ Display-name trap: the in-game **"Terawatt Gas Core III"** is dataName **GasCoreFissionReactorVI**
(like OrbitalTorusHabs → "Ring Habs"). Confirmed: 1 t/GW, 96% eff, 747 t at 746.8 GW output.

## 5. Radiator mass — sized to reactor waste heat `[code][tpl]`

```
waste_heat_GW = required_power_GW × (1 − reactor.efficiency)        # reactor inefficiency
radiator_mass = waste_heat_GW × radiator_t_per_GW
radiator_t_per_GW = 1000 / radiator.specificPower_KWkg              # Tin Droplet: 8 → 125 t/GW
```
`WasteHeat_GW = max(crewHeat, requiredOutput) × (1 − reactor.efficiency)`
(`TIPowerPlantTemplate.cs:67-81`; radiator sizing `TISpaceShipTemplate.cs:2832`) `[code]`.
**Closed-cycle** drives (e.g. Lodestar) radiate this; **open-cycle** drives vent it with the
propellant exhaust and need radiators only for crew heat (negligible). The drive's *own*
mechanical loss (`req power − thrustRating_GW`, e.g. 56 GW on Lodestar x4) goes to the **exhaust,
not the radiator** — confirmed because radiating it would need ~10,000 t, vs the actual ~3.7K t.

**Per-thruster mass (Lodestar on Terawatt GC III):** reactor 186.7 t (186.7 GW × 1) + radiator
933 t (186.7 × 0.04 × 125) = **1,120 t/thruster**; ~83% is radiator. (Lodestar on GasCoreV =
653 + 1,167 = 1,820 t/thruster — radiator dominates because GC-V is heavier & less efficient.)

## 6. Delta-V and the EV multiplier `[code]`

```
ΔV_kps = modifiedEV_kps × ln(wetMass_tons / dryMass_tons)            # TISpaceShipTemplate.cs:489
modifiedEV_kps = driveTemplate.EV_kps × ∏(utility-module EVMultiplier) # TISpaceShipTemplate.cs:3251
```
The template `EV_kps` is the **thrust-relevant** value (thrust = ṁ × EV; jet power = ½·thrust·EV).
The **ΔV uses the *modified* EV** = template EV × product of installed utility-module EVMultipliers.

- **Liquid Hydrogen Containment** is the only EVMultiplier module: `EVMultiplier = 1.2`
  (`specialModuleValue`) `[code][tpl]`. So a ship with LHC has effective EV = `EV_kps × 1.2`
  (≈ +17% ΔV) for one 5 t module slot. Without LHC, factor 1.0.
- This is what an earlier "drive-specific 1.2 ΔV factor" actually was — a property of the **LHC
  module**, not the drive. Ships carrying LHC (the three LHC-carrying reference designs) all showed 1.2.

In `warship_optimizer.py`: `Warship(ev_multiplier=1.2)` when LHC is fitted (1.0 otherwise).

## 7. Combat acceleration & thrust cap `[code]`

```
combat_thrust_N = drive.thrust_N × modifiedThrustCap                 # nominal thrustCap = 20
combat_accel_g  = combat_thrust_N / (wet_mass_kg × 9.80665)
```
Combat accel is **capped by the faction's max-survivable-combat-acceleration** (the g-cap from the
crew/biology tech ladder — High-Thrust Ergonomics → Astronaut Fitness Regimen → Acceleration
Pharmaceuticals → High-G Recombinants, each +0.5 g, additive/stackable). The
shipbuilder **clips** displayed combat accel to that cap,
so thrust beyond the cap is wasted. `modifiedThrustCap` drops to ~0.55× nominal on small hulls
without a heat-sink module (`effective_thrustcap_multiplier`).

## 8. Hull armor `[code][tpl]`

Per-point armor mass = `area_m² × thickness_per_point(7.86 cm Nanotube) × density / 1000`, or read
the in-game **armor module tooltip** directly (it shows t/point for nose-or-tail and lateral, and
the per-section caps). `HULL_ARMOR_COEFFICIENTS` (t per point, Nanotube; coef = t/pt ÷ 1.72):

| Hull | nose/tail t/pt | lateral t/pt | caps N / L / T |
|---|---:|---:|---|
| Lancer | (per-hull) | (per-hull) | — |
| Monitor | 43.1 | 799.1 | 57 / 30 / 57 |
| **Battlecruiser** | **42.5** | **1,119** | **80 / 30 / 80** |
| Battleship | 67.6 | 1,594 | — |
| Dreadnought | 134.7 | 3,072 | 126 / 53 / 126 |

Armor depth caps scale with hull geometry (`nose ≤ length × 0.036`, `lateral ≤ width × 0.12`,
`TIShipHullTemplate.cs:120-146`). Lateral is far more expensive than nose on every hull →
**nose-heavy splits are structurally favored** (e.g. N80/L5/T10).

## 9. Worked example — reference battlecruiser (Terawatt GC III, N80/L5/T10, LHC)

All reproduce the in-game shipbuilder exactly:

| Drive | Tanks | Reactor | Radiator | Drive-sys | Wet | ΔV | Combat g |
|---|---:|---:|---:|---:|---:|---:|---:|
| Lodestar x3 | 60 | 560 t | 2,800 t | 3,360 t | 22,476 t | 11.8 | 3.0 |
| Lodestar x4 | 65 | 747 t | 3,734 t | 4,481 t | 24,096 t | 11.8 | 3.7 |
| Lodestar x5 | 65 | 934 t | 4,668 t | 5,602 t | 25,216 t | 11.2 | 4.0 (capped) |

Each added thruster = +1,120 t (mostly radiator). x5 overshoots the 4.0 g cap (clipped). ΔV uses
modifiedEV = 31.4 × 1.20 (LHC) = 37.7 kps. A reference-campaign siege-battlecruiser design case supplies the full
design analysis and the x3-vs-x4-vs-x5 verdict (stay x3 for a stationary-base siege).

## Cross-refs
- [Drives Refits and Logistics](Drives%20Refits%20and%20Logistics.md) — refit legality, open-cycle cooling, the same radiator/waste rule
- [Space Combat Math](Space%20Combat%20Math.md) — weapon/armor damage, hardpoint mounts, battle cap
- `scripts/warship_optimizer.py` — the executable model (calibrations baked in)
