---
title: Weapon Doctrine vs the Hydra
game_version: 1.0.32 (build 22085164)
---

# Weapon Doctrine vs the Hydra

> **Evidence vintage caveat (applies to all code citations in this note):** decompiled-source evidence is from a repo bracketed to builds 1.0.30–1.0.33 (commit 2025-06-12). Constants could drift in newer builds — re-verify after any game patch (templates via `sync_game_data.py`; code via the repo if updated).

## Verdict (expanded)

### The core armor math (everything follows from this)

`TISpaceShipState.AbsorbAndApplyArmorDamage`; 1 damage point = 20 MJ:

| Damage type | Armor interaction |
|---|---|
| **Kinetic/thermal (non-laser)** | **Flat subtraction** of armorValue from damage points. Armor 40 hard-blocks a 36-pt round; a 113-pt round goes through with 73 left. |
| **Laser** | Effective armor = **armor^1.5 × ArmorEffectivenessAtRange**, where AE = spotArea_m²/0.005 and spot diameter = range×1000×√((1.22·λ·beamQuality)² + (2·jitter·mirrorDiam)²)/mirrorDiam. **Aperture and wavelength enter quadratically** — a 960 cm mirror quarters effective enemy armor vs a 480 cm at equal range. 0 armor = effective 0 → the weakest laser kills a stripped facing. |
| **Particle beam** | `heatFraction` (0.6 ion/particle, 0.1 e-beam) hits as normal damage; the xRay/baryon radiation fraction attenuates by **min(0.0625, 0.5^(thickness_cm/halfValue_cm))** — ANY unchipped armor caps radiation at 6.25 % pass-through. |
| **Plasma** | `flatChipping 0.8`: 80 % of bolt energy *chips armor*, only 20 % is direct damage vs FULL armor value. Chipping is divided by armor-facing **volume** — big ships strip slowly. |

### Class assignments that fall out of the math

- **Kinetics for line ships.** Flat subtraction + **kinetic damage scales with closing-velocity²** (`ProjectileDamageSource` uses relative impact speed) — burn TOWARD targets. RailCannonMk3: 35.8 pts static → **~113 pts at +5 kps closing**, penetrating every alien nose in the 2032 save. Coilguns strictly supersede railguns per mount (HeavyCoilCannonMk3 ~617 MJ/s vs HeavyRail Mk3 ~133 MJ/s, higher muzzle velocity, salvo fire); SpinalSiegeCoilerMk3 ≈410+ pts — kills any alien nose. "Armor never counters kinetics" is overstated early: 40+ noses hard-block mid-tier railgun rounds at zero closing speed; it becomes true at siege-coiler class and high closing velocities.
- **Lasers for flankers.** Bigger mounts are structurally superior (mirror D⁻² spot area + more shot power). Alien SIDE armor runs 1–9, noses 8–79 (median ~40): green 240 cm penetrates sides at 280–430 km and flanker noses under ~110 km, but line noses are immune to green-tier lasers outside knife range. Endgame: 960 cm UV Phaser penetrates 25 armor at its full 1000 km, ~84 at 400 km — kills flankers at max range while 100+ noses still block it.
- **Plasma = supplementary armor-stripper** (PD-immune `isPointDefenseTargetable:false`, fast 30–42 kps bolts, free ammo) — **"premier anti-armor primary weapon" is REFUTED**: HeavyPlasmaCannonMk3 does ~5.5 direct pts (blocked by any line nose) + ~22 chip pts per 40 s, and chipping divides by facing volume.
- **Particle weapons: skip as weapons** (radiation floor-capped; SpinalParticleLance ≈7.2 effective pts vs armor; Spinal Neutron Lance heatFraction 0 cannot ship-kill). Note "alien instant repair" is actually a 1.5× crew damage-control multiplier, not instant.

### PD composition matrix

| PD type | Strengths | Hard limits |
|---|---|---|
| **40 mm autocannon** (NavalGun) | The anti-slug specialist all game: each ~1-pt shell strips 10 kg slug mass, 6-shot salvo/4 s, 350 km, 2000 rounds, and its own shells are NOT PD-targetable | Ammo-limited; saturation cap 4 engagers/projectile |
| **PD Ion / E-beam** (Charged) | Cheapest missile-killer: 5 t/1 crew/3 s cooldown (vs 20 t/2 crew/5 s laser turret); any hit kills a missile | **Physically cannot engage kinetic slugs** (`CanOnlyDefensivelyTargetMissiles`); 200 km |
| **PD laser** | Generalist; scales with Laser Engine modules at **half rate** (defense-only mounts get ×0.5 bonus power); no engagement cap | Damage vs small cross-sections collapses with range |

