---
title: Alien Hate and Diplomacy
game_version: 1.0.32 decompile (build 22085164; decompile repo brackets 1.0.30–1.0.33); lessons re-verified through 1.0.38+
---

# Alien Hate and Diplomacy

Campaign-independent reference for the alien (Hydra) hate system: what raises it, what lowers it, what it triggers, and which community myths are dead. Product of the 2026-06 Deep Strategic Review adversarial-verification pass (Phase 3, cluster A) — every fact below was checked against decompiled code and/or local game templates, not model memory or the wiki alone.

> **Evidence vintage caveat (applies to every constant in this note):** decompiled-source citations (`*.cs`) come from a repo whose single commit is dated 2025-06-12, bracketing builds ≈1.0.30–1.0.33 — it is *not* guaranteed byte-identical to the installed 1.0.32 (build 22085164). Template citations (`TIXxxTemplate.json`) ARE from the installed build. Constants can drift across patches: **after any game patch, re-verify templates via `sync_game_data.py` and code constants against an updated decompile.** Known divergence candidates are flagged inline.

> **Difficulty enum (code-verified — never use the old 0–3 community table):** the difficulty int = dropdown index + 1: **1 = Cinematic/Forgiving (`_C`), 2 = Normal (`_N`, the switch *default* branch — case 2 is intentionally absent in code), 3 = Veteran (`_V`), 4 = Brutal (`_B`)**. Evidence: `StartMenuController.cs:285` (`difficulty = dropdown.value + 1`), `TIGlobalConfig.cs` switch pattern (case 1→`_C`, 3→`_V`, 4→`_B`, default→`_N`), `localization/UIOptions.en:199-202` (Difficulty1..4 = Forgiving/Normal/Veteran/Brutal). A save showing `difficulty=2` is **Normal**. Confidence: high.

Reference-campaign numbers below are examples only, labeled "e.g. reference campaign" — that save is **Normal** difficulty, `alienProgressionSpeed = 2.0`, campaign start 2026-02-01, snapshot in-game 2032-05-09, alien→Resistance hate 437.55, used MC 516.

## 1. The hate variable — scale, clamps, key thresholds

Hate is a per-faction-pair float. Every change routes through `GainFactionHate`, which **clamps to [MinimumFactionHate, MaximumFactionHate] on every write** (`TIFactionState.cs:10901-10930`) — nothing (events, peace gestures, the SetAlienHate effect) can push hate below the floor. `SetFactionHate` is implemented as a delta through `GainFactionHate`, so it clamps too (`TIFactionState.cs:10896`). Changes with |value| ≥ 1 are randomized ±20% (`hateVariance = 0.2`, `TIGlobalConfig.cs:2202`). Confidence: high.

| Threshold | Value | Meaning | Evidence |
|---|---:|---|---|
| War | **50** | Aliens move to war as `FactionsGoToWarProgress = hate/50` fills (evaluated monthly); war goal discards if hate < 50 and not Total War | `TIGlobalConfig.cs:2175` `alienFactionHateWarValue = 50f`; `AIEvaluators.cs:5215-5217` |
| Total War | **200** (= 50 × 4) AND time gate (§3) | `FactionGoal_WarOnFaction.cs:176-190` `AlienTotalWarHateThreshold = alienFactionHateWarValue * 4f` |
| Hard floor (ideology) | **20** | Applies when the pair is veryProAlien vs veryAntiAlien (aliens x = −3; Resistance x = 1 ⇒ always for Resistance): floor = max(MC floor, `factionHateConflictThreshold` = 20) | `TIFactionState.cs:10981`; `TIGlobalConfig.cs:2163` |
| Max ceiling | `startingMax + increase × modified-years` | Normal/Veteran/Brutal: **1000 + 100/modified-yr**; Cinematic: 70 + 2/yr. Past the Total-War gate year the ceiling is also floored at 200. Floor overrides max if they ever cross. | `TIGlobalConfig.cs:1845-1866`; `GetAlienHateMaximum()` |

**Modified years** (used by Total War gate, max-hate growth, passive hate, Advanced Master Project): `elapsed calendar years × Customizations.alienProgressionSpeed` (`TIGlobalValuesState.cs:1943`). E.g. reference campaign at 2032-05: 6.27 y × 2.0 = 12.5 modified years; ceiling ≈ 2253 (not binding at hate 437).

## 2. The MC-based hate floor

