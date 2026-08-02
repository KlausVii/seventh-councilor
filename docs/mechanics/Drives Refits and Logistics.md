---
title: Drives Refits and Logistics
game_version: 1.0.32 decompile (build 22085164; decompile repo brackets 1.0.30–1.0.33); lessons re-verified through 1.0.38+
---

# Drives, Refits and Logistics

Verified drive/refit/refuel rules and transit math from the Phase-3 adversarial review (2026-06). Campaign-independent rules first; current-campaign numbers appear only as labeled examples from the reference campaign (Normal difficulty, in-game 2032-05).

> **Evidence caveat (applies to every citation below):** decompiled-source evidence is from a repo vintage bracketed **1.0.30–1.0.33** (sole commit dated 2025-06-12); template evidence is from the installed build's own JSON (build 22085164 = v1.0.32 public). Constants could drift in newer builds — **re-verify after any game patch** (templates via `sync_game_data.py`, code via the decompile repo if updated). Citation tags: `[code]` decompiled C#, `[tpl]` template JSON, `[save]` save-file empiric, `[calc]` phase-3 computed from cited inputs.

## 1. The refit rule (code-exact, high confidence)

A built ship can refit a part only under these constraints:

| Part | Refit legality condition | Evidence |
|---|---|---|
| **Drive** | new drive matches old drive's **driveClassification AND requiredPowerPlant AND propellant** (all three) | `TIDriveTemplate.cs:526-529 IsValidRefitPart` `[code]` |
| **Reactor** | same **powerPlantClass** | `TIPowerPlantTemplate.cs:112` `[code]` |
| **Hull** | **immutable** — never refittable | `TISpaceShipTemplate.cs:1834-1868 IsAValidRefitFor` (hull equality) `[code]` |

Consequences:
- **Cross-family drive transitions are impossible** — switching chains (e.g. fission → fusion → antimatter) always means new construction. "Switch to antimatter lategame" via refit does not exist.
- Commit to 1–2 drive chains; redundant drive lines are pure RP waste (no drive tech appears in any victory-required closure `[tpl]`).
- The refit "family" is **wider than a name-line**: ALL drives sharing `Fission_Thermal / Gas_Core_Fission / Hydrogen` are mutually refittable — **Burner ↔ Firestar ↔ Lodestar ↔ Pharos ↔ Flare ↔ Quartz ↔ Lightbulb** all legal `[tpl]`. Burner is a safe early buy: it upgrades in place all the way up the fission ladder.
- **NeutronFluxLantern → NeutronFluxTorch is a legal refit** (both `NuclearSaltWater / Any_General / Water`) `[tpl]` — NFL hulls are future-proofed for the Kuiper-tier torch.
- Reactors upgrade in place within a class: GasCoreFissionReactor I–VI are one `powerPlantClass` (IV+ carry the "Terawatt" branding) `[tpl]`.
- **A fourth constraint beyond the family match: `drive.powerRequirement_GW ≤ reactor.maxOutput_GW`** (`TISpaceShipTemplate.cs:521/1482/1511` `[code]`). So a same-family drive *upgrade* can FORCE a reactor-tier upgrade: reference campaign — Firestar's 882 GW (x6) can't run on Gas Core III's 150 GW cap, so the legal Pharos→Firestar refit drags the reactor to Gas Core IV+ (1,650 GW). And reactor-tier refit *value* scales with that same `powerRequirement` — huge on Lodestar-class draws, ~nothing on self-powered NSWR drives (Poseidon Lantern draws ≈0). Decision rules in [LESSONS-ships](../lessons/LESSONS-ships.md) S21.

## 2. The cooling rule — and the community's recurring radiator error

`openCycleCooling = (cooling == Open) || (cooling == Calc && (pulsed || massFlow ≥ 3 kg/s))` (`TIDriveTemplate.cs:254-258` `[code]`).

