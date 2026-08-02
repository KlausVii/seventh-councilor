# The campaign log — a monthly time-series for your run

A **campaign log** is a per-campaign markdown file of append-only timeline tables: one row
per analyzed save, tracking the alien footprint, your economy and military, nation health,
and research throughput over the whole run. Keep one per campaign, anywhere you like
(it's your data — don't commit it to this repo). Its value compounds: single-save analysis
tells you where you are; the log tells you which way every number is *moving* — whether the
aliens are outbuilding you, whether your resource buffers are thinning, whether research
throughput justifies your lab investment.

Three scripts work with it:

- **`scripts/campaign_log_row.py <save.json>`** — computes the six active rows (Tables A,
  B, D, E, F, G) for one save, formatted ready to paste.
- **`scripts/research_income.py <save.json> --all-factions`** — appends a research-income
  decomposition row (the table historically lettered "Table H").
- **`scripts/alien_progress_timeline.py`** — *reads* the log (`campaign/log.md` by default;
  override with the `TI_CAMPAIGN_LOG` environment variable): walks the dates in the
  `### Table A` section, finds the matching save files, and reports alien
  ships/tonnage/bases across the run.

Because the third script parses the file, the section headings and row format below are
**load-bearing** — use `### Table A` (etc.) exactly, and start every data row with
`| YYYY-MM-DD |`.

## Why there is no Table C

The lettering runs A, B, D, E, F, G, H — **Table C was removed** (it reported per-resource
income from `cachedYearlyRevenue`, which is stale in saves and ~2× off; see `CLAUDE.md`
hard rule 4). The letters were kept stable rather than reshuffled so old logs stay parseable.

## File skeleton

Start a new campaign log from this skeleton. Header rows are for humans — the scripts emit
and parse only the `| YYYY-MM-DD | … |` data rows.

```markdown
# Campaign log — <faction>, <difficulty>, started <real date>

## Save-by-save metrics timeline

### Table A
Alien hate & footprint.

| Date | Hate | MC | Floor | Above | Xeno | Kills | AlienInv | SpaceStr |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2031-03-01 | 28.4 | 55 | 20.0 | 8.4 | 2 | 1 | 3 | 0.412 |

### Table B
Resource buffers, in days of cover (stock ÷ daily net income; `∞` = no net drain).

| Date | Money | Influence | Ops | Boost | Metals | Water | Vol | Nobles | Fissiles |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2031-03-01 | 45d | 210d | 90d | 38d | 400d | ∞ | 120d | 300d | 85d |

### Table D
Own infrastructure & military.

| Date | Habs | T1 | T2 | T3 | Ships | Mass(kt) | CPs | MC-use | OpsC | Mines(act/off/bld) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2031-03-01 | 12 | 7 | 4 | 1 | 9 | 2 | 41 | 55 | 6 | 10/2/3 |

### Table E
Nation health for your anchor nations (config `anchor_nations`, or auto-detected as your
top-3 controlled nations by GDP), four columns each: cohesion, cohesion rest point,
inequality, GDP in $T. Name the columns after your own anchors — the header below shows
a campaign anchored on USA / China / Russia **as an example**.

| Date | Nat1 Coh | Rest | Ineq | GDP$T | Nat2 Coh | Rest | Ineq | GDP$T | Nat3 Coh | Rest | Ineq | GDP$T |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2031-03-01 | 6.10 | 5.80 | 0.42 | 24.3 | 5.45 | 5.50 | 0.38 | 19.8 | 3.90 | 4.20 | 0.44 | 2.1 |

(Example header for a USA/China/Russia campaign: `| Date | USA Coh | Rest | Ineq | GDP$T |
CHN Coh | … | RUS Coh | … |`.)

### Table F
Research throughput & balance of power.

| Date | ThisMo | Cumulative | TopRival(stale) | AlienShips | AlienHabs | You(ships/habs/CPs) |
|---|---:|---:|---:|---:|---:|---|
| 2031-03-01 | 4 | 87 | 41,250 | 14 | 6 | 9 / 12 / 41 |

### Table G
Tech completion counts.

| Date | GlobalTechs | FactionProjects |
|---|---:|---:|
| 2031-03-01 | 32 | 55 |

### Table H
Research-income decomposition (from `research_income.py`).

| Date | Total/mo | Nations/mo | Nat1 rm | Nat2 rm | Nat3 rm | Habs/mo | Dist/mo | HQ+Counc/mo | HF | Init | Serv | Prot | Acad | Exod |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2031-03-01 | 8,916 | 4,120 | 1,850.5 | 2,210.0 | 960.2 | 2,400 | 1,486 | 610 | 7,900 | 8,400 | 6,100 | 5,200 | 9,100 | 4,800 |
```

(The example rows above are invented plausible numbers, not from any real campaign.)

