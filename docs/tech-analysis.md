# Terra Invicta — curated tech & project analysis

This document collects the **human-written strategic analysis** that was layered on top of an
auto-generated Terra Invicta research vault. The full per-tech reference pages (stats, prereqs,
effects, unlock chains) are **generated from the game's own template files** by `generate_vault.py`
and `generate_modules.py` — regenerate them locally against your install; they are not reproduced
here. What follows is only the judgment layer: which projects are worth researching, which are
traps, and the general evaluation lessons learned along the way.

**How to read the entries:**

- Scores are 0–10 with a letter tier (S+/S/A/B/C/D/E/F). They were assigned during one long
  Resistance campaign (playing defense against the alien "Hydra" fleet, roughly game years
  2031–2033), so "skip"/"queue now" verdicts reflect that campaign's state — treat them as a
  worked example, not gospel. Several entries were re-scored later in the campaign; where the
  correction taught something, the reasoning is kept.
- **RP costs are game-template costs** (as they appear in `TIProjectTemplate.json`). The reference
  campaign ran at a 200% research-rate setting, so its in-game price was template ÷ 2 — some
  timing notes ("~2 months at weight 3") assume that scaling.
- Game-data facts (module stats, effect values) come from the game's template JSONs and should be
  re-verified against your install/version; balance patches move these numbers.

The analyzed set skews toward **faction projects** (the per-faction research menu) because that is
where per-slot decisions are made; global techs were ranked separately, but a few global-tech
worked examples whose reasoning generalizes (fusion ladders, the coilgun family, Future Techs)
are included in their category sections below. Ship-module comparison
tables in the vault are fully generated and carry no hand analysis, so they are omitted here.

---

## General lessons (meta-rules that came out of these analyses)

1. **Check the `stackable` flag before calling two projects redundant.** Two projects granting the
   same effect (e.g. `Effect_MiningFissilesBonus` ×1.15) stack multiplicatively when
   `stackable: true` — 1.15 × 1.15 = +32.25%. An early "redundant, abandon it" verdict was wrong
   for exactly this reason.
2. **"Raises/doubles a cap" projects are worthless unless you actually hit the cap.** Verify the
   binding constraint first. Armor Struts was scored 1/10 when no hull approached the armor cap,
   then 9/10 a year later when every flagship class was cap-bound. Same logic applies to the
   combat-g cap-raise chain.
3. **Do marginal analysis per ship, not fleet-wide hand-waving.** "Raises the g cap for the whole
   fleet" sounds universal; counting hulls showed the second +0.5g raise helped ~10 of 60 ships and
   the third helped essentially zero. Scores were corrected downward accordingly.
4. **Scan paused/partially-researched projects, not just the "available" list.** A 24%-complete
   mega-project can be the cheapest strategic option on the board (sunk-cost recovery), and
   one-time-globally projects can be sniped by AI factions if you sit on them.
5. **Beware the efficiency trap on lasers.** IR variants show higher efficiency numbers than Green,
   but wavelength dominates armor penetration (Infrared < Green < Ultraviolet); the "better" stat
   is a decoy.
6. **Missile families have a strict tier ordering** (Hypergolic → Hydrolox → Nerva propulsion).
   Once the Hydrolox tier is researched, the Hypergolic tier of the same warhead class is a strict
   downgrade — don't backfill it.
7. **Don't refit half an upgrade pair.** Example: upgrading only the reactor (Gas Core III → IV) on
   a hull that keeps its old drive adds hundreds of tons of dead reactor mass for zero thrust; the
   drive and reactor refits must go together.
8. **Cheap ≠ free.** A 200–800 RP project still costs slot-days that could go to a victory-chain or
   fleet-wide multiplier project. Opportunity cost is the real price.
9. **Project availability rolls are probabilities, not schedule items.** The tech panel's "Unlock
   Chance 100%" means *eventually guaranteed*; the monthly trigger (base ramp + contribution bonus
   + councilor Science) determines when. Read the live trigger value from a save rather than
   assuming a fixed delay.

---

## Xenology

### Wormholes (`Project_Wormholes`) — 10/10, S+
Victory-chain step for several factions (for Resistance: Wormholes → The Choke Point → The Final
Assault = win). No direct in-game effect; pure progression. There is no comparison — every other
faction project is a delay relative to this once its prereq (Their Purpose) is done. 30,000 RP
(template). Research immediately; auto-trigger candidate.

