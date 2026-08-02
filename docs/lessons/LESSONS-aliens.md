# TI analyzer lessons — Aliens: hate, threat, campaign

Part of the Seventh Councilor lessons library (see the repo `CLAUDE.md`). IDs permanent
(`A1`…). Dates and worked numbers come from the
reference campaign (Resistance, 2026 start, Normal difficulty, alien progression 200%). Read
before any hate, alien-threat, victory-campaign, or specimen/milestone question. Canonical
win-path decode:
[Victory Conditions and Endgame](../mechanics/Victory%20Conditions%20and%20Endgame.md).

## A1 — Alien hate: the formula, not vibes

Use the analyzer's `Alien hate analysis` section as the authoritative answer — do NOT invent
thresholds or formulas.

**Formula** (anti-alien factions: Resist / Destroy / Exploit / Escape / Cooperate):

```
displayed_hate (`assessedAlienHateOfMe`) ≈ true_hate, tracked LIVE.

true_hate = max(floor, action_hate)
floor = max(20, MC_usage × diff_mod × 0.8^N_masking)   # USED MC (ships+habs+mining), not cap

action_hate accumulates per discrete event:
  +10                               per xenoform killed
  +0.4 × alien_hull.structuralIntegrity (±20%)   per alien ship killed
                                    (SI: Corvette=10, Destroyer=24, BC=48, Titan=90
                                     → hate ≈ 4 / 9.6 / 19.2 / 36; see
                                     Alien Hate and Diplomacy §5)
  +~10                              per alien hab/station destroyed
  (SI coefficient: 0.4 decompile-derived; wiki says 0.35 — see Alien Hate and Diplomacy §5)
decay: −0.64 on even months (≈−0.32/mo effective) while action_hate > floor
       (canonical derivation: Alien Hate and Diplomacy §6)
```

**Difficulty modifiers** — ⚠️ CORRECTED 2026-06-11 against decompiled `TIGlobalConfig.cs`
(switch: 1=Cinematic, 3=Veteran, 4=Brutal, default=Normal; the old 0-3 mapping mislabeled the
reference campaign Veteran for months). Read your campaign's `difficulty` from `config.json`
and use the matching row:

| Enum | Name | Hate-floor ×/MC |
|---:|---|---:|
| 1 | Cinematic | 0.05× |
| 2 (default) | Normal (the reference campaign — save metadata says "Normal") | 0.3× |
| 3 | Veteran | 0.6× |
| 4 | Brutal | 1.0× |

Every difficulty-keyed constant uses the column matching the config's difficulty (the
reference campaign: Normal): hate floor 0.3×MC; venting divisor 3 (C/N/V/B = 2/3/4/5);
knockdown reprieve 0.35 (0.5/0.35/0.15/0); Total-War year gate 20 modified years (25/20/12/0);
Alien Advanced Master Project gate 25 modified years (35/25/16/10). "Modified years" = elapsed
real years × alienProgressionSpeed (= `alien_progression_pct` / 100; the reference campaign:
200% → ×2).

**Thresholds:** ≤20 Tolerance (peace) · 20–49 Conflicted (Earth ops only) · **≥50 War** —
aliens dispatch strike fleets as their production allows.

**MCUsageMasking projects** — 4 exist, each `Effect_MCUsageMasking` (×0.8, stackable; all 4 →
0.8⁴ ≈ 0.41× floor): StrategicDeception, Maskirovka, OperationalMisdirection (anti-alien) +
OperationalSecurity (**Resistance-only**). Canonical table with costs/prereqs:
[Alien Hate and Diplomacy](../mechanics/Alien%20Hate%20and%20Diplomacy.md) §2.

**The meter is LIVE — the "frozen between fix events" theory is dead.** Verified 2032-02-27
(`killed_alien_fleet` save): destroying 2 alien fleets (≈185 total hull SI at 0.4×SI/kill) moved displayed
hate 339.33 → 413.35 (+74.0) while `lastDateOfFixedAlienHate` stayed pinned — the jump matched
the above-floor delta almost exactly, the floor ticked DOWN with MC, and `aliensRemoved` was
flat. The earlier Dec→Jan plateau at 255.86 across 26 saves was equilibrium (MC-growth ≈
above-floor decay), not a frozen meter. Corollary: a fleet kill is a near-permanent hate
commitment (~+74 above-floor ≈ 19 years at the effective ~−0.32/mo decay).