**Radiator mass derives from REACTOR (power plant) inefficiency, NOT drive efficiency**: `WasteHeat_GW = max(crewHeat, requiredOutput) × (1 − reactor.efficiency)`; for open-cycle drives the reactor heat is vented with the propellant and radiators are sized for crew heat only (`3.75 × crew / 1000` — negligible) (`TIPowerPlantTemplate.cs:67-81`; radiator sizing at `TISpaceShipTemplate.cs:2832` `[code]`).

- **REFUTED (recurring community error):** drive-ranking tables that compute radiator mass from drive efficiency (e.g. the conKORDian Reddit engine analysis) systematically **understate open-cycle / high-massFlow drives** and overrate closed-cycle sustained-cruise chains. Re-compute before trusting any community powertrain-mass ranking.
- Example of the rule in action `[tpl][calc]`: AntimatterPlasmaCoreTorch is `Calc` with massFlow ≈ 3.1 kg/s ≥ 3 → effectively **open-cycle** (one of the few late-game open-cycle drives); AdvancedAMPlasmaCoreTorch has massFlow 1.11 → **closed-cycle**, needs real radiators (the "~50% radiator-mass titan" anecdote is plausible for it).

## 3. Warship figure of merit

- **Combat thrust = cruise thrust × thrustCap** (burst multiplier). Rank warship drives by **combat-thrust × √EV**, never by cruise numbers — full lesson in the lessons library (§drive recommendations).
- Examples `[tpl]`: Lodestar 66 MN × 20 = **1,320 MN** combat (×6, the fission warship king); Firestar 30 × 22 = 660 MN (but EV 50 vs Lodestar 31.4 — its value is legs, not guns); Pharos 5.34 × 16 = 85 MN; **NeutronFluxLantern/Torch thrustCap = 2** → transit drives, never warship drives despite huge cruise thrust.
- Low thrustCap (≤ ~2–5) = logistics/cruise drive regardless of other stats. High-thrustCap fusion (Triton tier thrustCap 25–40) is what makes real outer-system warships.
- Save-empiric refinement (from `warship_optimizer.py`, see the lessons library): **effective thrustCap ≈ 0.55 × nominal without a heat-sink module** — combat-g projections must include the heat-sink multiplier.

## 4. ISRU & refueling rules (code-exact)

- Exactly **4 drives have `freeISRU: true`** (self-refuel from raw sites with no module): **E-Beam Drive, Pulsed Plasmoid Drive, Mass Driver, Superconducting Mass Driver** — all `Anything` propellant `[tpl]`.
- The **ISRU utility module** grants `RefuelFromUnimprovedSites`: refuel from a raw hab site without any hab present (`TISpaceShipState.cs:5257-5262 CanRefuelFromHabSite` `[code]`).
- Refuel rate = the site's daily resource production, with a **hard 90-day cap per refuel operation** (`ResupplyOperation.cs:344-360` `[code]`) — a poor site gives you 90 days' worth, not a full tank.
- **The whole fleet refuels in parallel**: operation completion time = max over ships, not sum (`SetCompletionTime_Days(max)` `[code]`).
- **ISRU modules cannot pair with antimatter-propellant drives** (`TISpaceShipTemplate.cs:1452`: requires perTank antimatter ≤ 0) `[code]`.

## 5. The scoop rule (atmospheric refueling)

`CanRefuelFromJovianAtmosphere` (`TISpaceShipState.cs:5241/17062` `[code]`): requires interface orbit at a **Massive-atmosphere body** + drive propellant == **Hydrogen** + per-tank mix **100% water/volatiles** (or `Anything`).

- Late-game qualifiers `[tpl]`: **DeuteronTorus** (tokamak, EV 769), **ProtiumTorusLantern** (tokamak, EV 952), **DeuteronReflexDrive** (mirror cell, water 1.0). **"Tokamaks are the only scoop drives" is overstated** — the Reflex qualifies too.
- Fail the rule: all Helion variants (0.1 fissiles in mix), Z-pinch (ReactionProducts propellant — genuinely scoop-incompatible), Fusor, NSWR (wrong propellant), every antimatter drive.