### Exotic Hybrid Systems (`Project_ExoticHybridSystems`) — 9/10, S
Direct effects are noise (+5% to a few army/military IP priorities — worthless unless you actually
allocate those pips). The real value is the **unlock tree**: UV Phaser Cannon/Batteries (the true
next laser tier — not IR), Spinal Neutron Lance, Antimatter Beam Core Reactor, fusion reactors,
Interstellar Launching Laser, Styx Nuclear Torpedoes, The Great Journey. 25,000 RP. Queue after the
victory-chain step but before smaller A-tier picks; every late-game laser refit and reactor decision
flows through this gate.

### Pherocyte Resistance (`Project_PherocyteResistance`) — scored 8/10 A initially, settled at 6/10 B
+2 Pherocyte Resistance per councilor — defense against alien mind-control conversion
(community-verified to roughly halve lifetime conversion probability). Also unlocks A Permanent
Peace, Hydra Biowarfare, Pherocyte Mastery. 30,000 RP is a lot for a slow-burn threat; worth it if
you have irreplaceable councilors at risk, but it sequences after victory-chain and fleet-multiplier
projects.

### Pherocyte Liability Theory (`Project_PherocyteLiabilityTheory`) — 7/10, A
+2 Executive Protection: aliens suffer −2 on enthrall missions against your control points.
Complementary to (not a substitute for) Pherocyte Resistance — this defends CPs, that defends
councilors. 10,000 RP; cheap preventive insurance whenever the alien faction is running Earth-side
ops. In the reference campaign it also carried partial sunk progress, making it cheaper to finish.

---

## Space Science (drives)

The drive verdicts compare **combat thrust at a full x6 stack**, exhaust velocity (EV), and cooling
type (Closed = self-cooled and combat-safe; Open/Calc = radiator-dependent and combat-vulnerable).

### Lodestar Fission Lantern (`Project_LodestarFissionLantern`) — 10/10, S+ ("warship king")
x6: 66 MN cruise, thrustCap 20 → **1,320 MN combat**, EV 31.4 km/s, Closed cooling, needs Gas Core
Fission IV. Combat thrust is 15–550× any other fission-era drive. Deploy on every warship; 10,000 RP
is trivially repaid.

