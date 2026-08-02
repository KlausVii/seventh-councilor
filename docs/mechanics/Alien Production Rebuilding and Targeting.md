---
title: Alien Production Rebuilding and Targeting
game_version: 1.0.32 decompile (build 22085164; decompile repo brackets 1.0.30–1.0.33); lessons re-verified through 1.0.38+
---

# Alien Production, Base Rebuilding, Victory-SCV Counting, and Retaliation Targeting

Campaign-independent, code-verified reference for how the Hydra **regenerates** (ships and
bases), how the `FreeFleets_DefeatAliens` victory check actually counts fleets, and how the
alien AI **picks targets** among player assets. Product of the 2033-06 strategic review's
decompiled-source pass (2026-07-13). Complements [Alien Hate and Diplomacy](Alien%20Hate%20and%20Diplomacy.md) (hate/Total War
triggers) and [Victory Conditions and Endgame](Victory%20Conditions%20and%20Endgame.md) (win-condition semantics).

> **Evidence vintage caveat:** all `*.cs` citations are from the community decompile
> (`Armandox33/Terra-Invicta-AI-Assistant`, commit 2025-06-12, brackets builds 1.0.30–1.0.33);
> the campaign runs 1.0.39. Constants marked ✱ are `TIGlobalConfig.cs` field initializers and
> can additionally be overridden by the game's config JSON at load. Logic structure is likely
> stable; numeric constants may have drifted.

## 1. Alien ship production — conventional, resource-constrained, demand-driven

**Verdict: the alien navy REGROWS if their economy is left intact. Ships are built at alien
habs' shipyards for full resource cost — not spawned at the HQ, not delivered on a wormhole
schedule.** Confidence: high (structure), medium (rates — data-driven).

- Ship builds pay a full `TIResourcesCost` (metals, water, volatiles, exotics for advanced
  parts) assembled in `TISpaceShipTemplate` (~lines 3150–3184), multiplied by
  `GetAIShipbuildingCostDifficultyScaling` — on **Normal, aliens pay 1.0× sticker cost**
  (`TIModifier_AlienAIShipBuildingScaling_N = 1.0`✱; Cinematic 1.25×, Brutal 0.75×).
- Build *demand* comes from `FactionGoal_AssembleFleet`:
  `ComputeDesiredFleetCombatValue() = max(base, 0.33 × Σ current fleet SCV)`
  (`FactionGoal_AssembleFleet.cs:186–194`), maintained by
  `AIDailyFactionPlanner.ManageFleetGoals` (~1299+). Every alien base of tier > 1 and the
  primary hab also raise per-location `FactionGoal_DefendWithFleet` goals (~1301–1409), so
  losses at a defended site regenerate demand there.
- **The rebuild target scales DOWN as you kill**: 0.33 × current total means a navy cut in
  half rebuilds toward a halved target, not back to its peak.
- Not gated by hate or by a loss-triggered timer; rate is bounded by alien resource income +
  shipyard throughput (data/save facts, not code constants — UNVERIFIED absolute rates).

**Campaign implication:** attrition-only warfare against ships is a treadmill; killing alien
**mining/shipyard habs** cuts the regeneration rate AND (via the 0.33× rule) each fleet kill
permanently lowers their rebuild ceiling.

## 2. Alien base rebuilding — bases do NOT stay dead

**Verdict: the alien AI holds a target base count and re-founds when below it, driving new
bases to full tier 3 — which re-triggers the `FreeBases_DefeatAliens` failure.** Confidence:
high.

- `AlienHabPlanner.ManageHabGoals` (lines 12–120): while
  `bases + pending FoundBase goals < GetMaxAlienBases(0f)` it adds
  `FactionGoal_FoundBase(GoalType.BuildFullBase)`. Cap = `maxAlienBaseGoals_N = 12`✱,
  **+3 in the Total War era** (`extraMaxAlienBaseGoals_TotalWarEra_N = 3`✱) → 15.
  It also founds refuelling/economy bases on foreseen upkeep insecurity (82–108).
