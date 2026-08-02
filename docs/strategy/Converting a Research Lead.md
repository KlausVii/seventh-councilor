---
title: Converting a Research Lead
game_version: 1.0.32 (build 22085164)
---

# Converting a Research Lead

> **Evidence vintage caveat (applies to all code citations in this note):** decompiled-source evidence is from a repo bracketed to builds 1.0.30–1.0.33 (commit 2025-06-12). Constants could drift in newer builds — re-verify after any game patch (templates via `sync_game_data.py`; code via the repo if updated).

## Verdict (expanded)

### Slot discipline — the real mechanic behind "diversify"

- **There is NO "Versatility" spread bonus** (grep of source: zero hits — myth REFUTED). The actual mechanic is a PENALTY: the category bonus is multiplied by **0.9 for each ADDITIONAL slot simultaneously researching the same category** (`categoryBonusPenaltyPerExtraSlot`). Concentrating *weight* into fewer slots is free; spreading one category across slots is taxed.
- **Research slots 3/4/5:** slot 3 is base; the **first active org granting project capacity unlocks slot 4**; the **first hab project source unlocks slot 5**.
- **Faction-project speed bonus** (`MultipleFacilitiesMultiplier`): counts **ACTIVE project-slot-granting facilities** (councilor trait slots + org slots beyond the first + hab slots beyond the first) — NOT completed projects (myth corrected: burning cheap projects does not compound speed). Tiers: first 20 ×5 % (+100 %), next 20 ×3 % (+160 % at 40), then +1 % each. Applies **only to faction-project research, not global techs** — so slot-granting orgs/modules are the project-speed stat.

### Category bonuses — soft caps and the Xenology exception

Per source-class pool (habs / orgs / traits / investigations / fleets): raw sums ≤ 0.5 pass through; above that, bonus = 0.5 + 0.5·(x−0.5)/((x−0.5)+2), asymptote +100 % per pool. Worked example: six T3 Science Institutes = raw 1.5 → **+66.7 %, not +150 %**.

- **Xenology labs are 2–4× stronger per building** than every other category: 0.10/0.25/0.50 by tier (XenologyLab/XenoscienceResearchCenter/XenoscienceInstitute) vs 0.025/0.10/0.25 for all others — and Xenology uniquely adds +alienInvestigations/100.
- T3 institutes are `onePerHab=false` with **no per-faction cap**, each also granting +15 flat research/mo — stacking is legal, just soft-capped per pool.
- Since the entire victory chain is Xenology ([Research Skips](Research%20Skips.md)), **Xenology lab stacking is the single highest-leverage research investment for a Resistance run.**

### Contribution flooding — controlling project drops

