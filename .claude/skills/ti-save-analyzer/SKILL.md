---
name: ti-save-analyzer
description: >
  Extract a complete strategic snapshot from a Terra Invicta save file (.json/.gz). Use
  whenever the user asks about *anything* in their game — research status, military balance
  vs the aliens, nation/CP control, hab modules and Mission Control infrastructure, resource
  buffers, victory chain progress, ship design, or full critique of their position. The
  bundled extractor reads the save in one pass and produces a single markdown report — DO
  NOT write ad-hoc Python to pull individual fields. Trigger on: "save file", "analyze my
  game", "what should I research/build/do", "critique my run", "what am I researching",
  "tech tree status", "available projects", "missed projects", "fleet status", "MC
  capacity", "nation control", "ship design", "which mines".
---

# Terra Invicta save-file analyzer

This skill is a thin entry point. The full operating runbook is the repo's `CLAUDE.md`
(two levels up from this file); the domain rules live in `docs/lessons/`. Read `CLAUDE.md`
first if this session hasn't already loaded it.

Core loop:

1. **Setup check** — `config.json` and `scripts/templates/` must exist; otherwise ask ONE
   question ("set up from your most recent save?") and run
   `python3 scripts/setup_campaign.py` — it auto-detects faction and campaign settings from
   the save. Never recite shell commands or ask for save-derivable facts (CLAUDE.md § First
   run).
2. **First pass** — `python3 scripts/extract_snapshot.py --newest` (or a specific save path).
   Its report answers most questions directly.
3. **Domain deep-dive** — pick the specialist script from the inventory in `CLAUDE.md`
   (ship design → `warship_optimizer.py`, mines/MC → `mine_completion_timeline.py` /
   `mine_shutdown_advisor.py`, research income → `research_income.py`, ETAs →
   `transfer_eta.py`, …) and read the matching `docs/lessons/LESSONS-*.md` before
   interpreting output.
4. **No spoilers** — redact information the game hides from the player (unsurveyed site
   yields, un-scanned alien internals, rival intel beyond level). Rules in `CLAUDE.md`.
5. **Ground truth** — the save and in-game tooltips outrank every reconstruction, including
   yours. If the user reports a discrepancy, verify instead of defending.