### Poseidon Lantern (`Project_NeutronFluxLantern`) — 7/10, A (transit/strike niche)
x6: 77.4 MN cruise but thrustCap only 2 → 155 MN combat; EV 66 km/s; Open cooling; any reactor;
propellant includes 20% fissiles. The 2× thrustCap marks it as a transit/cruise drive: use for
long-range strike/bomber hulls that need ΔV, never for stationary defenders (vulnerable radiators,
and Lodestar's combat thrust crushes it). Note the in-game UI renames `NeutronFluxLantern` to
"Poseidon Lantern". 35,000 RP.

### Pharos Drive (`Project_PharosDrive`) — 4/10, C (legacy; re-scored down from 8)
x6: 85 MN combat, EV 25.5, Closed cooling. Once Gas Core IV exists, Lodestar matches Pharos on
cooling and propellant while beating it on every thrust/EV metric — Pharos has **no new-build
role**. The original 8/10 "workhorse" score conflated "what the legacy fleet happens to use" with
"good pick" — different things. Pharos → Lodestar is a valid in-family refit (both Fission_Thermal,
Closed, Hydrogen) but forces a paired reactor refit to Gas Core IV, because Lodestar x6 needs
~1,120 GW. **Never refit the reactor alone** — on a Pharos hull, Gas Core IV adds ~560 t of dead
reactor mass for zero thrust gain.

### Mass Driver (`Project_MassDriver`) — 5/10, B
A **drive**, not a weapon, despite the name (Electromagnetic class): 12 kN cruise, 120 kN combat,
EV 9.81, Closed cooling, any reactor, **any propellant**. 10,000× weaker than Lodestar in combat —
its niche is dirt-cheap unmanned cargo/mining hulls fed on arbitrary reaction mass. At 200 RP it's
nearly free, and it unlocks the Superconducting Mass Driver upgrade.

### Burner Drive (`Project_BurnerDrive`) — 2/10, D
x6 combat 15.6 MN, EV 69, Open cooling, Gas Core only. Strictly dominated by Poseidon on every
axis (10× combat, 119× cruise, same EV class, same cooling, more reactor flexibility). Never use.

### Fission Spinner Drive (`Project_FissionSpinnerDrive`) — 2/10, D
x6 combat 45 MN, EV 17.7, **Calc cooling** (radiators take combat damage and the drive can shut
down mid-fight — the dealbreaker), Molten Core reactor. Pharos beats it everywhere with Closed
cooling. The "frees Gas Core capacity" argument fails once Gas Core is mature.

### Teardrop Drive (`Project_TeardropDrive`) — 2/10, D
x6 combat 30 MN, EV 19.6, Calc cooling, Molten Core. Strictly worse than Fission Spinner, which is
itself strictly worse than Pharos — two-step dominated. Never deploy.

### Lars Drive (`Project_LarsDrive`) — 2/10, D
x6 combat 8.8 MN, EV 19.6, Closed cooling (its one virtue), Molten Core. Pharos gives Closed
cooling at 10× the combat thrust. On hulls small enough that Lars's mass profile matters, ion
drives or VASIMRs are the better answer anyway.

### Cavity Drive (`Project_CavityDrive`) — 2/10, D
x6 combat 5.1 MN, EV 20.4, Closed. ~1/17 of Pharos's combat thrust; the downstream Advanced Cavity
(x6 → 31.7 MN) is also worse than Pharos. Useful only in the very early game before Pharos exists.
Cheap (750 RP) but the slot-days are pure opportunity cost.

### Helicon Drive (`Project_HeliconDrive`) — 3/10, D (extreme-EV niche)
x6 combat 2.4 MN but **EV 314 km/s** — 5× Poseidon. Calc cooling, Noble Gases propellant, glacial
0.12 MN cruise. Theoretically relevant for an ultra-long-range one-shot transit hull (deep Kuiper
colony, interstellar prep); no use case in a normal inner-system campaign.

---

## Materials (armor, heat sinks, radiators)

### Future Tech: Materials (global tech, repeatable) — check WHO the effect pays
Its effect is `Effect_AllHumanFactionsGainExotics` — it hands exotics to **every human
faction**, not just you. Once your own exotics pipeline exists, researching it mostly arms
your rivals. The general rule: repeatable Future Techs are last-resort filler, and any
global whose effect names "all factions" must be scored on the *net* transfer, not your
gross gain (same reasoning family as the shared-globals caveat in
[Research Sequencing](strategy/Research%20Sequencing.md)).

### Armor Struts (`Project_ArmorStruts`) — 1/10 → re-scored 9/10, A+ (the poster child for lesson 2)
**Doubles the maximum armor-thickness cap per hull section** (nose/lateral/tail); costs 100 t +
1 utility slot to install. First analysis (mid-campaign): no realistic build approached the cap —
accel/turn/ΔV constraints bound long before it — so the module added literally zero armor and the
project scored 1/10. A year later both flagship classes sat *at* their nose caps (Battleship N91,
Monitor N57) and wanted more; below the biological g-cap, added armor is "free" (doesn't reduce
displayed combat g). At that point the same 1,000 RP project became the cheapest cap-busting
research in the game and the #1 open-slot pick. **The score is entirely a function of whether the
cap binds — check your own shipyard before queueing.** Also note: on utility-starved hulls
(Monitor: 3 slots, all essential) the install slot may be too expensive even when the cap binds.

### Exotic Armor (`Project_ExoticArmor`) — 8–9/10, A/A+
The armor material itself looks unimpressive next to Nanotube on raw resistance numbers, but
per-point volume packing changes the math: computed per **ton**, Exotic delivers ~3× the X-ray and
~10× the baryonic (kinetic) absorption of Nanotube, and swapping material at the same thickness cap
saves thousands of tons per capital hull. Combined with Armor Struts (doubled cap × better
material) a battleship gets roughly 3–8× total absorption for *less* mass than before. Also the
gateway to Hybrid Armor and Nuclear Hardening. 10,000 RP. Not S-tier only because Adamantane
(behind the Diamondoids global tech) supersedes it.

**Adamantane's own value was understated** (corrected 2026-07-30): an armor POINT is a
material-specific thickness, so Adamantane buys 2.01× Nanotube's points per ton and raises a hull's
max-point cap 2.11× → **~3× maxed Nanotube's laser block, at zero exotics**. It is the correct
siege armor whenever Hybrid's exotics aren't affordable, not merely an anti-kinetic pick (LESSONS-ships S12 amendment).

### Hybrid Armor (`Project_HybridArmor`) — 9/10, A
Best per-mass **laser** armor in the game (laser mass-index 90 kg/m²·halving vs Exotic 114,
Nanotube 342) plus the unique **LaserResistance 0.75** specialty (a ×0.75 DAMAGE multiplier = the UI's **25%**
reduction, ONE effect — not 75%; corrected 2026-07-30), at half the exotics build-cost of Exotic
Armor. Against a beam-dominant
alien fleet (in the reference campaign: 132 lasers vs 19 particle weapons, and lasers are hitscan —
un-dodgeable) this is the correct endgame armor. Unlock path: Exotic Armor → Diamondoids (global) →
Adamantane Armor → Hybrid enters the monthly unlock-roll pool. In the reference campaign it rolled
six days after Adamantane completed (the ~30%/month trigger hit early), at which point it strictly
dominated Exotic on both damage axes: doctrine became "every design frozen after that date wears
Hybrid".
See also (armor entries): [Weapon Doctrine vs the Hydra](strategy/Weapon%20Doctrine%20vs%20the%20Hydra.md) — the armor-placement and doctrine-level verdict these material picks feed into.

### Exotic Heat Sinks (`Project_ExoticHeatSink`) — 9/10, A+
7.20 GJ/ton — 4× the efficiency of Molten Salt. Swapping a battleship's Heavy Molten Salt sink for
Heavy Exotic gives −470 t *and* 2× heat capacity (≈2× sustained combat duration before heat
throttling); swapping to the standard Exotic sink gives −720 t at equal capacity. Across a
20-capital fleet that's five figures of tons. Caveat that kept it out of S: heat-sink type-swaps
may be an **invalid refit** (check the refit dialog); if so the upgrade needs new hulls. Note heat
capacity does not affect peak combat g (biological cap) — it buys engagement *duration*.

### Foamed Metal Armor (`Project_FoamedMetalArmor`) — 4/10, C
Lightest armor in the tree (920 kg/m³, ~half Nanotube) with ChippingResistance 0.75, but ~2.6×
lower baryonic resistance per point — per ton of armor it roughly breaks even, with different
chipping behavior. Wrong material for line defenders (they want per-point absorption); genuinely
useful for transit-mass-sensitive hulls (bombers/assault ships) where ΔV budget dominates.

### Ionic Dust Radiator (`Project_IonicDustRadiator`) — 2/10, D
~700 t per GW of waste heat vs Tin Droplet's ~105 — **~5× heavier than the free radiator you
already have**. Its community-reported niche is combat survivability (dust is harder to shoot off
than droplet sheets), which only matters for doctrines that keep drives lit under fire. For
mass-optimized warships it is a strict downgrade; the genuine upgrades are Gallium Mist / Lithium
Spray / Dusty Plasma later in the tree.

### Cobalt Dust Radiator (`Project_CobaltDustRadiator`) — 3/10, D
Same story as Ionic Dust, slightly less bad: ~331 t/GW, i.e. ~3× heavier than Tin Droplet. Skip
for the same reasons.

---

## Military Science (weapons)

### Coilguns (global tech, 30,000 RP) — the salvo trap, and where each Mk actually lands
A worked family-vs-family comparison (reference campaign: Rail Mk1–3 fully deployed, Coilguns
freshly on the menu) that produced the R18 "salvo trap" lesson. Coilguns fire SALVOS
(`salvo_shots` × `intraSalvoCooldown_s`, then `cooldown_s` between salvos — Mk1 = 3-shot,
Mk2 = 4-shot, Mk3 = **5-shot**); railguns are single-shot. Comparing bare cooldowns first
called Coil Mk1 a 4–5× downgrade and Coil Mk3 a "parity sidegrade" — both wrong. Full
salvo-cycle sustained DPS, mount for mount vs Rail Mk3:

- **Coil Mk1: ~2–2.5× behind** everywhere. Never mount it; it's a research rung.
- **Coil Mk2: parity in battery (turret) mounts** with ~+46% muzzle velocity there — a
  defensible PD-role stopgap if its gates arrive before Mk3's — but still 1.3–1.45× behind
  in the cannon/spinal damage mounts and −50 km range everywhere.
- **Coil Mk3: a genuine ~1.4–1.9× upgrade in every mount class**, with the fastest slugs
  (9.0–9.9 kps) at equal range. This is the refit target; the family's whole value is the
  entry fee to it.
- Two second-order effects both favor coil: lower shot-energy draw per MJ delivered
  (efficiency 0.5 vs rail's 0.35 — pairs naturally with the Ultracapacitors global for the
  salvo's burst draw), and PD penetration (faster slugs spend less time in hitscan-PD
  engagement range; salvo bunching spikes peak arrival density). Counterweight: rail slugs
  are ~30% heavier, and PD erodes slug mass per hit — see the PD model in
  [Weapon Doctrine vs the Hydra](strategy/Weapon%20Doctrine%20vs%20the%20Hydra.md).
- Raw same-tier DPS tables are the **no-PD floor**; against PD-dense enemies the coil
  advantage widens. Verify per-patch with the generated Magnetic Guns table — and check
  `salvo_shots` on EVERY gun template before any DPS claim.

### Hypergolic-Fueled Nuclear Torpedoes (`Project_CerebrusNuclearTorpedoBay`) — 9/10, S
The first researchable **nuclear** warhead: ~1.13e9 MJ per hit (300 kt) vs a conventional heavy
missile's 720 MJ — six orders of magnitude — with chipping 1.0 (best) and bombardment 50 (can
strike surface bases). Bay: 25 t, magazine 4, ΔV 6.41, 7.47 g, 1,000 km range; ammo costs ~1%
fissiles. Hypergolic propulsion is the family's weak leg (EV 3.23), but nothing else conventional
kills 40k-structural-value alien hulls. This is the payload the Advanced Missile Warfare Doctrine
global tech is bought for. Upgrade path: the Hydrolox nuclear tier (Hades: ~2.45e9 MJ, ΔV 7.7,
9.14 g, 20 t, bombardment 100) is strictly better when it rolls — swap then.
See also: [Orbital Bombardment](mechanics/Orbital%20Bombardment.md) — what the bombardment values actually do against surface bases.

