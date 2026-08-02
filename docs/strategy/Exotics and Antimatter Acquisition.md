---
title: Exotics and Antimatter Acquisition
game_version: 1.0.32 (build 22085164)
---

# Exotics and Antimatter Acquisition

> **Evidence vintage caveat (applies to all code citations in this note):** decompiled-source evidence is from a repo bracketed to builds 1.0.30–1.0.33 (commit 2025-06-12). Constants could drift in newer builds — re-verify after any game patch (templates via `sync_game_data.py`; code via the repo if updated). One version-skew flag specific to this topic: the 1.0.32 templates name an effect (`GainExoticsFromSpaceIndustry`) the decompiled enum lacks — exotics-grant logic carries slight version risk.

## Verdict (expanded)

### Exotics — the complete 1.0.32 acquisition list (exhaustive, template-verified)

**There is NO human exotics income.** Grep of all 156 hab module templates: only alien modules produce exotics (AlienWormholeFacility 10/mo). No market purchase path exists. No game-wide quantity cap exists either (the "capped at a few hundred" myth is REFUTED — `CanAmassExotics` is a boolean unlock; the alien faction holds 2,259 in this save). Human paths:

1. **Capture alien habs — the farm.** Bonus exotics = `3 × habTier × (1 + SL) × rand(0.8–1.2)`, plus materials refund, under-construction-ship exotics, intel, milestones, **FactionExposed** (every alien councilor revealed) and assessed-hate sync — canonical loot formula and worked T3 numbers: [Economy Markets and Loot](../mechanics/Economy%20Markets%20and%20Loot.md) § Path 1.
   - Success levels: **marines-only assault → SL −1 (success) / 0 (crit)** → bonus exotics ZERO / ≈7–11 on a T3.
   - **Councilor-led Seize Space Asset → SL 1 / 3** → T3 yields **≈14–22 normal / ≈29–43 crit** — the community's "20–30 with councilor, <1 with marines" is the mechanic, not anecdote.
   - **Capture quirk (code-confirmed): on Seize success/crit the code returns BEFORE the attacker-damage block** — a successful councilor assault inflicts zero damage on your marine ships; only failures hurt. The reusable "yeet fleet" farming pattern is sound, cadenced by the monthly mission cycle.
   - Alien-hab "capture" always loots-then-DESTROYS (no operating captured alien habs). Destroy Hab op salvages 10 %; nuclear/AM **bombardment** of a hab destroys with **0 %**.
2. **Ship-kill salvage (thin):** exoticsCost × rand(0–0.85) × difficulty salvage rate (Normal 1.0, Veteran 0.5 — the reference campaign is Normal) ÷ alienProgressionSpeed × **(0.2 + fleet SalvageBonus)** (soft-capped ~0.25+; SalvageBay +0.1/module) → effectively ~2–10 % of component cost per kill. **AoE/nuked ships yield salvage like any other kill** — the "no salvage from nuke kills" rule does NOT exist in 1.0.32 code (myth REFUTED; the true analogue is the hab-bombardment 0 % above). Salvage applies to human exotic-built ships too (Servant/Protectorate Phaser ships are lootable).
3. **Earth Assault Alien Asset councilor mission:** 3 × rand(0.75–1.25) = **2.25–3.75 per facility, crit included** (no crit doubling — claim corrected).
4. **FutureTechMaterials endgame tech** (100k, repeatable end-game reroll): +20 exotics to ALL human factions per completion.

**Spend-side discipline:** budget exotics for the endgame guns — 960 cm UV Phaser ≈3.6 each, SpinalSiegeCoilerMk3 ≈6; mid-tier exotic spends (UV Arc cannons, Exotic/Hybrid armor, exotic radiators) strand the endgame. AM particle weapons need **zero exotics** (trace AM only) — the exotics-free heavy-beam path if you ever have AM.

### Antimatter — production table and the skip verdict

| Source | Output | Notes |
|---|---:|---|
| ParticleCollider (T1 station) | 0.0001/mo | +1 fissile/mo support → 10,000 fissiles per AM |
| Atomsmasher (T2) | 0.01/mo | 3 fissiles/mo → 300 per AM |
| Supercollider (T3) | 0.1/mo | 10 fissiles/mo → **100 per AM**; +120 money +30W/30V/20M/20NM monthly support |
| Natural harvesting | ~1.67e-12/mo | Best orbit (SynchronousSaturnOrbit, 200 µg/yr) × AntimatterFarm 100 %; one harvester per orbit. **Provably useless.** |

