---
title: Research Mechanics
game_version: 1.0.32 decompile (build 22085164; decompile repo brackets 1.0.30–1.0.33); lessons re-verified through 1.0.38+
---

# Research Mechanics

Code-verified facts **beyond** the structural basics (two tracks, three global slots, picking rights, project availability fields — covered in `docs/lessons/LESSONS-research.md`; this note does not repeat them). Part of the [Mechanics index](README.md); siblings: [Economy Markets and Loot](Economy%20Markets%20and%20Loot.md), [Victory Conditions and Endgame](Victory%20Conditions%20and%20Endgame.md), [Alien Hate and Diplomacy](Alien%20Hate%20and%20Diplomacy.md).

> **Evidence caveat (applies to every code citation below):** decompiled-source evidence comes from a repo vintage bracketed **1.0.30–1.0.33** (commit dated 2025-06-12); constants could drift in newer builds — **re-verify after any game patch** (templates via `scripts/sync_game_data.py`; code via an updated decompile). Note: `TIGlobalConfig.json` in the install is a partial override file with //-comments; the research constants cited here (0.9 slot penalty, 5/3/1% facility tiers, 0.075 MC conversion) are **C# defaults** from TIGlobalConfig.cs that govern when no template override exists — verified absent from the JSON.

Reference-campaign examples are labeled **[reference campaign]** = Normal difficulty, `researchSpeedMultiplier` 2.0, `alienProgressionSpeed` 2.0, in-game ≈ 2032-05.

---

## 1. Project slots are internally slots 3/4/5

A faction's private project slots are indexed **3, 4, 5** (`GetDefaultProjectForSlot` slots {3,4,5}, after the three global slots):

- Slot 3 — always available.
- Slot 4 — unlocks with the **first active org** granting project capacity (`orgProjectSlotUnlocked` = any active org with `projectCapacityGranted > 0`, TIFactionState.cs:5429).
- Slot 5 — unlocks with the **first hab module** granting project capacity (analog at :5483).

*(code, high confidence)*

## 2. Category research bonuses — how the % numbers actually work

### They are BONUSES above 100%, not sub-100% multipliers

The per-category numbers shown in-game (and previously mis-transcribed in earlier notes) are **additive bonuses on top of nominal**: a category showing "+87%" runs **1.87× nominal**, not 0.87×. An earlier reading in the reference campaign log ("Energy 87% / Life 70% run slow") was a **misread — those categories ran +87%/+70% FASTER than nominal**; only the relative prioritization between categories was valid. *(corrected against TIFactionState.GetEffectiveResearch / DistributedCategoryModifierValue; high confidence)*

### Per-source-class soft caps

The category bonus is the sum of separate pools — **habs, orgs, councilor traits, fleets** (+ investigations, Xenology only) — and each pool is soft-capped independently (TIFactionState.cs:12352–12356):

```
raw pool sum x ≤ 0.5   → passes through unchanged
x > 0.5                → bonus = 0.5 + 0.5·(x − 0.5) / ((x − 0.5) + 2)
asymptote              → +100% per pool
```

Worked example: six T3 Science Institutes (0.25 each) → raw 1.5 → 0.5 + 0.5·(1.0)/(3.0) = **+66.7%, not +150%**. Stacking same-class sources past raw 0.5 bleeds value fast; diversify source classes instead.

### Xenology labs are 2–4× stronger per module than every other category

Hab research-lab category bonuses by tier (TIHabModuleTemplate.json): **Xenology 0.10 / 0.25 / 0.50** (XenologyLab / XenoscienceResearchCenter / XenoscienceInstitute) vs **0.025 / 0.10 / 0.25** for every other category's lab line. T3 institutes are `onePerHab=false` with no per-faction cap and also give flat 15 research/mo each. Xenology uniquely adds **+ alienInvestigations/100** (`InvestigationsModifier`, TIFactionState.cs:12358). Since the entire Resistance victory chain is Xenology projects (see [Victory Conditions and Endgame](Victory%20Conditions%20and%20Endgame.md)), Xenology labs are the highest-leverage research buildings in the game. *(templates+code, high confidence)*

> **`alienInvestigations` — how it's earned (and what the "AlienInv" campaign-log column is):** the counter ticks up when your councilors complete the **Investigate Alien Activity** mission (+2 on the higher success tier, +1 on the lower; `TIMissionEffect_InvestigateAlienActivity`). So the Xenology `+alienInvestigations/100` bonus is a slow, mission-driven ramp, not automatic — running Investigate Alien Activity is a genuine research investment, not just intel-gathering (it also feeds alien-space-asset detection). It is **your** count of investigating the aliens — not the aliens investigating you. It only rises, so a plateau means you stopped running the mission. *(code, high confidence)*

### The aliens have no research economy

