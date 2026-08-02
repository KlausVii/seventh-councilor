# TI analyzer lessons — Councilors, nations, opinion & orgs

Part of the Seventh Councilor lessons library (see the repo `CLAUDE.md`). IDs permanent (`C1`…). Dates and
worked numbers come from the reference campaign (Resistance, 2026 start, Normal difficulty).
Read before councilor-mission, nation-investment, public-opinion, or org advice.

## C1 — Inert priority pips: founded programs and the multiplier trap

`Effect_SpaceflightProgramPriorityBonus50` (Bootstrap Spaceflight Programs) multiplies
`Civilian_InitiateSpaceflightProgram`, which only produces output on nations WITHOUT a
spaceflight program — once `spaceFlightProgram == True` the pips go inert. Same for
`Military_InitiateNuclearProgram` (post `nuclearProgram`) and `Military_FoundMilitary`.
Generic "+X% priority" effects only help if the player has real pip allocation there —
**always check `pip_distribution` per nation before recommending them.**

**CRITICAL: inert Initiate-X pips are save-state artifacts, NOT actionable.** After founding,
the UI hides the priority — the player cannot remove the pips, and they don't draw from the IP
pool. Do NOT recommend "reallocate these N inert pips"; the extractor labels them
"informational" and excludes them from effective pip-share math. Use them only as a signal
that the program is founded (so multiplier projects are worthless).

## C2 — CP priority pips compete for a fixed per-nation IP pool

Each player CP has `controlPointPriorities` (category → 0-3 pips) and the nation has
`baseInvestmentPoints_month`; a category's IP share = its pips ÷ total pips set across the
faction's CPs in that nation. Don't recommend "add pips to X" without noting the dilution of
everything else. The extractor's per-nation pip-distribution section shows this correctly.

## C3 — The biggest IP lever is cohesion, not pip reallocation

IP is suppressed when cohesion sits below rest-state (e.g. USA 2.07 vs rest 6.00). Unity pips
speed recovery; Knowledge pips help toward 5; Oppression pips REDUCE cohesion despite their
surveillance value. The extractor's nation dashboard flags cohesion gaps and estimates the IP
recovery. Check the gap before optimizing pip mixes.

## C4 — Cohesion rest-state formula (verified from tooltip)

`cohesionRestState_dailyCache` = base 16.0 − inequality×~2 (penalty MITIGATED while education
< 10!) − GDP-per-capita-loss×inequality − population penalty − geographic-sprawl penalty −
hostile claims (mitigated by low government) + 1/near-peer rival + **2/active war** −
elite-public ideology variance − public-opinion variance + autocracy bonus ((5−democracy)
scaled, reduced by unrest).

Player levers to RAISE rest: **Welfare pips** (inequality — the big fixable one), Knowledge
(pulls toward 5), **stay at war** (+2 each), don't annex. Counterintuitive: education above 10
EXPOSES the full inequality penalty — fix Welfare before raising education. Per-IP cohesion
(current, not rest): Unity +0.015–0.022 per IP; Knowledge +0.003–0.005 per 0.5 IP toward 5.

## C5 — Councilor `attributes` excludes traits and orgs

`attributes` = base + augmentations + XP only. The in-game core-stats view adds applicable
trait statMods (some conditional on location/nation/faction state). **Orgs never appear in
displayed stats** — they contribute at mission time; firing a councilor only returns their
orgs to the pool. The extractor's roster applies trait mods with condition evaluation.

## C6 — Recruit pool ≠ unfactioned pool

The hireable pool is exactly `faction.availableCouncilors` (~9 rolled candidates). The global
unfactioned pool is much larger but not hireable now. Never recommend a candidate who isn't in
`availableCouncilors`.

## C7 — Only recommend orgs in `faction.availableOrgs`

The marketplace is a rolling eligibility-filtered subset. "Buy Mossad" is wrong unless Mossad
is literally in `availableOrgs` right now.

## C8 — Martyr trait: NEVER recommend Assassinate

`Martyr.specialTraitRule = 'GlobalPropagandaIfKilled'` (value 35). Killing a Martyr-trait enemy councilor
(2031-10-20) caused +27pp Appease in USA/CHN/RUS and a ~2.6-point rest-state crash across ~80%
of nations. The trait is `easilyVisible` — scan every enemy councilor (the extractor flags
them); the effect fires regardless of mission detection. Offer Purge / Coup / Press Asset
instead. The propaganda hit is TEMPORARY (~60-day decay, ~0.4-0.5pp/day — USA recovered by
~Dec 25) but the two-month vulnerability window is real. When meeting an unfamiliar enemy
trait, check `TITraitTemplate.json` for any `specialTraitRule` before recommending lethal
action.

