# TI analyzer lessons — Ship design, drives, armor & combat

Part of the Seventh Councilor lessons library (see the repo `CLAUDE.md`). IDs permanent
(`S1`…). Dates and worked numbers come from the
reference campaign (Resistance, 2026 start, Normal difficulty). **Rule zero: for ANY
design/refit/mass/ΔV/combat-g question, run `warship_optimizer.py` first** (see the repo
`CLAUDE.md` script inventory). Read this file before ship recommendations.

## Verified core formulas (code-verified against decompiled source, 2032-06; single canonical copy)

- **Ship ΔV** = `modifiedEV_kps × ln(wetMass / dryMass)` (`TISpaceShipTemplate.cs:489`).
- **modifiedEV_kps** = `driveTemplate.EV_kps × ∏(utility EVMultiplier)` — template `EV_kps`
  is also the thrust-side value (thrust = mdot × EV); ΔV uses the MODIFIED EV.
- **Liquid Hydrogen Containment**: the only EVMultiplier module — ×1.2 EV (~+17% ΔV).
- **Propellant tank** = 10 resource units (`spaceResourceToTons = 0.1`) = **100 t, regardless
  of propellant** (decompiled + clean tank-only shipbuilder sweep; encoded as
  `DEFAULT_PROP_PER_TANK_T = 100.0` in `warship_optimizer.py`, with
  `PROP_PER_TANK_BY_PROPELLANT` now empty). The earlier "~117 t/tank for hydrogen drives"
  was a compensating-error artifact: the calibration ships all carried Liquid Hydrogen
  Containment, and back-solving tank mass while ignoring its ×1.2 EV multiplier reproduced
  the observed ΔV. The real ~17% is the LHC EV multiplier, not the tank. See
  [Ship Mass and Delta-V Model](../mechanics/Ship%20Mass%20and%20Delta-V%20Model.md) §2/§6.
  Refuel RESOURCE cost is water regardless (E17).
- **Radiator waste heat** = `requiredOutput × (1 − reactor.efficiency)`; radiator t/GW =
  1000/specificPower (Tin Droplet 125, Exotic Spike 41.7).
- **Combat g** = `min(n_thr × cruise_per_thr × thrustCap / wet / 9.81, BIOLOGICAL_G_CAP)` — S11.
- **Per-thruster mass** decomposition — S14.
- Optimizer calibrations (Battleship/Lodestar/Nanotube: OTHER 3,707 t; per-thruster GC-V
  1,820 t; Battlecruiser armor coefs nose 24.71 / lateral 650.58) live in
  `warship_optimizer.py` — trust the script over memory.

## S1 — Check COMBAT thrust (cruise × `thrustCap`), never cruise + EV

`thrustCap` is the combat burst multiplier — the warship number. Per-thruster (x1) examples:
Lodestar 11 MN × 20 = **220 MN combat** (x6 = 1,320 — the fission warship king); Firestar
5 MN × 22 = 110; Pharos 0.89 × 16 = 14.2; **Poseidon Lantern (NeutronFluxLantern) 12.9 MN ×
2 = 26** — huge cruise numbers, transit drive, NOT a warship drive (the old "77.4 MN cruise"
figure was the x6 variant). Electric drives (Pebble/PlasmaWave/PulsedPlasmoid) are worse than
mid-fission in combat. Sort warships by `combat_thrust × √EV`; transit/colony picks may use
cruise. Past mistake: called NFL "strictly better than Lodestar" — backward by ~6× in combat.

## S2 — Refits stay within the SAME reactor/drive family

The refit UI only allows higher tiers of the same family (`driveClassification` for drives —
NOT name prefix: Pharos and Lodestar are both `Fission_Thermal`, so that refit is legal;
NSWR `NuclearSaltWater` is its own family). SolidCore→GasCore etc. is blocked. Workflow:
group by family, find the researched family max, flag only below-max ships; family-max ships
are "stranded — keep as legacy" (scrap+rebuild almost never pays on a metals-tight run).

## S3 — Reactor enum ↔ UI-name translation

`requiredPowerPlant` enums differ from project friendlyNames: `Liquid_Core_Fission` = **Molten
Core Fission Reactor**; SolidCore dataNames VIII/IX/X display as **Compact Solid Core
III/IV/V**. Always translate to the display name (the extractor's
`required_reactor_display` does) or you'll claim a drive is blocked that isn't.

## S4 — `cooling: Closed` vs `Calc` matters for warships

Calc-cycle drives need external radiators — extra mass AND combat-vulnerable. Prefer Closed
(Lodestar/Pharos/Pulsar ✓; Pegasus/Helicon ✗) unless the thrust/EV gap is overwhelming.

## S5 — friendlyNames drift between patches; don't claim a drive doesn't exist

When the user names a module the script doesn't print, check the `DRIVE_FRIENDLY_OVERRIDE`
map / localization first (NeutronFluxLantern → "Poseidon Lantern"; NeutronFluxTorch →
"Poseidon Torch"). Extend the map on each new rename.

## S6 — Don't reflex-add Magazine to Mk3+ kinetic ships

Mk3 kinetic base magazines last 60–240 minutes of continuous fire vs 5–15-minute battles.
Magazine IS right for missile/torpedo bays (Apollo: 6→9 shots) and multi-engagement campaign
fleets; wrong on single-engagement defenders, Mk3 spinals, and laser ships. The freed slot
usually wants Component Armor.

## S7 — Armor mass = hull geometry coefficient × density; read templates

Density from `TIShipArmorTemplate.json` (FoamedMetal 920 / Nanotube 1720 / Adamantane 1800 /
Hybrid 2000 (LaserResistance 0.75) / Steel 7850 kg/m³); per-hull section coefficients derive
once from a reading (Lancer: nose=tail 64.42 m³/pt, lateral 1,484.30 — **23× nose**). The
lateral/nose asymmetry drives allocation: max nose+tail cheaply, minimize lateral. The
optimizer reads densities directly.

**Armor COST per ton = `weightedBuildMaterials × 0.1`** (verified against the in-game Hybrid
tooltip: weights .38/.45/.165/.005 → 0.038 vol / 0.045 met / 0.017 nob / **500u (0.0005) exotics**
per ton). Treating the raw weights as per-ton costs over-states armor cost **10×** and wrongly
rules out exotics-bearing plate — a full Hybrid set is well under 1 exotic on a light hull, not 5+.
Use `warship_optimizer.armor_cost(mass_t, armor_name)`.

## S8 — Calibrate per-thruster mass from CONTROLLED-VARIATION screenshot series

Only the drive count may vary between readings (same hull/armor/tanks/utilities/reactor).
Lodestar on GC-V = 1,820 t/thruster (calibration battleship series, 4 readings, ±1 t); construction cost
≈ 131.5 metals + 19.6 nobles + 3.3 fissiles + 6.5 water + 33 vol per thruster. Reactor-tier
shift: `(new_spec − calibrated_spec) × req_GW_per_thruster` (GC-VI: 1,353 t predicted →
confirmed via S14 as 1,120 with radiator scaling). Never back-solve from two dissimilar ships.

