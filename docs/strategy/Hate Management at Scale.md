---
title: Hate Management at Scale
game_version: 1.0.32 (build 22085164)
---

# Hate Management at Scale

> **Evidence vintage caveat (applies to all code citations in this note):** decompiled-source evidence is from a repo bracketed to builds 1.0.30–1.0.33 (commit 2025-06-12). Constants could drift in newer builds — re-verify after any game patch (templates via `sync_game_data.py`; code via the repo if updated). One flagged constant: `factionHateSIFactorPerShipDestroyed` = 0.4 in the decompile vs 0.35 on the wiki (possibly an older value) — settle in-game by killing one isolated alien ship and reading the intel hate-estimate delta (it updates live).

## Verdict (expanded)

### The MC-driven hate floor

**Floor = max(usedMC × per-difficulty multiplier × 0.8^maskingProjects, 20)** — usedMC is MC
*consumed* by ships + habs + refits (not your cap, not latent demand), and every hate write
clamps to [floor, ceiling], so nothing pushes hate below it. Canonical derivation, the
difficulty multipliers (Cinematic/Normal/Veteran/Brutal = 0.05/0.3/0.6/1.0) and the four
masking projects (stackable ×0.8 each → 0.8^n; OperationalSecurity is Resistance-only):
[Alien Hate and Diplomacy](../mechanics/Alien%20Hate%20and%20Diplomacy.md) §2.

- The **hard floor 20** applies to Resistance specifically: aliens are veryProAlien (ideology x=−3), Resistance veryAntiAlien (x=1) → `factionHateConflictThreshold = 20`.

**War begins at hate ≥ 50** (`alienFactionHateWarValue`; war progress = hate/50, evaluated monthly; the war goal discards when hate < 50 and not Total War). Maximum used MC that keeps the floor under the war line:

| Masking projects | Cinematic | Normal | Veteran | Brutal |
|---:|---:|---:|---:|---:|
| 0 | 1000 | 167 | 83 | 50 |
| 1 | 1250 | 208 | 104 | 62 |
| 2 | 1562 | 260 | 130 | 78 |
| 3 | 1953 | 325 | 162 | 97 |
| 4 | 2441 | 407 | 203 | 122 |

Any serious mid-game space economy (hundreds of used MC) exceeds these on Normal+ → **permanent war is MC-locked**; peace would require both cutting usage below the ceiling AND waiting out hate decay to <50 at ~0.32/month (decades).

### Action hate (dominates everything)

| Action | Hate gained |
|---|---|
| Ship killed (when not exempt — see below) | **0.4 × hull structuralIntegrity, ±20 %** (`hateVariance 0.2`) |
| Hab assault | 8 × tier |
| Hab destroyed | 1 + 3 × tier (+1 × moduleTier per module destroyed in combat contexts) |
| Initiating bombardment | 1 |
| Trade (equal / favorable-to-AI) | −9 / −18 — the ONLY reducer, and **unavailable to Resistance** (CanContactAlien requires proAlien ideology x<0) |

The ship-kill rule **REFUTES** the old "hate += full SI per kill" claim and resolves the escort anomaly: AlienEscort SI 10 → 0.4×10 = 4.0 ±20 % = 3.2–4.8, matching the empirical ~3.5/kill; a Battlecruiser (SI 48) costs 19.2 ± 3.8, not 48. **Zero-hate exemptions** (defense is free — full mechanics in [LEO Defense Doctrine](LEO%20Defense%20Doctrine.md)): combat at your own hab, victim was the combat's Attacker, or victim had an offensive goal vs you within 14 days.

### Passive growth and decay

Monthly gain (applied day 1 of each month) = components × `steadyAlienHateGainModifier` × progression-modified-years / 60:

| Component | Value |
|---|---|
| You are the aliens' most-threatening human enemy AND strongest human faction | +1.3 |
| Most-threatening but not strongest | +0.65 |
| Strongest but not most-threatening | 0 (wiki's two independent +0.65s overstated this) |
| Victory objective active | +0.5 |
| Resistance ideology (antiAlien 0.07 + veryAntiAlien 0.10) | +0.17 |

| `steadyAlienHateGainModifier` | Cinematic | Normal | Veteran | Brutal |
|---|---:|---:|---:|---:|
| | 0 | 1.0 | 1.9 | 3.3 |

Decay: monthly −1 ×0.8 (alien) ×0.8 (antiAlien target) = −0.64, applied to the most-threatening enemy **only on even months** → effective ≈0.32/mo; ×1.5 possible when aliens fight >2 factions and you're not most-threatening.

Hate ceiling = 1000 + 100 × progression-modified-years (Normal/Veteran/Brutal; Cinematic 70 + 2/yr), floored at 200 once past the Total-War gate year. Floor-overrides-max exists but rarely binds.

### Strategic synthesis: fastest win dominates

Passive gain scales with elapsed modified years (monotone), the ceiling rises, the Total-War gate arrives on a fixed date ([Base Sacrifice and Hate Venting](Base%20Sacrifice%20and%20Hate%20Venting.md)), and the alien escalation project fires on a fixed date ([Offense Timing vs Aliens](Offense%20Timing%20vs%20Aliens.md)). **Time works against you on every axis** — the wiki's "war by year ~17 on Veteran with zero hostile actions" table is plausible (the generating function `GetExpectedYearsUntilWarWithAliens` exists and matches; lands later on Normal). Don't optimize hate; optimize time-to-victory and keep defense in the zero-hate channels.

### Hate spill (multi-faction bookkeeping)

Alien hate gains feed the Proxy faction (Servants) +value/2 (if contacted, else /4) and the Appeaser +value/3 (only when they can contact aliens). Fighting Exodus/HF does NOT feed alien hate; attacking the PROXY feeds aliens value/4 (contacted) or /8.

## Evidence

**Tier 1 (code/templates/save, verified):** `TIFactionState.cs:10970` MCBasedAlienHate; `:3455` missionControlUsage definition; `:10981` MinimumFactionHate (conflict threshold 20); `:10901–10930` GainFactionHate clamp; `TIGlobalConfig.cs:1941–1950` per-MC multipliers; `:2175` warValue 50; `:2163` conflictThreshold 20; `:1845–1866` ceiling constants; `:1809–1818` steady-gain modifiers; `:2148` SI factor 0.4; `:2202` hateVariance; `:2136–2154` action-hate constants; `:2157–2160` trade constants; `AIDailyFactionPlanner.cs:365–402` monthly gain components; `:528–531` deescalation cadence; `TIEffectTemplate.json` Effect_MCUsageMasking {Multiplicative 0.8, stackable}; `TIFactionState.cs:17147` CanContactAlien (proAlien gate); spill at `:10930–10960`. *(all high)*

**Verdict provenance:** MC floor formula VERIFIED (exact code claim); war threshold + ceiling arithmetic VERIFIED; floor/venting difficulty numbers MODIFIED (community used Veteran values everywhere); passive-growth components MODIFIED (strongest-only = 0); "hate += SI per kill" REFUTED (0.4×SI); "Veteran 0.6 applies to the reference campaign" REFUTED (campaign is Normal); "nothing can lower hate for Resistance" MODIFIED (passive decay + venting channels exist).

**REFUTED myths:** ~~"Masking projects subtract 20 % each (additive)"~~ — multiplicative 0.8^n · ~~"The hate floor uses MC capacity"~~ — used MC only · ~~"hate += hull SI per kill"~~ — 0.4×SI ±20 %.

## Worked example — the reference campaign (Resistance, 2032-05 snapshot)

- **Normal difficulty** (save difficulty=2; the campaign's hardness is from customizations: alienProgressionSpeed 2.0, researchSpeed 2.0). All Veteran-keyed community numbers are wrong for this save.
- Hate **437.55**; used MC **516**; 3/4 masking done (missing OperationalMisdirection, gated on FleetLogistics 45k) → floor = 516 × 0.3 × 0.512 = **79.3** (→ **63.4** with the 4th project). Floor > 50 → war is MC-locked at current scale; exit would need usage ≤325 (3 proj)/≤406 (4 proj) plus decades of decay from 437. **Permanent war confirmed — by Normal numbers, not Veteran ones.**
- Ceiling currently ≈2253 (not binding). Passive growth runs at ×1.0, half the Veteran-keyed estimate.
- Operational rule: defend in the zero-hate channels, buy FleetLogistics for the 4th mask (it double-counts toward Titans and OperationalMisdirection), and treat every elective offensive as a 0.4×SI hate purchase.

## Sources

- https://wiki.hoodedhorse.com/Terra_Invicta/Diplomacy · …/Aliens (MediaWiki api.php)
- https://github.com/Armandox33/Terra-Invicta-AI-Assistant — TIFactionState.cs / TIGlobalConfig.cs
- https://www.reddit.com/r/TerraInvicta/comments/1tjsfrz/when_to_stop_trying_to_control_hate/ · …/1s09hj1/alien_hate_this_one_simple_trick/
- Save-empirics 2032-05-09. Related: [Base Sacrifice and Hate Venting](Base%20Sacrifice%20and%20Hate%20Venting.md) · [LEO Defense Doctrine](LEO%20Defense%20Doctrine.md) · [Offense Timing vs Aliens](Offense%20Timing%20vs%20Aliens.md)
