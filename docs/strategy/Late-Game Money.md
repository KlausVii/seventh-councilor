---
title: Late-Game Money
game_version: 1.0.32 (build 22085164)
---

# Late-Game Money

> **Evidence vintage caveat (applies to all code citations in this note):** decompiled-source evidence is from a repo bracketed to builds 1.0.30–1.0.33 (commit 2025-06-12). Constants could drift in newer builds — re-verify after any game patch (templates via `sync_game_data.py`; code via the repo if updated).

## Verdict (expanded)

### Lever 1 — the resource market (usually the sleeping giant)

Sale price = market value × min(2/3, `baseEarthSaleInefficiency`(0.05) × (1 + Σ market-efficiency effects)). The three projects are **additive**: +1 (Project_CommercialMiningCompanies) +1 (Project_ResourceMarketAdministration) +2 (IntegratedResourceMarket) → 5 % / 10 % / 15 % / 25 %.

| Resource | Initial market value | Unit price @25 % |
|---|---:|---:|
| Water | 1 | 0.25 |
| Volatiles | 5 | 1.25 |
| Metals | 10 | 2.5 |
| Noble metals | 50 | 12.5 |
| Fissiles | 100 | 25 |
| Exotics | 1,500 | 375 |
| Antimatter | 50,000 | 12,500 |

- Selling requires a **completed-core STATION in LowEarthOrbit1–4** (`isEarthLEO` — not "interface orbit" generally).
- Per-unit market depression is tiny (1–2e-6/unit, floor 0.001) — bulk lots are fine. Prices drift with global supply (metals had RISEN to 14.75 in the reference campaign).
- Market values are global state: selling depresses, scarcity raises — check `resourceMarketValues` before dumping.

### Lever 2 — commercial hab modules (money/month, template-verified)

| Module | Money/mo |
|---|---:|
| SpaceResort | 400 |
| NanofacturingComplex | 300 (+LEOBonusEconomy) |
| GeriatricsFacility | 300 |
| SpaceHotel | 120 |
| Nanofactory | 90 (+Materials research; NO exotics on 1.0.32) |
| OrbitalHospital | 90 |

(The "hospital boost-to-money" sub-mechanic was not located — unverified.)

### Lever 3 — unused MC

Each unused MC = **0.2 money/day** (+0.075 research), capped at buildable-source MC. ~50 slack MC ≈ 10/day ≈ 3,650/yr — real but small; never a reason to underbuild.

### Lever 4 — Funding priority (the Earth-side engine)

Each Funding completion adds `fundingPriorityBaseIncomeIncrease + numControlPoints` to annual funding, hard-capped at **0.5 % of nation GDP in millions**; owning the **FinancialSector CP multiplies the payout**. Big-GDP nations + FinancialSector CP = the scaling rule. **Spoils degrades** sustainability + environment per completion — it strip-mines the nation that funds you.

### Anti-lever — antimatter for money

1 AM costs ≈100 fissiles (≈10k money) at the **Supercollider** (the only collider worth running: fissiles-per-AM = 10,000/300/100 for T1/T2/T3) and sells for 12,500 at 25 % — **thin margin before** the Supercollider's other support costs (120 money + 30 water/30 volatiles/20 metals/20 nobles per month), **and one completed collider paints the hab on the alien attack-target list** ([Exotics and Antimatter Acquisition](Exotics%20and%20Antimatter%20Acquisition.md)). Break-even with aggro: not a money strategy.

### Org portfolio hygiene (the dead exploit)

1.0.32's trade evaluator structurally kills junk-org dumping: each org's trade value is **multiplied by the COUNT of orgs in the offer** (quadratic penalty), hab values count-multiplied with a 0.75–5× asymmetry clamp (+×5 when no hab comes back), Boost weighted ×5, received-offer value divided by hate/5 above hate 6, a flat 200 floor on every offer, and lopsided wins double the hate cost (goodTradeThreshold 0.3). **Hold orgs for what they DO — research project slots ([Converting a Research Lead](Converting%20a%20Research%20Lead.md)), `miningBonus`, MC — not as trade chips.**