### Vital Point Shell Targeting (`Project_VitalPointShellTargeting`) — 9/10, S
`Effect_ShipMagDamage` ×1.1: **+10% damage to every magnetic weapon fleet-wide, permanently, with
no refit**. For a kinetic-doctrine fleet (dozens of rail/coil mounts) this is the flat-upgrade
project — massively undervalued by its name. Requires the AccessAlienShip milestone. 10,000 RP.
Research as soon as kinetic hulls are being built; earlier = more accumulated value.

### Precision Focusing Software (`Project_PrecisionFocusingSoftware`) — 6/10, B
The laser twin: `Effect_ShipLaserDamage` ×1.1, same 10,000 RP, same milestone gate. Score tracks
your fleet doctrine — B-tier for a kinetic-leaning fleet, reassess to 8–9 if you flip to
laser-heavy (e.g. after UV Phasers unlock).

### Smart Spacecraft Defenses (`Project_SmartSpacecraftDefenses`) — 8/10, A
`Effect_SurvivabilityUpgrades` ×0.95: fleet takes **−5% damage from everything, permanently,
without spending utility slots or mass** (unlike Component Armor / ECM modules). 20,000 RP.
Underrated by name; pairs with Vital Point Shell for compound offense+defense. Queue before major
capital engagements.

