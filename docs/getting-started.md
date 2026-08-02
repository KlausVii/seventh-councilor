# Getting started

For players who have never used GitHub, never used an AI coding tool, and would rather not
learn. You do not need a GitHub account, and you do not need to know what "git" is.

Pick one of the two paths below. **Path A is the one you want** unless you specifically don't
want to use an AI assistant.

---

## Path A — with an AI assistant (recommended, ~10 minutes)

### 1. Install Claude Code

Go to **[claude.com/claude-code](https://claude.com/claude-code)** and follow the install
instructions for your computer.

If you're not comfortable in a terminal, install the **desktop app** — it's a normal
application window where you type in plain English, and it's much friendlier than the
command-line version. Everything below works the same in either one.

Claude Code needs a paid Anthropic account. If you'd rather not pay for one, skip to Path B —
the tools still work, you just drive them yourself.

### 2. Ask it to set everything up

Open Claude Code and paste this, exactly as written:

> Clone https://github.com/mahaniok/seventh-councilor into a new folder, open that folder,
> and set it up from my newest Terra Invicta save. If I'm missing anything I need to install
> first, like Python, tell me how to install it before you continue.

That's the whole installation. It will download the repo, check what your computer is
missing, find your Terra Invicta saves on its own, detect your faction and campaign settings,
and copy the game's data files out of your own install.

If it can't find your saves or your game folder, it will ask — the usual locations are listed
at the bottom of [setup.md](setup.md) if you need to paste one in.

### 3. Ask it something

Try these, in plain English, exactly like you'd ask a person:

- *"Analyze my newest save. How am I doing?"*
- *"What should I click on my bases right now?"*
- *"Which mines should I power down to get under my Mission Control cap?"*
- *"Which asteroid should I send my fleet to?"*
- *"Why did my country lose cohesion?"*

Then browse [examples.md](examples.md) for the full catalog of what it can answer.

### 4. Next time you play

You don't repeat any of this. Open the folder in Claude Code again and ask your question — it
picks up your newest save automatically. Re-run the setup only after a Terra Invicta patch, or
if you turn mods on or off.

**Using ChatGPT Codex or another coding agent instead?** Same thing. Point it at the folder;
it reads `AGENTS.md` and learns the toolkit the same way.

---

## Path B — no AI, just the tools (~5 minutes)

Every analyzer is an ordinary program you can run yourself. You'll need to use a terminal, but
only to type the four commands below.

### 1. Download the repo

Go to **[github.com/mahaniok/seventh-councilor](https://github.com/mahaniok/seventh-councilor)**,
click the green **`Code`** button near the top right, and choose **Download ZIP**. Unzip it
somewhere you'll find again — your Documents folder is fine. No account needed.

### 2. Install Python

You need **Python 3.10 or newer**. Get it from [python.org/downloads](https://www.python.org/downloads/).

On Windows, tick **"Add Python to PATH"** in the installer — it's a checkbox on the first
screen and it's easy to miss.

macOS and most Linux systems already have it. To check, open a terminal and run
`python3 --version`.

### 3. Open a terminal in the folder

- **Windows** — open the unzipped folder in File Explorer, click the address bar, type `cmd`,
  press Enter.
- **macOS** — right-click the folder, then *Services → New Terminal at Folder*.
- **Linux** — right-click inside the folder, *Open Terminal Here*.

### 4. Set up and run

```bash
python3 scripts/setup_campaign.py
python3 scripts/extract_snapshot.py --newest --brief
```

The first command finds your saves and game install and configures everything. The second
prints a summary of your latest save — if you see it, you're working.

From there, every tool runs the same way:

```bash
python3 scripts/base_fix_audit.py           # what to click on your bases
python3 scripts/cc_upgrade_planner.py       # which Ops Center to upgrade next
python3 scripts/mine_shutdown_advisor.py    # which mines to power down
python3 scripts/<any-script>.py --help      # what a tool does and its options
```

The full list of tools is in the table in [`CLAUDE.md`](../CLAUDE.md).

---

## If something goes wrong

- **"python3 is not recognized"** (Windows) — Python isn't on your PATH. Re-run the Python
  installer, choose *Modify*, and make sure "Add Python to PATH" is ticked. Or try `py`
  instead of `python3`.
- **"It can't find my saves."** Open `config.json` and set `save_dir` to your saves folder —
  the usual locations per platform are at the bottom of [setup.md](setup.md).
- **"The numbers look wrong after a game update."** Re-run `python3 scripts/sync_game_data.py`.
  See [setup.md](setup.md) § Patch drift.
- **Still stuck?** Open an issue on the repo and say what you ran and what you saw.