- `FactionGoal_BuildFullBase.GoalFulfilled()` requires ALL completed modules at tier 3
  (`FactionGoal_BuildFullBase.cs:48`) — "full base" literally means grown to T3.
- Victory test (`TIVictoryTemplate.FreePlanetRegion`, 517–634): a base fails the player iff
  `tier ≥ 3 && anyCoreCompleted && hab != AlienFaction().primaryHab` on the surveyed set —
  so a re-founded base is harmless **until** it reaches T3 + completed core, then it blocks
  the win again. New site selection is `SelectHabSiteForDevelopment` — not necessarily the
  same body.

**Campaign implication:** kill the 8 victory-relevant T3 surface bases **late and within one
construction window**, not piecemeal years apart. Rebuild-to-T3 time is data-driven
(UNVERIFIED in code) — estimate from observed alien construction, and expect the +3 base-goal
bump after Total War (~2036-02 in the reference campaign).

**Forensic — which specific bases changed between two saves (the count hides churn):** the
alien base *count* is a net figure — a new foundation can mask a base you destroyed, so a count
that returns to its old value does **not** mean your kill was undone. To identify the actual
habs, diff the set of alien-owned `TIHabState` **IDs** across the two saves: an ID **gone
entirely** = that base was destroyed; an ID whose **owner flipped** to a human faction =
captured (rare — usually you see destruction, not capture). `alien_progress_timeline.py`
reports net counts only; for identity, list each alien hab per save with its `displayName`,
`templateName`, `tier`, and location (`habSite` → surface body/region for bases, `barycenter`
→ orbited body for stations). Re-founded bases often reappear at a *different* body via
`SelectHabSiteForDevelopment` (§2), so match by ID, not by name or location.

## 3. `FreeFleets_DefeatAliens` — live-state, per-fleet, no intel filter

**Verdict: the ≥4,000 SCV check iterates the alien faction's REAL fleet list (visibility
irrelevant), per fleet as currently grouped, using LIVE ship state — damage reduces counted
SCV, but ships repair, so only kills stick.** Confidence: high.

- Entry: `TIVictoryTemplate.SingleVictoryConditionMet` → `FreeFleetRegion(faction, condition,
  keySpaceBody: null, …)` (428–439); with null body it runs
  `foreach fleet in AlienFaction().fleets: if (fleet.SpaceCombatValue() >= 4000) return false`
  (735–745). **No trajectory/retreat exclusion on this branch** (the crash/exit-system
  exclusion at 716–721 exists only in the UI/region branch) and **no player-intel filter**.
- Per-ship SCV (`TISpaceShipState.SpaceCombatValue`, 923–948): design value ×
  (fraction of weapons able to fire) × 0.75-if-out-of-ammo × (down to 0.8 when
  propellant-dry) × `(25 − min(25, damagedParts+damagedSystems))/25`. 25+ damaged
  components → SCV 0. Cached (`_cachedSpaceCombatValue`), recomputed on dirty flag.
- Aliens control their own merging/splitting — you cannot game their grouping.

**Campaign implication:** a mauled fleet can dip below 4,000 but climbs back as it repairs.
The victory snapshot is instantaneous at Close-the-Gate time, so a "cripple everything
simultaneously" finish is *theoretically* legal but practically fragile — plan on kills.

## 4. Total War (~2036-02) and Advanced Master Project (~2038-08) — what actually changes

Confidence: high for venting/base-goals; UNVERIFIED items flagged.

- **Total War trigger** (`FactionGoal_WarOnFaction.DailyGoalMaintenance`, 187–190): elapsed
  modified years ≥ 20 AND hate ≥ 200 (`alienFactionHateWarValue 50 × 4`). Reference campaign:
  hate long past 200 → flips deterministically at the date. Effects: hate **venting on
  asset-destruction stops** (`TIFactionState.RegisterKill` 16274–16324, vent skipped when
  `IsTotalWar`), war goal becomes non-discardable, **+3 alien base goals** (§2).