### The IR laser family — all 2/10, D (four projects: IR Laser Cannon 500 RP, IR Laser Batteries 500 RP, IR Arc Laser Cannon 1,500 RP, IR Arc Laser Batteries 1,500 RP)
IR is the weakest of the three laser wavelengths (Infrared < Green < Ultraviolet). The IR variants
are stat-identical to their already-cheap Green counterparts *except* the 810 nm wavelength, which
armor eats exponentially harder than Green's 540 nm — and they carry half the bombardment value.
**Trap stat:** the Arc variants show higher efficiency (0.35 vs 0.30) than Green Arc — it looks
like an upgrade and isn't; wavelength dominates. If Green is researched, every IR project is a
strict combat downgrade. The real next laser tier is UV Phaser via Exotic Hybrid Systems.
See also: [Weapon Doctrine vs the Hydra](strategy/Weapon%20Doctrine%20vs%20the%20Hydra.md) — the fleet-level wavelength and laser-role doctrine.

### Hypergolic missile tier — obsolete once Hydrolox is in hand (lesson 6)
- **Hypergolic Explosive (Anaconda, 800 RP) — 5/10 → re-scored 2/10, D.** Strictly worse than the
  Hydrolox HE bay (Copperhead): half the flat damage (360 vs 720 MJ), lower EV/accel. Only a
  stopgap for a player with no Hydrolox research.
- **Hypergolic Fragmentation (Rattler, 800 RP) — 4/10 → 2/10, D.** Same pattern vs Viper (Hydrolox
  frag): −38% EV, −23% accel, −26% ΔV, same warhead. Its sole edge (5 t bay vs 10 t) only matters
  on hulls too small to want missile bays at all.
