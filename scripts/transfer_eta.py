#!/usr/bin/env python3
"""Estimate fleet transfer time the way the game's transfer planner does — accel-limited
burn/coast/burn — instead of the old "coast at ΔV/2" hack, which is ~40% optimistic for
low-accel torch ships (a 2.7 mg settler: Quaoar crude 32 wk vs actual 51.4 wk).

Usage:
    python3 transfer_eta.py <save.json> --fleet "<fleet name>" [--to Quaoar Pluto ...]
        [--faction <templateName>] [--dv-frac 0.975]

    --to omitted → ETA table to ALL prospect-worthy dwarf planets / listed bodies.
    --dv-frac: fraction of current ΔV the planner may spend (default 0.975 — the in-game
      default thrust profile spends ~97.5%, e.g. 627.5 of 643.6 kps on the Quaoar leg).

Physics (constant current accel a, straight-line distance d, ΔV budget b):
    brachistochrone needs dv = 2·sqrt(d·a); if dv <= b:  t = 2·sqrt(d/a)     (accel-limited)
    else burn to v = b/2, coast, decel:                   t = d/v + v/a       (ΔV-limited)

DECOMPILED-SOURCE GROUNDING (verified 2026-07-13, MasterTransferPlanner.cs +
TorchTransfer.cs in Armandox33/Terra-Invicta-AI-Assistant):
  - This model IS the game's own quick estimator `GetLinearDuration_s` (burn time
    min(sqrt(2·(d/2)/a), (ΔV/2)/a), coast the rest) — theirs uses FULL ΔV halves and
    AverageDistanceBetweenTwoSpaceObjects_m.
  - The interactive planner is exact: `CalculateTorchTransfers` scans transit durations in
    1-week steps (sun barycenter) and Newton-solves `TorchTransfer.Solve` — a two-burn
    intercept of the target's position AT ARRIVAL TIME in the mean-velocity co-moving
    frame, keeping the cheapest feasible ΔV per duration.
  - The residual between this script and the planner is the MOVING-TARGET term: a Kuiper
    dwarf at ~4.5 kps over a ~1 yr transit moves ~1 AU — the observed 4-7% gap. Not
    modeled here (needs orbit propagation); the planner optimizes the window, so real
    times come in SHORTER than this estimate.

CALIBRATION vs in-game planner (2033-07-03 save, a settler fleet a=0.02604 m/s², ΔV 643.6,
docked Low Callisto Orbit; game numbers from reference-campaign transfer-planner screenshots):
    Quaoar: game 51.39 wk / ΔV 627.5  → model 53.4 wk (+3.9%)
    Pluto:  game 46.20 wk / ΔV 619.2  → model 49.3 wk (+6.7%)
Model runs LONG by ~4-7% (target motion + launch-geometry optimization not modeled).
Treat output as +0/-7%; the in-game planner is truth.
"""
import json, gzip, argparse, math

AU = 1.496e11
DEFAULT_BODIES = ['Quaoar', 'Pluto', 'Haumea', 'Makemake', 'Goibniu', 'Meng Po', 'Orcus',
                  'Salacia', 'Varuna', 'Ixion', 'Triton', 'Titan', 'Rhea', 'Ariel', 'Oberon']


def key(k):
    return k['value'] if isinstance(k, dict) else k


def load_save(path):
    raw = open(path, 'rb').read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return json.loads(raw)


def eta_seconds(d_m, a_ms2, dv_budget_mps):
    """Burn/coast/burn time. Returns (seconds, dv_spent_mps, mode)."""
    dv_brach = 2 * math.sqrt(d_m * a_ms2)
    if dv_brach <= dv_budget_mps:
        return 2 * math.sqrt(d_m / a_ms2), dv_brach, 'brach'
    v = dv_budget_mps / 2
    return d_m / v + v / a_ms2, dv_budget_mps, 'coast'


def fleet_perf(fleet, ships, dv_frac):
    """(cruise accel m/s², usable ΔV m/s, position) — slowest/thirstiest ship governs."""
    p = fleet.get('globalPosition') or {}
    fp = (p.get('x', 0), p.get('y', 0), p.get('z', 0))
    fs = [ships[key(s)] for s in fleet['ships'] if key(s) in ships]
    a = min(s.get('cruiseAcceleration_mps2') or 0 for s in fs)
    dv = min(s.get('currentDeltaV_kps') or 0 for s in fs) * 1000
    return a, dv * dv_frac, fp, dv


def my_fleets(gs, fid, kits_only=False):
    """[(name, fleetValue)] for the faction. kits_only → only fleets carrying an outpost/hab kit
    (the colony/settler ships). Names come from displayNameByFaction (P5)."""
    out = []
    for f in gs['PavonisInteractive.TerraInvicta.TISpaceFleetState']:
        v = f['Value']
        if key(v.get('faction')) != fid or not v.get('ships'):
            continue
        nm = next((e.get('Value') for e in (v.get('displayNameByFaction') or [])
                   if key(e.get('Key')) == fid and e.get('Value')), None)
        if nm is None:
            continue
        out.append((nm, v))
    return out