The alien (Hydra) faction produces **zero** Research and Projects: the councilor-income path hard-returns `0f` for those resource types when `isAlien` (`TICouncilorState.GetMonthlyIncome`), the AlienCouncil holds no control points and no research habs, and its `baseIncomes` Research is 0. Consequently it never shows a research figure in `research_income.py --all-factions` and must **not** be given a research column. The Hydra advances on a **timer**, not RP — alien progression speed × modified-year escalation gates (Total War, inner-system exotic attacks, the Advanced Master Project; see [Alien Hate and Diplomacy](Alien%20Hate%20and%20Diplomacy.md) §3/§9 and [Alien Production Rebuilding and Targeting](Alien%20Production%20Rebuilding%20and%20Targeting.md) §4). Practical consequence: there is no alien tech *pace* to out-run in a race sense — the thing racing you is the campaign clock, so "winning fast" beats "out-teching them." *(code + save-empiric, high confidence)*

### The ×0.9 same-category slot penalty — "Versatility bonus" is a myth

**REFUTED:** there is **no** "Versatility" spread bonus anywhere in the code (grep: 0 hits). The real mechanic is a **penalty**: the category bonus is multiplied by **0.9 for each ADDITIONAL slot simultaneously researching the same category** (`categoryBonusPenaltyPerExtraSlot = 0.9`, TIGlobalConfig.cs:1602, applied in `DistributedCategoryModifierValue`, TIFactionState.cs:12360).

- Concentrating **weight** into fewer slots: free.
- Occupying **multiple slots with the same category**: taxed ×0.9 per extra slot.

> **[reference campaign]** slot-table deltas Info 104→94%, Social 111→100% are exactly this ×0.9 applied to the bonus portion when the same category held two slots.

## 3. MultipleFacilitiesMultiplier — faction projects only

`TIFactionState.MultipleFacilitiesMultiplier` (TIFactionState.cs:12351) multiplies **faction-project research only** (the `isProject` branch of `GetEffectiveResearch`, :12361 — global techs get nothing). It counts **ACTIVE project-slot-granting facilities** — councilor trait sources + org sources beyond the first + hab sources beyond the first:

| Active slot-granting facilities | Bonus each | Cumulative max |
|---|---:|---:|
| First 20 | +5% | +100% |
| Next 20 | +3% | +160% at 40 |
| Beyond 40 | +1% | open |

(TIGlobalConfig `first20/second20/overageExtraProjectBonusPct = 0.05/0.03/0.01`.)

**REFUTED myth:** *"burn cheap projects to compound research speed"* — the bonus is **NOT** per completed project. Completing projects does nothing here; **holding** more slot-granting orgs/modules/traits does. The multiplier drops if those facilities deactivate (org lost, module unpowered).

> **[reference campaign]** the +173% faction-project bonus visible in-game = this multiplier over the faction's active facility count.

## 4. Project unlock-roll mechanics

Active when the campaign has `variableProjectUnlocks = true` (a save-level flag — check it before applying any of this). Mechanism (TIFactionState.cs:6930–6987, B-cluster verified):

1. **Trigger creation** — when the last prereq completes, `RollToAddProjectTrigger` fires once. Availability uses `factionAvailableChance` scaled ×7/numFactions; at ≥100 the trigger is guaranteed.
2. **Starting chance** — `monthlyTriggerValue = initialUnlockChance + TechContributionBonus×100 + councilor Science/5` (+ any `ProjectUnlockChance` effects).
3. **Daily roll** — runs at the daily-equivalent of the monthly probability: `p_day = 1 − (1 − p_month)^(1/30.44)` (literal exponent 0.032854885 in `DailyProjectTriggerCheck`; ≈2.25%/day at p_month 50%).
4. **Monthly climb** — `monthlyTriggerValue += deltaUnlockChance × researchSpeedModifier`, clamped to `maxUnlockChance` (`MonthlyProjectTriggerChanceChange`, called from MonthlyFactionUpdate).

Practical consequence for 50/50/100 projects (e.g. the victory-chain unlocks): worst case ≈ 1 month + 1 day after prereq completion; expected 2–3 weeks; "monthly rolls" is the wrong mental model — it is a **daily** roll whose rate steps up monthly. Details of the Choke Point / Final Assault application: [Victory Conditions and Endgame](Victory%20Conditions%20and%20Endgame.md).

## 5. Global-tech contribution buys project-unlock chance

When a global tech completes, each faction's contribution fraction is recorded (`TIGlobalResearchState.OnPublicTechCompleted`, :510). Project trigger rolls then add **`TechContributionBonus × 100` percentage points ≈ +1pp per 1% contribution**, averaged across the project's tech prereqs (`TechContributionBonus`, TIFactionState.cs:5748; consumed in `RollToAddProjectTrigger`, :12389).

**Strategy that falls out:** flood research into global techs whose project drops you need — you're buying unlock probability, not just denying the pick. And if you never unlocked a project, it is still obtainable via the **Steal Project** mission or **project trading** (`CanTradeProject`, TIFactionState.cs:12643). *(code, high confidence)*