## 6. Propellant-mix gotchas (per-tank weights, template-exact)

Constants: propellant tank = **100 t**; 1 resource unit = 10 t (`spaceResourceToTons = 0.1`) → a tank = 10 resource units `[code][tpl]`.

| Drive | Per-tank mix (weight) | Gotcha |
|---|---|---|
| NeutronFluxLantern | water .65 / volatiles .15 / **fissiles .20** | manageable fissile burn |
| **NeutronFluxTorch** | water .25 / volatiles .15 / **fissiles .60** | **3× more fissile-hungry than NFL** — "the torch was buffed to need fewer fissiles" is NOT this build's template. Burn discipline + fissile income required |
| NSWR family | 20–60% fissiles | no fissile income → no NSWR/Orion fleets |
| **PionTorch** | water .5 / **antimatter .5** | **5 AM units per tank** ≈ never affordable; rated zero correctly |
| AMPCT | antimatter 4.1e-5 | trivial AM/tank; EV 820 (NOT ~300 — that's the AMPCL Lantern, EV 360) |
| AAMPCT | antimatter 2.2e-4 | = **0.0022 AM units/tank** (the community's "0.0022 mass fraction" is 10× off) |
| Alien drives | water 1.0 | aliens burn pure water; salvaging them yields no AM |

**Water is the universal resupply FEEDSTOCK — not just NSWR.** The `propellant` TYPE field (Hydrogen / NobleGases / Water / ReactionProducts) is NOT what you pay to refuel — `perTankPropellantMaterials.water` is, and it's ~0.65–1.0 water/tank for nearly every drive: Lodestar/Pharos/Firestar/Pulsar say "Hydrogen" but cost ~**0.98 water/tank**; Helicon "NobleGases" ~0.9; NSWR "Water" 0.65 (the hab cracks water into the actual propellant). So the ENTIRE fleet bills water at resupply ≈ `tanks × waterPerTank × 10` per full refill. *(Corrects "Lodestar is a hydrogen drive" for logistics: the tank holds hydrogen by MASS, the resupply RESOURCE is water.)* **Fleet resupply from stockpile is therefore the dominant WATER sink** — the `ResupplyOperation` + `ResupplyAndRepairOperation` ledger lines — and it scales with operational TEMPO, not idle draw, so a mobile fleet's water bill hides behind healthy idle days-cover. A water crash is almost always fleet resupply, not a mining shortfall: attribute it with `resource_flow.py`, and identify which fleets by docked station + `hab.orbitState` → `TIOrbitState.displayName` (fleets carry no useful name — all "GenericFleetTemplate"). *(code+tpl, high confidence; 2032-11 Resistance: 85/90 ships water-propellant; a 16-ship Lodestar-drive class ~3,920 + a 4-ship 70-tank NSWR class ~1,820 the top draws)*

## 7. Transit-class table: dV class → reachable targets

Model: flat-space burn-coast-burn, one-way to the Kuiper belt (~50 AU; e.g. Haumea 50.3 AU). **Caveat: TI's real Lambert/porkchop planner differs ±20–30%, and sub-escape coast speeds are far worse than the flat model suggests** `[calc]`. Solar escape velocity ≈ **42.1 kps at 1 AU** — the hard line.

| Usable dV class | What it can do | Example drives |
|---|---|---|
| 16–29 kps | **inner system only** — below solar escape; literally cannot make an outer-system trip | Lodestar warship fits (e.g. the player's 2032-05 fleet avg 38 kps vs alien 648 `[save]`) |
| ~80 kps | minimum practical outer-system | first stretch fission high-EV fits |
| 200–400 kps | Kuiper in **1.2–2.5 yr** | first-gen fusion (Triton tier) |
| 800–1400 kps | Kuiper in **0.4–1.2 yr** | NFT-class, D-D fusion |

Specific one-way times to ~50 AU `[calc]`: **Helicon (EV 314) at 65% propellant ≈ 1.8–2.4 yr** (assault-tug/logistics only — ~2.4 MN ×6 combat); NeutronFluxLantern ≈ 8 yr; Firestar ≈ 10 yr (orbital-defense drive, not a Kuiper drive); **NeutronFluxTorch (EV 1700, 13 MN, open-cycle, Any_General reactor) ≈ 0.4–0.6 yr**.

Strategic constant: a Kuiper campaign is **infeasible pre-fusion** (or pre-NFT). Plan research accordingly before any "go kill the alien home base" timeline.

## 8. RP closures for the drive ladder (from-scratch; recompute remaining vs your save)

| Buy | Headline cost | Full prereq closure | Notes |
|---|---|---|---|
| **Project_HeliconDrive** | 1,500 RP | **34,500 RP** | EV 314, noble-gas propellant, ANY reactor; cheapest high-EV logistics drive in the game |
| **DeuteriumTritiumFusion** (tech) | 50,000 RP | **150,250 RP** (16 nodes) | gates the entire fusion ladder. Closure transitively includes the GLOBAL techs HighEnergyLasers (1k) + ParticleCannon (5k) via Neutronics — "skip particle weapons" means skip the weapon PROJECTS, not these globals `[tpl]` |
| **Project_NeutronFluxTorch** | 150,000 RP | **437,750 RP** from scratch | one of the most expensive drive buys; no new reactor class needed (Any_General); NFL ships refit to it legally (§1) |
| Magnetics trio: HTS 40k + MagneticPlasmaConfinement 35k + MagneticNozzles 50k | — | **125,000 RP** | gates EVERY outer-system drive (and HTS doubles as the coilgun-chain gate) — buy once, unlock both ladders |

- e.g. the reference campaign, 2032-05 position `[save][calc]`: NFT remaining = 275k (project 150k + the magnetics trio); Triton-tier warship drives 207–264k each remaining (TritonTorus 210k, TritonPolywell 207.5k, ZetaTriton 245k, TritonNova 264k → 1.8–2.5 yr transits, thrustCap 25–40); DeuteronPolywell (D-D) 320k; DT-Fusion itself was queueable immediately (both prereqs done). At the player's 272 RP/day income, closures translate to years — sequence the magnetics trio early.

## 9. Misconception graveyard (do not resurrect)

| Myth | Status | Truth |
|---|---|---|
| Radiator mass follows drive efficiency | **REFUTED** | reactor inefficiency; open-cycle vents reactor heat with propellant (§2) |
| Rank drives by cruise thrust / payload at 0.01 g | **REFUTED** for warships | combat = cruise × thrustCap; rank by combat-thrust × √EV (§3, the lessons library) |
| "Tokamaks are the only late scoop drives" | overstated | DeuteronReflexDrive also qualifies (§5) |
| AAMPCT burns 0.0022 AM mass-fraction/tank | **REFUTED** | 0.00022 weight = 0.0022 AM units/tank (§6) |
| AMPCT has ~300 kps EV | **REFUTED** | AMPCT EV 820; the Lantern (AMPCL) is EV 360 — name confusion (§6) |
| NFT was buffed to need fewer fissiles | **REFUTED** on this build | per-tank 60% fissiles, 3× the NFL (§6) |
| Lategame fleets can refit across drive families | **REFUTED** | refit triple is absolute; new construction only (§1) |
| Z-pinch can scoop | **REFUTED** | ReactionProducts propellant fails the Hydrogen rule (§5) |
| NFL/NFT are warship drives ("huge thrust") | **REFUTED** | thrustCap 2 → transit drives (§3) |

Cross-checks: ZetaDeuteronTorch ×6 supports ≈44 kt at 0.01 g cruise (freight metric, verified `[tpl]`) — fine for haulers, irrelevant for warships.

See also: [Space Combat Math](Space%20Combat%20Math.md) (what the fleet does when it arrives), the lessons library (`docs/lessons/LESSONS-ships.md` — optimizer + FoM lessons).
