#!/usr/bin/env python3
"""research_income.py — FULL faction research-income reconstruction from a save file.

Reproduces the in-game 🧪 top-bar research tooltip (and the per-nation research the
player receives) from the save alone. Validated against saves 159 (2033-02-04) and
248 (2033-04-03): every term within 1%, totals within 0.1%.

    save 159 tooltip: 500.6/day = 1 HQ + 25.4 counc + 225 nations + 147.3 habs
                      + 1.7 unusedMC + 100.1 distribution(25%)   → computed 500.2
    save 248 tooltip: 562.1/day = 1 + 25.4 + 230.9 + 175 + 129.7(30%) → computed 561.6

THE CRACKED FORMULAS (all code-verified against the installed 1.0.39 build,
see LESSONS-research; R19's "not reconstructable" is now obsolete):

  research_month(nation)  [TINationState.get_research_month — matches wiki §Research]
      = ( pop_Mn × gdpTerm(perCapGDP) × edu×min(edu,12) × max(dem,1)^(1/6) × 0.0075
          + min(pop/5000, numCP + edu + dem/2) )
        × (1.25 − |cohesion−5|/10) × (1 − unrest²/100) × (1 + adviserScienceBonus)
      gdpTerm(pc) = (pc/15000)^0.6 if pc≤30000 else 1.5157166+0.90943×(ln(pc/15000)−ln2)
      adviserScienceBonus = Σ_i sci_i/100/(i+1), advisors sorted desc by effective
      Science = attributes.Science + Σ org.science + Σ unconditional trait Science mods.
      ► The Nations screen "research" flask column IS this value (USA 2.0K, CHN 2.4K…).
        The 730.9/809.8/872.5 numbers previously logged as "research" were the SPACE
        FUNDING column (historySpaceFunding[0]) — a mis-read, root of the 2.76× puzzle.

  player research from a nation  [GetMonthlyResearchFromControlPoint × myCPs]
      = research_month × ksBonus × cpResearchMult / numControlPoints × myCPs(not disabled)
      ksBonus        = 1.05 iff the faction owns that nation's KnowledgeSector CP
      cpResearchMult = Π multiplicative ControlPointResearch effects of the faction
                       (TIEffectsState.factionEffectsNames[fid]['ControlPointResearch'];
                        Effect_CPResearch10=×1.1 …; this run: two ×1.1 → ×1.21)
      ► "N from nations" tooltip line = Σ over CPs, ×12/365.2421875 for per-day.

  councilors [GetMonthlyIncomeFromCouncilors]: per councilor (not detained):
      (Σ org.incomeResearch_month + Σ trait.incomeResearch) × (1 + effScience/100)

  habs: Σ powered+completed player module template incomeResearch_month.

  unused MC: max(0, maxMC − usedMC) × 0.075/day  (ExcessMCToResearchConversion_Day;
      maxMC = 22 HQ+bonus… computed here as hq+councilor+hab+nation MC sums).

  distribution bonus [get_BonusPctFromDistribution]:
      0.05 × (# of researchWeights slots > 0; slots 4/5 only if org/hab slot unlocked)
      TOTAL tooltip = (HQ + councilors + nations + habs + unusedMC) × (1 + bonus)

Usage:
  python3 research_income.py <save.json>                    # player faction breakdown
  python3 research_income.py <save.json> --all-factions     # + rival research estimates
  python3 research_income.py <save.json> --rivals 1.9K,...  # pass Intel numbers for Table H
  python3 research_income.py <save.json> --nations 2026_USA,2026_CHN,2026_RUS
      # Table H per-nation columns (default: config anchor_nations, else
      # auto-detect = top 3 by GDP among nations where your faction holds a CP)
"""
import sys, os, math, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_snapshot as er

DAYS_YR = 365.2421875            # the DLL's year constant for daily income
MO = 30.436874389648438          # the DLL's month constant
EXCESS_MC_RESEARCH_DAY = 0.075   # TIGlobalConfig.ExcessMCToResearchConversion_Day
DIST_PER_SLOT = 0.05             # TIGlobalConfig.researchBonusPerSlotInUse
KS_BONUS = 1.05                  # TIGlobalConfig.knowledgeSectorResearchBonus

