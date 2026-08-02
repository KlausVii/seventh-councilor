---
title: Economy Markets and Loot
game_version: 1.0.32 decompile (build 22085164; decompile repo brackets 1.0.30–1.0.33); lessons re-verified through 1.0.38+
---

# Economy, Markets and Loot

Code-verified, campaign-independent reference for the resource market, mining, Mission Control economics, exotics acquisition, antimatter, salvage, and trade-AI anti-exploit scoring. Part of the [Mechanics index](README.md) MOC; siblings: [Research Mechanics](Research%20Mechanics.md), [Alien Hate and Diplomacy](Alien%20Hate%20and%20Diplomacy.md), [Victory Conditions and Endgame](Victory%20Conditions%20and%20Endgame.md), [Space Combat Math](Space%20Combat%20Math.md), [Drives Refits and Logistics](Drives%20Refits%20and%20Logistics.md).

> **Evidence caveat (applies to every code citation below):** decompiled-source evidence comes from a repo vintage bracketed **1.0.30–1.0.33** (commit dated 2025-06-12). It is mutually consistent with the installed build's templates and save except where flagged, but constants can drift in newer builds — **re-verify after any game patch** (templates via `scripts/sync_game_data.py`; code via an updated decompile). One known skew is flagged in § Exotics.

**Difficulty enum (code-verified):** `1 = Cinematic, 2 = Normal (default switch branch), 3 = Veteran, 4 = Brutal` — `TIGlobalConfig.Diff_*` switches, e.g. `Diff_GetExoticsSalvageRate()`. Alien-proxy players get the mirrored value `5 − difficulty`. The old community 0–3 table is **wrong — REFUTED**.

Reference-campaign examples below are labeled **[reference campaign]** = Normal difficulty, `alienProgressionSpeed` 2.0, `researchSpeedMultiplier` 2.0, in-game ≈ 2032-05.

---

## 1. Resource market (selling space resources for money)

**Where you can sell:** requires a **station** in **Low Earth Orbit** with a **completed core** — `TIHabState.CanSellResources` (TIHabState.cs:492–495) checks `IsStation && orbitState.isEarthLEO && anyCoreCompleted`. The `earthLEO` flag exists only on orbits `LowEarthOrbit1–4` (TIOrbitTemplate.json). Not "any interface orbit" — LEO specifically. *(code+template, high confidence)*

**Sale price formula** (TIGlobalValuesState.cs:509):

```
sale price per unit = marketValue[resource] × min(2/3, 0.05 × (1 + Σ ResourceMarketSales effects))
```

- Base sell rate = `baseEarthSaleInefficiency = 0.05` (TIGlobalConfig.cs) → **5%** of market value.
- Hard ceiling 66.7%, but the only effects in 1.0.32 reach **25%**:

| Project (dataName) | RP (template) | Prereqs | Effect | Cumulative rate |
|---|---:|---|---|---:|
| — (none) | — | — | — | 5% |
| `Project_CommercialMiningCompanies` | 2,000 | SpaceCommerce | `Effect_SpaceMarketEfficiency1` (+1) | 10% |
| `Project_ResourceMarketAdministration` | 2,000 | WhiteCollarAutomation + SpaceMiningandRefining | `Effect_SpaceMarketEfficiency1` (+1) | 15% |
| `Project_IntegratedResourceMarket` | 5,000 | IntegratedEarthSpaceEconomy (40,000 RP tech) | `Effect_SpaceMarketEfficiency2` (+2) | **25%** |

Effects are **additive** inside the `(1 + Σ)` term: 0.05 × (1+1+1+2) = 0.25. *(TIEffectTemplate.json + TIProjectTemplate.json, high confidence)*

**Campaign-start market values and resulting unit prices** (TIGlobalConfig.cs `initial*Value`, fields near :2277–2295):

