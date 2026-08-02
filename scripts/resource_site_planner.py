#!/usr/bin/env python3
"""Rank surveyed high-yield resource sites for acquisition: ownership, diplomacy filter,
distance to the player's fleets/yards, and the assets able to take or found them.

Usage:
    python3 resource_site_planner.py <save.json> [--resource fissiles|metals|water|volatiles|nobles|all] [--min-monthly 8]
        [--faction <templateName>] [--avoid EscapeCouncil,DestroyCouncil]
        [--unclaimed-only] [--weights metals=8,water=5,nobles=5,fissiles=4,volatiles=4]

    --resource all → combined weighted score across all five resources (colony-site
    planning: "where should my outpost-kit ships found the next surface mine"). Adds a
    per-site column for the nearest OUTPOST-KIT fleet (kits counted from the live ship
    utilityModules, not the design — kits are consumed on founding; ⚠ a ship UNDER
    REPAIR reports an empty/partial utilityModules list until repair completes, so a
    kit ship mid-repair shows kits=0 — cross-check damaged ships before writing one
    off as spent; save-verified 2026-07 on two mid-repair kit ships), an ETA from the
    shared accel-limited burn/coast/burn model in transfer_eta.py (+0/−7% vs the
    in-game planner — truth), and each in-transfer kit fleet's DESTINATION + arrival
    date resolved from `trajectory.destination` (prevents double-booking a target).

Output: per-site table (raw monthly yield, current hab+owner, distance from the player's
nearest shipyard hab and nearest marine-carrying fleet) + player asset summary (marine
fleets with dV, outpost-kit ships, shipyard habs). Raw site rates are for RANKING only
(E15/E20: actual income = raw × tier × K).

⚠ SPOILER CAVEAT (2026-07-05, SOLVED 2026-07-13): TIHabSiteState carries TRUE yields even
for UNPROSPECTED sites, whose in-game display is only a range PRIOR — and the prior can be
plain WRONG (observed: one site showed metals 80-120 pre-survey, true 158; another
showed 0-25, true 65). Quoting exact values — or even a ranking derived from them — for
unprospected bodies is a CHEAT. Prospected state IS in the save (decompiled
`TIFactionState.Prospected()` = `GetIntel(spaceBody) >= 1.0`): the faction's `intel` array,
keyed by SPACE-BODY gamestate ID. intel 1.0 = prospected (exact yields visible in-game);
0.1 = prospector/probe en route (`LaunchProspector`); absent = dark. This script now
AUTO-REDACTS: sites on non-prospected bodies are excluded from the ranked table and only
summarized by body name + en-route status, never by yield.

FOUNDING RULES (2026-07-13):
- Unprospected sites cannot be founded. Ship-based prospecting needs the `Prospector`
  specialModuleRule — carried by MobileSpaceScienceLab (200 t utility). Check each
  colony-ship design's utility modules: designs without the lab can only found
  ALREADY-prospected sites.
- A powered Nanofactory/NanofacturingComplex/ConstructionModule hab founds in-range sites
  directly (click-to-colonize, no colony ship). Never recommend sailing a kit ship to a body
  that's already inside a founder hab's range (e.g. Ganymede/Europa with a Jupiter
  nanofactory). This is now computed per-site (E30, via free_founding.FreeFounding — the same
  logic colony_planner uses): free-foundable sites show "no ship — free-found Tn" in the
  dispatch column and are never assigned a kit fleet + ETA. Kit-fleet ETAs remain for sites
  that genuinely need a ship (e.g. lone belt asteroids, each its own sun-orbiting object).
"""
TRANSFER_DEST_NOTE = """An in-transfer fleet's destination IS readable (correcting an earlier
"not stored" claim that only inspected trajectory.Segments — those end Sol-barycentric with
null endTimes and never name the target): `fleet.trajectory.destination` is a TIOrbitState
ref — resolve via `orbit.barycenter` to the body — and `trajectory.arrivalTime` is the
arrival date (save-verified against the in-game readout, 2026-07). This script prints both
for every kit fleet, because the failure it prevents is real: one settler fleet was already
bound for a body when that same body was recommended to its sister ship."""

