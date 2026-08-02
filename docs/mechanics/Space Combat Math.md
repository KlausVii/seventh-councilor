---
title: Space Combat Math
game_version: 1.0.32 decompile (build 22085164; decompile repo brackets 1.0.30–1.0.33); lessons re-verified through 1.0.38+
---

# Space Combat Math

Verified combat formulas and constants from the Phase-3 adversarial review (2026-06, 115 claims checked against decompiled source + build templates + save empirics). Campaign-independent rules first; current-campaign numbers appear only as labeled examples from the reference campaign (Normal difficulty, alienProgressionSpeed 2.0, in-game 2032-05).

> **Evidence caveat (applies to every citation below):** decompiled-source evidence is from a repo vintage bracketed **1.0.30–1.0.33** (sole commit dated 2025-06-12); template evidence is from the installed build's own JSON (build 22085164 = v1.0.32 public). Constants could drift in newer builds — **re-verify after any game patch** (templates via `sync_game_data.py`, code via the decompile repo if updated). Citation tags: `[code]` decompiled C#, `[tpl]` template JSON, `[save]` save-file empiric, `[calc]` phase-3 computed from cited inputs.

## 1. Damage fundamentals

- **1 damage point = 20 MJ.** All weapon energies convert via `points = MJ / 20` (`TIShipWeaponTemplate.cs:317-331` `[code]`, high confidence).
- Part hit points: every ship part has `3 × internalSize` hp **except lasers**: human ship lasers hp 1, alien lasers hp 2 (`TILaserWeaponTemplate.json`, 66 human / 22 alien entries `[tpl]`). Lasers are the most fragile thing on any ship.
- Alien "instant repair" is a myth — aliens get a **1.5× crew-efficiency damage-control multiplier**, nothing more (`TISpaceShipState.DamageControl`: `IsAlienFaction ? 1.5f : 1f` `[code]`). **REFUTED: "aliens repair instantly."**

## 2. Armor mechanics by damage type

All in `TISpaceShipState.AbsorbAndApplyArmorDamage` `[code]` unless noted.

### 2.1 Non-laser (kinetic, missile warhead, particle heat-fraction): flat subtraction

`appliedDamage = damagePoints − armorValue`. Armor is a hard floor: a 36-pt round vs armor 40 does **zero**. Corollary: **"armor never counters kinetics" is overstated** — it hard-blocks any round below the armor value; it only becomes irrelevant against rounds far above it (siege-coiler class, 400+ pts).

### 2.2 Lasers: armor^1.5 × spot-area scaling

Effective armor vs a laser shot = `armor^1.5 × ArmorEffectivenessAtRange`, where `AE = spotArea_m² / 0.005` (`TILaserWeaponTemplate.ModifyArmorValueForLaserShot` `[code]`).

Spot diameter (m) = `range_km × 1000 × sqrt((1.22·λ·beamQuality)² + (2·jitter·mirrorDiameter)²) / mirrorDiameter` (`TILaserWeaponTemplate.SpotDiameterPrecise_m` `[code]`).

Consequences (all structural, campaign-independent):
- Spot **area** grows as range² and shrinks as mirrorDiameter⁻² → **aperture, not shot power, is the long-range laser stat**. A 960 cm mirror quarters effective enemy armor vs a 480 cm at equal range (`[calc]`: 480 cm UV Phaser penetrates armor 10 at 1000 km; 960 cm penetrates 25).
- Shorter wavelength (UV 270 nm < green 540 nm < IR) shrinks the spot the same way — quadratic with jitter in the diameter formula.
- **Armor 0 means 0^1.5 = 0**: the weakest laser kills a stripped facing.
- Bigger mounts are almost always superior: bigger mirror → smaller spot → lower effective armor, plus more shot power.
- e.g. in the reference campaign `[calc]`: a 240 cm Green cannon penetrates alien side armor (4–9) at 280–430 km and flanker noses under ~110 km, but alien line noses (40–79) are immune to it at any usable range — lasers kill flankers, kinetics/missiles kill line ships.

### 2.3 Particle beams: heat fraction + capped radiation

Only the **heatFraction** does conventional (flat-subtraction) damage: **0.6 for ion/particle weapons, 0.1 for e-beams, 0.0 for the Spinal Neutron Lance** (pure radiation — structurally cannot destroy a ship) (`TIParticleWeaponTemplate.json` `[tpl]`).

