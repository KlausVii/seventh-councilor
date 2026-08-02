---
title: Earth Endgame Consolidation
game_version: 1.0.32 (build 22085164)
---

# Earth Endgame Consolidation

> **Evidence vintage caveat (applies to all code citations in this note):** decompiled-source evidence is from a repo bracketed to builds 1.0.30–1.0.33 (commit 2025-06-12). Constants could drift in newer builds — re-verify after any game patch (templates via `sync_game_data.py`; code via the repo if updated).

## Verdict (expanded)

### What the win actually demands from Earth

`vc_resistVictory` has exactly three conditions, and only ONE touches Earth: **`AlienNationMaxRegionProportion = 0`** — literally zero Earth regions inside the Alien Nation at the moment the win mission runs (`GameStateManager.AlienNation.regions.Count / all-regions ≤ 0`). There is **no CP-count, nation-count, GDP, or unification condition anywhere in the Resistance victory chain** (the other two conditions are space-side: no alien T3 surface bases, no alien fleet ≥ 4000 SCV — see [Capital Ship Doctrine](Capital%20Ship%20Doctrine.md) § victory and the Mechanics notes).

**Corollary:** every Earth CP beyond what funds/researches/defends your space program is optional. "Unite Earth to win" is a player preference, not a mechanic.

### How much CP is enough (the tall criterion)

Enough CP to (a) fund the space program, (b) keep research income dominant, (c) deny the Alien Nation footholds. Mechanics that size the answer:

- **CP cap inputs** (separate from MC): global `controlPointMaintenanceFreebies` (+125 in the reference campaign's save), `AdministrationNode/Tower/Complex` modules in **Earth-LEO habs only** (+4/+12/+30 class; habs outside LEO don't count), and stacked `ControlPointMaintenanceBonus` project effects. Going over cap exposes space assets to accident/seizure penalties.
- **Funding mechanics**: each Funding priority completion adds `fundingPriorityBaseIncomeIncrease + numControlPoints` to annual funding, hard-capped at **0.5 % of nation GDP (in millions)**; owning the **FinancialSector** CP multiplies the payout (`financialSectorFundingBonus`). So a few huge-GDP nations with the Financial Sector CP beat many small ones.
- **Research flows through CP share**: your research from a nation = nation output × your CP ownership share — full ownership of a few research giants dominates scattered minority stakes ([Converting a Research Lead](Converting%20a%20Research%20Lead.md)).
- **Spoils degrades**: each Spoils completion damages sustainability + environment — Spoils-farming hollow nations is a real cost, not free money ([Late-Game Money](Late-Game%20Money.md)).

### Formation (meganation) projects

~12 union/federation-forming projects exist in 1.0.32 by display name (African Union, South American Union, Nordic Federation, Central Asian Union, Maghreb, etc.). Their value is **consolidation efficiency** — fewer, bigger nations mean fewer CPs to defend for the same GDP/research, larger armies against alien-controlled neighbors, and fewer rival entry points. None are victory-required. (The community's "~48 total unification/breakup projects" count could not be reproduced — unverifiable.)

**Federation ≠ unification — they are two steps, and only the second consolidates CPs.** *Federating* nations keeps them separate (they retain their own control points, governments, and regions); it grants pooled Funding/Boost, an Economy-priority investment bonus, and mutual defense, and it is the **prerequisite** for *unifying* them. *Unification* is the actual merger that collapses the members into one nation — that is where the "fewer CPs to defend" payoff above lives. So "federate to cut my CP maintenance" does nothing on its own; federate to start the clock toward a unification that will. The federation's lead nation is fixed by claim count, not chosen. Full mechanic decode (code + localization): [LESSONS-politics](../lessons/LESSONS-politics.md) C16.

### Denying the Alien Nation

Since the win requires the Alien Nation at zero regions, the Earth endgame task is **containment/eviction**, not conquest: keep armies and CP presence sufficient to evict alien-controlled regions before the win mission, and prevent Servant-fed expansion. (The detailed army/eviction mechanics were not part of this review's verified set — flag for a future question.)

## Evidence

**Tier 1 (code/templates, verified):** `TIVictoryTemplate.json` vc_resistVictory (AlienNationMaxRegionProportion 0, FreeBases_DefeatAliens 3, FreeFleets_DefeatAliens 4000); `TIVictoryTemplate.cs` region-proportion check; `TIMissionTemplate.json` ResistWin conditions (TargetInRange/Human/VictoryCondition — no Earth-control condition); `TINationState.cs:5380–5393` funding increment + `:5370` 0.5 % GDP cap + `:4127` FinancialSector multiplier; Spoils sustainability/environment penalties (~:5364); localization — 12 union/federation project display names. *(high)*

**Tier 1 (save-empiric):** CP-cap inputs (freebies +125, AdministrationNode +40 total, ControlPointMaintenanceBonus effects ≈+212). *(high, this save)*

**Confidence note:** this question received thinner adversarial coverage than the combat/economy clusters — the victory-condition and funding mechanics are code-verified (high), but the "how much is enough" sizing is synthesis (medium). No REFUTED myths specific to this note beyond the general ~~"you must unite Earth to win"~~ — refuted by the victory template itself.

## Worked example — the reference campaign (Resistance, 2032-05 snapshot)

- The player holds **19 CPs**, concentrated in three great-power pillars held at or near full control plus one partial hold — already the tall pattern: ~55 % of the player's ~272 RP/day comes through nation CP share (~150 RP/day from the three pillars alone). No Earth expansion is needed for victory; the marginal Earth move is defending these pillars.
- CP load ≈608 vs explained cap inputs ≈377 (+ unverified org/councilor cap sources) — cross-check the in-game CP tooltip before adding CPs; if over cap, build AdministrationNodes in LEO or drop low-value CPs (Mass Media/Trade Unions class).
- The Alien Nation held zero-to-marginal Earth regions at snapshot; the Earth side of victory is currently nearly satisfied — keep it that way rather than expanding.

## Sources

- https://www.reddit.com/r/TerraInvicta/comments/1qg7inx/end_game_nation_control_strategies/ + …/1nqhl6k/is_a_united_earth_really_the_best_way_to_control/
- https://wiki.hoodedhorse.com/Terra_Invicta/Victory
- Local templates build 22085164 + decompile (github.com/Armandox33/Terra-Invicta-AI-Assistant); save-empirics 2032-05-09
- Related: [Late-Game Money](Late-Game%20Money.md) · [Converting a Research Lead](Converting%20a%20Research%20Lead.md) · [Hate Management at Scale](Hate%20Management%20at%20Scale.md)