When a global tech completes, each faction's contribution fraction is recorded; project unlock rolls then add **TechContributionBonus × 100 percentage points** (≈ +1 pp per 1 % contribution, averaged across the project's tech prereqs) on top of base availability (`factionAvailableChance × 7/numFactions`), councilor **Science/5**, and ProjectUnlockChance effects. **Flooding weight into globals whose project drops you need is mechanically supported.** Un-unlocked projects can also be obtained via the StealProject mission or project trading (`CanTradeProject`). (Active only when `variableProjectUnlocks=true` — it is in the reference campaign's save.)

### Unused MC is research

Each unused MC point = **0.075 research + 0.2 money per day**, capped at buildable-source MC — slack MC is a real (small) research source, another reason not to run deficits ([LEO Defense Doctrine](LEO%20Defense%20Doctrine.md)).

### The closure arithmetic and the drive-tier framework

Victory closure ≈ **196,275 RP (17 nodes, all Xenology + Skywatch)**. A research-dominant faction clears that in 1–2 years of partial allocation — **the lead converts through logistics, not more research**. Decision framework for the drive program (compute the REMAINING closure from your finished techs, never the from-scratch number):

| Tier | Missing RP (2032-05, this run) | One-way to Haumea (~50 AU) | Role |
|---|---:|---:|---|
| Helicon (researched) | 0 | ≈1.8–2.4 yr | Logistics/councilor "yeet ships" only (~2.4 MN ×6 combat) |
| Firestar (avail., 20k) | 20k | ≈10 yr | Orbital-defense drive, NOT a Kuiper drive; legal refit from Lodestar family |
| NeutronFluxTorch | 275k (project 150k + magnetics) | **≈0.4–0.6 yr** | Fastest transit; EV 1700 but thrustCap 2 → cruise drive, never a warship; 60 % fissiles/tank; legal refit from NeutronFluxLantern ships |
| Triton fusion tier (DT) | ~210–265k | ≈1.8–2.5 yr | First real Kuiper WARSHIPS (thrustCap 25–40) |
| D-D fusion tier | ~320k | ≈1–1.2 yr | DeuteronTorus is gas-giant-scoop-capable |

Two cross-cutting facts: **DeuteriumTritiumFusion (50k) gates the whole fusion ladder** and the **magnetics trio (HTS 40k + MagneticPlasmaConfinement 35k + MagneticNozzles 50k = 125k) gates every outer-system drive including NFT** — and HTS double-counts as the coilgun-chain gate ([Weapon Doctrine vs the Hydra](Weapon%20Doctrine%20vs%20the%20Hydra.md)). Transit numbers are a flat-space burn-coast-burn model, ±20–30 % vs the real trajectory planner; sub-42-kps (solar escape at 1 AU) fleets cannot make the trip at all.

### Numbers not to trust while planning

- **In-game laser combat scores are buggy** (unclamped armor-effectiveness divisor + single-range sampling) and **kinetic scores carry mixed-units + double-counted ammo penalties** on 1.0.32 — rank weapons from template math, not AI valuations.
- **Community drive tables built on drive-efficiency radiator math are systematically wrong**: code sizes radiators from REACTOR inefficiency, and open-cycle drives vent reactor heat with the propellant (radiators only for crew heat, 3.75 W/person). Open-cycle/high-massflow drives are understated in those tables; recompute before following any drive ranking.
- Per-category research percentages in the UI are per-category **bonuses** (+117 % etc.), not sub-100 % multipliers — a misread that has already produced one wrong note in this knowledge base (since corrected).

## Evidence

**Tier 1 (code/templates, verified):** `TIFactionState.DistributedCategoryModifierValue:12360` + `TIGlobalConfig.cs:1602` categoryBonusPenaltyPerExtraSlot 0.9; soft-cap blocks `:12352–12356`; `MultipleFacilitiesMultiplier:12351` + first20/second20/overage 0.05/0.03/0.01; `GetEffectiveResearch` isProject branch; slot unlocks `:5429/:5483`; `TIGlobalResearchState.cs:510` contribution recording; `RollToAddProjectTrigger:12389` + `TechContributionBonus:5748`; `TIGlobalConfig.cs:1037/1040` MC conversion 0.2/0.075; `TIHabModuleTemplate.json` Xenology lab line 0.10/0.25/0.50; victory-closure walk 196,275 RP; `TIDriveTemplate.json`/`TIDriveTemplate.cs:526` refit rule; `TIPowerPlantTemplate.cs:67–81` WasteHeat_GW (reactor-based, open-cycle crew-only); prereq closures computed vs save finished lists. *(high; transit model medium)*

**Verdict provenance:** research-conversion levers MODIFIED (per-completed-project bonus corrected to per-facility); allocation advice MODIFIED (no Versatility — penalty mechanism); global-research control VERIFIED; drive-evaluation methodology VERIFIED (with remaining-closure caveat); conKORDian drive meta MODIFIED (radiator methodology flawed); institute stacking quantified (new finding).

**REFUTED myths:** ~~"Versatility bonus for spreading research"~~ · ~~"+5 %/+3 %/+1 % per completed project"~~ · ~~"Six institutes = +150 %"~~ (+66.7 %) · ~~"Energy/Life categories run slower than nominal"~~ (they run +87 %/+70 % faster — the UI shows bonuses).

## Worked example — the reference campaign (Resistance, 2032-05 snapshot)

- Income ≈ **272 RP/day (~8.2k/mo, ~99k/yr)** — 3.3× the next faction. The victory closure alone is ~2 years exclusive; the schedule driver is the fusion fleet, not the Xenology chain.
- Recommended sequencing from the verified closure data: queue **DeuteriumTritiumFusion (queueable NOW — both prereqs done)** at the next global slot; buy the **magnetics trio (125k)**; decide NFT-vs-Triton by whether the first Kuiper push is logistics (NFT refit of existing NeutronFluxLantern ships) or combat (Triton warships). FleetLogistics 45k double-counts (Titan chain + 4th hate mask).
- The reference campaign runs `researchSpeedMultiplier 2.0` — unlock-chance climbs and project economics scale accordingly.
- Slot hygiene check from the save: avoid doubling categories across slots (the 117 %/111 % → −10 % deltas observed in the slot table are exactly the ×0.9 penalty).

## Sources

- https://www.reddit.com/r/TerraInvicta/comments/1r5gdw0/v10_best_engines_analysis_and_conclusion/ (local saved HTML)
- https://www.reddit.com/r/TerraInvicta/comments/1p3e5yn/rc4_ultimate_drive_chart/
- Decompile: https://github.com/Armandox33/Terra-Invicta-AI-Assistant; templates build 22085164; save-empirics 2032-05-09
- Related: [Research Skips](Research%20Skips.md) · [Drives Refits and Logistics](../mechanics/Drives%20Refits%20and%20Logistics.md) · [Offense Timing vs Aliens](Offense%20Timing%20vs%20Aliens.md)