**Misconceptions to avoid:**
- `Effect_FixAlienThreatMeter` (Their Purpose / Their Demands / Hydra Diplomacy) is instant:
  it RECALCULATES the meter once (`UpdateAlienThreatMeter_Accurate`). It does NOT freeze the
  meter, does NOT reduce hate, and in practice shows zero visible change (the meter was
  already accurate). Don't promise "Their Purpose will jump/drop your hate."
- `Effect_SetAlienHate0` (Coexistence Pact) is the only hard reset — **AppeaseCouncil only**.
- `highestSpaceStrengthSinceLastAlienKnockdown` has NO public retaliation threshold — don't
  invent one.
- The floor is reduced ONLY by scrapping MC-consuming infrastructure or masking projects.
- The Martyr trait (`GlobalPropagandaIfKilled`) moves NATION opinion, not alien hate (hate
  stayed 255.86 through a Martyr-councilor death event). Track them separately.
- The community "Mirror effect" (0.25× hate transfer from anti-Servant/Protectorate actions)
  is unsupported by the reference campaign's data — several collaborator councilors killed,
  no alien-hate change. Don't model it.

**Ship-build hate contribution**: each ship adds `MC_cost × diff_mod × 0.8^N_masking` to the
floor permanently (until scrapped). At Normal (0.3) with 3 maskings (0.512): Destroyer/Monitor
(2 MC) ≈ +0.31 floor, Cruiser/BC (3 MC) ≈ +0.46, Titan (5 MC) ≈ +0.77.

⚠ `extract_snapshot.py`'s report previously printed a stale "displayed hate is FROZEN between
fix events" caveat — fixed 2026-07-04 to the live-meter model; if you see the frozen wording
in an old report, ignore it.

## A2 — "Where should I build ships?" → the threat-assessment section

The analyzer's `Faction threat assessment` computes mutual hate, per-faction ships/mass/habs,
fleet locations, **immediate threats** (hostile fleet AT a body where you have habs) and
**opportunistic targets** (hostile, ≤10 ships, ≥30 mutual hate). Decision rules:

- **Defensive (urgent) shipyards** → at the immediate-threat bodies. Don't cite enemies with
  no ships near you.
- **Offensive (opportunistic)** → at your bodies closest to the target fleets.
- **Anti-alien (strategic)** → outer-system (Callisto/Ceres/Saturn moons); alien fleets
  concentrate beyond Jupiter, and LEO yards waste 10–20 km/s escaping Earth.
- **NEVER** recommend attacking a faction with low mutual hate (≤20) AND comparable-or-stronger
  space power.

Faction-attack hate cost: killing a faction's ship adds 0.4 × its structuralIntegrity (±20%)
to that faction's hate of you — one code path for alien and human victims alike (see A1;
[Alien Hate and Diplomacy](../mechanics/Alien%20Hate%20and%20Diplomacy.md) §5; the Mirror
transfer is unmodeled).

## A3 (new 2026-07-03) — Specimen milestones gate the Xenology quartet; raids earn them

Griffin/Salamander Interrogation, Megafauna/WarDog Necropsy and Rapid Response Teams carry
`requiredMilestone` gates BEYOND tech prereqs (`AccessLiveGriffin`, `AccessLiveSalamander`,
`AccessAlienMegafauna`, `AccessWarDogCorpus`, `TargetedByTerrorMission`). The extractor's
unlockable table shows a ⛔ BLOCKED gate column for these. How they're earned (decompiled
`TIHabState.CaptureHab`, `TIRegionUFOLandingState`, `TIArmyState`):