## C9 — Public-opinion investment rules

Thresholds on the player's faction share: ≥85% don't invest · 70–85% optional (idle
high-Persuasion councilor) · 50–70% invest · <50% URGENT. Public Campaign (`Propaganda`):
Persuasion-based, permanent-assignment cycle, needs councilor on Earth; best with
OpinionLeader/MediaDarling (in the reference campaign, a high-Persuasion councilor with OpinionLeader/MediaDarling was the go-to). What
else moves opinion: **Unity pips** (slow drift toward elite ideology — USA 55%→87% over ~2
months on 18 pips), **rally-around-the-flag events** (step changes: allied war entry + a
visible fleet victory jumped CHN 53%→83% in 2 days). Knowledge pips move cohesion, not
opinion; Spoils actively worsens variance. Always name the councilor and target nation —
never "run Public Campaign" generically.

## C10 — Advise cycles make nation IP oscillate

Advise gives the target ~+8-10 IP/mo while active (~15 days) with a cooldown gap — so IP
oscillates between two values even under continuous re-assignment. An IP "drop" between saves
is usually the cycle; a real change is monotonic or steps to a NEW value. Diagnose via
`priorMissionTemplateName`/`priorMissionTarget` and `nation.advisingCouncilors`. (One
adviser's rotation meant USA had Advise ~3 weeks per cycle, not "almost permanent".)

## C11 (new 2026-07-03, from the four-corrections set) — Defensive projects score against OBSERVED threat

Enthrall/pherocyte/abduction/sabotage-defense projects are insurance; their value is
conditional on the threat actually manifesting. Before scoring, scan every rival councilor's
`currentMissionTemplateName` + `priorMissionTemplateName` in the save. 2033-02 verification:
zero Enthrall or pherocyte ops by ANY faction, none targeting held nations → Pherocyte
Scanners is a 3, not a 6. Extension of R11's "does the player invoke the mechanic" test to
"does the ENEMY invoke the mechanic". Re-score if enthrall/terror events appear.

## C12 — Capability timing: verify the granting org/project is OWNED before scheduling

Seize Space Asset exists only with the Janus Section org (= The Final Assault completion); two
strategists once booked Seize missions ~4 months before the org could exist. Same error class
as tech-gated inert pips (C1/R12): a plan step must name the capability's source and confirm
it's already in hand at the step's date.

## C13 (2026-07-18) — How wars are stored: two alliance arrays + a per-nation enemy list, kept in sync

A human-nation war lives in a `TIWarState` object (`gamestates` →
`PavonisInteractive.TerraInvicta.TIWarState`), and it is recorded in TWO places that must
agree — any reader tracing "who is at war with whom", and any edit, has to handle both
(save-verified on the reference campaign, 2033-07-08):

1. **The war object.** `attacker` / `defender` are the two side LEADERS (single nation ids);
   `originalAttacker` / `originalDefender` preserve who started it. The FULL sides are
   `_attackingAlliance` and `_defendingAlliance` — id lists that include the leader plus every
   co-belligerent. `cohesionGainByNation` holds one Key/Value entry per participant (the war's
   cohesion term for that nation). `displayName` is `"<attacker leader>-<defender leader> War"`
   and does NOT rename when co-belligerents join — the name reflects the leaders only, so
   "X-Y War" can have many nations on each side. `historyWarStatus` on each nation is a
   32-entry rolling series the game recomputes — never hand-set it.
2. **Each nation's enemy list.** `TINationState.wars` is a **flat list of enemy nation-ids —
   NOT war-ids** (nothing on a nation references a war by id; the game joins nation→war via the
   alliances plus this list). It is the UNION of opposing-side nations across ALL of that
   nation's wars, so a nation fighting two wars lists every enemy from both. `nation.allies` is
   a SEPARATE relationship — standing diplomatic pacts, not war sides. Co-belligerents are
   usually also allies, but sharing a side does not by itself put a nation in another's
   `allies`.

**Consistency rule** any belligerent change must satisfy: when nation N joins the attacking
side, add N to `_attackingAlliance`, give N a `cohesionGainByNation` entry, and make **every**
attacker list **every** defender as an enemy and vice-versa — for the NEW nation and the
pre-existing ones (a pre-existing attacker gains only the newly-added defenders; the new
attacker gains the whole defending side it doesn't already list). Leave `attacker`/`defender`
(leaders) and `allies` untouched. `scripts/ti_war_editor.py` does exactly this; the
save-mutation mechanics (why it is byte-surgical, the backup + validation) are
[LESSONS-process](LESSONS-process.md) P15.

Two caveats from the reference-campaign edit: (a) new `cohesionGainByNation` entries were set
to 0.0 — a safe neutral the engine recomputes next tick, not a verified "correct" value;
(b) the tool adds BELLIGERENTS, not alliances — if the joining nation isn't already allied with
its new side (`allies`), the game may re-resolve the diplomacy on load, so check the joiner's
`allies` first. Strategic tie-in: an active war is also a **cohesion lever** — rest-state gets
+2 per active war (C4) — so widening or sustaining a war can prop a nation's IP, not only serve
a military aim.

## C14 (2026-07-13) — Councilor-led space capture: the Seize roll is Command-only, and orgs are movable — pick the councilor LAST

When you plan a councilor-led capture of an enemy or alien station (`SeizeSpaceAsset` —
the mission that pays crit-level loot and the live-specimen milestone,
[LESSONS-aliens](LESSONS-aliens.md) A3), read the resolution from the template before
naming a councilor. Template-verified (1.0.38, `TIMissionTemplate.json`,
`TIMissionResolution_Contested`):

**Attacker modifiers:** councilor **Command** (the only stat in the roll) + **Operations
spent** on the mission + **attacking force size** (marine modules on the fleet) + a penalty
if YOU are over MC cap (`TIMissionModifier_AttackerMissionControlShortage` — being over cap
directly debuffs your assault roll; the defender-side twin is
[LESSONS-economy](LESSONS-economy.md) E26). **Defender modifiers:** joint council
Command + protection + defending force size + support shortage + decommissioning state.
Hard conditions: troops present (`SeizeSpaceAssetTroopsPresent` — no marines, no mission),
target in range, and the mission is **SpaceOnly** — don't confuse it with
`AssaultAlienAsset`, which is **EarthOnly** (landed UFOs and Earth facilities).

**Who can run it:** native mission for seven councilor types (Astronaut, Commando,
Inspector, Kingpin, Officer, Operative, Rebel) — and **org-granted** to anyone by the
faction winner orgs (e.g. the Resistance's Janus Section, `ResistWinner`), the faction
space-group orgs, and rare marketplace orgs. Check `missionsGrantedNames` before ruling a
councilor out by class.

**Pick the councilor LAST, after packing the orgs.** Org stat bonuses apply at mission
time even though they never show on the councilor sheet, and orgs are freely transferable
between your councilors — so the real question is "who has the best BASE Command and can
be spared from Earth for the round trip", then consolidate every +Command org your faction
owns onto that one flyer (org capacity is bounded by the councilor's Administration; each
org costs its tier). Reference campaign: base Commands ran 10–12, but stacking the faction
special org (+10 Command) plus four smaller +Command orgs took the flyer from 12 to ~29
effective — the org packing mattered nearly 3× more than the councilor choice. Traits to
check: Combat Astronaut +1 Command; Pacifist −3 Command; **Earthbound hard-restricts
`SeizeSpaceAsset` and all space movement** (`restrictedMissionNames`) — an Earthbound
councilor can never fly, whatever their stats.

**Maximize the margin, not the pass chance.** Success level 3 (crit) is what grants
`AccessLiveGriffin` on an alien hab and roughly doubles the exotics loot (A3; [Victory
Conditions and Endgame](../mechanics/Victory%20Conditions%20and%20Endgame.md) §5) — a
councilor who "probably succeeds" is leaving the mission's best payouts on the table.
Spend Operations generously (it is usually your slackest resource late-game) and get under
MC cap before the roll fires.

**The win mission needs none of this.** `ResistWin` (Close the Gate) resolves
`TIMissionResolution_Automatic` — no roll, no stats. Any winner-org holder co-located with
the target wins. Optimize the flyer purely for the Seize rolls along the way, and do NOT
hold a high-value Earth councilor (your best adviser or counter-intel anchor) hostage to a
mission that any org-holder can execute.

## C15 (2026-07-18) — Public-opinion CRASHES are usually rival Public Campaigns: diagnose with step-bisection, and know that propaganda conversions do NOT decay

When your faction's public opinion in an anchor nation drops sharply, do not reach for
"organic decay", "war weariness", or a Martyr event first. Reference-campaign forensics
(a 32-pp collapse in the campaign's anchor nation, 87%→55% over four months): the entire
decline was **two single-cycle rival Public Campaigns** — one −15.8 pp step overnight
(two rival factions' councilors completing `Propaganda` on the same nation on the same
day) and one −12.1 pp step over six days, with dead-flat opinion between and after.

**The diagnosis workflow** (`opinion_trajectory.py` automates all of it):

1. Coarse pass, ~monthly saves, to bracket the drop (`--glob` per month works well).
2. Bisect the bracketing window with daily saves to the exact day. A drop of >5 pp
   inside one or two days is a DISCRETE EVENT, not drift.
3. Attribute: scan every faction's councilors for `priorMissionTemplateName ==
   'Propaganda'` and resolve `priorMissionTarget` to the nation. The mission cycle is
   ~15 days, so `priorMission*` still holds the culprit for days after the step lands.
   Also check whether the step hit ONE nation (targeted mission) or many at once
   (global event / Martyr death — cross-check a couple of other majors the same day).
4. If no propagandist surfaces, diff the councilor roster across the step for deaths
   (Martyr, [C8](LESSONS-politics.md)) before considering anything exotic.

**Mechanics verified on the reference campaign:**

- **Propaganda conversions persist indefinitely.** Unlike the Martyr
  `GlobalPropagandaIfKilled` surge (which decays ~0.4-0.5 pp/day, gone in ~2 months, C8),
  publics converted by a Public Campaign stay converted. The only standing counter-forces
  are your own Public Campaigns and **Unity-pip drift** — with ZERO Unity pips in the
  nation, the post-crash level is permanent (reference campaign: flat for 3+ months).
- **Opinion moves stepwise along the ideology spectrum, not straight to the caster's
  pole.** A Submit-faction campaign against a Resist-majority public surfaces as
  +Escape/+Cooperate gains, not +Submit — don't rule a faction out as the caster just
  because "their" ideology didn't move.
- `nation.historyPublicOpinion` is 32 entries, `[0]` = newest, ~2-day step (same
  newest-first convention as every nation history array, [LESSONS-process](LESSONS-process.md)) —
  one save gives you a free ~64-day trace before you need to open older saves.

**Response rules** once diagnosed: your share <70% → schedule your own Public Campaign
(C9 thresholds; name the councilor); add Unity pips in the nation if you hold the CPs
(the drift-back force C9 describes); and watch the gaining rival — a faction that
propagandized one of your anchors tends to rotate through the others next.

## C16 — Federation vs unification: what "federate" actually does (and who leads)

`federate` and `unify` are **two different mechanics** — conflating them is the common trap. A
**federation is an alliance-plus-pooling relationship in which the member nations stay separate**:
each keeps its own government, regions, and control points. Only **unification** merges nations
into one, and unification is **gated behind federation** — code: `TINationState.cs:6643`
`CanUnifyFeedback` requires `this.inFederation && this.federation == nation.federation`, and
`UI.Nation.CanUnifyFeedback6/8` reads "Must be in same federation" + "for a sufficient duration".
So "federate to cut my CP count" is wrong: federating changes nothing about CP count — the
CP consolidation only arrives later, at unification.

**What a federation actually grants** (`UI.Nation.FederationTooltipDetail` + `DevelopmentSummary`
in your localization; `nationState.inFederation` / `federation` in `TINationState.cs`):

- **Mutual defense** (a military alliance).
- **Pooled space-program Funding and Boost** — the federation's combined Funding/Boost is shared,
  and "the federation values are used in place of the domestic values when calculating our
  faction's share of incomes." A member without a space program may borrow the federation's Boost
  and Mission Control priorities as long as any member has one.
- **A bonus to Economy-priority investments** in every member.

So even before any unification, federating your own high-GDP pillars is a mild economic positive
(the Economy bonus helps a climate-GDP bleed; pooled Boost eases a Boost constraint) — and it
starts the duration clock toward unification.

**The lead nation is NOT a free pick — it is the member with the most claims** ("the member
nation with the most significant international ambitions (claims)"; code: `federation.leadNation`,
`TINationState.cs:16/1354`). You can only influence it by changing claim counts (Set-Policy claim
legitimization), rarely worth it. So decide *which nation you want leading* by what the federation
(and eventual unification) should be built around — economy/cohesion for a stable base, claim
count for future-expansion reach — then accept the default the claims produce, or don't federate.

**Dark Federation:** if the lead is authoritarian (low `democracy`), members may only leave with
the lead's consent, and leaving via coup/revolution lets the lead declare war
(`UI.Nation.DarkFederationTooltip`). Irrelevant when you control every member, but check it before
federating nations you don't fully hold.

**Reference campaign (2032-06):** two fully-held pillars were offered a federation — a large-GDP
nation (claims 49, cohesion 5.05, GDP ≈$39.5T) and a Russia-led federation-state (claims 82,
cohesion 4.17, inequality 3.34, GDP ≈$20.5T). The Russia-led state leads by claim count (82 > 49
— not choosable). Verdict: federate — the claims default was also the structurally better lead
(lower inequality → healthier base; larger claim set → stronger future-expansion hub), the
larger economy still flows into the pooled pot, and it opens the path to a later unification that
*would* consolidate the CPs. Federation itself neither merged the two nations nor dropped any of
the held CPs.

Strategy tie-in: the CP-consolidation value people attribute to "forming a meganation" belongs to
**unification**, not federation — see [Earth Endgame Consolidation](../strategy/Earth%20Endgame%20Consolidation.md)
(formation projects) for the tall-Earth sizing.

## C17 (2033-09-01 in-game; authored 2026-07-19) — Compare CP **LOAD**, not CP **seats** — and the exact per-CP cost-against-cap formula

**Seat count ≠ political power.** "Control points held" is a raw headcount; it says nothing about
how much Earth economy a faction commands. The metric that matters — and the one the game's own
CP-capacity tooltip uses ("Capacity Used") — is **CP LOAD**: the summed economic weight of the
control points a faction holds. A faction can hold the FEWEST seats and DOMINATE by load
(concentration on a few high-GDP nations). **Never rank factions by seats; rank by load.**

**The exact per-CP cost against the cap** (decompiled `TINationState.ControlPointMaintenanceCost`,
build 1.0.39 DLL):

```
perCP_cost = (nation.GDP / 1e9) ** controlPointCostScaling / (2 * nation.numControlPoints)
           = 0   if nation.alienNation, or if the CP's benefitsDisabled (crackdown) is set
```

- `controlPointCostScaling = 0.6` (lives in `TIGlobalConfig`, NOT mirrored into save/templates;
  calibrated below). **Do not confuse with `controlPointIPScaling = 0.35`**, which defines the
  DIFFERENT quantity `economyScore = (GDP/1e9)^0.35` (that one drives IP, not cap cost).
- `numControlPoints` is the NATION's total CP slots (clamped to 6), **not** how many a faction
  holds — so every CP in a nation costs the same, and holding k of n costs `k × perCP_cost`. A
  nation fully held therefore costs `(GDP/1e9)^0.6 / 2`, split evenly across its slots.
- Crackdown zeroes a CP's cost (`CurrentMaintenanceCost` returns 0 when `benefitsDisabled`),
  matching the tooltip line "Control points suffering from a crackdown do not count against this cap."

**Calibration (exact).** 2033-09-01 reference save vs the in-game CP tooltip: four nations
(56.58 / 40.95 / 35.18 / 25.51) — all reproduced to the decimal at scaling 0.6, and the
player's summed load = **847.2** vs the tooltip's **Capacity Used 847**. `extract_snapshot.py` now
emits `cp_load_by_faction` and the player's `cp_load`, and ranks factions by load (helper
`cp_cost_against_cap`).

**Why this matters — the trap it kills.** In the reference campaign the Resistance held **20 seats
(dead last of 7 factions)** but **847 load — #1 by ~2×** (next: Exodus 423, Initiative 422), at
**42/seat vs 5–12/seat** for rivals: a textbook concentration play (three of the
richest economies). Reading the seat headcount alone produced the flatly-wrong call that the
player was "dead last / politically squeezed / starved of Earth income" — when they controlled the
majority of Earth's research/boost/MC. **How to apply:** for any "who controls Earth / am I behind
politically" question, quote CP LOAD (and the income tables: Faction comparison, Per-nation
research contribution). Seats are a footnote. Being OVER cap (load > capacity) is a real problem
(influence maintenance + seizure window, [LESSONS-economy](LESSONS-economy.md) E26) — but it is the
*rich*-empire problem, never evidence of being starved.

## C18 (2033-05-12 in-game; authored 2026-07-19) — Annexation before-vs-after audit: what lands instantly, what lags, and why your scores DROP first

When the player annexes/conquers a nation and asks "what did that do to my scores", run a
disciplined two-save audit (`nation_report.py <annexer> before.gz after.gz`), not a
memory-based narrative. The workflow and the traps, save-verified on the reference
campaign's annexation of a 5-region, $5.9T neighbor (2033-05-12):

**Finding the "right before" save.** Bisect by REGION COUNT, not by date labels:
`nation_report.py <annexer> --scan "<date-glob>" --watch <target-templateName>`. The
annexed nation's `TINationState` object PERSISTS after annexation with `exists` still
true — its `regions` list just goes empty, while the annexer's count jumps. Multiple
saves can share one in-game date; the region columns tell you exactly which pair
brackets the event.

**Instant vs lagged.** Live scalars update at annexation: `GDP`, `spaceFunding_year`,
`unrest`, `cohesion`, `regions`, `inequality`, `education`. The `history*` heads
(`[0]`, [LESSONS-process](LESSONS-process.md) P16) refresh on their own cadence and can
lag a same-day event by one sample — the reference campaign's save showed MC 111 while
the in-game panel already read 112. Tooltips outrank the save on the day of the event
(P1).

**Additivity sanity checks** (all exact in the reference campaign): annexer GDP += the
target's GDP (+$5.94T); Funding += the target's full budget (+758); population +=
the target's (+120M); Mission Control += the target's MC network (85→111, +26 — often
the single biggest prize); boost jumped +37%. If a sum doesn't add up, you diffed the
wrong save pair.

**The transient — expect the scores to get WORSE before better.** Annexation spiked
unrest ~0→3.75 and dropped cohesion 4.86→3.89, so despite absorbing a nation producing
~215 research/day, the annexer's research FELL 2,526→2,218/day (−12%) and available IP
fell ~15% (the unrest multiplier, C19). Do not tell the player the conquest "boosted
research" — it will, but only after the unrest is worked off. Recovery levers: quell
unrest (C19's ~15% multiplier is the fast win), Welfare/Unity investment toward the
cohesion rest-state (C3/C4 — and note annexation also LOWERS rest-state via population
and sprawl), and each army disbanded post-war returns +0.5 IP/month (C19). Also expect
`inequality` and `education` to shift toward the population-weighted blend, `democracy`
to barely move (it converges slowly rather than averaging), and `displayName` possibly
to change — keep identifying the nation by `templateName`
([REFERENCE](REFERENCE.md) § Nation history arrays).

**The unrest spike is a DEMOCRACY-GAP effect, and it fires ONLY on FULL absorption** (code-verified
`TINationState.AbsorbNation`, 1.0.39 DLL). When a nation is fully absorbed (all regions taken, the
target ceases to exist), the annexer takes `UnrestReason_DemocracyLostInRegionTransfer` iff the
absorbed nation is MORE democratic: `if (absorbed.democracy - 1 > annexer.democracy)` then
`unrest += (absorbed.democracy - annexer.democracy) / 2` (cap 9.8; the alien nation scales it by
`1 - Submit-opinion`). So the case that spikes unrest is a **high-democracy nation swallowed WHOLE
by an authoritarian one** (a dem-8.7 EU fully absorbed into a dem-2 annexer would add
`(8.7-2)/2 ~= 3.35`, matching this note's reference ~3.75). A dictatorship-absorbs-dictatorship, or
absorbing a LESS-democratic nation, adds little or nothing.

**A PARTIAL annexation does NOT spike unrest - leaving a rump is the escape hatch.** Ceding only
some regions (peace deal / war gains) while the target survives runs through
`TransferRegionsControlTo` (`UnrestReason_RegionTransfer`, a cohesion/region calc) and **never
invokes `AbsorbNation`, so the democracy-gap spike never applies**. Diagnose full-vs-partial by
whether the target's `TINationState` still holds regions afterward (it persists with `exists` true).
**Correction (2033-09 reference case):** the player's dem-2 annexer took 11 of the EU's 15 regions, leaving a
4-region rump renamed "France" (`2026_EUA` persists) - a PARTIAL take, so unrest FELL (0.145->0.092)
with no spike, and research/IP did NOT drop from unrest (only from the separate cohesion-tracker
`Annexation` penalty, which decays). An earlier hypothesis blamed the missing spike on a
"friendly/player-aligned population" - WRONG; the sole cause was partial-vs-full absorption. Cohesion
still crashes via the Annexation penalty regardless of full/partial.

## C19 (2033-05-12 in-game; authored 2026-07-19) — Monthly IP decomposition: base = economyScore, and the save field is the POST-penalty number

The in-game Monthly Investment Points tooltip decomposes as: **GDP-derived base →
−unrest percentage → −0.5 per army safe at home → −0.5 per navy → (occupation
penalties) → available**. Decoded and verified on the reference campaign
(2033-05-12):

- **The base IS `economyScore` = `(GDP/1e9)^0.35`** (`controlPointIPScaling`, see
  [REFERENCE](REFERENCE.md) § CP LOAD for the sibling constant warning). Tooltip base
  44.68 vs save `economyScore` 44.66 — a 0.05% match. So the base rises with GDP and
  with nothing else on the tooltip's first line.
- **Unrest penalty:** at unrest 3.75 the tooltip read −15%. Applied multiplicatively to
  the base BEFORE the flat army/navy deductions: 44.68 × 0.85 − 3.5 (7 armies) − 2.0
  (4 navies) = 32.48 ≈ tooltip available 32.36.
- **`baseInvestmentPoints_month` in the save is the AVAILABLE (post-penalty) number,
  not the base.** Don't reconcile it against `(GDP/1e9)^0.35` directly.
- **An IP number that looks "too high" for the formula is usually an Advise cycle.**
  The reference campaign's pre-annexation available IP oscillated 36.8 ↔ 48.0 with no
  underlying change — the ~+8-10 IP Advise boost switching on and off (C10). Check
  `nation.advisingCouncilors` before theorizing; a first-pass reconstruction here
  mis-attributed the gap to a phantom "GDP base drop" until the Advise cycle explained
  it (P1: the tooltip decomposition outranks any reconstruction).
- Navy count isn't read from `TINationState` by the current tooling (armies are the
  `armies` list); take the navy line from the tooltip.

Diagnosis recipe for "why did my IP crash": read unrest (each tooltip tier skims the
base), count armies/navies added since the last save, check for occupations, then check
the Advise cycle — in that order. Post-annexation both big terms move at once: the base
RISES with the absorbed GDP while the unrest multiplier takes a bigger bite (C18).

## C20 (2033-09 in-game; authored 2026-07-20) — Full vs PARTIAL annexation: what transfers, what stays with the rump, and why the rump's income may read zero (a PLAYER choice)

Two distinct outcomes. Tell them apart by whether the target nation still holds regions
afterward — its `TINationState` PERSISTS either way (`exists` stays true), so identify by
`templateName`, never `displayName` (it renames — C18).

**FULL annexation** (`AbsorbNation`, target ceases — 0 regions left): everything transfers
ADDITIVELY to the annexer — GDP, population, regions, Mission Control, AND the target's whole
Funding program folds in (C18 additivity reference). Fires the democracy-gap unrest spike if the
absorbed nation is more democratic (`DemocracyLostInRegionTransfer`, C18).

**PARTIAL annexation** (region cession / sunder — target survives as a rump): the annexer gains
only the REGIONS taken, weighted by their ECONOMIC value (NOT region count). **A partial annex can
take MOST of a country (leaving a tiny rump) or just a SMALL slice** — the transfer scales with
what you take. 2033-09 case: the annexer took **11 of the EU's 15 regions ≈ 99% of its GDP/pop**
(+$10.1T, +174M, +41 MC); rump **"France" (`2026_EUA`) kept 4 tiny regions** ($89B GDP, 3M pop).
Consequences that differ from a full annex:
- **Funding does NOT transfer — the entire Funding program STAYS WITH THE RUMP.** It's a national
  institution, hard-capped at **4% of the nation's GDP** (so it decays toward 4% of the rump's
  shrunken economy; sticky short-term). Verified: France kept **686.6/mo** Funding; the
  annexer's Funding was unchanged. So a partial annex of a Funding-rich nation leaves the Funding
  behind unless you go FULL.
- **NO democracy-gap unrest spike** (runs through `TransferRegionsControlTo`, not `AbsorbNation` —
  C18). Leaving a rump is the escape hatch from the unrest hit.

**You KEEP the rump's income by default — disabling it is a PLAYER CHOICE, not an annexation
side-effect.** After a partial annex you still hold the rump's CPs, so its Funding/research/etc.
keep flowing to you at your control share; the annexation does NOT auto-suppress them. A CP earns
**ZERO** income (Funding, research, boost, MC, IP all show share **0.0**) only when it is
`benefitsDisabled`, which happens by one of THREE routes — read the cause, don't assume:
1. **Your own decision** — the standard one: **Abandon Nation** (`UI.…AbandonNation`: CPs "provide
   no direct benefits… cost nothing against our Control Point cap… helpful for when we are over our
   Control Point cap"; optional Auto-Renew), or running your OWN **Crackdown** on them. This is a
   deliberate CP-cap-shedding move — crackdown/abandoned CPs are excluded from the cap (C17;
   `UI.Nations.CPMaint9` "from Crackdowns and Abandonment").
2. A **rival's Crackdown mission** against you (offensive — sets up a Purge to steal the CP).
3. A **Coup** side-effect (`Each of our control points has suffered a crackdown`).

**2033-09 case — a rational player move, NOT a trap:** the player was **59 over CP cap (847/788)**
and rump France's Funding was decaying toward its 4% cap anyway, so they **deliberately
abandoned/cracked-down France** (`benefitsDisabled`, both CPs, to 2034) to shed low-value cap load.
Result: France's Funding shows player share **0.0 by choice**. So the "0 income from France" is a
CP-cap decision, not an automatic consequence — the player traded ~275/mo of decaying, capped
Funding for CP-cap relief. **Correction of two earlier wrong reads:** (a) it is NOT "you keep ~100%
of the rump's Funding" (the player disabled it); (b) it is NOT "partial annex commonly crackdowns
your rump CPs automatically" — that disabling was the player's manual Abandon/Crackdown decision.

**How to model the player's income change (per-source, never "you took the economy so you gained
everything"):** the annexed regions' research/MC/boost move to the ANNEXER (collected at its
control share); the target's Funding stays with the RUMP and is yours to collect UNLESS you abandon
it. Net 2033-09: gained the EU economy via the annexer + evicted Humanity First + no unrest spike;
CHOSE to give up the rump-France Funding/research/MC share (~275/mo Funding) for CP-cap relief.

**Scripts:** every income-SHARE computation must EXCLUDE `benefitsDisabled` CPs. `research_income.py`
already does; `extract_snapshot.py`'s per-nation research contribution now does too (was a bug —
it counted the cracked-down France CPs). C17's CP-load already excludes them.

## C21 (2026-07-20) — Nation before/after: show the COMPLETE scorecard, then PROJECT the recovery

When reporting how a nation changed (annexation, federation, war, crackdown), present the FULL
before/after — never cherry-pick rows (the player WILL notice missing numbers). `nation_report.py
<nation> before after` emits the complete diff; show all of it, grouped and in the player's income
unit (P17, /mo by default):

- **Scale:** GDP, Population, Regions, Economy score (IP base)
- **Outcomes (incomes /mo):** Research, Funding, Mission Control, Boost, Available IP
- **Basic (society/health):** Cohesion + **Cohesion rest state**, Unrest + **Unrest rest state**,
  Education, Inequality, Sustainability, Military tech, Democracy
- **Other:** Wars, Armies, Nuclear weapons, CP slots

**Always show the REST STATES beside current cohesion/unrest** (`cohesionRestState_dailyCache`,
`unrestRestState_dailyCache`; now in `nation_report`) — they tell you whether the value recovers or
decays and to what ceiling. Annexation LOWERS the cohesion rest (bigger population/sprawl), so
recovery tops out BELOW the pre-event level; it RAISES the unrest rest, so a calm current-unrest
number can hide a structurally more fragile nation held down by suppression (Oppression /
authoritarian government). The rest state itself can still be settling a day or two after the
event — re-read a later save.

**Then IMMEDIATELY project the recovery — don't wait to be asked:**
- **Research and IP scale ~linearly with cohesion**, so at recovery ≈ `current × (cohesion_rest /
  cohesion_now)`. (2033-09 annexer: cohesion 2.27 → rest 3.76 ⇒ ×1.66 ⇒ research ~1,250 → **~2,050/mo**,
  IP 41 → **~68/mo**. The IP figure is the extract's own model; treat research as an estimate ±~20%.)
- **Timeframe:** estimate from the observed cross-save cohesion-recovery RATE against the gap
  (2033-09: ~+0.3/mo vs a 1.49 gap ⇒ ~4–6 months). The **Annexation penalty decays** (may speed the
  early part); **Unity pips** on the nation add current cohesion directly and shorten it.
- Label every projection an ESTIMATE with error bars; refine as more saves arrive.

Ties to C18 (additivity + unrest-spike mechanic), C19 (IP = economyScore × cohesion/unrest terms),
C20 (full vs partial transfer + the rump's Funding/crackdown). Income units per P17.