| Resource | Initial value | @5% | @10% | @15% | @25% |
|---|---:|---:|---:|---:|---:|
| Water | 1 | 0.05 | 0.10 | 0.15 | 0.25 |
| Volatiles | 5 | 0.25 | 0.50 | 0.75 | 1.25 |
| Metals | 10 | 0.50 | 1.00 | 1.50 | 2.50 |
| Noble Metals | 50 | 2.50 | 5.00 | 7.50 | 12.50 |
| Fissiles | 100 | 5.00 | 10.00 | 15.00 | 25.00 |
| Exotics | 1,500 | 75 | 150 | 225 | 375 |
| Antimatter | 50,000 | 2,500 | 5,000 | 7,500 | 12,500 |

**Prices drift over the campaign:**

- **Depression on sale** — each sale multiplies the market value by `(1 − rand(1e-6, 2e-6) × unitsSold)`, floored at 0.001 (`TIGlobalValuesState.ModifyMarketValuesForResourceSale`, :447). Selling 10,000 units depresses that resource's price ~1–2% — negligible at normal volumes; sell in bulk without fear.
- **Appreciation from Earth economy** — every nation Economy-priority completion multiplies Metals value by `(1 + rand(1e-5, 2e-5))` and Nobles by `(1 + rand(5e-6, 1e-5))` (`TIGlobalValuesState.ModifyMarketValuesForEconomyPriority`). Metals/nobles prices **rise** over years. *(both code-verified, high confidence)*

> **[reference campaign]** metals market value had risen to 14.75 by 2032-05 (vs initial 10). Holding 7,261 nobles vs 1,021 money, a bulk nobles sale grossed ≈44k at 10% (only CommercialMiningCompanies done) or ≈66k after the 2,000-RP ResourceMarketAdministration — a ~50× cash position change for one cheap project.

**There is NO general buy-side on the resource market (money → space resources) — REFUTED as a planning lever (2026-07-13).** The market converts space resources → money only (`CanSellResources` / `GetModifiedResourceMarketValueForSelling`). `GetPurchaseResourceMarketValue` (TIGlobalValuesState.cs:14552, returns FULL undiscounted market value) has exactly **one consumer** in the 1.0.30–33 decompile: the **hab-module build path** (HabitatsScreenController.cs:2864) — when a hab build lacks space resources, the game charges money at 100% market value **plus Boost** to launch the equivalent mass from Earth's surface (`GenericTransferBoostFromEarthSurface`). Consequences: ① hab modules can be money+boost-financed (the familiar early-game mechanic — expensive at full value, boost-hungry for deep-space habs); ② **ship construction has NO money-substitution path** — shipyard builds draw real space resources only; ③ "sell nobles → buy metals for the fleet" is NOT a thing; the only money→metals route is inter-faction diplomacy trade (see § trade-AI scoring), unavailable while at war with every rival. A metals crunch during a build program is a **flow-allocation problem** (prioritize queues, add mine income), not a liquidity problem. *(code-verified, high confidence)*

---

## 2. Mission Control economics

### Unused MC trickle

Every point of **unused** MC yields **0.2 money/day + 0.075 research/day** simultaneously (`ExcessMCToMoneyConversion_Day = 0.2`, `ExcessMCToResearchConversion_Day = 0.075`, TIGlobalConfig.cs:1037/1040), capped at `min(buildable-source MC, available MC)` (TIFactionState.cs:2978–2982). See [Research Mechanics](Research%20Mechanics.md) for the research side. *(code, high confidence)*

### MC deficit penalties (running negative MC)

1. **Combat:** hab defense value is reduced by the faction's `MissionControlShortage` — `TIHabState.ModifiedDefenseCombatValue` subtracts it directly. An MC deficit weakens every hab against assault. *(code, high confidence)*
2. **Module destruction event:** `event_HabModuleMalfunction` (TINarrativeEventTemplate.json) fires when MC balance < 0; its weight multiplies **×3 / ×6 / ×10** below **−50 / −100 / −200**. Outcomes escalate from destroying **2** modules (weight 1) to **4** (weight 0, +2 modifier if balance < −100) to **8** (weight 0, +3 if < −200).
   - **1.0.32 caveat:** the 1.0.34 beta patch note says these conditional outcome weights were *not being applied* — so on 1.0.32 deficits likely only ever destroy 2 modules per event (deficits under-punished). Template structure verified; the bug itself is inferred from the patch note, medium confidence.

