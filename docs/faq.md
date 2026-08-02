# FAQ

### 1. Is this cheating?

It's built not to be. The save file contains everything — including things the game
deliberately hides from you until you've earned them — and reporting those would be cheating,
so the analyzers redact them and tell you they're redacting. That covers hab-site yields on
bodies you haven't surveyed, alien ship internals you haven't scanned in combat, rival
councilor stats you haven't investigated, rival faction internals above your intel level, and
alien sites you haven't detected.

What's left is arithmetic over information you already have. Sorting your two hundred habs by
which upgrade pays off fastest isn't a secret — it's a spreadsheet you'd have built by hand if
you had the patience. Whether that crosses your personal line is your call, but it isn't
reading the answer key.

### 2. Do I have to pay for an AI subscription?

No. Every analyzer is a plain Python program that runs on your own machine with no AI, no
account, and no API key — `python3 scripts/base_fix_audit.py` works standalone. Path B in
[getting-started.md](getting-started.md) is the whole no-AI route.

The AI layer is what makes it pleasant rather than what makes it work: instead of learning
which of forty tools answers your question, you ask the question. That part needs a paid
assistant — Claude Code is what the repo was built and tuned against, and ChatGPT Codex works
too via `AGENTS.md`. Any capable coding agent should manage; it's Python and markdown, not a
product.

### 3. Does my save file get uploaded anywhere?

The save stays on your computer. The analyzers read it locally and print results; nothing
uploads it.

Be aware of the ordinary consequence of using any cloud AI, though: when an assistant runs a
tool for you, what that tool *printed* goes to the AI provider as part of the conversation.
So summaries of your campaign do reach them, the same as anything else you type into a chat.
Your 90 MB save file is never shipped wholesale — the toolkit is deliberately built so the
agent reads analyzer output rather than raw save data. If you'd rather nothing at all leave
your machine, use Path B.

### 4. Will it work with my version of the game? With mods?

Mods, yes — better than you'd expect. The repo ships **no** game data. At setup it copies the
templates and localization out of *your* install, so it reads whatever your game actually has,
modded or not. Re-run `python3 scripts/sync_game_data.py` after you change your mod list.

Versions are a softer yes. Anything read straight from your save or your templates tracks your
version automatically. But some constants were reverse-engineered and calibrated against build
**1.0.38** — the mining Mission Control formula, armor mass coefficients, the alien hate model
— and a patch can quietly change those. After a big update, re-sync your game data and treat
those numbers as "check against a tooltip before trusting." If you catch one that's drifted,
please open an issue.

### 5. Can it break my save, or play the game for me?

It can't play for you. There's no connection to the running game — it reads save files, it
doesn't click buttons. Every decision and every click stays yours.

Practically everything in the repo is read-only. The single exception is
`scripts/ti_war_editor.py`, which edits a save to add belligerents to an existing war. It only
runs when you explicitly ask for it, never as a side effect of asking a question. It always
writes a timestamped backup first, re-parses and validates the result before replacing
anything, and aborts leaving your original untouched if the check fails. Keep the backup until
you've confirmed the edited save loads.

---

Something not covered here? [getting-started.md](getting-started.md) has installation
troubleshooting, [setup.md](setup.md) has the manual setup and per-platform paths, and
[examples.md](examples.md) is the full catalog of what you can ask.
