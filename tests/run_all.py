#!/usr/bin/env python3
"""Local test suite — run before sending a PR:  python3 tests/run_all.py

Deliberately local-only (this repo has no CI): stdlib unittest, no game data
and no save file required, finishes in a few seconds. Four groups:

  1. compile   — every scripts/*.py byte-compiles
  2. cli       — every CLI answers --help with exit 0 (known exceptions below)
  3. security  — the greppable claims SECURITY.md makes stay true:
                 network/subprocess confined to fetch_ladder.py, file writers
                 confined to the documented set, imports stdlib-only
  4. loader    — ti_config.load_save handles .json/.gz/BOM/lying extensions
                 and memoizes correctly; parse_intel_map shape
"""

from __future__ import annotations

import ast
import gzip
import json
import os
import py_compile
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

ALL_SCRIPTS = sorted(SCRIPTS.glob("*.py"))

# --help exceptions. Everything else must exit 0 on --help with no game data,
# no config.json and no save present.
NO_ARGPARSE = {
    "fetch_ladder.py",       # manual argv: prints its doc and exits 1
}
NEEDS_GAME_DATA = {
    # These abort with a clear message when the templates mirror is absent;
    # on a set-up machine they must exit 0 instead.
    "generate_modules.py",
    "generate_vault.py",
}

# SECURITY.md's writer table — scripts allowed to write/replace/copy files.
WRITERS = {
    "extract_snapshot.py", "save_trajectory.py",       # report output
    "generate_vault.py", "generate_modules.py",        # generated/ pages
    "setup_campaign.py",                               # config.json
    "sync_game_data.py",                               # mirrors game data IN
    "ti_war_editor.py",                                # opt-in save editing
}
WRITE_CALLS = {
    ("os", "replace"), ("os", "remove"), ("os", "unlink"), ("os", "rename"),
    ("os", "makedirs"), ("shutil", "copy"), ("shutil", "copy2"),
    ("shutil", "move"), ("shutil", "rmtree"),
}
NET_MODULES = {"urllib", "socket", "http", "subprocess", "ssl", "ftplib"}
LOCAL_MODULES = {p.stem for p in ALL_SCRIPTS}


def _top_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            mods.add(node.module.split(".")[0])
    return mods


class Compile(unittest.TestCase):
    def test_all_scripts_compile(self):
        for p in ALL_SCRIPTS:
            with self.subTest(script=p.name):
                py_compile.compile(str(p), doraise=True)

    def test_tests_compile(self):
        py_compile.compile(__file__, doraise=True)


class Cli(unittest.TestCase):
    def test_help_exits_zero(self):
        for p in ALL_SCRIPTS:
            if p.name in NO_ARGPARSE or p.name == "ti_config.py":
                continue
            with self.subTest(script=p.name):
                r = subprocess.run([sys.executable, str(p), "--help"],
                                   capture_output=True, text=True, timeout=60,
                                   encoding="utf-8", errors="replace")
                if p.name in NEEDS_GAME_DATA and r.returncode != 0:
                    self.assertIn("not found", r.stdout + r.stderr,
                                  f"{p.name}: unexpected --help failure:\n{r.stderr}")
                    continue
                self.assertEqual(r.returncode, 0,
                                 f"{p.name} --help failed:\n{r.stderr or r.stdout}")

    def test_tic_list_and_editor_refusal(self):
        r = subprocess.run([sys.executable, str(SCRIPTS / "tic.py"), "list"],
                           capture_output=True, text=True, timeout=60,
                           encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("snapshot", r.stdout)
        r = subprocess.run([sys.executable, str(SCRIPTS / "tic.py"), "ti_war_editor"],
                           capture_output=True, text=True, timeout=60,
                           encoding="utf-8", errors="replace")
        self.assertNotEqual(r.returncode, 0, "tic must refuse to dispatch the save editor")
        self.assertIn("refusing", r.stderr + r.stdout)


class SecurityClaims(unittest.TestCase):
    """SECURITY.md invites readers to verify its claims by grep; verify them
    structurally (AST) instead, so docstrings can't false-positive."""

    def test_network_and_subprocess_confined_to_fetch_ladder(self):
        for p in ALL_SCRIPTS:
            if p.name == "fetch_ladder.py":
                continue
            with self.subTest(script=p.name):
                hits = _top_imports(p) & NET_MODULES
                self.assertFalse(hits, f"{p.name} imports {hits} — SECURITY.md "
                                       "promises network/subprocess only in fetch_ladder.py")

    def test_stdlib_only(self):
        allowed = set(sys.stdlib_module_names) | LOCAL_MODULES
        for p in ALL_SCRIPTS:
            with self.subTest(script=p.name):
                extra = _top_imports(p) - allowed
                self.assertFalse(extra, f"{p.name} imports third-party modules: {extra}")

    def test_file_writes_confined_to_documented_writers(self):
        for p in ALL_SCRIPTS:
            if p.name in WRITERS:
                continue
            tree = ast.parse(p.read_text(encoding="utf-8"))
            offenses = []
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                f = node.func
                # open(..., 'w'/'a'/'wb'/...)
                if isinstance(f, ast.Name) and f.id == "open" and len(node.args) > 1:
                    mode = node.args[1]
                    if isinstance(mode, ast.Constant) and isinstance(mode.value, str) \
                            and any(c in mode.value for c in "wax+"):
                        offenses.append(f"open(mode={mode.value!r}) line {node.lineno}")
                # os.replace/remove/..., shutil.copy/...
                if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) \
                        and (f.value.id, f.attr) in WRITE_CALLS:
                    offenses.append(f"{f.value.id}.{f.attr} line {node.lineno}")
                # Path.write_text / write_bytes
                if isinstance(f, ast.Attribute) and f.attr in ("write_text", "write_bytes"):
                    offenses.append(f".{f.attr} line {node.lineno}")
            with self.subTest(script=p.name):
                self.assertFalse(offenses,
                                 f"{p.name} writes files but is not in SECURITY.md's "
                                 f"writer table: {offenses}")


