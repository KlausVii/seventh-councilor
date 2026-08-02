#!/usr/bin/env python3
r"""
ti_war_editor.py -- save-EDITING utility (modifies your save, not an analyzer):
add belligerents to an existing Terra Invicta war in a save file.

Worked example: add one nation to the attacker side and another to the defender side of an
existing war, rewiring every participant's per-nation `wars` enemy list, new and existing.

WHAT IT CHANGES
  1. Core war object (TIWarState):
       * appends each --attacker nation to `_attackingAlliance`
       * appends each --defender nation to `_defendingAlliance`
       * appends a `cohesionGainByNation` entry (Value 0.0) for every added nation
  2. Per-nation enemy lists (TINationState `wars`, a flat list of enemy nation-IDs):
       * every nation on one side gets every nation on the OTHER side as an enemy,
         for the NEW participants AND the pre-existing ones (only missing IDs added).
  It does NOT touch `allies` (diplomatic pacts) or `attacker`/`defender` (side leaders).

WHY IT'S SAFE
  Edits are byte-surgical: it clones the exact bytes of an existing array element and
  substitutes the ID, so CRLF line endings, 4-space indentation, ASCII \uXXXX escaping
  and non-standard Infinity tokens are all preserved. Nothing else in the ~94MB file
  is re-serialized. Before overwriting it makes a timestamped backup, then validates by
  re-parsing the result and deep-comparing it to an independently-built expected model
  (plus CRLF/ASCII/Infinity integrity guards). If anything mismatches it aborts and
  leaves the original untouched.

USAGE
  # list every war with its two sides (to get the exact name / ID):
  python3 ti_war_editor.py --list-wars

  # add a belligerent to an existing war (newest save is picked automatically):
  python3 ti_war_editor.py --war "<War Name or ID>" \
                           --attacker "<Nation>" --defender "<Nation>"

  # options
  #   --save PATH       act on a specific save        (default: newest non-backup *.json)
  #   --war NAME|ID     target war  (name substring, case-insensitive, or numeric ID)
  #   --attacker NAME|ID  add nation to attacking side (repeatable)
  #   --defender NAME|ID  add nation to defending side (repeatable)
  #   --dry-run         print the plan, write nothing
  # A timestamped .BACKUP-* copy of the save is ALWAYS written before any change
  # (there is deliberately no flag to skip it). Nations/wars accept a name
  # (unambiguous substring OK) or a numeric ID.
"""
import argparse, copy, glob, json, os, re, sys, time

from ti_config import find_save_dir
SAVES_DIR = str(find_save_dir() or os.path.expanduser("~/Documents/My Games/TerraInvicta/Saves"))
NATION_T  = b"PavonisInteractive.TerraInvicta.TINationState"
WAR_T     = b"PavonisInteractive.TerraInvicta.TIWarState"

# ---------------------------------------------------------------- byte scanners
def _match_pair(raw, b, openc, closec):
    """Index of the bracket/brace matching the one at `b` (string-aware)."""
    depth = 0; instr = False; esc = False
    for j in range(b, len(raw)):
        c = raw[j:j+1]
        if instr:
            if esc: esc = False
            elif c == b'\\': esc = True
            elif c == b'"': instr = False
        else:
            if c == b'"': instr = True
            elif c == openc: depth += 1
            elif c == closec:
                depth -= 1
                if depth == 0: return b, j
    raise ValueError("unbalanced bracket from %d" % b)

def _section_bracket(raw, typ):
    """(open '[' , close ']') for the gamestates section header  "<typ>": [ ... ]."""
    occ = [m.start() for m in re.finditer(re.escape(b'"%s": [' % typ), raw)]
    if len(occ) != 1:
        raise ValueError("expected 1 section header for %r, found %d" % (typ, len(occ)))
    b = raw.index(b'[', occ[0])
    return _match_pair(raw, b, b'[', b']')

