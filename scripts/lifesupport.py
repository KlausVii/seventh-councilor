#!/usr/bin/env python3
"""lifesupport.py — CANONICAL per-hab / per-module LIFE-SUPPORT for TI (WATER + VOLATILES).

Computes the HAB-MODULE component of faction water/volatiles income, hab-by-hab, module-by-module,
from the decompiled formula (TIHabState.GetNetCurrentMonthlyIncome / TIHabModuleTemplate.
MonthlySupportCost + MonthlyCrewSupportCost). Formula STRUCTURE from the Armandox33 decompile
(0.4.x-era Early Access); NUMBERS calibrated/validated against the LIVE build's in-game tooltips
(originally build 1.0.38, re-validated here on a 1.0.39 save — see the population patch-drift note).

⚠⚠ VOLATILES have a life-support drain IDENTICAL in form to water (docs/lessons/LESSONS-economy.md
E35). Crew consume volatiles at the SAME 3.5 t/crew/yr rate as water (crewVolatilesConsumptionTons_
year == crewWaterConsumptionTons_year == 3.5, VERIFIED in TIGlobalConfig.cs → the SAME R). Farms
("recycles matter into fresh food and breathable air") offset BOTH water and volatiles crew upkeep
(Farm tooltip, verified: "up to 600 crew, 17.5 water + 17.5 volatiles/month" = 600×R each), and
modules carry an innate volatiles upkeep (supportMaterials_month.volatiles, e.g. FusionReactorFarm
6/mo) that Farms do NOT defray. `--resource volatiles` folds mine PRODUCTION into the same balance.

*** TWO GROUND-TRUTH FACTS that reconcile the tooltip (verified vs decompiled source + 2033-09-26) ***
  1. The resource tooltip's headline ("Our daily income from our habs is X / monthly Y") is
     GetDailyIncome = the faction GRAND TOTAL (habs + HQ baseIncomes + nations + councilors + ships
     + diplomacy + orgs + excess-MC), NOT habs-only despite the label (GeneralControlsController.
     AssembleSpaceResourceTooltip passes GetDailyIncome). For water/volatiles the only non-hab term
     that's ever non-zero is HQ base income (baseIncomes_year); this tool adds it as a separate line
     so 'FACTION TOTAL' ≈ the tooltip. (nations/councilors/orgs carry no space-resource income.)
  2. The hab "population" / farm-offset cap (Min(farmValue, this.crew)) uses Σ FULL TEMPLATE crew of
     okay modules in the CURRENT build — VERIFIED by the calibration hab (pop 2772 = Σ template crew,
     Farm "65% discount" = 1800/2772). The decompiled Armandox33 source is 0.4.x-era Early Access
     (repo pushed 2025-06; the pre-RC1 build was 0.4.90a), and there its TIHabModuleState.crew getter
     returns prior/0 for building modules (Σ state.crew = 497 on that hab). That's PATCH DRIFT: between
     the decompile and the live 1.0.39 the game shipped a big overhaul (Release Candidate 1, "final
     major update before 1.0", 2025-11) → RC13 → 1.0 → 1.0.39, and population now counts designed
     crew. (The exact changelog line isn't quotable — Pavonis posts detailed notes only on Discord /
     their Cloudflare-walled site; Steam carries summaries only. So we follow the live tooltip as
     ground truth, not the stale getter.) The compute() uses habcrew (template crew).

Validated 2033-09-26 (Resistance, 200% research): FACTION TOTAL volatiles +1,570/mo vs tooltip
1,542 (+1.8%); water +9,169 vs tooltip 9,127 (+0.5%). Residual is the derived global mining
multiplier's precision — the game exposes it only as the rounded "89% bonus" (volatiles, ×1.89) /
"150% bonus" (water, ×1.15²×1.89). Machinery cross-checked EXACT on the no-crew/no-farm resources:
metals +13.2K, nobles +3.6K, fissiles +809 — all match the top bar to <1 ton.

⚠⚠ THE HAB WATER TOOLTIP ("daily income from our habs is X") = THIS TERM ⚠⚠
Calibrated to the 2033-03 tooltips (229 +58.1/day, 230 reloaded +53.2/day). Two parts:
  • PRODUCTION: mine water × K (K encodes the FULL stated "106% bonus to production" — my
    derived K=62.8 = 30.44 × 2.063; = MiningWaterBonus techs ×1.15² + SpaceMiningBonus +0.20 +
    org miningBonus +0.36). Production is EXACT — the tooltip's 106% matches K; there is no
    missing water tech, and NO Administration adviser (in the reference campaign no hab is advised, so
    hab.advisingCouncilors is empty and the multiplier is 1.0).
  • CONSUMPTION (per-hab, EXACT — matches the HABS-list water column to 0.1):
      crew life support = template.crew × R for EVERY okay module (active + unpowered + building,
        at FULL template crew — Σ = the hab "population" number, e.g. 2455 on the validation hab)
      + material water upkeep (supportMaterials_month.water) on POWERED modules only
      − farm offset = min(600×#poweredFarms, population) × R
    Verified 2033-04-01 on a 2,455-crew colony hab: crew×R=71.6 + material 15 (5 ResearchCampus×3, the
    building mining complex's 15 does NOT count) − farm 0 (all 3 farms unpowered) = −86.6, EXACT.
    Per-module tooltips confirm: Colony Core 125→3.6, Colony Mining Complex 200→5.8, Farm 5→0.15.
  • FACTION "income from habs" tooltip = Σ(per-hab net), EXACT. 2033-04-01: Σ = +1793/mo =
    +58.91/day, matching the tooltip's +58.9/day to the decimal. (No adviser, no powered-crew
    basis, no version gap — those were all wrong theories compensating for a production bug: habs
    whose CORE was mid-UPGRADE were zeroed out because the code required a *completed* core module.
    Fix: read the stored `hab.anyCoreCompleted` flag, which stays True through a core upgrade.)
    Faction water is nominally 8 terms (Habs+Ships+HQ+…) but for water the habs term IS the total.

*** THE MYSTERY THIS TOOL SOLVED (2033-03, saves 229/230/233) ***
"Water fell from +58/day (229) to -3.7/day (230) after I only turned off a mine + started
CC upgrades." GROUND TRUTH: 229 and 230 hab modules are near-identical → this tool gives
identical HAB income both saves (+58.1/day tooltip, +1770/mo). The hab water income did NOT
change. The -3.7/day was the TOP-BAR net at that instant, dragged down by a fleet
**ResupplyAndRepairOperation** (-22.5 water, one tx) in flight when 230 was saved: water stock
23.27 -> 0.80 (Δ = -22.47 ≈ the -22.5 op). "Income from habs" (the tooltip) stayed +58 in
both; the top bar dipped only while the resupply drew. The "+1858/mo life-support eater"
never existed. Life support is slow/structural and does not swing 60/day between two saves
5 hours apart — when water lurches with static hab inventory, look at FLEETS first.

THE HAB FORMULA (per hab, monthly, resource = Water) — matches the HABS-list water column exactly
--------------------------------------------------------------------------------------------------
  crew life support = template.crew * R   for EVERY okay module (active, unpowered, AND building,
                                          at FULL template crew; Σ = the hab "population" number)
  + material water upkeep (supportMaterials_month.water [+ fissiles if UsesHelium3 & He3Access])
                                          POWERED modules only
  + mine water production                 POWERED mines only (× K)
  − farm offset = min(600 * #poweredFarms, population) * R      POWERED farms only
  hab net = production − (crewLS_all_okay + material_powered − farmOffset)
  where R = 3.5 * 0.1 / 12 = 0.0291667 water/crew/mo.

  farmValue = sum specialRulesValue(=600) over ACTIVE Farm modules
  farmOffset = min(farmValue, habCrew) * R          # habCrew = Σ FULL TEMPLATE crew (= population)
  hab net water = income - (cost - farmOffset)

where  R = crewWaterConsumptionTons_year(3.5) * spaceResourceToTons(0.1) / 12
         = 0.0291667 water/crew/month   (600 crew Farm = 17.5/mo; 1000 crew CC = 29.2/mo)
Validated: a T2 station computes -46.2/mo, EXACTLY matching its in-game tooltip.

⚠ CREW BASIS — the LIVE build (1.0.39) charges crew life support AND caps the farm offset on Σ FULL
TEMPLATE crew of every okay module (incl. under-construction ones), which IS the in-game "population"
(verified: the calibration hab shows pop 2772 = Σ template crew, and its Farm's "65% discount" =
farmValue 1800 / 2772). This DIFFERS from the 0.4.x-era decompile's TIHabModuleState.crew getter
(completed->template.crew, building-new->0, building-upgrade->prior; the `state_crew()` helper below),
which would give 497 on that hab. PATCH DRIFT between the decompile and 1.0.39 (see the volatiles
note up top). compute() follows the live tooltip = template crew (`habcrew`), NOT state_crew.

CommandCenter upgrade water cost (verified vs saves 235/236 = -0.7/day per CC): it is NOT
charged on click. While the CC upgrade is under construction the module still reports the
PRIOR OperationsCenter's 200 crew (state.crew), so ~0 change; the extra (1000-200)*R =
+23.3/mo hits only when the upgrade COMPLETES and crew jumps 200 -> 1000.

Usage:  python3 lifesupport.py <save.json> [<save2> ...] [--faction <templateName>]
        python3 lifesupport.py <save.json> --resource volatiles   # NET volatiles income
        python3 lifesupport.py --diff <saveA> <saveB> [--resource volatiles]  # module diff
"""
import sys, os, json, argparse
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mine_completion_timeline import (load_save, kv_items, deref, fac_id_from_field,
                                       derive_K_income)

