---
title: Missile Swarm Doctrine
game_version: 1.0.32 (build 22085164)
---

# Missile Swarm Doctrine

> **Evidence vintage caveat (applies to all code citations in this note):** decompiled-source evidence is from a repo bracketed to builds 1.0.30–1.0.33 (commit 2025-06-12). Constants could drift in newer builds — re-verify after any game patch (templates via `sync_game_data.py`; code via the repo if updated).

## Verdict (expanded)

Missiles are a **saturation-only** weapon class. The mechanics that force this:

1. **One PD hit kills any missile, unconditionally** (`MissileController.ApplyDamage` sets `beenDestroyed=true` on any hit; AOE warheads may still detonate if an enemy is inside the blast radius). There is no missile HP pool to chew through.
2. **PD kill rate is cooldown-bound, not damage-bound.** The alien dedicated PD laser fires every **2.4 s** out to **350 km**; dual-mode main lasers also engage missiles, but only inside **range/3** (≈233–266 km for alien main guns) at their 12–18 s cooldowns. A *sequential* missile stream is destroyed one-by-one indefinitely; a *simultaneous* salvo larger than the shots-available-in-the-terminal-window gets leakers through. That window math (per alien warship-class target at 2032 tier): **~18–30 intercepts per dedicated PD turret per terminal window, +2–5 per dual-mode main laser** → super-salvos of **~30–50 missiles per target, arriving simultaneously**, are required.
3. **Micro burden is by design, not a UI flaw.** Missile weapons get only Focus/Salvo fire modes, which fire **exclusively at the ship's manually designated `primaryTarget`** — there is no offensive auto-fallback. Salvo mode auto-idles after firing `FullAmmoCount/4`. There is no cross-ship launch synchronization; building the super-salvo is manual per-target work every battle.
4. **Magazines are finite and there is no in-combat reload.** Standard missile Bays carry **16** per launcher (Pods 4, nuclear missiles 8/4, torpedo bays 4–6, Krait 12 — always pick the 16-round Bay variants). Each **Magazine utility module adds +50% ammo** (`specialModuleValue 0.5`, 100 t, stacks). Resupply requires returning to a hab. An all-missile ship is inert after dumping.
5. **Targeting Computers are mathematically mandatory.** Non-AOE missile hits are negated with probability = target ECM − attacker TargetingBonus, and **the bonus only counts if the launching ship still exists** at impact. Census of the alien fleet (save, 2032-05): **50/85 ships carry AlienECM (0.6)**; all 80 combat ships carry AlienTargetingComputer (0.5). Without a TC your missiles are **60 % negated**; with TC3 (0.5) only **10 %**. ([Weapon Doctrine vs the Hydra](Weapon%20Doctrine%20vs%20the%20Hydra.md) has the beam-side ECM rules.)
6. **AOE (nuclear/antimatter) missiles ignore ECM entirely** — `MissileDamage` skips the ECM roll for `AOEWeapon`.
7. **Missiles cost zero ship energy** (`TIMissileTemplate.EnergyUsage_GJ` returns 0) — no weapon-heat interaction, so missile mounts don't compete with lasers for power/heat budget.

### Torpedoes vs missiles — what "better" actually means

Torpedoes carry **2–4× missile delta-V** but **LOWER acceleration** (4.89–9.14 g vs 14.9–18.3 g for late missiles; Athena torpedo is 4.89 g, *not* ~15 g — that figure belongs to mid-tier missiles like Anaconda/Cobra at 14.94 g). `TIMissileTemplate.EstimateChanceToHit` applies a **×0.1 hit penalty when the target both out-accelerates AND out-dVs the munition** — so torpedo superiority is dV/tracking-endurance against capital targets, not agility; high-g alien light craft can evade both classes.

### Counter-PD interactions worth exploiting

- **Non-beam PD self-limits** ("saturation values"): simultaneous engagers per projectile are capped at **Missile 1 / Magnetic 2 / NavalGun 4** via the `enemiesTargetingMe` broadcast; **beam PD has no cap**. Alien PD is 100 % beam (46 PD lasers + 3 PD particle beams in the current opfor, zero ammo-based PD) — so alien PD never wastes shots, but also never runs dry.
- **PD-damaged leakers hit softer**: damaged projectiles/missiles deal damage proportional to remaining warhead mass (`effectiveMass_kg = warheadMass − massDamage`). Release-week "leaker math" overstates damage on this build.
- **Autoresolve treats PD as imperfect**: simulated combat scales projectile-PD kills by a 0.33 effectiveness factor (lerped toward ~0.08 as PD saturates) with an irreducible 2–10 % leak floor. Missile fleets autoresolve *better* than the real-time math would suggest; don't calibrate doctrine from autoresolve outcomes.
- **Mixed doctrine synthesis** (verified mechanics, community judgment): missiles as **PD-stressor adjunct** to a gun line is coherent — missiles strip PD attention (each costs a 2.4 s PD cooldown) while 656 kg siege-coiler slugs need ~21 PD hits each to stop. See [Capital Ship Doctrine](Capital%20Ship%20Doctrine.md).

