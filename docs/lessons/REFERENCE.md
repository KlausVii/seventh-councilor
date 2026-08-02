# TI analyzer reference — formulas & save-data shapes

Part of the Seventh Councilor lessons library (see the repo `CLAUDE.md`). Canonical
formulas and data locations; lessons live in the `LESSONS-*.md` files. Calibration data comes
from the reference campaign (Resistance, 2026 start, Normal difficulty, research rate 200%).

## Research

### Slots (6 total)
- Slots 0–2 = global tech (shared across factions; the top contributor picks the successor when
  a slot completes). Slots 3–5 = faction project slots. `researchWeights[0..5]` splits income.
- Category bonuses: see [LESSONS-research](LESSONS-research.md) R16 (sources, diminishing
  returns, and the ×0.9 same-category concurrency penalty).

### The canonical 6-source research-income formula
The in-game 🧪 tooltip is the only authoritative live decomposition; no single save field has
it. Validated to the decimal on the reference campaign's 2032-04-28 save (244.7 base × 1.30 =
318.1/day):

| Source | Derivation |
|---|---|
| 1. Faction HQ | `baseIncomes_year.Research ÷ 365.25` (≈1.0/day). Exact. |
| 2. Councilors | ≈ 4/councilor + Science × ~0.5 (empirical). Approximate. |
| 3. Nations | Σ over your CPs of `nation.historyResearch[0] × CP share` (~83%) **plus active Advise missions** (`nation.advisingCouncilors`; adviser Sci+Adm, diminishing past the first) — NOT "Knowledge-pip weighting". |
| 4. Habs | Join module `templateName` → `TIHabModuleTemplate.incomeResearch_month`, **powered + completed only**. Exact. |
| 5. Unused MC | `(capacity − missionControlUsage) × 0.075`/day. |
| 6. Distribution bonus | ×(1 + rate) on the subtotal (tech-gated; was 30%, later 21% — derive from tooltip ÷ subtotal). |

Monthly = ×30.44; annual = ×365.25. ❌ Never `cachedYearlyRevenue.Research` (stale ~2× for the
player). Don't estimate from habs alone (~10× under).

### Nation history arrays: NEWEST at `[0]`
All `TINationState.history*` arrays (GDP, Research, Population, SpaceFunding, Inequality,
Cohesion, RestState, InvestmentPoints, MissionControl) are newest-first, 32 entries × 2-day
step. `arr[0]` = current; `arr[-1]` is ~2 months stale (verified against the in-game UI on a
federation-jump day). Identify nations by `templateName` (`2026_USA`…), never `displayName`
(renames on federation/annexation).

## Mission Control vs Earth CP-cap — TWO top-bar counters

### CP-cap formula (code-verified 2026-07-07, `TIFactionState:~2501`)

`CP cap = controlPointMaintenanceFreebies (global, 125) + Σ councilor.controlPointCapacity
+ Σ hab.controlPointCapacityValue (LEO admin modules) − SumEffects(Context.ControlPointMaintenance)`
— the effects carry NEGATIVE values, so subtracting them ADDS cap (Transnational Management
−120 → +120 cap; Management Research −5/repeat). `ControlPointMaintenance` localizes to
"Control Point Cap" — it is NOT money/influence upkeep (R8/R22 trap).


| Counter | Icon | Limits | "Used" field |
|---|---|---|---|
| Mission Control | blue sphere | habs + ships supported | `missionControlUsage` (exact) |
| Earth CP cap | red shield | Earth political CPs maintained | not stored — computed |

**MC available** = HQ (`baseIncomes_year.MissionControl`, typ. 22) + councilor-org
`incomeMissionControl` + `region.missionControl` (majority nations) + POWERED module MC>0.
**MC required** = Σ ship `missionControlConsumption` + POWERED module |MC<0| + mining
quadratic `(active_mines − freebies)²/2`. Reconstruction accuracy + the powered-filter rule:
[LESSONS-economy](LESSONS-economy.md) E19/E25 (top bar is truth; usage + mining exact;
available ≈ +7 high).