R = 3.5 * 0.1 / 12.0            # tons/crew/month — SAME rate for water AND volatiles (E35),
                               # verified vs Farm & CC tooltips (crewWaterConsumptionTons_year
                               # 3.5 × spaceResourceToTons 0.1 / 12); volatiles reuses it exactly.
HERE = os.path.dirname(os.path.abspath(__file__))

# Efficiency special-rule modules → administrationModuleModifier = Π(1+value) over ACTIVE ones.
EFFICIENCY = {'AdministrationNode': 0.025, 'AdministrationTower': 0.05, 'AdministrationComplex': 0.1}
# Administration ADVISER multiplier (production ×= 1 + advising-councilor Administration/100).
# DEFAULT 1.0: if no councilor is advising a hab, advisingCouncilors is empty → no bonus. Keep the
# hook only for games that DO advise habs. (An earlier 1.156 here was bogus — it silently masked a
# crew over-charge, since fixed by charging crew life support on ACTIVE modules only.)
DEFAULT_ADMIN_ADVISER = 1.0


def state_crew(m, T):
    """The DECOMPILED (0.4.x-era) TIHabModuleState.crew getter: completed->template.crew;
    building-new->0; building-upgrade->prior template crew.

    ⚠ NOT used by compute() — the LIVE build's hab population (and the Farm-offset cap) counts
    FULL template crew for every okay module, incl. building ones (verified: calibration-hab pop
    2772 = Σ template crew, not the 497 this getter yields). Retained as a reference for the
    patch-drift and for callers that want the old current-population number. See module docstring."""
    if m.get('destroyed'):
        return 0
    if not m.get('constructionCompleted'):
        if m.get('priorModuleCompleted') and m.get('priorModuleTemplateName'):
            return T.get(m['priorModuleTemplateName'], {}).get('crew', 0)
        return 0
    return T.get(m['templateName'], {}).get('crew', 0)