## S9 — Salvage Bay is CORE on Defenders

Defenders kill in friendly space; wrecks stay near friendly habs; Salvage Bay reclaims
200–500 metals per Hydra wreck. Keep it unless metals are flush (>180d) AND the slot has a
time-critical competitor.

## S10 — Utility modules cannot TYPE-swap in refit

Slots are committed to their module family at first build (Salvage Bay → Component Armor =
"invalid refit"); only tier upgrades within family work (TargetingComputer 1→2→3). A
different utility loadout requires a NEW CLASS. Design first builds accordingly — this is why
researching a key utility (e.g. Exotic Heat Sinks) BEFORE a hull generation is laid down
matters.

## S11 — Combat g cap is BIOLOGICAL

`displayed_combat_g = min(peak_thrust/mass/g, BIOLOGICAL_G_CAP)` where the cap =
**3.0 + 0.5 × completed cap-raisers** (four LifeScience projects, additive, stackable, max
5.0g): High-Thrust Ergonomics (1k tpl) → Astronaut Fitness Regimen (2.5k) → Acceleration
Pharmaceuticals (10k) → High-G Recombinants (20k, needs Genies). Verified by a 4-variant
light-hull design series (x3/x4 both flat at the then-cap 3.5 with no heat sink anywhere).
**Retracted theories** (kept as tombstones — do not resurrect): the heat-sink multiplier
model (old #39, "0.55× without heat sink") and the heat-dissipation "sustainable cap" model
(old #43) were curve-fits to too little data. Heat sinks affect sustained-burst endurance
(GJ capacity), not peak g. **Surviving corollaries** (true under the bio-cap): on hulls whose
peak exceeds the cap, extra thrusters are wasted and armor/tanks are FREE for displayed g
until peak falls to the cap — so max nose armor before adding drives on capped light hulls
(old #40's practical rule). Combat value of raising the cap depends on the ENEMY: beams are
hitscan (see S16), so vs a laser-dominant fleet the gain is engagement-geometry only.

**Derive the cap from the SAVE, never a hardcoded default — and mind the HYPHENS.** The raiser
project dataNames are `Project_High-ThrustErgonomics`, `Project_AstronautFitnessRegimen`,
`Project_AccelerationPharmaceuticals`, `Project_High-GRecombinants`. Matching without the hyphen
silently misses raisers: 2033-10 an analyst read the cap as **3.5 g when it was actually 4.0 g**
(High-ThrustErgonomics missed), under-stating every mass-at-cap budget by 14%. Use
`warship_optimizer.bio_g_cap_from_save(finished_project_names)`.

## S12 — The in-game armor tooltip is CANONICAL for per-point mass

It displays mass per nose/tail point, per lateral point, thickness per point (a SINGLE value
across sections — 7.86 cm for Nanotube; the asymmetry is pure area), per-hull max caps, and
points-to-halve X-ray/baryonic. Monitor Nanotube: 43.1 t/pt nose/tail, 799.1 lateral. Known
caps: Lancer 114/38/114, Battleship 91/38/91, Monitor 57/30/57. Nanotube halves X-ray per
2.53 pts vs baryonic per 19.78 (≈8× better vs lasers). When calibrating a new hull/armor
combo, ask for the tooltip screenshot; the W²-formula is the fallback (±0.5%).
**Armor specialties (corrected 2026-07-06 — Adamantane is NOT "balanced"):** Hybrid =
LaserResistance 0.75; **Adamantane = KineticsResistance 0.75** (its mirror); Exotic = none.
Per-mass halving indices (kg/m², lower better; laser/kinetic): Hybrid 90/220 · Exotic
114/264 · Adamantane 324/2084 · Nanotube 342/2673. Hybrid dominates all axes vs the
beam-heavy Hydra; Adamantane = zero-exotics builds (see the amendment below — stronger than
this line implies) or anti-kinetic (human) enemies;
Exotic is obsolete once Hybrid is researched.

**⚠ AMENDMENT (2033-10-25) — an armor POINT is not a fixed thickness across materials, so every
per-point mass AND every per-hull cap is material-specific:**

    thickness_cm_per_point = xRayHalfValue_cm / XRayResistance     # template fields
    Nanotube 7.866 (= tooltip's 7.86 ✓) · Adamantane 3.734 · Exotic 2.600 · Hybrid 2.500

The caps above (Lancer 114/38/114 etc.) are **Nanotube** readings. A hull's cap is a fixed max
THICKNESS, so `cap_material = cap_nanotube × 7.866 / cm_per_point`, and mass per point scales the
same way: `t/pt = hull_coef_nanotube × (cm_per_point / 7.866) × density`. Consequences that flip
earlier conclusions:

| Hull / material | nose t/pt | nose cap (pts) | block at cap (pts^1.5) |
|---|---:|---:|---:|
| Lancer Nanotube | 110.8 | 114 | 1,217 |
| Lancer Adamantane | 55.1 | **240** | 3,721 |
| Lancer Hybrid | 40.9 | 359 | 6,793 |
| Battlecruiser Nanotube | 42.5 | 80 | 716 |
| Battlecruiser Adamantane | 21.1 | **169** | 2,187 |
| Battlecruiser Hybrid | 15.7 | 252 | 3,994 |

Since laser block is `points^1.5` and the material contributes ONLY its LaserResistance multiplier
(S12 above / [[Mechanics/Orbital Bombardment]] §8), buying cheap points is most of the game:
**maxed Adamantane blocks ~3× maxed Nanotube on the same hull** — so Adamantane is the correct
*exotics-free siege* armor, not merely an anti-kinetic niche pick. Hybrid still wins outright when
exotics allow. Validation: `armor_cm_per_point` reproduces the Monitor Nanotube tooltip (43.1 /
799.1 t/pt) exactly, predicts the player's observed Lancer-Adamantane cap of 241 as 240, and
reproduces the Orbital Bombardment doc's BC-Hybrid figures (17 t/pt, cap 252) as 15.7 / 252.
`warship_optimizer.py` applies this scaling in `armor_coefficients()`; before the 2026-07-30 fix it
priced every non-Nanotube design ~2× too heavy per point and silently understated its cap.

## S13 — Missile-boat armor allocation: max nose, min body, medium tail

⚠ Do NOT repeat the Vector Thrusters hallucination: VT adds ROTATIONAL force only ("quicker
ship rotations") — no off-axis thrust; ships burn along the nose. Standoff missile geometry:
missiles are facing-independent; approach and firing are nose-on (aspect ~1° at 700-900 km);
retreat is TAIL-on; lateral exposure is ~1 second of a lost merge. Allocation on a Monitor:
Nose MAX (57) / Body 1 (lateral costs 18.5× nose per point — worst ROI in the game) / Tail
~7–20 (retreat phase; free for displayed g while peak > cap, costs only ΔV). Nose 57 Nanotube
≈ 22 laser-halvings — a bow shield exactly where laser fire arrives.

## S14 — Per-thruster mass = reactor + radiator + drive hardware

`per_thruster = drive_hw + req_GW × reactor_spec_t/GW + req_GW × (1 − reactor_eff) ×
radiator_t/GW_waste`. Lodestar (186.7 GW/thruster, drive_hw ≈ 0!): GC-VI + Tin Droplet =
1,120 t ✓; GC-V + Tin Droplet = 1,820 t ✓. So a GC-V→VI refit saves ~700 t/thruster (233 of
it radiator shrinkage). In `warship_optimizer.py:mass_per_thruster_from_first_principles()`.

## S15 — Weapon MOUNT TYPE, not hardpoint count, determines fit

Mounts are sized strings: `OneHull`/`FourHull`, `ThreeNoseAngle`/`FourNose`. A single 720cm
laser cannon is `ThreeNoseAngle` — it consumes ALL 3 BC nose hardpoints; the 960cm
(`FourNose`) doesn't fit a 3-nose hull at all. Map each proposed weapon's `mount` against the
hull's free hardpoints (`TIShipHullTemplate.json`: nose/hull/internal — Battlecruiser 3/2/5)
before claiming a slot is free.

## S16 (new 2026-07-03, from the four-corrections set) — Beams are HITSCAN; acceleration doesn't dodge them

`Weapon.InArc` (decompiled): laser and particle weapons use an angle-only check — instant
beams. Only guns/missiles use intercept prediction with target velocity+acceleration. The
ship-RATING mobility term also clamps at 3g (`clamp(combatAccel_g, 0.1, 3)` in the SCV
formula). So vs the Hydra's beam-dominant armament (~132 lasers / 19 particle), combat-g
raises buy engagement-geometry control (closing/kiting), not survivability; census which
hulls actually clip the current cap AND the enemy weapon mix before scoring g-cap projects
(cross-ref R19).

## S17 (new 2026-07-03) — Marine capability lives on SHIPS (assault units) and habs (defense)

Assault troops for Seize Space Asset / hab raids come from ship utility modules
MarineAssaultUnit / Advanced / Elite (values 4/6/8, 200 t, 30 crew) — or a DropTroops hab of
yours at the target's own location. Marine BARRACKS hab modules (Platoon/Company/Battalion,
values 10/20/40) are `HabDefense` for YOUR habs — not an assault tool. Check what the fleet
already carries before scoring marine anything (2033-02: Elite MAUs were researched and
fitted on 15 designs). Assault success: `P = 1 − 0.5 × 0.775^(attacker − defender)`; alien-hab
"capture" is a raid that destroys the hab and loots exotics
([Victory Conditions and Endgame](../mechanics/Victory%20Conditions%20and%20Endgame.md) §5;
specimen milestones: [LESSONS-aliens](LESSONS-aliens.md) A3).

## S18 (2026-07-07) — Munition semantics: warhead class, naming traps, and volley geometry

From the AMWD batch analysis (templates `TIMissileTemplate.json`):
- **"Nuclear-Powered X Torpedoes" = NERVA PROPULSION with conventional warheads** (Ares/
  Zeus/Athena), NOT nuclear warheads. "X-Fueled Nuclear" = actual nukes (Cerebrus/Hades/
  Python/Nemesis). Read `warheadClass`, never the display name.
- Damage fields: Explosive/Nuclear carry `flatDamage_MJ`; **Penetrator/Frag have NONE** —
  kinetic ½mv² on `warheadMass_kg`, scaling with closing-velocity² (great head-on, ~zero in
  a stern chase). Frag splits to submunitions at terminal: PD-saturation layer, weak vs
  armor (engine behavior, community-verified).
- Profile split: 800-km "missiles" = mag 16, 8-shot salvos, 18.3 g (saturation wave);
  1,000-km "torpedoes" = mag 4-6, singles, slower (standoff). Mixed loadouts interlock:
  frag screen flies the same profile as same-propellant missiles and soaks PD for them.
- Shaped-nuclear ladder (Olympus→Acheron→Tartarus→Styx) = same 1 MT, tightening
  `shapedChargeAngle` 0.2→0.15→0.125→0.085 rad (≈5.5× energy density Olympus→Styx), at
  falling ΔV and creeping exotics. Nemesis (plain 1.2 MT nuclear) needs no new global.
- `bombardmentValue` doubles as the surface-flattening stat (Hades 100 / Cerebrus+Python 50)
  — factor it when the same bays must soften a base for assault.

## S19 (2026-07-14) — Engagement math includes the STATION stack; design-SCV sums are optimistic

A strike on the ~172k of alien fleets at Europa was recommended on a 2:1 design-SCV ratio
(the player's 354k Jupiter fleet) — wrong on two counts (save-verified 2026-07): if the
player attacks, the alien station at Europa joins the battle and kills the whole fleet.
① Fleets docked at a hab fight WITH the
hab's modules — that station adds 6× AlienBattlestations (~29k by the fortress-base 4,854
per-module figure) + 2 Citadels + **AlienLayeredDefenseArray** (dense PD that eats
missile/torpedo alpha, the backbone of the player's fleets). ② Σ design
`_unnormalizedCombatValue` ignores live state, crew/officer quality, PD interaction, and
fleet-vs-station mechanics — treat it as a screening ratio only; the in-game intel battle
assessment (and the player's own sim experience) is the ground truth. Rules: evaluate the
full stack (all docked fleets + station modules) at the defender's hab; prefer engaging alien
fleets in open orbit, in transit-arrival at YOUR stations (your stack advantage — the
own-station-anchor doctrine), or detached from their anchors. Corollary: the Europa alien station
carries **5× AlienSpaceworks** — a top production-kill target for the properly-built
expedition, exactly the class of target
[Alien Production Rebuilding and Targeting](../mechanics/Alien%20Production%20Rebuilding%20and%20Targeting.md)
§1 says makes fleet kills stick — later, with counter-PD saturation, not with today's fleet.

## S20 (game 2033-08-22) — Fusion reactor LADDERS split into a REACH line and a THRUST line; don't call one "dominated"

Each fusion reactor family drives a distinct drive family; two families with the SAME reactor
tier trade EV against thrust, so ranking them on a single axis is wrong. Verified per-thruster
(x1) from `TIDriveTemplate.json`:

| Tier | **Torus** (Tokamak reactors) | **Nova** (ICF reactors) |
|---|---|---|
| Deuteron (needs DDF) | EV **769**, 12.5 MN | EV 572, **21 MN** |
| Helion (needs DHe3) | EV **690**, 39 MN | EV 527, **95 MN** |
| Protium (deep) | EV **952**, 151 MN | EV 1,000, **396 MN** |

**Nova = warships** (higher thrust → higher combat-g, S1); **Torus = couriers / freighters /
colony haulers** (higher EV → reach). Both tier up on the same DDF→DHe3 globals, one
Fusion-Tokamak-N / ICF-N reactor + drive project each.

**Third axis — PROPELLANT COST (`perTankPropellantMaterials`, fraction of each tank's mass by
resource). Always compare it; it decides SUSTAINED operating cost and varies ~60× across
drives:**
- Deuteron Torus = **100% water** (cheapest fuel in the game) — reinforces Torus-for-logistics.
- Deuteron Nova = 99% water / 1% nobles (cheap). Lodestar 98% water. Helicon 90% water/10% metals.
- **Helion tier FLIPS expensive: both Helion Torus and Helion Nova burn 10% FISSILES/tank** —
  a real fissile logistics tail every refuel; don't over-tank Helion hulls, and plan fissile
  production around a Helion warship fleet.
  **⚠ Correction (2033-09, localization-verified): ONE active Helium-3 Mine ERASES this.**
  `HabModuleSpecialRule.HarvestHelium3`: "all of this faction's Helion fusion drives do not
  use any fissiles in its propellant load, and heavy fusion modules do not use fissiles in
  their construction or ongoing support costs." The mine is a tier-3 gas-giant interface-orbit
  module; `Project_Helium-3Mine` is 5,000 template RP, 100% avail (prereqs: Ring Core,
  DeuteriumHelium3Fusion, Mission to Jupiter, Space Mining and Refining). So Helion operating
  cost is ~pure water WITH the mine, fissile-heavy WITHOUT — always check for it before
  scoring Helion fuel logistics. (The Heavy fusion HAB modules — HeavyFusionPile/ReactorArray/
  ReactorFarm — carry the matching `UsesHelium3` rule; regular fusion hab modules do not.)
- **State per-tank cost in ABSOLUTE units, not % mix**: 1 tank = 100 t = 10 resource units,
  so Poseidon Torch's "60% fissiles" = **6 fissiles + 1.5 volatiles + 2.5 water per tank**.
  Players budget refuels in units against stockpiles/income; a % mix hides that (e.g. a
  volatiles stockpile of 13 units can't fill ONE 12-tank Torch hauler at 1.5/tank).
  `fusion_ladder_planner.py` prints a per-tank-units column.
- Extremes (fissile-brutal, single-leg / no-refuel drives, NOT shuttles): **Dusty Plasma 100%
  fissiles**, **Poseidon Torch 60% fissiles**. Triton Fusor is metals-heavy (24% metals/tank).
So the courier winner isn't just "high EV" — it's **Deuteron Torus: high reach AND pure-water
fuel**. Rank drives on THREE axes within role: thrust (combat-g), EV (reach), propellant cost.
So a deep-system expansion fleet WANTS the Tokamak/Torus line even though ICF "dominates" on
combat thrust — the earlier flat "Tokamak is dominated, skip" (the 2033-02 global ranking,
3/C−) was warship-tunnel-vision; corrected to run BOTH ladders (5/B− for a logistics fleet).
Generalize: before scoring a drive/reactor line, name the ROLE (combat vs transit, S1's
cruise×cap vs EV) and compare within role. Mirror-Cell/Electrostatic ladders remain true dead
ends (Reflex/Fusor, 1–5 MN AND low EV) — "two lines" is not "every line is good." (The
Tokamaks re-score and the Torus/Nova table come from an earlier reference-campaign
ranking pass.)

## S21 — Reactor power draw couples to the drive: the maxOutput gate and the refit-value law

Reactor mass is `powerRequirement_GW × spec_t/GW` (S14,
[Ship Mass and Delta-V Model](../mechanics/Ship%20Mass%20and%20Delta-V%20Model.md) §4), and the
reactor must satisfy `powerRequirement_GW ≤ reactor.maxOutput_GW` to power the drive at all
(`TISpaceShipTemplate.cs:521` `powerPlant.maxOutput_GW >= this.powerRequirement_GW`, enforced in
the refit-validity check at `:1482/1511` `[code]`). Two consequences decide refits:

**(1) A drive upgrade can FORCE a reactor upgrade.** If the new drive's `powerRequirement_GW`
(template field `req power`) exceeds the current reactor's `maxOutput_GW`, the shipbuilder won't
let you keep the reactor — you must upgrade the reactor tier with it, even inside the legal drive
family (S2). Reference campaign: **Firestar Fission Lantern x6 needs 882 GW; Gas Core Fission
Reactor III maxes at 150 GW** — so a Pharos→Firestar refit (same
`Fission_Thermal/Gas_Core_Fission/Hydrogen` family) is *forced* to also carry the reactor from
Gas Core III up to a tier with `maxOutput ≥ 882` (IV/V/VI = 1,650 GW). Even Firestar x2 (294 GW)
overruns Gas Core III. When a player says "the shipbuilder won't let me put this drive on," this
is why — check the drive's `powerRequirement` against the reactor's `maxOutput`.

**(2) Reactor-tier refit value scales with the drive's power draw — score it that way.** A
reactor-tier refit saves `powerRequirement_GW × (spec_old − spec_new)`, so it pays *big* on
high-thrust warship drives and *nothing* on low- or zero-draw drives:

- Lodestar (186.7 GW/thruster): Gas Core V→VI saves ~700 t/thruster (S14) — a real gain on a
  capital hull.
- Burner draws ~26 GW total: Gas Core III→VI saves ~53 t — ~1 % of a multi-kt hull, negligible.
- **⚠ Higher tier ≠ better specific power — reactor refits can ADD mass.** The same
  formula goes NEGATIVE when `spec_new > spec_old`, and that happens in the real ladder:
  Gas Core IV is **10 t/GW vs Gas Core III's 3** (template-verified — the Terawatt tiers
  trade mass efficiency for output ceiling; the ladder runs 8/5/3/10/3.5/1 for I–VI).
  This exactly reproduces R18's measured Pharos disaster: 13.35 GW/thruster × (10−3) × 6
  = +561 t of dead reactor mass. Rule: NEVER assume tier order = spec order; read
  `specificPower_tGW` from TIPowerPlantTemplate before scoring any reactor refit.
- **Self-powered NSWR drives draw ZERO reactor power for propulsion.** Poseidon Lantern
  (`NeutronFluxLantern`) has `powerRequirement ≈ 0`; its reactor only feeds weapons/systems, so a
  reactor-tier refit saves ~nothing. Reference campaign: reactor-refitting Poseidon-Lantern and
  Burner-drive ships was scored near-worthless for exactly this reason, while the same refit on
  Lodestar hulls saved thousands of tons.

Rule: before recommending a reactor-tier refit, read the ship's drive `powerRequirement` — if
it's small or zero the refit is cosmetic; spend the metals on the high-thrust hulls instead.
Combine with S2 (family legality) and run `warship_optimizer.py` for the exact before/after.


## S22 (2033-09-01 in-game; authored 2026-07-19) — Fleet build-out has FOUR possible bottlenecks; identify which binds, never assume

Before recommending "build a fleet" — or "activate the idle shipyards", or "you have MC slack,
build ships" — determine WHICH constraint actually binds this save and phase. There are four, and
it varies by campaign, by phase, and by target body. **Never hard-code the conclusion** (the
first cut of this lesson wrongly enshrined "always materials"; the mistake before that assumed
"always shipyards" — both are wrong).

1. **Materials** — metals/volatiles/exotics **stockpile + NET flow** (`resource_flow.py`). Paid
   UP FRONT at build-click (E24) from the single faction-wide pool (E32). Binds when income is
   already consumed by other construction.
2. **Shipyard / build capacity** — enough POWERED Shipyard/SpaceDock queues, AND a yard large
   enough for the hull class (capitals need the bigger yard). Binds early-game or at thin forward
   yards even when materials are flush.
3. **Mission Control** — every hull adds `missionControlConsumption`; near MC cap you can't field
   more without freeing MC first (E19/E25/E26). Binds in MC-tight saves.
4. **Tech / timing** — sometimes the right call is to WAIT. If a materially better
   drive/reactor/weapon/armor/hull, or a utility that can't be TYPE-swapped in refit later (S10),
   is ~one research cycle out, hulls laid now are obsolete you'd scrap or can't upgrade in-family
   (S2/S21). Building can be the wrong move even when materials, yards, AND MC are all free.

These stack and shift — diagnose all four, state which binds, and only then advise.

**Diagnosis checklist (run every time):**
- Materials: hull cost (S8 / `warship_optimizer.py`) vs stock; days-to-bank = (cost − stock) ÷
  **NET** flow (after the hab pipeline, not gross mining income).
- Yards: free powered queues + the max hull size buildable at the target body.
- MC: current MC slack vs per-ship consumption (top bar is truth, E25).
- Tech: is a decisively better drive/armor/weapon/hull/utility < ~1 cycle out? If so, waiting may beat building.

**Worked case — MATERIALS-bound (2033-09-01 reference save; ONE instance, not the rule).** 75 idle
shipyard queues, yet the player could not build a single hull: metals stock 1,347, gross ~576/day,
but **net only +572 over 45 days** — ~97% consumed by the hab-construction pipeline (101 Farms, 38
CommandCenters, 34 Nanofactories, …). The extractor's "latent MC demand / 75 idle yards" line
prompted the wrong "turn on the shipyards" call; the real lever was freeing the materials pool.
Had this been an early-game or MC-tight save, a different one of the four would have bound.

**The extractor now diagnoses this for you** (guard against a cold-start repeat): wherever idle
shipyards appear, `extract_snapshot.py` prints a **"Fleet build-out readiness — which gate binds?"**
table with THIS save's numbers for all four gates (materials STOCK + net flow, shipyard queues, MC
slack/pending, tech-timing), the decision rule (**compare STOCK to hull cost, not flow** — because
E24 pays up front; a naive net-flow read is itself a trap, since the 2033-09-01 7-day net metals
was +449/d while stock was 1,347 and no hull was buildable), and fires hard-gate flags
(exotics≈0 → Hybrid blocked; thin metals → bank first; MC-tight; all yards busy). Trust that block
over any glance at "N idle shipyards" or MC slack.

**Levers WHEN the binding constraint is materials:** (1) stop STARTING new hab modules so the pool
banks (E24 — in-flight builds are already paid); (2) mine-TIER upgrades (MC-free, E29); (3) source
exotics via alien raids (A3) for Hybrid armor (S12); volatiles likewise. For the other three
constraints the lever is different — build more/bigger yards, free MC (E26 levers), or wait for the
tech — which is exactly why you must identify the binding one first.

## S23 (2033-09-03 in-game; authored 2026-07-19) — Score a drive by TRANSIT TIME on real routes (eta_seconds), not raw EV — and benchmark in-role vs the player's existing drives

Two evaluation failures from the Triton Torus episode, both correctable:

**(1) Benchmark a new drive against the player's existing non-obsolete drives IN THE SAME ROLE**
— not against a flagship. Triton Torus (a logistics/transit drive) was first compared only to
Lodestar (a warship — useful only to confirm it *isn't* one) and to the one drive it superficially
resembled (Triton Fusor). But the player already flew Helicon (EV 314), Dusty Plasma (EV 3750),
Poseidon Lantern, etc. Always pull the full in-role roster first (the extractor's drive table marks
✓ RESEARCHED / ○ AVAILABLE) before judging whether a new option adds anything. Generalizes to
modules/tech: score the candidate against what the player ALREADY has in that role.

**(2) EV is a PROXY for reach, not the metric — score drives by actual transit TIME.** Time is set
by ΔV (= EV·ln massRatio) AND acceleration (= cruise thrust / mass), through the game's own
burn/coast model (`transfer_eta.eta_seconds(distance, accel, ΔV_budget)`): brachistochrone
`t=2√(d/a)` when ΔV is plentiful (**accel-limited**), else coast `t=d/v+v/a`, `v=ΔV/2`
(**ΔV-limited**). **The EV ranking routinely REVERSES once you compute time**: short/inner legs are
accel-limited (thrust wins), long/deep legs are ΔV-limited (EV wins).

Worked (reference hauler 2000 t, mass-ratio 2.5, x6 drives; representative straight-line AU;
first-principles ±, in-game planner is truth):

| Drive | EV | ΔV kps | cruise a m/s² | Earth→Ceres | Callisto→Pluto |
|---|---:|---:|---:|---:|---:|
| Triton Torus | 308 | 282 | 0.351 | **3.9 wk** 🥇 | 60 wk |
| Triton Fusor | 364 | 334 | 0.116 | 5.1 wk | **52.5 wk** 🥇 |
| Helicon | 314 | 288 | 0.060 | 7.0 wk | 62 wk |
| Dusty Plasma | 3750 | 3436 | 0.017 | 13.4 wk | 57 wk |
| Poseidon Lantern | 66 | 60 | 38.7 | 15.1 wk | 277 wk |

EV-only would rank Dusty ≫ Fusor > Helicon > Torus. Yet on the inner leg the LOWEST-EV mid-drive
(Torus) is FASTEST (3× cruise thrust dominates the accel-limited brachistochrone); on the deep leg
Fusor beats Torus and Dusty's monster EV finally pays. So "Torus has less reach than Fusor →
redundant" was WRONG: Torus is the best inner/mid hauler, Fusor/Dusty win Kuiper hauls. The right
question is "fastest on the ROUTES this fleet flies," answered by eta, not an EV column.

**Method for any drive question:** (a) list the in-role roster; (b) build/estimate ΔV + cruise
accel per drive on ONE constant reference hull (`warship_optimizer.py` if the drive family is
calibrated — it is NOT for fusion/transit families like Torus/Fusor/Helicon/Dusty without an
in-game shipbuilder reading; else rocket-eqn ΔV + cruise-thrust/mass accel, with stated error
bars); (c) run `eta_seconds` for the routes the player actually flies — an inner shuttle AND a deep
haul; (d) rank by time per route. Caveats: hold the hull constant; heavier drives leave less tank
room (lowers their ΔV — a second-order penalty the constant-mass shortcut ignores); for precision
use real save body positions via `transfer_eta.py` on actual fleets (±7%; the in-game planner is
truth). **Extends Rule zero:** for transit/logistics drive questions run `transfer_eta`, not just
`warship_optimizer`.

**⚠ The constant-hull shortcut is FIRST-order wrong for heavy-stack drives — check pair stack
mass vs the hull budget before quoting an eta (2033-09 worked case).** Helion Nova Torch on the
2,000 t reference hull "beat" Poseidon Torch Callisto→Pluto (5.0 wk vs 9.6 wk) — but its
reactor+radiator stack is **8,216 t**: it cannot exist on that hull at all. On a realistic
~12 kt super-capital its cruise accel drops to ~0.33 m/s² and the same route takes ~12 wk — the
ranking REVERSES. Meanwhile ΔV-limited coast times (v = ΔV/2) are nearly hull-mass-independent,
so light-stack/self-powered drives (NSWR: stack ≈ 0) keep their table times while heavy-stack
fusion rows are always flattered. Rule: compare `stack t` (fusion_ladder_planner) to the hull's
mass budget; if the stack doesn't fit the reference hull, re-run the eta at a hull that fits.

## S24 (2033-09-16 in-game; authored 2026-07-20) — Expedition battle fleets are DRIVE-REACH-limited; score combat g at ARRIVAL mass, and remember the 3g rating clamp

From the "bring battlecruisers to the Kuiper belt" analysis. Three portable rules:

1. **Check strategic reach before combat stats — the best combat drive may simply not arrive.**
   Lodestar (EV 31, warship ΔV ~22 kps at MR 2) needs ~13 YEARS for 30 AU: it is a home-system
   line drive, full stop. A deep-strike force is filtered first by "can it get there in campaign
   time," and only the drives that pass get compared on combat. (Reference numbers, 10 kt BC,
   MR 2.0: Poseidon Torch 12.7 wk to 30 AU; Helion Torus Lantern 32 wk; Helion Nova Lantern
   41 wk; Firestar 428 wk; Lodestar 682 wk.)
2. **Combat g = thrust / CURRENT mass — a torch that burns its transit propellant fights at
   near-dry mass.** Poseidon Torch on a 10 kt-wet BC reads 1.6g at departure but ~2.7–3.2g at
   the destination (~5–6 kt remaining). "Combat g at wet" undersells expedition torches;
   compute arrival mass for the leg actually flown. Corollary: on high-EV torches, TANKAGE is a
   design knob — shed tanks (or size dry mass) to make arrival g hit the bio cap; EV ~1,700
   keeps hundreds of kps of ΔV anyway.
3. **Weigh the g-gap through S11+S16 before paying for it:** the ship-rating mobility term
   clamps at 3g and beams are hitscan, so vs a beam-dominant enemy an expedition ship at ~3g
   concedes only engagement geometry to a home ship at a 4g+ bio cap. The cap-raise project
   ladder and high-thrustCap drives buy little for THIS role; they pay on home-defense hulls
   vs kinetic/missile threats (census the enemy mix first, R19/S16).

Doctrine shape that falls out: **two-tier fleet** — max-combat line drive (Lodestar-class) for
the home system; high-thrust+high-EV torch (NSWR-class) for expeditions, with per-fill
propellant budgeted in units (S20) since deep space has no fissile depots. Refit lock (S2)
means the expedition tier is usually NEW BUILDS, so its utility loadout must be right at first
build (S10).

## S25 (2033-10-28; authored 2026-07-21) — CHOOSING PD WEAPONS: Ion vs Arc Laser vs 40 mm — the complete rule

The single most-misplayed fit in the game. PD is not one stat — the engine splits incoming fire
into classes and each PD weapon can only engage some of them. **Pick by projectile CLASS first,
then by shot count. Never by damage.**

### The three mechanics that decide everything

1. **Any hit of any size kills a missile** (`MissileController.ApplyDamage → beenDestroyed`). PD
   only has to clear a **0.15-pt** floor (`DP_DestroyMissile`). ⇒ vs missiles, **shot power is
   irrelevant; shot COUNT, range and mass are everything.**
2. **Slugs are never killed outright — they are ERODED**, `massDamage_kg += damage_pts × 10`, and
   a survivor hits proportionally softer (`effectiveMass = warheadMass − massDamage`). Floor to
   fire is **0.5 pts**. ⇒ vs slugs, damage per second IS the stat.
3. **Only some classes may engage some targets.** Charged-dispersion particle PD (Ion, E-beam) is
   hard-locked to missiles (`CanOnlyDefensivelyTargetMissiles`); **NavalGun (40 mm) is the only PD
   that engages kinetic slugs**; beams/plasma bolts are `isPointDefenseTargetable:false` and can
   never be intercepted by anything.

### The comparison (in-game panel values, 2033-10-28)

| | **PD Ion Battery** | **PD Arc Laser** | PD Laser (older) | **40 mm Autocannon** |
|---|---:|---:|---:|---:|
| Engages missiles/torpedoes | ✅ | ✅ | ✅ | ✅ |
| **Engages kinetic slugs** | ❌ never | weak chip | weak chip | ✅ **only option** |
| **Defensive range** | **200 km** | **129 km** | shorter still | 350 km (targeting) |
| Mass | **5 t** | 20 t | 20 t | 25 t |
| Crew | **1** | 2 | 2 | 1 |
| Cooldown | **3 s** | 4 s | 5 s | 4 s (**6-shot salvo**) |
| Shot power | 5 MJ | 50 MJ | 50 MJ | 20.28 MJ ×6 |
| Energy / shot | **0.025 GJ** | 0.14 GJ | — | none (ammo) |
| Build cost | **0.38 met** | 1.3 met | — | 2000-round magazine |

### The rule

- **Default anti-missile PD = Point Defense Ion Battery.** It beats the Arc Laser on *every axis
  that matters*: 4× lighter, half the crew, faster cooldown, **55% more defensive range**, 5.6×
  less power, ~3.4× cheaper. The Arc's 50 MJ is ~300× the 0.15-pt kill floor — pure waste.
- **Always carry 40 mm for slugs.** It is the *only* anti-kinetic PD, all game. As enemies shift to
  mag/coil/rail armament the 40 mm stops being optional — an all-laser/all-Ion screen is defenceless
  against thousands of inbound rounds. Keep at least one on any line ship.
- **PD Arc Laser is the compromise pick**, worth taking only when you want one mount that can do a
  bit of both (missiles + weak slug chip) or you have mass/hardpoints to spare. **PD Laser (non-Arc)
  is strictly dominated by the Arc** — never build it once Arc is researched.
- **Beams and plasma are ARMOR's problem, not PD's.** Do not buy PD to answer them.
- **Ratio comes from the enemy, not from taste**: count their missile/torpedo bays vs their
  mag/coil batteries and size each channel — `counter_fleet_planner.py` does this arithmetic (S26).

### Two traps that produce backwards advice

- **`targetingRange_km` is the ATTACK envelope, NOT PD reach.** The Arc Laser's template says
  `300`, but its panel reads **129 km defensive**, because laser PD range is *damage*-limited —
  spot area grows as range², so damage drops under the 0.15-pt floor long before the envelope ends
  ([Space Combat Math](../mechanics/Space%20Combat%20Math.md) §2.2/§3). The Ion's 200 km template
  and 200 km defensive agree. Comparing template fields makes the Ion look shorter-ranged when it
  actually **out-ranges the laser by 55%**. Read the designer panel.
- **TORPEDOES ARE MISSILES.** Torpedo bays live in `TIMissileTemplate.json` and route through
  `MissileController`, so "Ion only targets missiles" does **not** exclude them — one Ion hit kills
  an Iridescent Star torpedo outright. The "useless vs penetrator torpedoes' kinetic mass" caveat
  refers only to MASS EROSION, which you never need against something you can destroy in one hit.

### Fit notes for a dedicated PD screen

- **Drop the Targeting Computer** — PD screens are ECM-proof (ECM applies only to ship targets;
  projectiles have no ECMValue). Spend the slot on a heat sink.
- **Laser Engine is near-worthless here**: defense-only mounts get **half** the bonus
  (`GetBonusPowerForWeapon_MJ`: `!attackMode → ×0.5`) and range scales as √power, so +10% power
  buys ~+5% range. It's for *attack* lasers.
- **Size the heat sink to actual waste heat**: `shotPower × (1/efficiency − 1)` per shot × shots per
  battle. Four Arc turrets over a 10-minute fight ≈ 56 GJ, so a 525 GJ Lithium sink is ~9× over-spec;
  guns add ~none (efficiency 1.0). Don't over-buy — heat sinks set burst endurance, never peak g (S11).

## S26 (2033-10-28; authored 2026-07-21) — Counter-fleet design: split the enemy into THREE PD channels and size each with arithmetic

Do not eyeball "more PD". Decompose the specific enemy fleet into the three channels the PD system
treats differently, then size each with the verified constants. Tool: **`counter_fleet_planner.py
<save> --fleet "<name>" --screen-hulls N`** (prints the decomposition and the required mount counts).

| Channel | Killed how | Counter | Sizing formula |
|---|---|---|---|
| **Missiles / torpedoes** | **ANY hit kills** (`MissileController`) | **PD Ion** (cheapest shot) | `mounts ≥ Σ(salvo/cooldown) ÷ PD shots-per-sec` |
| **Kinetic slugs** | eroded, `massDamage_kg += pts × 10` | **40 mm only** (NavalGun) | `mounts ≥ Σ(warheadMass × salvo ÷ cooldown) ÷ per-gun kg/s` |
| **Beams / plasma** | **uninterceptable** | **ARMOR** (match plate to damage type) | n/a — PD does nothing |

Per-gun erosion = `(damage_MJ ÷ 20) × 10 kg × salvo ÷ cooldown`; ~20 MJ = 1 damage point. The
40 mm = `(20.28/20) × 10 × 6 ÷ 4` = **15.2 kg/s**. PD Ion = 1 shot / 3 s = **0.333 kills/s**.

**Worked case — Victor-72 (9 alien ships, arriving Callisto 2034-05):** 10 torpedo bays →
**1.25 launches/s**; 5 mag mounts (2× Adv. Mag Cannon 72 kg, 3× Adv. Mag Battery 27 kg) →
**57.8 kg/s** inbound slug mass; 9 beam mounts (armor's problem); **their** PD only 6 mounts.
⇒ need **≥ 3.8 Ion** and **≥ 3.8 autocannon** fleet-wide. Spread over 6 screen hulls that is a
**1 Ion + 1 gun per hull MINIMUM**; the built answer (6 × `Aegis-PD` Monitor with 3 Ion + 1 gun =
18 Ion / 6 guns) carries 4.7× and 1.6× margin for misses and firing geometry.

Two judgement rules the arithmetic doesn't give you: **erosion is proportional** (a partly-stripped
slug hits proportionally softer — `effectiveMass = warheadMass − massDamage`), so partial anti-slug
coverage still pays linearly; and **NavalGun saturation caps at 4 engagers per projectile**, so past
~4 guns extra value comes from engaging MORE slugs at once — which favours spreading 1 gun across
many hulls over stacking 4 on one. Corollary in the other direction: a LOW enemy PD count is your
own missile opening (Victor-72's 6 PD vs the player's 38 launchers).

## S27 (2026-07-21) — In the Ship Designer the NOSE IS ON THE RIGHT; never read the armor triplet left-to-right as nose→tail

**Recurring analyst error — caught by the player three times.** The designer's three armor pentagons
are laid out **tail (left) · lateral (middle) · nose (RIGHT)** — the nose is on the same side as the
nose-weapon mounts. Reading them left-to-right as "nose/lateral/tail" inverts the ship: a correct
`nose 70 / lateral 1 / tail 10` build gets misread as a nonsensical `nose 10 … tail 70`, and the
analyst then "corrects" a design that was already right. **Always confirm orientation against the
nose-weapon side (or the save's `noseArmor`/`lateralArmor`/`tailArmor` fields, which are unambiguous)
before commenting on armor allocation.**

Same family of error: **read the construction-cost ROW ICONS, don't guess by position.** A trailing
`1.9` next to the radiation glyph is **fissiles**, not exotics — mistaking it produced a bogus
"exotics will cap you at one hull" warning when the design used zero exotics. When a cost line
matters, ask the player which resource the icon is, or pull the design's `weightedBuildMaterials`
from the save.

## S28 (2033-10-25 in-game; authored 2026-07-30) — Ship build TIME is hull-only; mass, armor and cost never change it

**Player correction — do not repeat the "trim it to build it faster" advice.** Construction time comes
from one flat template field, `TIShipHullTemplate.baseConstructionTime_days`:

| Hull | base days | Hull | base days |
|---|---:|---|---:|
| Gunship | 60 | Cruiser | 180 |
| Escort / Corvette | 90 | **Battlecruiser** | **180** |
| Frigate / **Monitor** | 120 | Battleship | 200 |
| Destroyer | 135 | **Lancer** / Dreadnought | **240** |
| | | Titan | 270 |

(Alien hulls for reference: AlienGunship 64 · AlienFrigate 128 · AlienMonitor/Destroyer 256 ·
AlienCruiser 320 · AlienBattlecruiser/Battleship/Lancer 360 · AlienDreadnought 480.)

**Nothing about the loadout enters.** Armor points, tank count, weapons, wet mass and construction
COST are all irrelevant to the day count — two designs on the same hull take the same time whether
they weigh 27 kt or 45 kt.

**The three numbers are the yard TIERS** — SpaceDock / Shipyard / Spaceworks,
`TIHabModuleTemplate.constructionTimeModifier` = 1.0 / 0.8 / 0.6 (alien: 1.0 / 0.75 / 0.5).
Calibrated on an EMPTY Battlecruiser (base 180) reading **205 / 137 / 82** (2033-11-20 screenshot):

    displayed_days ≈ base_days × (1.139 / 0.761 / 0.456)     # t1 / t2 / t3

Cross-check that also proves the proportionality to `baseConstructionTime_days`: ×4/3 gives a Lancer
273 / 183 / **109**, and the same campaign's Lancer read **410 / 274 / 182** a month earlier — the
identical ladder shifted one column, from before its Spaceworks existed. Matched columns agree to
within a day, so hull base days scale the whole row exactly.

⚠ **Two unresolved gaps — treat the factors as campaign-calibrated, not universal.** The column
ratios are 1 : 0.667 : 0.400, which the yard modifiers alone (1 : 0.8 : 0.6) do not produce; they
match the yard modifier × the matching construction-module modifier (ConstructionModule 0.9 /
Nanofactory 0.75 / NanofacturingComplex 0.6 → 0.9 : 0.6 : 0.36 = 1 : 0.667 : 0.4) exactly, which is
the likely mechanism but is unverified. And a constant ≈1.266 sits between that template product and
the displayed days (205 = 180 × 0.9 × 1.266), source unidentified. **Re-read one empty hull's triple
after any yard or construction-module change** rather than trusting the stored factors.

**Design implications:**
1. To field a hull SOONER, drop a hull CLASS — never tonnage. Trimming lateral armor or propellant
   tanks buys resources, ΔV, combat g and MC support; it buys **zero days**.
2. Time-to-theater per unit of capability favours the smaller hull twice over: fewer days AND
   cheaper armor points (nose t/pt scales with the hull's end-cap area — Battlecruiser 21.1 vs
   Lancer 55.1 on Adamantane), so a BC often out-armors a Lancer that was never built to its cap.
3. Bound it by what the hull can MOUNT, not by days: a Monitor is 120 days but cannot take a 3-nose
   cannon, so it is not a base-cracker at any schedule (see [Orbital Bombardment](../mechanics/Orbital%20Bombardment.md) § laser sizing).

**Tooling:** `python3 scripts/warship_optimizer.py --build-times` prints the whole ladder (base days
+ all three yard tiers) from the templates; `hull_build_days(hull, tier)` is importable. Use it
instead of quoting days from memory.

**Analyst caveats:** REFITS are a separate, much faster path (in-queue examples run 1.3–19.4 days) —
never compare a refit ETA to a new-build ETA. And when a player-reported number doesn't fit your
ladder, **the ladder is the suspect, not the player**: "a Battlecruiser in 82 days" was dismissed
here as probably-a-Monitor-refit when it was a straight BC reading, and it was the tier factors —
back-solved from a single triple taken before that campaign had a Spaceworks — that were wrong. Ask
for the screenshot before theorising a cost term into the model.

## S29 (2033-11-09, player ground truth) — A hab's DEFENDING FORCE is bigger than its marine modules; read the HABS list, don't reconstruct it

Planning a mine capture with a 6-marine ship, the analyst reconstructed Leibniz Base's ground
defence from its modules: one **Marine Company Barracks**, `specialRulesValue` 20 → defence 20.
The player's in-game HABS list read **23**, and the module tooltip confirmed the barracks' own
"Combat strength: 20". So the module sum **under-reads the real defending force** — by 3 on this
tier-3 colony (1,103 population). One data point, so no formula is claimed; the residual is
plausibly a per-hab or population floor.

Rules:
1. **The HABS list's defence/marine columns are ground truth** and the game shows them for RIVAL
   habs even at intel 0.1 (verified: Leibniz at intel 0.1 displayed 14 / 23). A module-derived
   estimate is therefore not privileged information — but it is an estimate, and it reads LOW.
   `capture_target_planner.py` now plans against `module_sum + 3` and prints the caveat.
2. **Plan the marines you must BRING, not the odds you happen to have.** With
   P = 1 − 0.5 × 0.775^(attacker − defender): parity = 50%, +3 = 77%, +6 = 89%, +9 = 95%. Against
   Leibniz's 23 that means ~29 marine value for a near-sure thing — five times the 6 aboard a
   single Mjolnir. Sort capture candidates by what you can actually take today; a 470 vol/mo prize
   you lose your marines against is not a plan.
3. The raw assault expression goes hugely NEGATIVE when the defender out-numbers the attacker
   (−8083% at 6 vs 20). Clamp to [0,1] — that is a 0% capture, not a negative probability.

## S30 (2033-11-09, player ground truth) — Rank operations by ETA, never by distance; and check the RETURN ΔV

Recommending capture targets, the analyst sorted by straight-line AU and led with 46 Hestia
(4.89 AU) and 97 Klotho (4.92 AU). The player opened the in-game transfer planner: **46 Hestia
38.62 weeks, 97 Klotho 49.27 weeks** — 8.9 and 11.3 months — and replied *"46 Hestia is far.
97 Klotho is farther. you didn't seem to have checked the time-to-travel."* An equivalent target
(Pushkin Base, 56 Melete) was **2.7 months** away. Three months of a 584/mo site is ~1,750
resources; six months of ranking error costs more than any yield difference on the list.

1. **Distance is not travel time and the two do not even rank the same.** ETA depends on the
   fleet's acceleration and ΔV budget, and a low-thrust hull is accel-limited, not
   distance-limited. Any tool that ranks destinations MUST print ETA — `transfer_eta.eta_seconds`
   is importable for exactly this. `capture_target_planner.py` now ranks on it.
2. **Calibration of the straight-line model vs the in-game planner** (same day, same fleet,
   182.3 mg, 52.4 kps): 46 Hestia 10.9mo modelled vs 8.9mo actual (**+22%**), 97 Klotho 11.0 vs
   11.3 (**−3%**), 56 Melete 2.7mo modelled and accepted. ΔV matched to 1% (51.1 modelled vs
   51.0 / 51.9). So the model is a SCREEN with roughly ±25% error on long legs — it ignores
   orbital phasing and launch windows entirely. Never quote it as a plan; shortlist with it and
   read the real number off the in-game planner.
3. **Check what ΔV the ship has LEFT on arrival.** Every candidate on that list spent 51.1 of
   52.4 kps getting there — one-way trips. A capture that strands the assault ship at the target
   is a decision, not a detail; say so before the player commits.