## Column meanings

**Table A — alien hate & footprint** (one row per save):
- `Hate` — your faction's `assessedAlienHateOfMe` = `clamp(kill-accumulator, Floor, cap)`. It's
  driven by your **kills** of alien ships/stations (~0.4 × hull SI each), with the MC-based
  `Floor` only as a lower bound — usually non-binding once you've killed anything (LESSONS-aliens A4).
- `MC` — your Mission Control usage. Sets the hate **floor** (next row), **not** the hate itself.
- `Floor` — the computed hate floor: `max(20, MC × difficulty_mod × 0.8^masking_projects)`
  (difficulty mod: Cinematic 0.05 / Normal 0.30 / Veteran 0.60 / Brutal 1.0).
- `Above` — `Hate − Floor`: the ventable/decayable portion (your accumulated kill-hate above the floor).
- `Xeno` — aliens removed (councilor-level xeno kills); `Kills` — your recorded kills of alien
  ships (the real hate driver); `AlienInv` — your **Investigate-Alien-Activity** mission counter,
  which also feeds the Xenology research bonus (+AlienInv/100; docs/mechanics/Research Mechanics);
  `SpaceStr` — your peak space-strength share since the last alien knockdown, the reference the
  game vents hate against when your strength drops >35% below it (docs/mechanics/Alien Hate and
  Diplomacy §4).

**Table B — resource buffers**: days of cover per resource, computed as
`stock ÷ (yearly revenue ÷ 365)`; `∞` when the yearly rate is zero or negative-tracked.
Columns: Money, Influence, Operations, Boost, Metals, Water, Volatiles, Noble Metals,
Fissiles.

**Table D — infrastructure**: total habs and the tier-1/2/3 split; ship count and total
fleet mass in kt; Earth control points; MC usage; Operations+Command Centers built (`OpsC`);
mines as `active/off/building`.

**Table E — nation health**: for your anchor nations, in order — cohesion, the cohesion
rest point it is drifting toward, inequality, and GDP in trillions. Anchors come from
`--nations`, else config `anchor_nations`, else auto-detect (top 3 by GDP among nations
where your faction holds a control point); identified by `templateName`, never
`displayName` (which renames on federation). **Pick your anchors once and keep them** —
changing anchors mid-campaign breaks column comparability across rows. (In the reference
campaign the anchors are USA / China / Russia.)

**Table F — research throughput & balance of power**: `ThisMo` = techs+projects finished
since the previous row (pass the previous row's `Cumulative` via `--prev-cumulative`,
otherwise it prints `?`); `Cumulative` = finished global techs + finished faction projects;
`TopRival(stale)` = the highest rival research rate from the save's cached revenue (marked
stale — treat as a rough indicator only); alien ship and hab counts; and your
`ships / habs / CPs` triple for the balance-of-power read.

**Table G — tech counts**: finished global techs and finished faction projects separately
(their sum is Table F's `Cumulative`).

**Table H — research income** (from `research_income.py`, which reproduces the in-game 🧪
tooltip to ~0.1%): your total research/month; the nations component; the raw
`research_month` value of each anchor nation (same anchors as Table E; the Nations-screen
flask column — not your share); the habs component; the distribution bonus; HQ + councilors; then the six rivals'
estimated monthly research in the order Humanity First, Initiative, Servants, Protectorate,
Academy, Exodus (computed by `--all-factions`, or pass Intel-screen ground truth via
`--rivals`).

## Workflow

1. **On each new save you analyze** (monthly-ish cadence works well):
   ```bash
   python3 scripts/campaign_log_row.py <save.json> --prev-cumulative <last Table F Cumulative>
   python3 scripts/research_income.py <save.json> --all-factions
   ```
2. **Paste** each emitted `| date | … |` row under its matching `### Table X` heading
   (the first script prints them grouped by heading; the second prints the Table H row at
   the end of its report).
3. **Read trends, not points.** With the log populated, an agent (or you) can answer
   "is alien tonnage growth outpacing mine?", "when did my money cover start shrinking?",
   or "did the lab buildout actually move research/month?" from the deltas. For the alien
   side specifically:
   ```bash
   TI_CAMPAIGN_LOG=/path/to/your-campaign-log.md python3 scripts/alien_progress_timeline.py
   ```
   walks every date in your Table A and prints alien ships/kt/bases (with your own
   ships/kt alongside) across the whole run — note its output is ground truth including
   undetected alien assets, so treat it as historical record, not in-character intel.

## Related

- [Lessons: process](lessons/LESSONS-process.md) — ground-truth discipline the tables encode.
- [Lessons: aliens](lessons/LESSONS-aliens.md) — the hate model behind Table A's floor column.
- [Strategy: Hate Management at Scale](strategy/Hate%20Management%20at%20Scale.md) — what to do with the Table A trend.