- **Alien loot contains ZERO antimatter**: no alien hull/drive/reactor/module has AM in build materials (alien drives burn pure water); the alien faction's AM stockpile (22.06 in save) does NOT transfer on capture. "Salvage/capture aliens for AM" is REFUTED.
- **Nothing in the Resistance victory path requires AM.** Consumers: AM drives (AAMPCT 0.0022/tank, AMPCT 0.0041/tank-row class, Pion 5/tank — fleet-scale Pion is unaffordable forever), AM reactors, trace AM-weapon build costs. Fusion torches need none.
- **Bait mechanic (code-real):** the alien daily planner adds any human hab owning ONE completed module with `incomeAntimatter_month > 0` to its attack-target list. A single finished collider paints the hab. Usable deliberately as bait; otherwise another reason to skip.
- Money angle: 1 AM ≈ 100 fissiles ≈ 10k money to make, sells for 12,500 at the 25 % market rate — roughly break-even before support costs ([Late-Game Money](Late-Game%20Money.md)).

**Verdict: skip AM unless and until committing to AM drives**; the research gate is multi-year anyway (AntimatterContainment ← AdvancedHydrogenContainment 20k, then ParticleCollider 15k / AntimatterMassProduction 125k / Atomsmasher 30k / Accelerando 150k / Supercollider 100k + RingCore).

## Evidence

**Tier 1 (code/templates, verified):** `TIHabState.cs:2312` capture exotics formula + `TIGlobalConfig.cs:2397` ExoticsPerAlienHabTier=3; `:2349` salvage refund (2+SL)/10; `:2347` under-construction ships SL/4; `AssaultHabOperation.cs:276/279` SL −1/0 vs `TIMissionEffect_SeizeSpaceAsset.cs:94/97` SL 1/3 + ApplyEffect ordering (return before PostAssaultDamage); `DestroyHabOperation.cs:120` 0.1; `TISpaceShipState.cs:3240` nuke-bombard 0; `CombatRecord.cs:86–95` salvage rolls (no warheadClass check anywhere); `TISpaceCombatState.cs:1930` ×(0.2+SalvageBonus); `TIRegionAlienFacilityState.cs:158` Earth raid 3×rand(0.75–1.25); `TIHabModuleTemplate.json` collider outputs + incomeExotics grep; `TIOrbitState.cs:792` harvesting math; `AIDailyFactionPlanner.cs:2926–2942` AM-bait targeting; alien templates — zero AM in build materials. *(high)*

**Verdict provenance:** capture-formula claims VERIFIED/MODIFIED (crit-doubling on Earth raids removed; Live-Hydra tier≥2 condition added); councilor-farming numbers VERIFIED; AM-from-aliens REFUTED; harvesting-useless VERIFIED; "exotics capped game-wide" REFUTED; "nuked ships yield no salvage" REFUTED for 1.0.32; nanofactory-exotics income REFUTED for 1.0.32 (it is a 1.0.38+ mechanic; on this build nanofactories give money+Materials research only).

**REFUTED myths:** ~~"Capture alien nanofactory habs for antimatter"~~ · ~~"AoE kills yield no salvage"~~ · ~~"Exotics are capped at a few hundred"~~ · ~~"Build nanofactories for exotics income (1.0.32)"~~.

## Worked example — the reference campaign (Resistance, 2032-05 snapshot)

- Stockpile at 2032-05: **5.8 exotics, 0 AM, 0 income**. Every combat acquisition path is gated on assault capability: marine-module projects researched (MarineAssaultUnit/Advanced/Elite = 4/6/8 marine-ops value per 200 t module), but a Seize-capable expedition needs ships + a spare councilor. One T3 councilor capture ≈ tripling-to-quadrupling current stockpile.
- Difficulty note: the reference campaign is **Normal** → `Diff_ExoticsSalvageRate` 1.0, divided by alienProgressionSpeed 2.0 = **net 0.5** ([Economy Markets and Loot](../mechanics/Economy%20Markets%20and%20Loot.md) § Path 2). No double discount — an earlier draft's "Veteran 0.5, additionally halved by progression" misread the campaign difficulty and double-counted.
- The player's Phaser-tier guns are far off; the exotics the player farms now should be hoarded, not spent on mid-tier toys.

## Sources

- https://www.reddit.com/r/TerraInvicta/comments/1lk5nzi/exotics_motherload/
- https://wiki.hoodedhorse.com/Terra_Invicta/Resources · …/Aliens
- Steam guide threads on AM economics + bait
- Decompile: https://github.com/Armandox33/Terra-Invicta-AI-Assistant; local templates build 22085164; save-empirics 2032-05-09
- Related: [Capital Ship Doctrine](Capital%20Ship%20Doctrine.md) · [Late-Game Money](Late-Game%20Money.md) · [Offense Timing vs Aliens](Offense%20Timing%20vs%20Aliens.md)