## 6. Template RP ≠ in-game RP — uniform ×(100 / research_rate_pct)

In-game RP cost = template `researchCost` × 100 / `research_rate_pct` — **uniform across techs and projects**. At Research Rate 200% every cost is exactly ×0.5 (verified against many 2033 screenshots: DTF 50k→25k, Final Assault 25k→12.5k, GPA 40k→20k, Maglev 15k→7.5k…). See [LESSONS-research](../lessons/LESSONS-research.md) R5.

*(Supersession note: an earlier revision of this section reported per-project template→in-game ratios of ×0.5 to ×5.5 and called uniform-×0.5 wrong. That observation predates the R5 screenshot verification and conflated other effects; no non-×0.5 cost has matched any observation since. If an in-game cost ever deviates from template × 100/rate, screenshot it and re-open.)*

**Rule: quote in-game costs (template × 100/rate per the campaign's `config.json`), and when a single project's timeline is load-bearing, confirm against the tooltip.** *(screenshot-verified across many 2033 saves, high confidence)*

Related verified scaling: `researchSpeedModifier` (the 200% campaign setting) does multiply the **deltaUnlockChance** climb in §4 — so unlock chances ramp twice as fast at 200%, independent of cost display.

## 7. Unused-MC research trickle

Each point of unused Mission Control yields **0.075 research/day** (+0.2 money/day), capped at `min(buildable-source MC, available MC)` — `ExcessMCToResearchConversion_Day = 0.075` (TIGlobalConfig.cs:1040), TIFactionState.cs:2978–2982. (76 free MC ≈ 5.7 research/day, matching the in-game tooltip.) Money side and MC-deficit penalties: [Economy Markets and Loot](Economy%20Markets%20and%20Loot.md). *(code + tooltip-corroborated, high confidence)*

## 8. Research traps and skip rules

### Exofighters (OrbitalFighters) is a global TRAP

`OrbitalFighters` is a **global** tech (7,500 RP, MilitaryScience): once ANY faction finishes it, it is finished for everyone. Exofighters are **nation** assets commanded by executive factions, launched from Earth facilities against fleets/stations in Earth interface orbits (`LaunchSTOInterceptorsOperation`). Consequences:

- Researching it primarily **arms hostile human factions (and alien-controlled nations) to raid YOUR LEO assets** — even if you build none yourself.
- The aliens field their own fighters regardless (`AlienFighterController`) — researching it does not protect you from those.
- It is in **no victory-required closure** → fully skippable.

Verdict for a space-dominant faction holding LEO assets: **do not research it; let someone else pay for the privilege of arming your enemies later rather than sooner.** *(templates+code+closure walk, high confidence)*

### "Skip particle weapons" has a closure exception

The fusion-drive path **transitively requires** the global techs `HighEnergyLasers` (1,000 RP) and `ParticleCannon` (5,000 RP) via `Neutronics` (15,000) → `NuclearFusioninSpace` / `DeuteriumTritiumFusion`. Skip the particle-weapon **projects**, not these globals. *(prereq closure walk, high confidence)*

### What victory actually requires

The full Resistance victory research closure (Final Assault incl. Choke Point + Defend the Earth) is **17 nodes / 196,275 template RP — all Xenology projects + Skywatch/DeepSystemSkywatch**. No weapon, drive, or armor branch is transitively required. Drive techs are likewise absent from every victory closure, and refit rules lock drive families (see [Drives Refits and Logistics](Drives%20Refits%20and%20Logistics.md)) — redundant drive lines are the classic research-rich-faction money pit. Details: [Victory Conditions and Endgame](Victory%20Conditions%20and%20Endgame.md).

## 9. Misconception ledger (so they stay dead)

| Claim | Status | Truth |
|---|---|---|
| "Versatility bonus" for spreading categories across slots | **REFUTED** | ×0.9 **penalty** per additional same-category slot; no such symbol in code |
| Completing cheap projects compounds research speed (+5/3/1%) | **REFUTED** | MultipleFacilitiesMultiplier counts **active slot-granting facilities**, projects-only multiplier |
| Category % under 100 means "runs slower than nominal" | **REFUTED** | The figures are bonuses **above** nominal (+87% = 1.87×) |
| 6 × T3 institutes = +150% | **REFUTED** | Soft cap → +66.7%; per-source-class cap asymptote +100% |
| Template→in-game RP ratio varies per project (×0.5–×5.5) | **CORRECTED** | Uniform ×(100/research_rate_pct) — exactly ×0.5 at 200%, screenshot-verified (LESSONS-research R5); the variance reading conflated other effects |
| Project unlocks roll monthly | **CORRECTED** | Daily roll at the monthly-equivalent rate; the rate climbs monthly |
| All labs equal per tier | **REFUTED** | Xenology line 0.10/0.25/0.50 vs 0.025/0.10/0.25 for all others |
| Exofighter tech improves your defense | **REFUTED** | Global tech that arms hostile executive factions vs your LEO; aliens unaffected |