def _elements(raw, typ):
    """{Key.value -> (obj_start, obj_end)} for every entry object in a section."""
    b, e = _section_bracket(raw, typ); p = b + 1; out = {}
    while p < e:
        while p < e and raw[p:p+1] in (b' ', b'\r', b'\n', b'\t', b','): p += 1
        if p >= e or raw[p:p+1] != b'{': break
        ob, oe = _match_pair(raw, p, b'{', b'}')
        m = re.search(rb'"Key":\s*\{\s*"value":\s*(-?\d+)', raw[ob:oe+1])
        out[int(m.group(1))] = (ob, oe); p = oe + 1
    return out

def _field_array(raw, obj_start, obj_end, field):
    """Absolute (open '[', close ']') for obj's  "field": [ ... ]."""
    seg = raw[obj_start:obj_end+1]
    m = re.search(rb'"' + re.escape(field) + rb'":\s*\[', seg)
    if not m: raise ValueError("field %r not found" % field)
    bo = seg.index(b'[', m.start())
    _, bc = _match_pair(seg, bo, b'[', b']')
    return obj_start + bo, obj_start + bc

def _top_objs(raw, open_idx, close_idx):
    """(start,end) of each {..} directly inside array [open_idx..close_idx]."""
    p = open_idx + 1; out = []
    while p < close_idx:
        while p < close_idx and raw[p:p+1] in (b' ', b'\r', b'\n', b'\t', b','): p += 1
        if p >= close_idx or raw[p:p+1] != b'{': break
        s, e = _match_pair(raw, p, b'{', b'}'); out.append((s, e)); p = e + 1
    return out

def _leading_ws(raw, idx):
    return raw[raw.rfind(b'\n', 0, idx) + 1: idx]

# ---------------------------------------------------------------- edit builders
def _append_value(raw, edits, open_idx, close_idx, ids):
    """Append {"value": id} objects to a value-array; builds fresh form if empty."""
    objs = _top_objs(raw, open_idx, close_idx)
    if objs:                                   # clone the last element's exact bytes
        ls, le = objs[-1]; ws = _leading_ws(raw, ls); tmpl = raw[ls:le+1]
        ins = b''.join(b',\r\n' + ws + re.sub(rb'("value":\s*)-?\d+', rb'\g<1>%d' % i, tmpl, count=1)
                       for i in ids)
        edits.append((le + 1, le + 1, ins))
    else:                                      # empty []: build with derived indent
        prefix = _leading_ws(raw, open_idx)    # e.g. b'                    "wars": '
        li = len(prefix) - len(prefix.lstrip(b' '))   # leading SPACES only (label indent)
        ei, vi, ci = b' ' * (li + 4), b' ' * (li + 8), b' ' * li
        blocks = [ei + b'{\r\n' + vi + b'"value": %d\r\n' % i + ei + b'}' for i in ids]
        edits.append((open_idx, close_idx + 1, b'[\r\n' + b',\r\n'.join(blocks) + b'\r\n' + ci + b']'))

def _append_cohesion(raw, edits, open_idx, close_idx, ids, value=b'0.0'):
    """Append {"Key":{"value":id},"Value":0.0} objects by cloning the last element."""
    objs = _top_objs(raw, open_idx, close_idx)
    ls, le = objs[-1]; ws = _leading_ws(raw, ls); tmpl = raw[ls:le+1]
    def mut(i):
        b1 = re.sub(rb'("value":\s*)-?\d+', rb'\g<1>%d' % i, tmpl, count=1)      # Key.value
        return re.sub(rb'("Value":\s*)[^\r\n]+', rb'\g<1>' + value, b1, count=1)  # -> 0.0
    edits.append((le + 1, le + 1, b''.join(b',\r\n' + ws + mut(i) for i in ids)))

# ---------------------------------------------------------------- resolution
def _load(path):
    raw = open(path, 'rb').read()
    return raw, json.loads(raw)

