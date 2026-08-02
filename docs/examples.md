# What can I ask?

The canonical list of tasks this repo equips your AI assistant to do. Phrasings are
examples — ask naturally; the assistant picks the right tool. (Parenthetical notes show
what runs under the hood, in case you want the CLI directly.)

**Curation rule:** list ONLY tasks where the assistant adds value the game UI doesn't —
cross-save trends, cross-hab/faction aggregation, formulas and reconstructions, spoiler-safe
reads of hidden data, or ranked recommendations. Do NOT add single-glance UI facts (a number
in a tooltip, why a button is greyed, a panel stat) — no one opens an AI for those. A new
tool/lesson does not automatically earn an example; it earns one only if a player would
plausibly ask an assistant instead of just looking.

## Getting started

- "Set me up." — one-time; everything is detected from your newest save (`setup_campaign.py`)
- "Analyze my newest save. How am I doing?" (`extract_snapshot.py`)
- "Give me a full strategic review — map my path to victory and what to do over the next few months." (the whole toolkit in sequence: `extract_snapshot.py` for state → research ranking → `ops_query.py` for the military picture → victory-chain + `base_siege_calc.py`/`assault_planner.py` for the endgame → synthesized, prioritized orders with tripwires. Read `campaign/doctrine.md` first so it fits how you play.)
- "Compare my position now vs three months ago." (`extract_snapshot.py` on two saves; `lifesupport.py --diff`)
- "Explain how X actually works." (mechanic decode from `docs/mechanics/` + the decompiled source — e.g. how bombardment interception, the hate floor, or a shaped-nuclear warhead works; grounded in code, not lore)
- "What changed since the last patch? Re-sync my game data." (`sync_game_data.py` drift report)

## Research