- **Hypergolic Penetrator (Harlequin, 1,500 RP) — 1/10, F.** Strict downgrade of the Hydrolox
  penetrator line. Mark obsolete in the menu.

### Hydrolox Penetrator (Lancehead, `Project_LanceheadMissileBay`, 1,500 RP) — 5/10, B−
Penetrator chipping 0.6 vs frag 0.5 — a modest anti-armor upgrade on existing missile-boat mounts.
Verified refit verdict: ✓ swap Copperhead bay → Lancehead bay (−5 t/bay, same magazine/salvo and
accel; per-hit ~720 MJ flat becomes ~6,400 MJ kinetic at 8 km/s closing — velocity²-dependent, so
great when closing, poor in a stern chase). ✗ do **not** replace the frag (Viper) bays: the frag
terminal submunition split is the PD-saturation layer against a point-defense-heavy enemy fleet,
and Viper out-legs Lancehead on ΔV.

### Nuclear-powered (Nerva) conventional torpedoes — skip while nukes exist
- **Explosive (Athena, 2,000 RP) — 2/10, D.** 1,800 MJ chemical warhead with ΔV 12.83 but only
  4.89 g. Against alien armor that's chip damage; the nuclear torpedo delivers ~600,000× more per
  hit in the same slot.
- **Fragmentation (Zeus, 2,000 RP) — 3/10, C−.** Longest conventional reach (ΔV 13.69) but 4.89 g
  and chipping 0.5 — a standoff frag screen a close-volley doctrine doesn't need when faster frag
  bays already fill the saturation role.
- **Penetrator (Ares, 5,000 RP) — 4/10, C.** Kinetic, no flat damage, 4.89 g (slow through the PD
  envelope). Nerva EV buys reach, not lethality. A sidegrade; revisit only if a PD-immune standoff
  doctrine emerges.

See also (for the missile tiers above): [Missile Swarm Doctrine](strategy/Missile%20Swarm%20Doctrine.md) — the saturation mechanics and salvo sizing that determine which bays are worth mounting at all.

### Elite Marine Assault Unit (`Project_EliteMarineAssaultUnit`) — 5/10, B
Assault 8 module (vs Advanced Marine 6, Marine 4) and the gateway to the three faction top-marine
projects (assault 10). Marines only matter for boarding/assault ops — irrelevant while playing
defense, but research before any victory chain that ends in assaulting alien stations. 2,500 RP.

---

## Information Science

### Automated Platform Core (`Project_AutomatedPlatformCore`) — 3/10, C (re-scored 2026-07; was 8/10)
Automated platform founding kit: −1 Mission Control instead of −2, zero crew, no councilor
founding visit. **The catch that sank the original A score: automated cores are a permanent
tier-1 dead end** — no core module lists them in `upgradesFromName` (the crewed ladder is
PlatformCore→OrbitalCore→RingCore only), so an automated hab can never tier up and never hosts
tier-2+ modules (Ops Centers, big-mine upgrades, institutes). Worth it ONLY if your doctrine
founds wide, disposable tier-1 sprawl (remote belt claims); worthless to a tall economy that
upgrades every mining hab — see [LESSONS-research R25](lessons/LESSONS-research.md). The
reference campaign carried the stale A score for a year past the point its economy stopped
founding tier-1 platforms. Downstream unlocks (Automated Fission Pile / Solar Collector /
Supply Depot / Solar Mirror) share the same ceiling. 1,000 RP.

### Automated Outpost Core (`Project_AutomatedOutpostCore`) — 3/10, C (re-scored 2026-07; was 7/10)
Same idea for surface outposts (−1 MC, 0 crew vs −2 MC, 5 crew) and the same tier-1 dead end
(nothing upgrades from it; the crewed ladder OutpostCore→SettlementCore→ColonyCore is the only
path up). Gateway to Automated Mining Complex. Same verdict: wide-sprawl doctrines only; skip
in a tall campaign. If you do want automation, research both — but decide the doctrine question
first (R25).

*(Vital Point Shell Targeting and Precision Focusing Software are Information Science projects in
the game's taxonomy; they're covered under Military Science above with the other weapons.)*

---

## Social Science

### Nation-expansion projects — the rule
One-time-globally unification projects **require majority control of the anchor nation**;
researched without it, the RP is wasted (or helps whoever does control it). Verdicts are therefore
pure functions of your nation map:

