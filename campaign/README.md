# Your campaign workspace

Everything in this folder except this README is **gitignored** — it belongs to you and your
campaign, not to the repo. This is where your AI assistant keeps the knowledge that is true
for *your* run but wouldn't generalize to other players: your log, your doctrine, your ship
designs, your local lessons.

Nothing here is required — the analyzers work statelessly off your save. But a maintained
workspace is what turns "analyze this save" into "advise me, knowing my campaign."

## Layout

| Path | What lives here |
|---|---|
| `log.md` | Your campaign timeline log — monthly rows for Tables A–H (format: `docs/campaign-log.md`). Scripts emit paste-ready rows; `alien_progress_timeline.py` reads Table A back. |
| `doctrine.md` | Durable playstyle preferences and standing decisions: faction goals, economy shape, fleet doctrine, research policy ("one category at a time"), what you've explicitly chosen NOT to do. The assistant reads this before scoring options so advice matches how you actually play. |
| `designs.md` | Your ship classes: hull/drive/armor/loadout per class, plus **shipbuilder calibration readings** (measured wet mass, combat g, turn rate). These feed `warship_optimizer.py`'s `calibrate()` for ~1 t-accurate predictions on your hulls. |
| `lessons.md` | Campaign-local lessons — things you or the assistant got wrong once and verified. If one turns out to be universally true, promote it (PR the repo's `docs/lessons/`); until then it stays here. |
| `reports/` | Saved analyzer output: extractor snapshots, research rankings, assault recon. Date-stamp filenames (`2036-02-01-snapshot.md`). |
| `notes/` | Freeform: strategic reviews, war plans, "why I did this" write-ups. |

## Conventions

- **Absolute in-game dates everywhere** (`2036-02-01`), never "last month".
- **Ground truth over memory**: when a note disagrees with the save, the save wins; fix the note.
- One `log.md` row set per analysis session (monthly granularity is plenty).
- Starting a new campaign? Archive this folder's contents into `notes/old-<campaign>/` (or
  delete them) and update `config.json` — stale doctrine poisons advice.