### Mining-network MC penalty (quadratic past the free limit)

`TIFactionState.GetMissionControlRequirementFromMineNetwork` (TIFactionState.cs, token 0x06002FA9):

```
n = (active mines) − (MC-free mine network size)
extra MC = 0                  if n ≤ 0
extra MC = max(1, n²/2)       if n > 0   (integer math)
```

Marginal cost of the **next** mine therefore grows linearly (≈ n + 0.5; `GetMissionControlRequirementFromNextMine`). The free network = `spaceMineFreebies` (TIGlobalConfig default **0**, no JSON override in 1.0.32) + Σ `MCFreeSpaceMineNetwork` effects, granted by:

| Source | dataName | RP | Free mines |
|---|---|---:|---:|
| Mission to the Moon | `MissiontotheMoon` | 1,000 | +3 |
| Mission to Mars | `MissiontoMars` | 2,500 | +6 |
| Mission to the Asteroids | `MissiontotheAsteroids` | 3,500 | +6 |
| Mission to the Inner Planets | `MissiontotheInnerPlanets` | 15,000 | +3 |
| Mission to Jupiter | `MissiontoJupiter` | 10,000 | +6 |
| Mission to Saturn | `MissiontoSaturn` | 25,000 | +6 |
| Mission to the Outer Planets | `MissiontotheOuterPlanets` | 75,000 | +6 |
| Future Tech: Space Science (repeatable) | `FutureTechSpaceScience` | 100,000 | +1 each |
| Gold Rush (project, Exodus victory line, single faction) | `Project_GoldRush` | 2,500 | +6 |

Full non-repeatable tech line = **36** free mines. (Mission to Mercury / Venus grant none.) *(code + TITechTemplate.json/TIEffectTemplate.json, high confidence)*

> **[reference campaign]** 6 of 7 freebie techs done (all but Outer Planets) → 30 free mines; 43 active mines → 13 over → 13²/2 = **84 extra MC**; a 44th mine would add ~14 MC beyond its own module cost.

### Mining yield multiplier

`TIFactionState.GetCurrentMiningMultiplierFromOrgsAndEffects` (TIFactionState.cs:3492–3528): multiplier = 1 + Σ org `miningBonus` (additive) + `SpaceMiningBonus` effects (additive) + per-resource context (e.g. `MiningMetalsBonus` for metals). Verified boosters:

| Project | RP | Prereqs | Effect |
|---|---:|---|---|
| `Project_AdvancedProspectingSurveys` | 1,500 | OrbitalShipbuilding + IndustrializationofSpace + Project_MobileSpaceScienceLab | +10% all resources (`Effect_SpaceMiningBonus10`) |
| `Project_AlgorithmicExtractionManagement` | 50,000 | AdministrationAlgorithms + SpaceCommerce | +10% all resources |
| `Project_DeepSpaceMetallurgy` | 15,000 | SpaceMiningandRefining + AppliedArtificialIntelligence | ×1.15 **metals** (`Effect_MiningMetalsBonus`, multiplicative) |
| `Project_PlasmaExtractionTechniques` | 20,000 | SpaceCommerce + ElectrostaticPlasmaConfinement | ×1.15 **metals** |
| `Project_GoldRush` | 2,500 | Exodus escape-victory line only | +10% all + 6 free mines |

Orgs with `miningBonus` stack additively in the same multiplier — an extra metals lever beyond projects. **REFUTED myth:** "no faction project boosts metals mining" — two metals-specific multiplicative projects exist. *(code+templates, high confidence)*

