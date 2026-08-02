#!/usr/bin/env python3
"""Colonization planner: where can you found, what's worth founding, and does it need a SHIP?

The central question this answers (E30, code-verified 2026-07-15): a colony/outpost-kit ship is
only worth spending on a body whose SUN-ORBITING system contains no owned hab with an active
construction module. `TIFactionState.CanFoundHabFromHabAtLocation` founds a hab with NO fleet
and NO kit whenever some owned hab shares `location.GetSunOrbitingRelatedObject` and has a
CanFoundTierN module — ConstructionModule→T1, Nanofactory→T2, NanofacturingComplex→T3 (the
system's cap = best module in it). For a Jovian moon the sun-parent is JUPITER, so one
nanofactory on any moon covers every other moon. `EligibleForFoundingBase(body)` =
`Prospected(body) && !alienTerritory && CanExplore(body) && vacantHabSites > 0` — no ship term.

Usage:
    python3 colony_planner.py <save>                       # ranked SHIP-ONLY targets
    python3 colony_planner.py <save> --free                # systems you can found in for free
    python3 colony_planner.py <save> --body "41 Daphne"    # one-body detail
    python3 colony_planner.py <save> --resource volatiles  # rank by a single resource
    python3 colony_planner.py <save> --include-free        # rank everything incl. free-found
    python3 colony_planner.py <save> --max-alien 2.0       # drop targets w/ alien fleet closer

Options: --faction <templateName> · --top N · --resource water|volatiles|metals|nobles|fissiles

🕶 SPOILER RULE (P13): yields are quoted ONLY for bodies with `faction.intel[body] >= 1.0`
(= Prospected; 0.1 = prospector/probe en route; absent = unknown). Unprospected bodies are
listed WITHOUT yields under --unprospected, because in-game you only have a range prior and
that prior can be badly wrong. Never lift `*_day` for an unprospected body into advice.

--unprospected ranks by PRIOR EXPECTATION instead (E33, spoiler-safe): each site template
names a mining profile (TIHabSiteTemplate → TIMiningProfileTemplate, the player's own
mirror), whose per-resource mean/width/jump ARE the ranges the in-game panel shows before a
survey. That answers "where do I send my prospector/survey ship — I want fissiles" without
reading hidden yields: `--unprospected --resource fissiles`. Only RockyPlanetoidMine
carries a guaranteed fissiles floor (mean 2, min 2, jump 0.8) — rocky-planetoid clusters
are the fissiles prospecting targets. Pair with `transfer_eta.py` for the transit times,
and skip bodies whose cover column shows a prospector already en route.

⚠ Occupancy/linking (P14): habs↔bodies join via `hab.habSite -> TIHabSiteState.parentBody`,
NEVER by position proximity (that hid a station on 87 Sylvia and collapses whole moon
systems — all Saturn moons are <0.07 AU apart). A site is vacant iff `site.hab is None`.

⚠ "Clear of aliens" is a SNAPSHOT — fleets move (Titan). Re-check before a hull commits.
"""
import json, gzip, argparse, math
from collections import defaultdict
from free_founding import FreeFounding  # E30 free-founding (shared)

AU = 1.496e11
RESOURCES = ['water', 'volatiles', 'metals', 'nobles', 'fissiles']
# scarcity weights for the default composite score (fissiles/nobles are the binding constraints)
WEIGHTS = {'fissiles': 400.0, 'nobles': 8.0, 'volatiles': 1.5, 'metals': 1.2, 'water': 0.5}


def key(k):
    return k['value'] if isinstance(k, dict) else k


def load_save(path):
    raw = open(path, 'rb').read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return json.loads(raw)