class Loader(unittest.TestCase):
    MINI = {"gamestates": {"PavonisInteractive.TerraInvicta.TIFactionState": []},
            "currentDateTime": "2026-09-01"}

    def _fixtures(self, d: Path) -> list[Path]:
        text = json.dumps(self.MINI)
        paths = []
        (d / "plain.json").write_text(text, encoding="utf-8")
        (d / "bom.json").write_text(text, encoding="utf-8-sig")
        (d / "plain.gz").write_bytes(gzip.compress(text.encode()))
        (d / "bom_inside.gz").write_bytes(gzip.compress("﻿".encode("utf-8") + text.encode()))
        (d / "lying_name.json").write_bytes(gzip.compress(text.encode()))  # gz bytes, .json name
        paths = [d / n for n in
                 ("plain.json", "bom.json", "plain.gz", "bom_inside.gz", "lying_name.json")]
        return paths

    def test_all_save_shapes_parse(self):
        import ti_config
        with tempfile.TemporaryDirectory() as td:
            for p in self._fixtures(Path(td)):
                with self.subTest(fixture=p.name):
                    self.assertEqual(ti_config.load_save(p), self.MINI)

    def test_memoization_and_cap(self):
        import ti_config
        with tempfile.TemporaryDirectory() as td:
            paths = self._fixtures(Path(td))
            a = ti_config.load_save(paths[0])
            self.assertIs(a, ti_config.load_save(paths[0]), "same file must be a cache hit")
            # rewritten file (new mtime/size) must re-parse
            paths[0].write_text(json.dumps({"gamestates": {}, "x": 1}), encoding="utf-8")
            os.utime(paths[0], ns=(1, 1))
            self.assertIsNot(a, ti_config.load_save(paths[0]))
            for p in paths:  # cache stays bounded on multi-save scans
                ti_config.load_save(p)
            self.assertLessEqual(len(ti_config._SAVE_CACHE), ti_config._SAVE_CACHE_MAX)

    def test_parse_intel_map(self):
        import ti_config
        fv = {"intel": [
            {"Key": {"$type": "PavonisInteractive.TerraInvicta.TIHabState", "value": 5},
             "Value": 0.5},
            {"Key": {"$type": "PavonisInteractive.TerraInvicta.TISpaceFleetState", "value": 9},
             "Value": 1.0},
        ]}
        self.assertEqual(ti_config.parse_intel_map(fv),
                         {("TIHabState", 5): 0.5, ("TISpaceFleetState", 9): 1.0})
        self.assertEqual(ti_config.parse_intel_map({}), {})

    def test_alien_ground_truth_is_opt_in(self):
        from extract_snapshot import extract_alien_progress
        with self.assertRaises(ValueError):
            extract_alien_progress({}, factions={}, faction_template="ResistCouncil")


if __name__ == "__main__":
    unittest.main(verbosity=2)