def kit_fleet_names(gs, fid):
    """Names of fleets carrying an outpost/hab kit — the ships that can actually found."""
    ships = {key(s['Key']): s['Value'] for s in gs['PavonisInteractive.TerraInvicta.TISpaceShipState']}
    me = [f['Value'] for f in gs['PavonisInteractive.TerraInvicta.TIFactionState']
          if key(f['Key']) == fid][0]
    designs = {d['dataName']: d for d in me.get('shipDesigns', [])}
    names = []
    for nm, v in my_fleets(gs, fid):
        for sid in v['ships']:
            s = ships.get(key(sid))
            if not s:
                continue
            d = designs.get(s.get('templateName'), {})
            mods = [m.get('moduleName') or '' for m in (d.get('moduleTemplateEntries') or [])]
            if any('Kit' in m for m in mods):
                names.append(nm)
                break
    return names


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('save')
    ap.add_argument('--fleet', help='fleet name; "all" = every fleet, "kits" = colony ships only')
    ap.add_argument('--to', nargs='*', default=None)
    ap.add_argument('--faction', default=None)
    ap.add_argument('--dv-frac', type=float, default=0.975)
    ap.add_argument('--matrix', action='store_true',
                    help='fleets × targets grid (best ship per target); implies --fleet kits')
    args = ap.parse_args()
    from ti_config import require_faction
    args.faction = require_faction(args.faction)

    gs = load_save(args.save)['gamestates']
    fid = [key(f['Key']) for f in gs['PavonisInteractive.TerraInvicta.TIFactionState']
           if f['Value'].get('templateName') == args.faction][0]
    pos = {}
    for b in gs['PavonisInteractive.TerraInvicta.TISpaceBodyState']:
        v = b['Value']
        p = v.get('globalPosition') or {}
        pos[v.get('displayName')] = (p.get('x', 0), p.get('y', 0), p.get('z', 0))
    ships = {key(s['Key']): s['Value'] for s in gs['PavonisInteractive.TerraInvicta.TISpaceShipState']}

    sel = args.fleet or ('kits' if args.matrix else None)
    if sel is None:
        raise SystemExit('need --fleet NAME | --fleet all | --fleet kits | --matrix')
    if sel == 'kits':
        want = set(kit_fleet_names(gs, fid))
    elif sel == 'all':
        want = None
    else:
        want = {sel}
    fleets = [(nm, v) for nm, v in my_fleets(gs, fid) if want is None or nm in want]
    if not fleets:
        raise SystemExit(f'no fleet matched "{sel}"')
    targets = args.to or DEFAULT_BODIES

    if args.matrix or len(fleets) > 1:
        # fleets × targets; best (fastest) ship per target
        print(f"# ETA matrix — {len(fleets)} fleets × {len(targets)} targets "
              f"(ΔV×{args.dv_frac}; model runs +0/−7% vs the in-game planner)")
        best = {}
        grid = {}
        for nm, v in fleets:
            a, budget, fp, dv = fleet_perf(v, ships, args.dv_frac)
            for b in targets:
                if b not in pos:
                    continue
                if a <= 0 or budget <= 0:
                    continue
                d = math.dist(pos[b], fp)
                t, spent, mode = eta_seconds(d, a, budget)
                grid[(nm, b)] = (t, d, mode)
                if b not in best or t < best[b][0]:
                    best[b] = (t, nm, d, mode)
        w = max(len(n) for n, _ in fleets) + 1
        print(f"{'target':18}" + ''.join(f"{n[:w-1]:>{w}}" for n, _ in fleets) + "   BEST")
        for b in targets:
            if b not in pos:
                print(f"{b:18} — not found")
                continue
            row = f"{b:18}"
            for nm, _ in fleets:
                g = grid.get((nm, b))
                row += f"{(f'{g[0]/604800:.0f}w' if g else '—'):>{w}}"
            bb = best.get(b)
            row += f"   {bb[1]} ({bb[0]/604800:.1f}w, {bb[2]/AU:.1f}AU, {bb[3]})" if bb else "   —"
            print(row)
        return

    nm, fleet = fleets[0]
    a, budget, fp, dv = fleet_perf(fleet, ships, args.dv_frac)
    print(f"# {nm}: a={a * 1000:.2f} mm/s² ({a / 9.81 * 1000:.2f} mg), "
          f"ΔV {dv / 1000:.1f} kps × {args.dv_frac} = {budget / 1000:.1f} kps usable")
    print(f"{'body':16} {'AU':>6} {'ETA wk':>7} {'ETA':>9} {'ΔV kps':>7}  mode   (±5%; in-game planner is truth)")
    rows = []
    for b in targets:
        if b not in pos:
            print(f'{b:16} — not found')
            continue
        d = math.dist(pos[b], fp)
        t, spent, mode = eta_seconds(d, a, budget)
        rows.append((t, b, d, spent, mode))
    for t, b, d, spent, mode in sorted(rows):
        wk = t / 604800
        pretty = f'{t / 86400:.0f}d' if t < 120 * 86400 else f'{t / 86400 / 30.44:.1f}mo'
        print(f'{b:16} {d / AU:6.1f} {wk:7.1f} {pretty:>9} {spent / 1000:7.0f}  {mode}')


if __name__ == '__main__':
    main()
