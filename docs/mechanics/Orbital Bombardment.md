---
title: Orbital Bombardment
game_version: 1.0.32 decompile (build 22085164; decompile repo brackets 1.0.30–1.0.33); lessons re-verified through 1.0.38+
---

# Orbital Bombardment vs Defended Bases

Code-verified after the failed 2033-08-19 bombardment of a T3 alien fortress base (3 ships lost, zero
damage dealt, every projectile "intercepted by surface defenses"). Explains the interception
formula, altitude bands, STO counterfire, and what actually kills a battlestation base.
Sibling of [Space Combat Math](Space%20Combat%20Math.md).

## 1. Interception is a POOLED RATIO, not per-shot PD

Defense pool = every **powered** combat module on the hab (`ActiveCombatModules()` =
functional && powered && spaceCombatValue>0 — Battlestations AND Citadels;
`TIHabState.cs:367–372`, `TIHabModuleState.cs:182–188`).

```
num  (defense) = Σ_modules( hab.tier × defWeapon.EstimateDPS(alt) )
                 × 60 (habDefensesPDDPSMultiplier, TIGlobalConfig.cs:1581)
                 × (1 + (altitude_km − 200)/200)          (TISpaceFleetState.cs:3033)
num2 (attack)  = Σ gun-type bombard weapons( ½·v_impact²·warheadMass / cooldown )
                 + count(missile-type bombard weapons)     (TISpaceFleetState.cs:3008–3032)
projectileVPDRatio = num / num2                            (:3045)
```

Each projectile independently rolls `Random.value < ratio` → intercepted
(`TISpaceShipState.cs:3228–3232`). **If num/num2 ≥ 1, interception is 100% — infinite
volume changes nothing.** Volume only helps by raising `num2` above `num` (kinetic energy
throughput is the currency: warhead mass × impact velocity² ÷ cooldown; torpedoes add ~1
each — nearly nothing).

## 2. Altitude bands (Low 200 / Med 400 / High 600 km — TIGlobalConfig.cs:2409–2415)