class World:
    """Parsed view of the save: bodies, sites, habs, intel, free-founding tiers."""

    def __init__(self, path, faction=None):
        from ti_config import require_faction
        faction = require_faction(faction)
        gs = load_save(path)['gamestates']
        self.gs = gs
        facs = {key(f['Key']): f['Value'] for f in gs['PavonisInteractive.TerraInvicta.TIFactionState']}
        self.fname = {k: v.get('templateName') for k, v in facs.items()}
        self.my_fid = [k for k, v in self.fname.items() if v == faction][0]
        self.me = facs[self.my_fid]
        self.alien_fids = {k for k, v in self.fname.items() if v == 'AlienCouncil'}

        self.bodies, self.pos, self.bary = {}, {}, {}
        for b in gs['PavonisInteractive.TerraInvicta.TISpaceBodyState']:
            v = b['Value']
            bid = key(b['Key'])
            p = v.get('globalPosition') or {}
            self.bodies[bid] = v
            self.pos[bid] = (p.get('x', 0), p.get('y', 0), p.get('z', 0))
            self.bary[bid] = key(v['barycenter']) if v.get('barycenter') is not None else None

        # P13: prospect knowledge == faction.intel[body] (>=1.0 prospected, 0.1 probe en route)
        self.intel = {key(e['Key']): e.get('Value') for e in (self.me.get('intel') or [])}
        self.sites = {key(s['Key']): s['Value'] for s in gs.get('PavonisInteractive.TerraInvicta.TIHabSiteState', [])}
        self.habs = {key(h['Key']): h['Value'] for h in gs['PavonisInteractive.TerraInvicta.TIHabState']}
        self._index_sites()
        # E30 free-founding, shared with resource_site_planner (free_founding.FreeFounding).
        self._ff = FreeFounding(self.gs, self.my_fid, bodies=self.bodies,
                                habs=self.habs, sites=self.sites)
        self.free_tier = self._ff.free_tier
        self._index_alien_fleets()
        self._load_mining_profiles()

    # --- indexing -------------------------------------------------------
    def _index_sites(self):
        self.sites_by_body = defaultdict(list)
        self.vacant_by_body = defaultdict(list)
        for sid, st in self.sites.items():
            pb = st.get('parentBody')
            if pb is None:
                continue
            bid = key(pb)
            self.sites_by_body[bid].append(st)
            if st.get('hab') is None:          # P14: vacant iff site.hab is None
                self.vacant_by_body[bid].append(st)

    def sun_parent(self, bid):
        """Walk barycenters to the body that orbits Sol (Jovian moon -> Jupiter)."""
        return self._ff.sun_parent(bid)

    def hab_body(self, hid):
        """P14: hab -> body via habSite.parentBody. NEVER by position."""
        return self._ff.hab_body(hid)

    def _index_alien_fleets(self):
        self.alien_fleets = []
        for f in self.gs['PavonisInteractive.TerraInvicta.TISpaceFleetState']:
            v = f['Value']
            if key(v.get('faction')) in self.alien_fids and v.get('ships'):
                p = v.get('globalPosition') or {}
                self.alien_fleets.append(((p.get('x', 0), p.get('y', 0), p.get('z', 0)), len(v['ships'])))

    def _load_mining_profiles(self):
        """Pre-survey PRIORS (spoiler-safe): each site template names a mining profile whose
        `<res>_mean/_width/_jump` fields are exactly what the in-game body panel shows as
        yield ranges BEFORE a survey. Ranking unprospected bodies by these priors reveals
        nothing hidden — but the priors can be wrong BOTH ways (that is why surveying
        matters), so they are expectations, never income claims. Needs the player's own
        template mirror (`sync_game_data.py`); degrades gracefully without it."""
        self.site_profile, self.profiles = {}, {}
        try:
            from ti_config import find_templates_dir
            td = find_templates_dir()
            if not td:
                return
            with open(td / 'TIHabSiteTemplate.json', encoding='utf8') as f:
                self.site_profile = {t['dataName']: t.get('miningProfileName') for t in json.load(f)}
            with open(td / 'TIMiningProfileTemplate.json', encoding='utf8') as f:
                self.profiles = {t['dataName']: t for t in json.load(f)}
        except Exception:
            self.site_profile, self.profiles = {}, {}

    def site_prior(self, st):
        """Mining-profile template for one site, or None (no templates / unknown site)."""
        return self.profiles.get(self.site_profile.get(st.get('templateName')))

    def body_prior(self, bid, resource=None):
        """(prior score over vacant sites, {profileName: n}, {res: Σmean}, {res: max jump}).
        Score = Σ site means × scarcity WEIGHTS (or the single --resource mean)."""
        counts, means, jumps = defaultdict(int), defaultdict(float), defaultdict(float)
        for st in self.vacant_by_body.get(bid, []):
            p = self.site_prior(st)
            if not p:
                continue
            counts[p['dataName']] += 1
            for r in RESOURCES:
                means[r] += p.get(f'{r}_mean', 0) or 0
                jumps[r] = max(jumps[r], p.get(f'{r}_jump', 0) or 0)
        if resource:
            score = means.get(resource, 0.0)
        else:
            score = sum(means[r] * WEIGHTS[r] for r in RESOURCES)
        return score, dict(counts), dict(means), dict(jumps)

    # --- queries --------------------------------------------------------
    def prospected(self, bid):
        v = self.intel.get(bid)
        return isinstance(v, (int, float)) and v >= 1.0

    def probe_en_route(self, bid):
        return self.intel.get(bid) == 0.1

    def body_id(self, name):
        for bid, v in self.bodies.items():
            if v.get('displayName') == name:
                return bid
        return None

    def nearest_alien(self, bid):
        if not self.alien_fleets:
            return (999.0, 0)
        return min(((math.dist(self.pos[bid], fp) / AU, n) for fp, n in self.alien_fleets))

    def free_found_tier(self, bid):
        return self._ff.free_found_tier(bid)

    def owners(self, bid):
        out = []
        for hid, h in self.habs.items():
            if self.hab_body(hid) == bid:
                out.append((h.get('displayName'), self.fname.get(key(h.get('faction')))))
        return out

    def monthly(self, site, res):
        return (site.get(f'{res}_day') or 0) * 30.44

    def body_yield(self, bid, res, vacant_only=True):
        src = self.vacant_by_body[bid] if vacant_only else self.sites_by_body[bid]
        return sum(self.monthly(s, res) for s in src)

    def score(self, bid, resource=None):
        if resource:
            return self.body_yield(bid, resource)
        return sum(self.body_yield(bid, r) * WEIGHTS[r] for r in RESOURCES)


