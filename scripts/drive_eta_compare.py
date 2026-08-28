#!/usr/bin/env python3
"""
drive_eta_compare.py — rank drives by ACTUAL transit TIME on representative routes, not raw EV.

EV is only a PROXY for reach. Wall-clock transit time is set by ΔV (= EV·ln massRatio) AND
acceleration (= cruise thrust / mass), so the EV ranking routinely REVERSES once you compute time:
short/inner legs are ACCEL-limited (thrust wins), long/deep legs are ΔV-limited (EV wins). This is
LESSONS-ships S23; the physics is transfer_eta.eta_seconds (the game's own quick estimator).

Uses a first-principles reference ship held CONSTANT across drives (warship_optimizer is not
calibrated for the fusion/transit drive families). For each drive variant:
    ΔV_kps       = EV_kps × ln(mass_ratio)
    cruise accel = drive thrust_N (cruise) / wet_mass_kg      [combat thrust = thrust_N × thrustCap]
    transit time = transfer_eta.eta_seconds(distance, cruise_accel, ΔV_budget)   per route

CAVEATS: representative straight-line AU distances — relative ranking is robust, absolute weeks are
±; the in-game transfer planner is truth. Holding the ship constant ignores that heavier drives
leave less tank room (slightly lowers their ΔV). For a specific ship/fleet, use transfer_eta.py on
the save. Income/terminology conventions per LESSONS-process P17 (this tool reports no incomes).

Usage:
    python3 drive_eta_compare.py                                   # all drives, x6, default routes
    python3 drive_eta_compare.py --drives TritonTorus,TritonFusor,Helicon,DustyPlasma,NeutronFluxLantern
    python3 drive_eta_compare.py --variant 3 --wet-t 3000 --mass-ratio 3
    python3 drive_eta_compare.py --routes "Earth-Ceres:1.8,Callisto-Pluto:33"
"""
import argparse, glob, json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from transfer_eta import eta_seconds
try:
    from ti_config import find_templates_dir
except Exception:
    def find_templates_dir():
        return None

AU = 1.496e11
DEFAULT_ROUTES = [("Earth→Ceres", 1.8), ("Mars→Ceres", 1.0), ("Callisto→Pluto", 33.0)]
FRIENDLY = {"NeutronFluxLantern": "Poseidon Lantern", "NeutronFluxTorch": "Poseidon Torch"}
_ABBR = {"water": "wat", "volatiles": "vol", "fissiles": "FIS", "metals": "met",
         "nobleMetals": "nob", "antimatter": "am"}


def load_drives():
    cands = []
    tdir = find_templates_dir()
    if tdir:
        cands += glob.glob(os.path.join(str(tdir), "*Drive*emplate*.json"))
    cands += glob.glob(os.path.join(os.path.dirname(__file__), "templates", "*Drive*emplate*.json"))
    for p in cands:
        try:
            d = json.load(open(p))
            if isinstance(d, list) and d:
                return d
        except Exception:
            continue
    sys.exit("Could not load a drive template (TIDriveTemplate.json). Run sync_game_data.py first.")


def base_name(d):
    dn = d.get("dataName", "")
    for k, v in FRIENDLY.items():
        if dn.startswith(k):
            return v
    return (d.get("friendlyName") or dn).rsplit(" x", 1)[0]


