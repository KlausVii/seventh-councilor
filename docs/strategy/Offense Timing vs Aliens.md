---
title: Offense Timing vs Aliens
game_version: 1.0.32 (build 22085164)
---

# Offense Timing vs Aliens

> **Evidence vintage caveat (applies to all code citations in this note):** decompiled-source evidence is from a repo bracketed to builds 1.0.30–1.0.33 (commit 2025-06-12). Constants could drift in newer builds — re-verify after any game patch (templates via `sync_game_data.py`; code via the repo if updated).

## Verdict (expanded)

### The defend-at-parity criterion (doctrine, judgment-grade)

"Go on offense when you can defend" is community doctrine, not code — but the physics premise is verified: alien drives massively out-dV human early/mid fleets, so **the aliens choose every engagement** until you reach drive parity. Until then, posture is defense-first because nothing else is physically available. Two code-verified facts make defense-first cheap:

1. **Defense is hate-free.** Destroying ships generates zero hate for the killer when the victim initiated the combat, had an offensive goal against you within 14 days, or the fight was at your own hab ([LEO Defense Doctrine](LEO%20Defense%20Doctrine.md) for full mechanics). Even **active interception of an alien fleet en route to attack you is hate-free on this build** — the cost of defense is ~zero.
2. **Offense is priced.** Hunting alien fleets that had not targeted you costs 0.4 × hull SI per kill (±20 %) — quantifiable, modest, but it feeds the war machine ([Hate Management at Scale](Hate%20Management%20at%20Scale.md)).

### What offense triggers — the alien home-system response

Code-verified (this is the 1.0.30–1.0.32 alien AI overhaul): defenders of the alien faction's **primary-hab system** get **1.5× desired fleet combat value** and may concentrate up to **4× the normal max fleet ratio** (vs 2× elsewhere) when the system is in defense mode; alien factions skip the 0.6× human discount. **Camping or raiding the alien home system triggers a much stronger organized response than mid-system raiding.** The 1.0.30–32 changelog also adds consolidated alien rescue/defense fleets when the primary system is occupied or about to be — size any Kuiper assault for their **total remaining navy**, not the local garrison.

### Alien rebuild rate vs kill rate

- Once the alien mining economy is dead, their losses are effectively irreplaceable (judgment, consistent with mine-limit and hab-raid mechanics; not code-audited).
- **The Alien Advanced Master Project clock**: `Project_AlienAdvancedMasterProject` auto-completes when progression-modified campaign years exceed the difficulty threshold, granting the aliens ×0.8 ship build time (**+25 % build rate**) and **+5,000 exotics**:

| | Cinematic | Normal | Veteran | Brutal |
|---|---:|---:|---:|---:|
| `yearsBeforeAlienAdvancedTech` (modified years) | 35 | 25 | 16 | 10 |

Kill rate vs build rate therefore *degrades on a fixed date* — another reason fastest-win dominates.

### Zero-hate interception doctrine (the refinement)

The old doctrine was "park, never sortie." The verified 1.0.32 rule is better: **sortie freely against committed attackers** (any alien fleet with an AttackWithFleet/CaptureHab goal against you in the last 14 days, including current) — it costs nothing. What still costs: hunting uncommitted patrols, trespassing into alien turf (≥Jupiter SMA, any alien-base system, any non-Earth alien-station system — where your losses also vent nothing), and elective deep raids.

### Expendable pickets

Sacrificial picket screens vs superior alien ΔV are an option (their premise — interception genuinely fails at low dV — is save-verified), but the claimed "aliens need recovery time after any engagement" mechanism was NOT found in code. Treat picket-sacrifice as unproven tempo tech; remember trespassing pickets vent nothing when they die.

## Evidence

**Tier 1 (code/save, verified):** `FactionGoal_DefendWithFleet.cs` — IsPrimarySystemDefender (line 150), ×1.5 desired value, 4× max ratio, alien skip of ×0.6 human discount. `TIFactionState.MonthlyFactionUpdate:1859` + `TIGlobalConfig` yearsBeforeAlienAdvancedTech 35/25/16/10; `TIProjectTemplate.json` Project_AlienAdvancedMasterProject (Effect_ShipConstructionTimeReduction 0.8 + 5,000 exotics). `TISpaceCombatState.cs:1340–1366` zero-hate exemptions. Save-empiric: fleet dV asymmetry. *(high)*

**Tier 3/4 (judgment, flagged):** defend-at-parity criterion (plausible, no template refutes); alien convergence to defend final bodies (changelog-supported, not code-verified); picket recovery-time premise (unverified). *(medium/low)*

**Verdict provenance:** "go on offense when you can defend" judged plausible; home-system defense AI VERIFIED; alien escalation MODIFIED (conditions corrected — it had NOT fired in the save, and the campaign is Normal); expendable-pickets premise verified, mechanism unverified.

## Worked example — the reference campaign (Resistance, 2032-05 snapshot)

- **Force balance at 2032-05:** aliens 85 ships / 33 fleets / 565.5 kt vs the player's 66 ships / 331 kt; average dV **648 kps (alien) vs 38 kps (the player's)**; combat accel 27.2 vs 10.9 m/s². The player's fleet literally cannot reach the alien rear (Lodestar warships are below solar escape velocity) — offense is gated on the fusion-drive program, not on courage. See [Converting a Research Lead](Converting%20a%20Research%20Lead.md) § drive-tier framework.
- **The two clocks:** Total War flips ≈**2036-02** ([Base Sacrifice and Hate Venting](Base%20Sacrifice%20and%20Hate%20Venting.md)); Alien Advanced Master Project fires at modified years >25 → elapsed >12.5 yr → ≈**2038-08** (code-derived; see Alien Production Rebuilding and Targeting) (NOT fired yet in the save — the current alien fleet is *not* building 25 % faster). The comfortable offensive window is therefore roughly 2033–2038: late enough to have fusion drives, early enough to beat the +25 % build rate and the 5,000-exotic infusion.
- Near-term doctrine: zero-hate interception at home, kill committed attackers freely, no elective hunts, build toward the Kuiper-capable fleet.

## Sources

- https://www.reddit.com/r/TerraInvicta/comments/1oym9dz/whens_a_good_time_to_fight_the_aliens/
- https://www.pavonisinteractive.com/phpBB3/viewtopic.php?f=26&t=29984 (patch notes, Claude-in-Chrome MCP)
- Decompile: https://github.com/Armandox33/Terra-Invicta-AI-Assistant; save-empirics 2032-05-09
- Related: [Hate Management at Scale](Hate%20Management%20at%20Scale.md) · [LEO Defense Doctrine](LEO%20Defense%20Doctrine.md) · [Capital Ship Doctrine](Capital%20Ship%20Doctrine.md) · [Exotics and Antimatter Acquisition](Exotics%20and%20Antimatter%20Acquisition.md)