_NS = 'PavonisInteractive.TerraInvicta.'


def _load_templates_extra():
    """Trait Science mods / research incomes + ControlPointResearch effect values."""
    tdir = er.find_templates_dir()
    out = {'trait_sci': {}, 'trait_res': {}, 'cp_res_effects': {}}
    if not tdir:
        return out
    for t in er._safe_load_json(os.path.join(tdir, 'TITraitTemplate.json')) or []:
        dn = t.get('dataName')
        if not dn:
            continue
        sci = 0.0
        for m in (t.get('statMods') or []):
            if m.get('stat') == 'Science' and m.get('operation', 'Additive') == 'Additive' \
                    and not m.get('condition'):
                try:
                    sci += float(m.get('strValue', 0) or 0)
                except ValueError:
                    pass
        if sci:
            out['trait_sci'][dn] = sci
        if t.get('incomeResearch'):
            out['trait_res'][dn] = t['incomeResearch']
    for e in er._safe_load_json(os.path.join(tdir, 'TIEffectTemplate.json')) or []:
        if 'ControlPointResearch' in (e.get('contexts') or []):
            out['cp_res_effects'][e.get('dataName')] = (
                e.get('operation', 'Additive'), e.get('value', 0.0))
    return out


class SaveResearch:
    """One loaded save; computes research incomes for any faction in it."""

    def __init__(self, save_path):
        self.gs = er.load_save(save_path)['gamestates']
        gs = self.gs
        self.date, _ = er.get_game_date(gs)
        self.nations = dict(er.kv_items(gs, _NS + 'TINationState'))
        self.regions = dict(er.kv_items(gs, _NS + 'TIRegionState'))
        self.cps = dict(er.kv_items(gs, _NS + 'TIControlPoint'))
        self.councilors = dict(er.kv_items(gs, _NS + 'TICouncilorState'))
        self.orgs = dict(er.kv_items(gs, _NS + 'TIOrgState'))
        self.habs = dict(er.kv_items(gs, _NS + 'TIHabState'))
        self.modules = list(er.kv_items(gs, _NS + 'TIHabModuleState'))
        self.effstate = list(er.kv_items(gs, _NS + 'TIEffectsState'))
        self.factions = er.get_factions(gs)
        self.templates = er.load_game_templates()
        self.extra = _load_templates_extra()
        self._sec_to_hab = {}
        for hid, h in self.habs.items():
            for s in (h.get('sectors') or []):
                self._sec_to_hab[er.deref(s)] = hid

    # ---------- councilor science ----------
    def eff_science(self, cid):
        """GetAttribute(Science): base + org science + unconditional trait mods."""
        c = self.councilors.get(cid, {}) or {}
        sci = (c.get('attributes', {}) or {}).get('Science', 0) or 0
        sci += sum((self.orgs.get(er.deref(o), {}) or {}).get('science', 0) or 0
                   for o in (c.get('orgs') or []))
        sci += sum(self.extra['trait_sci'].get(tn, 0)
                   for tn in (c.get('traitTemplateNames') or []))
        return sci

    # ---------- nation research ----------
    def adviser_science_bonus(self, nation):
        """GetAdvisingScore(Science): Σ sci_i/100/(i+1), best advisor first."""
        b = sorted((self.eff_science(er.deref(a)) / 100.0
                    for a in (nation.get('advisingCouncilors') or [])), reverse=True)
        return sum(x / (i + 1) for i, x in enumerate(b))

    def research_month(self, nid):
        """TINationState.get_research_month — the Nations-screen research value."""
        n = self.nations[nid]
        pop = sum((self.regions.get(er.deref(r), {}) or {}).get('populationInMillions', 0) or 0
                  for r in (n.get('regions') or []))
        if pop <= 0:
            return 0.0
        pc = (n.get('GDP') or 0) / (pop * 1e6)
        if pc <= 30000:
            g = (pc / 15000.0) ** 0.6
        else:
            g = 1.515716552734375 + 0.90942996740341187 * (math.log(pc / 15000.0)
                                                           - 0.69314718246459961)
        edu = n.get('education') or 0.0
        dem = n.get('democracy') or 0.0
        coh = n.get('cohesion') or 0.0
        unr = n.get('unrest') or 0.0
        ncp = n.get('numControlPoints') or 0
        base = pop * g * (edu * min(edu, 12.0)) * max(dem, 1.0) ** (1 / 6) * 0.0075
        base += min(pop * 1e6 / 5000.0, ncp + edu + dem / 2.0)
        return (base * (1.25 - abs(coh - 5.0) / 10.0) * (1.0 - unr * unr * 0.01)
                * (1.0 + self.adviser_science_bonus(n)))

    def cp_research_mult(self, fid):
        """Product of the faction's multiplicative ControlPointResearch effects."""
        mult, add = 1.0, 0.0
        for _, e in self.effstate:
            for entry in (e.get('factionEffectsNames') or []):
                if er.deref(entry.get('Key')) != fid:
                    continue
                for en in ((entry.get('Value') or {}).get('ControlPointResearch') or []):
                    op, v = self.extra['cp_res_effects'].get(en, ('Additive', 0.0))
                    if op == 'Multiplicative':
                        mult *= v
                    else:
                        add += v
        return mult, add

    def nations_income(self, fid):
        """Per-nation research the faction receives (monthly) + total.
        = Σ myCPs(not benefitsDisabled): research_month×ks×mult/numCP  (+ additive/numCP)."""
        mult, add = self.cp_research_mult(fid)
        per = {}
        for cp in self.cps.values():
            if er.fac_id_from_field(cp.get('faction')) != fid or cp.get('benefitsDisabled'):
                continue
            nid = er.deref(cp.get('nation'))
            d = per.setdefault(nid, {'cps': 0, 'ks': False})
            d['cps'] += 1
            if cp.get('controlPointType') == 'KnowledgeSector':
                d['ks'] = True
        rows = []
        for nid, d in per.items():
            n = self.nations[nid]
            rm = self.research_month(nid)
            ncp = max(n.get('numControlPoints') or 1, 1)
            ks = KS_BONUS if d['ks'] else 1.0
            contrib_mo = (rm * ks * mult + add) / ncp * d['cps']
            rows.append({'template': n.get('templateName'),
                         'name': (n.get('displayName') or n.get('templateName')),
                         'research_month': rm, 'my_cps': d['cps'], 'num_cps': ncp,
                         'knowledge_sector': d['ks'], 'player_month': contrib_mo})
        rows.sort(key=lambda r: -r['player_month'])
        total_mo = sum(r['player_month'] for r in rows)
        return rows, total_mo

    # ---------- other tooltip terms ----------
    def hq_income_day(self, fac):
        return ((fac.get('baseIncomes_year') or {}).get('Research', 0) or 0) / DAYS_YR

    def councilor_income_month(self, fac):
        total = 0.0
        for cid in (er.deref(c) for c in (fac.get('councilors') or [])):
            c = self.councilors.get(cid, {}) or {}
            if c.get('detained'):
                continue
            base = sum((self.orgs.get(er.deref(o), {}) or {}).get('incomeResearch_month', 0) or 0
                       for o in (c.get('orgs') or []))
            base += sum(self.extra['trait_res'].get(tn, 0)
                        for tn in (c.get('traitTemplateNames') or []))
            if base > 0:
                total += base * (1.0 + self.eff_science(cid) / 100.0)
        return total

    def hab_income_month(self, fid):
        mri = self.templates.get('module_research_income', {})
        total = 0.0
        for _, m in self.modules:
            if not m.get('constructionCompleted') or not m.get('powered', True):
                continue
            hid = self._sec_to_hab.get(er.deref(m.get('sector')))
            if hid is None or er.deref((self.habs.get(hid) or {}).get('faction')) != fid:
                continue
            total += mri.get(m.get('templateName'), 0) or 0
        return total

    def mission_control(self, fid):
        """(maxMC, usedMC). max = HQ+councilor+hab+nation MC; used = reported demand."""
        hab_inv = er.extract_hab_inventory(self.gs, fid)
        mc = er.extract_mc_full(self.gs, fid, hab_inv, self.factions)
        nation_mc = 0
        for cp in self.cps.values():
            if er.fac_id_from_field(cp.get('faction')) != fid or cp.get('benefitsDisabled'):
                continue
            n = self.nations[er.deref(cp.get('nation'))]
            cur = sum((self.regions.get(er.deref(r), {}) or {}).get('missionControl', 0) or 0
                      for r in (n.get('regions') or []))
            ncp = max(n.get('numControlPoints') or 1, 1)
            share = cur // ncp
            if (cp.get('positionInNation') or 0) >= ncp - (cur % ncp):
                share += 1
            nation_mc += share
        max_mc = (mc.get('mc_hq', 0) or 0) + (mc.get('mc_councilors', 0) or 0) \
                 + (mc.get('mc_hab_produced', 0) or 0) + nation_mc
        return max_mc, (mc.get('mc_used_reported', 0) or 0)

    def distribution_pct(self, fac):
        rw = fac.get('researchWeights') or []
        slots = sum(1 for i in (0, 1, 2, 3) if len(rw) > i and rw[i] > 0)
        if fac.get('orgProjectSlotUnlocked') and len(rw) > 4 and rw[4] > 0:
            slots += 1
        if fac.get('habProjectSlotUnlocked') and len(rw) > 5 and rw[5] > 0:
            slots += 1
        return DIST_PER_SLOT * slots

    # ---------- assembled breakdown ----------
    def breakdown(self, faction_template=None, with_mc=True):
        from ti_config import require_faction
        faction_template = require_faction(faction_template)
        fid = er.faction_id_by_template(self.factions, faction_template)
        fac = self.factions[fid]
        rows, nations_mo = self.nations_income(fid)
        hq_day = self.hq_income_day(fac)
        counc_day = self.councilor_income_month(fac) * 12 / DAYS_YR
        habs_day = self.hab_income_month(fid) * 12 / DAYS_YR
        nations_day = nations_mo * 12 / DAYS_YR
        mc_day = 0.0
        if with_mc:
            max_mc, used_mc = self.mission_control(fid)
            mc_day = max(0, max_mc - used_mc) * EXCESS_MC_RESEARCH_DAY
        dist_pct = self.distribution_pct(fac)
        base_day = hq_day + counc_day + nations_day + habs_day + mc_day
        total_day = base_day * (1 + dist_pct)
        # actually-booked daily research from the transactions ledger (save ground truth)
        di = (fac.get('Transactions') or {}).get('Daily Income') or []
        booked = [e.get('Amount', 0) for e in di if e.get('Resource') == 'Research']
        return {
            'date': self.date, 'faction': faction_template,
            'hq_day': hq_day, 'councilors_day': counc_day, 'nations_day': nations_day,
            'habs_day': habs_day, 'unused_mc_day': mc_day, 'dist_pct': dist_pct,
            'dist_day': base_day * dist_pct, 'total_day': total_day,
            'total_month': total_day * MO, 'nations_month': nations_mo,
            'nation_rows': rows, 'booked_day': booked[-1] if booked else 0.0,
        }


