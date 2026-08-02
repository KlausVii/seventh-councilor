---
title: Strategy doctrine (index)
game_version: 1.0.32 (build 22085164)
---

# Terra Invicta — Strategy doctrine

**Purpose:** answered strategic questions, banked. Each note below is a *doctrine verdict* produced by an adversarial "Deep Strategic Review" pipeline: community claims were collected with provenance, then adversarially verified against the decompiled game code, the build-matched templates (build 22085164 = v1.0.32), and the live save. Verdicts cite code symbols and template fields inline; REFUTED community myths are named explicitly so they don't resurrect.

**The question-list philosophy:** answered questions accumulate. **Check this folder before re-researching anything** — these notes replace re-running a ~40-agent verification pipeline. If a note answers your question, trust its tiered evidence (and its named refutations) over fresh community lore. If the game gets patched, re-verify the cited constants first (templates via `sync_game_data.py`, code via the decompile repo) rather than re-deriving the doctrine.

**Reading convention:** every note states the campaign-independent rule first (all difficulty columns — enum: 1=Cinematic, 2=Normal, 3=Veteran, 4=Brutal), with reference-campaign numbers only as labeled examples (Resistance, Normal difficulty, alienProgressionSpeed 2.0, researchSpeed 2.0 — scale by your config). The single most consequential review finding: **the reference campaign is Normal, not Veteran** — any community table using Veteran-keyed constants for a Normal save is wrong.

## The twelve questions

### Combat doctrine
- [Missile Swarm Doctrine](Missile%20Swarm%20Doctrine.md) — Q1: saturation-only mechanics; super-salvos 30–50/target; PD-window math; magazine sizing; the micro burden; AM-torpedo escort swarms (far-future).
- [Weapon Doctrine vs the Hydra](Weapon%20Doctrine%20vs%20the%20Hydra.md) — Q4: kinetics-for-line / lasers-for-flankers; closing-velocity² kinetics; plasma = stripper (myth refuted); PD composition matrix; TC mandatory; nose-heavy armor with breakpoint caveats.
- [Capital Ship Doctrine](Capital%20Ship%20Doctrine.md) — Q8: the 30-ship battle cap as the real case for capitals; hardpoints-per-MC table; Lancer = the cheap 4-nose capital (960 cm fits it); corvette filler; hab-assault math.

### The alien relationship
- [Hate Management at Scale](Hate%20Management%20at%20Scale.md) — Q5: the MC-driven hate floor by difficulty; masking stack 0.8^n; action-hate table; passive growth/decay; why the fastest win dominates.
- [Base Sacrifice and Hate Venting](Base%20Sacrifice%20and%20Hate%20Venting.md) — Q2: the three vent conditions; vent amounts; the knockdown reprieve (never Total-War-locked); the deterministic Total War clock per difficulty.
- [LEO Defense Doctrine](LEO%20Defense%20Doctrine.md) — Q10: the three zero-hate exemptions; the 14-day committed-attacker rule (interception is free); station defense; never run an MC deficit.
- [Offense Timing vs Aliens](Offense%20Timing%20vs%20Aliens.md) — Q6: defend-at-parity criterion; zero-hate interception; the alien home-system 1.5×/4× response; the two fixed clocks bounding the offensive window.

### Research and economy
- [Research Skips](Research%20Skips.md) — Q3: victory closure is pure Xenology+Skywatch (~196k RP); engine/weapon/exofighter/plasma skips; the HighEnergyLasers+ParticleCannon fusion-gate exception.
- [Converting a Research Lead](Converting%20a%20Research%20Lead.md) — Q11: slot discipline (no Versatility bonus — a ×0.9 penalty); Xenology lab stacking; contribution flooding; the drive-tier decision framework.
- [Exotics and Antimatter Acquisition](Exotics%20and%20Antimatter%20Acquisition.md) — Q9: the complete exotics loot formula; councilor-assault farming; AM = colliders-only, skip-unless-needed.
- [Research Sequencing](Research%20Sequencing.md) — *method addendum (deliberately un-numbered — it's the "how to drive the queue" companion to Q3/Q11, not a thirteenth verdict)*: the campaign-independent slot/weight method — read the UI as ground truth, weight the binding lanes, pre-plan every opening slot, write tripwires, re-derive each snapshot. Worked applications live per-campaign in `campaign/reports/`.
- [Late-Game Money](Late-Game%20Money.md) — Q12: market selling (the 50× infusion pattern); commercial modules; funding mechanics; AM break-even; org portfolio hygiene.

### Earth
- [Earth Endgame Consolidation](Earth%20Endgame%20Consolidation.md) — Q7: the win needs ZERO Earth expansion (only zero alien regions); tall CP sizing; formation projects as efficiency, not requirement.

## Related
- [Mechanics index](../mechanics/README.md) — the mechanics-reference layer these doctrines cite (formulas without the strategic judgment).
- [Space Combat Math](../mechanics/Space%20Combat%20Math.md) · [Drives Refits and Logistics](../mechanics/Drives%20Refits%20and%20Logistics.md) — mechanics notes these doctrines lean on most.
- `docs/lessons/` — the verified-lessons library.

## Open questions (not yet banked — candidates for the next review)
- Alien adaptive counter-design vs player weapon mix (UNVERIFIABLE this pass; experiment design exists in [Weapon Doctrine vs the Hydra](Weapon%20Doctrine%20vs%20the%20Hydra.md)).
- Earth army/eviction mechanics for clearing the Alien Nation (flagged in [Earth Endgame Consolidation](Earth%20Endgame%20Consolidation.md)).
- Exact installed-build value of the ship-kill hate constant (0.4 vs 0.35) — one-kill in-game test settles it ([LEO Defense Doctrine](LEO%20Defense%20Doctrine.md)).
- Alien post-combat recovery-time behavior (picket doctrine premise, unverified).