- **Attack cadence on Normal:** `alienReducedWarAttacks_N = true`✱ is **independent of Total
  War** — aliens keep reduced simultaneous war attacks (≈2 base + up to 2 extra concurrent
  fleet attacks; they randomly drop a station or base target each pass). UNVERIFIED whether
  1.0.39 changed this in Total War — the community "Total War unleashes them" claim is NOT
  supported by this decompile vintage.
- **Earlier escalation gates that matter more than Total War:**
  `GetCampaignDurationBeforeAlienInnerSystemExoticAttacks_N = 16`✱ modified years →
  **~2034-02 in the reference campaign** (inner-system exotic attacks begin);
  `yearsBeforeInnerSystemOffensives_N = 20`✱ → ~2036-02 (inner-system offensives).
- **Advanced Master Project**: `TIFactionState.MonthlyFactionUpdate` (1858–1866)
  auto-completes `Project_AlienAdvancedMasterProject` once elapsed modified years > 25
  (`_N = 25`✱) → **~2038-08 in the reference campaign** (earlier notes said "2038-39"; the code puts it
  at 12.5 real years from start). Permanent. The "+25% build rate / +5,000 exotics"
  magnitudes are template-JSON facts, not code-verified here.

## 5. Retaliation targeting — what the aliens attack, and when forward bases die

**Verdict: value-weighted (mass^1.5), construction-hab-prioritized (×2), gated by a local
force-superiority test. An undefended forward shipyard base near an alien stronghold is a
top-priority, easily-cleared target — predictably suicidal.** Confidence: high.

- Hab selection (`AIEvaluators.cs`): `SelectBaseToAttack`/`SelectStationToAttack` weight by
  `mass_kg^1.5` (4184, 4226); bases ×1.3 vs stations (`SelectHabToAttack`, 4104); habs with
  zero hab-weapon SCV preferred (4207–4224). `GetCriticalConstructionHabs` (4107–4147) flags
  shipyard/founding-capable habs — filtered-to-first and **×2 weight** (4184, 4226); the
  *only* construction hab in a system is singled out.
- Fleet selection: `SelectFleetToAttack` weights `SCV²` (4266) but skips the single
  strongest fleet unless the aliens have desired superiority (4262–4265) — they hunt
  strong-but-beatable fleets.
- Attack gate: `expectedAttackStrength / target.PerceivedAggregateDefensiveScore ≥
  GetMinimumSuperiorityForSpontaniousAttack` (4159–4176); local-system balance via
  `SystemFleetStrengths` / `GetRequiredDefenseStrength` (3944–3966; required defense scales
  ×((tier−1)/10 + 1), ×2 for the primary hab).

**Campaign implication (forward-basing doctrine):** a new forward shipyard base (e.g.
Saturn/Titan next to a Dione stronghold) combines the two biggest weight multipliers with a
trivially-passed superiority test. Forward-base ONLY with a stationed defense fleet strong
enough to fail their superiority check, or after thinning the local alien fleets so
`expectedAttackStrength` can't clear the bar.

## Sources

- Decompiled source: `TIVictoryTemplate.cs`, `TISpaceFleetState.cs`, `TISpaceShipState.cs`,
  `TISpaceShipTemplate.cs`, `FactionGoal_AssembleFleet.cs`, `FactionGoal_BuildFullBase.cs`,
  `FactionGoal_WarOnFaction.cs`, `AlienHabPlanner.cs`, `AIDailyFactionPlanner.cs`,
  `AIEvaluators.cs`, `TIFactionState.cs`, `TIGlobalConfig.cs` (repo
  `Armandox33/Terra-Invicta-AI-Assistant`, commit 2025-06-12).
- Produced for the 2033-06 strategic review; campaign dates use 2026-02-01 start ×
  `alienProgressionSpeed 2.0`.