Interception multiplier: **Low ×1.0 · Med ×2.0 · High ×3.0.** Kinetic impact velocity
(damage AND num2) *rises* slightly with altitude via gravitational fall, but the defense
multiplier dominates. **Bombard from LOW orbit, always.** (Reference-campaign failure, 2033-08: HIGH orbit =
tripled interception. The player's hypothesis was correct — but insufficient alone.)

## 3. Weapon classes vs bases

- **Kinetics (gun-type):** the num2 currency. Heavy + fast + short cooldown.
- **Plain Nuclear / Antimatter missiles+torpedoes:** intercepted by the SAME roll (they're
  `isPointDefenseTargetable`). A leaker that lands **instakills the hab** (`DestroyHab`,
  `TISpaceShipState.cs:3238–3242` — the 0%-loot path, see [Economy Markets and Loot](Economy%20Markets%20and%20Loot.md)) —
  ⚠ do NOT land plain nukes on a base you intend to capture.
- **ShapedNuclear** (`TISpaceShipState.cs:3228, 3272–3275`): **20% interception bypass
  (`Random.value > 0.2` term) + ignores module armor** on hit, and kills modules rather
  than the hab. THE base-cracking warhead class. Template census (`TIMissileTemplate.json`):
  **Olympus** — ⚠ CORRECTED 2026-07-15 (player report: "not yet available"): prereqs are AMWD +
  MilitarizationofSpace + **FissionPulseDrives (global, 12.5k in-game — must be slotted
  first)** + Project_SCFR VIII, and then `factionAvailableChance: 50` — a **one-time 50%
  gate that can come up NEVER**, then rolls ≤50%/mo (LESSONS-research R11: never gate a plan on
  this). Acheron/Sidewinder require Project_Olympus itself + Heavy Pulsed Propulsion —
  **Olympus is the sole gateway to the entire ShapedNuclear ladder.**
  Hades/Python/Nemesis/Cerebrus are all plain Nuclear.
  **Warhead data (`TIMissileTemplate.json`, raw `flatDamage_MJ` = warhead energy):**
  Python 250 kg / 188 TJ (~45 kt), Hades 450 kg / 2,450 TJ (~585 kt), Nemesis 900 kg /
  4,520 TJ (~1.1 Mt) — all plain Nuclear (isotropic; energy smears over 4πr², armor soaks
  it). **Olympus 800 kg / 4,185 TJ (~1 Mt) but `shapedChargeAngle: 0.2`** — a ~0.13-sr
  cone concentrates the SAME energy ~100× in intensity (J/m²) in one direction → overwhelms
  the per-area armor budget = the "ignores module armor" rule. Physics: shaped charge /
  Casaba-Howitzer (nuclear Munroe effect). **Olympus has LESS raw energy than Nemesis** →
  Nemesis/Hades win vs ships (raw yield, little armor), Olympus wins vs bases (concentration
  beats armor). The 20% PD bypass = standoff detonation of the directed jet (game constant;
  standoff is the physical read).
- **Beams: only LASERS bombard — particle weapons do NOTHING.** A weapon's bombardment
  contribution is its `bombardmentValue` (code: `BombardmentValue` sums `GetLocalBombardment
  Value` per weapon, `TISpaceShipState.cs:3585–3607`). Lasers have it (720cm GreenArc **2.8**,
  240cm 1.2, 60cm 0.4); **ALL particle lances = `bombardmentValue 0`** (Light/Particle/Heavy/
  Spinal/**SpinalNeutronLance** — verified 2026-07-15), so even the 560 MJ Spinal Neutron
  Lance does ZERO base damage regardless of shot power. Physically coherent: particle beams
  are the 6.25%-radiation crew/system killers ([Space Combat Math](Space%20Combat%20Math.md)), not structure
  demolishers. Corollary: a pure-particle ship has BombardmentValue 0 → STO ignores it, but
  it also can't damage the base — useless for siege either way.
- Laser bombardment is still gated by armor: module `AntiBombardmentArmor` applies as
  armor^1.5 × range-scaled effectiveness (grows with altitude; `TILaserWeaponTemplate.cs:
  52–66`), and **powered COMBAT modules carry ×8 anti-bombardment armor** (×4 unpowered;
  `TIHabModuleState.cs:873–876`) — which is why lasers are absorbed by battlestations but
  KILL the non-combat reactor farms (no ×8). See §8.

## 4. STO counterfire (why the fleet got shredded)

- Fires only after your first ranging strike (`firstBombardmentStrike`,
  `TISpaceFleetState.cs:2889–2895`), then EVERY powered combat module fires per cycle,
  each a 2-pulse loop (`TIHabState.cs:4425–4432`, `TIHabModuleState.cs:1455–1512`).
- **DOGPILE — the decisive mechanic (2033-08-31 probe, code-confirmed).** `SelectSTOTarget`
  = `list.MaxBy(BombardmentValue)` returns a SINGLE ship, and EVERY powered combat module
  calls it independently → all modules pick the **same** highest-bombardment-value ship.
  9 battlestations × 2 pulses = **~18 STO beams/cycle ALL onto one ship**
  (`TIHabModuleState.cs:1410–1425, 1436, 1455–1512`). A lone bomber IS that ship → eats
  100%. A formation does NOT split the fire — it still lands entirely on the single
  highest-value hull; the others are untouched but your "tank" still dies.
- **Facing: nose-ON, code-confirmed** (`GetDesiredRotation`, `TISpaceShipState.cs:2015–2043`:
  `LookRotation(bombardmentTarget − ship)` points the nose at the base). ⚠ CORRECTS the
  earlier "flank/geometric, uncontrolled" guess — the nose armor faces the base. Death is
  by **ablation under volume**: ~18 × 768 MJ beams strip even armor-80 nose in ~one cycle
  (armor degrades per hit; penetration climbs 9→38 across the cycle), and slow nose cannons
  (720cm) never cycle before the ship dies.
- To-hit = `1 + weapon targeting − target ECM` (`:1447`): ECM reduces it but 18 shots ×
  even 0.4 = ~7 hits/cycle = dead. ECM alone cannot save a dogpiled ship.
- Beam damage falls with altitude — but not enough to justify High orbit's ×3 interception.

## 5. Module attrition & the power snowball

Hits land on a RANDOM `OkayModules()` pick — **you cannot snipe reactors or specific
battlestations** (`TISpaceShipState.cs:3245–3250`; core excluded while >1 module remains).
Each destroyed/unpowered combat module drops out of num AND STO fire; killing reactors
de-powers modules (halving their bombardment armor and silencing them) — but only as a
statistical consequence of sustained penetration, not a targetable opener.

## 6. The AI's committal rule (mirror it)

`FactionGoal_AttackWithFleet.GetDesiredBombardmentValue` = `max(20, core
AntiBombardmentArmor, hab.SpaceCombatValue) × n`, and the AI commits only at **fleet
bombardment value ≥ 1.5×** that (`FactionGoal_AttackWithFleet.cs:628–635`,
`AIEvaluators.cs:5254–5255`), scaling up after failed attacks. Below the ratio the engine
guarantees zero result — which is exactly what happened on 2033-08-19.

## 7. Doctrine (strictly code-derived)

1. LOW orbit only.
2. **Primary owned-tech path: target the REACTOR FARMS with 720cm+ beams to trigger the
   power cascade (§8)** — reactor farms are soft (no ×8 armor), only beams reach them, and
   killing them de-powers the battlestations. ShapedNuclear (Olympus) is the low-micro
   alternative if the lottery lands. Kinetics/plain-nukes are wasted vs a powered base.
3. Bombers: ECM3 mandatory; nose armor faces the base (nose-on, §4) but **the dogpile
   ablates even N80 in one cycle if too few hulls share the field** — a single or few-ship
   bombardment of a 9-battlestation base is suicide (§8).
4. Field ≥1.5× the base's SCV in bombardment value before committing — AND enough hulls that
   no single tank absorbs a fatal share of ~18 beams/cycle. Against 9 battlestations at
   fission tech this is effectively unmeetable; wait for ShapedNuclear or a fusion fleet (§8).
5. Marine assault resolves separately — **empirically confirmed 2033-09-01 (in-game
   tooltip, the same fortress base)**: Defending Force Strength 395 = the module marine-rule values
   (2× Citadel 96 + 9× Battlestation 18 + Barracks 24 + core ~17); attacker = councilor
   Command + marine force **− a "Recent Mission Control Shortage" penalty (−12.2 observed
   while running MC over-cap — deliberate MC deficits tax assault ops)**. 52.8 vs 398.6 →
   0%. Flatten the defense modules first; the assault tooltip is a LIVE gauge — re-read it
   between bombardment passes and assault when defender ≤ ~25 (P = 1 − 0.5×0.775^Δ —
   canonical curve: [Victory Conditions and Endgame](Victory%20Conditions%20and%20Endgame.md) §5).
   Capture loot survives module-killing; only hab destruction (e.g. a plain-nuke leaker)
   forfeits it. Specimen carriers: core = Salamanders (always survive), battlestations =
   Griffins, battlestations/citadels/barracks = WarDogs.

## 8. THE REACTOR-FARM POWER CASCADE — the fission-tech base-kill doctrine (2033-08-19, code-confirmed)

⚠️ **SUPERSEDES the earlier "non-viable" verdict.** The 2033-08 runs looked like total
failure — until a battleship’s full-fleet log line showed **"720cm Green Arc Laser Cannon:
Alien Fusion Reactor Farm destroyed by 10.9 damage."** The path was hiding in plain sight:
**don't attack the battlestations — starve them of power.**

**Why reactor farms are the soft target:** `AlienFusionReactorFarm` has `spaceCombatModule`
= None → **NOT a combat module → no ×8 anti-bombardment armor** (that bonus is combat-modules-
only, §3). So ~11 damage kills one, and the 720cm (20 base) does it whenever it lands on one.
Nukes/kinetics can't — they're intercepted (§1); **only beams reach the reactor farms.**

**The power cascade (`TIHabState.UpdatePowerManagement`, code-verified):** the fortress base runs
**6× FusionReactorFarm (+300 each = 1,800 supply)** vs **9× Battlestation (−150) + 2× Citadel
(−60) = 1,470 combat demand** + ~330 economy. Battlestations/Citadels have `PowerFirst`
(power-priority via keySelector +10M), so as reactor farms die the ECONOMY modules shut off
first (~330 buffer ≈ 1 reactor). **Past the ~2nd reactor kill, supply < combat demand → the
lowest-priority battlestations go UNPOWERED.** Each unpowered battlestation drops from
`ActiveCombatModules` → **stops intercepting (num falls), stops STO return fire, armor halves
×8→×4.** Snowball: fewer STO beams → bombers survive longer → more reactor kills → more dark
→ base defenseless → nukes/kinetics/marines all penetrate → capture.

**Survivability = HYBRID armor.** Laser-vs-armor (code, `TISpaceShipState.AbsorbAndApplyArmor
Damage` + `ModifyArmorValueForLaserShot`): `through = max(0, incoming × LaserMod − points^1.5
× rangeFactor)`, LaserMod = **0.75 Hybrid / 1.0 Nanotube** (the 0.75 LaserResistance specialty
= the UI "25%", ONE effect — do not double-count). ⚠ **KEY: the `points^1.5` block uses only
the POINT COUNT — material is irrelevant to blocking.** So per-point Hybrid = Nanotube's ^1.5 block PLUS the
25% (×0.75 on incoming); NOT ~4× better per point (that ratio is per-TON: 17 vs 45.9 t/pt →
2.7× pts/ton → ^1.5 → ~4×). **The 25% DOES shift the point-equivalence — don't round it away.**
Immunity-threshold conversion: ×0.75 on damage → 1/0.75=1.333× on the D-threshold → `1.333^(2/3)
= 1.211×` on POINTS. So **80 Nanotube = 66 Hybrid; 80 Hybrid = 97 Nanotube-equivalent** (in the
high-penetration regime the 25% helps even more → Hybrid needs even fewer). **Don't cut nose
points anyway — go HIGHER** (Hybrid max nose 252 vs Nanotube 80); the win is you can afford it.

**Siege-nose sizing (block × vs Nanotube-80 = (pts/80)^1.5; mass = pts×17 t; exotics =
tons×0.0005):**

| Hybrid nose | block × | mass | exotics/ship |
|---:|---:|---:|---:|
| 80 | 1.0× | 1,360 t | 0.68 |
| 127 | 2.0× | 2,159 t | 1.08 |
| 166 | 3.0× | 2,822 t | 1.41 |
| **202** | **4.0×** | **3,434 t** | 1.72 |
| 252 | 5.6× | 4,284 t | 2.14 |

**Hybrid-202 blocks 4× the laser of Nanotube-80 at LESS mass (3,434 < 3,672 t) for 1.72
exotics** — push siege tanks to ~166-202 nose. **NOSE ONLY:** Hybrid lateral = 412.9 t/pt
(24× nose) — drop lateral to 1, tail cheap (17 t/pt). **Exotics is the limiter** (0.68→2.14/
ship — e.g. a ~6.8 stockpile ≈ 3 full siege tanks) → build a FEW dedicated Hybrid siege hulls, keep
the rest of the fleet on cheap armor.

⚠ **The t/pt figures above are BATTLECRUISER-Hybrid** — per-point mass and the per-hull cap are
BOTH material-specific (`cm/pt = xRayHalfValue_cm / XRayResistance`; Nanotube 7.866 · Adamantane
3.734 · Hybrid 2.500 — see [LESSONS-ships](../lessons/LESSONS-ships.md) S12 amendment, applied by
`warship_optimizer.armor_coefficients()`). Read your own hull off the tool or the in-game tooltip
before sizing.

**Exotics-free siege armor = ADAMANTANE, not Nanotube** (corrected 2026-07-30; the earlier
"Adamantane = kinetics-resist, wrong vs the laser STO" dismissal was wrong). The `points^1.5` block
depends only on POINT COUNT — the material contributes solely its LaserResistance multiplier — and
Adamantane buys points at ~half Nanotube's mass with a 2.1× higher cap:

| Hull | Nanotube max block | Adamantane max block | Hybrid max block |
|---|---:|---:|---:|
| Battlecruiser | 716 (80 pts @ 42.5 t/pt) | **2,187** (169 pts @ 21.1 t/pt) | 3,994 (252 pts @ 15.7 t/pt) |
| Lancer | 1,217 (114 pts @ 110.8 t/pt) | **3,721** (240 pts @ 55.1 t/pt) | 6,793 (359 pts @ 40.9 t/pt) |

So a zero-exotics siege hull still reaches ~3× maxed-Nanotube protection (~55% of maxed Hybrid,
before Hybrid's ×0.75 damage resist). Hybrid remains first choice when exotics allow; Adamantane is
the answer when they don't, and it needs no project beyond `Project_AdamantaneArmor`.

**Smaller hulls are better siege platforms than their tonnage suggests:** nose t/pt scales with the
hull's end-cap area, so a Battlecruiser's points cost 38% of a Lancer's, and its Adamantane cap
(169) already exceeds what most Lancers are actually built to. Combined with hull-only build time
([LESSONS-ships](../lessons/LESSONS-ships.md) S28: BC 180 base days vs Lancer 240) the BC carrying a
3-nose 720cm cannon is the efficient base-cracker — **but never drop below a 3-nose cannon to save
schedule**: per-shot damage must clear the module absorption floor (~9 on a reactor farm), which is a
cliff, not a slope, and a Monitor cannot mount one at any build time.

**Laser sizing (bombardmentValue = base-damage contribution; verified 2026-07-15):**
960cm Cannon 4.0 (4-nose, Lancer/Titan) · **720cm Cannon 2.8 (3-nose, BC — workhorse)** ·
480cm 2.0 · **360cm Battery 1.6 (4-hull, Monitor — only useful battery)** · 240cm 1.2 ·
120cm Battery 0.8 · 60cm Battery 0.4. **Particle lances = 0 (§3).** ⚠ **Base-cracking rewards
BIG single shots, not volume** — each shot must clear the module's armor absorption (reactor
farm absorbs ~9; 60cm's 6.1 base is fully absorbed → useless, empirically confirmed; 720cm's
20 → 10.9 through → kills). One 720cm >> four 60cm despite similar total firepower (same logic
as siege-coiler kinetics). **Strip small batteries from siege hulls** — but for the right reason
(corrected 2026-07-30): they cost armor-and-ΔV mass and return ~nothing through module absorption,
and PD is dead weight against an enemy with no kinetics or missiles. They do NOT increase the fire
you take: `SelectSTOTarget` is `MaxBy` — **ordinal** — and the volume is set entirely base-side
(powered combat modules × 2 pulses), so being the pick by 2.8 or by 12 draws the identical ~18
beams. The targeting risk lives on your OTHER hulls: arming escorts, tankers or marine/capture
ships can flip the `MaxBy` pick onto a hull with no siege armor. **Keep every non-siege ship's
bombardmentValue clearly below the designated siege hull's** so the dogpile lands where you chose.
(Mild counter-point: extra modules slightly dilute the random `OkayModules()` hit pick — not worth
the mass.)

**⭐ UV Phasers (UV Combat Lasers) ~DOUBLE bombardmentValue every tier:**
720cm GreenArc 2.8 → 720cm UV Phaser **5.6**; 960cm 4 → **8.0**. The single highest-value
weapon tech for an endgame base-kill campaign — cracks reactor farms far faster AND starts
penetrating the ×8-armored battlestations directly.

**Doctrine** *(worked plan from the reference campaign, which had every listed tech in hand
and ~6.8 exotics stockpiled — adjust to your own tech/stockpile state)*:
1. Purpose-built laser siege ship: **biggest nose cannon the hull allows (720cm on a BC;
   960cm on Lancer/Titan) + Hybrid armor (all facings) + ECM3**, LOW orbit; STRIP small hull
   batteries. No nukes/kinetics/particle (wasted vs powered base).
2. Sustained beam fire; ~30% of 720cm hits land on the 6 reactor farms (random OkayModules
   pick). Kill 2-3 → cascade self-accelerates.
3. **UV Combat Lasers dramatically accelerates it** — shorter
   wavelength → better armor penetration → faster reactor kills + eventually cracks the
   unpowered battlestations directly.
4. **This is the method for every victory-list alien base** — each runs on FusionReactor
   Farms with the same power vulnerability. It is THE endgame base-kill doctrine.

**Siege coilers do NOT crack the base (2026-07-15).** They're kinetic → intercepted by the
same num/num2 wall (verified via `base_siege_calc.py --spinal-siege-coiler-mk3 N`). num2 per
mount = impact_vel² × 0.5 × mass / cd: Spinal Siege Coiler Mk3 = 547, Heavy Mk3 = 362 (vs
Rail Mk3 73). Interception is a HARD wall — ratio ≥ 1 = 100% intercepted, ANY leak needs
num2 > num. The fortress base’s full num = 34,560 → you'd need **~64 Spinal Mk3 mounts** to leak,
infeasible; even 8 mounts don't land until the base is fully dark (num=0). So kinetics only
"finish" after lasers have already de-powered everything — and lasers do that finishing too.
Worse: carrying siege coilers to the siege RAISES the ship's bombardmentValue (coiler bombVal
8-9) → the STO `MaxBy` focuses it harder for zero payoff. **Verdict: don't bring kinetics to
a base siege.** Siege coilers' real value is the FLEET war (nose-breakers, survive tactical
PD by mass — [Space Combat Math](Space%20Combat%20Math.md) §3) → research them for `FreeFleets`, not bases. Mk3 >>
Mk2 >> Mk1 (num2 & per-hit both scale steeply); Spinal (FourNose, Lancer/Titan) > Heavy
(ThreeNoseAngle, fits a BC).

**Still-valid caveats:** the 2033-08 losses were real (Nanotube bombers + no reactor focus);
and per [Alien Production Rebuilding and Targeting](Alien%20Production%20Rebuilding%20and%20Targeting.md) §2 the 8 bases re-found/regrow, so kill
them LAST in one window. **Alternatives that ALSO work:** ShapedNuclear/Olympus (20% leak +
ignores armor — the low-micro option if the FPD→lottery lands) and an overwhelming fusion
fleet. But the reactor cascade is available NOW with owned tech.

## § Verify against 1.0.39

The ×60 multiplier, altitude bands/term, and 20% shaped bypass are 1.0.30–33 decompile
constants — exactly the class of numbers Pavonis retunes. **Fire one cheap probing volley
from LOW orbit and read the log before committing the fleet.**