- **Marine-raid any alien hab**: every alien CORE module carries Salamanders → capture grants
  AccessLiveSalamander. Shipyard modules + defense arrays/battlestations carry Griffins;
  barracks/garrison/citadel/defense arrays carry WarDogs — surviving modules at capture time
  grant those milestones.
- **Councilor-led Seize Space Asset at successLevel ≥3 (crit)** grants AccessLiveGriffin on any
  alien hab; **Assault Alien Asset vs a landed UFO at Critical Success** does too.
- **AccessAlienMegafauna**: an army you control must destroy a spawned `AlienMegafauna` army on
  Earth — cannot be proactively farmed (spawning is the aliens' move).

Practical: the campaign's first exotics raid usually unlocks Griffin+Salamander Interrogation
(+3 Seize / +3 Assault attack) and WarDog Necropsy in one op. Assault math + loot:
[Victory Conditions and Endgame](../mechanics/Victory%20Conditions%20and%20Endgame.md) §5.

## A4 (new 2026-07-06, CORRECTED 2026-07-07) — Alien hate is KILL-driven; MC is only a (usually non-binding) floor

⚠️ **The first cut of A4 was WRONG** — it credited "your MC footprint" as the hate driver;
verification against the decompiled source disproved it. The correlation analysis had
conflated MC and kills (both climb monotonically over the campaign, so r can't separate
them). Do not resurrect the MC-driver reading. Corrected mechanism below.

**Source** (`TIFactionState`, build 1.0.39 DLL):
```
assessedAlienHateOfMe = Clamp( AlienFaction.GetFactionHate(me),
                               MinimumFactionHate(me), MaximumFactionHate(me) )
GetFactionHate(me)   = factionHate[me]         # a STORED ACCUMULATOR (the kill/action term)
MinimumFactionHate   = MCBasedAlienHate(me)    # = the FLOOR only (clamp lower bound)
MCBasedAlienHate     = missionControlUsage × AI_AlienHatePerMCUtilitizedMultiplier[difficulty] (+ effect mods)
```
So displayed hate ≈ **max( kill-accumulator , MC-floor )**. The accumulator grows via
`GainCombatFactionHate` (destroy an alien ship/station → `+hull.structuralIntegrity ×
factionHateSIFactorPerShipDestroyed`) and `GainFactionHate` (other destruction/hostile events). MC
sets ONLY the floor; it is not the hate value unless the accumulator is below it.

**Why kills, not MC, is the real driver (reference campaign):** hate sat pinned at the ~20
minimum through 2026 → mid-2029 **with zero kills, even as MC grew** (MC×mult stayed < 20, so
the floor never moved dynamically). The campaign's first kills (2029-12, Kills 0→4) snapped
hate to 79, and it tracked cumulative kills ever since — 2033-04 displayed **553** vs an
MC-floor of only **~123**. Every point of hate above the early-game ~20 is kills. The floor has
been non-binding since the first battle. (r(Hate,MC)=r(Hate,Kills)=+0.99 in the campaign's
tracking table is the time confound that fooled the first analysis.)

**Buildup is NOT a hate input — and the arrow, if any, runs hate → alien response, never the
reverse.** Alien ship/base counts do not appear anywhere in the hate formula, so hate cannot be
"caused by" their buildup. The only hate→alien coupling is escalation: at hate ≥
`alienFactionHateWarValue` (~50) the Hydra goes to War and dispatches strike fleets. Their raw
*buildup* grew steadily even while the player was floored at 20 (6→24 ships across 2026-28), so
total alien production is mostly alien-progression/time-driven, independent of your hate. Do not
tell the player the aliens "built up because you angered them," and do not tell them their
footprint is generating hate.

**Advice implications:** (1) hate is a ledger of YOUR kills — each alien ship/station destroyed is a
near-permanent +SI commitment (a Titan kill is +36 hate — ~9 yrs at the effective ~−0.32/mo decay, A1/§6); (2) you can't cut
hate by shrinking MC unless the kill-accumulator has already decayed below the MC floor (rare once
you're at war); (3) masking projects lower the *floor* (A1), which only helps in the pre-war /
low-kill regime where the floor is what binds. See A1 for the floor formula and decay.