def au(w, bid, ref):
    return math.dist(w.pos[bid], w.pos[ref]) / AU


def cmd_free(w):
    print("=== FREE FOUNDING (own hab + ACTIVE construction module in the same sun-system) ===")
    print("    no ship, no outpost kit needed — E30\n")
    rows = sorted(w.free_tier.items(), key=lambda x: (-x[1], w.bodies[x[0]].get('displayName')))
    print(f"{'System (sun-parent)':22s} {'cap':>4s}  vacant prospected sites in system")
    for sp, t in rows:
        # every body sharing this sun-parent
        n_sites, bodies_ = 0, []
        for bid in w.bodies:
            if w.sun_parent(bid) != sp or not w.prospected(bid):
                continue
            v = len(w.vacant_by_body.get(bid, []))
            if v:
                n_sites += v
                bodies_.append(f"{w.bodies[bid].get('displayName')}×{v}")
        extra = f"  {n_sites:>3} vacant: " + ', '.join(bodies_[:6]) if n_sites else "  (none vacant)"
        print(f"{w.bodies[sp].get('displayName'):22s}  T{t}{extra}")
    print("\nTip: a system's cap is the BEST module in it — build a NanofacturingComplex on any")
    print("hab to lift the whole system to T3 (cheaper than shipping kits).")


def cmd_body(w, name, earth):
    bid = w.body_id(name)
    if bid is None:
        raise SystemExit(f'body "{name}" not found')
    chain, cur = [], bid
    for _ in range(6):
        chain.append(w.bodies[cur].get('displayName'))
        nxt = w.bary.get(cur)
        if nxt is None or nxt not in w.bodies:
            break
        cur = nxt
    v = w.bodies[bid]
    naf = w.nearest_alien(bid)
    ft = w.free_found_tier(bid)
    print(f"=== {name} ===")
    print(f"  barycenter chain : {' → '.join(chain)}")
    print(f"  sun-parent       : {w.bodies[w.sun_parent(bid)].get('displayName')}")
    print(f"  position         : {au(w, bid, w.body_id('Sol') or bid):.2f} AU sun · "
          f"{au(w, bid, earth):.2f} AU Earth")
    print(f"  maxHabTier       : {v.get('maxHabTier')}   alienTerritory: {v.get('alienTerritory')}")
    st = ('PROSPECTED (yields readable)' if w.prospected(bid)
          else ('probe en route (intel 0.1) — yields HIDDEN' if w.probe_en_route(bid)
                else 'UNPROSPECTED — yields HIDDEN'))
    print(f"  intel            : {w.intel.get(bid)}  → {st}")
    print(f"  nearest alien flt: {naf[0]:.1f} AU ({naf[1]} ships)")
    print(f"  FOUNDING         : " + (f"FREE from own hab, up to T{min(ft, v.get('maxHabTier') or 3)}"
                                      f" (system cap T{ft}, body max T{v.get('maxHabTier')})" if ft
                                      else "needs a SHIP with an outpost kit"))
    occ = w.owners(bid)
    if occ:
        print(f"  existing habs    : " + ', '.join(f"{n} ({o})" for n, o in occ))
    sites = w.sites_by_body.get(bid, [])
    print(f"  sites            : {len(sites)} total, {len(w.vacant_by_body.get(bid, []))} vacant")
    for s in sites:
        vac = 'vacant' if s.get('hab') is None else 'TAKEN'
        line = f"    {s.get('displayName') or '?':26s} {vac:6s}"
        if w.prospected(bid):
            line += ''.join(f" {r[0]}{w.monthly(s, r):7.1f}" for r in RESOURCES)
        else:
            line += "   (yields redacted — unprospected)"
        print(line)