- **Pan-Asian Combine** (`Project_Pan-AsianCooperative`, 40,000 RP, requires China) — 7/10 →
  re-scored **9/10, S** in the reference campaign: China fully controlled, 24% of the cost already
  sunk (resuming a paused mega-project is the cheapest strategic buy on the board — lesson 4), and
  it gates the Pacific League → Greater PanAsia chain that adds Korea/Japan/Taiwan + SE Asia to the
  bloc. Also AI-denial value: one-time-globally means a research-leading rival can take it first.
- **Greater United North America** (30,000 RP, requires USA) — 6/10, B when USA is held. Real bloc
  expansion, but priced like a victory-chain step, so it queues after those.
- **Akhand Bharat** (15,000 RP, requires India) / **Europe Ascendant** (25,000 RP, requires EU) /
  **Restored Commonwealth** (10,000 RP, requires UK) — **1/10, E** in any run that doesn't hold the
  anchor nation. Skip entirely.

### Stakeholder Subversion (`Project_StakeholderSubversion`) — 7/10, A
+2 to Hostile Takeover missions (steal enemy orgs: their benefits move to your roster and leave
theirs). Cheap (5,000 RP), permanent, offensive; strongest with a high-Persuasion councilor to run
the missions.

### Government Network Analysis (`Project_GovernmentNetworkAnalysis`) — 6/10, B
+3 to Coup missions. Higher leverage than Stakeholder Subversion in principle (flips whole
nations), but only if expanding bloc width is part of your strategy; a "hold three majors and win
on the victory chain" plan barely uses it. 7,500 RP.

### Encrypted Research Systems (`Project_EncryptedResearchSystems`) — 5/10, B
Blocks enemy intel-scanning of your research queue. Matters most right before sensitive
victory-chain research, where knowledge of what you're researching can trigger reactive AI moves.
One is enough — don't stack further intel-shield projects after it. 10,000 RP.

---

## Life Science — the combat-g cap-raise chain

Human ships clip displayed combat acceleration at a biological g-cap:
`min(peak_thrust/mass/g, CAP)`. Base cap 3.0g; four projects each add +0.5g
(`Effect_IncreaseMaxSurvivableCombatAcceleration`, additive, stackable):

| # | Project | Template RP | Cumulative cap |
|---|---|---:|---:|
| 1 | High-Thrust Ergonomics | 1,000 | 3.5g |
| 2 | Astronaut Fitness Regimen | 2,500 | 4.0g |
| 3 | Acceleration Pharmaceuticals | 10,000 | 4.5g |
| 4 | High-G Recombinants (gated behind the Genies global tech) | 20,000 | 5.0g |

Same effect, wildly different value per link — the chain is the clearest illustration of marginal
analysis (lesson 3). See also: [LESSONS-ships](lessons/LESSONS-ships.md) S11 — the verified biological-cap formula and why added armor below the cap is "free".

### Astronaut Fitness Regimen — 10/10 initially, settled at 8/10, A+
Cheapest unlocked raise (4× and 8× cheaper than the next two for the same +0.5g). Scored 10/10 as
"single biggest fleet tech" until a per-hull count showed it meaningfully helped ~20 of 60 ships
(the high-thrust monitor classes; most older hulls never approached the cap). Still a top pick —
but Armor Struts typically comes first: cheaper, addresses a cap binding on *every* flagship class,
and defensive headroom compounds better than offensive thrust headroom.

### Acceleration Pharmaceuticals — 4/10 → 9/10 → settled 6/10, A− (score history is the lesson)
First pass called the effect "unclear, likely flavor" — wrong; the template wasn't properly
searched (it grants the same +0.5g). Re-scored 9/10 when many hulls were cap-clipped… then
corrected to 6/10 on marginal analysis: by the time it completes, the previous raise has already
un-clipped most hulls, so this one helps ~10 of 60 ships. Worth doing eventually; not the automatic
next pick.

### High-G Recombinants — 8/10 → 5/10, C
The final raise (4.5 → 5.0g) lifted the cap above every existing hull's peak thrust — near-zero
value for the current fleet, 20,000 RP, and locked behind Genies. Valuable only if you then design
new max-thrust hulls to exploit the headroom. Document the chain so it's remembered when the gate
opens, but don't prioritize it.

### Residential Module (`Project_ResidentialModule`) — 4/10, C
Hab module for population capacity/growth; gateway to Civilian Complex. Fine in principle, but if
your binding constraints are Mission Control and metals rather than population, the other 1,000 RP
cheapies (automated cores, Armor Struts) buy strictly more. Skip unless a slot would otherwise go
to something worse.