**Floor = USED Mission Control × per-difficulty multiplier × 0.8^(masking projects)**, then max'd with the hard floor 20 for the veryAntiAlien-vs-alien pair. Confidence: high (code + templates).

- **Used MC**, not built capacity: `missionControlUsage = GetMissionControlRequirementFromShips() + FromHabs(true) + FromRefits()` (`TIFactionState.cs:3455`).
- Formula site: `TIFactionState.cs:10970` `MCBasedAlienHate = missionControlUsage × AI_AlienHatePerMCUtilitizedMultiplier() + SumEffectsModifiers(Context.AlienHateFromMCUsage, …)`.
- The alien AI starts worrying when `MCBasedAlienHate × 1.2 ≥ 50` (`TIFactionState.cs:10966`).

| Difficulty | Hate per used MC | Pre-masking used-MC war-line breakeven (floor = 50) |
|---|---:|---:|
| 1 Cinematic | 0.05 | 1000 |
| 2 Normal | 0.30 | ~167 |
| 3 Veteran | 0.60 | ~83 |
| 4 Brutal | 1.00 | 50 |

Evidence: `TIGlobalConfig.cs:1941-1950`. With masking the breakeven scales by 1/0.8^n: e.g. Normal with 3 projects ⇒ ≤325 used MC keeps the floor under 50; with 4 ⇒ ≤406.

### The 4 masking projects

`Effect_MCUsageMasking` is **Multiplicative 0.8, stackable** ⇒ true 0.8^n, **not** additive −20% each (4 projects = 0.8⁴ ≈ 0.41) (`TIEffectTemplate.json`). Confidence: high.

| Project | Research cost | Availability | Prereqs (template) |
|---|---:|---|---|
| `Project_OperationalSecurity` | 2,500 | **Resistance only** | MilitarizationofSpace, Project_ResistVictory |
| `Project_StrategicDeception` | 10,000 | all factions | ArrivalSecurity, Project_HydraInterrogation |
| `Project_Maskirovka` | 15,000 | all factions | QuantumEncryption, Project_StrategicDeception, Project_TheirTechnology |
| `Project_OperationalMisdirection` | 20,000 | all factions | **FleetLogistics**, Project_StrategicDeception |

(Source: `TIProjectTemplate.json` + phase-1 save empirics. Note FleetLogistics is a 45k tech that also gates Titan hulls — double-duty buy.)

E.g. reference campaign: 516 used MC × 0.3 × 0.8³ = **floor 79.3** (63.4 if OperationalMisdirection is finished) — above the 50 war line either way, so war is MC-locked at that scale; exiting war would additionally require decaying 437→50 at ~0.32/mo (decades).

## 3. Total War