def load_templates():
    mt = json.load(open(os.path.join(HERE, 'templates', 'TIHabModuleTemplate.json')))
    T = {}
    for m in mt:
        sm = m.get('supportMaterials_month') or {}
        T[m['dataName']] = {
            'crew': m.get('crew', 0) or 0,
            'water_up': sm.get('water', 0) or 0,
            'vol_up': sm.get('volatiles', 0) or 0,      # innate volatiles upkeep (E35)
            'fissiles_up': sm.get('fissiles', 0) or 0,
            'core': bool(m.get('coreModule')),
            'mine': bool(m.get('mine')),
            'mining_mod': m.get('miningModifier', 1) or 1,
            'rules': set(m.get('specialRules') or []),
            'rules_val': m.get('specialRulesValue', 0) or 0,
        }
    return T


def compute(save_path, faction_tmpl=None, resource='water', verbose=True,
            adviser=DEFAULT_ADMIN_ADVISER):
    """Per-hab life-support + mine-production balance for RESOURCE ∈ {water, volatiles}.

    Water and volatiles share the SAME structure (E35): crew life support = crew × R on every
    okay module; innate module upkeep = supportMaterials_month[resource] on POWERED modules;
    mine production on POWERED mines × K[resource]; Farm offset = min(600×poweredFarms, pop) × R
    defraying crew upkeep only. Because production is folded in, the per-hab `net` and its Σ ARE
    the faction NET income the in-game tooltip shows for that resource.
    """
    if resource not in ('water', 'volatiles'):
        raise SystemExit(f"--resource must be water or volatiles, not {resource!r}")
    from ti_config import require_faction
    faction_tmpl = require_faction(faction_tmpl)
    gs = load_save(save_path)['gamestates']
    T = load_templates()
    faction_id = next((fid for fid, fv in kv_items(gs, 'TIFactionState')
                       if fv.get('templateName') == faction_tmpl), None)
    fac = dict(kv_items(gs, 'TIFactionState')).get(faction_id, {})
    he3 = bool(fac.get('He3Access'))
    K, K_breakdown = derive_K_income(gs, faction_id)

    sectors = dict(kv_items(gs, 'TISectorState'))
    sector_to_hab = {sid: deref(sv.get('hab')) for sid, sv in sectors.items()}
    habs = dict(kv_items(gs, 'TIHabState'))
    sites = dict(kv_items(gs, 'TIHabSiteState'))
    bodies = {bid: (bv.get('displayName') or bv.get('templateName') or '?')
              for bid, bv in kv_items(gs, 'TISpaceBodyState')}

    hab_mods = defaultdict(list)
    for mid, mv in kv_items(gs, 'TIHabModuleState'):
        name = mv.get('templateName')
        if not name:
            continue
        if mv.get('destroyed') or mv.get('decommissioning'):
            continue                                   # not okay
        sid = deref(mv.get('sector'))
        hid = sector_to_hab.get(sid)
        if hid is None or hid not in habs:
            continue
        if fac_id_from_field(habs[hid].get('faction')) != faction_id:
            continue
        hab_mods[hid].append(mv)

    per_hab = []
    mod_ledger = []            # (hab, module, state, crew_water, mat_water, income)
    n_pwr_farms = 0            # powered Farm modules (for the reconciliation label)
    for hid, mods in hab_mods.items():
        hv = habs[hid]
        hab_name = hv.get('displayName') or hv.get('templateName') or '?'
        site = sites.get(deref(hv.get('habSite')), {})
        body = bodies.get(deref(site.get('parentBody')), '(orbital)')
        core_done = bool(hv.get('anyCoreCompleted'))   # stored flag: True even while the core
                                                        # is UPGRADING (prior core keeps hab live)
        # Mirror TIHabState.GetNetCurrentMonthlyIncome (structure from the 0.4.x-era decompile;
        # the this.crew population basis follows the LIVE 1.0.39 build — see patch-drift note):
        #   num2 = Σ mine production (active) ; num3 = Σ crew LS (all okay, TEMPLATE crew)
        #        + Σ material upkeep (active) ; num4 = Σ farm specialRulesValue (active)
        #   num4 = min(num4, this.crew)   # this.crew = Σ STATE crew (0 for building-new)
        #   num2 *= AdministrationAdviser × administrationModuleModifier (Efficiency modules)
        #   num3 -= num4 × R ; num3 = max(num3, 0) ; net = num2 − num3
        income = mat_cost = farmval = habcrew = 0.0
        crew_all = 0.0                   # crew life support: TEMPLATE crew × R over ALL okay modules
        admin_mod = 1.0                  # administrationModuleModifier = Π(1+value) over ACTIVE Efficiency
        for m in mods:
            name = m['templateName']
            tt = T.get(name)
            if tt is None:
                continue
            completed = bool(m.get('constructionCompleted'))
            active = completed and bool(m.get('powered')) and core_done
            crew = tt['crew']              # FULL template crew — crew LS basis AND the hab "population"
            habcrew += crew                # in-game population (verified 2772 on the calibration hab);
                                           # also the farm-offset cap basis in the CURRENT build
            crew_all += crew * R           # crew LS: MonthlyCrewSupportCost uses moduleTemplate.crew,
                                           # charged for EVERY okay module (active + unpowered + building)
            mat_w = 0.0
            inc = 0.0
            if active:
                if resource == 'water':
                    # water carries the decompiled He3 cross-charge; volatiles does not (E35)
                    mat_w = tt['water_up'] + (tt['fissiles_up'] if ('UsesHelium3' in tt['rules'] and he3) else 0.0)
                else:
                    mat_w = tt['vol_up']   # innate volatiles upkeep, POWERED modules only
                if tt['mine']:
                    inc = (site.get(resource + '_day', 0) or 0) * tt['mining_mod'] * K[resource]
                if 'Farm' in tt['rules']:
                    farmval += tt['rules_val']
                    n_pwr_farms += 1
                if 'Efficiency' in tt['rules']:
                    admin_mod *= 1.0 + tt['rules_val']   # Administration Node/Tower/Complex
            mat_cost += mat_w
            income += inc
            state = 'active' if active else ('built/unpowered' if completed else 'building')
            mod_ledger.append((hab_name, name, state, crew * R, mat_w, inc))
        farm_off = min(farmval, habcrew) * R             # Min(farmValue, this.crew); this.crew = Σ
                                                          # TEMPLATE crew in the current build (ground
                                                          # truth: Farm tooltip's "65% discount" = 1800/2772)
        income_b = income * adviser * admin_mod          # num2 × AdministrationAdviser × adminModuleModifier
        support = max(crew_all + mat_cost - farm_off, 0.0)   # num3, clamped ≥0 (Mathf.Max(num3, 0))
        clamp = max(0.0, farm_off - (crew_all + mat_cost))   # farm offset lost to the ≥0 clamp
        net_shown = income_b - support                   # net = num2 − num3
        per_hab.append({'hab': hab_name, 'body': body, 'income': income,
                        'boost': income_b - income, 'crew_all': crew_all, 'mat': mat_cost,
                        'farm_off': farm_off, 'clamp': clamp, 'net': net_shown, 'crew': habcrew})

    per_hab.sort(key=lambda r: r['net'])
    tot = {k: sum(h[k] for h in per_hab)
           for k in ('income', 'boost', 'crew_all', 'mat', 'farm_off', 'clamp', 'net')}
    tot['n_pwr_farms'] = n_pwr_farms
    tot['global_mult'] = (K_breakdown or {}).get('global_mult')
    # Tooltip's "N% bonus to production" is RESOURCE-SPECIFIC: K/base − 1 =
    # (1.15^res_count × global_mult) − 1. Water (×1.15²): 150%; volatiles (×1.15⁰): 89%.
    from mine_completion_timeline import DAYS_PER_MONTH
    tot['res_bonus_pct'] = (K[resource] / DAYS_PER_MONTH - 1.0) * 100.0
    # Faction-level HQ base income (baseIncomes_year) — NOT a hab/life-support term, but the
    # in-game resource tooltip's headline number is GetDailyIncome = the GRAND TOTAL (habs + HQ +
    # nations + councilors + ships + diplomacy + orgs + excess-MC). For water/volatiles the only
    # non-hab term that's ever non-zero is HQ base (nations/councilors/orgs carry no space-resource
    # income; ships/diplomacy/excess-MC are 0 for these). Add it so 'faction total' ≈ the tooltip.
    tot['hq_base'] = (fac.get('baseIncomes_year') or {}).get(resource.capitalize(), 0.0) / 12.0
    tot['faction_total'] = tot['net'] + tot['hq_base']
    if verbose:
        RES = resource.capitalize()
        print(f"\n=== {os.path.basename(save_path)} — hab {resource} balance ===")
        print(f"{'hab':32s} {'body':10s} {'mineInc':>8s} {'crewLS':>8s} {'matUpk':>7s} "
              f"{'farmOff':>8s} {'NET/mo':>8s} {'pop':>6s}")
        for h in per_hab:
            print(f"{h['hab'][:32]:32s} {h['body'][:10]:10s} {h['income']:8.1f} {h['crew_all']:8.1f} "
                  f"{h['mat']:7.1f} {h['farm_off']:8.1f} {h['net']:8.1f} {int(h['crew']):6d}")
        # Reconciliation: GROSS mine production → NET income (matches the in-game tooltip).
        # The tooltip's "N% bonus to production" is RESOURCE-SPECIFIC (global × 1.15^res_count − 1).
        gmult = f" — mining bonus {round(tot['res_bonus_pct'])}% (== tooltip)"
        LBL = 40
        print(f"\n=== {RES} NET income reconciliation (faction 'income from habs' tooltip){gmult} ===")
        print(f"  {'GROSS mine '+resource+' (powered mines):':<{LBL}}{tot['income']:+9.1f}/mo")
        if abs(tot['boost']) > 0.05:
            print(f"  {'+ Efficiency boost (Admin modules):':<{LBL}}{tot['boost']:+9.1f}/mo")
        print(f"  {'− crew life-support (Σ template crew × R):':<{LBL}}{-tot['crew_all']:+9.1f}/mo")
        print(f"  {'− module innate upkeep (powered):':<{LBL}}{-tot['mat']:+9.1f}/mo")
        print(f"  {f'+ Farm offset ({n_pwr_farms} powered Farms, ≤pop):':<{LBL}}{tot['farm_off']:+9.1f}/mo")
        if abs(tot['clamp']) > 0.05:
            print(f"  {'− offset lost to ≥0 support floor:':<{LBL}}{-tot['clamp']:+9.1f}/mo")
        print(f"  {'':<{LBL}}{'—'*10}")
        print(f"  {'= hab-module NET '+resource+':':<{LBL}}{tot['net']:+9.1f}/mo "
              f"= {tot['net']/30.44:+.1f}/day")
        if abs(tot['hq_base']) > 0.05:
            print(f"  {'+ faction HQ base income (baseIncomes):':<{LBL}}{tot['hq_base']:+9.1f}/mo")
            print(f"  {'':<{LBL}}{'—'*10}")
            print(f"  {'= FACTION TOTAL '+resource+' (≈ in-game tooltip):':<{LBL}}"
                  f"{tot['faction_total']:+9.1f}/mo = {tot['faction_total']/30.44:+.1f}/day")
        print(f"\n(The in-game resource tooltip's headline number is GetDailyIncome = the GRAND"
              f"\n TOTAL, not habs-only despite its 'income from our habs' label. For {resource} the"
              f"\n only non-hab term is HQ base income; hab-module net is the life-support core.)")
    return per_hab, tot, mod_ledger


