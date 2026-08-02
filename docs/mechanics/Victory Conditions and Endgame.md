---
title: Victory Conditions and Endgame
game_version: 1.0.32 decompile (build 22085164; decompile repo brackets 1.0.30–1.0.33); lessons re-verified through 1.0.38+
---

# Victory Conditions and Endgame

Campaign-independent decode of `vc_resistVictory` (the Resistance win) end-to-end: the exact victory-condition semantics, the project chain, the unlock-roll math, and the Close the Gate mission mechanics. Product of the 2026-06 Deep Strategic Review adversarial-verification pass (Phase 3, clusters B/D/F) — every fact checked against decompiled code and/or local game templates.

> **Evidence vintage caveat (applies to every constant in this note):** decompiled-source citations (`*.cs`) come from a repo whose single commit is dated 2025-06-12, bracketing builds ≈1.0.30–1.0.33 — not guaranteed byte-identical to the installed 1.0.32 (build 22085164). One concrete mismatch found: the save serializes ship design combat value as `_unnormalizedCombatValue` while the decompile uses `_combatValue`. Patch notes show no victory-chain changes 1.0.26–1.0.33, so this chapter is low-drift-risk — but **re-verify after any patch** (templates via `sync_game_data.py`; code via an updated decompile). 1.0.34-beta differences are flagged in §6.

> **Difficulty enum (code-verified):** 1 = Cinematic, 2 = Normal (default), 3 = Veteran, 4 = Brutal. See [Alien Hate and Diplomacy](Alien%20Hate%20and%20Diplomacy.md) for the derivation.

Reference-campaign numbers are examples only, labeled "e.g. reference campaign" (Normal difficulty, alienProgressionSpeed 2.0, snapshot in-game 2032-05-09).

## 1. Victory-template structure (generic)

`TIVictoryTemplate.json` holds **7 entries** — one per faction (`vc_resistVictory`, plus Destroy/Submit/Exodus/Escape/Appease/Cooperate chains). Each is a list of named conditions evaluated by `SingleVictoryConditionMet`; `AllVictoryConditionsMet` is the AND. Crucially, **the victory check is evaluated as a *targeting condition* of the faction's win mission** — all conditions must hold simultaneously *at the moment the mission is run*, and the state is re-evaluated live (a condition can un-satisfy if e.g. aliens found a new base). Other factions' chains decode the same way if ever needed.

`vc_resistVictory` = three conditions:

| Condition | Value | Exact meaning |
|---|---:|---|
| `AlienNationMaxRegionProportion` | 0 | `GameStateManager.AlienNation().regions.Count / all-regions ≤ 0` — **literally zero Earth regions** in the Alien Nation at mission time |
| `FreeBases_DefeatAliens` | 3 | No alien hab with `habType == Base`, tier ≥ 3, `anyCoreCompleted`, on the surveyed-region set (§2) — **stations excluded, alien primaryHab exempt** |
| `FreeFleets_DefeatAliens` | 4000 | No single alien fleet with `SpaceCombatValue() ≥ 4000` — **per-fleet**, not aggregate (§3) |

Evidence: `TIVictoryTemplate.json` vc_resistVictory; `TIVictoryTemplate.cs` FreePlanetRegion/FreeFleetRegion. Confidence: high.

## 2. FreeBases_DefeatAliens — which alien bases actually count

`FreeBases_*` conditions call `FreePlanetRegion`, which filters: `if (defeatAllBasesCondition.Contains(condition)) list = list.Where(x => x.IsBase)` where `IsBase => habType == HabType.Base` (`TIHabState.cs:262`). Therefore:

- **Stations never count.** They are enumerated (`TISpaceBodyState.cs:1371` `habs => stationsInOrbit.Union(surfaceBases)`) and then dropped.
- **The alien HQ (primaryHab) is exempt by construction**: a hab only fails the check if `hab.faction.IsActiveHumanFaction || hab != hab.faction.primaryHab`; aliens are not human (`IsActiveHumanFaction => !template.isAlien`, `TIFactionState.cs:187`), so their primaryHab passes. No "destroy the HQ" paradox — the win mission target always stands (§5).
- **Surveyed-region set:** major planets + moons (via `GetMajorPlanetRegions`, which includes Venus; the *UI description* uses the buildable-region call without Venus — cosmetic inconsistency, irrelevant since aliens can't base on Venus), plus asteroid-belt and Kuiper-belt objects expanded **only where `habSites.Length > 1`**; **Centaurs are never added** to the region set (`TISpaceBodyState` `centaur()`: Jupiter < a ≤ Neptune). So alien T3 bases on 1-habsite belt rocks and on Centaurs are **structurally invisible** to the condition.
- **The list re-grows**: aliens founding/upgrading new T3 bases (core completed) on surveyed bodies re-add entries; checked live at mission-targeting time.
- **In-game verification:** the victory-conditions panel renders from the same `FreePlanetRegion` call — trust its red-line list.

E.g. reference campaign (2032-05): of 12 alien T3 surface bases + 12 T3 stations, only **8 bases** counted. Exempt: the alien HQ (primaryHab); two 1-habsite belt rocks; one Centaur; all 12 stations.

## 3. FreeFleets_DefeatAliens = 4000 — per-fleet, sum-of-ship SCV

`FreeFleetRegion`'s global branch (the victory check passes `keySpaceBody = null`) fails on the **first alien fleet whose `SpaceCombatValue() ≥ 4000`**. Total alien power is irrelevant; sub-4000 remnants may survive. **No trajectory exemption in the global branch** — fleets on system-exit or crash trajectories still count (the `endsInCrash`/`exitsSolarSystem` exemptions exist only in the unused regional branch). A lone alien frigate or destroyer typically blocks victory (design values ≈11–36k). Evidence: `TIVictoryTemplate.cs` FreeFleetRegion; `TISpaceFleetState.cs:668`. Confidence: high.

### Ship SpaceCombatValue formula sketch (for auditing the fleet condition)

- **Fleet SCV** = Σ over ships of ship SCV (`TISpaceFleetState.cs:668`).
- **Ship SCV** = cached design value × usable-weapon fraction (×0.75 if rearm needed) × delta-V factor (`1 − (1 − clamp01(dv/maxdv)) × 0.2`, floor 0.8) × damage factor `(25 − damagedCount)/25` (`TISpaceShipState.cs:923`).
- **Design value** = `sqrt(defense × offense × mobility)` (`TISpaceShipTemplate.cs:495-546`), where:
  - *offense* = nose-weapon GenericScore × 0.75 × sqrt(angular accel) + hull weapons, with a magazine exponent;
  - *defense* = (nose armor + lateral × 1.25 + tail × 0.6 + SI, armor diminishing past 30) × sqrt(SI), × ECM/repair/component-armor multipliers;
  - *mobility* = 0.5 × sqrt(clamp(combatAccel_g, 0.1, 3)) × (clamp(dV/accel, 60, 1800)^0.2 − 2) × rotation^0.25, min-capped against the other two terms.
- Saves cache per-design values (`_unnormalizedCombatValue` in 1.0.32 saves) — read those rather than recomputing; cross-check one fleet's in-game displayed strength before planning a kill order (absolute scale vs UI was not verified).

E.g. reference campaign: 31 of 33 alien fleets over the bar; biggest ≈255k; only a lone escort (~3.8k) and gunship (~2.6k) under. Per-class design ranges: Titan 134–152k · Mothership 69–93k · Dreadnought 36–86k · Lancer 42–74k · Battleship 22–49k · Battlecruiser 39–43k · Cruiser 18–57k · Monitor 13–38k · Destroyer 11–36k · Frigate 11–29k · Corvette 7–13k · Escort 2.2–7.4k · Gunship 2.6–4.6k.

## 4. The Resistance project chain

| Step | Cost (RP) | Role | Evidence |
|---|---:|---|---|
| `Project_TheChokePoint` | 40,000 | **Pure gate** — prerequisite only (for The Final Assault, and the Kill the Hive / Enslave the Masters / A Permanent Peace alternates) | `TIProjectTemplate.json` |
| `Project_TheFinalAssault` | 25,000 | Grants the **Janus Section** org (wiki: 3-star, not on market) whose holder gets the **Close the Gate** and Assault Enemy Space Asset missions | template + wiki (org details wiki-grade) |
| Close the Gate (`ResistWin` mission) | — | The actual win (§5) | `TIMissionTemplate.json` |

Full wiki-claimed prereq chain ≈168k RP including itself (plausible, not independently recomputed).

### Unlock-roll mechanics for gated projects (generic — applies to any `initialUnlockChance` project)

Verified mechanism (`TIFactionState.cs:6930-6990, 12389`; active when the save has `variableProjectUnlocks = true`):

1. When the last prereq completes, `RollToAddProjectTrigger` fires **once**: availability passes with probability `factionAvailableChance` (scaled ×7/numFactions for generic projects; ≥100 = guaranteed). On pass, a trigger is created with `monthlyTriggerValue = initialUnlockChance + tech-contribution bonus + councilor Science/5`.
   - **Tech-contribution bonus** = `TechContributionBonus(project) × 100` percentage points ≈ **+1 pp per 1% of your contribution to the project's prereq global techs** (averaged over prereqs; recorded when each global tech completes — `TIGlobalResearchState.cs:510`). Flooding globals whose project drops you need is mechanically supported.
2. A **DAILY roll** then runs at the daily-equivalent of that monthly probability: `p_day = 1 − (1 − p_month)^(1/30.44)` (the code constant 0.032854885 = 1/30.44). At p_month 50% ⇒ ~2.25%/day.
3. At each `MonthlyFactionUpdate`, the value climbs by `deltaUnlockChance × researchSpeedModifier`, clamped to `maxUnlockChance`.

**Choke Point and Final Assault both have `factionAvailableChance:100, initialUnlockChance:50, deltaUnlockChance:50, maxUnlockChance:100`** ⇒ guaranteed trigger; worst case ~1 month + 1 day from prereq completion; expected ~2–3 weeks, faster with Science/contribution bonuses. **No RNG hedging needed.** Confidence: high.

Un-unlocked projects can also be obtained from other factions: `StealProject` mission and project trading (`CanTradeProject`).

## 5. Close the Gate — exact mission mechanics (1.0.32)

`ResistWin` in `TIMissionTemplate.json`. Confidence: high.

- **Conditions (all three):** `TargetInRange` + `Human` + `VictoryCondition` (= `AllVictoryConditionsMet`, §1).
- **Resolution: `TIMissionResolution_Automatic`** — automaticSuccess = true, success chance 1.0, outcome always Success, attacking/defending modifier lists empty. **No roll, no defense, uncontested** once you're there. Effect: `TIMissionEffect_Win` → EndGame.
- **Target = the hab MODULE** whose template SpecialRules contain `HabModuleSpecialRule.AlienWormhole`, drawn from KnownHabs' OkayModules (`TIMissionTarget_VictoryMissionTarget.cs`). The wormhole module sits at the alien primaryHab.
- **Wormhole + core are indestructible** at the alien primaryHab through ANY destruction path: `TIHabState.cs` `DestroyModule` returns false for AlienWormhole/core modules there, and `SelectModuleToDestroy` excludes them — the mission target always exists. (Wiki claims the wormhole facility produces large resource/MC income for the aliens; template confirms `incomeExotics_month = 10` on `AlienWormholeFacility`; the rest of the output figures were not verified.)
- **The councilor must be AT the hab**: `TIMissionCondition_TargetInRange` requires councilor co-location with the target hab (or a ValidDestination move there). **No from-orbit execution in 1.0.32.**
- **Getting the councilor there = landing a fleet**: `LandOnSurfaceOperation.cs:74` — a fleet may land at an enemy-held hab site **only if the hab's `SpaceCombatValue() ≤ 0`**.
- **"Destroy all combat modules" is therefore only the access gate, and DE-POWERING suffices**: hab SCV = Σ ACTIVE modules' combat values, where active = `functional && powered` (`TIHabState.cs:1187`; `TIHabModuleState.cs`). Killing the HQ's **power modules** (`SelectModuleToDestroy_Power` is a combat path) zeroes its SCV exactly like destroying every weapon module. Core + wormhole carry no SCV and can't be destroyed anyway.

**Executable flow on 1.0.32:** meet the three victory conditions (§1–3) → bombard the HQ's active combat/power modules to SCV 0 → land the fleet carrying the Janus councilor at the HQ site → run Close the Gate → automatic win, with the HQ still standing.

### Marine assault of the HQ — what it is and isn't

- Victory **never requires** assaulting or capturing the HQ (primaryHab exempt §2; mission needs only co-location §5).
- In current code, marine "capture" of ANY alien hab is a **raid**: `CaptureHab`'s alien branch loots exotics (3 × tier × (1 + successLevel) × rand 0.8–1.2) then **destroys the hab** — you can never capture-and-operate an alien base. Councilor-led `SeizeSpaceAsset` passes successLevel 1/3 (success/crit) vs fleet-only assault −1/0, which is why councilor assaults pay ~14–43 exotics on a T3 and marine-only success pays ~0 (see [Economy Markets and Loot](Economy%20Markets%20and%20Loot.md)). The Seize roll itself is contested on councilor **Command** (+ Operations spent + marine force size, − your MC shortage) — councilor selection, org stacking, and why crit is the target: [LESSONS-politics C14](../lessons/LESSONS-politics.md).
- Assault success curve: `P = 1 − 0.5 × 0.775^(attacker − defender)` — parity 50%, +9 ≈ 95%, +18 ≈ 99.5%; **no hard 0% block**, odds just collapse (`AssaultHabOperation.cs` GetSuccessChance).
- Hab ground defense = coreTier + Σ(specialRulesValue per matching marine-rule) × CommandAdviserMultiplier (+ effects, docked fleets, − MC shortage). The marine-rule range is MarinePlatoon..Salamanders, so an `AlienCitadel` (Salamanders + WarDogs, value 48) counts **twice** = 96 — there is NO flat "6×" alien multiplier. E.g. the reference campaign's alien HQ ≈530+ defense intact, ≈37 after bombarding everything destructible.
- **REFUTED as current mechanic:** the Oct-2022 "platform-kit marine-spam to capture the final base" recipe — capture destroys alien habs now, and the win path doesn't need it.

## 6. 1.0.32 vs 1.0.34+ (beta) differences

Verified-absent in 1.0.32, reported-present from 1.0.34 (shipped in beta 1.0.35; Pavonis forum patch notes):

1. **Marines may once again assault the alien primary base** (as a raid; the two plot-required modules — wormhole + core — survive, consistent with the `DestroyModule` hard block). The decompile shows no primaryHab exclusion in `AssaultHabOperation.GetPossibleTargets`, which matches the post-1.0.34 state; whether 1.0.32 specifically blocks the assault op could **not** be settled from available evidence. In-game test: orbit the HQ with a troop fleet and check whether the assault op lists it.
2. **Win mission launchable FROM ORBIT** once the base is defanged — no from-orbit path exists in the decompiled `TIMissionCondition_TargetInRange` (co-location only), so on 1.0.32 plan for a physical landing. ("Unclear" status: the change may live outside the decompiled file.)

Pre-2026 endgame walkthroughs are obsolete specifically on the assault step; the May-2026 sequence (clear conditions → bombard → land councilor → automatic win) is the code-verified one for 1.0.32.

## 7. Misconception graveyard

- **REFUTED:** "you must destroy the alien HQ / all 24 alien habs." Stations never count; the HQ is exempt; 1-habsite belt rocks and Centaurs are invisible to the condition (§2).
- **REFUTED:** "alien fleet strength must be reduced below 4000 total." It's per-fleet (§3).
- **REFUTED:** "combat modules must be *destroyed*." De-powering works; the requirement is hab SCV ≤ 0 for landing only (§5).
- **REFUTED:** "Close the Gate can fail / is contested." Resolution is Automatic, success 1.0 (§5).
- **REFUTED:** "Choke Point/Final Assault unlock is a risky monthly roll." Guaranteed trigger, daily rolls, ≤ ~1 month worst case (§4).
- **REFUTED:** "capture and hold the final base" (pre-1.0 recipes). Alien hab capture = raid-and-destroy (§5).

Related: [Alien Hate and Diplomacy](Alien%20Hate%20and%20Diplomacy.md) (Total War clock, hate cost of the campaign) · [Drives Refits and Logistics](Drives%20Refits%20and%20Logistics.md) (reaching the Kuiper HQ) · [Space Combat Math](Space%20Combat%20Math.md) (winning the fleet battles) · [Mechanics index](README.md)
