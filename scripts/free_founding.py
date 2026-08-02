#!/usr/bin/env python3
"""E30 free-founding computation — shared by colony_planner.py and resource_site_planner.py.

Founding a hab needs NO ship and NO outpost kit where some owned hab shares the target's
SUN-ORBITING parent and has an ACTIVE (powered) CanFoundTierN module:
ConstructionModule→T1, Nanofactory→T2, NanofacturingComplex→T3 (a system's cap = the best
such module in it). For a Jovian moon the sun-parent is JUPITER, so one nanofactory on any
moon covers every other moon. Code-verified against
`TIFactionState.CanFoundHabFromHabAtLocation` / `MaxTierCanFoundAtLocation`; see
docs/lessons/LESSONS-economy.md E30.

This is the single source of truth for that computation so the two planners can never drift
(the bug that motivated extraction: resource_site_planner assigned kit fleets + ETAs to
Jupiter's moons that needed no ship at all).
"""

# HabModuleSpecialRule CanFoundTierN -> tier, by module templateName (E25: powered, not just built)
FOUND_MODULES = {'ConstructionModule': 1, 'Nanofactory': 2, 'NanofacturingComplex': 3}


def key(k):
    return k['value'] if isinstance(k, dict) else k


class FreeFounding:
    """Given the parsed save's gamestates + the player's faction id, compute the free-founding
    tier of every sun-orbiting system and answer `free_found_tier(body_id)`.

    Pass already-parsed `bodies` (bid->value), `habs` (hid->value) and `sites` (sid->value)
    to avoid re-walking the big state arrays; any omitted arg is built from `gs`.
    """

    def __init__(self, gs, my_fid, bodies=None, habs=None, sites=None):
        self.gs = gs
        self.my_fid = my_fid
        self.bodies = bodies if bodies is not None else {
            key(b['Key']): b['Value']
            for b in gs['PavonisInteractive.TerraInvicta.TISpaceBodyState']}
        self.bary = {bid: (key(v['barycenter']) if v.get('barycenter') is not None else None)
                     for bid, v in self.bodies.items()}
        self.habs = habs if habs is not None else {
            key(h['Key']): h['Value']
            for h in gs['PavonisInteractive.TerraInvicta.TIHabState']}
        self.sites = sites if sites is not None else {
            key(s['Key']): s['Value']
            for s in gs.get('PavonisInteractive.TerraInvicta.TIHabSiteState', [])}
        self.free_tier = {}          # sun-parent body id -> best foundable tier
        self._index()

    def sun_parent(self, bid):
        """Walk barycenters to the body that orbits Sol (Jovian moon -> Jupiter)."""
        seen = set()
        while bid not in seen:
            seen.add(bid)
            par = self.bary.get(bid)
            if par is None or par not in self.bodies:
                return bid
            if self.bodies[par].get('displayName') == 'Sol':
                return bid
            bid = par
        return bid

    def hab_body(self, hid):
        """P14: hab -> body via habSite.parentBody. NEVER by position."""
        h = self.habs[hid]
        sid = key(h.get('habSite')) if h.get('habSite') is not None else None
        if sid is None or sid not in self.sites:
            return None
        pb = self.sites[sid].get('parentBody')
        return key(pb) if pb is not None else None

    def _index(self):
        """E30: sun-parent system -> max tier foundable with no ship."""
        sec2hab = {}
        for hid, h in self.habs.items():
            for s in (h.get('sectors') or []):
                sec2hab[key(s)] = hid
        hab_tier = {}
        for m in self.gs['PavonisInteractive.TerraInvicta.TIHabModuleState']:
            v = m['Value']
            if not (v.get('exists') and v.get('constructionCompleted')
                    and not v.get('destroyed') and v.get('powered')):
                continue                        # E25: powered, not merely built
            hid = sec2hab.get(key(v.get('sector')))
            if hid is None or key(self.habs[hid].get('faction')) != self.my_fid:
                continue
            t = FOUND_MODULES.get(v.get('templateName'))
            if t:
                hab_tier[hid] = max(hab_tier.get(hid, 0), t)
        for hid, t in hab_tier.items():
            bid = self.hab_body(hid)
            if bid is None:
                continue
            sp = self.sun_parent(bid)
            self.free_tier[sp] = max(self.free_tier.get(sp, 0), t)

    def free_found_tier(self, bid):
        """Best tier the player can found on `bid` with no ship (0 = needs a ship+kit)."""
        if bid is None:
            return 0
        return self.free_tier.get(self.sun_parent(bid), 0)