**Actual mine income ≠ the site's raw rate.** `TIHabSiteState.{metals,water,volatiles,nobles,fissiles}_day` is the RAW geological rate — NOT the module's income. Real monthly income = `site_day × module.miningModifier × (the global multiplier above) × ~30.44`. Tier `miningModifier` (`TIHabModuleTemplate.json`): Outpost 1.0 / Automated 1.25 / **Settlement (T2) 1.5** / **Colony (T3) 2.0** (alien variants 2/4). So a T3 Colony mine with a ~1.68× metals multiplier yields **~3.4× its printed `metals_day`**. Calibrate the global multiplier once against an in-game module tooltip (e.g. a reference-campaign mining base: site 2.88 metals_day → 220.6/mo displayed); `mine_completion_timeline.py` does exactly this. Using `*_day` as income under-reports by 2.5–3.4×. *(code+tpl, high confidence)*

---

## Boost economy — production, latitude, and the real sinks

Boost = Earth→orbit launch capacity (stored as dekatons/year on regions; UI shows /month). Constants `TIGlobalConfig.cs`: `boostPriorityIncreaseAtEquator 4`, `boostLatitudeDivisor 25`, `spaceResourceToTons 0.1`, `priority_BOO 2`.

**Production — four sources, and priority pips are the WEAKEST:**
1. **Authored per-region baseline** `region.baseBoostPerYear_dekatons` (`TIRegionState.cs:368`) — the bulk. Space powers start with large regional boost before any priority runs; nation boost = Σ region boost (`TINationState.cs:3447`). *A nation showing 33/mo with zero LaunchFacilities history is all baseline.*
2. **Spaceflight-program founding** — one-time `spaceflightInitialBoost = 0.1 dk/yr` to the lowest-|lat| coastal region.
3. **`LaunchFacilities` ("Boost") priority buildout — GLACIAL.** Each completion = 2 IP, adds `BoostIncrease = (4 − |boostLatitude|/25) × 0.1` dk/YEAR to the lowest-|lat| region (`OnBoostPriorityComplete`→`BoostIncrease`, `TINationState.cs:5429`). Equator 0.4/yr · 25° 0.3 · 50° 0.2 · 75° 0.1. Heavy pips ≈ 1–3 completions/mo → output creeps up a *fraction of a boost/month per month invested* — **decades to matter. Pips do NOT fix a boost deficit.** If ever allocating: **China > USA > Russia** (China most IP + low latitude; Russia fewest IP + worst latitude). "Funding" is money, unrelated to boost.
4. **Orgs** — `incomeBoost_month` (tech-unlocked, buyable with cash); some cost one-time `costBoost`; a rare few have NEGATIVE incomeBoost (hidden drain).

Faction share of a nation = `boostIncome_month / numControlPoints × (faction CPs)` (`TINationState.cs:4131/4199`); excludes fully-occupied regions; routes through the federation pool.

**Sinks — module support is obvious; the killers are hidden:**
- **Module support** `supportMaterials_month.boost`: Administration **Node/Tower/Complex 1/4/12** boost/mo; SpaceHotel 3 / SpaceResort 6; Residential 0.5; OrbitalHospital 1 / GeriatricsFacility 3.
- **Resource-shortage BACKFILL (the big hidden sink):** building/resupplying in space without enough local metals/water/volatiles silently pays the shortfall in **boost + money from Earth** (`GetBoostSubstitutedCost`, `TIResourcesCost.cs:201-240`) — this is most of the ledger's "Construct Hab Module" boost, and it SHRINKS as the space resource economy matures (a construction-driven boost drain is partly self-resolving).
- One-time construction from Earth (`BoostCostFromEarth`), ship repair/resupply/ammo substitution, scuttle, probe / STO-interceptor launches.

