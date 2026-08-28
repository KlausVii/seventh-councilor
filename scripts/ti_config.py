"""Shared campaign configuration for The Seventh Councilor's scripts.

Reads `config.json` at the repo root (copy `config.example.json` and edit).
Every value has a sane fallback so the scripts also work with no config at all:
save/install locations auto-detect across Windows, macOS (native + CrossOver),
Linux (native + Proton), and WSL.

Usage from any script in this folder:

    from ti_config import CONFIG, find_save_dir, newest_save, find_templates_dir

    save = newest_save()                # Path to the most recent save, or None
    faction = CONFIG["faction"]         # e.g. "ResistCouncil"
    rp_divisor = CONFIG["research_rate_pct"] / 100.0   # in-game RP cost = template / divisor
"""

from __future__ import annotations

import gzip
import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_REPO_ROOT = Path(__file__).resolve().parent.parent

_DEFAULTS = {
    "save_dir": None,
    "game_install_dir": None,
    "faction": None,               # scripts require --faction if unset
    "anchor_nations": None,        # nation templateNames for trend tables; None = auto-detect
                                   # (resolution helper: extract_snapshot.resolve_anchor_nations)
    "research_rate_pct": 100,
    "alien_progression_pct": 100,
    "difficulty": "Normal",
}

_FACTIONS = [
    "ResistCouncil", "ExploitCouncil", "SubmitCouncil", "AppeaseCouncil",
    "CooperateCouncil", "DestroyCouncil", "EscapeCouncil",
]


def _load_config() -> dict:
    cfg = dict(_DEFAULTS)
    path = _REPO_ROOT / "config.json"
    if path.is_file():
        try:
            user = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            raise SystemExit(f"config.json is unreadable or invalid JSON: {e}")
        for k in _DEFAULTS:
            if user.get(k) is not None:
                cfg[k] = user[k]
        if cfg["faction"] is not None and cfg["faction"] not in _FACTIONS:
            raise SystemExit(
                f"config.json: unknown faction {cfg['faction']!r}. "
                f"Valid templateNames: {', '.join(_FACTIONS)}"
            )
    return cfg


CONFIG = _load_config()


# ---------------------------------------------------------------------------
# Save-folder discovery. The game writes saves under a per-user "My Games"
# directory whose location varies by platform/launcher.
# ---------------------------------------------------------------------------

def _candidate_save_dirs() -> list[Path]:
    home = Path.home()
    cands = [
        # Windows native
        home / "Documents" / "My Games" / "TerraInvicta" / "Saves",
        home / "OneDrive" / "Documents" / "My Games" / "TerraInvicta" / "Saves",
        # macOS: CrossOver/Wine bottle keeps a Windows-shaped user dir, but the
        # game usually resolves Documents to the real macOS ~/Documents
        home / "Documents" / "My Games" / "TerraInvicta" / "Saves",
        home / "Library" / "Application Support" / "CrossOver" / "Bottles" / "Steam"
             / "drive_c" / "users" / "crossover" / "Documents" / "My Games"
             / "TerraInvicta" / "Saves",
        # Linux / Steam Deck (Proton prefix)
        home / ".local" / "share" / "Steam" / "steamapps" / "compatdata" / "1176470"
             / "pfx" / "drive_c" / "users" / "steamuser" / "Documents" / "My Games"
             / "TerraInvicta" / "Saves",
    ]
    # WSL: scan every mounted Windows drive for the default profile layout
    mnt = Path("/mnt")
    if mnt.is_dir():
        for drive in mnt.iterdir():
            users = drive / "Users"
            if users.is_dir():
                for prof in users.iterdir():
                    cands.append(prof / "Documents" / "My Games" / "TerraInvicta" / "Saves")
                    cands.append(prof / "OneDrive" / "Documents" / "My Games"
                                 / "TerraInvicta" / "Saves")
    return cands


def find_save_dir() -> Path | None:
    """The configured save_dir if set, else the first auto-detected one."""
    if CONFIG["save_dir"]:
        p = Path(os.path.expanduser(CONFIG["save_dir"]))
        return p if p.is_dir() else None
    for p in _candidate_save_dirs():
        try:
            if p.is_dir():
                return p
        except OSError:
            continue
    return None


