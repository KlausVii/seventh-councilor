---
title: Research Sequencing
game_version: 1.0.32 (build 22085164)
---

# Research Sequencing

> **What this note is:** the campaign-independent *method* for driving a live research queue —
> how to allocate the six slots and their weights, pre-plan the openings, and write invalidation
> conditions. It is the "how to sequence" companion to the "what to skip" verdict in
> [Research Skips](Research%20Skips.md) and the slot-discipline verdict in
> [Converting a Research Lead](Converting%20a%20Research%20Lead.md). It ranks nothing for you —
> every sequence is derived against *your* save, from *your* victory path.

Terra Invicta gives you six concurrent research slots (three global-tech, three faction-project)
each carrying a 1–3 weight that splits your RP. Sequencing is the recurring decision of which
lanes to run, at what weight, and what fills each slot the moment it frees. The method below is
stable across campaigns; the answers never are.

## The method

1. **Read the UI as ground truth.** In-game progress bars, weights (pips), and completion dates
   override every extractor estimate. **Active-lane ETAs in particular cannot be reconstructed
   from template cost alone** — a weighted lane's rate depends on your live RP income and its
   pip share, not its sticker RP, so `extract_snapshot.py` deliberately suppresses active-lane
   ETAs until you've read the UI completion date (a template-cost estimate once read ~48 months
   for a lane the game showed at 3.5). Two more UI-authority traps: a freshly saved JSON can
   show *pre-reweight* pips (the screenshot is the current authority), and visible MC slack
   misleads while idle yards / off mines / under-construction modules are staged under the cap.
2. **Identify the binding lanes.** Find the one or two techs/projects that gate your victory
   chain or your current hard constraint (MC, drive tier, a fissile gate) and weight those at 3.
   Everything else competes for what's left.
3. **Let short lanes finish at weight 1.** A lane already landing soon needs no extra pips —
   spending them there just starves a binding lane. Weight buys *time-to-completion*, and only
   where completion timing changes a decision.
4. **Pre-plan every slot that will open, with scenario logic.** For each lane about to finish,
   write the next pick *and* its "if X is still running, use short filler Y" branch, so a
   completion never idles a slot or grabs a default. Bar named high-value picks (the victory
   gate, a drive spine) from being displaced by opportunistic weapon/utility techs.
5. **Write tripwires** (see below).
6. **Re-derive on every snapshot.** No sequence survives a new save unexamined — a completion,
   a re-weight, or a project appearing invalidates the plan. Bank each worked snapshot in your
   own `campaign/reports/` so the next session sees what you decided and why.

## Rules that govern sequencing

- **Globals can't be swapped mid-slot** without losing the sunk progress — so a global-slot
  commitment is heavier than a project-slot one; choose it as if it were irreversible for its
  duration (LESSONS-research R1).
- **Same-category concurrency is penalized ×0.9** per extra same-category slot — running two
  Energy globals (or two Xenology projects) at once taxes the category bonus. Stagger
  same-category lanes, and never run a side project in the victory lane's category unless an
  active emergency forces it ([Converting a Research Lead](Converting%20a%20Research%20Lead.md),
  LESSONS-research R16).
- **Every global you finish is handed to *all* factions** the moment it completes — global
  research is shared. Weigh what a pick gives your rivals, not only what it gives you: a global
  that opens nation-breakup projects, or unlocks STO fighters / outer-system expansion for
  everyone, can be a net negative even when its own effect helps you. Score it on the *net*
  transfer (same reasoning as the shared-effect caveat in
  [`docs/tech-analysis.md`](../tech-analysis.md)). Faction projects carry no such externality —
  they're yours alone.
- **A project isn't yours until it's rolled available** — "prereqs met" ≠ slotable, so never
  hard-gate a sequence on an un-rolled project; keep a filler ready (LESSONS-research R11).

## Tripwires

The plan is a hypothesis; tripwires are the pre-committed conditions that falsify it and the
response you'll take when they do. Write them *before* you need them, phrased as observable
numbers so a later session (or you) can check them mechanically:

- **A binding-lane ETA drifting** past its target while its constraint still binds → restore its
  weight by cutting the lowest-value active lane first (name which one now).
- **MC slack collapsing** below a floor after pending modules land, or any deficit → power down
  the lowest-value active mines before starting new modules (`mine_shutdown_advisor.py`).
- **A gate resolving** (a drive/fissile prereq completing) → re-cost the operation it unlocks
  against your actual stock; branch to the hedge if the numbers don't clear.
- **A hard date** by which a linchpin must exist → the fallback you commit to instead of waiting
  for the perfect version.

A tripwire without a named response is just anxiety — always pair the condition with the move.

## Sources

- Slot discipline and the ×0.9 no-Versatility finding: [Converting a Research Lead](Converting%20a%20Research%20Lead.md)
- What's safe to skip toward victory: [Research Skips](Research%20Skips.md)
- The scoring protocol every pick runs through: `docs/lessons/LESSONS-research.md`
- A fully worked application of this method lives per-campaign in `campaign/reports/`
  (gitignored) — generate your own with each queue decision.
