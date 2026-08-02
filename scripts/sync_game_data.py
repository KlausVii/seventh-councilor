#!/usr/bin/env python3
"""Sync Terra Invicta game data (templates + English localization) into this repo.

Copies ALL template JSONs and all English .en localization files from the local
game install into the local mirror next to the scripts, but FIRST prints a
content-level drift report:

  * Template JSONs are parsed and compared per-dataName entry:
    added / removed / changed entries (with the changed top-level keys and a
    compact old -> new value preview).
  * .en localization files get a line-level summary (added / removed lines,
    with a few examples).
  * Files present only in the source (never mirrored before) are reported as NEW.

Usage:
    python3 sync_game_data.py                 # report drift, then copy
    python3 sync_game_data.py --dry-run       # report drift only, copy nothing
    python3 sync_game_data.py \
        --src-templates /path/to/Templates \
        --src-localization /path/to/Localization/en \
        --dst-templates /path/to/templates \
        --dst-localization /path/to/localization

Defaults (no CLI args needed when auto-detection works):
    source templates    = <game install>/TerraInvicta_Data/StreamingAssets/Templates
                          (from config.json "game_install_dir", else auto-detected
                          via ti_config across Windows/macOS/Linux/WSL)
    source localization = .../StreamingAssets/Localization/en
    dest   templates    = scripts/templates      (next to this script)
    dest   localization = scripts/localization
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

from ti_config import CONFIG, _candidate_install_dirs

_SCRIPTS_DIR = Path(__file__).resolve().parent


def _find_game_streaming_assets() -> Path | None:
    """StreamingAssets dir of the game install (config first, then auto-detect)."""
    import os
    roots = []
    if CONFIG["game_install_dir"]:
        roots.append(Path(os.path.expanduser(CONFIG["game_install_dir"])))
    roots += _candidate_install_dirs()
    for root in roots:
        sa = root / "TerraInvicta_Data" / "StreamingAssets"
        if (sa / "Templates").is_dir():
            return sa
    return None


_GAME_SA = _find_game_streaming_assets()
DEFAULT_SRC_TEMPLATES = (_GAME_SA / "Templates") if _GAME_SA else None
DEFAULT_SRC_LOCAL = (_GAME_SA / "Localization" / "en") if _GAME_SA else None
DEFAULT_DST_TEMPLATES = _SCRIPTS_DIR / "templates"
DEFAULT_DST_LOCAL = _SCRIPTS_DIR / "localization"

PREVIEW_LEN = 110
MAX_EXAMPLES = 12


def compact(v) -> str:
    s = json.dumps(v, ensure_ascii=False, sort_keys=True, default=str)
    if len(s) > PREVIEW_LEN:
        s = s[: PREVIEW_LEN - 1] + "…"
    return s


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def index_by_dataname(data):
    """Return ({dataName: entry}, ok) — ok False if not a list of dataName dicts."""
    if not isinstance(data, list) or not data or not all(
        isinstance(e, dict) and "dataName" in e for e in data
    ):
        return None, False
    idx = {}
    for e in data:
        idx[e["dataName"]] = e  # last-wins on duplicate dataNames
    return idx, True


def diff_json_file(src: Path, dst: Path) -> bool:
    """Print drift for one template JSON. Returns True if any content drift."""
    name = src.name
    try:
        s_data = load_json(src)
    except Exception as ex:
        print(f"  !! {name}: source unparseable ({ex}) — will copy verbatim")
        return True
    if not dst.exists():
        n = len(s_data) if isinstance(s_data, list) else 1
        print(f"  ++ {name}: NEW (not previously mirrored) — {n} entries")
        return True
    try:
        d_data = load_json(dst)
    except Exception as ex:
        print(f"  !! {name}: mirror copy unparseable ({ex}) — will overwrite")
        return True

    s_idx, s_ok = index_by_dataname(s_data)
    d_idx, d_ok = index_by_dataname(d_data)
    if not (s_ok and d_ok):
        same = json.dumps(s_data, sort_keys=True) == json.dumps(d_data, sort_keys=True)
        if same:
            return False
        print(f"  ~~ {name}: content differs (not a per-dataName file; whole-file compare)")
        return True

    added = [k for k in s_idx if k not in d_idx]
    removed = [k for k in d_idx if k not in s_idx]
    changed = []
    for k in s_idx:
        if k in d_idx and s_idx[k] != d_idx[k]:
            keys = sorted(
                set(s_idx[k]) | set(d_idx[k]),
                key=lambda kk: kk,
            )
            ck = [kk for kk in keys if s_idx[k].get(kk) != d_idx[k].get(kk)]
            changed.append((k, ck))

    if not (added or removed or changed):
        return False

    print(f"  ~~ {name}: {len(added)} added, {len(removed)} removed, {len(changed)} changed "
          f"(mirror {len(d_idx)} → install {len(s_idx)} entries)")
    for k in added[:MAX_EXAMPLES]:
        print(f"       + {k}")
    if len(added) > MAX_EXAMPLES:
        print(f"       + … and {len(added) - MAX_EXAMPLES} more")
    for k in removed[:MAX_EXAMPLES]:
        print(f"       - {k}")
    if len(removed) > MAX_EXAMPLES:
        print(f"       - … and {len(removed) - MAX_EXAMPLES} more")
    for k, ck in changed[:MAX_EXAMPLES]:
        print(f"       ~ {k}: keys changed: {', '.join(ck)}")
        for kk in ck[:4]:
            old = compact(d_idx[k].get(kk))
            new = compact(s_idx[k].get(kk))
            print(f"           {kk}: {old} → {new}")
    if len(changed) > MAX_EXAMPLES:
        print(f"       ~ … and {len(changed) - MAX_EXAMPLES} more changed entries")
    return True


def diff_en_file(src: Path, dst: Path) -> bool:
    """Line-level summary for a .en localization file. Returns True on drift."""
    name = src.name
    s_text = src.read_text(encoding="utf-8-sig", errors="replace")
    if not dst.exists():
        n = sum(1 for ln in s_text.splitlines() if "=" in ln)
        print(f"  ++ {name}: NEW (not previously mirrored) — ~{n} tagged lines")
        return True
    d_text = dst.read_text(encoding="utf-8-sig", errors="replace")
    if s_text == d_text:
        return False
    s_lines = s_text.splitlines()
    d_lines = d_text.splitlines()
    s_set, d_set = set(s_lines), set(d_lines)
    added = [ln for ln in s_lines if ln not in d_set]
    removed = [ln for ln in d_lines if ln not in s_set]
    print(f"  ~~ {name}: {len(added)} lines added/changed, {len(removed)} lines removed/changed "
          f"(mirror {len(d_lines)} → install {len(s_lines)} lines)")
    for ln in added[:5]:
        print(f"       + {ln[:PREVIEW_LEN]}")
    if len(added) > 5:
        print(f"       + … and {len(added) - 5} more")
    for ln in removed[:5]:
        print(f"       - {ln[:PREVIEW_LEN]}")
    if len(removed) > 5:
        print(f"       - … and {len(removed) - 5} more")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src-templates", type=Path, default=DEFAULT_SRC_TEMPLATES)
    ap.add_argument("--src-localization", type=Path, default=DEFAULT_SRC_LOCAL)
    ap.add_argument("--dst-templates", type=Path, default=DEFAULT_DST_TEMPLATES)
    ap.add_argument("--dst-localization", type=Path, default=DEFAULT_DST_LOCAL)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the drift report but copy nothing")
    args = ap.parse_args()

    for p, label in [(args.src_templates, "source templates"),
                     (args.src_localization, "source localization")]:
        if p is None:
            sys.exit(f"ERROR: could not auto-detect the game install ({label}). "
                     "Set \"game_install_dir\" in config.json or pass "
                     "--src-templates / --src-localization.")
        if not p.is_dir():
            sys.exit(f"ERROR: {label} dir not found: {p}")

    src_jsons = sorted(args.src_templates.glob("*.json"))
    src_ens = sorted(args.src_localization.glob("*.en"))

    print("=" * 72)
    print("DRIFT REPORT — game install vs local mirror")
    print(f"  templates:    {args.src_templates}")
    print(f"            →   {args.dst_templates}")
    print(f"  localization: {args.src_localization}")
    print(f"            →   {args.dst_localization}")
    print("=" * 72)

    print(f"\n--- Templates ({len(src_jsons)} JSON files in install) ---")
    t_drift = 0
    for src in src_jsons:
        if diff_json_file(src, args.dst_templates / src.name):
            t_drift += 1
    print(f"  => {t_drift} template file(s) with drift, "
          f"{len(src_jsons) - t_drift} identical at content level.")

    # Mirror-only template files (would become stale orphans)
    if args.dst_templates.is_dir():
        orphans = sorted(set(p.name for p in args.dst_templates.glob("*.json"))
                         - set(p.name for p in src_jsons))
        for o in orphans:
            print(f"  ?? {o}: present in local mirror but NOT in install (left untouched)")

    print(f"\n--- Localization ({len(src_ens)} .en files in install) ---")
    l_drift = 0
    for src in src_ens:
        if diff_en_file(src, args.dst_localization / src.name):
            l_drift += 1
    print(f"  => {l_drift} .en file(s) with drift, "
          f"{len(src_ens) - l_drift} byte-identical.")
    if args.dst_localization.is_dir():
        orphans = sorted(set(p.name for p in args.dst_localization.glob("*.en"))
                         - set(p.name for p in src_ens))
        for o in orphans:
            print(f"  ?? {o}: present in local mirror but NOT in install (left untouched)")

    if args.dry_run:
        print("\n--dry-run: nothing copied.")
        return

    print("\n--- Copying ---")
    args.dst_templates.mkdir(parents=True, exist_ok=True)
    args.dst_localization.mkdir(parents=True, exist_ok=True)
    for src in src_jsons:
        shutil.copy2(src, args.dst_templates / src.name)
    for src in src_ens:
        shutil.copy2(src, args.dst_localization / src.name)
    print(f"Copied {len(src_jsons)} template JSONs and {len(src_ens)} .en files.")


if __name__ == "__main__":
    main()