**The Administration non-LEO trap:** an Admin module's CP-cap works ONLY in Earth LEO (`LEOControlPointCapacity`). Built anywhere else it gives only the `Efficiency` bonus — ×(1 + `specialRulesValue`: Node .025 / Tower .05 / Complex .10) on the hab's GROSS income (`TIHabState.cs:3364-3523`, multiplicative, powered-only) — for the FULL boost cost. On a mining base that's ~+5% output for 4 boost/mo — a bad trade and a known community trap. In a crunch, **power OFF (not decommission — irreversible) the non-LEO Admin Towers first**, especially "dead" ones whose mine isn't producing yet (+5% × 0 = nothing).

**Deficit fix (community + code):** shut down boost-hungry modules (emergency); close the space-resource gap so backfill stops; buy boost orgs; push off-Earth mining. Diagnose with `boost_analysis.py`. *(code+tpl+community, high confidence)*

---

## 3. Exotics

### The one-sentence truth for 1.0.32

**No human production path exists.** Exotics come only from looting the aliens (capture/raid/salvage), trade, story grants, and one endgame repeatable. Grep of all 156 `TIHabModuleTemplate.json` entries: only `AlienWormholeFacility` has `incomeExotics_month` (10/mo, alien-only, `EverAllowedForFaction` requires alien faction). Lore text agrees ("our only way of obtaining it will be to steal or scavenge it from the aliens", TIObjectiveTemplate.en ResearchExotics). *(template-exhaustive, high confidence)*

**REFUTED myths:**
- *"Exotics are capped at a few hundred units game-wide."* No cap exists — `UnlockedExotics` is the boolean effect `CanAmassExotics` (TIFactionState.cs:3661), not a quantity cap; no cap constant in TIGlobalConfig.cs. (e.g. the alien faction held 2,259 exotics in the reference-campaign save.)
- *"Powered nanofactories give exotics income."* Not on 1.0.32 — Nanofactory grants money + Materials research only. The "exotic gains scale with nano factories" 1.0.38 patch note maps to the **endgame tech** `FutureTechMaterials` (100,000 RP, repeatable): `Effect_AllHumanFactionsGainExotics` = instant **+20 exotics to ALL human factions** (instantEffect `GainExoticsFromSpaceIndustry`) — a periodic grant, not an income stream. **Version-skew flag:** this effect name exists in the 1.0.32 templates but not in the decompile's `InstantEffect` enum (which only has `GainExoticsIncome`), so symbol-level findings near exotics-grant logic carry slight version risk.
- *"Earth alien-facility raids give double exotics on crit."* Raid yield is `3 × rand(0.75–1.25)` = **2.25–3.75 exotics for ANY success including crit** — no crit branch exists (`TIRegionAlienFacilityState.cs:158`).

### Path 1 — capture/raid alien habs (the big one)

Against alien habs, "capture" is a **loot raid**: `CaptureHab`'s alien branch ends in `DestroyHab` — you can never keep/operate an alien hab (TIHabState.cs:2349). Payouts on success, all scaled by **success level (SL)**:

| Attack type | SL on Success | SL on Crit | Evidence |
|---|---:|---:|---|
| Marines-only Assault Hab fleet operation | −1 | 0 | AssaultHabOperation.cs:276/279 |
| Councilor **Seize Space Asset** mission (marines present) | **1** | **3** | TIMissionEffect_SeizeSpaceAsset.cs:94/97 |

(Control Space Asset cannot target alien habs — its condition is `TIMissionCondition_EnemyHumanSpaceAsset`; Seize uses `TIMissionCondition_EnemySpaceAsset` + troops-present, TIMissionTemplate.json.)

Loot formula (TIHabState.cs:2306–2352, `ExoticsPerAlienHabTier = 3` at TIGlobalConfig.cs:2397):

```
bonus exotics      = 3 × habTier × (1 + SL) × rand(0.8–1.2)
materials refund   = module build materials × (2 + SL)/10      (incl. exotics in alien module costs)
ship exotics bonus = exotics cost of under-construction alien ships × clamp(SL/4, 0, 1)
intel              = 5 × (1 + SL) × habTier
```