def fmt_day(x):
    return f"{x:8.1f}/day ({x * MO:8.0f}/mo)"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('save', nargs='?', help='save .json (default: newest in the saves dir)')
    ap.add_argument('--faction', default=None)
    ap.add_argument('--all-factions', action='store_true',
                    help='also print rival faction research estimates (cf. Intel screen)')
    ap.add_argument('--rivals', default=None,
                    help='HF,Init,Serv,Prot,Acad,Exod monthly from Intel (for Table H row)')
    ap.add_argument('--nations', default=None,
                    help='comma-separated nation templateNames for the Table H per-nation '
                         'columns (default: config anchor_nations, else auto-detect)')
    a = ap.parse_args()
    from ti_config import require_faction
    a.faction = require_faction(a.faction)

    save = a.save
    if not save:
        from ti_config import newest_save
        ns = newest_save()
        save = str(ns) if ns else None
    if not save or not os.path.isfile(save):
        sys.exit('no save file found/given')

    sr = SaveResearch(save)
    b = sr.breakdown(a.faction)

    print(f"\n=== faction research income — {b['date']}  ({a.faction}) ===")
    print(f"  HQ           {fmt_day(b['hq_day'])}")
    print(f"  Councilors   {fmt_day(b['councilors_day'])}")
    print(f"  Nations      {fmt_day(b['nations_day'])}")
    print(f"  Habs         {fmt_day(b['habs_day'])}")
    if b['unused_mc_day']:
        print(f"  Unused MC    {fmt_day(b['unused_mc_day'])}")
    print(f"  Distribution {fmt_day(b['dist_day'])}   [+{b['dist_pct']:.0%} of the above]")
    print(f"  TOTAL        {fmt_day(b['total_day'])}   [in-game 🧪 tooltip figure]")
    print(f"  (booked in ledger: {b['booked_day']:.1f}/day — excludes the distribution "
          f"bonus & any same-day changes)")

    print(f"\n  --- per-nation research (what {a.faction} receives) ---")
    print(f"  {'nation':24s} {'research/mo':>11s} {'CPs':>7s} {'KS':>3s} {'→ player/mo':>12s} {'/day':>7s}")
    for r in b['nation_rows']:
        print(f"  {r['name'][:24]:24s} {r['research_month']:11.1f} "
              f"{r['my_cps']:>3d}/{r['num_cps']:<3d} {'✓' if r['knowledge_sector'] else '·':>3s} "
              f"{r['player_month']:12.1f} {r['player_month'] * 12 / DAYS_YR:7.2f}")

    # rival columns for Table H, in the order HF,Init,Serv,Prot,Acad,Exod
    rival_computed = None
    if a.all_factions:
        print("\n  --- rival factions (computed; Intel shows monthly research) ---")
        rival_computed = []
        for ftmpl in ('DestroyCouncil', 'ExploitCouncil', 'SubmitCouncil',
                      'AppeaseCouncil', 'CooperateCouncil', 'EscapeCouncil'):
            try:
                rb = sr.breakdown(ftmpl, with_mc=False)
                rival_computed.append(f"{rb['total_day'] * MO:,.0f}")
                print(f"  {ftmpl:17s} {rb['total_day'] * MO:9.0f}/mo  "
                      f"(nations {rb['nations_month']:7.0f}, counc {rb['councilors_day'] * MO:6.0f}, "
                      f"habs {rb['habs_day'] * MO:6.0f}, dist {rb['dist_pct']:.0%})")
            except Exception as ex:
                rival_computed.append('?')
                print(f"  {ftmpl:17s} — {ex}")

    # Campaign-log timeline row (research-income table)
    anchors = er.resolve_anchor_nations(sr.gs, faction_template=a.faction,
                                        cli_value=a.nations)

    nid_by_template = {nv.get('templateName'): nid for nid, nv in sr.nations.items()}

    def anchor_rm(t):
        """research_month for an anchor nation, whether or not we hold a CP there."""
        r = next((r for r in b['nation_rows'] if r['template'] == t), None)
        if r:
            return r['research_month']
        nid = nid_by_template.get(t)
        return sr.research_month(nid) if nid is not None else None
    anchor_rms = [anchor_rm(t) for t in anchors]
    # explicit --rivals (Intel ground truth) wins; else computed --all-factions; else placeholders
    if a.rivals:
        rv = (a.rivals.split(',') + ['?'] * 6)[:6]
    elif rival_computed:
        rv = (rival_computed + ['?'] * 6)[:6]
    else:
        rv = ['?'] * 6
    hqc = (b['hq_day'] + b['councilors_day']) * MO
    labels = " / ".join(er.nation_label(t) for t in anchors)
    print(f"\n--- paste into Table H (research_month per nation; nations total = player share) ---")
    print(f"--- per-nation columns (anchors): {labels} — changing anchors mid-campaign "
          f"breaks log-column comparability ---")
    nation_cells = " | ".join(
        f"{rm:,.1f}" if rm is not None else "?" for rm in anchor_rms)
    print(f"| {b['date']} | {b['total_month']:,.0f} | {b['nations_month']:,.0f} | "
          f"{nation_cells} | {b['habs_day'] * MO:,.0f} | "
          f"{b['dist_day'] * MO:,.0f} | {hqc:,.0f} | " + " | ".join(rv) + " |")


if __name__ == '__main__':
    main()
