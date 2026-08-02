#!/usr/bin/env python3
"""
campaign_log_row.py — compute the 6 active save-by-save timeline rows for a campaign
log's "Save-by-save metrics timeline" section, formatted ready to paste. Each
analysis run should call this so the timeline accretes without hand-deriving
fields.

Tables (Table C was removed 2026-06-07; it pulled stale `cachedYearlyRevenue`):
  A  Alien hate              | Date Hate MC Floor Above Xeno Kills AlienInv SpaceStr
  B  Resource buffers (days) | Date Money Influence Ops Boost Metals Water Vol Nobles Fissiles
  D  Infrastructure          | Date Habs T1 T2 T3 Ships Mass(kt) CPs MC-use OpsC Mines(act/off/bld)
  E  Nation health           | anchor nations × (Coh Rest Ineq GDP$T)
  F  Faction + research thru  | Date ThisMo Cumulative TopRival(stale) AlienShips AlienHabs You(ships/habs/CPs)
  G  Tech progress           | Date FinishedGlobalTechs FinishedFactionProjects

Reuses extract_snapshot.py helpers (load_save, kv_items, get_factions,
extract_hab_inventory, extract_mine_inventory, get_game_date). For Table F's
"this month" throughput delta, pass --prev-cumulative (= prior row's
"Cumulative finished"); else it prints the cumulative and leaves the delta blank.

Table E's nations come from --nations A,B,C (templateNames), else config.json
"anchor_nations", else auto-detect (top 3 by GDP among nations where your
faction holds a control point).

Usage:
    python3 campaign_log_row.py <save.json> [--faction <templateName>] [--prev-cumulative N]
                                [--nations 2026_USA,2026_CHN,2026_RUS]
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_snapshot as er

MASK_PROJECTS = {'Project_StrategicDeception', 'Project_Maskirovka',
                 'Project_OperationalSecurity', 'Project_OperationalMisdirection'}
DIFF_MOD = {1: 0.05, 2: 0.30, 3: 0.60, 4: 1.0}   # Cinematic/Normal/Veteran/Brutal

# Resource keys in display order for Table B
RES_B = ['Money', 'Influence', 'Operations', 'Boost', 'Metals', 'Water',
         'Volatiles', 'NobleMetals', 'Fissiles']


def days_cover(stock, yearly):
    if yearly is None or yearly <= 0:
        return '∞'
    return f"{int(round(stock / (yearly / 365.0)))}d"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('save')
    ap.add_argument('--faction', default=None)
    ap.add_argument('--prev-cumulative', type=int, default=None)
    ap.add_argument('--nations', default=None,
                    help='comma-separated nation templateNames for Table E '
                         '(default: config anchor_nations, else auto-detect)')
    args = ap.parse_args()
    from ti_config import require_faction
    args.faction = require_faction(args.faction)

    d = er.load_save(args.save)
    gs = d['gamestates']
    date, _ = er.get_game_date(gs)
    factions = er.get_factions(gs)
    pid = er.faction_id_by_template(factions, args.faction)
    P = factions[pid]
    alien_id = er.faction_id_by_template(factions, 'AlienCouncil')

    gvs = gs.get('PavonisInteractive.TerraInvicta.TIGlobalValuesState', [])
    difficulty = gvs[0]['Value'].get('difficulty', 2) if gvs else 2
    diff_mod = DIFF_MOD.get(difficulty, 0.30)

    # ---- Table A: alien hate ----
    hate = P.get('assessedAlienHateOfMe', 0.0)
    mc_use = P.get('missionControlUsage', 0)
    n_mask = sum(1 for p in P.get('finishedProjectNames', []) if p in MASK_PROJECTS)
    floor = max(20.0, mc_use * diff_mod * (0.8 ** n_mask))
    above = hate - floor
    xeno = P.get('aliensRemoved', 0)
    alien_inv = P.get('alienInvestigations', 0)
    space_str = P.get('highestSpaceStrengthSinceLastAlienKnockdown', 0.0)
    kills = 0
    for e in P.get('Kills', []):
        k = e.get('Key', {})
        if (k.get('value') if isinstance(k, dict) else k) == alien_id:
            kills = len(e.get('Value', []))

    # ---- Table B: resource buffers ----
    res = P.get('resources', {})
    rev = P.get('cachedYearlyRevenue', {})
    b_cells = [days_cover(res.get(k, 0) or 0, rev.get(k)) for k in RES_B]

    # ---- Table D: infrastructure ----
    hi = er.extract_hab_inventory(gs, pid)
    habs = hi['habs']
    tier_ct = {1: 0, 2: 0, 3: 0}
    for h in habs:
        t = h.get('tier')
        if t in tier_ct:
            tier_ct[t] += 1
    n_habs = len(habs)
    # Ships attribute to a faction via their fleet (storedFaction fallback for reserve hulls)
    fleet_fac = {fid: er.fac_id_from_field(fv.get('faction'))
                 for fid, fv in er.kv_items(gs, 'PavonisInteractive.TerraInvicta.TISpaceFleetState')}

    def ship_fac(sv):
        flid = er.deref(sv.get('fleet'))
        return fleet_fac.get(flid) if flid is not None else er.fac_id_from_field(sv.get('storedFaction'))

    ship_states = [v for _, v in er.kv_items(gs, 'PavonisInteractive.TerraInvicta.TISpaceShipState')]
    ships = [v for v in ship_states if ship_fac(v) == pid]
    n_ships = len(ships)
    mass_kt = sum((v.get('currentMass_kg') or 0) for v in ships) / 1e6
    cps = sum(1 for _, c in er.kv_items(gs, 'PavonisInteractive.TerraInvicta.TIControlPoint')
              if er.fac_id_from_field(c.get('faction')) == pid)
    opsc = (hi['modules_built'].get('OperationsCenter', 0)
            + hi['modules_built'].get('CommandCenter', 0))
    mi = er.extract_mine_inventory(gs, pid)
    mines = f"{len(mi['active'])}/{len(mi['off'])}/{len(mi['building'])}"

    # ---- Table E: nation health ----
    anchor_templates = er.resolve_anchor_nations(gs, faction_template=args.faction,
                                                 cli_value=args.nations)
    nat = {tn: nv for _, nv in er.kv_items(gs, 'PavonisInteractive.TerraInvicta.TINationState')
           for tn in [nv.get('templateName')]}
    e_cells = []
    for tname in anchor_templates:
        n = nat.get(tname, {})
        coh = n.get('cohesion'); rest = n.get('cohesionRestState_dailyCache')
        ineq = n.get('inequality'); gdp = (n.get('GDP') or 0) / 1e12
        e_cells += [f"{coh:.2f}" if coh is not None else '-',
                    f"{rest:.2f}" if rest is not None else '-',
                    f"{ineq:.2f}" if ineq is not None else '-',
                    f"{gdp:.1f}" if gdp else '-']

    # ---- Table F + G: research / tech ----
    grs = gs['PavonisInteractive.TerraInvicta.TIGlobalResearchState'][0]['Value']
    n_global = len(grs.get('finishedTechsNames', []))
    n_proj = len(P.get('finishedProjectNames', []))
    cumulative = n_global + n_proj
    this_mo = (cumulative - args.prev_cumulative) if args.prev_cumulative is not None else None
    # top rival research (stale cache)
    top_rival = 0.0
    for fid, fv in factions.items():
        if fid in (pid, alien_id):
            continue
        top_rival = max(top_rival, fv.get('cachedYearlyRevenue', {}).get('Research', 0) or 0)
    alien_ships = sum(1 for v in ship_states if ship_fac(v) == alien_id)
    alien_habs = sum(1 for _, h in er.kv_items(gs, 'PavonisInteractive.TerraInvicta.TIHabState')
                     if er.fac_id_from_field(h.get('faction')) == alien_id)

    # ---- emit ----
    print(f"# Save: {args.save}")
    print(f"# Game date: {date}  Difficulty: {difficulty} (mod {diff_mod})  Masking projects done: {n_mask}\n")
    print("### Table A")
    print(f"| {date} | {hate:.1f} | {mc_use} | {floor:.1f} | {above:.1f} | {xeno} | {kills} | {alien_inv} | {space_str:.3f} |")
    print("\n### Table B")
    print(f"| {date} | " + " | ".join(b_cells) + " |")
    print("\n### Table D")
    print(f"| {date} | {n_habs} | {tier_ct[1]} | {tier_ct[2]} | {tier_ct[3]} | {n_ships} | {mass_kt:.0f} | {cps} | {mc_use} | {opsc} | {mines} |")
    e_labels = " / ".join(er.nation_label(t) for t in anchor_templates)
    print(f"\n### Table E   [anchors: {e_labels} — each × Coh Rest Ineq GDP$T]")
    print("# NOTE: changing anchor nations mid-campaign breaks log-column comparability.")
    print(f"| {date} | " + " | ".join(e_cells) + " |")
    print("\n### Table F")
    tm = '?' if this_mo is None else str(this_mo)
    print(f"| {date} | {tm} | {cumulative} | {top_rival:,.0f} | {alien_ships} | {alien_habs} | {n_ships} / {n_habs} / {cps} |")
    print("\n### Table G")
    print(f"| {date} | {n_global} | {n_proj} |")


if __name__ == '__main__':
    main()
