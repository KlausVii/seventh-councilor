---
title: Capital Ship Doctrine
game_version: 1.0.32 (build 22085164)
---

# Capital Ship Doctrine

> **Evidence vintage caveat (applies to all code citations in this note):** decompiled-source evidence is from a repo bracketed to builds 1.0.30–1.0.33 (commit 2025-06-12). Constants could drift in newer builds — re-verify after any game patch (templates via `sync_game_data.py`; code via the repo if updated).

## Verdict (expanded)

### The battle cap is the real argument for capitals

Default in-combat ship cap = **30 total** (`TIPlayerProfileManager.maxShipsInCombat`, a player-profile slider, max 90 — the community's "~40" is REFUTED). Each side's share = `clamp(yourShips/totalShips, 1/3, 2/3) × 30` → **10–20 ships per side**. Inside a fixed slot budget, bigger hulls = more firepower per slot. That — not MC efficiency — is why capitals matter.

**Corvette filler (verified mechanism):** bringing ~100 cheap hulls pushes your share to the 2/3 cap (20 of 30) and **starves the enemy side down to 10**, so your capitals always outnumber inside the instance. Corvettes cost 1 MC each. (The companion trick "re-roll until the alien AI picks a bad tactic" is unverified.)

### Hull table (template-verified)

| Hull | Nose | Hull HP | SI | MC | consTier | Build days | Hardpoints/MC |
|---|---:|---:|---:|---:|---:|---:|---:|
| Corvette | 1 | — | 10 | 1 | 1 | — | filler |
| Monitor | 0 | 4 | 22* | 2 | — | — | 2.00 |
| Battlecruiser | 3 | — | 24 | — | 2 | 180 | big nose slots without capital mass |
| Battleship | 2 | 6 | 40 | 3 | 3 | 200 | 2.67 |
| Lancer | 4 | 3 | 36 | — | 3 | 240 | — |
| Dreadnought | 3 | 8 | 48 | 4 | 3 | 240 | **2.75** |
| Titan | 4 | 6 | 64 | 5 | 3 | 270 | 2.00 |

*Monitor SI from alien analog; human Monitor = 4 hull hardpoints at 2 MC — cheapest broadside platform. Alien references: AlienTitan 6n/8h SI 90; AlienMothership 4n/16h SI 512. Utility slots: Titan 9, Dreadnought 7 (not 8/6 as the community thread had it); Titan = Lancer +3 hull/+2 utility.

**Hardpoints-per-MC peaks at Dreadnought (2.75) and Battleship (2.67); Titan ties Monitor (2.0)** — "capitals give more firepower per MC" is false as stated; it's true per battle slot.

### The aperture finding — Lancer is the cheap capital

960 cm-class lasers are **FourNose** mounts, and the human hulls with 4 nose hardpoints are **LANCER and TITAN** — the community's "960 cm is Titan-only" is wrong. Since aperture quarters effective enemy armor vs a 480 cm at equal range ([Weapon Doctrine vs the Hydra](Weapon%20Doctrine%20vs%20the%20Hydra.md)), the Lancer is the cheapest path to a long-range laser capital; Titan's edge is utility slots (more stacked Laser Engines) and SI.

### The endgame meta, priced

"960 cm UV Phaser + Siege Coiler Mk3" is template-real (UV Phaser: 400 MJ/10 s/1000 km, penetrates 25 armor at full range, ~5 % exotics in build mix ≈3.6 exotics/gun; SpinalSiegeCoilerMk3: FourNose, 875 kg, ~410+ pts, ≈6 exotics; HeavySiegeCoiler ThreeNoseAngle 656 kg). PD survivability: damage points = MJ/20, each point strips 10 kg from magnetic slugs, alien PD laser = 64 MJ = 32 kg/hit → CoilCannon round dies in ~2 hits, **siege-coiler rounds take 21–28 hits** — only capital-grade rounds survive alien PD density. Small lasers (60 cm: armor-5 ceiling at 82 km) and light coilguns (~6.5 pts) are genuinely useless vs 100+ noses.

### When capitals matter at habs

A defended hab fights with its modules: hab SpaceCombatValue = Σ active (functional && powered) combat modules, and **fleets can only land at an enemy hab site when its SCV ≤ 0** — capital bombardment is the tool that zeroes battlestation-class defenses (modules need only be de-powered or destroyed; killing power modules zeroes SCV too). Ground side: hab defense = coreTier + Σ marine-rule values × adviser multiplier (AlienCitadel counts TWICE = 96 each — Salamanders+WarDogs both match; no flat 6× multiplier exists); assault success P = 1 − 0.5 × 0.775^(attacker − defender) (full curve and HQ-scale numbers: [Victory Conditions and Endgame](../mechanics/Victory%20Conditions%20and%20Endgame.md) §5). Bombard-then-assault collapses marine requirements (e.g. alien HQ ≈530 defense → ≈37 after bombardment, ~6 Elite Marine Assault Units instead of ~68).

### What victory does NOT need

The win mission (Close the Gate / ResistWin) has **no hull-class condition anywhere in its chain** — conditions are TargetInRange + Human + AllVictoryConditionsMet, target is the AlienWormhole hab module. An all-missile Monitor anecdote beating Brutal is unverifiable but mechanics-consistent. Capitals are an efficiency choice, not a requirement.

### Refit discipline (binding constraint on capital programs)

Drives refit only within the same classification/reactor/propellant family; hulls are immutable. A capital line committed to one drive family rides reactor upgrades in place (GasCoreFissionReactor I–VI are one `powerPlantClass`) but can never cross chains — plan hulls around the drive endgame, not current drives. See [Research Skips](Research%20Skips.md) and [Drives Refits and Logistics](../mechanics/Drives%20Refits%20and%20Logistics.md).

## Evidence

**Tier 1 (code/templates, verified):** `TIPlayerProfileManager.cs:943` maxShipsInCombat=30; `SpaceCombatManager.cs:473–491` per-side clamp + reinforcement; `TIShipHullTemplate.json` (all hull stats, missionControl, shipModuleSlots, baseConstructionTime_days); `TIShipHullTemplate.cs:120–146` armor-depth caps; `TILaserWeaponTemplate.json` 960cm entries (FourNose) incl. 960cmGreenArcLaserCannon `requiredProject=Project_240cmGreenArcLaserCannon`; `TIMagneticGunTemplate.json` siege coilers; `ProjectileController.cs:436` 10 kg/pt erosion; `TIHabState.cs:1187` hab SCV = active modules; `LandOnSurfaceOperation.cs:74` SCV≤0 landing gate; `AssaultHabOperation.cs` success curve; `TIShipHullTemplate.json` Corvette MC=1. *(high)*

**Verdict provenance:** BC/Lancer meta facts VERIFIED; hull stats VERIFIED; capital-MC claim MODIFIED (per-slot not per-MC); corvette filler VERIFIED (mechanism); "fleet cap ~40" REFUTED (30 default); "960cm Titan-only" REFUTED (Lancer fits); endgame meta MODIFIED (real but ~458k RP + exotics away for this run); platform-kit marine-spam recipe REFUTED as current mechanic (capture of alien habs is loot-then-destroy; victory needs no assault).

**REFUTED myths:** ~~"Default battle cap ≈40"~~ (30, slider to 90) · ~~"Capitals give more firepower per MC"~~ (per battle slot) · ~~"960 cm lasers need Titan"~~ (Lancer = 4 nose) · ~~"Capture and operate the alien HQ"~~ (alien-hab capture always destroys).

## Worked example — the reference campaign (Resistance, 2032-05 snapshot)

- **Buildable-today capital (the practical finding):** Lancer hull is unlocked NOW (`Project_ShipsoftheLine` finished) and `Project_240cmGreenArcLaserCannon` (finished) also unlocks the **960cmGreenArcLaserCannon** (FourNose, 400 MJ/20 s, 1000 km, **zero exotics**). A Lancer + 960 cm Green Arc + Lodestar-family drive is a zero-new-research capital available immediately.
- The UV-Phaser/Siege-Coiler meta is ≈458k unique RP away (Siege Coiler chain 140k: Coilguns 30k → HTS 40k → Ultracaps 40k → CoilCannon Mk1/2/3 30k; 960 UV Phaser +148k; Titan hull +170k) plus exotics the player lacks (3.6–6/gun vs 5.8 stockpile, 0 income — [Exotics and Antimatter Acquisition](Exotics%20and%20Antimatter%20Acquisition.md)). FleetLogistics (in the Titan chain) double-counts toward the 4th hate mask.
- Default profile cap 30 applies to the player's battles; corvette filler is available at 1 MC each against 10–20-ship alien instances.

## Sources

- https://www.reddit.com/r/TerraInvicta/comments/1s5qu49/what_are_titans_and_dreadnaughts_for/
- Steam discussions 3810659147975989411 / 4355620138226308499 / 767435762118452561 — single-community caveat: contains ≥1 verified material error (the Titan-only claim)
- Decompile: https://github.com/Armandox33/Terra-Invicta-AI-Assistant; local templates build 22085164; save-empirics 2032-05-09
- Related: [Weapon Doctrine vs the Hydra](Weapon%20Doctrine%20vs%20the%20Hydra.md) · [Missile Swarm Doctrine](Missile%20Swarm%20Doctrine.md) · [Offense Timing vs Aliens](Offense%20Timing%20vs%20Aliens.md) · the generated module reference pages (run `scripts/generate_modules.py`)
