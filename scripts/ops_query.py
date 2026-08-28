#!/usr/bin/env python3
"""One-command military/operational sitrep over a Terra Invicta save: all your
fleets + transits, councilor locations & missions, an optional theater
drill-down around any body/hab, ships under construction, shipyard geography,
stockpiles, and the alien fleet order of battle ranked by summed design SCV.

Usage examples:
  python3 ops_query.py --faction <templateName>
      Full sitrep on the newest save (theater/ship-name sections skipped).
  python3 ops_query.py --faction <templateName> --theater Ceres --ship-name Orion
      Adds a Ceres theater drill-down and a search for ships named *Orion*.
  python3 ops_query.py mysave.json --faction HumanityFirst --section fleets,aliens
      Only the fleet list and the alien order of battle, from a specific save.

Flags:
  save                 positional, optional — save .json/.gz (default: newest save)
  --faction TEMPLATE   your faction templateName (or via ti_config default)
  --theater SUBSTR     drill into any body/hab whose displayName contains SUBSTR
  --ship-name SUBSTR   search your fleets for ships whose name contains SUBSTR
  --section a,b,...    subset of: fleets,councilors,theater,construction,aliens
"""
import argparse
import json, os
from collections import defaultdict

import sys
from ti_config import newest_save, require_faction

SECTIONS = ("fleets", "councilors", "theater", "construction", "aliens")


def parse_args():
    ap = argparse.ArgumentParser(
        description="One-command military/operational sitrep over a Terra Invicta save.")
    ap.add_argument("save", nargs="?", default=None,
                    help="save file (.json or .gz); default: newest save auto-detected")
    ap.add_argument("--faction", default=None,
                    help="your faction templateName (e.g. ResistCouncil)")
    ap.add_argument("--theater", default=None, metavar="SUBSTR",
                    help="body/hab displayName substring to drill into (case-insensitive)")
    ap.add_argument("--ship-name", default=None, metavar="SUBSTR",
                    help="search your fleets for ships whose displayName contains SUBSTR")
    ap.add_argument("--section", default=None, metavar="a,b,...",
                    help="comma-separated subset of: " + ",".join(SECTIONS) + " (default: all)")
    args = ap.parse_args()

    args.save = args.save or str(newest_save() or "")
    if not args.save:
        ap.error("No save given and none auto-detected; pass a save path.")
    args.faction = require_faction(args.faction)
    if args.section:
        wanted = [s.strip() for s in args.section.split(",") if s.strip()]
        bad = [s for s in wanted if s not in SECTIONS]
        if bad:
            ap.error(f"unknown --section value(s): {', '.join(bad)} (choose from {', '.join(SECTIONS)})")
        args.sections = set(wanted)
    else:
        args.sections = set(SECTIONS)
    return args


def key(k):
    return k["value"] if isinstance(k, dict) else k


from ti_config import load_save  # THE shared loader: gzip magic + BOM, memoized


def dt(d):
    if not d or not isinstance(d, dict):
        return None
    y, mo, da = d.get("year"), d.get("month"), d.get("day")
    if y is None or mo is None or da is None:
        return None
    return f"{y:04d}-{mo:02d}-{da:02d}"


def kv(gs, typename):
    return {key(e["Key"]): e["Value"] for e in gs.get(f"PavonisInteractive.TerraInvicta.{typename}", [])}