- "Which global tech should I pick next?" (`global_tech_tree_walk.py` + the research-scoring protocol in LESSONS-research)
- "I just finished a tech — rank EVERYTHING on my global menu, with a slot plan." (full-menu sweep: tree walk per tech, tier scores, a slot sequence that respects the same-category ×0.9 stacking penalty (R16) and your current slot weights, plus re-weight advice when a spine tech is starving at low weight)
- "Rank my available faction projects."
- "What projects am I missing, and which milestones gate them?"
- "How much research am I actually making, and from where?" (`research_income.py` — decomposition to ~0.1%)
- "How do I widen my research lead over the other factions?" (`research_income.py --all-factions`)
- "Who is winning the race on each global tech — who picks what's queued next?" (`tech_contributions.py`)
- "How did that faction gain 7,000 points on one tech in two days?!" (`tech_contributions.py` across daily saves — flags the windfall and names the mechanic from their spend ledger; see LESSONS-research R24 on Steal Project)
- "What drive upgrades could I research soon, and are they worth it?" (`drive_upgrade_finder.py`)
- "An alien fleet is inbound — what exactly should I build to beat it?" (`counter_fleet_planner.py --fleet "<name>"` — decomposes their armament into missiles/torpedoes (any PD hit kills → size PD Ion by launch rate), kinetic slugs (only the 40mm autocannon engages them → size by kg/s of inbound slug mass) and beams (uninterceptable → armor), then gives per-hull mount counts — LESSONS-ships S26)
- "Which drive is actually FASTEST for my freighters/couriers — Earth→Ceres, Callisto→Pluto?" (`drive_eta_compare.py` — ranks drives by real transit TIME, not EV; the EV order reverses because short legs are accel-limited (thrust wins) and long legs are ΔV-limited (EV wins) — LESSONS-ships S23)
- "Will researching fusion get me better warship drives?" (mostly not soon: first-gen fusion lanterns don't beat Lodestar's combat thrust — early fusion buys EV/REACH for couriers/haulers, and Deuterium-Tritium Fusion is a reactor + economy tech, not a near-term drive upgrade; the combat jump is deep. Score fusion globals as reactor+drive PAIRS on three axes — LESSONS-research R2/R20, LESSONS-ships S1/S20)
- "Which fusion ladder do I invest in — ICF, Tokamak, Z-Pinch, or Hybrid? What reactor+drive pair actually comes out, and what are the odds?" (`fusion_ladder_planner.py` — one row per pair: per-mass thrust, per-hull thrust, unlock-lottery flags, He3 dependence, per-tank propellant units, remaining RP vs YOUR save; a cheap second ladder is insurance against a 25%-never linchpin drive)
- "The game just offered me this reactor/drive project — is it worth it?" (score it as a reactor+drive PAIR, not the drive alone — `fusion_ladder_planner.py` for the three axes + `drive_eta_compare.py` for what it actually buys on your routes; early fusion usually buys reach, not combat — LESSONS-research R20, LESSONS-ships S1/S20)
- "I'm partway through a drive/reactor project — finish it, or pivot to what's coming?" (weigh sunk progress against unlock-lottery odds, the propellant tail, and refit-family reach together — `fusion_ladder_planner.py` + `drive_eta_compare.py`; and re-audit any standing 'invest in ladder X' advice the moment a lottery drive actually rolls or your victory chain closes — insurance stops being worth its premiums once the risk it covered is gone — LESSONS-research R27)
- "Is the new gun family worth switching to, or is it a downgrade from what my fleet already mounts?" (mount-for-mount family comparison from the generated Ship Modules tables — full salvo-cycle DPS, never bare cooldowns (R18 salvo trap), muzzle velocity, range, PD survivability per docs/strategy/Weapon Doctrine vs the Hydra; the classic trap is a shiny Mk1 that loses to your deployed Mk3 — LESSONS-research R14)
- "I read online that X beats Y — is that true in my game?" (claim-by-claim template verification; community posts often predate balance patches or mix up mount classes. Steam threads are tiebreakers, never canon)
- "Is this tech safe to skip this run?" (docs/strategy/Research Skips + tech-analysis)
- "A new project just popped up — should I research it?" (template pull + same-tier comparison + the scoring protocol; never scored from the name alone)
- "What's the full research path and cost to get weapon/drive X?" (`global_tech_tree_walk.py --projects` — prereq-closure costing, globals and projects separated)
- "When will this pending project actually appear? What are its odds?" (`factionAvailableChance` / unlock-roll ramps — some projects are lifetime lotteries; LESSONS-research R11)
- "My project menu is cluttered — which projects should I mark obsolete, and which only LOOK dead?" (scoring protocol + downstream-gate and faction-lock checks, LESSONS-research R21 — a gate whose payoff belongs to another faction gates nothing for you)
- "How should I spend my limited exotics stockpile — armor, heat sinks, or radiators?" (module `weightedBuildMaterials` exotics fractions + docs/strategy/Exotics and Antimatter Acquisition)
- "Re-check that ranking you gave me — is it still valid?" (every reused score gets a newer-lessons sweep; a lesson written after an analysis can invalidate its score outright — LESSONS-research R26)
- "Is this hab/core unlock worth researching, or does it build something I'll never found?" (tier-ceiling check: `upgradesFromName` chains — automated cores are permanent T1 dead ends — LESSONS-research R25)

## Economy, Mission Control, mining