Worked numbers for a **T3** alien hab: councilor-led 14.4–21.6 exotics (success) / 28.8–43.2 (crit) + 30–50% materials refund; marines-only **0** (success, since 1+SL = 0; refund 10%) / 7.2–10.8 (crit). Always send a councilor.

Extra effects on any successful capture vs aliens: **all alien councilors revealed** (`FactionExposed` → `GainIntelToMinimum` on every councilor), **assessed alien hate reset to actual** (`FixAssessedAlienHateToActualValue` — see [Alien Hate and Diplomacy](Alien%20Hate%20and%20Diplomacy.md)), milestone completions (AccessAlienTech / HydraCorpus; **AccessLiveHydra** requires `(SL ≥ 3 AND habTier ≥ 2) OR zero alien councilors on Earth` — TIHabState.cs:2322).

**Zero-attacker-damage quirk (code-confirmed, exploitable):** in `TIMissionEffect_SeizeSpaceAsset.ApplyEffect`, Success/CritSuccess `return` at `CaptureHab()` **before** the attacker-fleet `PostAssaultDamage` block runs — a successful councilor-led assault inflicts **zero damage on your marine ships**; only failures damage the attacker. *(decompile, high confidence within vintage caveat)*

**Assault odds:** `P(success) = 1 − 0.5 × 0.775^(attackerValue − defenderValue)` (AssaultHabOperation.cs:GetSuccessChance) — parity = 50%, +9 ≈ 95%, +16–18 ≈ 99%+. No hard 0% or 100% exists. Hab defense = core tier + marine-rule module values (× command-adviser multiplier) + docked fleets − MC shortage; see [Victory Conditions and Endgame](Victory%20Conditions%20and%20Endgame.md) for HQ-scale numbers.

### Path 2 — ship-kill salvage

On combat victory the winner rolls salvage per destroyed ship (CombatRecord.cs:86–95, TISpaceCombatState.cs:1930–1933):

```
exotics salvage = exoticsCost × rand(0, 0.85) × Diff_ExoticsSalvageRate(difficulty) / alienProgressionSpeed
                  × (0.2 + fleet SalvageBonus)
basic materials = cost × rand(0, 0.25) × (0.2 + SalvageBonus)
```

| Difficulty | 1 Cinematic | 2 Normal | 3 Veteran | 4 Brutal |
|---|---:|---:|---:|---:|
| `Diff_ExoticsSalvageRate` | 2.0 | 1.0 | 0.5 | 0.3333 |

(TIGlobalConfig.cs:2049–2058; divided by `alienProgressionSpeed` customization.) `SalvageBonus` from salvage modules has diminishing returns past 0.25 (TISpaceFleetState.cs:4324–4343); base recovery without modules is only **20% of the rolled amount**. Salvage is faction-agnostic — Servant/Protectorate ships built with exotic components (Phasers, Mk3 plasma) salvage exotics too.

> **[reference campaign]** Normal + progression 2.0 → rate 0.5; expected exotics per alien kill ≈ 0–8.5% of the ship's exotics cost without salvage bays.

**REFUTED myth:** *"ships killed by AoE/nuke yield no salvage."* No `warheadClass` check exists anywhere in the 1.0.32 ship-death salvage path (`RecordShipDestroyed → CombatRecord.AddAssetDestroyedRecord`) — every kill rolls salvage identically. The TRUE adjacent rule: **bombarding a HAB** with Nuclear/Antimatter warheads destroys it with **0%** materials recovery (TISpaceShipState.cs:3238–3241) vs **10%** from the fleet **Destroy Hab** operation (DestroyHabOperation.cs:120) vs **(2+SL)/10** from capture. Capture > destroy-op > nuke, always.

### Path 3 — Earth alien-facility raids

Councilor assault on an alien Earth facility: `3 × rand(0.75–1.25)` = 2.25–3.75 exotics per success, crit identical (TIRegionAlienFacilityState.cs:158).

### What exotics are for (demand reference points)