The xRay/baryon radiation fraction is attenuated by `min(0.0625, 0.5^(thickness_cm / halfValue_cm))` — **any unchipped armor caps radiation pass-through at 1/16** (`AbsorbAndApplyArmorDamage` ParticleBeam branch `[code]`). This is why particle weapons rate as anti-ship research waste: e.g. SpinalParticleLance ≈ 7.2 effective pts vs an armored facing `[calc]`.

### 2.4 Plasma: PD-immune armor-stripper, not a killer

- `flatChipping = 0.8`: **80% of bolt energy erodes armor, only 20% is direct damage** — and that 20% faces the full armor value (`TIPlasmaWeaponTemplate.json` `[tpl]`; `TIGunTypeWeaponTemplate.BaseDamageAtRange_MJ` = `KE × (1−flatChipping)` `[code]`).
- Chipping is divided by the armor **facing volume** (`ChipArmor` `[code]`) — big hulls (motherships) strip slowly.
- Bolts are `isPointDefenseTargetable: false` (never intercepted) and fast (30–42 kps) `[tpl]`.
- e.g. HeavyPlasmaCannonMk3 551 MJ → ~5.5 pts direct (blocked by any line nose) + ~22 pts chip per shot `[calc]`.
- **REFUTED: "plasma is the premier anti-armor primary weapon."** Verified role: supplementary stripper feeding the armor^1.5→0 laser mechanic. Railguns also chip (see 2.5) and can out-chip plasma at similar tiers.
- Mk3 plasma weapons cost only 0.02 exotics build-weight on this build (post-1.0.30 reduction; Mk1/Mk2 need none) `[tpl]`.

### 2.5b Armor stat → damage-channel map (which UI stat defends what)

Common trap (verified 2026-07-15): the designer's "points to halve X-ray/baryonic" stats do
**NOT** defend against lasers. Each damage channel reads different armor properties
(`AbsorbAndApplyArmorDamage` `[code]`):

| Incoming | Armor mechanic | Stats used |
|---|---|---|
| **Laser** | `points^1.5 × rangeFactor` subtraction | point count + `LaserResistance` specialty (Hybrid 0.75 = the UI "25% bonus", ONE effect) |
| **Kinetic** (rail/coil/missile warhead) | flat `armorValue` subtraction | point count + `KineticsResistance` specialty (Adamantane 0.75) |
| **Particle beam** (xRay+baryon fractions) | `min(0.0625, 0.5^(thickness/halfValue))` | **points-to-halve-X-ray** + **points-to-halve-baryonic** |
| **Nuclear / radiation** | X-ray halving | **points-to-halve-X-ray** |

- **"Points to halve"** = `halfValue_cm ÷ cm-per-point` (verified: Nanotube X-ray 19.9/7.86=2.53,
  baryonic 155.4/7.86=19.78; Hybrid 4.5/2.50=1.80, 11/2.50=4.40 — all match the UI). Lower =
  fewer points to halve that radiation type. **Only matters vs particle weapons + nukes.**
- **Per-point laser blocking is material-INDEPENDENT** (only the point count enters `points^1.5`);
  a material's only laser edge is its `LaserResistance` specialty. So vs a pure-laser threat
  (alien base STO, `AlienT3BaseDefenseLaser` 450nm), Hybrid = Nanotube's ^1.5 block + the 25%;
  the "~4× better" is per-TON (17 vs 45.9 t/pt), not per-point. **Point-equivalence of the 25%:**
  ×0.75 on damage → 1.333× on the immunity threshold → `1.333^(2/3)=1.211×` on POINTS, so
  **80 Nanotube = 66 Hybrid** and **80 Hybrid = 97 Nanotube-equiv** (the naive ÷1.25→64 is a
  ~3% approximation; the ^1.5 makes the true factor 1.211, not 1.25). See [Orbital Bombardment](Orbital%20Bombardment.md) §8.
- **Hybrid is the best general anti-Hydra armor:** +25% in the laser channel AND far better
  halving vs the aliens' particle cannons (baryonic 4.40 vs Nanotube 19.78 pts).