**Module table** (canonical): AdministrationNode 0 MC / +4 CP-cap (LEO only!) · Tower +1 / +12
· Complex +2 / +30 · OperationsCenter +4 · CommandCenter +10 · Outpost/PlatformCore −2 ·
Settlement/OrbitalCore −3 · Colony/RingCore −4 · ResearchCampus −1 / University −2 ·
Helium-3Mine −3 · SentinelComplex −1 · InterstellarLaunchingLaser −20. Admin modules' CP-cap
applies ONLY in Earth LEO (`LEOControlPointCapacity`).

**CP-cap inputs** the extractor can see: `controlPointMaintenanceFreebies` + LEO Admin
`controlPointCapacity` + `Effect_ControlPointMaintenanceBonus*` (value in trailing digits) —
partial; in-game tooltip is ground truth.

**CP LOAD ("Capacity Used") — exact, code-verified** (`TINationState.ControlPointMaintenanceCost`,
1.0.39 DLL): per held CP, `cost = (nation.GDP/1e9)^controlPointCostScaling / (2 × nation.numControlPoints)`,
zeroed for the alien nation and for crackdown CPs (`benefitsDisabled`). `controlPointCostScaling = 0.6`
(TIGlobalConfig; calibrated to reproduce the 2033-09-01 tooltip to the decimal — player load 847.2 =
Capacity Used 847). numControlPoints = the NATION's slots (clamp 6), so k-of-n costs k×cost. **Rank
factions by LOAD, not seat count** (`extract_snapshot.py` emits `cp_load_by_faction`;
[LESSONS-politics](LESSONS-politics.md) C17). The old `total_CPs × 32` flat heuristic is RETIRED —
per-CP cost ranges ~25–57 by GDP. Do NOT confuse `controlPointCostScaling`=0.6 (cap cost) with
`controlPointIPScaling`=0.35 (which defines `economyScore`, an IP quantity).

Overage history: `history_MCCapOverageByDay` — **NEWEST-FIRST** (index 0 = today; slice recent as
`[:N]`, never `[-N:]` — [LESSONS-process](LESSONS-process.md) P16), 32-day rolling.
`cachedYearlyRevenue.MissionControl` is only the Earth-facility flow — misleading.

## LEO bonus types (all cap 30%; detection +9 pts)

| Bonus | Modules (T1/T2/T3) | LEO-only? |
|---|---|:---:|
| MissionControl | SpaceScience Lab / Research Center / Institute | bonus LEO-only |
| Government | Social Science ladder | bonus LEO-only |
| Knowledge | Information Science ladder | bonus LEO-only |
| Welfare | Life Science ladder | bonus LEO-only |
| Environment | Climate ladder | **build LEO-only** |
| LaunchFacilities (Boost) | Energy ladder | bonus LEO-only |
| Miltech | Materials ladder | bonus LEO-only |
| ArmyCombatValue | Military Science ladder | bonus LEO-only |
| Economy | Nanofactory +2% / NanofacturingComplex +5% | bonus LEO-only |
| AlienDetection | Xenology ladder (+1/+2/+3 pts) | bonus LEO-only |
| HumanDetection + Oppression (coupled) | Listening Post / Recon Array / Argus | **build LEO-only** |
| PropagandaStrength | Broadcast Outlet / Comms Hub / Media Center | bonus LEO-only |

These same science modules also carry faction-wide CATEGORY research bonuses
([LESSONS-research](LESSONS-research.md) R16).

## Key save-file locations

