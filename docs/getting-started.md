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

### 2. Decide what it's allowed to touch — do this before anything else

An AI coding agent isn't a normal program. It can read and write files and run commands, it
doesn't do exactly the same thing every time, and it works by sending what it reads to a
company's servers. That's true of every agent, not just this project — but if this is your
first one, decide the boundaries now rather than after.

Three things, in order of how much they actually protect you:

1. **Give it its own folder.** When it asks where to put the repo, choose a fresh empty folder
   — `Documents/seventh-councilor` is fine. Don't start the agent in your home directory, your
   Desktop, or anywhere with unrelated personal files. What it can see is mostly decided by
   where you start it.
2. **Leave the permission prompts on.** Agents offer a mode that auto-approves every action
   without asking — variously "accept edits", "auto-approve", "YOLO mode". Leave it **off** and
   read what it proposes. This is the control that catches a misunderstood instruction before
   it runs, and it costs you a few clicks.
3. **If you want real isolation, use a VM or container.** A `Dockerfile` is included for the
   analyzers — see [SECURITY.md](../SECURITY.md). This is the strongest option and also the
   most work; the folder choice and the permission prompts are enough for most people.

One thing that gets suggested a lot and isn't a real safeguard: *asking the agent to restrict
itself.* Telling it "don't touch anything outside this folder" is a request, not a boundary —
the same non-determinism that makes it useful means it can't be trusted to police itself. Use
the folder you start it in, the permission prompts, and the VM. Those are enforced; a polite
instruction isn't.

Full breakdown of what the scripts do versus what the agent does, with commands to verify it
yourself: [SECURITY.md](../SECURITY.md).

### 3. Ask it to set everything up

In the folder you chose, paste this, exactly as written:

> Clone https://github.com/mahaniok/seventh-councilor into this folder and set it up from my
> newest Terra Invicta save. Work only inside this folder. If I need to install something
> first, like Python, tell me what and why, and wait for me to say yes before installing
> anything.

That's the whole installation. It will download the repo, tell you what your computer is
missing, find your Terra Invicta saves, detect your faction and campaign settings, and copy
the game's data files out of your own install.

If it can't find your saves or your game folder, it will ask — the usual locations are listed
at the bottom of [setup.md](setup.md) if you need to paste one in.

### 4. Ask it something

Try these, in plain English, exactly like you'd ask a person:

- *"Analyze my newest save. How am I doing?"*
- *"What should I click on my bases right now?"*
- *"Which mines should I power down to get under my Mission Control cap?"*
- *"Which asteroid should I send my fleet to?"*
- *"Why did my country lose cohesion?"*

Then browse [examples.md](examples.md) for the full catalog of what it can answer.

### 5. Next time you play

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
