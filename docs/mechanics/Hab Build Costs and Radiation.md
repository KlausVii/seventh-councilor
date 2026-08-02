---
title: Hab build costs — the radiation surcharge
evidence: save-empiric (queued `TIHabModuleState.buildCost` readings, cross-checked against the in-game "Build In Space" line); confidence high for the bodies listed, extrapolated for other belt objects
---

# Hab build costs — the radiation surcharge

Module build/upgrade costs in space are **not** uniform per template: high-radiation bodies
carry a large surcharge, mostly on metals. **Gravity is NOT the driver** — Mercury and Mars
have similar surface gravity and wildly different costs; the pattern tracks the radiation
environment (Jupiter's belts, solar proximity).

Read the real cost for anything you're about to click from the in-game Build panel — it is
ground truth. The table below is for *planning* (ranking candidate sites before you're
in-game); `mine_upgrade_planner.py` embeds it as `BODY_COST`; `cc_upgrade_planner.py` carries the CC variant as `BODY_METALS` (§ below).

## T2→T3 mine upgrade (Settlement → Colony Mining Complex): water / volatiles / metals

| Body | Cost (wat / vol / metals) | Notes |
|---|---|---|
| Luna | 33.8 / 33.8 / **267** | baseline, low radiation |
| Ceres & main-belt asteroids | ~51 / 51 / **~412** | extrapolated to unlisted belt objects (marked `~` in script output) |
| Deimos / Phobos | 60.4 / 60.4 / **477** | |
| Callisto | 60.8 / 60.8 / **480** | outside Jupiter's worst belts |
| Mars | 62.3 / 62.3 / **492** | |
| Ganymede | 69.5 / 69.5 / **1,313** | radiation ≈×2.7 on metals vs the Mars/Callisto baseline (~×4.9 vs Luna) |
| Mercury | 130.9 / 130.9 / **2,300** | solar radiation, not gravity |
| Europa | 80.9 / 80.9 / **2,500** | |
| Io | 99.7 / 99.7 / **3,800** | worst radiation — ~14× Luna on metals |

Readings from queued builds in reference-campaign saves (build ~1.0.38). Same-body costs for
other module types scale with the same surcharge pattern.

## Planning consequences

- **ColonyCore (T2→T3 hab core) upgrades are cheap by comparison** (~27 volatiles + 27–85
  metals, 45–60 days even on Ganymede). "Needs a T3 core first" is a minor tax on a mine
  upgrade, not a blocker — queue the core early so the mine click is ready when you can
  afford it.
- **Payback ordering follows the surcharge**: identical site yields pay back in weeks–months
  on Luna/Mars/belt/Callisto and in 2–4 *years* on Io/Mercury/Europa. Upgrade radiation
  bodies only with a strategic resource reason (e.g. a uniquely rich fissile site).
- **Costs are paid entirely up front at click time** (see LESSONS-economy on construction —
  no pause, no refund; shortfalls silently backfill from Earth on boost). Keep each click
  within your current stockpile.
- Mining production multipliers from tech/orgs stack on top of site rate × tier — derive
  them from your save (`mine_completion_timeline.py` does this automatically); e.g. the
  reference campaign in 2033 ran ×2.2 on water/metals/nobles/fissiles and ×1.7 volatiles.

## Build TIME — the construction-accelerator (nanofactory) speed law

Cost is one axis; **time** is the other, and it has its own lever. A hab-module build or
upgrade takes `baseBuildDuration_days × build_time_bonus`, and every **powered, completed**
module at that hab whose template carries `constructionTimeModifier < 1` speeds it up.
Sorted strongest-first, the k-th accelerator multiplies build time by **`1 − (1−modifier)/k²`**
— so the first one does almost all the work and each extra adds sharply less. Code-verified
against 16 distinct `appliedBuildConstructionBonus` readings from reference-campaign saves,
including mixed stacks; encoded in `cc_upgrade_planner.py::build_time_bonus()`.

The accelerator modifiers (from the templates; alien equivalents match):

| Module | `constructionTimeModifier` | 1 alone | notes |
|---|---:|---:|---|
| NanofacturingComplex (T3) | 0.60 | **×0.60** | strongest — beats any stack of the weaker two |
| Nanofactory (T2) | 0.75 | ×0.75 | the cheap, common accelerator |
| ConstructionModule (T1) | 0.90 | ×0.90 | marginal |

Worked stacks (reference campaign, matched to 5 decimals): 1 Nanofactory = ×0.75 (a 160-day
Shipyard→Spaceworks upgrade → 120 d); 2 = ×0.703; 3 = ×0.684; 6 Nanofactories = ×0.662;
1 NanofacturingComplex + 3 Nanofactories = ×0.538. **One accelerator captures nearly the
whole benefit** — stacking is deeply diminishing, so spread accelerators across production
habs rather than piling them on one.

⚠ **Shipyard/Spaceworks do NOT accelerate hab-module builds** — their `constructionTimeModifier`
(`allowsShipConstruction: true`) speeds SHIP construction only. A base with two powered
Spaceworks and no nanofactory still builds modules at ×1.0.

Two planning consequences: (1) **a Shipyard→Spaceworks upgrade's base time is ~160 days**, not
the module template's headline figure — with one nanofactory it lands in ~120; pick which yards
to upgrade partly by which already have an accelerator. (2) When choosing where to build a
module wave, prefer habs that already carry a NanofacturingComplex or Nanofactory.

## Upgrades vs fresh builds — duration and cost discounts

Upgrading a module IN PLACE is cheaper and faster than the template's headline
figures, and the discount is visible directly in queued builds
(`baseBuildDuration_days`, `buildCost.resourceCosts`):

- **Duration: an upgrade runs at ~2/3 of the fresh-build base.** Reference-campaign
  reading: every queued OperationsCenter→CommandCenter upgrade shows a 160-day base
  (template `buildTime_Days` 240); the one fresh CC build over a destroyed slot shows
  the full 240.
- **Cost: same pattern.** OC→CC upgrades read **400 metals** at baseline bodies where
  the fresh build reads 600.
- **The prior module goes OFFLINE at click time** (its module state is replaced;
  only `priorModuleTemplateName` remains). Its income/MC leaves your totals the moment
  you click, not when the upgrade finishes — so an OC→CC completion is +10 MC vs the
  current top bar, not +6 (see LESSONS-economy on module upgrades).

### OC→CC upgrade metals by body (calibrated from queued builds)

| Body | Metals | Confidence |
|---|---:|---|
| Earth orbit, Luna, Mars, Phobos/Deimos, Ceres, belt, outer-Jovian irregulars, Callisto orbit | **400** | exact (many readings) |
| Mercury | **933** | exact |
| Ganymede / Europa / Io | ~750 / ~950 / ~1,100 | extrapolated from the mine surcharge curve — the CC surcharge is much gentler than the mine one (Mercury: ×2.33 vs ×8.6), so read the Build panel before trusting these |

`cc_upgrade_planner.py` embeds this table (`BODY_METALS`); update it from
`buildCost.resourceCosts` when you queue a CC on an uncalibrated body.

## Accelerators apply MID-BUILD

A Nanofactory/NanofacturingComplex/ConstructionModule finishing while another build is
in progress at the same hab starts accelerating the REMAINING work the moment it comes
online — you don't need to wait for it before clicking. Planning consequence: it can be
right to start a 160-day upgrade at a hab whose NanofacturingComplex lands in a month —
the effective total is far below 160. `cc_upgrade_planner.py` simulates this (piecewise
progress rates, bonus recomputed at each incoming accelerator's ETA) and shows the
incoming accelerators per candidate; treat its est-days as an estimate and the in-game
completion date after clicking as truth.
