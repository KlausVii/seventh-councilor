---
title: Research Skips
game_version: 1.0.32 (build 22085164)
---

# Research Skips

> **Evidence vintage caveat (applies to all code citations in this note):** decompiled-source evidence is from a repo bracketed to builds 1.0.30–1.0.33 (commit 2025-06-12). Constants could drift in newer builds — re-verify after any game patch (templates via `sync_game_data.py`; code via the repo if updated).

## Verdict (expanded)

### What victory actually requires (the floor you cannot skip)

A full prerequisite-closure walk of `Project_TheFinalAssault` (incl. The Choke Point) + Defend the Earth gives **17 nodes, 196,275 RP — all Xenology projects plus Skywatch/DeepSystemSkywatch**. Zero weapon, drive, or armor branches are transitively required for the Resistance win. Key costs: Project_TheChokePoint **40,000**, Project_TheFinalAssault **25,000**, Project_ResistVictory ("Defend the Earth") only **2,500** (prereq: Project_TheirOperations).

Victory-chain projects roll reliably once prereqs complete: `factionAvailableChance 100` guarantees the unlock trigger; it starts at a 50 %-monthly-equivalent daily roll (+Science/5 +tech-contribution bonus) and climbs +50/month (× research-speed modifier) to 100 — **worst case ≈1 month + 1 day** from prereq completion, expected 2–3 weeks. No RNG hedging needed.

Everything else you research is for *survival and force projection*, not victory — which is what makes the skips below safe.

### Safe skips (verified mechanisms)

| Skip | Why (mechanism) |
|---|---|
| **~90 % of engine lines** | Built ships can only refit drives within the SAME `driveClassification` + `requiredPowerPlant` + `propellant` (`TIDriveTemplate.IsValidRefitPart`). Cross-chain transitions force new construction. Commit to 1–2 chains. The "family" is wider than name-lines: ALL Fission_Thermal/Gas_Core_Fission/Hydrogen drives are mutually refittable (Burner↔Firestar↔Lodestar↔Pharos↔Flare↔Quartz↔Lightbulb); NeutronFluxLantern→NeutronFluxTorch is a legal refit. Zero drive nodes in any victory closure. |
| **Redundant weapon lines** | One kinetic chain + one laser chain covers the doctrine matrix ([Weapon Doctrine vs the Hydra](Weapon%20Doctrine%20vs%20the%20Hydra.md)). Coilguns strictly supersede railguns per mount. |
| **Exofighters (OrbitalFighters, 7,500 RP)** | TRAP. It's a **global** tech: once ANY faction finishes it, it's finished for everyone, and exofighters are *nation* assets commanded by executive factions, launched from Earth facilities against fleets/stations in Earth interface orbits — researching it mainly accelerates hostile humans (and alien-run nations) raiding YOUR LEO. Aliens field their own fighters regardless (`AlienFighterController`). Not in any victory closure. |
| **Particle weapon PROJECTS** | Radiation pass-through is hard-capped at 6.25 % through any unchipped armor; Spinal Neutron Lance has `heatFraction 0` — pure radiation, literally cannot structure-kill a ship. |
| **Plasma (this run / generally as a primary)** | Plasma is an armor-stripper, not a killer (flatChipping 0.8, max ~5.5 direct pts). A researched railgun line already out-chips it. See the full refutation in [Weapon Doctrine vs the Hydra](Weapon%20Doctrine%20vs%20the%20Hydra.md). |
| **Exotic armor (only)** | Obsolete once Hybrid is researched (no specialty; worse per-mass than Hybrid on every axis). **Hybrid is NOT a skip** — see the exception below. |
| **Most military Earth-defense projects** | Consistent with Defend the Earth costing only 2.5k with a Xenology prereq — the military projects are not part of the chain (judgment, plausible). |

### Must-NOT-skip exceptions (the traps inside the skips)

**Hybrid armor (superseded verdict, 2033 re-verification):** an earlier draft listed Exotic/Hybrid as a safe skip on "terrible radiation halfValues (5.2/4.5 cm)" — that compared raw cm rather than points-to-halve, and applies only vs particle-weapon threats. Per-point laser blocking is material-independent, so Hybrid's LaserResistance 0.75 makes it the **best general anti-Hydra armor** (the Hydra is beam-heavy); Adamantane wins only the kinetic channel. See [Space Combat Math](../mechanics/Space%20Combat%20Math.md) §2.5b and [LESSONS-ships](../lessons/LESSONS-ships.md) S12.