Green Phasers 0.025 / UV Phasers 0.05 exotics build-weight (≈3.6 exotics per 960 cm UV Phaser cannon); IR Phasers need **none**; all human Mk3 plasma weapons 0.02 (post-1.0.30 cheap — TIPlasmaWeaponTemplate.json); exotic/hybrid armor 0.01/0.005; AM particle weapons effectively zero (6.7e-12–2e-11). Budget exotics for endgame guns, not mid-tier spends.

---

## 4. Antimatter

### Production = colliders, full stop

| Module | Tier | AM/month | Fissiles/month | Fissiles per AM | Other support/mo |
|---|---:|---:|---:|---:|---|
| `ParticleCollider` (station-only) | 1 | 0.0001 | 1 | 10,000 | — |
| `Atomsmasher` | 2 | 0.01 | 3 | 300 | — |
| `Supercollider` | 3 | 0.1 | 10 | **100** | 120 money, 30 water, 30 volatiles, 20 metals, 20 nobles; crew 100 |

(TIHabModuleTemplate.json `incomeAntimatter_month` / `supportMaterials_month`; Energy research bonus +0.01/+0.025/+0.05.) Only the Supercollider is economically sane.

**Natural harvesting is provably useless:** best orbit in the game is `SynchronousSaturnOrbit` (`amat_ugpy = 200`, TIOrbitTemplate.json) → `200e-12 × 0.1 / 12` ≈ **1.67e-12 units/month** even with the AntimatterFarm at 100% efficiency (specialRulesValue 1.0; Trap is 0.25), and only one harvester station is allowed per orbit (TIHabModuleTemplate.cs:1059–1070, TIOrbitState.cs:792). *(code+template, high confidence)*

**Research gate (template costs):** `AdvancedHydrogenContainment` 20,000 → `AntimatterContainment` 10,000 → `Project_ParticleCollider` 15,000; then `AntimatterMassProduction` 125,000, `Atomsmasher` 30,000, `Accelerando` 150,000 (+ RingCore), `Supercollider` 100,000. A multi-year endgame line.

### You cannot loot AM from the aliens — REFUTED acquisition path