### Escort-swarm / AM-torpedo variant (far-future)

`AntimatterTorpedoLauncher` exists: flatDamage 22.47 GJ ≈ **1.1 M damage points AOE**, only 2 kg warhead, 14.64 kps dV but 4.89 g — and as AOE it **ignores ECM**. The community tactic (cheap escorts out-accelerate your own torpedoes, fly ahead and soak PD) is mechanically plausible — torps are 4.89 g, escorts can exceed that — but formation-targeting behavior is unverified, and the economic dissent (≈1.5 k metals per throwaway escort) is fair. File under "endgame option to test", not doctrine.

## Evidence

**Tier 1 (code/templates, verified by adversarial review):**
- `MissileController.ApplyDamage` — single-hit destruction; `MissileController.MissileDamage` ctor — ECM negation roll (`random + TargetingBonus < ECMValue → Damage 0`), null-check on `attacker.ref_shipCarrier` (launcher must survive), AOE skip. *(high confidence)*
- `DefenseFireMode.SaturationValues` dict — Missile 1/Magnetic 2/NavalGun 4; beam PD uncapped. *(high)*
- `TILaserWeaponTemplate.json` `AlienPointDefenseLaserTurret` — 64 MJ, cooldown 2.4 s, 350 km; `TILaserWeaponTemplate.EffectiveRangeAgainstProjectiles` — attack-mode lasers engage missiles at range/3. *(high)*
- `TIMissileTemplate.json` — magazine column (Bay 16, Pod 4, nuclear 8/4, torpedoes 4–6, Krait 12); Athena 12.83 kps/4.89 g vs Copperhead 3.68 kps/18.27 g; `AntimatterTorpedoLauncher` flatDamage 2.247e10 MJ. *(high)*
- `TIUtilityModuleTemplate.json` Magazine `specialModuleValue 0.5`; AlienECM 0.6; TargetingComputer3 0.5. *(high)*
- `SalvoFireMode` ctor — `_totalSalvo = FullAmmoCount_Max/4 → FireMode.Idle`; `FocusFireMode.AcquireTarget` — primaryTarget only. *(high)*
- `TISpaceCombatState.SimulateCombat` (~line 2248) — autoresolve PD effectiveness 0.33/leak floor. *(high)*
- `TISpaceCombatProjectileState.effectiveMass_kg` — damaged-warhead damage reduction. *(high)*
- Save-empiric (2032-05-09): alien PD census — 39/85 ships zero dedicated PD, 43 one, 3 two; all beam. AlienECM on 50/85. *(high, this save)*

**Verdict provenance (Phase 3 adversarial review):** wiki torpedo-volley doctrine MODIFIED (torpedo agility corrected); PD mechanics VERIFIED; magazine claims VERIFIED; "Athena ~15 g" REFUTED; all-missile-fleet anecdote (7 Monitors + 8 Escorts beats Brutal) UNVERIFIABLE but mechanics-consistent.

**REFUTED community myths (do not resurrect):**
- ~~"Torpedoes are more agile than missiles"~~ — torpedoes have *lower* acceleration; their edge is dV.
- ~~"Athena pulls ~15 g"~~ — Athena is 4.89 g.
- ~~"Stagger your launches to drain PD"~~ — PD has no ammo on the alien side; staggering feeds missiles into the cooldown grinder one at a time. Simultaneity is everything.

## Worked example — the reference campaign (Resistance, 2032-05 snapshot)

- At 2032-05 the player's missile tier is **Krait/Viper/Copperhead bays — NO torpedoes researched**, TC1–3 researched, Magazine module researched, `Project_AlienECM` finished (the player's ECM works against aliens). The AM-torpedo variant is not actionable this decade.
- The current opfor (85 alien ships) fields **57 IridescentStar torpedo bays + 20 mag weapons** against the player — the player's own PD composition matters as much as the player's offense; see [Weapon Doctrine vs the Hydra](Weapon%20Doctrine%20vs%20the%20Hydra.md) § PD matrix.
- With 39/85 alien ships carrying zero dedicated PD, target selection for missile salvos should prioritize PD-less ships first (they die to small salvos), saving super-salvos for the 1–2-PD ships.

## Sources

- https://wiki.hoodedhorse.com/Terra_Invicta/Fleets · https://wiki.hoodedhorse.com/Terra_Invicta/Spaceships
- https://www.reddit.com/r/TerraInvicta/comments/1qo6kxl/the_case_for_lategame_missiles_sponsored_by/
- https://steamcommunity.com/sharedfiles/filedetails/?id=3624583882 and Steam discussion threads
- Decompile: https://github.com/Armandox33/Terra-Invicta-AI-Assistant
- Local templates build 22085164 + save-file empirics (2032-05-09 save)
