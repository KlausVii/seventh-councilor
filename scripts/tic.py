#!/usr/bin/env python3
"""tic — one process, many analyzers: short aliases + parse-once batches.

Every analyzer parses the save through ti_config.load_save, which memoizes per
process. Run several tools in ONE tic invocation and the 60–90 MB save is
parsed once, not once per tool — separate the commands with `::`:

    python3 scripts/tic.py snapshot --brief :: audit :: power --all
    python3 scripts/tic.py mines
    python3 scripts/tic.py list                # all aliases

Each command gets exactly the argv it would get standalone; output and exit
codes are unchanged (batch exit code = worst command's). `tic <script_name>`
works too, alias or not.

Deliberately NOT dispatchable: ti_war_editor (mutates the save — invoke it
explicitly: python3 scripts/ti_war_editor.py), per CLAUDE.md § Save editing.

Note for batches: analyzers are read-only by convention; a tool that mutated
the parsed save dict in memory would poison later commands in the same batch
(see the cache note in ti_config.load_save).
"""

import os
import runpy
import sys
import traceback

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# alias -> module. The bare module name always works as well.
ALIASES = {
    "snapshot": "extract_snapshot",
    "audit": "base_fix_audit",
    "mines": "mine_completion_timeline",
    "mine-up": "mine_upgrade_planner",
    "shutdown": "mine_shutdown_advisor",
    "life": "lifesupport",
    "research": "research_income",
    "techtree": "global_tech_tree_walk",
    "techrace": "tech_contributions",
    "ships": "warship_optimizer",
    "counter": "counter_fleet_planner",
    "drives": "drive_upgrade_finder",
    "drive-eta": "drive_eta_compare",
    "fusion": "fusion_ladder_planner",
    "armor": "armor_calc",
    "siege": "base_siege_calc",
    "assault": "assault_planner",
    "capture": "capture_target_planner",
    "colony": "colony_planner",
    "sites": "resource_site_planner",
    "free": "free_founding",
    "eta": "transfer_eta",
    "boost": "boost_analysis",
    "flow": "resource_flow",
    "mc": "mc_capacity_projection",
    "cc": "cc_upgrade_planner",
    "modules": "module_completion_dates",
    "power": "hab_power_audit",
    "nation": "nation_report",
    "opinion": "opinion_trajectory",
    "ops": "ops_query",
    "alien": "alien_progress_timeline",
    "trajectory": "save_trajectory",
    "logrow": "campaign_log_row",
    "setup": "setup_campaign",
    "sync": "sync_game_data",
    "fetch": "fetch_ladder",
    "vault": "generate_vault",
    "genmod": "generate_modules",
}

EXCLUDED = {
    "ti_war_editor": ("mutates the save — run it explicitly and on purpose: "
                      "python3 scripts/ti_war_editor.py (CLAUDE.md § Save editing)"),
}

SEP = "::"


def _usage():
    print(__doc__.strip())
    print("\nAliases:")
    width = max(map(len, ALIASES))
    for a in sorted(ALIASES):
        print(f"  {a:<{width}}  {ALIASES[a]}.py")


def _resolve(name):
    mod = ALIASES.get(name, name)
    if mod in EXCLUDED:
        sys.exit(f"tic: refusing to dispatch {mod!r}: {EXCLUDED[mod]}")
    if not os.path.isfile(os.path.join(HERE, mod + ".py")):
        sys.exit(f"tic: unknown command {name!r} — `tic list` shows every alias")
    return mod


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "list"):
        _usage()
        return 0

    commands, cur = [], []
    for a in argv:
        if a == SEP:
            commands.append(cur)
            cur = []
        else:
            cur.append(a)
    commands.append(cur)
    if any(not c for c in commands):
        sys.exit(f"tic: empty command in batch (stray {SEP!r}?)")

    rc = 0
    for cmd in commands:
        mod = _resolve(cmd[0])
        if len(commands) > 1:
            print(f"\n{'═' * 20} tic: {' '.join(cmd)} {'═' * 20}", flush=True)
        sys.argv = [mod + ".py"] + cmd[1:]
        try:
            runpy.run_module(mod, run_name="__main__")
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
            if code and not isinstance(e.code, int):
                print(e.code, file=sys.stderr)
            rc = max(rc, code)
        except Exception:
            traceback.print_exc()
            rc = max(rc, 1)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
