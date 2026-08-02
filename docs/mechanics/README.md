---
title: Mechanics reference (index)
game_version: 1.0.32 decompile (build 22085164; decompile repo brackets 1.0.30–1.0.33); lessons re-verified through 1.0.38+
---

# Terra Invicta — Mechanics reference

**Version & precedence:** constants here were calibrated at the ~1.0.32 decompile snapshot; the lessons library has since been re-verified through 1.0.38+ — **where a `docs/lessons/` entry supersedes a mechanics passage, the lesson wins**, and supersessions are marked inline in the affected section.

**Purpose of this folder:** code-verified, **campaign-independent** game mechanics, written so you (or your analysis agent) never re-derive or re-verify them. These notes came out of a ~40-agent adversarial "Deep Strategic Review" of community claims against the decompiled game code. Each note states the general rule first (all four difficulty columns), carries inline evidence for every fact (code symbol, template field, or save-empiric + confidence), and quarantines current-campaign numbers as clearly-labeled examples.

## The notes (2026-06-11 Deep Review, Phase 5a; + later additions)

- [Alien Hate and Diplomacy](Alien%20Hate%20and%20Diplomacy.md) — the complete hate system: MC-based hate floor and the 4 masking projects, war (50) / Total War (200 + time gate) thresholds, venting and the knockdown reprieve, zero-hate combat exemptions, hate-per-kill = 0.4×SI (myth "hate += SI" refuted), passive growth/decay, the Advanced Master Project escalation clock.
- [Victory Conditions and Endgame](Victory%20Conditions%20and%20Endgame.md) — `vc_resistVictory` decoded exactly (zero alien Earth regions; T3 *surface bases* only, HQ exempt, stations/Centaurs/1-habsite rocks invisible; per-fleet <4000 SCV), the Choke Point → Final Assault → Janus Section → Close the Gate chain, project unlock-roll math, ship-SCV formula sketch, 1.0.32-vs-1.0.34-beta endgame differences.
- [Space Combat Math](Space%20Combat%20Math.md) — weapon/armor damage formulas (flat subtraction vs kinetics, armor^1.5×spotArea vs lasers, the 6.25% radiation cap), PD mechanics and saturation, missile/torpedo hit math and ECM/Targeting Computer interactions, hull hardpoints and battle-cap (30 default) mechanics.
- [Drives Refits and Logistics](Drives%20Refits%20and%20Logistics.md) — the refit legality rule (same driveClassification + reactor + propellant; hull immutable), drive-family ladders, open-cycle cooling and radiator truth, remass-scoop eligibility, transit-time classes for outer-system (Kuiper) campaigns.
- [Economy Markets and Loot](Economy%20Markets%20and%20Loot.md) — exotics and antimatter acquisition paths (no human exotics income on 1.0.32 — salvage/capture only; councilor-led assaults pay, marine-only doesn't), collider economics, resource-market mechanics and money levers, mining multipliers.
- [Research Mechanics](Research%20Mechanics.md) — global-tech vs faction-project split, category bonuses and soft caps, institute stacking, the MultipleFacilitiesMultiplier (+5/3/1% per *active facility*, not per completed project), tech-contribution → project-unlock coupling, unused-MC research conversion.
- [Orbital Bombardment](Orbital%20Bombardment.md) *(added 2026-07-15)* — bombardment vs defended bases: interception is a pooled num/num2 RATIO (100% wall when defense DPS ≥ your kinetic throughput — volume of torpedoes ≈ nothing), altitude multiplies interception ×1/×2/×3 (Low/Med/High — always bombard LOW), lasers absorbed by module armor^1.5 (powered = ×8), **ShapedNuclear (Olympus/Acheron/Tartarus/Styx) = 20% bypass + ignores module armor** while plain nukes are intercepted like slugs and instakill-the-hab (0% loot) if they land; STO counterfire focuses your best bomber nose-on (MaxBy bombardmentValue is ORDINAL — extra guns do not increase incoming volume; exotics-free siege armor = Adamantane, ~3x maxed Nanotube), ECM-only defense; AI committal rule ≥1.5× base SCV.
- [Alien Production Rebuilding and Targeting](Alien%20Production%20Rebuilding%20and%20Targeting.md) *(added 2026-07-13)* — how the Hydra regenerates and retaliates: ship production is conventional and resource-constrained (rebuild target = 0.33× current fleet total, so kills permanently lower the ceiling); destroyed bases are re-founded toward a 12(+3 in Total War) cap and regrown to T3 (kill the victory-list bases late, in one window); `FreeFleets_DefeatAliens` counts LIVE per-fleet SCV with no intel filter (damage dips it, repairs restore it — kills stick); escalation clocks (inner-system exotic attacks ~16 modified yrs, Total War 20, Master Project 25); retaliation targeting weights mass^1.5 ×2-for-shipyard-habs gated by local superiority — forward-basing doctrine follows.
- [Ship Mass and Delta-V Model](Ship%20Mass%20and%20Delta-V%20Model.md) *(added 2026-06-15)* — full code-verified mass decomposition: propellant tank = 100 t, drive hardware = 0 (mass is reactor + radiator), reactor = req_power × spec_power, radiator = req_power × (1−reactor_eff) × (1000/radiator_specificPower), ΔV = modifiedEV × ln(wet/dry) where modifiedEV = EV_kps × ∏(utility EVMultiplier) and **Liquid Hydrogen Containment = ×1.2** (the "1.2 ΔV factor"), combat-accel g-cap clipping, per-hull armor coefficients (Battlecruiser added), the GasCoreVI = "Terawatt GC III" display-name trap. Backs `warship_optimizer.py`.
- [Hab Build Costs and Radiation](Hab%20Build%20Costs%20and%20Radiation.md) *(added 2026-07-17)* — the per-body build/upgrade cost surcharge: radiation (not gravity) drives module costs, Luna 267 metals → Io 3,800 for the same T2→T3 mine leg; ColonyCore prereqs are cheap by comparison; costs are paid up-front at click. Backs the `BODY_COST` table in `mine_upgrade_planner.py` / `cc_upgrade_planner.py`.
- [Hab Power and Solar Output](Hab%20Power%20and%20Solar%20Output.md) *(added 2026-07-19)* — the code-verified solar law (`SolarPowerOutput` = natural multiplier × rating + mirror bonus, 8× cap; multiplier priority orbit→site→body), the reconstructed surface/orbit multiplier validated against three in-game ☀ readouts, why a 240-rated Solar Farm makes 543 on a mirror-served Mars base, and the power-planning rules (idle generators are instant capacity; upgrades need only the NET draw). Backs `hab_power_audit.py`.

## Evidence standards

> **Decompiled-source location (confirmed 2026-06-15):** a full community decompilation of the
> game's C# exists on GitHub at **`Armandox33/Terra-Invicta-AI-Assistant`**, path
> `TI Assembly Project/Assembly-CSharp/…` (one `.cs` per class). These docs cite class/method
> names and derived formulas from it — none of that source is copied here. Constants were
> cross-checked against the installed build; re-verify after any patch.

**No mechanic claim from model memory.** Evidence tiers — higher beats lower; contradictions get recorded explicitly, never averaged:

1. **Local game templates + save-file empirics** (installed build's `TIXxxTemplate.json` + extractor reads)
2. **Lessons-library verified lessons** (`docs/lessons/`, empirically tested in-game)
3. **Official wiki** (hoodedhorse)
4. **Community lore** (Reddit, Steam guides) — judgment input only, never a fact source

Plus, for these notes specifically: **decompiled C# source** is treated as tier-1-adjacent with a vintage caveat — the available repo's commit is dated 2025-06-12, bracketing ≈1.0.30–1.0.33, so it may not be byte-identical to the installed 1.0.32. Where the decompile and the wiki disagree on a constant (e.g. hate-per-kill 0.4 vs 0.35), both values are recorded and an in-game n=1 test is named.

## Re-verify-after-patch rule

Constants in these notes are valid for **1.0.32 (build 22085164)**. After ANY game patch:

1. Re-sync templates: `scripts/sync_game_data.py` (content-level drift report tells you what moved).
2. Re-check code constants against an updated decompile if one exists — especially flagged drift candidates (hate constants, victory thresholds, endgame mission paths; 1.0.34-beta already changes marine-assault-of-HQ, from-orbit win, hate-generation tweaks, and kinetic estimation).
3. Bump `game_version:` in any note you re-verify; record contradictions, don't overwrite history silently.

## Conventions

- General formula first, **all difficulty columns** (enum: 1 = Cinematic, 2 = Normal, 3 = Veteran, 4 = Brutal — code-verified; the old 0–3 community table is wrong).
- Campaign numbers only as labeled examples from the reference campaign (Resistance, Normal difficulty, alienProgressionSpeed 2.0, researchSpeed 2.0 — scale by your config).
- Every fact: inline citation (`file.cs:symbol`, `TIXxxTemplate.json` dataName/field, or save-empiric) + confidence.
- Misconceptions are kept and marked **REFUTED** so they don't resurrect.
- Absolute ISO dates; UTF-8 with characters as themselves.

Related reference elsewhere in this repo: `docs/lessons/` (verified formulas and save-file semantics), `docs/strategy/` (doctrine built on these mechanics), `scripts/` (analyzers + `sync_game_data.py`).
