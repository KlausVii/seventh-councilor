---
title: Hab power and solar output — the real generation math
evidence: decompiled C# (`TIHabModuleTemplate.SolarPowerOutput`, `NaturalSolarPowerMultiplier`, `SolarMirrorBonus`) for the call chain and cap; save-empiric + in-game UI readings for the multiplier reconstruction (three-body validation); mirror aggregation is a labeled estimate
---

# Hab power and solar output — the real generation math

Why you need this: a hab's power balance decides whether a module you power on (or an
upgrade you click) actually runs. Summing template `power` values gets solar habs badly
wrong — in the reference campaign, a Mars base read as −200 deficit on naive template math
while the game showed **+722 surplus**, because each of its Solar Farms (template power
240) actually produced **543**. This note is the decode. Tool: `hab_power_audit.py`
(per-hab ledger, idle generators, powerable-now verdicts).

**REFUTED — "solar output = template power × 1/r²."** Template power is a 1-AU-ish rating
but the real multiplier is NOT bare inverse-square: surface sites see day/night and
atmosphere, orbits see horizon shadowing, and solar-mirror stations can push a base's
output far ABOVE its rating (up to the 8× cap below).

## The code-verified law (`TIHabModuleTemplate.SolarPowerOutput`)

For any module whose template carries the `Solar_Power_Variable_Output` special rule
(SolarCollector/SolarArray/SolarFarm and automated variants):

```
output = round(basePower × NaturalSolarPowerMultiplier(location))
         [+ SolarMirrorBonus                — surface BASES only]
output = min(output, 8 × basePower)         — hard cap
```

- `NaturalSolarPowerMultiplier` reads a `solarMultiplier` field with location priority
  **orbit → hab site → space body** (0 if none resolve).
- `SolarMirrorBonus = spaceBody.solarMirrorBonus[faction] × basePower` — mirrors beam power
  to **bases** on that body; stations don't receive it.
- Non-solar generators (fission/fusion arrays, cores) produce flat template power —
  no location scaling.

`solarMultiplier` is runtime-computed, **not serialized in the save** (`TIHabSiteState`
carries yields/latitude but no multiplier), so scripts must reconstruct it. The in-game
site info box shows it directly (the ☀ number) — that readout is ground truth.

## Reconstructing the multiplier (save-empiric, 3-body validation)

**Surface site:** `solarMultiplier ≈ dayFraction × atmosphereFactor × (1 AU / a)²`,
where `a` = the semi-major axis of the body's Sun-orbiting ancestor
(`TISpaceBodyTemplate.semiMajorAxis_AU`; moons use their planet's) and dayFraction = 0.5.

Validated against three in-game site readouts (reference campaign, build 1.0.38):

| Site | a (AU) | atmosphere | computed | in-game ☀ |
|---|---:|---|---:|---:|
| Mars surface | 1.5237 | Thin → 0.75 | 0.1615 | **0.16** ✓ |
| Mercury surface | 0.387 | None → 1.0 | 3.34 | **3.3** ✓ |
| Io surface | 5.204 (Jupiter) | Trace → 1.0 | 0.0185 | **0.018** ✓ |

Atmosphere factors (`TISpaceBodyTemplate.atmosphere`): None/Trace **1.0** and Thin
**0.75** are validated by the table; Standard **0.5**, Thick **0.25**, Dense **0.0** are
extrapolated estimates — confirm against a ☀ readout before leaning on them.

Two lower-confidence refinements (labeled estimates, encoded in `hab_power_audit.py`):

- **Polar sites on low-tilt bodies** (|latitude| > ~85°, body tilt < ~5°, Sun-orbiting —
  e.g. Mercury's poles) run a higher day fraction, ≈ `0.5 + |lat|/360` (near-constant
  illumination).
- **Orbital stations**: `solarMultiplier ≈ (1 − atan(R_body / a_orbit)/π) × (1 AU / a)²` —
  full sun minus the fraction of the orbit shadowed by the body's disk.

## Solar mirrors — how a 240-rated farm makes 543 on Mars

Mirror modules (`SolarMirror` ×0.1-class, `SolarMirrorArray` ×0.2-class — **Station-only**
modules with trivial own power draw, −1/−4) accumulate into the body-level
`solarMirrorBonus` for their faction; every solar module on a **base** at that body then
adds `bonus × basePower` on top of its natural output.

Reference-campaign worked example (Mars, heavy mirror coverage): Solar Farm output
**543** = round(240 × 0.1615 = 39 natural) + 504 mirror bonus → implied
`solarMirrorBonus ≈ 2.10`. The per-mirror contribution and its distance scaling are NOT
pinned down — treat any mirror math as an estimate, read the module's **Generator** line
in-game for truth. The **8 × basePower cap** (code-verified) bounds how far mirror
stacking can go: a Solar Farm can never exceed 1,920.

## Power-planning rules that fall out

1. **Idle generators are instant capacity.** A completed generator with `powered: false`
   is switched off, not broken — powering it on beats building a new reactor by 60–120
   days. Any power audit must count idle-generator capacity before declaring a module
   "not powerable" (`hab_power_audit.py` does).
2. **Upgrades need only the NET draw.** The prior module goes offline at click time (see
   [Hab Build Costs and Radiation](Hab%20Build%20Costs%20and%20Radiation.md)), so an
   OperationsCenter→CommandCenter upgrade needs +200 headroom (−300 new vs −100 old), not
   +300 — unless the OC was already unpowered, in which case budget the full 300.
3. **A generator under construction counts for sequencing, not for now.** If the reactors
   land before the upgrade completes, it's safe to click both; the audit lists in-flight
   generators per hab so you can check the ETAs (`module_completion_dates.py`).
4. **Solar habs at Mercury are power-rich, radiation-taxed** — huge surpluses (multiplier
   ~3.3, before mirrors) but the build-cost surcharge is what kills upgrade payback there;
   see [Hab Build Costs and Radiation](Hab%20Build%20Costs%20and%20Radiation.md).
5. **Ground truth beats the reconstruction.** The site ☀ readout and each module's
   Generator line are authoritative; the script's solar figures are estimates (exact for
   validated atmosphere classes, no mirror term) and it says so in its output.