PD screens are **ECM-proof** — ECM negation applies only against ship targets with an ECMValue; projectiles have none, so a dedicated screen ship can drop the TC for a heat sink. Beam thresholds: lasers/particles won't fire at ships unless expected post-armor damage ≥ 1 pt (0.25 if facing stripped or >20 % chipped), ≥0.15 vs missiles, ≥0.5 vs mag rounds — anything buffing laser power (LaserEngine +10 MJ, Advanced +20 MJ, stacking) extends both attack and PD range.

### Targeting Computers are mandatory (quantified)

All alien combat ships carry AlienTargetingComputer (0.5); ~59 % carry AlienECM (0.6). Without a TC: your missiles are 60 % negated and your beams suffer bollix lockouts up to 0.6×(range fraction) per target acquisition (5 s per point missed; 10 s for missiles). With TC3 (0.5): 10 % negation. Inverse: **your ECM works against aliens ONLY with `Project_AlienECM`** (5,000 RP, `HumanECMAgainstAliens` effect); aliens partially learn around it (+0.02 attack bonus per prior ECM defeat).

### Armor doctrine

- **Nose-heavy.** Depth caps: nose ≤ length×0.036, lateral ≤ width×0.12; lateral *area* dominates mass — side armor is expensive. Sides only need to beat flanker lasers (historically ≤25 alien side-laser-relevant armor).
- **Breakpoint caveat:** the wiki's armor-vs-alien-laser breakpoints run **~10–25 % above raw template math** (raw: 21.6 blocks 512 cm violet at 400 km vs wiki 25; 44.5 vs wiki 50 for 768 violet; 69.3 vs wiki 80 for 1024 violet; ~120 vs wiki 150 for 1024 Xaser) — the wiki appears to bake in margin for alien officer/utility damage bonuses. Use wiki numbers as the safe spec, raw numbers as the floor.
- **Armor tech path:** Nanotube → **Hybrid** — the best general anti-Hydra armor (superseded verdict, 2033 re-verification). The Hydra is beam-heavy and per-point laser blocking is material-independent, so Hybrid's LaserResistance 0.75 (the only material laser edge) plus the best per-mass laser index (90 kg/m² vs Adamantane 324) dominate. **Adamantane** (heatOfVaporization 59.5 MJ/kg @1800 kg/m³, KineticsResistance 0.75) wins only the kinetic channel — the pick vs kinetic-heavy human threats or zero-exotics builds. The old "skip Exotic/Hybrid (halfValues 5.2/4.5 cm — bad vs radiation)" read compared raw cm rather than points-to-halve and applies only vs particle-weapon threats. See [Space Combat Math](../mechanics/Space%20Combat%20Math.md) §2.5b and [LESSONS-ships](../lessons/LESSONS-ships.md) S12.
- **Armor your magazine ships:** explosive parts add 2–6 bonus damage points on part hits, ×2–12 for highly-explosive parts (magazines), with leftover damage propagating (`ShipSecondaryExplosion`).

### Alien hardware taxonomy (template-verified)

Laser mounts: 256 cm = OneNose/800 km · 512 = TwoNose/900 · 768 = ThreeNose/1000 · 1024 = FourNose/1000. Hull noses: Gunship/Corvette/Frigate/Monitor 1 · Destroyer 2 · BC 3 · Dreadnought 4 · Lancer/Titan 6 · Mothership 4. Alien PD laser: 64 MJ/shot = 3.2 pts = 32 kg slug erosion, 2.4 s cooldown, 350 km.

### Known-bad numbers (do not trust)

- The game's own **laser AI-valuation code is buggy on this build**: `EstimateDPS` samples one range in all four weighted terms and `EstimatedDamageAtRange_MJ` divides by unclamped ArmorEffectivenessAtRange (→0 at short range → unbounded scores). Never rank lasers by in-game/AI combat scores.
- Kinetic estimation has mixed-units math + a double-counted ammo penalty (fixed only in ≥1.0.34 beta) — kinetic combat-value scores also differ from reality.
- "Aliens adaptively counter-design vs your weapon mix" — UNVERIFIABLE (no hook found in `DesignAlienShip`); experiment: two saves diverging only in player weapon mix, compare later alien PD counts.
- Flanker stand-off behavior ("rarely close under 300 km") — tactical-AI claim, unverified; only the weapon/armor math behind it is verified.