- No alien hull/drive/reactor/module/weapon has antimatter in `weightedBuildMaterials` (all 38 alien modules checked; all alien drives burn pure water — TIDriveTemplate.json `perTankPropellantMaterials = {water: 1}`).
- Capture salvage refunds **module build materials** only; the alien *faction stockpile* (22.06 AM in the example save) does **not** transfer on capture.
- Ship-kill AM salvage is therefore moot vs aliens. (For human AM-drive ships: decompile reads `if (Random.value >= 0.25) → add 100% of AM cost`, i.e. **75%** chance — possibly a decompiler inversion of the wiki's 25%; flagged, settle with an in-game test. `antimatterSalvageChance = 0.25`, TIGlobalConfig.cs:2382.)

### The bait mechanic (code-real)

The alien daily planner adds any human hab owning a **completed, functional** module with `incomeAntimatter_month > 0` (owner has `UnlockedAntimatter`) to its attack-goal target list (AIDailyFactionPlanner.cs:2926–2942, `FactionGoal_AttackWithFleet`). One finished collider suffices; under-construction modules don't trigger. Building a collider = volunteering that hab as an alien target — usable deliberately as bait, or avoided by not finishing colliders until you can defend them.

### AM economics and "do I even need it?"

- 1 AM via Supercollider costs 100 fissiles (≈10,000 money at full market value) + support; AM sells for 12,500 at the 25% market rate → roughly break-even as a money engine; thin margin after support costs.
- Demand side: AM drives per tank — AMPCT 0.00041, AAMPCT 0.0022, **Pion Torch 5.0** (fleet-scale Pion propellant is genuinely unaffordable at 0.1 AM/mo per Supercollider); AM reactors; trace amounts in AM particle weapons. Fusion torches need none.
- **Nothing in the Resistance victory path requires antimatter.** Skipping AM entirely is mechanically viable (see [Victory Conditions and Endgame](Victory%20Conditions%20and%20Endgame.md)).

---

## 5. Trade-AI anti-exploit scoring (1.0.32)

`TIFactionState.AI_EvaluateTradeOffer` (TIFactionState.cs:14903–14990) + DiplomacyController.cs:677. Verified structure:

- Flat **200 floor** on every offer's asking value.
- **Boost valued ×5**.
- **Habs:** value × hab count in the offer, × `clamp(asymmetry ratio, 0.75, 5)`, ×5 extra when no hab comes back.
- **Orgs:** each org's value × **number of orgs in the offer** — quadratic total; junk-org dumps on the AI are dead.
- **Hate gate:** received-offer value divided by hate/5 above hate 6 — hated factions get nothing accepted cheaply.
- **Lopsided-trade hate:** efficiency ratio below `goodTradeThreshold = 0.3` (TIGlobalConfig.cs:2169) doubles the hate cost of the trade (hateModifier ×2).

The patch note's exact "net-negative categories weighted 3×" phrasing was **not located** at symbol level (may live in AIEvaluators internals) — the multiplier wording is unconfirmed; the strategic conclusion (org-flipping/category-arbitrage vs the AI is nerfed) is verified in effect. *(code, high confidence on the listed terms; medium on completeness)*

---

## 6. Money levers (ranked pattern, campaign-independent)

1. **Sell surplus resources** at a LEO station (§1) — usually the single fastest fix; research the two cheap 2,000-RP market projects first.
2. **Commercial hab modules** (TIHabModuleTemplate.json `incomeMoney_month`): SpaceResort 400, NanofacturingComplex 300 (+LEO economy bonus), GeriatricsFacility 300, SpaceHotel 120, Nanofactory 90 (+LEO bonus), OrbitalHospital 90. (An often-cited "hospital boost-to-money" sub-mechanic was NOT found in templates — hospitals consume no boost; treat as unverified.)
3. **Unused MC**: 0.2 money/day each (§2).
4. **Nation Funding priority**: each completion adds `fundingPriorityBaseIncomeIncrease + numControlPoints` to annual funding (TINationState.cs:5380–5393), capped at **0.5% of GDP-in-millions per year** (:5370); owning the FinancialSector CP multiplies the payout (`financialSectorFundingBonus`, :4127). Funding scales with IP allocated, not GDP directly — GDP only caps it.
5. **Spoils** degrades the nation every completion (sustainability + environment penalties, TINationState.cs ~5364) — short-term cash, long-term damage.
6. **AM sales** — late-game, near-break-even (§4); not a real lever until Supercolliders.

---

## 7. Misconception ledger (so they stay dead)

| Claim | Status | Truth |
|---|---|---|
| Difficulty enum is 0–3 | **REFUTED** | 1=Cinematic, 2=Normal, 3=Veteran, 4=Brutal (code switch) |
| Exotics have a game-wide cap | **REFUTED** | `CanAmassExotics` is a boolean unlock; no cap constant |
| Nanofactories produce exotics (1.0.32) | **REFUTED** | No human module has `incomeExotics_month`; 1.0.38 mechanic ≠ this build |
| Earth facility raids crit-double exotics | **REFUTED** | 2.25–3.75 for any success incl. crit |
| AoE/nuked ships drop no salvage | **REFUTED** | No warheadClass check in the 1.0.32 salvage path; the 0%-recovery rule is for nuke-**bombarded habs** only |
| Capture alien habs for their antimatter | **REFUTED** | No AM in any alien build material; faction stockpile doesn't transfer |
| Salvage bays boost capture loot | **REFUTED** | `(0.2 + SalvageBonus)` applies only to ship-combat salvage, not capture refunds |
| "Selling needs any interface orbit" | **CORRECTED** | Completed-core **station in LowEarthOrbit1–4** specifically |
| No project boosts metals mining | **REFUTED** | DeepSpaceMetallurgy + PlasmaExtractionTechniques ×1.15 each, + two +10% all-resource projects |