def _nation_names(obj):
    return {e["Value"]["ID"]["value"]: e["Value"].get("displayName")
            for e in obj["gamestates"][NATION_T.decode()]}

def _wars(obj):
    return [e["Value"] for e in obj["gamestates"][WAR_T.decode()]]

def _resolve_nation(token, names):
    if re.fullmatch(r'-?\d+', token):
        i = int(token)
        if i in names: return i
        sys.exit("No nation with ID %d" % i)
    tl = token.lower()
    cand = [i for i, n in names.items() if (n or '').lower() == tl] \
        or [i for i, n in names.items() if tl in (n or '').lower()]
    if len(cand) == 1: return cand[0]
    if not cand: sys.exit("No nation matches %r" % token)
    sys.exit("Ambiguous nation %r -> %s" % (token, [(i, names[i]) for i in cand]))

def _resolve_war(token, obj):
    W = _wars(obj)
    if re.fullmatch(r'-?\d+', token):
        m = [w for w in W if w["ID"]["value"] == int(token)]
        if m: return m[0]
        sys.exit("No war with ID %s" % token)
    tl = token.lower(); m = [w for w in W if tl in w["displayName"].lower()]
    if len(m) == 1: return m[0]
    if not m: sys.exit("No war matches %r" % token)
    sys.exit("Ambiguous war %r -> %s" % (token, [w["displayName"] for w in m]))

def _newest_save():
    cands = [p for p in glob.glob(os.path.join(SAVES_DIR, "*.json"))
             if "BACKUP" not in os.path.basename(p) and not p.endswith(".NEW")]
    if not cands: sys.exit("No saves found in " + SAVES_DIR)
    return max(cands, key=os.path.getmtime)