Mining-boost rider (myth REFUTED — these exist): Project_DeepSpaceMetallurgy ×1.15 metals, Project_PlasmaExtractionTechniques ×1.15 metals, Project_AdvancedProspectingSurveys +10 % all, Project_AlgorithmicExtractionManagement +10 % all, plus org `miningBonus` — all stack additively inside `GetCurrentMiningMultiplierFromOrgsAndEffects`.

## Evidence

**Tier 1 (code/templates, verified):** `TIGlobalValuesState.cs:509` sale formula + `:447` depression (floor 0.001); `TIGlobalConfig.cs:2298` 0.05 base, `:2277–2295` initial values; `TIEffectTemplate.json` SpaceMarketEfficiency1 (+1, ×2 entries)/2 (+2); `TIHabState.cs:492–495` CanSellResources (IsStation ∧ isEarthLEO ∧ core); `TIOrbitTemplate.json` earthLEO = LowEarthOrbit1–4; `TIHabModuleTemplate.json` commercial module incomes + collider support costs; `TIGlobalConfig.cs:1037` ExcessMCToMoneyConversion_Day 0.2 + `TIFactionState.cs:2978` cap; `TINationState.cs:5380–5393` funding increment, `:5370` 0.5 % GDP cap, `:4127` FinancialSector multiplier, Spoils penalties ~:5364; `TIFactionState.AI_EvaluateTradeOffer:14903–14990` (org-count multiplier, hab clamps, ×5 boost, 200 floor, hate divisor) + `DiplomacyController.cs:677` goodTradeThreshold 0.3; `TIFactionState.cs:3492–3528` mining multiplier + project effect traces. *(high)*

**Verdict provenance:** money-fix list VERIFIED (with LEO-station precision); commercial-module/funding claims VERIFIED (hospital-boost line unverified); AM break-even VERIFIED; trade-nerf MODIFIED (direction confirmed, exact "3× net-negative weighting" wording not found in code); "no faction project boosts metals mining" REFUTED (two already completed in this save).

**REFUTED myths:** ~~"Sell anywhere with an interface orbit"~~ (Earth-LEO stations only) · ~~"AM production is a money printer"~~ (break-even + aggro) · ~~"No mining-boost projects exist"~~.

## Worked example — the reference campaign (Resistance, 2032-05 snapshot)

- **The immediate play (computed from the save):** the player holds ~7,300 noble metals and only ~1,022 money (5 days cover). At the player's current 10 % rate (only CommercialMiningCompanies done) the nobles are worth ≈44k; **Project_ResourceMarketAdministration costs 2,000 RP, prereqs (WhiteCollarAutomation + SpaceMiningandRefining) BOTH DONE** → 15 % → ≈66k. That's a ~50× cash infusion for one cheap project + a sell order at any of the player's 8+ LEO stations. IntegratedResourceMarket (25 %) waits behind IntegratedEarthSpaceEconomy (40k).
- Metals are the player's binding resource (≈11 days cover; market price risen to 14.75) — sell nobles/water surpluses, never metals; the unpulled metals levers are PlasmaExtractionTechniques, AlgorithmicExtractionManagement, and mining orgs.
- Funding: the player's CPs are concentrated in a few great-power pillars — the FinancialSector CP holding (1) is worth auditing against the multiplier.

## Sources

- https://wiki.hoodedhorse.com/Terra_Invicta/Resources
- Steam guide: late-game money for tall factions; https://www.pavonisinteractive.com/phpBB3/viewtopic.php?f=26&t=29984 (trade-nerf patch context)
- Decompile: https://github.com/Armandox33/Terra-Invicta-AI-Assistant; templates build 22085164; save-empirics 2032-05-09
- Related: [Exotics and Antimatter Acquisition](Exotics%20and%20Antimatter%20Acquisition.md) · [Earth Endgame Consolidation](Earth%20Endgame%20Consolidation.md) · [Converting a Research Lead](Converting%20a%20Research%20Lead.md)
