# Contributing

**Send a pull request.** That's the ask. This repo is built so that fixing it is mostly your
agent's job, not yours — point Claude Code (or Codex, or whatever you use) at the folder, and
`CLAUDE.md` teaches it the conventions, the tool inventory, and the house rules before it
writes a line. Your job is to describe the problem and review what comes back.

If you hit a wrong number, a missing analyzer, or an answer that doesn't match your game, the
fastest path to it being fixed is thirty minutes with your agent and a PR — not a ticket that
waits on me.

## The quickest useful PRs

- **A formula that drifted.** Constants here were calibrated on build 1.0.38. When a patch
  moves one, the fix is usually a number and a note in `docs/lessons/`.
- **An analyzer that doesn't exist yet.** If you wanted an answer the toolkit couldn't give,
  that gap is a script. Most of the existing ones started exactly that way.
- **A report that's missing a column.** Growing an existing script beats a new one — see the
  inventory in `CLAUDE.md` before you write something new.
- **Lessons from your own campaign.** If you disproved something the repo believes,
  `docs/lessons/` is where that goes, and it's as valuable as code.
- **Setup papercuts.** Anything that made the first ten minutes harder than it should be.

## The one rule: the game is ground truth

Your save file and the in-game tooltip are authoritative. Every formula in this repo is a
hypothesis about how the game works, and when the two disagree, **this repo is wrong.**

So the evidence standard for a mechanics change is: show what the game said. A tooltip
screenshot, a save-file field, or a decompiled symbol beats reasoning from first principles
every time, and "this is how it works in other 4X games" isn't evidence at all. Put that
evidence in the PR description — a number changed without it can't be reviewed.

An agent will happily produce a confident, well-formatted, wrong number. Check its output
against a tooltip yourself before you open the PR. The ground-truth rule applies to
contributions exactly as it applies to answers.

## Conventions that keep the toolkit coherent

- **Standard library only.** There is no `requirements.txt` and no virtualenv, on purpose — a
  player should be able to clone and run. Python 3.10+. Please keep it that way.
- **Every script is a real CLI.** Argparse, a working `--help`, sensible defaults. Locate
  saves through `scripts/ti_config.py` rather than hardcoding paths, and handle both `.json`
  and `.gz`.
- **Saves are 60–90 MB.** Answer from a single pass; don't re-walk the file per field.
- **Fix the existing script instead of adding a one-off.** If a report is missing something,
  the report should grow.
- **Translate names for players.** Use `scripts/localization/` so output reads "Poseidon
  Lantern", not `NeutronFluxLantern`. Internal names belong in parentheses, if anywhere.
- **Respect the spoiler policy.** The save contains things the game deliberately hides —
  unsurveyed site yields, un-scanned alien internals, rival internals above your intel level,
  undetected alien sites. New code must redact them and say that it's redacting. This isn't
  optional; it's why the project can call itself analysis rather than cheating.
- **Never commit game data.** `scripts/templates/` and `scripts/localization/` are mirrored
  from each user's own install and are gitignored. The repo ships no Pavonis assets and must
  stay that way.

Tell your agent to read `CONTRIBUTING.md` and `CLAUDE.md` first and it will follow most of
this without being asked.

## What to put in the PR

Keep it short. What was wrong, what the game actually said, what you changed. If it's a
mechanics correction, include the evidence. If it's a new analyzer, one line of sample output
is worth more than a paragraph describing it.

I'd rather merge an imperfect PR and clean it up than have the fix not exist. Don't polish it
into never being sent.

## If you genuinely can't fix it yourself

Then yes, open an issue — a real bug I don't know about is better than silence. Include what
you asked, what it answered, what the game said, your game build, and whether you're running
mods. But if you have an agent and thirty minutes, the PR is strictly better for both of us.
