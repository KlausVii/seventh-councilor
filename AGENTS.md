# Agent instructions — The Seventh Councilor

**Read [`CLAUDE.md`](CLAUDE.md) first and follow it in full.** It is the master runbook for
this repo: the script inventory, the lessons library map, the setup flow, the spoiler policy,
and the hard rules. This file exists so agents that look for `AGENTS.md` (OpenAI Codex and
others) find their way there; `CLAUDE.md` is the single source of truth and this file is
deliberately thin so the two can't drift apart.

The repo was developed against Claude Code, but nothing in it is Claude-specific — the
analyzers are plain Python 3.10+ CLIs and the guidance is plain markdown. Any agent that can
read files and run commands can use it.

## The short version, if you read nothing else

1. **The save file and in-game tooltips are ground truth.** Every reconstruction is a
   hypothesis. When the player says the game disagrees with you, stop defending and verify.
2. **Run the existing script before deriving anything yourself.** The inventory is in
   `CLAUDE.md`. Saves are 60–90 MB — never walk one ad-hoc when a script already extracts the
   field. If a script's report is missing something, fix the script rather than writing
   one-off code.
3. **Read the relevant `docs/lessons/` file before working in its domain** (research, ships,
   economy, politics, aliens, process). They encode mistakes already made once.
4. **Don't spoil.** The save contains information the game hides from the player — unsurveyed
   site yields, un-scanned alien ship internals, rival internals above the player's intel
   level, undetected alien sites. Redact it and say that you are redacting.
5. **Everything here is read-only analysis except `scripts/ti_war_editor.py`**, which mutates
   the save and runs only when the player explicitly asks for it.

## First run

If `config.json` doesn't exist, the repo isn't set up. Ask one question — "should I set things
up from your most recent save?" — and on yes run `python3 scripts/setup_campaign.py`, which
detects faction and campaign settings from the newest save and mirrors game data from the
player's install. Full details, including the manual fallback, are in `CLAUDE.md` and
`docs/setup.md`.