def cmd_rank(w, args, earth):
    include_free = args.include_free
    rows = []
    for bid in w.bodies:
        if w.pos[bid] == (0, 0, 0) or not w.vacant_by_body.get(bid):
            continue
        if args.unprospected:
            if w.prospected(bid):
                continue
        else:
            if not w.prospected(bid):
                continue
        if w.bodies[bid].get('alienTerritory'):
            continue
        if any(o == 'AlienCouncil' for _, o in w.owners(bid)):
            continue
        ft = w.free_found_tier(bid)
        if ft and not include_free:
            continue                       # E30: free — no ship needed, not a ship target
        naf = w.nearest_alien(bid)
        if naf[0] < args.max_alien:
            continue
        prior = w.body_prior(bid, args.resource) if args.unprospected else None
        sc = prior[0] if args.unprospected else w.score(bid, args.resource)
        rows.append((sc, bid, ft, naf, prior))
    rows.sort(key=lambda r: -r[0])
    what = ('UNPROSPECTED (survey-capable ships only; PRIOR expectations, not yields)'
            if args.unprospected
            else ('ALL targets (incl. free-founding)' if include_free else 'SHIP-ONLY targets'))
    rank_by = f"by {args.resource}/mo" if args.resource else "by scarcity-weighted score"
    if args.unprospected:
        rank_by = (f"by PRIOR {args.resource} mean" if args.resource
                   else "by scarcity-weighted PRIOR score")
    print(f"=== {what} — {rank_by}, alien fleet ≥ {args.max_alien} AU ===")
    hdr = f"{'Body':22s} {'AUsun':>5s} {'AUear':>5s} {'vac':>3s} {'maxT':>4s}"
    if args.unprospected:
        hdr += ''.join(f"{'~' + r[:4]:>6s}" for r in RESOURCES) + f" {'jump':>5s} {'cover':>6s}"
    else:
        hdr += ''.join(f"{r[:5]:>7s}" for r in RESOURCES)
    hdr += f" {'alien':>6s} found"
    if args.unprospected:
        hdr += '  profiles'
    print(hdr)
    sol = w.body_id('Sol')
    for sc, bid, ft, naf, prior in rows[:args.top]:
        v = w.bodies[bid]
        line = (f"{v.get('displayName'):22s} {au(w, bid, sol):>5.1f} {au(w, bid, earth):>5.1f} "
                f"{len(w.vacant_by_body[bid]):>3} {str(v.get('maxHabTier')):>4}")
        if args.unprospected:
            _, counts, means, jumps = prior
            jr = args.resource or 'fissiles'
            line += ''.join(f"{means.get(r, 0):6.0f}" for r in RESOURCES)
            line += f" {jumps.get(jr, 0):5.1f}"
            cover = '0.1→' if w.probe_en_route(bid) else '—'
            line += f" {cover:>6s}"
        else:
            line += ''.join(f"{w.body_yield(bid, r):7.1f}" for r in RESOURCES)
        line += f" {naf[0]:>5.1f}/{naf[1]:<2} " + (f"FREE-T{ft}" if ft else "ship")
        if args.unprospected:
            line += '  ' + ', '.join(f"{k.replace('Mine', '')}×{n}" for k, n in
                                     sorted(prior[1].items(), key=lambda x: -x[1]))
        print(line)
    if not rows:
        print("  (no targets match)")
    if args.unprospected:
        if not w.profiles:
            print("\n⚠ no template mirror found — PRIOR columns empty. Run sync_game_data.py first.")
        else:
            print("\n~cols = Σ profile MEANS over vacant sites — the same prior the in-game panel")
            print("shows pre-survey (E33). Priors can be wrong BOTH ways; never quote them as yields.")
            print(f"jump = max {args.resource or 'fissiles'} jackpot chance among the body's profiles.")
            print("cover: 0.1→ = a prospector/probe is already en route (don't double-book).")
    print("\n⚠ alien-fleet distances are a SNAPSHOT — fleets move; re-check before a hull commits.")
    if not args.unprospected and not include_free:
        print("⚠ free-founding bodies are EXCLUDED (E30) — run --free to see what needs no ship.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('save')
    ap.add_argument('--faction', default=None)
    ap.add_argument('--free', action='store_true', help='list systems I can found in for free')
    ap.add_argument('--body', help='detail on one body')
    ap.add_argument('--resource', choices=RESOURCES, help='rank by one resource instead of the composite')
    ap.add_argument('--include-free', action='store_true', help='include free-founding bodies in the ranking')
    ap.add_argument('--unprospected', action='store_true', help='list unprospected targets (yields redacted)')
    ap.add_argument('--max-alien', type=float, default=1.0, help='drop targets with an alien fleet closer than this (AU)')
    ap.add_argument('--top', type=int, default=20)
    args = ap.parse_args()
    from ti_config import require_faction
    args.faction = require_faction(args.faction)

    w = World(args.save, args.faction)
    earth = w.body_id('Earth')
    if args.free:
        cmd_free(w)
    elif args.body:
        cmd_body(w, args.body, earth)
    else:
        cmd_rank(w, args, earth)


if __name__ == '__main__':
    main()