def main():
    ap = argparse.ArgumentParser(description="Rank drives by transit time, not EV (LESSONS-ships S23).")
    ap.add_argument("--drives", help="comma-separated dataName prefixes (default: all drives)")
    ap.add_argument("--variant", type=int, default=6, help="thruster count x1..x6 (default 6)")
    ap.add_argument("--wet-t", type=float, default=2000.0, help="reference wet mass, tons")
    ap.add_argument("--mass-ratio", type=float, default=2.5, help="wet/dry (sets ΔV = EV·ln)")
    ap.add_argument("--dv-frac", type=float, default=0.975, help="fraction of ΔV the planner may spend")
    ap.add_argument("--routes", help='"name:AU,name:AU" (default: inner + deep)')
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    a = ap.parse_args()

    routes = DEFAULT_ROUTES
    if a.routes:
        routes = [(p.rsplit(":", 1)[0], float(p.rsplit(":", 1)[1])) for p in a.routes.split(",")]

    prefixes = [x.strip() for x in a.drives.split(",")] if a.drives else None
    lnR = math.log(a.mass_ratio)
    suffix = "x%d" % a.variant

    rows = []
    for d in load_drives():
        dn = d.get("dataName", "")
        if not dn.endswith(suffix):
            continue
        if prefixes and not any(dn.startswith(p) for p in prefixes):
            continue
        ev = d.get("EV_kps") or 0.0
        thr = d.get("thrust_N") or 0.0          # cruise thrust (total, this variant)
        cap = d.get("thrustCap") or 0
        if not ev or not thr:
            continue
        dvkps = ev * lnR
        cruise_a = thr / (a.wet_t * 1000.0)      # m/s²
        etas = [eta_seconds(au * AU, cruise_a, dvkps * 1000.0 * a.dv_frac) for _, au in routes]
        mix = d.get("perTankPropellantMaterials") or {}
        fuel = "+".join("%g%s" % (v * 10, _ABBR.get(k, k[:3]))
                        for k, v in sorted(mix.items(), key=lambda kv: -kv[1])) or "?"
        rows.append({"name": base_name(d), "ev": ev, "dv": dvkps, "a": cruise_a,
                     "combat_mn": thr * cap / 1e6, "fuel": fuel,
                     "wk": [(s / 604800.0, mode) for s, _, mode in etas]})
    if not rows:
        sys.exit("No drives matched (variant %s, filter %s)." % (suffix, a.drives))
    rows.sort(key=lambda r: r["wk"][0][0])       # fastest on the first route

    if a.json:
        payload = {
            "reference_ship": {"variant": a.variant, "wet_t": a.wet_t,
                               "mass_ratio": a.mass_ratio, "dv_frac": a.dv_frac},
            "routes": [{"name": nm, "au": au} for nm, au in routes],
            "drives": [{"name": r["name"], "ev_kps": r["ev"], "dv_kps": r["dv"],
                        "cruise_accel_ms2": r["a"], "combat_mn": r["combat_mn"],
                        "fuel_per_tank": r["fuel"],
                        "route_etas": [{"route": nm, "weeks": wk, "mode": mode}
                                       for (nm, _), (wk, mode) in zip(routes, r["wk"])]}
                       for r in rows],
        }
        print(json.dumps(payload, indent=2, default=str))
        return

    print("# Drive transit-time comparison (%s) — LESSONS-ships S23" % suffix)
    print("Reference ship: wet %.0f t, mass-ratio %s (ΔV = EV × %.3f); ΔV budget %s. "
          "Ranked by fastest %s." % (a.wet_t, a.mass_ratio, lnR, a.dv_frac, routes[0][0]))
    print("EV is a PROXY — thrust wins short/accel-limited legs, EV wins long/ΔV-limited legs.\n")
    hdr = ("%-22s %5s %7s %9s %7s  %-16s " % ("drive", "EV", "ΔV", "cruise_a", "combat", "fuel/tank")
           + " ".join("%16s" % nm for nm, _ in routes))
    print(hdr); print("-" * len(hdr))
    for r in rows:
        cells = " ".join(("%.1fwk %s" % (wk, mode)).rjust(16) for wk, mode in r["wk"])
        print("%-22s %5.0f %7.0f %9.3f %6.0fMN  %-16s %s"
              % (r["name"], r["ev"], r["dv"], r["a"], r["combat_mn"], r["fuel"], cells))
    print("\nCAVEAT: representative straight-line AU; relative ranking robust, absolute weeks ±. "
          "In-game planner is truth. For a specific fleet use transfer_eta.py on the save.")


if __name__ == "__main__":
    main()