- ⚠ **But "Adamantane is wrong vs beams" was WRONG (corrected 2026-07-30).** A POINT is a
  material-specific thickness (`cm/pt = xRayHalfValue_cm / XRayResistance`: Nanotube 7.866 ·
  Adamantane 3.734 · Hybrid 2.500), so per ton and per hull CAP the point counts differ hugely —
  and since block is `points^1.5` with the material entering only as `LaserResistance`, **cheap
  points beat resistance**. Adamantane buys 2.01× Nanotube's points per ton (2.86× the laser block)
  and raises the hull's max-point cap 2.11×: maxed Adamantane ≈ **3× maxed Nanotube**, ~55% of maxed
  Hybrid. Hybrid still wins outright; Adamantane is the right EXOTICS-FREE armor, not a
  kinetic-only pick. `armor_calc.py list` prints cm/pt, points/ton and cap×;
  [LESSONS-ships](../lessons/LESSONS-ships.md) S12 amendment has the per-hull table.

### 2.5 Kinetics: closing-velocity² scaling

Kinetic damage uses **relative impact speed**, so damage scales with (closing velocity)² (`ProjectileDamageSource` uses impact velocity `[code]`). Burning *toward* the enemy is a damage multiplier.

- e.g. RailCannonMk3: 1102 MJ KE → 35.8 pts direct + ~19 pts chip static; at **+5 kps closing it hits ~113 pts** and penetrates every alien nose in the 2032-05 save `[calc]`.
- Guns also split direct/chip via their own `flatChipping` (`TIGunTypeWeaponTemplate` `[code]`).
- Coilguns strictly beat railguns per mount at equal tier: HeavyCoilCannonMk3 ~617 MJ/s vs HeavyRailCannonMk3 ~133 MJ/s, higher muzzle velocity, salvo fire `[tpl]`.
- Siege coilers are the nose-breakers: HeavySiegeCoilerMk3 (ThreeNoseAngle mount, 656.25 kg warhead), SpinalSiegeCoilerMk3 (FourNose, 875 kg, 10,938 MJ ≈ 410+ pts) — out-damages any alien nose AND survives PD by mass (see §3) `[tpl]`.

### 2.6 Armor materials & geometry

- **Hybrid is the best general mainline armor vs the Hydra** (§2.5b): per-point laser blocking is material-independent, so Hybrid's LaserResistance 0.75 — the only material laser edge — plus the best per-mass laser index (90 kg/m² halving vs Adamantane 324) dominate against a beam-heavy opponent, and its points-to-halve beat Nanotube vs alien particle cannons (baryonic 4.40 vs 19.78). **Adamantane** (heatOfVaporization 59.5 MJ/kg at 1800 kg/m³, KineticsResistance 0.75 `[tpl]`) wins only the kinetic channel — the pick vs kinetic-heavy (human) threats or zero-exotics builds. The earlier "skip Exotic/Hybrid — terrible radiation halfValues (5.2/4.5 cm)" verdict compared raw cm rather than points-to-halve and is superseded (see [LESSONS-ships](../lessons/LESSONS-ships.md) S12); it survives only as a caveat scoped to particle-weapon threats.
- Armor depth caps scale with hull geometry: nose ≤ length × 0.036, lateral ≤ width × 0.12 (`TIShipHullTemplate.cs:120-146` `[code]`). Lateral area dominates mass → **nose-heavy armor splits are structurally favored** (60/5/5-style).
- Magazine secondary explosions are real and escalate: explosive parts add `Random(1,4)+Random(1,4)` bonus pts, **× Random(2,12) if HighlyExplosive (magazines)**, and leftover damage keeps propagating (`TISpaceShipState.ApplyDamageToPart:17039` `[code]`). Armor missile boats accordingly.

## 3. Point-defense economy

Core constants (`MissileController` / `ProjectileController` / `DefenseFireMode` `[code]`, high confidence):

| Rule | Value | Evidence |
|---|---|---|
| Missile vs PD | **one hit of any size kills any missile** | `MissileController.ApplyDamage` → `beenDestroyed=true` |
| Mag-slug erosion | **each PD damage point removes 10 kg of slug mass** | `ProjectileController.ApplyDamage` `massDamage_kg += amount×10` |
| Damaged leakers hit softer | damage ∝ remaining warhead mass | `effectiveMass_kg = warheadMass − massDamage` (`TISpaceCombatProjectileState`) |
| PD won't fire unless it can do | ≥ 0.15 pts vs missiles, ≥ 0.5 vs mag rounds | `TIGlobalConfig` `DP_DestroyMissile`/`DP_FireAtMagRound` |
| Saturation dedup (max simultaneous engagers per projectile) | **Missile 1 / Magnetic 2 / NavalGun 4; beam PD uncapped** | `DefenseFireMode.SaturationValues` |
| Charged-dispersion particle PD (Ion, E-beam) | **can ONLY engage missiles** — never slugs | `CanOnlyDefensivelyTargetMissiles` (dispersionModel==Charged) |
| Plasma bolts | **cannot be intercepted at all** | `isPointDefenseTargetable: false` `[tpl]` |

