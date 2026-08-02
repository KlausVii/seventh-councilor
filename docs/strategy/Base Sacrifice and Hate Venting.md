---
title: Base Sacrifice and Hate Venting
game_version: 1.0.32 (build 22085164)
---

# Base Sacrifice and Hate Venting

> **Evidence vintage caveat (applies to all code citations in this note):** decompiled-source evidence is from a repo bracketed to builds 1.0.30–1.0.33 (commit 2025-06-12). Constants could drift in newer builds — re-verify after any game patch (templates via `sync_game_data.py`; code via the repo if updated).

## Verdict (expanded)

### The per-asset vent — three conditions, all required

When the aliens destroy one of your assets, they vent hate (negative `GainFactionHate`) **only if all of**:

1. **No Total War**: the alien `WarOnFaction` goal vs you has `IsTotalWar == false`.
2. **The asset was NOT trespassing in alien turf.** Alien turf (`AIEvaluators.MyTurf`): any system at/beyond **Jupiter's semi-major axis**; any system containing an **alien base** (no Earth exemption); any non-Earth system containing an **alien station**. Bait sent into their territory vents *nothing*.
3. **The aliens had an active/dynamic attack-type goal on that exact asset** (`AttackWithFleet` goal or `FactionGoal_Fleet.dynamicAttackTarget` == the destroyed asset). Kills made in self-defense — things you threw at them — vent nothing.

**Practical reading:** sacrificial assets must be things the aliens *chose* to attack, on your side of the line. You cannot manufacture venting by feeding them ships in their space.

### Vent amounts (per-difficulty divisor)

| What dies                 | Hate vented                                                         |
| ------------------------- | ------------------------------------------------------------------- |
| Functional hab module     | tier² (+tier if mine, +tier if construction module) ÷ divisor       |
| Under-construction module | same shape, reduced — they DO vent                                  |
| Ship                      | hull `consTier` (1–3)                                               |
| Whole hab                 | max(habTier [tier/2 if no core complete], Σ module terms ÷ divisor) |

Module-vent divisor `hateBurnoffFromKillingHabmodulesDivisor` by difficulty (1=Cinematic, 2=Normal, 3=Veteran, 4=Brutal):

| Cinematic | Normal | Veteran | Brutal |
|---:|---:|---:|---:|
| 2 | 3 | 4 | 5 |

E.g. a T3 module on Normal vents 9/3 = **3.0** hate (not the 2.25 the Veteran-keyed community table gives).

### The knockdown reprieve — the big one, and it never locks

If your **space-humanity share** (your fleet SpaceCombatValue share + hab core-MC share, vs *your own peak since the last knockdown* — `AIEvaluators.ComputeFactionStengthEstimates`) drops **more than 35 %**, the aliens vent `alienHateReprieveAfterKnockdown` × **CURRENT hate**, then your peak resets:

| Cinematic | Normal | Veteran | Brutal |
|---:|---:|---:|---:|
| 0.50 | 0.35 | 0.15 | 0 |

This is **not gated by Total War** (it lives in a separate branch of `TIFactionState.RegisterKill`) — a catastrophic fleet/hab loss buys an automatic hate rebate even during permanent war. Councilor-kill venting is likewise not Total-War-gated; **only the per-asset vent is**.

### Total War — the foreclosure clock (deterministic, per difficulty)

Total War flips when **hate ≥ 200** (= `alienFactionHateWarValue` 50 × 4) AND **progression-modified campaign years** (= elapsed years × `alienProgressionSpeed`) reach the difficulty gate, checked **daily** inside the alien's existing `WarOnFaction` goal (not an event, not probabilistic; requires target not veryProAlien):

| | Cinematic | Normal | Veteran | Brutal |
|---|---:|---:|---:|---:|
| `yearsBeforeAlienTotalWarAllowed` (modified years) | 25 | 20 | 12 | 0 |

**IsTotalWar is one-way** — never unset; the goal can never be fulfilled or discarded. Total War: disables per-asset venting, makes the war goal permanent, unlocks alien flagship/exotic ship designs against you, +1 war-goal importance.

### Is deliberate sacrifice ever correct?

