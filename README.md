# The Seventh Councilor

*Ground truth for Terra Invicta — an AI analyst seat for your council.*

Your council seats six. This is the seventh: an AI-assisted analysis toolkit for
[Terra Invicta](https://store.steampowered.com/app/1176470/Terra_Invicta/) players.
Point [Claude Code](https://claude.com/claude-code) (or any capable coding agent) at this repo, hand it your
save file, and ask things like:

- *"Analyze my save — how am I doing?"*
- *"Which mines should I power down to get under my Mission Control cap?"*
- *"Suggest a fleet composition to assault this alien station."*
- *"Help me design a ship around this drive."*
- *"Which global tech should I pick next?"*
- *"Why did my country lose cohesion?"*

Everything here grew out of one very long, very instrumented Resistance campaign: dozens of
battle-tested Python analyzers that read your save directly, code-verified mechanics notes
(researched from the game's actual logic, not folklore), strategy doctrine, and a hard-won
"lessons" library that teaches the AI to avoid the mistakes it already made once.

## What's inside

| Path | What it is |
|---|---|
| `CLAUDE.md` | The master runbook — Claude Code reads this automatically and learns how to analyze your saves |
| `scripts/` | Python analyzers: full save snapshot, research income, ship optimizer, mine/MC planners, transfer ETAs, colony planner, assault recon, and more |
| `docs/lessons/` | The lessons library — verified formulas, save-file semantics, and mistakes-not-to-repeat, by domain |
| `docs/mechanics/` | Code-verified mechanics deep-dives (combat math, victory conditions, hate model, economy) |
| `docs/strategy/` | Strategy doctrine (research sequencing, fleet doctrine, hate management, endgame) |
| `docs/tech-analysis.md` | Curated analysis of notable techs and projects |
| `docs/examples.md` | **What can I ask?** — the canonical list of tasks and example questions |
| `docs/getting-started.md` | **Never used GitHub or an AI coding tool?** Start here — includes a no-AI route |
| `docs/faq.md` | Is it cheating? Does it cost money? Does my save get uploaded? Mods? Five answers |
| `docs/setup.md` | First-run setup: locating saves, syncing game data from your install |
| `docs/reaching-walled-sources.md` | Verifying a mechanic against the wiki: its MediaWiki `api.php`, Wayback, and what to do when a source is unreachable |
| `campaign/` | **Your** private workspace (gitignored): campaign log, doctrine, ship designs, local lessons — see its README |
| `.claude/skills/ti-save-analyzer/` | Claude Code skill packaging for the save analyzer |

## Quick start

1. Clone this repo and open it in Claude Code.
2. Say: *"set me up"* — Claude detects your faction and campaign settings from your newest
   save, writes your config, and mirrors your install's game templates locally (this repo
   does **not** redistribute game data; it reads yours).
3. Ask: *"analyze my newest save."* — then anything in [docs/examples.md](docs/examples.md).

**New to GitHub or to AI coding tools?** Start with
[docs/getting-started.md](docs/getting-started.md) — step by step, no prior knowledge assumed,
including a no-AI route. Common questions: [docs/faq.md](docs/faq.md).

Working without an agent? The manual setup is three commands — see `docs/setup.md`.

**Hit a wrong number, or want an analyzer that doesn't exist?** You can fix it yourself — your
agent does most of the work. See [Contributing](#contributing) below.

## Requirements

- Terra Invicta (any platform; save paths auto-detected for Windows, macOS/CrossOver, Linux/Proton)
- Python 3.10+
- Claude Code or another agent harness (the scripts also work standalone from the CLI)

## What this repo does NOT contain

- **No game data.** Templates and localization are mirrored from *your* install at setup time
  (`scripts/sync_game_data.py`) and are gitignored. All rights to Terra Invicta and its data
  belong to Pavonis Interactive and Hooded Horse.
- **No spoiler policy violations.** The analyzers deliberately redact information the save
  contains but the game hides from you (unsurveyed site yields, un-scanned alien internals,
  rival internals beyond your intel level). Analysis, not cheating.

## Provenance and calibration

Formulas here are verified against decompiled game code and calibrated against in-game
tooltips (ship wet mass typically within ~1 t, combat acceleration within 0.04 g, research
income within ~0.1%). Mechanics claims cite their verification method. When the game updates,
re-verify: `docs/setup.md` § Patch drift.

It is still all reverse-engineered, so some of it is wrong — which brings us to:

## Contributing

**Pull requests, please.** And you don't have to be a Python developer to send one: this repo
teaches your agent its own conventions the moment you open it — the tool inventory, the
formulas, the house rules — so fixing something is mostly the agent's job. Yours is to
describe the problem and review what comes back.

If a number disagrees with your tooltip, don't file a ticket and wait on me. Open the folder
in Claude Code, say *"this number is wrong, here's what the game says, find out why and fix
it,"* and send the PR. Same for a missing analyzer: thirty minutes with your agent is the
fastest path to having it — and then everyone else has it too.

Highest-value PRs: formulas that drifted after a patch, analyzers that don't exist yet,
existing reports missing a column, and lessons from your own campaign that disprove something
here. I'd rather merge an imperfect PR than have the fix not exist.

Conventions, the evidence standard for mechanics changes, and what to do if you genuinely
can't fix it yourself: [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE). Created by Ihar Mahaniok ([@mahaniok](https://github.com/mahaniok)).
Terra Invicta © Pavonis Interactive / Hooded Horse; this is an unofficial fan project, not
affiliated with or endorsed by either company — see [NOTICE](NOTICE).