import json, gzip, argparse, os, math
from collections import defaultdict
from free_founding import FreeFounding  # E30 free-founding (shared with colony_planner)

AU = 1.496e11
MAR = {'MarineAssaultUnit': 4, 'AdvancedMarineAssaultUnit': 6, 'EliteMarineAssaultUnit': 8}


def key(k):
    return k['value'] if isinstance(k, dict) else k


def load_save(path):
    raw = open(path, 'rb').read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return json.loads(raw)


def fleet_name(v, my_fid):
    """Player fleet names live in displayNameByFaction (per-faction map); displayName is
    often empty and rivals see procedural Romeo-names (save-verified 2026-07)."""
    for e in (v.get('displayNameByFaction') or []):
        if key(e.get('Key')) == my_fid and e.get('Value'):
            return e['Value']
    return v.get('displayName') or '(unnamed)'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('save')
    ap.add_argument('--resource', default='fissiles')
    ap.add_argument('--min-monthly', type=float, default=8.0)
    ap.add_argument('--faction', default=None)
    ap.add_argument('--avoid', default='EscapeCouncil,DestroyCouncil',
                    help='factions whose sites are politically off-limits')
    ap.add_argument('--unclaimed-only', action='store_true',
                    help='drop sites that already have any hab on them')
    ap.add_argument('--weights', default='metals=8,water=5,nobles=5,fissiles=4,volatiles=4',
                    help='resource weights for --resource all combined score')
    args = ap.parse_args()
    from ti_config import require_faction
    args.faction = require_faction(args.faction)
    avoid = set(x for x in args.avoid.split(',') if x)
    weights = {}
    for tok in args.weights.split(','):
        k, _, v = tok.partition('=')
        weights[k.strip()] = float(v or 1)

    gs = load_save(args.save)['gamestates']
    facs = {key(f['Key']): f['Value'] for f in gs['PavonisInteractive.TerraInvicta.TIFactionState']}
    fname = {k: v.get('templateName') for k, v in facs.items()}
    my_fid = [k for k, v in fname.items() if v == args.faction][0]
    me = facs[my_fid]

    bodies, pos = {}, {}
    for b in gs['PavonisInteractive.TerraInvicta.TISpaceBodyState']:
        v = b['Value']
        bodies[key(b['Key'])] = v.get('displayName')
        p = v.get('globalPosition') or {}
        pos[v.get('displayName')] = (p.get('x', 0), p.get('y', 0), p.get('z', 0))

    habs = {key(h['Key']): h['Value'] for h in gs['PavonisInteractive.TerraInvicta.TIHabState']}
    sites = {key(s['Key']): s['Value'] for s in gs.get('PavonisInteractive.TerraInvicta.TIHabSiteState', [])}
    orbits = {key(o['Key']): o['Value'] for o in gs.get('PavonisInteractive.TerraInvicta.TIOrbitState', [])}

    # E30: sites in a sun-system where the player already holds a hab with an ACTIVE
    # CanFoundTierN module (ConstructionModule/Nanofactory/NanofacturingComplex) can be
    # founded directly — no ship, no outpost kit (e.g. any Jupiter nanofactory covers all
    # Jovian moons). Same computation colony_planner uses, so the two can't drift.
    free_founding = FreeFounding(gs, my_fid, habs=habs, sites=sites)

    def transfer_dest(v):
        """(destination body name, 'YYYY-MM-DD' arrival) for an in-transfer fleet — see
        TRANSFER_DEST_NOTE. destination is usually a TIOrbitState; fall back to a body id."""
        tr = v.get('trajectory')
        if not tr:
            return None, None
        dest = None
        d = tr.get('destination')
        if d is not None:
            did = key(d)
            if did in orbits:
                bc = orbits[did].get('barycenter')
                if bc is not None:
                    dest = bodies.get(key(bc))
            dest = dest or bodies.get(did)
        at = tr.get('arrivalTime') or {}
        arr = f"{at['year']}-{at.get('month', 0):02d}-{at.get('day', 0):02d}" if at.get('year') else None
        return dest, arr

    def site_body_id(st):
        for f in ('parentBody', 'spaceBody', 'naturalSpaceObject'):
            if st.get(f) is not None:
                return key(st[f])
        return None

    def site_body(st):
        return bodies.get(site_body_id(st))

    # prospected = faction intel on the body >= 1.0 (TIFactionState.Prospected, decompiled);
    # 0.1 = prospector en route. Yields of non-prospected bodies are hidden in-game — redact.
    body_intel = {key(e['Key']): e['Value'] for e in (me.get('intel') or []) if key(e['Key']) in bodies}

    # site -> existing hab (owner)
    site_hab = {}
    for hid, h in habs.items():
        sid = key(h.get('habSite')) if h.get('habSite') is not None else None
        if sid is not None:
            site_hab[sid] = (h.get('displayName'), fname.get(key(h.get('faction'))))

    # player shipyard habs + founding habs, with positions
    sec2hab = {}
    for hid, h in habs.items():
        for s in (h.get('sectors') or []):
            sec2hab[key(s)] = hid
    yard_habs, founder_habs = {}, {}
    for m in gs['PavonisInteractive.TerraInvicta.TIHabModuleState']:
        v = m['Value']
        if not (v.get('exists') and v.get('constructionCompleted') and not v.get('destroyed')):
            continue
        hid = sec2hab.get(key(v.get('sector')))
        if hid is None or key(habs[hid].get('faction')) != my_fid:
            continue
        tn = v.get('templateName') or ''
        if any(x in tn for x in ('Shipyard', 'Spaceworks')):
            yard_habs[hid] = habs[hid]
        if v.get('powered') and any(x in tn for x in ('Nanofactory', 'NanofacturingComplex', 'ConstructionModule')):
            founder_habs[hid] = habs[hid]

    def hab_pos(h):
        sid = key(h.get('habSite')) if h.get('habSite') is not None else None
        if sid is not None and sid in sites:
            b = site_body(sites[sid])
            if b and b in pos:
                return pos[b], b
        return None, '(orbital)'

    yard_pts = []
    for hid, h in yard_habs.items():
        p, b = hab_pos(h)
        if p:
            yard_pts.append((h.get('displayName'), b, p))

    # player fleets: marines / kits / dV
    ships = {key(s['Key']): s['Value'] for s in gs['PavonisInteractive.TerraInvicta.TISpaceShipState']}
    design = {d['dataName']: d for d in me.get('shipDesigns', [])}

    def ship_mods(s):
        d = design.get(s.get('templateName'), {})
        return [e.get('moduleName') for e in (d.get('moduleTemplateEntries') or [])], d.get('_displayName', '?')

    fleets = []
    for f in gs['PavonisInteractive.TerraInvicta.TISpaceFleetState']:
        v = f['Value']
        if key(v.get('faction')) != my_fid or not v.get('ships'):
            continue
        mar = kits = 0
        classes = defaultdict(int)
        dvs, mxs, accs = [], [], []
        for sid in v.get('ships', []):
            s = ships.get(key(sid))
            if not s:
                continue
            mods, cls = ship_mods(s)
            classes[cls] += 1
            mar += sum(MAR.get(m, 0) for m in (mods or []) if m)
            # kits from LIVE utilityModules (consumed on founding); design list overcounts
            live = [e.get('moduleTemplateName') for e in (s.get('utilityModules') or [])]
            kits += sum(1 for m in live if m and 'OutpostKit' in m)
            dvs.append(s.get('currentDeltaV_kps') or 0)
            mxs.append(s.get('currentMaxDeltaV_kps') or 0)
            accs.append(s.get('cruiseAcceleration_mps2') or 0)
        p = v.get('globalPosition') or {}
        fp = (p.get('x', 0), p.get('y', 0), p.get('z', 0))
        near = min(pos.items(), key=lambda kv: math.dist(kv[1], fp))[0] if pos else '?'
        dest, arr = transfer_dest(v)
        fleets.append({'name': fleet_name(v, my_fid), 'near': near, 'pos': fp,
                       'n': len(v.get('ships', [])), 'marines': mar, 'kits': kits,
                       'min_dv': min(dvs) if dvs else 0, 'min_maxdv': min(mxs) if mxs else 0,
                       'min_acc': min(accs) if accs else 0,
                       'transfer': v.get('trajectory') is not None, 'dest': dest, 'arrival': arr,
                       'comp': ', '.join(f'{c}×{n}' for c, n in sorted(classes.items(), key=lambda x: -x[1])[:4])})

    kit_fleets = [f for f in fleets if f['kits'] > 0]
    RES = ('metals', 'water', 'volatiles', 'nobles', 'fissiles')
    combined = args.resource == 'all'
    rows = []
    hidden = defaultdict(lambda: [0, 0.0])  # body -> [n_vacant_sites, intel]
    for sid, st in sites.items():
        bi = body_intel.get(site_body_id(st), 0.0)
        if bi < 1.0:
            if not site_hab.get(sid):
                h = hidden[site_body(st)]
                h[0] += 1
                h[1] = bi
            continue
        per = {r: (st.get(r + '_day') or 0) * 30.44 for r in RES}
        if combined:
            score = sum(per[r] * weights.get(r, 1) for r in RES)
            monthly = sum(per.values())
        else:
            score = monthly = per.get(args.resource, (st.get(args.resource + '_day') or 0) * 30.44)
        if monthly < args.min_monthly:
            continue
        b = site_body(st)
        hn, hf = site_hab.get(sid, (None, None))
        if args.unclaimed_only and hn:
            continue
        free_t = free_founding.free_found_tier(site_body_id(st))  # E30: 0 = needs a ship+kit
        bp = pos.get(b)
        d_yard = min((math.dist(bp, yp) / AU, yn, yb) for yn, yb, yp in yard_pts) if (bp and yard_pts) else (None, '', '')
        # free-foundable sites need no ship, so don't assign a kit fleet + ETA to them
        d_kit = (min(((math.dist(bp, f['pos']) / AU, f) for f in kit_fleets), key=lambda x: x[0])
                 if (not free_t and bp and kit_fleets) else None)
        rows.append({'site': st.get('displayName') or f'site{sid}', 'body': b, 'monthly_raw': monthly,
                     'score': score, 'per': per, 'free_tier': free_t,
                     'hab': hn, 'owner': hf, 'd_yard_au': d_yard[0], 'yard': f'{d_yard[1]} ({d_yard[2]})',
                     'd_kit_au': d_kit[0] if d_kit else None, 'kit_fleet': d_kit[1] if d_kit else None})
    rows.sort(key=lambda x: -x['score'])

    print(f"# {args.resource} site acquisition — {os.path.basename(args.save)}")
    print("Only PROSPECTED bodies are ranked (faction intel ≥ 1.0); unprospected yields are "
          "hidden in-game and redacted here.")
    if combined:
        print(f"weights: {weights}")
    print(f"\n## Candidate sites (raw monthly ≥ {args.min_monthly}; RANKING numbers, not income — E15)")
    hdr_yield = 'met/H2O/vol/nob/fis (raw/mo)' if combined else 'raw/mo'
    print(f"{'site':26} {'body':16} {'score':>7} {hdr_yield:>29} {'owner':14} {'dispatch (AU→kit/free)':24} {'~ETA':>6} AU→my yard")
    for r in rows:
        own = r['owner'] or ('MINE' if r['hab'] and r['owner'] == args.faction else '— unclaimed')
        if r['owner'] == args.faction:
            own = 'MINE'
        flag = ' ⛔avoid' if r['owner'] in avoid else ''
        d = f"{r['d_yard_au']:.2f}" if r['d_yard_au'] is not None else '?'
        p = r['per']
        ycol = ('/'.join(f"{p[x]:.0f}" for x in RES)) if combined else f"{r['monthly_raw']:.1f}"
        # E30: free-founding sites need no ship; only ship-needed sites get a kit fleet + ETA
        eta = ''
        if r['free_tier']:
            kcol = f"no ship — free-found T{r['free_tier']}"
        elif r['d_kit_au'] is not None:
            kcol = f"{r['d_kit_au']:.2f} {r['kit_fleet']['name']}"
            # accel-limited burn/coast/burn (shared model, +0/−7% vs the in-game planner)
            kf = r['kit_fleet']
            if kf['min_maxdv'] > 0 and kf['min_acc'] > 0:
                from transfer_eta import eta_seconds
                t, _, _ = eta_seconds(r['d_kit_au'] * AU, kf['min_acc'], kf['min_maxdv'] * 1000 * 0.975)
                eta = f'{t / 86400:.0f}d' if t < 100 * 86400 else f'{t / 86400 / 30.44:.1f}mo'
        else:
            kcol = '—'
        print(f"{r['site'][:26]:26} {str(r['body'])[:16]:16} {r['score']:7.0f} {ycol:>29} {(own or '')[:14]:14}{flag} {kcol[:24]:24} {eta:>6} {d}")

    if hidden:
        enroute = sorted((b for b, (n, i) in hidden.items() if i >= 0.1), key=str)
        dark = sorted((b for b, (n, i) in hidden.items() if i < 0.1), key=str)
        print(f"\n## Redacted: {sum(n for n, _ in hidden.values())} vacant sites on {len(hidden)} unprospected bodies")
        if enroute:
            print(f"  prospector EN ROUTE ({len(enroute)}): " + ', '.join(f'{b}({hidden[b][0]})' for b in enroute))
        if dark:
            print(f"  no prospecting ({len(dark)}): " + ', '.join(f'{b}({hidden[b][0]})' for b in dark[:30]) + (' …' if len(dark) > 30 else ''))

    if kit_fleets:
        print(f"\n## Outpost-kit fleets (live kit count; ETAs = burn/coast/burn model, planner is truth)")
        for f in sorted(kit_fleets, key=lambda x: x['name']):
            t = ''
            if f['transfer']:
                t = f" [IN TRANSFER → {f['dest'] or '?'}" + (f", arrives {f['arrival']}]" if f['arrival'] else ']')
            print(f"  {f['name'][:20]:20} near {f['near'][:14]:14} kits={f['kits']} ΔV cur/max {f['min_dv']:.0f}/{f['min_maxdv']:.0f} kps{t}  [{f['comp']}]")
        if any(f['transfer'] for f in kit_fleets):
            print("  ⚠ in-transfer fleets are COMMITTED — never assign their destination to another kit ship.")

    print(f"\n## My fleets (marines / kits / dV)")
    for f in sorted(fleets, key=lambda x: -x['marines']):
        if f['marines'] or f['kits'] or f['n'] >= 4:
            t = ' [IN TRANSFER]' if f['transfer'] else ''
            print(f"  {f['name'][:20]:20} near {f['near'][:14]:14} ships={f['n']:3} marines={f['marines']:3} kits={f['kits']} "
                  f"ΔV cur/max {f['min_dv']:.0f}/{f['min_maxdv']:.0f} kps{t}  [{f['comp']}]")

    print(f"\n## My shipyard habs ({len(yard_pts)}) — build-local option")
    seen = set()
    for yn, yb, _ in yard_pts:
        if yb not in seen:
            seen.add(yb)
            names = [n for n, b, _ in yard_pts if b == yb]
            print(f"  {yb}: {len(names)} yard-hab(s) — {', '.join(names[:3])}")
    print(f"\nFounding habs (powered Nanofactory/ConstructionModule): {len(founder_habs)} — unclaimed sites in range can be founded directly, no ship needed.")


if __name__ == '__main__':
    main()