Rarely as an *engineered* play: you can't choose what they target, trespassing assets don't count, and the vent per asset is small (a T3 module ≈ 3 hate on Normal vs a war threshold of 50 and typical war-time hate in the hundreds). Where it IS correct:

- **Don't over-defend doomed low-value assets** the aliens have committed against — the loss pays a rebate and may trigger the knockdown reprieve at no extra strategic cost.
- **Before the Total War date**, losing a big chunk of space-share in one engagement converts 35 % (Normal) of current hate into breathing room — if a major defeat is coming anyway, taking it in one concentrated knockdown beats bleeding slowly.
- After Total War, only the knockdown reprieve remains; per-asset sacrifice is mechanically dead.

## Evidence

**Tier 1 (code, verified):**
- `TIFactionState.cs:16275–16325 RegisterKill` — vent condition triple (attack-goal-on-target ∧ ¬IsTrespassing ∧ (no war goal ∨ ¬IsTotalWar)); separate knockdown branch `if 1 − spaceStrength/highestSinceLastKnockdown > 0.35 → GainFactionHate(hate × −AlienHateReprieveAfterKnockdown)`. *(high)*
- `TIGlobalConfig.cs:929–938` divisors 2/3/4/5; `:1881–1890` reprieve 0.5/0.35/0.15/0; `:1761–1770` Total-War gates 25/20/12/0; `:2175` `alienFactionHateWarValue = 50f`. *(high)*
- `TISpaceShipState.cs:3280–3300` module vent math; `:1566` ship vent = hull consTier; `TIHabState.cs:2586` whole-hab vent. *(high)*
- `FactionGoal_WarOnFaction.cs:176–190` — `AlienTotalWarHateThreshold = alienFactionHateWarValue × 4`; daily deterministic check; `GoalFulfilled`/`ShouldDiscardGoal` both require `!IsTotalWar`. *(high)*
- `TIGlobalValuesState.cs:1943` — modified duration = exact campaign years × `alienProgressionSpeed`. *(high)*
- `AIEvaluators.cs:3769 MyTurf`; `:5653+5540` space-strength definition. *(high)*

**Verdict provenance:** wiki venting-conditions claim VERIFIED verbatim (with the trespass condition added); vent amounts MODIFIED (difficulty-keyed, the community used Veteran values); "10 years on Veteran" time gate MODIFIED (it's 12 modified years on Veteran, 20 on Normal, vs progression-modified duration); "Total War has already locked venting" REFUTED for the reference campaign (see below).

**REFUTED myths:**
- ~~"Total War locks all hate venting"~~ — only the per-asset vent; knockdown reprieve and councilor-kill venting survive.
- ~~"Sacrifice bait fleets in alien space to vent hate"~~ — trespassing assets never vent.

## Worked example — the reference campaign (Resistance, 2032-05 snapshot)

- Campaign is **Normal** difficulty, started 2026-02-01, `alienProgressionSpeed 2.0`. Total War flips deterministically when 6.27 elapsed years × 2.0 reaches 20 → **≈2036-02-02 in-game** (hate 437.55 ≥ 200 already; the alien WarOnFaction goal exists, importance 18 = 15+3×clamp01(hate/200), cross-validating the read). As of 2032-05 `IsTotalWar=false` — **the venting window is OPEN for ~3.7 more in-game years**, contrary to several Phase-2 claims.
- Knockdown reprieve at current hate 437 ≈ **−153 hate** in one event (0.35 on Normal).
- Vent divisor 3, not 4; module vents are ⅓ bigger than the Veteran-keyed tables suggest.

## Sources

- https://wiki.hoodedhorse.com/Terra_Invicta/Aliens · https://wiki.hoodedhorse.com/Terra_Invicta/Victory (MediaWiki api.php)
- Decompile: https://github.com/Armandox33/Terra-Invicta-AI-Assistant
- Save-file empirics, 2032-05-09 save (difficulty enum, hate value, goal importance)
- Related: [Hate Management at Scale](Hate%20Management%20at%20Scale.md) · [LEO Defense Doctrine](LEO%20Defense%20Doctrine.md) · [Offense Timing vs Aliens](Offense%20Timing%20vs%20Aliens.md)