## Evidence

**Tier 1 (code/templates, verified):** `TISpaceShipState.AbsorbAndApplyArmorDamage` (all four branches); `TILaserWeaponTemplate.ModifyArmorValueForLaserShot` + `SpotDiameterPrecise_m`; `TIPlasmaWeaponTemplate.json` (flatChipping 0.8, isPointDefenseTargetable false); `TIMagneticGunTemplate.json` KE/warhead values; `TIParticleWeaponTemplate` Charged dispersion → missiles-only PD; `TIGunTemplate.json` 40mm; `TISpaceShipState.GetBonusPowerForWeapon_MJ` (×0.5 defense); `Weapon.TargetChance` + bollix constants (5 s/10 s, +0.02/defeat); `TISpaceShipState.ECMValue` HumanECMAgainstAliens gate; `TIShipArmorTemplate.json`; `TIShipHullTemplate.cs:120–146` armor-depth caps; `TISpaceShipState.ApplyDamageToPart:17039` magazine explosions; `TIAttackFireMode.GetMinimumExpectedDamageToFire`; `TIGlobalConfig` DP_DestroyMissile 0.15/DP_FireAtMagRound 0.5; save-empiric alien census (weapons/armor/PD/ECM). *(high)*

**Verdict provenance:** kinetics-for-line/lasers-for-flankers VERIFIED; PD matrix VERIFIED; armor doctrine MODIFIED (kinetics overstatement corrected, particle immunity stronger than claimed); alien taxonomy VERIFIED with breakpoints MODIFIED (~10–25 % margin); plasma-as-primary REFUTED; 960cm meta VERIFIED but mount claim corrected (FourNose fits Lancer too — see [Capital Ship Doctrine](Capital%20Ship%20Doctrine.md)).

**REFUTED myths:** ~~"Plasma is the premier anti-armor primary"~~ (stripper only) · ~~"Armor never counters kinetics"~~ (false until siege-coiler class) · ~~"Particle weapons melt through armor"~~ (6.25 % cap) · ~~"Aliens repair instantly"~~ (1.5× damage control).

## Worked example — the reference campaign (Resistance, 2032-05 snapshot)

- The player's tier at 2032-05: Green 540 nm lasers (60 cm battery, 240 cm cannon, regular+Arc), Railgun/RailCannon Mk1–3 (NO coilguns), Krait/Viper/Copperhead missiles, ParticleBeam/Lance/Ion researched (PD Ion available), **zero plasma**, Composite/Component/Nanotube armor, TC1–3, Magazine, LaserEngine, 40 mm, Project_AlienECM, VitalPointShellTargeting.
- Current opfor is **96 % violet-laser era** (no Xasers fielded): nose 8–79/median ~40, sides 1–9. The player's 240 cm green kills flankers and strips sides; RailCannonMk3 with closing velocity kills line ships. **Keep one 40 mm per ship**: 57 alien torpedo bays + 20 mag weapons are pointed at the player.
- Coilgun chain (Coilguns 30k → HTS 40k → Ultracaps 40k → CoilCannon Mk1/2/3 30k = 140k) is the next kinetic buy; HTS double-counts toward fusion magnetics ([Converting a Research Lead](Converting%20a%20Research%20Lead.md)).

## Sources

- https://wiki.hoodedhorse.com/Terra_Invicta/Help:Gameplay_Guides/Armor_Guide · …/Combat_Doctrines_for_various_stages_of_the_game
- https://www.reddit.com/r/TerraInvicta/comments/1qm5g9v/weapon_to_fight_aliens_in_2033s/; Steam guide threads
- Decompile: https://github.com/Armandox33/Terra-Invicta-AI-Assistant; local templates build 22085164; save-empirics 2032-05-09
- Related: [Missile Swarm Doctrine](Missile%20Swarm%20Doctrine.md) · [Capital Ship Doctrine](Capital%20Ship%20Doctrine.md) · [Space Combat Math](../mechanics/Space%20Combat%20Math.md)