PD loadout doctrine that follows:
- **PD Ion = cheapest missile-killer**: 5 t / 1 crew / 3 s cooldown / 200 km (vs PD laser turret 20 t / 2 crew / 5 s); any hit kills a missile. Useless vs slugs/penetrator torpedoes' kinetic mass.
- **40 mm autocannon = the anti-kinetic specialist all game**: NavalGun class engages slugs; ~20 MJ ≈ 1 pt per 6 kg shell @2.6 kps → strips 10 kg slug mass each; 6-shot salvo / 4 s; 350 km; 2000-round magazine; its own shells are `isPointDefenseTargetable:false` so enemy PD can't thin them `[tpl]`. Keep at least one on any line ship.
- **PD lasers/phasers** are mid-tier generalists; damage vs small cross-sections collapses with range (damage scales by crossSection/spotArea). They scale with Laser Engine modules but **defense-only mounts get HALF the laser-engine bonus** (`GetBonusPowerForWeapon_MJ`: `!attackMode → ×0.5` `[code]`).
- **PD screens are ECM-proof**: ECM/bollix applies only against ship targets with an ECMValue; projectiles have none — on a dedicated PD screen, dropping the Targeting Computer for a heat sink is mechanically sound `[code]`.
- Kinetic-round PD survivability (vs the alien 64 MJ PD laser = 3.2 pts = 32 kg/hit): CoilCannonMk3 43.75 kg round ≈ 2 hits; HeavySiegeCoilerMk3 656.25 kg ≈ 21 hits; SpinalSiegeCoilerMk3 875 kg ≈ 28 hits `[calc]`. Only capital-grade rounds survive dense PD.
- **Autoresolve PD is NOT perfect**: simulated combat scales projectile-PD kill mass by **0.33 effectiveness** (lerped down to ~0.08 as PD saturates) and adds an irreducible **2–10% leak-through floor** (`TISpaceCombatState.SimulateCombat` ~line 2248 `[code]`). Autoresolve verdicts on missile fights differ from manual play.

## 4. Missiles & torpedoes

- **Magazine sizes** `[tpl]`: standard missile Bay **16**, Krait bay 12, Pod 4, nuclear missile bay 8 (nuclear pod 4), torpedo bay 6, nuclear torpedo bay 4. Prefer 16-round variants. **Magazine utility module = +50% ammo each** (specialModuleValue 0.5, 100 t; `FullAmmoCount = (1+multiplier) × magazine`).
- Missile bays use **zero ship energy** (`TIMissileTemplate.EnergyUsage_GJ` returns 0 `[code]`) — no weapon-heat interaction.
- **No in-combat reload**; resupply requires returning to a hab.
- **ECM negation roll** (`MissileController.MissileDamage` `[code]`): for non-AOE missiles, if `random + attackerTargetingBonus < targetECMValue` → damage 0. The TargetingBonus is added **only if the launching ship still exists** at impact. **AOE warheads skip the ECM check entirely.**
- **×0.1 hit-chance penalty** when the target BOTH out-accelerates AND out-dVs the munition (`TIMissileTemplate.EstimateChanceToHit` `[code]`) — high-g alien small craft can dodge missiles.
- **Torpedoes are dV/endurance weapons, not agility weapons**: torpedoes 4.89–9.14 g vs late missiles 14.9–18.3 g; e.g. Athena torpedo 12.83 kps dV @ 4.89 g vs Copperhead 3.68 kps @ 18.27 g `[tpl]`. **REFUTED: "Athena pulls ~15 g"** (that figure belongs to mid-tier missiles, Anaconda/Cobra 14.94 g).
- Antimatter torpedoes: AOE (ignores ECM), 2 kg warhead, 14.64 kps / 4.89 g, template flatDamage ~2.2e10 MJ — one-shots anything in radius `[tpl]`.

### Saturation doctrine (the only way missiles work vs PD)

PD kill rate is cooldown-bound (alien dedicated PD ≈ 1 missile / 2.4 s; alien dual-mode main lasers ≈ 1 / 12–18 s inside range/3). A **dedicated alien PD turret gets ~18–30 intercepts per terminal window** plus 2–5 per dual-mode laser `[calc]`. Therefore:
- **Sequential launches are eaten one-by-one. Fire simultaneous super-salvos** — vs alien warship-class targets in the 2032-05 era, ~30–50 missiles per target in one wave `[calc]`.
- Never let weapons auto-cycle salvos: Focus/Salvo fire on each weapon's own cooldown with no cross-ship synchronization — manual simultaneous release is the player's edge.
- Missiles double as PD-saturators for a gun line: they strip PD attention while heavy slugs (≈20+ PD hits each) walk in.