def newest_save(save_dir: Path | None = None) -> Path | None:
    """Most recently written save (.json or .gz), by mtime — filename dates lie."""
    d = save_dir or find_save_dir()
    if not d:
        return None
    saves = sorted(
        (p for p in d.iterdir() if p.suffix in (".json", ".gz")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return saves[0] if saves else None


# ---------------------------------------------------------------------------
# Save loading — THE one loader (P3). Every script imports this instead of
# defining its own: gzip is detected by magic bytes (the extension lies), and
# the text is decoded as utf-8-sig because some saves — including inside .gz —
# carry a UTF-8 BOM that plain utf-8/json.loads(bytes) rejects.
# ---------------------------------------------------------------------------

# Parses are memoized by (realpath, mtime, size) so a batch of analyzers run in
# ONE process (scripts/tic.py) parses a 60–90 MB save once, not once per tool.
# Capped at two entries: diff workflows hold two saves; multi-save scans must
# not accumulate twenty parsed saves in memory. Analyzers are read-only by
# convention — a caller that mutates the returned dict would poison later
# cache hits in the same process, so don't.
_SAVE_CACHE: dict[tuple, dict] = {}
_SAVE_CACHE_MAX = 2


def load_save(path) -> dict:
    """Parse a Terra Invicta save (.json or .gz), memoized per process."""
    p = os.path.realpath(str(path))
    st = os.stat(p)
    key = (p, st.st_mtime_ns, st.st_size)
    hit = _SAVE_CACHE.get(key)
    if hit is not None:
        return hit
    with open(p, "rb") as f:
        raw = f.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    obj = json.loads(raw.decode("utf-8-sig"))
    while len(_SAVE_CACHE) >= _SAVE_CACHE_MAX:
        _SAVE_CACHE.pop(next(iter(_SAVE_CACHE)))
    _SAVE_CACHE[key] = obj
    return obj


def parse_intel_map(faction_value: dict) -> dict[tuple[str, int], float]:
    """A faction's `intel` list as {(stateType, id): level}, e.g.
    ('TIHabState', 123) -> 0.5. THE spoiler gate for rival/alien internals:
    quote details only at the intel level the in-game UI shows them
    (calibration notes: capture_target_planner.py header, CLAUDE.md 🕶)."""
    intel: dict[tuple[str, int], float] = {}
    for e in (faction_value.get("intel") or []):
        k = e.get("Key") or {}
        intel[((k.get("$type") or "").split(".")[-1], k.get("value"))] = e.get("Value", 0)
    return intel


# ---------------------------------------------------------------------------
# Game-data discovery (templates / localization). Preference order:
#   1. the local mirror created by sync_game_data.py (scripts/templates — gitignored)
#   2. the configured game_install_dir
#   3. auto-detected Steam library locations
# ---------------------------------------------------------------------------

def _candidate_install_dirs() -> list[Path]:
    home = Path.home()
    cands = [
        home / "Library" / "Application Support" / "CrossOver" / "Bottles" / "Steam"
             / "drive_c" / "Program Files (x86)" / "Steam" / "steamapps" / "common"
             / "Terra Invicta",
        home / "Library" / "Application Support" / "Steam" / "steamapps" / "common"
             / "Terra Invicta",
        home / ".local" / "share" / "Steam" / "steamapps" / "common" / "Terra Invicta",
        Path("C:/Program Files (x86)/Steam/steamapps/common/Terra Invicta"),
    ]
    mnt = Path("/mnt")
    if mnt.is_dir():
        for drive in mnt.iterdir():
            cands.append(drive / "Program Files (x86)" / "Steam" / "steamapps"
                         / "common" / "Terra Invicta")
            cands.append(drive / "Games" / "Steam" / "steamapps" / "common"
                         / "Terra Invicta")
    return cands


def find_templates_dir() -> Path | None:
    local = Path(__file__).resolve().parent / "templates"
    if (local / "TIProjectTemplate.json").is_file():
        return local
    roots = []
    if CONFIG["game_install_dir"]:
        roots.append(Path(os.path.expanduser(CONFIG["game_install_dir"])))
    roots += _candidate_install_dirs()
    for root in roots:
        t = root / "TerraInvicta_Data" / "StreamingAssets" / "Templates"
        if (t / "TIProjectTemplate.json").is_file():
            return t
    return None


def find_localization_dir() -> Path | None:
    local = Path(__file__).resolve().parent / "localization"
    if (local / "TITechTemplate.en").is_file():
        return local
    tdir = find_templates_dir()
    if tdir and tdir.name == "Templates":
        loc = tdir.parent / "Localization" / "en"
        if loc.is_dir():
            return loc
    return None


def require_faction(cli_value: str | None) -> str:
    """Resolve the player faction from CLI flag or config; exit with help if neither."""
    faction = cli_value or CONFIG["faction"]
    if not faction:
        raise SystemExit(
            "No faction set. Pass --faction <templateName> or set \"faction\" in "
            f"config.json. Valid values: {', '.join(_FACTIONS)}"
        )
    return faction