- Cross-references between gamestate objects are `{"value": <id>}` wrapper dicts (so is
  each object's own `ID`) — deref the wrapper before joining (`extract_snapshot.deref`);
  a raw compare of ref vs id never matches. Saves can carry a UTF-8 BOM (even inside
  `.gz`) — open with `encoding="utf-8-sig"` ([LESSONS-process](LESSONS-process.md) P3).
- `TIGlobalResearchState` — global tech progress, `finishedTechsNames`.
- `TINationState` — per-nation scores: `GDP`, `economyScore` (= `(GDP/1e9)^0.35`, the IP
  base — [LESSONS-politics](LESSONS-politics.md) C19), `baseInvestmentPoints_month`
  (**available** monthly IP, post-penalty), `education` / `democracy` / `cohesion` /
  `unrest` / `inequality` / `militaryTechLevel` / `sustainability`, `spaceFunding_year`,
  `numNuclearWeapons`, `regions` (ref list — annexation audits diff its length, C18),
  `armies`, `wars` (enemy nation-ids, C13), `publicOpinion`, `controlPoints`, and the
  newest-first `history*` arrays (§ above). A nation object persists after annexation
  with `regions` emptied — `exists` stays true.
- `TIFactionState` — `researchWeights`, `currentProjectProgress` (active AND paused),
  `finishedProjectNames` / `availableProjectNames` / `missedProjects` / `hiddenProjects`,
  `activeProjectTriggers`, `resources.*`, `missionControlUsage`, `Transactions` (the spend
  ledger), `milestones` + `objectiveNames` (capability gates), `shipDesigns`,
  `availableCouncilors`, `availableOrgs`, `knownAlienSites`, `assessedAlienHateOfMe`.
- `TIHabState` (owner/type/tier/`sectors`/`habSite`) ↔ `TIHabModuleState` (via `sector`;
  fields `templateName`, `constructionCompleted`, **`powered`**, `_spaceCombatValue`,
  `destroyed`, `buildCost.resourceCosts` — the real per-body price paid, incl. the
  radiation surcharge). Solar output is NOT flat template power and the multiplier is
  NOT serialized — reconstruct per `docs/mechanics/Hab Power and Solar Output.md`
  (`hab_power_audit.py`); station habs resolve their body via
  `orbitState → TIOrbitState.barycenter` (which may be a Lagrange-point state, e.g.
  Sun-Mercury L1 — cost calibrations differ there).
- `TISpaceShipState` — `fleet`, weapons arrays (`moduleTemplateName`), `currentDeltaV_kps`,
  `currentMaxDeltaV_kps`, `cruiseAcceleration_mps2`, `propellant_tons`,
  `missionControlConsumption`, damage fields.
- `TISpaceFleetState` — `ships`, `faction`, `globalPosition`, `dockedLocation`, `trajectory`
  (destination + `arrivalTime` — committed transfers), `orbitState`.
- `TISpaceBodyState` — `displayName`, `globalPosition` (meters; Sol at origin).
- `TIControlPoint` — `faction` / `nation` / `controlPointType` per CP slot.
- `TIWarState` — a human-nation war: `attacker`/`defender` (side LEADERS),
  `_attackingAlliance`/`_defendingAlliance` (full sides incl. co-belligerents),
  `cohesionGainByNation`, `displayName` (leaders only). Nations reference a war ONLY through
  these arrays plus `TINationState.wars` — a flat list of **enemy nation-ids, not war-ids**;
  `TINationState.allies` = standing diplomatic pacts (distinct from war sides). Decode + the
  keep-both-in-sync rule: [LESSONS-politics](LESSONS-politics.md) C13; mutation safety:
  [LESSONS-process](LESSONS-process.md) P15.
- Rival snapshots: `resources` exact; `cachedYearlyRevenue` stale ±15-20% (rivals) and wrong
  for the player; fleet fuel mass in `fleetWetMassDuringHighestShipMaintainence.Water`.

## Faction templateNames

Resistance `ResistCouncil` · Initiative `ExploitCouncil` · Servants `SubmitCouncil` ·
Protectorate `AppeaseCouncil` · Academy `CooperateCouncil` · Humanity First `DestroyCouncil` ·
Project Exodus `EscapeCouncil` · Aliens `AlienCouncil`.

## Difficulty enum (code-verified 2026-06-11)

1=Cinematic, **2=Normal (default)**, 3=Veteran, 4=Brutal. Hate-floor ×/MC:
0.05 / 0.3 / 0.6 / 1.0. Read the campaign's difficulty from `config.json` and use the matching
column for every difficulty-keyed constant (the reference campaign ran Normal —
[LESSONS-aliens](LESSONS-aliens.md) A1).

## Victory

Per-faction condition sets in `TIVictoryTemplate.json`; full code-verified decode (conditions
semantics, win-mission mechanics, assault math, loot) in
[Victory Conditions and Endgame](../mechanics/Victory%20Conditions%20and%20Endgame.md).
Resistance status lives in the extractor's victory-chain table.