# ---------------------------------------------------------------- expected model
def _expected(orig, war_id, new_att, new_def, add_enemies):
    """Independently rebuild the intended parsed structure, for validation."""
    exp = copy.deepcopy(orig)
    W = next(w["Value"] for w in exp["gamestates"][WAR_T.decode()]
             if w["Value"]["ID"]["value"] == war_id)
    for i in new_att: W["_attackingAlliance"].append({"value": i})
    for i in new_def: W["_defendingAlliance"].append({"value": i})
    for i in new_att + new_def: W["cohesionGainByNation"].append({"Key": {"value": i}, "Value": 0.0})
    idx = {e["Value"]["ID"]["value"]: e["Value"] for e in exp["gamestates"][NATION_T.decode()]}
    for n, adds in add_enemies.items():
        for i in adds: idx[n]["wars"].append({"value": i})
    return exp

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Add belligerents to a Terra Invicta war.")
    ap.add_argument("--save")
    ap.add_argument("--war")
    ap.add_argument("--attacker", action="append", default=[], metavar="NATION")
    ap.add_argument("--defender", action="append", default=[], metavar="NATION")
    ap.add_argument("--list-wars", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    save = a.save or _newest_save()
    print("SAVE:", save)
    raw, obj = _load(save)
    names = _nation_names(obj)

    if a.list_wars:
        for w in _wars(obj):
            aa = [x["value"] for x in w["_attackingAlliance"]]
            da = [x["value"] for x in w["_defendingAlliance"]]
            print("\nID %d: %s" % (w["ID"]["value"], w["displayName"]))
            print("   attackers:", [names[i] for i in aa])
            print("   defenders:", [names[i] for i in da])
        return

    if not a.war or not (a.attacker or a.defender):
        sys.exit("Need --war and at least one --attacker/--defender (or --list-wars).")

    war = _resolve_war(a.war, obj); war_id = war["ID"]["value"]
    A = [x["value"] for x in war["_attackingAlliance"]]
    D = [x["value"] for x in war["_defendingAlliance"]]
    new_att = list(dict.fromkeys(_resolve_nation(t, names) for t in a.attacker))
    new_def = list(dict.fromkeys(_resolve_nation(t, names) for t in a.defender))

    part = set(A) | set(D)
    for n in new_att + new_def:
        if n in part:
            sys.exit("Nation %d (%s) is already a participant in war %d." % (n, names[n], war_id))
    if set(new_att) & set(new_def):
        sys.exit("A nation cannot join both sides.")

    Ap, Dp = A + new_att, D + new_def          # full sides after the edit
    nat_wars = {v["ID"]["value"]: [x["value"] for x in v["wars"]]
                for v in (e["Value"] for e in obj["gamestates"][NATION_T.decode()])}
    add_enemies = {}                           # nid -> [enemy ids to append, in order]
    for n in Ap:
        miss = [x for x in Dp if x not in set(nat_wars[n])]
        if miss: add_enemies[n] = miss
    for n in Dp:
        miss = [x for x in Ap if x not in set(nat_wars[n])]
        if miss: add_enemies[n] = miss

    # ---- report ----
    print("\nWAR %d: %s" % (war_id, war["displayName"]))
    print("  attacker side (leader %s):" % names[war["attacker"]["value"]],
          [names[i] for i in A], "+", [names[i] for i in new_att] or "-")
    print("  defender side (leader %s):" % names[war["defender"]["value"]],
          [names[i] for i in D], "+", [names[i] for i in new_def] or "-")
    print("  per-nation `wars` (enemy) updates:")
    for n, adds in add_enemies.items():
        print("    %-6d %-30s += %s" % (n, names[n], [names[i] for i in adds]))

    # ---- compute byte edits ----
    war_els, nat_els = _elements(raw, WAR_T), _elements(raw, NATION_T)
    ws_, we_ = war_els[war_id]; edits = []
    if new_att:
        o, c = _field_array(raw, ws_, we_, b"_attackingAlliance"); _append_value(raw, edits, o, c, new_att)
    if new_def:
        o, c = _field_array(raw, ws_, we_, b"_defendingAlliance"); _append_value(raw, edits, o, c, new_def)
    if new_att + new_def:
        o, c = _field_array(raw, ws_, we_, b"cohesionGainByNation"); _append_cohesion(raw, edits, o, c, new_att + new_def)
    for n, adds in add_enemies.items():
        ns, ne = nat_els[n]; o, c = _field_array(raw, ns, ne, b"wars"); _append_value(raw, edits, o, c, adds)

    if a.dry_run:
        print("\n[dry-run] %d byte-edits computed; nothing written." % len(edits)); return

    # ---- apply (descending offsets), then validate ----
    es = sorted(edits, key=lambda t: t[0], reverse=True)
    for x, y in zip(es, es[1:]):
        assert y[1] <= x[0], "overlapping edits"
    buf = bytearray(raw)
    for s, e, nb in es: buf[s:e] = nb

    new = json.loads(bytes(buf))
    if new != _expected(obj, war_id, new_att, new_def, add_enemies):
        sys.exit("VALIDATION FAILED: result != expected model. Original untouched.")
    assert bytes(buf).count(b'\n') == bytes(buf).count(b'\r\n'), "CRLF integrity lost"
    bytes(buf).decode('ascii')                                  # ASCII guard
    assert raw.count(b'Infinity') == bytes(buf).count(b'Infinity'), "Infinity token count changed"

    # ALWAYS back up the untouched original before replacing it — non-optional.
    bak = save + time.strftime(".BACKUP-%Y%m%d-%H%M%S")
    open(bak, 'wb').write(raw); print("\nbackup:", bak)
    tmp = save + ".NEW"; open(tmp, 'wb').write(buf); os.replace(tmp, save)
    json.load(open(save))                                       # final parse sanity
    print("DONE. Updated %s  (+%d bytes, %d edits)" % (save, len(buf) - len(raw), len(edits)))

if __name__ == "__main__":
    main()
