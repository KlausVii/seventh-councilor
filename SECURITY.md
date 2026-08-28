# Security and privacy

Two different things get installed when you follow the quick start, and they carry very
different risk. Worth separating them before you decide.

1. **This repo** — ~40 Python scripts that read your save file.
2. **An AI coding agent** (Claude Code, Codex, …) that runs them for you.

Most of the risk is in (2), and it isn't specific to this project. If you'd rather not accept
it, **Path B in [docs/getting-started.md](docs/getting-started.md) runs everything with no
agent at all** — that's a supported way to use this, not a fallback.

## What the scripts themselves do

Counts below are for the 43 files in `scripts/`, and you can verify every one yourself in a
few seconds — see [Audit it yourself](#audit-it-yourself).

| | Count | Which |
|---|---|---|
| **Read-only and fully offline** | **35 of 43** | every save analyzer, plus the `tic.py` dispatcher that runs them |
| Make any network call | **1** | `fetch_ladder.py` — fetches wiki/forum pages when researching a mechanic. Not part of save analysis |
| Use `subprocess` | **1** | same file |
| Write anything | **7** | `extract_snapshot.py`, `save_trajectory.py` (report output) · `generate_vault.py`, `generate_modules.py` (`generated/` pages) · `setup_campaign.py` (`config.json`) · `sync_game_data.py` (copies game templates *from* your install) · `ti_war_editor.py` (see below) |

Also true, and relevant:

- **No third-party dependencies.** Standard library only, no `requirements.txt`, no install
  step. There is no package supply chain to compromise.
- **No telemetry.** Nothing reports usage, and nothing uploads your save.
- **One tool modifies a save:** `ti_war_editor.py`, which adds belligerents to an existing
  war. It runs only when you explicitly ask, never as a side effect of a question. It writes a
  timestamped backup first, re-parses and validates the result before replacing the file, and
  aborts leaving your original untouched if validation fails.

## What the agent does — the real risk

An AI coding agent has whatever access you grant it, which by default includes reading and
writing files and running commands. That is the agent's permission model, not something this
repo adds or can take away. It's worth being clear-eyed about:

- **It's non-deterministic.** It will sometimes do something you didn't intend. Ordinary
  applications repeat the same behavior; agents don't.
- **File operations can go wrong.** An instruction you meant one way can be read another.
- **Conversation content goes to the AI provider.** Your save file is never uploaded wholesale
  — the analyzers read it locally and print results — but what those tools *print* becomes
  part of the conversation, like anything else you type into a chat.

None of that is unique to this project; it applies to every agent workflow. It matters more
here than in a developer's terminal because this repo actively invites non-technical players
to run an agent, possibly for the first time.

## Running it safely

Pick the level you're comfortable with:

- **Most cautious — no agent.** Run the scripts directly. No agent, no API key, no account:
  Path B in [docs/getting-started.md](docs/getting-started.md).
- **Isolate it.** A VM or container, or a separate user account. Several people run it this
  way and it's a reasonable default if you're at all unsure.
- **Don't blanket-approve.** Agents offer modes that auto-accept every action. Leave that off
  and read what it's about to do. Point it at a folder containing this repo, not your home
  directory.
- **Back up a save before any edit.** Only `ti_war_editor.py` writes to saves, and it backs up
  on its own, but Terra Invicta's own saves are cheap to copy and there's no reason not to.

## Running it in a container

A `Dockerfile` is included for running the analyzers isolated. It builds an image with no
dependencies — the analyzers are standard-library only, so there is no `pip install` step and
nothing is fetched at build time beyond the base image.

```bash
docker build -t seventh-councilor .

docker run --rm -it \
  --network none \
  -v "$PWD:/app" \
  -v "/path/to/TerraInvicta/Saves:/saves:ro" \
  -v "/path/to/Terra Invicta:/game:ro" \
  --user "$(id -u):$(id -g)" \
  seventh-councilor
```

What each flag buys you:

- **`--network none`** — the container has no network at all. Worth noting this *works*: the
  save analyzers never make a network call, so nothing breaks. (The one exception is
  `fetch_ladder.py`, which fetches wiki pages when researching a mechanic — drop the flag if
  you want that, and only then.)
- **`:ro` on `/saves` and `/game`** — read-only. The container cannot modify your saves or your
  game install, regardless of what runs inside it.
- **`-v "$PWD:/app"`** — your checkout, so `config.json` and the mirrored templates persist
  between runs instead of vanishing with the container.
- **`--user "$(id -u):$(id -g)"`** — files the container writes into your checkout stay owned
  by you.

Then point the config at the mounted paths, in `config.json`:

```json
{ "save_dir": "/saves", "game_install_dir": "/game" }
```

and run the tools as normal — `python3 scripts/setup_campaign.py`, then
`python3 scripts/extract_snapshot.py --newest --brief`, and so on.

**What this does and doesn't cover.** It isolates the *scripts*, which were the smaller half of
the risk to begin with. It does not containerize an AI agent — that's a harder problem (the
agent needs credentials, network, and a writable workspace, which gives back much of what the
container took away), and pretending otherwise would be worse than not shipping it. If you want
the agent isolated too, a VM is the honest answer today. Ideas and PRs welcome.

## Audit it yourself

The claims above are greppable. From the repo root:

```bash
# Everything that touches the network or shells out — expect exactly one file
grep -rnE "urllib|socket|requests|http\.client|import subprocess" scripts/*.py

# Everything that writes, deletes, or moves a file — expect the seven listed above
grep -rlE "open\([^)]*['\"][wa]|shutil\.(copy|move|rmtree)|os\.(remove|unlink|rename)|\.write_text\(" scripts/*.py

# Third-party imports — expect none
grep -rhoE "^\s*(import|from) [a-zA-Z0-9_]+" scripts/*.py | awk '{print $2}' | sort -u
```

Or run the test suite — `tests/run_all.py` asserts the three claims above structurally
(via the Python AST, so a docstring can't false-positive a grep) and fails if any script
grows a network call, a third-party import, or an undocumented file write:

```bash
python3 tests/run_all.py
```

It needs no save, no game data, and no network, and finishes in a few seconds.

Reviews are genuinely welcome, and so are hardening PRs — see
[CONTRIBUTING.md](CONTRIBUTING.md).

## Reporting a problem

If you find something that behaves worse than described here, open an issue. If you think it's
sensitive, use GitHub's private vulnerability reporting on this repo instead of a public issue.