- **"What should I click on my bases right now?"** (`base_fix_audit.py` — THE recurring hab-turn report in one save pass: unpowered modules worth flipping (boost-free first, E37), habs with no OpsCenter/CommandCenter split into in-flight vs real gaps, OC→CC ranked by BUILD TIME and gated on power, mine tier upgrades (0 MC) vs new mines (quadratic margin). Run this before the individual tools)
- "Which OC→CC upgrade should I start?" (`cc_upgrade_planner.py` — ranked by build TIME because the OpsCenter is dark for the whole build, so the real price is `days × 4` MC-days; `--sort metals` for a metals-constrained save. Power-gated: a CC draws 300 vs the OpsCenter's 100 — LESSONS-economy E28/E34)
- "Should I build a new mine or upgrade one?" (`mine_upgrade_planner.py` — almost always upgrade: mining MC is quadratic so mine n+1 costs `(active−36)²/2` at the margin while a tier upgrade replaces the module in place for **0 MC** — LESSONS-economy E38)
- "Which mines should I turn off to get under my MC cap?" (`mine_shutdown_advisor.py` — respects scarce-resource protections)
- "I'm WAY over the cap and modules are getting destroyed — get me under RIGHT NOW, protections be damned." (`mine_shutdown_advisor.py --need-mc N` — cumulative-savings ranking with a hard warning when mines alone can't close the gap, because mining MC is quadratic and caps out; the residual comes from instant hab-side levers: power ON idle Ops/Command Centers, power OFF ResearchCampuses — LESSONS-economy E29)
- "Am I really over cap, and by how much? My reconstruction says one thing, the game another." (the in-game top-bar tooltip is ground truth; the save's `missionControlUsage` is exact but reconstructed *available* over-reads — LESSONS-economy E25)
- "Water is plentiful now — pick a mine to power off that spares metals and fissiles." (`mine_shutdown_advisor.py --relax water` — scarcity-weighted, flags mines that quietly supply a big share of one resource)
- "MC slack is back — what can I power ON: mines, Ops Centers, Command Centers?" (`mine_shutdown_advisor.py --power-on` — sequences MC producers before mines, warns about the Admin-module trap)
- "When do my mines under construction finish, and what will they add?" (`mine_completion_timeline.py`, `module_completion_dates.py`)
- "Project my volatiles (or any resource) income forward — how much, and by when?" (`mine_completion_timeline.py --resource volatiles` for the gross mine wave + `lifesupport.py --resource volatiles` for the net; a completing mine adds ~FULL production because its crew life-support was already being paid while it built, so the completion wave is near-pure upside — LESSONS-economy E35)
- "Project my MC capacity over the next year — when will I reach 1,000?" (`mc_capacity_projection.py --target` — monthly capacity rollup + the crossing date)
- "Which command centers should I upgrade first?" (`cc_upgrade_planner.py` — cost-then-speed ranking: per-body radiation cost, the tier-3-core gate with core ETAs, live AND incoming build accelerators, unpowered-Ops-Center flags, stockpile pacing warning)
- "When do my Command Centers come online, and how much MC cap will they add?" (`module_completion_dates.py --module CommandCenter` — date-sorted, per-month ΔMC rollup; upgrades count the FULL new-module MC because the old module went offline at click time)
- "Which of my bases get a nanofactory soon? Start upgrades there — the bonus kicks in mid-build." (`cc_upgrade_planner.py` — the Incoming column; est-days simulates accelerators landing partway through)
- "Which mines are worth upgrading?" (`mine_upgrade_planner.py`; `--actionable` = only clicks you can make now, payback-sorted, with hab-tier readiness and an affordability tally vs your metals stockpile)
- "Rank my surface bases by mining potential — top L3 yield with all my bonuses, cost included." (`mine_upgrade_planner.py` — radiation surcharge priced per body, see docs/mechanics/Hab Build Costs and Radiation)
- "Do any of my bases have destroyed modules? Was a mine blown up and never rebuilt?" (`mine_upgrade_planner.py` — rubble slots are flagged; destroyed modules lose their template name, so a blown-up mine otherwise looks never-built)
- "Was one of my stations attacked? What did I lose, and when?" (`module_completion_dates.py --destroyed` — rubble slots with dates; same-date clusters date the attack. A module killed while still under construction vanishes from the save entirely — diff the pipeline across two saves to catch those)
- "Are any of my Ops/Command Centers sitting unpowered?" (`module_completion_dates.py --unpowered --module OperationsCenter --module CommandCenter`, or `mine_shutdown_advisor.py --power-on` for the sequenced version)
- "Do I have unpowered mines or research campuses I could power back on right now?" (`hab_power_audit.py --module Mining --module Research` — per-hab surplus with the real solar math, idle-generator capacity, POWER-ON-NOW verdicts; LESSONS-economy E34)
- "Does this base have the power headroom for that upgrade?" (`hab_power_audit.py --all` — an upgrade needs only the NET draw over the module it replaces, e.g. OC→CC = +200; docs/mechanics/Hab Power and Solar Output)
- "Why does my Solar Farm produce 543 power on Mars when it's rated 240?" (docs/mechanics/Hab Power and Solar Output — the location multiplier + solar-mirror bonus, capped at 8× rating)
- "Rank mine upgrades by MY resource values — nobles are worthless to me, fissiles are gold." (`mine_upgrade_planner.py --focus fissiles,metals` + your standing valuations recorded in `campaign/doctrine.md`, applied to the per-resource deltas)
- "Where did all my money/metals/boost go?" (`resource_flow.py` — the spend ledger)
- "Where did my water go — and which ships are drinking it?" (`resource_flow.py` — a sudden water crash is almost always FLEET RESUPPLY, not a leak: water is the universal propellant feedstock every drive refuels on (`perTankPropellantMaterials.water`, ~1 unit/tank even for "hydrogen" drives), so the culprit is operational tempo, not life support — LESSONS-economy E17/E27)
- "I'm metals-starved mid-build — how do I fix it?" (flow-allocation, not liquidity: there is NO money→resources market buy-side and ships have no cash-substitution path; prioritize queues, pause non-critical hab builds, add mine income — docs/mechanics/Economy Markets and Loot)
- "My income is positive but my stockpile keeps draining — what's eating it?" (income (a RATE: production − life-support − upkeep) and stockpile (a LEVEL) are separate axes; construction cost is an up-front lump-sum draw on the STOCKPILE and never touches the income rate — `resource_flow.py`'s NET is the stockpile change, not income — LESSONS-economy E24/E36)
- "Which shipyards should I upgrade to Spaceworks, and how do I make my builds finish faster?" (`cc_upgrade_planner.py` — the build-time speed law: powered NanofacturingComplex/Nanofactory/ConstructionModule modules cut build time; pick upgrade sites by which accelerators they already have — docs/mechanics/Hab Build Costs and Radiation)
- "Do I have a boost problem?" (`boost_analysis.py`)
- "Which Administration Towers should I power off — which are burning boost outside LEO for nothing?" (`boost_analysis.py` ranks non-LEO Towers by their real +5% Efficiency benefit and flags DEAD ones — a Tower whose hab's mine isn't producing yet multiplies ~0 income, so it's pure boost waste; an Admin module's CP-cap benefit exists ONLY in Earth LEO — LESSONS-economy E16)
- "Where can I get more fissiles (or metals/water/volatiles/nobles) — and does the site need a ship?" (`resource_site_planner.py [--resource X | all]` — ranks prospected sites by yield × distance and marks free-foundable ones "no ship" per E30)
- "How do I make more money in the late game?" (docs/strategy/Late-Game Money)

## Ship design & refits

- "Help me design a ship around this drive / for this role." (`warship_optimizer.py`)
- "Max nose armor on this hull while keeping 4 kps ΔV — what's the best allocation?"
- "Can I refit my existing cruisers to lasers, or do I need new builds?" (refit legality rules)
- "I'm metals-short — which ships should I refit to the new drive first, in priority order?" (family-legal targets first (LESSONS-ships S2), ranked by combat/role gain per metal; `warship_optimizer.py` — and a higher-power drive can drag a forced reactor-tier upgrade along with it, S21)
- "Is it worth refitting JUST the reactor on this ship?" (reactor-tier refit savings scale with the drive's power draw — big on Lodestar-class warship drives, ~nothing on Burner or self-powered NSWR drives like the Poseidon Lantern — LESSONS-ships S21)
- "The shipbuilder won't let me put this drive on my hull — why?" (a drive's `powerRequirement` must be ≤ the reactor's `maxOutput`; the new drive needs a higher reactor tier first — LESSONS-ships S21)
- "Here's a shipbuilder screenshot — calibrate the optimizer for this hull."
- "What's the right weapon mix against the aliens right now?" (docs/strategy/Weapon Doctrine vs the Hydra)
- "Is a missile swarm viable for me?" (docs/strategy/Missile Swarm Doctrine)
- "Compare armor materials for my next hull — per-ton protection, specialties, exotics cost." (`armor_calc.py`; per-mass halving indices in LESSONS-ships S12)
- "Which drive for a Kuiper courier / belt freighter? Include what the propellant costs me." (drive templates + `transfer_eta.py`; the three-axis rule — thrust, exhaust velocity, propellant — LESSONS-ships S20)
- "What drive takes my BATTLE fleet — capitals, not freighters — out to the Kuiper belt?" (`drive_eta_compare.py` on a warship hull: reach-filter FIRST — Lodestar is a ~13-year crawl to 30 AU — then judge combat-g at ARRIVAL mass, not departure (a torch fights near-dry), under the 3g rating clamp; the expedition tier is usually NEW builds, since NSWR/fusion drives can't refit onto a fission hull — LESSONS-ships S24)
- "What should go in my monitor's four missile slots?" (munition templates: warhead class, magazine/salvo, PD-penetration geometry — LESSONS-ships S18)
- "Where should I build my fleet — at the front or at home?" (resources are faction-pooled, so build location changes delivery point, threat exposure, and repair access, NOT cost — home-defense hulls where they'll fight, expeditionary hulls at the forward yards — LESSONS-economy)
- "Some ships vanished from my fleet — did I lose them, or are they refitting?" (a fleet-count drop is detach/refit/transfer until proven otherwise; refits leave the roster and return, and cost only the module delta — LESSONS-process P12)
- "Design a marine carrier / troop transport." (`warship_optimizer.py` — cram assault modules, keep cruise ΔV ≥ the slowest ship it escorts, ~1 g combat is plenty for a hull that shouldn't fight; assault math in `assault_planner.py`)

## Fleets & military operations

- **"My assault ship is fuelled and loaded — whose mine should I take?"** (`capture_target_planner.py --fleet "<name>"` — ranks every rival mining base by what the captured site would pay YOU under your own mining multipliers and scarcity weights, for any resource. Ground defence and assault odds are INTEL-GATED: below intel 0.5 the game hides the hab's modules, so those targets print `??` / "scout first" rather than a number you shouldn't have. Also shows the owner's navy and hate — a defenceless base owned by a fleet-heavy faction is a trap — and the quadratic MC the captured mine adds to your own network)
- "Give me a military sitrep." (`ops_query.py` — fleets, transits, construction, alien order of battle)
- "What's happening around Ceres?" (`ops_query.py --theater Ceres`)
- "How long until this fleet reaches Mars? Which of my fleets can get there fastest?" (`transfer_eta.py`, `--matrix`)
- "Plan an assault on this alien station." (`assault_planner.py` — defenses, marine math, local yards)
- "My bombardment did zero damage / I lost ships and barely scratched the base — what am I doing wrong?" (`base_siege_calc.py` + docs/mechanics/Orbital Bombardment — interception is a pooled ratio that 100%-blocks kinetics/nukes against a powered base; the answer is to starve the base's power: kill the reactor farms with LASERS to de-power the battlestations, from LOW orbit, on Hybrid- or Adamantane-armored hulls)
- "How do I actually crack a defended alien base?" (`base_siege_calc.py` — the reactor-farm power cascade; `armor_calc.py sizing --hull X --armor Y` for siege-hull armor sizing, which now derives t/pt and the material's point cap from the hull)
- "How long will this ship take to build? Should I use a smaller hull to field it sooner?" (build time is HULL-ONLY — `TIShipHullTemplate.baseConstructionTime_days`; trimming armor/tanks/mass buys ZERO days — LESSONS-ships S28)
- "Which armor should I use if I can't afford Hybrid?" (`armor_calc.py list` / `equiv --from … --to …` — an armor point is a material-specific THICKNESS, so cheaper points beat resistance: maxed Adamantane blocks ~3x maxed Nanotube — LESSONS-ships S12 amendment)
- "Why is my marine assault showing 0% success without bombing first?" (the base's Defending Force Strength is the sum of its powered defense modules — you can't out-roll it; flatten the defenses first, then the assault tooltip is your live gauge — docs/mechanics/Orbital Bombardment)
- "Should I attack now or keep building?" (docs/strategy/Offense Timing vs Aliens)
- "How should I defend Earth orbit?" (docs/strategy/LEO Defense Doctrine)
- "How did that faction capture my station — they don't even have a fleet?" (save forensics: rival mission history, Mission Control overage and the crew-mutiny mission — LESSONS-economy E26)
- "Get my councilor to that base fast — existing ship, recall one, or build a courier?" (`transfer_eta.py --matrix` + build-time comparison; building at the departure body often wins — LESSONS-process P9)
- "Plan a councilor-led capture of an alien station — who flies, and how do I maximize the roll?" (the Seize roll is Command-only: pick the councilor by base Command + who Earth can spare, then stack every +Command org onto them; spend Operations, bring marines, get under MC cap — crit level is the target, it pays double loot and the live-specimen milestone — LESSONS-politics C14 + LESSONS-aliens A3)
- "Which councilor should carry the winner org for the final mission — does it matter?" (barely: the win mission resolves automatically with no roll, so any holder co-located with the target wins; optimize for the Seize rolls en route instead — docs/mechanics/Victory Conditions and Endgame §5 + LESSONS-politics C14)

## Colonization & expansion

- "Where should I colonize next for volatiles?" (`colony_planner.py --resource`)
- "Which bodies can I settle without sending a ship?" (`colony_planner.py --free`)
- "What's worth prospecting in the outer system?"
- "Is it safe to colonize around Saturn?" (`colony_planner.py --max-alien` + the threat snapshot — whole moon systems share one garrison; alien-held systems are cleared, not settled)
- "What resources should I expect on this unprospected body?" (honest answer: a class-analogy guess only — the tooling refuses to read hidden yields, and in-game range priors can be badly wrong)

## Earth politics & nations

- "Why did my country lose cohesion?" (nation history arrays + LESSONS-politics)
- "Which control points should I take or drop?"
- "Two of my nations can federate — is it worth it, and what does federation actually do?" (federation ≠ merger: pooled Funding/Boost + an Economy-priority bonus + mutual defense, and the nations stay separate; it's the prerequisite to *unifying* them later, which is what actually consolidates CPs — LESSONS-politics C16)
- "Which nation leads the federation — can I pick?" (no — the lead is the member with the most claims, not a free choice; mind the Dark-Federation leave restriction if you don't hold both nations — LESSONS-politics C16)
- "How is public opinion trending in my key nations?" (`opinion_trajectory.py`)
- "Why did support for my faction suddenly crash in my anchor nation?" (`opinion_trajectory.py` step-bisection across saves + the Propaganda-caster scan — a sharp single-day drop is a rival Public Campaign, and those conversions never decay on their own; diagnosis workflow and counters in LESSONS-politics C15)
- "What should my councilors be doing this month?"
- "Which orgs should I buy for my council?"
- "Give me a full scorecard for my nation." (`nation_report.py <templateName>` — every live score plus the newest history samples; present the COMPLETE set incl. cohesion/unrest REST STATES, don't cherry-pick — LESSONS-politics C21)
- "I just conquered/annexed a nation — compare all my scores now vs right before." (`nation_report.py <nation> before after` — full before/after diff with additivity checks. **FULL** absorption (target gone) transfers everything incl. Funding and spikes unrest if the target was more democratic → research/IP drop first; **PARTIAL** annex (rump survives) transfers only the regions taken, leaves the target's Funding with the rump, and does NOT spike unrest. Show the complete scorecard + rest states, then PROJECT the recovery with `--recovery` (projects research/IP at cohesion recovery ×rest/current, plus a timing ETA from two post-event saves) — LESSONS-politics C18/C20/C21, income units P17)
- "When will that nation's research and IP recover after the crash, and to what?" (`nation_report.py <nation> <earlier-post-event> <now> --recovery` — research/IP ≈ current × rest/current cohesion, with a months-to-rest estimate from the observed cohesion rate)
- "Find me the save from right before that happened." (`nation_report.py <nation> --scan "<date-glob>" --watch <other-nation>` — one row per save; region counts bisect an annexation to the exact save pair, the same pattern C15 uses for opinion steps)
- "Why did my investment points drop by a third? Where do the penalties come from?" (the IP tooltip decomposition — base = economyScore, −unrest%, −0.5/army, −0.5/navy; and an IP number that oscillates between saves is an Advise cycle, not a change — LESSONS-politics C19/C10)
- "The game shows a different Mission Control / research number than you quoted — which is right?" (the in-game panel; same-day history samples in the save can lag an event by one tick — LESSONS-process P1/P16, LESSONS-politics C18)

## The aliens

- "How angry are the aliens, and what happens if I build 20 more mines?" (the hate model, LESSONS-aliens)
- "Can I still avoid Total War? For how long?"
- "How big is the alien fleet really, and how fast is it growing?" (`alien_progress_timeline.py` across saves)
- "Is my alien hate coming from my mission-control footprint or from my kills?" (kills — the MC-usage floor is real but usually stops binding once you've made kills; above the floor, the meter is combat history, at ~0.4 × hull SI each — LESSONS-aliens A4 + docs/mechanics/Alien Hate and Diplomacy §2/§5)
- "Do the aliens tech up like a faction — should I worry about their research?" (no — the Hydra has zero research economy; it advances on the campaign timer, not RP, so there's no tech pace to out-race — docs/mechanics/Research Mechanics § "The aliens have no research economy")
- "My alien base count dipped then recovered — which specific bases did I actually destroy?" (hab-ID diff across two saves; the net count hides churn, and re-founded bases pop up at new bodies — docs/mechanics/Alien Production Rebuilding and Targeting §2)
- "What do the AlienInv and SpaceStr columns in my hate/progress log mean?" (AlienInv = your Investigate-Alien-Activity mission counter, which also feeds the Xenology research bonus; SpaceStr = your peak space-strength share, the trigger reference for the knockdown hate-reprieve — docs/mechanics/Research Mechanics + Alien Hate and Diplomacy §4)
- "Which alien assets should I kill to lower their rebuild ceiling?" (docs/mechanics/Alien Production Rebuilding and Targeting)
- "What do I still need for my faction's victory condition?" (victory-chain status + docs/mechanics/Victory Conditions and Endgame)
- "Plan getting my victory-condition councilor to the alien home base — and not losing it in transit." (`transfer_eta.py` for the multi-year burn; carry a second qualified councilor and keep both on non-combat flee-stance hulls, and confirm the granting org is in hand before you sail — capability timing LESSONS-politics C12, endgame in docs/mechanics/Victory Conditions and Endgame)

## Campaign memory (the `campaign/` workspace)

- "Log this month's numbers." (`campaign_log_row.py`, `research_income.py` → `campaign/log.md`)
- "Remember: I never build He-3 mines this run." (→ `campaign/doctrine.md`, applied to future advice)
- "Show my campaign trends over the last year." (`save_trajectory.py`, log tables)
- "Save this analysis for later." (→ `campaign/reports/`)

## Save editing (opt-in, modifies your save)

- "Add a war between these two nations." (`ti_war_editor.py` — back up first)

## What it will NOT do

- Reveal what the game hides from you: unsurveyed site yields, un-scanned alien ship
  internals, rival intel beyond your level. The save knows; the tooling redacts.
- Invent numbers. Everything is read from your save, your game data, or code-verified
  mechanics — estimates are labeled as estimates.