**The fusion path transitively requires two cheap "particle/laser" GLOBAL techs:** `Neutronics` (15,000) — prereq of `NuclearFusioninSpace`/`DeuteriumTritiumFusion` — requires **`ParticleCannon` (5,000)**, which requires **`HighEnergyLasers` (1,000)**. "Skip particle weapons" must mean skip the weapon *projects*, never these globals, or you lock yourself out of every fusion drive.

### Earth-side note

~12 union/federation-forming projects exist by display name (African Union, South American Union, Nordic Federation, Central Asian Union, Maghreb, etc.) — consistent with "11–12 needed for the final meganations"; the community's "~48 unification/breakup projects" total could not be reproduced (unverifiable). Formation projects are efficiency, not victory requirements — see [Earth Endgame Consolidation](Earth%20Endgame%20Consolidation.md).

## Evidence

**Tier 1 (code/templates, verified):**
- Victory closure walk over `TIProjectTemplate.json`/`TITechTemplate.json`: 17 nodes / 196,275 RP, all Xenology + Skywatch. *(high)*
- `TIDriveTemplate.cs:526 IsValidRefitPart` — classification+reactor+propellant equality; `TIPowerPlantTemplate.cs:112` — same `powerPlantClass`. *(high)*
- `TITechTemplate.json` OrbitalFighters (7,500, MilitaryScience, global); localization: "nation assets under an executive faction's command… hangared at launch facilities"; `LaunchSTOInterceptorsOperation`. *(high)*
- `TIParticleWeaponTemplate.json` SpinalNeutronLance `heatFraction 0`; armor radiation cap `Mathf.Min(0.0625, 0.5^(thickness/halfValue))` in `TISpaceShipState.AbsorbAndApplyArmorDamage`. *(high)*
- DT-fusion closure includes ParticleCannon ← prereq of Neutronics; HighEnergyLasers ← prereq of ParticleCannon. *(high)*
- Unlock-roll machinery: `TIFactionState.RollToAddProjectTrigger` (monthlyTriggerValue = initialUnlockChance + bonuses), `DailyProjectTriggerCheck` (p_day = 1−(1−p_month)^(1/30.44), the 0.032854885 exponent), `MonthlyProjectTriggerChanceChange` (+deltaUnlockChance × research-speed, clamp at max). Choke Point/Final Assault both `factionAvailableChance:100, initial 50, delta 50, max 100`. *(high)*

**Verdict provenance:** minimal-tech-path claim MODIFIED (fusion-globals exception added); exofighter trap VERIFIED; drive-sprawl trap VERIFIED; research-beeline claim MODIFIED (union-project count partially corroborated); "monthly unlock rolls" mechanism MODIFIED (it's a daily roll at monthly-equivalent probability).

**REFUTED/corrected myths:**
- ~~"Burning cheap projects compounds research speed (+5%/+3%/+1% per completed project)"~~ — the multiplier counts ACTIVE project-slot-granting facilities, not completions. See [Converting a Research Lead](Converting%20a%20Research%20Lead.md).
- ~~"You need broad military research to win"~~ — the win chain is 100 % Xenology+Skywatch.

## Worked example — the reference campaign (Resistance, 2032-05 snapshot)

- The player's 271 finished projects already include the green-laser line, railguns Mk1–3, TC1–3, Project_AlienECM. Closure arithmetic: at ~272 RP/day the 196k victory chain alone ≈ 2 in-game years if researched exclusively — research is NOT the binding constraint; drives and fleet are ([Converting a Research Lead](Converting%20a%20Research%20Lead.md) § drive-tier framework).
- `DeuteriumTritiumFusion` (50k) is **queueable now** (prereqs NuclearFusioninSpace + Neutronics done — i.e., the player already paid the HighEnergyLasers/ParticleCannon toll).
- Plasma line: zero researched — correct, keep skipping.
- Note: the reference campaign runs `researchSpeedMultiplier 2.0` (customization), which scales the +50/month unlock-chance climb too.

## Sources

- https://www.reddit.com/r/TerraInvicta/comments/1qck42l/what_are_some_earlymid_game_research_traps_asking/
- https://wiki.hoodedhorse.com/Terra_Invicta/The_Choke_Point · https://wiki.hoodedhorse.com/Terra_Invicta/Close_the_Gate (rendered DOM)
- Decompile: https://github.com/Armandox33/Terra-Invicta-AI-Assistant; local templates build 22085164
- Related: [Converting a Research Lead](Converting%20a%20Research%20Lead.md) · [Weapon Doctrine vs the Hydra](Weapon%20Doctrine%20vs%20the%20Hydra.md) · [Drives Refits and Logistics](../mechanics/Drives%20Refits%20and%20Logistics.md)