---

## Energy

### Terawatt Gas Core Fission Reactor II (`Project_GasCoreFissionReactorV`) — 9/10, S
Gas Core V: 1,650 GW (+67% over Gas Core IV) at the same 3.5 t/GW specific power — bigger drives
and fewer reactor modules for the same total power. Unlocks the Flare Drive and the next reactor
tier (Terawatt III). The gas-core reactor ladder is the backbone of a fission-era fleet doctrine;
climbing it is always high-leverage. 10,000 RP.

### Choosing a fusion ladder — Tokamaks vs Inertial Confinement (global techs, worked example)
The reference campaign scored the Tokamaks global 3/10 from the drive table alone ("dominated
rung-for-rung by ICF") and had to reverse it to 7/10 the same day when the analysis was redone
as reactor+drive **pairs** (LESSONS-research R20; `fusion_ladder_planner.py` automates it).
What the pair table shows, and why it generalizes:

- **Per-mass thrust flips the verdict.** Tokamak reactors are the lightest and cleanest line at
  every tier (Fusion Tokamak V: 0.1 t/GW at 99% efficiency); ICF's early rungs are the
  dirtiest (ICF III at 92% efficiency drags kilotons of radiator per high-power thruster). At
  every shared fuel tier the Tokamak pair beats the ICF pair per ton of propulsion stack.
- **Per-hull absolute thrust is ICF's real edge.** Hulls cap at 6 thrusters, so only the big
  per-thruster ICF drives (Helion Nova and up, ending in the Protium Nova/Converter Torch)
  push capital hulls to fighting acceleration. Capitals live on the ICF lane; escorts and
  workhorses often do better per ton on the Tokamak lane.
- **Unlock odds are part of the price.** Several marquee fusion drives carry
  `factionAvailableChance` under 100% — a lifetime lottery, not a delay (in the reference
  campaign the ICF lane's linchpin lantern was 75%-available: a 25% chance of *never*). The
  Tokamak lane's first fusion drive was the only guaranteed one on the board. Running both
  ladders is cheap insurance: reactor rungs are project-lane, and the second global is small.
- **Fuel logistics differ.** Helion-tier drives need He3 mining infrastructure; the Tokamak
  lane's Deuteron and Protium rungs run on plain hydrogen.
- **No first-generation fusion lantern beats a top fission lantern per ton in combat** —
  early fusion buys exhaust velocity (reach), not combat power. Don't refit a defense fleet
  to first-gen fusion "because fusion".

---

## Faction-specific research

These appear only on particular factions' menus (though faction-availability metadata in the
generated pages proved incomplete — verify against your save, not the wiki).

### Guerrilla Warfare (Resistance, 5,000 RP) — 6/10, B
+2 Unrest missions; +3 unrest in your nations after they're conquered (harder to hold); a one-time
grant of 20 Operations on completion (significant if Ops is your tightest resource); and unlocks
two of the faction's marine projects (the path to assault-10 marines for late-game boarding). The
unrest mechanics are niche for a tall-economy playstyle — the unlock + resource grant carry the
score.

### Counterinsurgency Operations (Humanity First, 5,000 RP) — 5/10, B
+2 to Stabilize missions (cohesion recovery) and +10% national IP to the Oppression priority (only
matters if you actually allocate Oppression pips). Solid if your majors run chronic cohesion gaps
and you actively run Stabilize; note the boost doesn't add mission *capacity* — councilor slots
still bind.

### Subsurface Radiation Analysis (Project Exodus, 15,000 RP) — 5/10, B
`Effect_MiningFissilesBonus` ×1.15 — +15% fissile mining network-wide. Decent compounding value on
reactor-heavy runs; modest whenever fissiles aren't the binding resource.

### Rapid Fissile Enrichment (Initiative, 20,000 RP) — 5/10, B
The *same* ×1.15 fissile effect — and the effect is `stackable: true`, so researching both gives
1.15² = **+32.25%** combined (lesson 1; an earlier "redundant, abandon it" verdict was wrong).
Research after Subsurface Radiation Analysis; leverage rises if you're scaling reactor count or
heading into fusion's fissile appetite.

---

*56 of ~900 generated pages carried hand analysis at extraction time (2026-07-18). Everything else
in the source vault is machine-generated from game data — regenerate locally rather than copying.*