**Trigger (deterministic, checked DAILY inside the alien's existing `WarOnFaction` goal — not an event, not probabilistic):** flip `IsTotalWar = true` when ALL of:

1. hate ≥ **200**, AND
2. modified-years ≥ per-difficulty gate: **Cinematic 25 / Normal 20 / Veteran 12 / Brutal 0** (`TIGlobalConfig.cs:1761-1770` `yearsBeforeAlienTotalWarAllowed_C/N/V/B`), AND
3. target faction is not veryProAlien.

Evidence: `FactionGoal_WarOnFaction.cs:176-190` `DailyGoalMaintenance`. Confidence: high.

**ONE-WAY:** `IsTotalWar` is never unset; `GoalFulfilled()`/`ShouldDiscardGoal()` both require `!IsTotalWar`, so a Total-War goal can never be fulfilled or discarded. Permanent for the rest of the campaign.

**What `IsTotalWar` gates:** per-asset venting on kill disabled (§4 — *only* that vent channel; the knockdown reprieve survives); war goal permanent; alien AI unlocks flagship/exotic ship designs vs that faction; +1 war-goal importance; `AlienFullWarDeclared` notification; fleet-posture goals. (War-goal importance = 15 + 3 × clamp01(hate/200) — useful save-reading cross-check.)

E.g. reference campaign: hate 437 ≥ 200 already, so Total War flips on the exact day modified duration hits 20 y = **~2036-02-02** (start 2026-02-01 + 10 calendar years at 2.0× progression). Until then venting is OPEN — "Total War already locked venting" was a **REFUTED** Phase-2 claim for that save.

## 4. Venting (hate reduction when aliens destroy your stuff)

Aliens reduce hate when they kill an asset of yours **only if all three hold** (`TIFactionState.cs:16275-16325` `RegisterKill`):

1. No Total-War `WarOnFaction` goal vs your faction (limited war / retaliation only), AND
2. the destroyed asset was **not trespassing** in alien turf, AND
3. the aliens had an active/dynamic `AttackWithFleet`-type goal on that exact asset — i.e. *they* wanted it dead. Self-defense kills (your bait sent at them) vent **nothing**.

**Alien turf ("MyTurf", `AIEvaluators.cs:3769`):** any system at/beyond Jupiter's semi-major axis; any system containing an alien BASE (no Earth exemption); any non-Earth system containing an alien STATION.

**Vent amounts** (divide module sums by the per-difficulty divisor — `TIGlobalConfig.cs:929-938` `hateBurnoffFromKillingHabmodulesDivisor`):

| Asset destroyed | Vent | Evidence |
|---|---|---|
| Functional hab module | (tier² + tier if mine + tier if construction module) / divisor | `TISpaceShipState.cs:3280-3300` |
| Under-construction module | same shape, reduced — they DO vent | cluster-A verdict A2 |
| Ship | hull `consTier` (1–3, flat) | `TISpaceShipState.cs:1566` |
| Whole hab | max(habTier [or tier/2 if no core completed], Σ module terms / divisor) | `TIHabState.cs:2586` |

| Difficulty | Divisor | T3 module vents |
|---|---:|---:|
| 1 Cinematic | 2 | 4.5 |
| 2 Normal | 3 | 3.0 |
| 3 Veteran | 4 | 2.25 |
| 4 Brutal | 5 | 1.8 |

### Knockdown reprieve (big, separate, NEVER Total-War-locked)

If your **space-humanity strength share** — fleet SpaceCombatValue share + hab core-MC share among all human factions (`AIEvaluators.cs:5653+5540`) — drops **>35% below your own peak since the last knockdown**, aliens vent a fraction of **CURRENT** hate, then your peak resets (`TIFactionState.cs:16312-16321` — branch is outside the IsTotalWar gate):

| Difficulty | Fraction of current hate vented |
|---|---:|
| 1 Cinematic | 0.50 |
| 2 Normal | 0.35 |
| 3 Veteran | 0.15 |
| 4 Brutal | 0 |

Evidence: `TIGlobalConfig.cs:1881-1890` `alienHateReprieveAfterKnockdown`. Confidence: high. E.g. reference campaign: a knockdown at hate 437 vents ~−153 in one event. A major fleet/hab loss automatically buys this even during Total War. (Save field `highestSpaceStrengthSinceLastAlienKnockdown` tracks the peak.)

## 5. Hate from combat — and the zero-hate exemptions

**Hate per ship killed = 0.4 × hull structuralIntegrity, randomized ±20%.** One single code path; serves alien AND human victims alike; no cap, no class special-casing. `TISpaceCombatState.cs:1386`; `TIGlobalConfig.cs:2148` `factionHateSIFactorPerShipDestroyed = 0.4f`.

- **REFUTED myth: "hate += hull SI per kill."** AlienBattlecruiser SI 48 would give 48; code gives 19.2 ± 3.8. The escort anomaly (~3.5/kill observed) is resolved by the scalar: 0.4 × 10 = 4.0 ± 0.8.
- **Open question (uncalibrated coefficient): 0.4 (decompile) vs 0.35 (wiki).** The wiki's own 31.5-per-AssaultCarrier figure is internally consistent with 0.35 — which may be the *older or installed-build* constant; the shipped `TIGlobalConfig.json` template does not override hate constants, so the installed build's truth lives only in its `Assembly-CSharp.dll`. Both fit the small-hull empirics (0.35×10 = 3.5; 0.4×10 = 4.0±0.8). **n=1 settle:** kill one isolated alien ship and read the intel hate-estimate delta — it updates live via `UpdateEstimatedAlienHate`.

**Alien hull SI table** (multiply by 0.35–0.4 for hate per kill; `templates/TIShipHullTemplate.json`): Gunship 6 · Escort 10 · Corvette 10 · Frigate 20 · Monitor 22 · Destroyer 24 · Cruiser 36 · Battlecruiser 48 · Lancer 52 · Battleship 60 · Dreadnought 72 · Titan 90 · AssaultCarrier 90 · Mothership 512.

### Zero-hate combat rules (1.0.32) — defense is free

When a ship dies, the killer gains **no** hate if ANY of (`TISpaceCombatState.cs:1340-1366` `GainCombatFactionHate`):

1. Combat occurred **at a hab owned by the killer's faction** (park defense fleets on your stations — unconditional exemption);
2. the victim's fleet was the combat's **Attacker** (`Attacker = fleets[0]`, fixed at encounter creation, `TISpaceCombatState.cs:60` — your Accept-vs-Engage stance choice cannot change it);
3. the victim's fleet had an **offensive goal (AttackWithFleet / CaptureHab) targeting the killer's faction within the last 14 days** (incl. its current goal; `TIFactionGoalState.cs:459`).

Corollary: **intercepting an alien fleet en route to attack you is hate-free** in this build (exemption 3 covers it) — the old claim "interception always costs hate even on Accept" is wrong here. Hate accrues only when you hunt alien fleets that had not targeted you, at a modest, quantifiable 0.4×SI each.

**1.0.34-beta change note:** the beta adds a victim-capable-of-spontaneous-aggression check to `GainCombatFactionHate` (and a minimum-trade-value gate on trade-hate) — **absent in 1.0.32** (verified by code-body inspection, cluster F verdict 109). Re-verify this whole section after switching builds.

### Other combat hate reference costs (TIGlobalConfig.cs)

| Action | Hate | Evidence |
|---|---|---|
| Destroy a hab | 1 + 3 × tier (+1 × moduleTier per module destroyed in combat) | `TIHabState.cs:2518`; `:2139` |
| Assault a hab | 8 × tier | `:2136` |
| Initiate bombardment (any target) | 1 | `:2154` |
| Kill a xenoform | ~10 each (save-empiric, lifetime counter; lower confidence) | phase-1 empirics |

### Hate spill (conflagration) between factions

When the aliens gain hate vs you, related factions feed: **Proxy (Servants)** gains value/2 if you've contacted aliens, else /4; **Appeaser** gains value/3 (only when the appeaser can contact aliens). Attacking the *Proxy* feeds the aliens value/4 (contacted) or /8. Fighting Exodus/HF does **not** feed alien hate. (`TIFactionState.cs:10930-10960`.) Confidence: high.

## 6. Passive hate growth and decay

**Monthly gain** (applied day 1 of each month, `AIDailyFactionPlanner.cs:365-402` `GetMonthlyAlienHateGain`):

`gain = [components] × steadyHateGainModifier(difficulty) × modified-years / 60`

Components (corrected vs wiki, which overstated by treating them as two independent +0.65s):
- **+1.3** if you are the aliens' most-threatening human enemy AND the strongest human faction; **+0.65** if most-threatening but not strongest; **0** if strongest-but-not-most-threatening;
- **+0.5** if you hold the anti-alien victory objective;
- ideology: antiAlien **+0.07**, veryAntiAlien **+0.10** (Resistance x=1 gets both = +0.17), extremist (|x| ≥ 2) +0.17.

| Difficulty | steadyAlienHateGainModifier |
|---|---:|
| 1 Cinematic | 0 |
| 2 Normal | 1.0 |
| 3 Veteran | 1.9 |
| 4 Brutal | 3.3 |

Evidence: `TIGlobalConfig.cs:1809-1818`. Note the ×modified-years/60 term: passive growth accelerates with campaign age × progression speed — *time works against you; winning fast dominates* (wiki "war by year ~17 on Veteran with zero hostile actions" table: plausible-unverified; the generating function `GetExpectedYearsUntilWarWithAliens` exists and matches the inputs, but was not recomputed; lands later on Normal).

**Decay:** monthly −1 × 0.8 (alien) × 0.8 (antiAlien target) = **−0.64**, applied only to the aliens' most-threatening enemy and only on **even months** (`generalDeescalation = month%2==0`) ⇒ effective ~−0.32/mo for a most-threatening Resistance player; ×1.5 possible when aliens fight >2 factions and you are NOT most-threatening. (`AIDailyFactionPlanner.cs:528-531`.)

## 7. Hate reducers — complete inventory

| Channel | Amount | Who can use it | Evidence |
|---|---|---|---|
| Trade with aliens | −9 per equal trade (−8 treaty − 1 trade), **−18** when favorable to the AI (modifier 2 above `goodTradeThreshold`) | **proAlien factions only** (`CanContactAlien` requires ideology x < 0 + story progress) — Resistance (x=1) can NEVER trade with aliens | `TIGlobalConfig.cs:2157-2160`; `TIFactionState.cs:14715,17147`; `DiplomacyController.cs:676-686` |
| `Project_CoexistencePact` → `Effect_SetAlienHate0` | hard reset to 0 (still floor-clamped) | **AppeaseCouncil only** | `TIProjectTemplate.json` |
| Masking projects | floor only (§2) — do not reduce current hate | any (1 Resistance-only) | §2 |
| Per-asset venting | §4 amounts | anyone the aliens attack, pre-Total-War | §4 |
| Knockdown reprieve | 0.5/0.35/0.15/0 × current hate | anyone, **even in Total War** | §4 |
| Passive decay | ~−0.32 to −0.64/mo (§6) | most-threatening enemy | §6 |

So for an anti-alien faction the only *player-initiated* reducer is engineering a vent or a knockdown; "nothing can lower hate" is too fatalistic, but no lever moves hundreds of points except the knockdown reprieve.

## 8. Displayed vs true hate — Effect_FixAlienThreatMeter

The intel-screen value (`assessedAlienHateOfMe`) tracks true hate **LIVE** — kills move the display within days and the floor component ticks with MC changes. *(Supersession note, 2032-02-27: the earlier read of this section — "a snapshot frozen at the last fix event (`lastDateOfFixedAlienHate`), jumping only on the next fix" — is superseded. The 26-save dataset it rested on showed displayed hate flat at 255.86 for a month, but that plateau was an **equilibrium** — MC-floor growth ≈ above-floor decay — not a frozen meter: a controlled fleet-kill save moved the display 339.33 → 413.35 (+74.0) while `lastDateOfFixedAlienHate` stayed pinned. See [LESSONS-aliens](../lessons/LESSONS-aliens.md) A1.)* `Effect_FixAlienThreatMeter` (Their Purpose / Their Demands / Hydra Diplomacy) is **INSTANT** — it recalculates the meter once (`UpdateAlienThreatMeter_Accurate`); it does *not* reduce hate, does *not* buy a "free-build window," and in practice shows near-zero visible change because the meter was already accurate.

## 9. Alien Advanced Master Project (the escalation clock)

`Project_AlienAdvancedMasterProject` auto-completes when **modified-years > Cinematic 35 / Normal 25 / Veteran 16 / Brutal 10** (`TIGlobalConfig.cs` `yearsBeforeAlienAdvancedTech_C/N/V/B`; fired from `TIFactionState.MonthlyFactionUpdate:1859`). Grants the aliens `Effect_ShipConstructionTimeReduction` (×0.8 build TIME = **+25% build rate**) **+ 5,000 exotics** (`TIProjectTemplate.json`, `TIEffectTemplate.json`). Confidence: high.

E.g. reference campaign: not fired as of 2032-05 (string absent from save); on Normal at 2.0× progression it fires at elapsed > 12.5 y ⇒ **~2038-08** (per the code-derived date in Alien Production Rebuilding and Targeting). This plus the Total-War date (§3) quantifies the strike-timing window.

## 10. Misconception graveyard (do not resurrect)

- **REFUTED:** "hate += hull SI per ship killed" — it's 0.4 (or 0.35) × SI ± 20% (§5).
- **REFUTED:** "Total War time gate is a flat 10 years on Veteran" — it's per-difficulty 25/20/12/0 **modified** years vs progression-scaled elapsed time (§3).
- **REFUTED:** "masking is −20% additive per project" — multiplicative 0.8^n (§2).
- **REFUTED:** "knockdown reprieve and councilor-kill venting are Total-War-locked" — only the per-asset vent is (§4).
- **REFUTED:** "intercepting inbound hostiles always generates hate" — not when their goal targeted you within 14 days (§5; 1.0.32).
- **REFUTED:** "trade is available to everyone as a hate reducer" — proAlien ideology gate (§7).
- **REFUTED (campaign-class error):** reading `difficulty=2` as Veteran. 2 = Normal. The entire Phase-0–2 "Veteran" premise of the 2026-06 review was wrong; every `_V` constant had to be re-read as `_N`.

Related: [Victory Conditions and Endgame](Victory%20Conditions%20and%20Endgame.md) · [Space Combat Math](Space%20Combat%20Math.md) · [Mechanics index](README.md)
