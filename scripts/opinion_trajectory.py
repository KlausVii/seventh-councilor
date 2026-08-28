#!/usr/bin/env python3
"""Trace a nation's public-opinion trajectory across TI saves and find who moved it.

Usage:
    python3 opinion_trajectory.py 2026_USA save1.json save2.json ...
    python3 opinion_trajectory.py 2026_USA --glob "_2032-12-*"   # all Dec-2032 saves

For each save (sorted by save counter), prints the nation's publicOpinion by
ideology PLUS every councilor whose priorMissionTemplateName == 'Propaganda'
(faction, name, target nation) — the usual cause of step-drops.

Reference-campaign findings this script was built on (see LESSONS-politics C15):
  A Resist-anchor nation went 87→55 via TWO rival propaganda campaigns, not decay:
    one −15.8pp overnight step (two rival councilors' Propaganda completing same-day)
    and one −12.1pp step over six days (a third faction's councilor).
  No recovery afterward: zero Unity pips in the nation = no drift-back force.
  NOTE: a Submit/Coop propagandist can surface as +Escape/+Cooperate — opinion
  moves stepwise along the ideology spectrum, not directly to the caster's pole.
  historyPublicOpinion on the nation is 32 entries, [0]=newest, ~2-day step.
"""
import gzip, json, sys, glob, os, re

if '--help' in sys.argv or '-h' in sys.argv or len(sys.argv) < 3:
    print(__doc__ or 'Usage: see module docstring.')
    raise SystemExit(0 if '--help' in sys.argv or '-h' in sys.argv else 1)

from ti_config import find_save_dir

_save_dir = find_save_dir()
SAVES = str(_save_dir) + "/" if _save_dir else ""
IDEOLOGIES = ["Resist", "Exploit", "Escape", "Cooperate", "Appease", "Submit", "Destroy", "Undecided"]


from ti_config import load_save  # THE shared loader: gzip magic + BOM, memoized


def counter(path):
    b = os.path.basename(path)
    m = re.search(r"save(\d+)_", b)
    try:
        return int(m.group(1))
    except Exception:
        return 0


def analyze(nation_template, paths):
    print(f"{'date':12} " + " ".join(f"{i[:6]:>6}" for i in IDEOLOGIES) + "  | propaganda (prior mission)")
    for p in sorted(paths, key=counter):
        s = load_save(p)
        gs = s["gamestates"]
        fs = {f["Key"]["value"]: f["Value"].get("templateName") for f in gs["PavonisInteractive.TerraInvicta.TIFactionState"]}
        nid = {n["Key"]["value"]: n["Value"].get("templateName") for n in gs["PavonisInteractive.TerraInvicta.TINationState"]}
        nat = next((n["Value"] for n in gs["PavonisInteractive.TerraInvicta.TINationState"]
                    if n["Value"].get("templateName") == nation_template), None)
        if nat is None:
            print(os.path.basename(p), f"— nation {nation_template} not found"); continue
        o = nat["publicOpinion"]
        props = []
        for c in gs["PavonisInteractive.TerraInvicta.TICouncilorState"]:
            v = c["Value"]
            if v.get("priorMissionTemplateName") == "Propaganda":
                tgt = (v.get("priorMissionTarget") or {}).get("value")
                props.append(f"{fs.get((v.get('faction') or {}).get('value'))} {v.get('displayName')}→{nid.get(tgt, tgt)}")
        date = os.path.basename(p).split("_")[-1].replace(".json", "")
        print(f"{date:12} " + " ".join(f"{o.get(i, 0)*100:6.1f}" for i in IDEOLOGIES) + "  | " + ", ".join(props))


if __name__ == "__main__":
    nation = sys.argv[1]
    if sys.argv[2] == "--glob":
        if not SAVES:
            raise SystemExit("No save directory found — set save_dir in config.json "
                             "or pass explicit save paths instead of --glob.")
        paths = glob.glob(SAVES + "*" + sys.argv[3] + "*")
    else:
        paths = sys.argv[2:]
    analyze(nation, paths)