def main():
    args = parse_args()
    FACTION_TEMPLATE = args.faction
    theater = args.theater
    theater_lc = theater.lower() if theater else None
    ship_name = args.ship_name
    sections = args.sections

    data = load_save(args.save)
    gs = data["gamestates"]

    # ---- core lookups -------------------------------------------------
    facs = kv(gs, "TIFactionState")
    fac_name = {fid: v.get("templateName") for fid, v in facs.items()}
    my_fid = [k for k, v in fac_name.items() if v == FACTION_TEMPLATE][0]
    alien_fid = [k for k, v in fac_name.items() if v == "AlienCouncil"][0]
    me = facs[my_fid]
    alien_fac = facs[alien_fid]

    habs = kv(gs, "TIHabState")
    hab_mods = [m["Value"] for m in gs["PavonisInteractive.TerraInvicta.TIHabModuleState"]]
    bodies = kv(gs, "TISpaceBodyState")
    orbits = kv(gs, "TIOrbitState")
    ships = kv(gs, "TISpaceShipState")
    fleets = kv(gs, "TISpaceFleetState")
    councilors = kv(gs, "TICouncilorState")
    regions = kv(gs, "TIRegionState")
    nations = kv(gs, "TINationState")
    orgs = kv(gs, "TIOrgState")
    missions = kv(gs, "TIMissionState")
    time_state = list(gs.get("PavonisInteractive.TerraInvicta.TITimeState", []))
    save_date = None
    if time_state:
        tv = time_state[0]["Value"]
        save_date = tv.get("currentDateTime")

    lagrange = kv(gs, "TILagrangePointState")

    sec2hab = {}
    for hid, h in habs.items():
        for s in (h.get("sectors") or []):
            sec2hab[key(s)] = hid

    def body_name(bid, type_hint=None):
        if bid is None:
            return None
        if type_hint and "LagrangePoint" in type_hint:
            return lagrange.get(bid, {}).get("displayName", f"Lagrange point {bid}")
        if bid in bodies:
            return bodies[bid].get("displayName", f"body {bid}")
        if bid in lagrange:
            return lagrange[bid].get("displayName", f"Lagrange point {bid}")
        return f"body {bid}"

    def hab_body_name(h):
        bc = h.get("barycenter")
        if bc:
            return body_name(key(bc), bc.get("$type") if isinstance(bc, dict) else None)
        return "(unknown)"

    def fleet_name(v, fid=my_fid):
        for e in (v.get("displayNameByFaction") or []):
            if key(e.get("Key")) == fid and e.get("Value"):
                return e["Value"]
        return v.get("displayName") or "(unnamed)"

    def fleet_location(v):
        """Returns (location string, in-transit bool, dest string or None, arrival date or None)."""
        traj = v.get("trajectory")
        if traj:
            dest_body = None
            dest_station = traj.get("destinationStation")
            dest_fleet = traj.get("destinationFleet")
            dest_orbit = traj.get("destination")
            if dest_station:
                h = habs.get(key(dest_station))
                dest_body = h.get("displayName") if h else None
            elif dest_orbit:
                o = orbits.get(key(dest_orbit))
                if o:
                    obc = o.get("barycenter")
                    dest_body = body_name(key(obc), obc.get("$type") if isinstance(obc, dict) else None) if obc else o.get("displayName")
            arrival = dt(traj.get("arrivalTime"))
            bcv = v.get("barycenter")
            cur_body = body_name(key(bcv), bcv.get("$type") if isinstance(bcv, dict) else None) if bcv else "(transit)"
            return cur_body, True, dest_body, arrival
        # not in transfer -> parked/docked
        dl = v.get("dockedLocation")
        if dl:
            h = habs.get(key(dl))
            loc = f"docked at {h.get('displayName')}" if h else "docked"
        else:
            loc = "in orbit"
        bcv = v.get("barycenter")
        cur_body = body_name(key(bcv), bcv.get("$type") if isinstance(bcv, dict) else None) if bcv else "(unknown)"
        return f"{cur_body} ({loc})", False, None, None

    design_cache = {}

    def get_designs(fac_state):
        return {d.get("dataName"): d for d in (fac_state.get("shipDesigns") or [])}

    my_designs = get_designs(me)
    alien_designs = get_designs(alien_fac)
    # also merge every faction's designs in case ships were captured/refit across factions
    all_designs = {}
    for fid, fv in facs.items():
        for d in (fv.get("shipDesigns") or []):
            all_designs.setdefault(d.get("dataName"), d)

    OUT = []
    def P(s=""):
        OUT.append(str(s))

    P(f"# Terra Invicta operational query — save ({FACTION_TEMPLATE})")
    P(f"Save-file in-game date field found: {save_date}")
    P()

    # ---- shared fleet rows (used by fleets + theater + aliens sections) ----
    my_fleet_rows = []
    for fid, v in fleets.items():
        if key(v.get("faction")) != my_fid:
            continue
        ship_ids = [key(s) for s in v.get("ships", [])]
        sl = [ships[sid] for sid in ship_ids if sid in ships]
        if not sl:
            continue
        name = fleet_name(v)
        loc, transit, dest, arrival = fleet_location(v)
        dvs = [s.get("currentDeltaV_kps") or 0 for s in sl]
        mass_t = sum((s.get("currentMass_kg") or 0) / 1000.0 for s in sl)
        row = {
            "id": fid, "name": name, "loc": loc, "n": len(sl), "mass_t": mass_t,
            "dv_min": min(dvs) if dvs else 0, "dv_avg": sum(dvs) / len(dvs) if dvs else 0,
            "transit": transit, "dest": dest, "arrival": arrival, "ships": sl,
        }
        my_fleet_rows.append(row)

    alien_rows = []
    for fid, v in fleets.items():
        if key(v.get("faction")) != alien_fid:
            continue
        ship_ids = [key(s) for s in v.get("ships", [])]
        sl = [ships[sid] for sid in ship_ids if sid in ships]
        if not sl:
            continue
        loc, transit, dest, arrival = fleet_location(v)
        bc = key(v.get("barycenter")) if v.get("barycenter") else None
        alien_rows.append((fid, v, sl, loc, transit, dest, arrival, bc))

    def hab_modules(hid):
        mods = []
        for m in hab_mods:
            if sec2hab.get(key(m.get("sector"))) == hid and m.get("exists") and not m.get("destroyed"):
                mods.append(m)
        return mods

    # =====================================================================
    # Q1 — Every friendly fleet
    # =====================================================================
    if "fleets" in sections:
        P(f"## Q1 — {FACTION_TEMPLATE} fleets")
        P("Fields used: TISpaceFleetState.{ships,faction,barycenter,dockedLocation,trajectory."
          "{destination,destinationStation,arrivalTime}}, TISpaceShipState.{currentMass_kg,"
          "currentDeltaV_kps,currentMaxDeltaV_kps}, displayNameByFaction for player-visible name.")
        P()
        P("| Fleet | Location | Ships | Mass (t) | ΔV min/avg (kps) | Transit? | Destination | Arrival |")
        P("|---|---|---:|---:|---|---|---|---|")

        for r in sorted(my_fleet_rows, key=lambda x: -x["n"]):
            P(f"| {r['name']} | {r['loc']} | {r['n']} | {r['mass_t']:,.1f} | "
              f"{r['dv_min']:.2f} / {r['dv_avg']:.2f} | {'YES' if r['transit'] else 'no'} | "
              f"{r['dest'] or '—'} | {r['arrival'] or '—'} |")

        P()
        P(f"Total {FACTION_TEMPLATE} fleets with ships: {len(my_fleet_rows)} "
          f"(total ships {sum(r['n'] for r in my_fleet_rows)})")

        # Theater-named fleet search
        if theater:
            P()
            P(f"### Fleets with '{theater}' or 'Defense' in name, or located at {theater}")
            theater_hits = [r for r in my_fleet_rows if theater_lc in r["name"].lower() or "defense" in r["name"].lower()
                            or theater_lc in r["loc"].lower()]
            if theater_hits:
                for r in theater_hits:
                    P(f"- **{r['name']}** — {r['loc']}, {r['n']} ships, mass {r['mass_t']:,.1f} t")
            else:
                P(f"- none found by name; see body-grouped listing below for whichever fleet(s) sit at {theater}.")
            P()
            P(f"### All {FACTION_TEMPLATE} fleets physically at {theater} (by barycenter)")
            for r in my_fleet_rows:
                if theater_lc in r["loc"].lower():
                    P(f"- **{r['name']}** — {r['loc']}, {r['n']} ships, ΔV avg {r['dv_avg']:.2f} kps")

        # Ship-name search
        P()
        if ship_name:
            P(f"### Ships with '{ship_name}' in name")
            name_hits = []
            for r in my_fleet_rows:
                for s in r["ships"]:
                    if ship_name.lower() in (s.get("displayName") or "").lower():
                        name_hits.append((r, s))
            if name_hits:
                for r, s in name_hits:
                    P(f"- Fleet **{r['name']}** (fleet id {r['id']}) — ship '{s.get('displayName')}' "
                      f"(design `{s.get('templateName')}`), launched {dt(s.get('launchDate'))}, "
                      f"location: {r['loc']}, ΔV {s.get('currentDeltaV_kps'):.2f} kps")
            else:
                P(f"- no ship with '{ship_name}' in displayName found among {FACTION_TEMPLATE} fleets.")
        else:
            P("### Ship-name search")
            P("- pass --ship-name to search your fleets for a ship by name substring.")

    # =====================================================================
    # Q2 — Councilors
    # =====================================================================
    if "councilors" in sections:
        P()
        P("## Q2 — Councilors")
        P("Fields used: TICouncilorState.{location (region/hab/ship ref), activeMission, "
          "priorMissionTemplateName, orgs}, TIMissionState.{templateName, target, councilor}.")
        P()

        def loc_desc(loc):
            if not loc:
                return "(none)"
            lt = loc.get("$type", "") if isinstance(loc, dict) else ""
            lid = key(loc)
            if "ShipState" in lt:
                s = ships.get(lid, {})
                fid = key(s.get("fleet"))
                fv = fleets.get(fid, {})
                fname = fleet_name(fv) if fv else "?"
                return f"ABOARD ship '{s.get('displayName')}' (design {s.get('templateName')}), fleet '{fname}'"
            if "HabState" in lt:
                h = habs.get(lid, {})
                return f"AT HAB {h.get('displayName')} ({hab_body_name(h)})"
            if "RegionState" in lt:
                r = regions.get(lid, {})
                return f"Earth region {r.get('displayName')}"
            return f"(ref {lid}, type {lt})"

        def mission_desc(v):
            am = v.get("activeMission")
            if not am:
                pm = v.get("priorMissionTemplateName")
                return f"no active mission (last ran: {pm or '—'})"
            m = missions.get(key(am), {})
            tn = m.get("templateName", "?")
            tgt = m.get("target")
            tgt_desc = ""
            if tgt:
                tt = tgt.get("$type", "")
                tid = key(tgt)
                if "NationState" in tt:
                    tgt_desc = f" -> nation {nations.get(tid, {}).get('displayName')}"
                elif "ShipState" in tt:
                    s = ships.get(tid, {})
                    tgt_desc = f" -> ship '{s.get('displayName')}'"
                elif "TIRegionState" in tt:
                    tgt_desc = f" -> region {regions.get(tid, {}).get('displayName')}"
                else:
                    tgt_desc = f" -> {tt.split('.')[-1]} {tid}"
            return f"active mission **{tn}**{tgt_desc}"

        my_councilors = []
        for cid, v in councilors.items():
            if key(v.get("faction")) != my_fid:
                continue
            my_councilors.append((cid, v))

        P(f"### All {len(my_councilors)} {FACTION_TEMPLATE} councilors — location & mission")
        P("| Name | id | Location | Mission |")
        P("|---|---:|---|---|")
        for cid, v in sorted(my_councilors, key=lambda x: x[1].get("familyName", "")):
            name = f"{v.get('personalName')} {v.get('familyName')}"
            P(f"| {name} | {cid} | {loc_desc(v.get('location'))} | {mission_desc(v)} |")
        P()
        P(f"Total {FACTION_TEMPLATE} councilors found (status=Active or any): {len(my_councilors)}")

    # =====================================================================
    # Q3 — Theater drill-down
    # =====================================================================
    if "theater" in sections:
        P()
        if not theater:
            P("## Q3 — Theater drill-down")
            P("(pass --theater to drill into a location)")
        else:
            P(f"## Q3 — {theater} theater")
            P("Fields used: TIHabState.{displayName,faction,tier,sectors,barycenter}, "
              "TIHabModuleState.{templateName,powered,constructionCompleted,destroyed}.")
            P()

            # bodies/lagrange points whose displayName matches the theater substring
            theater_body_ids = set()
            theater_body_names = set()
            for bid, b in list(bodies.items()) + list(lagrange.items()):
                nm = b.get("displayName") or ""
                if theater_lc in nm.lower():
                    theater_body_ids.add(bid)
                    theater_body_names.add(nm)

            theater_habs = {hid: h for hid, h in habs.items()
                            if hab_body_name(h) in theater_body_names
                            or theater_lc in (h.get("displayName") or "").lower()}
            P(f"Habs found at {theater}: {len(theater_habs)}")
            P()
            for hid, h in theater_habs.items():
                owner = fac_name.get(key(h.get("faction")), "?")
                mods_all = hab_modules(hid)
                empty_slots = [m for m in mods_all if not m.get("templateName")]
                mods = [m for m in mods_all if m.get("templateName")]
                yard_mods = [m for m in mods if any(x in (m.get("templateName") or "") for x in ("Shipyard", "Spaceworks"))]
                P(f"### {h.get('displayName')} (id {hid}) — owner {owner}, tier {h.get('tier')}, type {h.get('habType')}")
                P(f"- Shipyard/Spaceworks modules: {len(yard_mods)}")
                for m in yard_mods:
                    state = "powered" if m.get("powered") else "UNPOWERED"
                    built = "built" if m.get("constructionCompleted") else f"building (completes {dt(m.get('completionDate')) if isinstance(m.get('completionDate'), dict) else m.get('completionDate')})"
                    P(f"  - {m.get('templateName')} — {state}, {built}")
                P(f"- Full module list ({len(mods)} real modules, + {len(empty_slots)} empty slot(s) omitted):")
                for m in mods:
                    state = "powered" if m.get("powered") else "unpowered"
                    built = "" if m.get("constructionCompleted") else " [UNDER CONSTRUCTION]"
                    P(f"  - {m.get('templateName')} ({state}){built}")
                P()

            # Ships under construction at theater shipyards (see Q4 for full list; filter here)
            P("(Ships under construction at these shipyards, if any, are covered in Q4.)")

            # Alien fleets at/near the theater
            P()
            P(f"### Alien fleet(s) at {theater}")
            for fid, v, sl, loc, transit, dest, arrival, bc in alien_rows:
                if bc in theater_body_ids or theater_lc in loc.lower():
                    classes = defaultdict(int)
                    for s in sl:
                        d = all_designs.get(s.get("templateName"), {})
                        classes[d.get("_displayName", s.get("templateName"))] += 1
                    comp = ", ".join(f"{c}×{n}" for c, n in sorted(classes.items(), key=lambda x: -x[1]))
                    P(f"- **{v.get('displayName') or fleet_name(v, alien_fid)}** — {loc}, {len(sl)} ships"
                      f"{' (in transit to ' + str(dest) + ', arr ' + str(arrival) + ')' if transit else ''}: {comp}")

            # Alien-owned station module tally (SCV & battlestation/citadel counts)
            for hid, h in theater_habs.items():
                if key(h.get("faction")) != alien_fid:
                    continue
                mods = [m for m in hab_modules(hid) if m.get("templateName")]
                P()
                P(f"### {h.get('displayName')} — module tally")
                tally = defaultdict(lambda: [0, 0])  # templateName -> [count, powered_count]
                scv_total = 0.0
                for m in mods:
                    tn = m.get("templateName")
                    tally[tn][0] += 1
                    if m.get("powered"):
                        tally[tn][1] += 1
                        scv_total += m.get("_spaceCombatValue") or 0
                for tn, (n, npowered) in sorted(tally.items(), key=lambda x: -x[1][0]):
                    flag = " <-- battlestation/citadel-class" if "AlienBattlestation" in tn or "Citadel" in tn else ""
                    P(f"  - {tn}: {n} total, {npowered} powered{flag}")
                P(f"- Station SCV (powered modules only): {scv_total:,.0f}")

    # =====================================================================
    # Q4 — Ships under construction anywhere (nShipyardQueues)
    # =====================================================================
    if "construction" in sections:
        P()
        P("## Q4 — Ships under construction (faction.nShipyardQueues)")
        P("Field used: TIFactionState.nShipyardQueues — dict keyed by Shipyard/Spaceworks module id, "
          "value = list of build orders {shipDesignTemplateName, startDate, daysToCompletion, shipyard}.")
        P()
        queues = me.get("nShipyardQueues") or []
        build_orders = []
        for entry in queues:
            shipyard_mod_id = key(entry["Key"])
            for order in (entry.get("Value") or []):
                build_orders.append((shipyard_mod_id, order))

        # map shipyard module id -> hab
        mod_by_id = {}
        for m in hab_mods:
            mid = m.get("ID", {})
            mod_by_id[key(mid) if isinstance(mid, dict) else mid] = m

        P(f"Total build orders found: {len(build_orders)}")
        P()
        import datetime as _dt
        save_dt_obj = None
        if save_date:
            save_dt_obj = _dt.date(save_date["year"], save_date["month"], save_date["day"])
        P("| Design | Kind | Hab (body) | Started | Days remaining (as of save) | Est. completion date |")
        P("|---|---|---|---:|---|")
        for shipyard_mod_id, order in build_orders:
            design_name = order.get("shipDesignTemplateName")
            d = all_designs.get(design_name, {})
            disp = d.get("_displayName", design_name)
            m = mod_by_id.get(shipyard_mod_id, {})
            hid = sec2hab.get(key(m.get("sector"))) if m else None
            h = habs.get(hid, {}) if hid else {}
            hab_desc = f"{h.get('displayName', '?')} ({hab_body_name(h) if h else '?'})" if h else f"shipyard mod {shipyard_mod_id}"
            started = dt(order.get("startDate"))
            days_left = order.get("daysToCompletion")
            est = (save_dt_obj + _dt.timedelta(days=days_left)).isoformat() if save_dt_obj else "?"
            if order.get("isRefit"):
                orig_dn = order.get("refit_originalShipDesignTemplateName")
                orig_disp = all_designs.get(orig_dn, {}).get("_displayName", orig_dn)
                kind = f"REFIT of {orig_disp} (ship {key(order.get('originalSpaceShipState'))})"
            else:
                kind = "new build"
            P(f"| {disp} | {kind} | {hab_desc} | {started} | {days_left:.1f} | {est} |")

        # =====================================================================
        # Q5 — Shipyard geography
        # =====================================================================
        P()
        P(f"## Q5 — {FACTION_TEMPLATE} shipyard/spaceworks geography")
        P("Fields used: TIHabState.{displayName,faction,barycenter}, TIHabModuleState.{templateName,powered}.")
        P()
        by_body = defaultdict(list)
        for hid, h in habs.items():
            if key(h.get("faction")) != my_fid:
                continue
            mods = hab_modules(hid)
            yards = [m for m in mods if m.get("templateName") in ("Shipyard", "Spaceworks") or
                     "Shipyard" in (m.get("templateName") or "") or "Spaceworks" in (m.get("templateName") or "")]
            if not yards:
                continue
            powered_yards = [m for m in yards if m.get("powered")]
            by_body[hab_body_name(h)].append((h.get("displayName"), len(yards), len(powered_yards),
                                                defaultdict(int, {t: sum(1 for m in yards if m.get("templateName") == t) for t in set(m.get("templateName") for m in yards)})))

        total_powered = 0
        for body, entries in sorted(by_body.items()):
            P(f"### {body}")
            for name, n, npow, tiers in entries:
                tier_str = ", ".join(f"{t}×{c}" for t, c in tiers.items())
                P(f"- {name}: {n} yard module(s) ({npow} powered) — {tier_str}")
                total_powered += npow
            P()
        P(f"**Total powered Shipyard/Spaceworks modules, all bodies: {total_powered}**")

        # =====================================================================
        # Q6 — Resource incomes
        # =====================================================================
        P()
        P("## Q6 — Resource incomes & stockpiles")
        P("Field used: TIFactionState.resources (current stockpiles, exact). "
          "TIFactionState.baseIncomes_year (Faction-HQ-only base income, annual) and "
          "cachedYearlyRevenue exist but per docs/lessons/REFERENCE.md + LESSONS, "
          "cachedYearlyRevenue is KNOWN STALE/WRONG for the player faction "
          "(don't use as ground truth) — no clean save-level income/expense ledger "
          "breakdown by resource is available beyond these two fields; a true daily "
          "income needs the 6-source reconstruction extract_snapshot.py does per-resource "
          "(research only) — no equivalent exists in-save for metals/water/volatiles/money.")
        P()
        res = me.get("resources", {})
        P("### Current stockpiles (exact, from `resources`)")
        for k in ("Metals", "Water", "Volatiles", "Money", "NobleMetals", "Fissiles", "Exotics"):
            P(f"- {k}: {res.get(k)}")
        P()
        P("### baseIncomes_year (HQ-only, annual — NOT total faction income)")
        biy = me.get("baseIncomes_year", {})
        for k, v_ in biy.items():
            if v_:
                P(f"- {k}: {v_} /year (= {v_/365.25:.3f} /day)")
        P()
        P("### cachedYearlyRevenue (present in save, but flagged unreliable for the player faction)")
        cyr = me.get("cachedYearlyRevenue", {})
        for k, v_ in cyr.items():
            P(f"- {k}: {v_:,.1f} /year (= {v_/365.25:,.2f} /day) — ⚠ do not treat as ground truth")
        P()
        P("`resourceIncomeDeficiencies` (resources currently running a deficit per the game's own flag): "
          f"{me.get('resourceIncomeDeficiencies')}")

    # =====================================================================
    # Q7 — Alien fleets, sorted by SCV
    # =====================================================================
    if "aliens" in sections:
        P()
        P("## Q7 — Alien fleets by summed design combat value")
        P("Field used: ship design `_unnormalizedCombatValue` (per Victory Conditions and Endgame.md: "
          "save serializes this as `_unnormalizedCombatValue`, code calls it `_combatValue`), "
          "looked up via ship.templateName -> faction.shipDesigns[].dataName. "
          "Fleet in-transit determined by non-null `trajectory`.")
        P()
        scored = []
        for fid, v, sl, loc, transit, dest, arrival, bc in alien_rows:
            total_scv = 0.0
            classes = defaultdict(int)
            for s in sl:
                d = all_designs.get(s.get("templateName"), {})
                total_scv += d.get("_unnormalizedCombatValue") or 0
                classes[d.get("_displayName", s.get("templateName"))] += 1
            scored.append((v.get("displayName") or fleet_name(v, alien_fid), loc, len(sl), total_scv, transit, dest, arrival, classes))

        scored.sort(key=lambda x: -x[3])
        P(f"Total alien fleets with ships found: {len(scored)}")
        P()
        P("| # | Fleet | Location | Ships | Σ design SCV | In transit? | Destination (arrival) |")
        P("|---:|---|---|---:|---:|---|---|")
        for i, (name, loc, n, scv, transit, dest, arrival, classes) in enumerate(scored, 1):
            trans_str = f"YES -> {dest} ({arrival})" if transit else "parked"
            P(f"| {i} | {name} | {loc} | {n} | {scv:,.0f} | {'YES' if transit else 'no'} | {trans_str if transit else '—'} |")

    print("\n".join(OUT))


if __name__ == "__main__":
    main()