## 5. Fire modes & targeting

- Missile weapons get **only Focus and Salvo** fire modes, and both fire **exclusively at the ship's manually designated `primaryTarget`** — there is no offensive auto-fallback (`Weapon.cs` fire-mode assembly; `FocusFireMode.AcquireTarget` `[code]`). Per-target salvo allocation is manual by design.
- **Salvo mode auto-idles after firing `FullAmmoCount/4`** (`SalvoFireMode` ctor `[code]`) — re-trigger it deliberately.
- Beam/gun lasers refuse to fire at ships unless expected post-armor damage ≥ **1.0 pt** (≥ **0.25** if the facing is stripped or >20% chipped) (`TIAttackFireMode.GetMinimumExpectedDamageToFire` `[code]`). Anything that buffs laser power (Laser Engine +10 MJ, Advanced +20 MJ per module, summed across all functional modules) extends effective range, since damage feeds `RangeToDoDamage`.
- Dual-mode (attack-capable) lasers engage projectiles only inside **range/3** while in attack mode (`EffectiveRangeAgainstProjectiles` `[code]`).

## 6. Battle cap & the cheap-hull filler mechanic

- Default in-combat cap = **30 ships total** (player profile setting `TIPlayerProfileManager.maxShipsInCombat = 30`; engine max `TIGlobalConfig.maxShipsAllowedInCombat = 90`) `[code]`. **REFUTED: "~40 (~20/side)."**
- Per-side allocation = `clamp(yourShips/totalShips, 1/3, 2/3) × cap` (`SpaceCombatManager.cs:485` `[code]`) → 10–20 per side at default.
- **Filler doctrine**: bringing a mass of cheap hulls (corvettes = 1 MC) pushes your share to the 2/3 ceiling (20) and starves the enemy side to 10 — your capitals always outnumber inside the instance. Verified mechanism; "re-roll until the AI picks a bad tactic" is unverified.
- Capital "efficiency": hardpoints/MC actually peaks at Dreadnought (2.75) and Battleship (2.67); Titan = Monitor (2.0). Capitals win on **firepower per battle-slot inside the 30-cap**, not per MC `[tpl]`.

## 7. Targeting Computers vs ECM (mandatory math)

- Alien standard fit: **AlienTargetingComputer 0.5 on every combat ship; AlienECM 0.6 on ~60%** (save-empiric example, 2032-05: TC on 80/80 combat ships, ECM on 50/85 `[save]`; values from `TIUtilityModuleTemplate.json` `[tpl]`).
- Your missiles vs AlienECM 0.6: **no TC → 60% of hits negated; TC3 (0.5) → 10%**. A Targeting Computer is mathematically mandatory on every missile/beam combatant.
- Beam weapons suffer **bollix lockouts** vs ECM: up to `ECM × rangeFraction` probability per target acquisition, costing **5 s per point missed (beams), 10 s (missiles)** (`ECM_SecondsBollixedPerPointMissed` `[code]`).
- **Your ECM does nothing against aliens until `Project_AlienECM`** (5,000 RP) grants `HumanECMAgainstAliens` (`TISpaceShipState.ECMValue` gate `[code]`). After that, human ECM 0.6-class modules work — but aliens partially learn around it: **+0.02 attack bonus per prior ECM defeat** (`attackBonusPerTargetECMDefeat` `[code]`).

## 8. Alien hull table (template — campaign-independent)

