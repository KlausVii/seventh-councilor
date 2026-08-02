---
title: LEO Defense Doctrine
game_version: 1.0.32 (build 22085164)
---

# LEO Defense Doctrine

> **Evidence vintage caveat (applies to all code citations in this note):** decompiled-source evidence is from a repo bracketed to builds 1.0.30–1.0.33 (commit 2025-06-12). Constants could drift in newer builds — re-verify after any game patch (templates via `sync_game_data.py`; code via the repo if updated). **Specific flag for this note:** the 14-day victim-goal exemption and the 0.4 hate constant could not be byte-verified against the installed 1.0.32 binary (the wiki's 0.35 may be the older constant). Cheap n=1 test: kill one isolated alien ship and read the intel hate-estimate delta — it applies the exact gained value live.

## Verdict (expanded)

### The three zero-hate exemptions (the doctrine's foundation)

When a ship dies, the killer gains NO hate if any of (`TISpaceCombatState.GainCombatFactionHate`):

1. **The combat occurred at a hab owned by the killer's faction.** Unconditional — parking defense fleets on your stations makes every defensive battle free.
2. **The victim's fleet was the combat's Attacker.** Attacker = `fleets[0]`, fixed at encounter creation — the player's Accept-vs-Engage stance choice cannot change attacker status.
3. **The victim's fleet held an offensive goal (AttackWithFleet / CaptureHab) targeting the killer's faction within the last 14 days** — including its currently assigned goal.

**The 14-day rule is the refinement that updates old doctrine:** intercepting an alien fleet *en route to attack you* is hate-free — exemption (3) covers it. The wiki's "interception generates hate even on Accept" is wrong whenever the inbound fleet's goal targets you. Interception only costs hate against fleets with no recent offensive goal vs you (patrols, fleets tasked elsewhere). So: **park AND sortie against committed attackers; only elective hunts are priced** (0.4 × hull SI ± 20 % per kill — see [Hate Management at Scale](Hate%20Management%20at%20Scale.md) for the full action-hate table).

Same code path serves alien and human victims alike — the doctrine works against human raiders too.

### Station-side defense mechanics

- **Hab combat strength** = Σ SpaceCombatValue of **active** combat modules (active = functional && **powered**). Battlestation-class modules + docked fleets defend together; an enemy fleet can only land/assault troops at a site once hab SCV ≤ 0.
- **Hab ground defense** = coreTier + Σ marine-rule module values × command-adviser multiplier + docked-fleet contribution **− faction MC shortage** (see below). Marine barracks the player can build: MarinePlatoonBarracks 10 / MarineCompanyBarracks 20 (researched); MarineBattalionBarracks 40 needs Project_RingCore.
- **Hab destruction costs the attacker hate** (1 + 3×tier) — aliens included, which is why aliens bombarding your LEO feeds your venting channels when they had attack goals ([Base Sacrifice and Hate Venting](Base%20Sacrifice%20and%20Hate%20Venting.md)).
- **Exploit-dodges are dead on this build:** a hab cannot *start* decommissioning while under bombardment; module cancel/decommission is blocked under bombardment; decommissioning habs remain bombardable.
- **AI hab capture exists on 1.0.32** (CaptureHab goals are created and executed; 1.0.34 broadened it) — stations face capture, not just bombardment; garrison accordingly.
- **What paints a target:** owning one completed antimatter-producing module puts the hab on the alien attack-goal list ([Exotics and Antimatter Acquisition](Exotics%20and%20Antimatter%20Acquisition.md)); generally the aliens attack assets their goals select — your LEO economy is exposure, which is the MC-floor story again.

### Never run an MC deficit (two separate penalties)

1. **Hab Module Malfunction event**: fires when MC balance < 0, with weight multipliers ×3/×6/×10 at balance −50/−100/−200, escalating from destroying 2 → 4 → 8 modules (escalation outcomes weight-0 with conditional modifiers at <−100/<−200). Note: a 1.0.34 changelog implies the escalation modifiers were *under-applied* on 1.0.32 — deficits are under-punished on this build but the structure is armed.
2. **Direct combat penalty**: `TIHabState.ModifiedDefenseCombatValue` subtracts the faction's `MissionControlShortage` from every hab's defense value — an MC deficit weakens all your habs against assault simultaneously.

## Evidence

**Tier 1 (code/templates, verified):** `TISpaceCombatState.cs:1340–1366` GainCombatFactionHate (three exemption flags; victim `GetRecentGoalInfo(14f)` ∩ OffensiveFleetGoals vs causing faction); `:60` Attacker => fleets[0]; `TIFactionGoalState.cs:459` OffensiveFleetGoals = {AttackWithFleet, CaptureHab}; `:1386` hate = SI × 0.4 (`TIGlobalConfig.cs:2148`) ±20 % (`:2202`); `TIHabState.cs:1187` SCV = active modules; `LandOnSurfaceOperation.cs:74` SCV ≤ 0 gate; `TIHabState.CanDecommissionHab:15565` + `TIHabModuleState.cs:1270` bombardment blocks; `TINarrativeEventTemplate.json` event_HabModuleMalfunction (3/6/10 weights; 2/4/8 modules); `TIHabState.ModifiedDefenseCombatValue` MC-shortage subtraction; `FactionGoal_FoundBase.cs:195` + `TISpaceFleetState.cs:3333–3345` AI CaptureHab on 1.0.32. *(high, with the version flag above on the 14-day check + 0.4)*

**Verdict provenance:** zero-hate exemptions VERIFIED (MODIFIED vs wiki: the interception claim corrected by the 14-day rule); 0.35/ship-SI wiki figure REFUTED for this decompile (0.4); MC-deficit event structure VERIFIED; exploit removals VERIFIED; "stations only face bombardment on 1.0.32" MODIFIED (AI capture exists, rarer).

**REFUTED/corrected myths:** ~~"Any sortie generates hate"~~ — committed attackers are free game · ~~"Accept vs Engage changes who counts as attacker"~~ — fixed at encounter creation · ~~"You can decommission-dodge bombardment"~~ — dead on this build.

## Worked example — the reference campaign (Resistance, 2032-05 snapshot)

- The player holds 11 Earth-LEO habs (8+ market-capable stations) — the backbone of money and CP cap ([Late-Game Money](Late-Game%20Money.md), [Earth Endgame Consolidation](Earth%20Endgame%20Consolidation.md)). Defense fleets parked on these stations fight at exemption (1) unconditionally.
- Current MC: 563 available vs 516 used — slack +47, **but ~140 MC of latent demand** sits in unpowered/under-construction mines and idle shipyards; re-enabling infrastructure without MC headroom walks into both deficit penalties. MC overage history last 32 days: zero — keep it that way.
- With 57 alien torpedo bays in the opfor, station PD composition follows [Weapon Doctrine vs the Hydra](Weapon%20Doctrine%20vs%20the%20Hydra.md) § PD matrix (keep 40 mm against mag weapons; PD Ion is the cheap missile screen).
- The hate cost of defending LEO this entire war so far: ~zero, if engagements stay in the three exemption channels. Maintain it; the 437 hate is from the MC floor and history, not from defense.

## Sources

- https://wiki.hoodedhorse.com/Terra_Invicta/Aliens (zero-hate exemption claims)
- https://www.reddit.com/r/TerraInvicta/comments/1qvs0th/how_to_develop_when_alien_destroys_your_stations/
- https://www.pavonisinteractive.com/phpBB3/viewtopic.php?f=26&t=29984 (1.0.34 changelog context; Claude-in-Chrome MCP)
- Decompile: https://github.com/Armandox33/Terra-Invicta-AI-Assistant; templates build 22085164; save-empirics 2032-05-09
- Related: [Hate Management at Scale](Hate%20Management%20at%20Scale.md) · [Base Sacrifice and Hate Venting](Base%20Sacrifice%20and%20Hate%20Venting.md) · [Offense Timing vs Aliens](Offense%20Timing%20vs%20Aliens.md)