def diff(a, b, faction=None, resource='water'):
    from ti_config import require_faction
    faction = require_faction(faction)
    _, ta, la = compute(a, faction, resource=resource, verbose=False)
    _, tb, lb = compute(b, faction, resource=resource, verbose=False)
    print(f"\n=== {resource.upper()} DIFF: {os.path.basename(a)} -> {os.path.basename(b)} ===")
    # 'income' = mine production, 'crew_all' = crew LS, 'mat' = module upkeep, 'farm_off', 'net'
    for k in ('income', 'crew_all', 'mat', 'farm_off', 'net'):
        print(f"  {k:9s}: {ta[k]:9.1f} -> {tb[k]:9.1f}   d {tb[k]-ta[k]:+8.1f}")
    def agg(l):
        d = defaultdict(lambda: [0.0, 0.0, 0.0, 0])
        for hab, mod, st, cw, mw, inc in l:
            key = (hab, mod, st)
            d[key][0] += cw; d[key][1] += mw; d[key][2] += inc; d[key][3] += 1
        return d
    da, db = agg(la), agg(lb)
    keys = set(da) | set(db)
    rows = []
    for key in keys:
        va = da.get(key, [0, 0, 0, 0]); vb = db.get(key, [0, 0, 0, 0])
        dcost = (vb[0] + vb[1]) - (va[0] + va[1])
        dinc = vb[2] - va[2]
        if abs(dcost) > 0.05 or abs(dinc) > 0.05:
            rows.append((dcost - dinc, key, va, vb, dcost, dinc))
    rows.sort(key=lambda r: -r[0])        # biggest net hit first
    print(f"\n  Top (hab,module,state) {resource} shifts (Dcost - Dincome, +=worse):")
    print(f"  {'hab':26s} {'module':22s} {'state':14s} {'#a':>3s}{'#b':>4s} {'Dcost':>8s} {'Dinc':>8s} {'Dnet':>8s}")
    for d, key, va, vb, dcost, dinc in rows[:35]:
        print(f"  {key[0][:26]:26s} {key[1][:22]:22s} {key[2]:14s} {va[3]:3d}{vb[3]:4d} "
              f"{dcost:8.1f} {dinc:8.1f} {-d:8.1f}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('saves', nargs='+')
    ap.add_argument('--faction', default=None)
    ap.add_argument('--resource', default='water', choices=('water', 'volatiles'),
                    help='which life-support resource to balance (default water)')
    ap.add_argument('--diff', action='store_true')
    a = ap.parse_args()
    from ti_config import require_faction
    a.faction = require_faction(a.faction)
    if a.diff:
        diff(a.saves[0], a.saves[1], a.faction, resource=a.resource)
    else:
        for s in a.saves:
            compute(s, a.faction, resource=a.resource)