`TIShipHullTemplate.json` `[tpl]`, high confidence. SI = structuralIntegrity (also drives hate-per-kill: hate = **0.4 × SI ±20%**, `factionHateSIFactorPerShipDestroyed = 0.4f` `[code]` — **REFUTED: "hate += full SI"** and the wiki's 0.35; zero hate when the victim was attacking you).

| Alien hull | SI | Nose hardpoints | Hull hardpoints |
|---|---|---|---|
| Gunship | 6 | 1 | — |
| Escort | 10 | — | — |
| Corvette | 10 | 1 | — |
| Frigate | 20 | 1 | — |
| Monitor | 22 | 1 | — |
| Destroyer | 24 | 2 | — |
| Cruiser | 36 | — | — |
| Battlecruiser | 48 | 3 | — |
| Lancer | 52 | 6 | — |
| Battleship | 60 | — | — |
| Dreadnought | 72 | 4 | — |
| Titan | 90 | 6 | 8 |
| AssaultCarrier | 90 | — | — |
| Mothership | 512 | 4 | 16 |

(— = not captured in the verified evidence; pull from templates when needed.)

## 9. Alien weapon taxonomy (templates)

| Weapon | Mount | Range | Notes |
|---|---|---|---|
| 256 cm laser cannon | OneNose | 800 km | violet era shotPower band 128–448 MJ across classes |
| 512 cm laser cannon | TwoNose | 900 km | |
| 768 cm laser cannon | ThreeNose | 1000 km | |
| 1024 cm laser cannon | FourNose | 1000 km | late: Xaser variants |
| PD laser turret | turret | 350 km | **64 MJ = 3.2 pts/shot, 2.4 s cooldown** |
| Iridescent Star torpedo | bay | — | 256 kg penetrator, 14.2 kps dV, 11.5 g |

Alien beams: beamQuality 1.05–1.1, jitter 1.3e-8–2.6e-8 `[tpl]`.

**Armor-to-block (at 400 km, raw template math `[calc]` vs wiki):** 512 cm violet → 21.6 (wiki 25); 768 orange → ~28 (wiki 30); 768 violet → 44.5 (wiki 50); 1024 violet → 69.3 (wiki 80); 1024 Xaser → ~120 (wiki 150). The wiki numbers bake in ~10–25% margin for alien damage bonuses — **use wiki numbers when armoring**, raw numbers when computing your own laser penetration.

- e.g. the reference campaign, 2032-05 `[save]`: alien fleet 96% violet-laser era, 4 orange weapons, zero Xasers; 85 ships: 57 torpedo bays, 49×64 cm batteries, 46×256 cm cannons, 46 PD turrets; armor nose 8–79 (median ~40), sides 1–9, tail 3–37; **39/85 ships have ZERO dedicated PD** — missile saturation has targets.

## 10. Known scoring bugs on 1.0.32 — distrust in-game numbers

- **Laser AI-valuation BUG** `[code]`: `TILaserWeaponTemplate.EstimateDPS` samples the SAME expectedRange in all four weighted terms (base class correctly samples 200/500/800), and `EstimatedDamageAtRange_MJ` divides by **unclamped** ArmorEffectivenessAtRange → →0 at short range → unbounded scores. **Do not trust laser combat scores / AI valuations on this build.**
- Kinetic estimation is also off: `TIProjectileWeaponTemplate.EstimateChanceToHit` mixes units (accel_g/0.3 ÷ impactVel/9) and `EstimateDPS` double-penalizes ammo (×`cooldown×magazine/salvo/480`) — fixed in later betas. Compute real damage from §2 formulas instead.

## 11. Misconception graveyard (do not resurrect)

| Myth | Status | Truth |
|---|---|---|
| Plasma = premier anti-armor primary | **REFUTED** | armor-stripper support role; 20% direct damage faces full armor (§2.4) |
| "Athena torpedo pulls ~15 g" | **REFUTED** | 4.89 g; ~15 g is mid-tier missiles (§4) |
| 960 cm lasers are Titan-only | **REFUTED** | FourNose mounts fit ANY 4-nose hull — Lancer and Titan `[tpl]` |
| Default battle cap ~40 | **REFUTED** | 30 total, 10–20/side (§6) |
| Alien hate += full hull SI per kill | **REFUTED** | 0.4 × SI ±20%, with self-defense exemptions (§8) |
| AoE/nuked ship kills yield no salvage | **REFUTED** | no warheadClass check anywhere in the 1.0.32 salvage path `[code]`; the true adjacent rule: nuke/AM **bombardment of a hab** destroys it with 0% recovery |
| Armor never counters kinetics | overstated | flat subtraction hard-blocks sub-armor rounds (§2.1) |
| Aliens repair instantly | **REFUTED** | 1.5× damage-control multiplier (§1) |
| Alien PD is perfect in autoresolve | **REFUTED** | 0.33 effectiveness + 2–10% leak floor (§3) |

See also: [Drives Refits and Logistics](Drives%20Refits%20and%20Logistics.md) (combat thrust, refits, reaching the fight), the lessons library (`docs/lessons/LESSONS-ships.md` — warship FoM and optimizer lessons).
