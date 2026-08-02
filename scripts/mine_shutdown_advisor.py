#!/usr/bin/env python3
"""mine_shutdown_advisor.py — which mines to power OFF to get under the MC cap
(and, with --power-on, what you can safely power back ON when slack returns).

Encodes the 2026-07 lesson set:
  - Mining-network MC is quadratic: cost = max(0, active − 36)²/2, so each shutdown at
    n active mines saves (n−36) − 0.5 MC — print the marginal, don't assume ~4/mine.
  - `missionControlUsage` is the game's EXACT used total; available/slack reconstruction
    over-reads (~7 post-fix) — this script does NOT reconstruct slack. Read the in-game
    top bar for the exact over/under number (LESSONS-economy E25); the save's
    `history_MCCapOverageByDay` (newest-first) is printed as the best in-save signal.
  - Rank shutdown candidates by ACTUAL income share, not raw score: a "low-score" mine
    can be 20% of faction fissile income (observed: score 37.8 but 134 fis/mo).
    Any mine supplying > --protect-share (default 10%) of a resource's total mining
    income is flagged 🔒 and pushed to the bottom.
  - Overage self-resolution: lists under-construction MC-PRODUCING modules
    (CommandCenter/OperationsCenter/Admin*) with ETAs — if +MC lands within days, one
    band-aid shutdown suffices (lesson 36). NB an OpsCenter→CommandCenter upgrade takes
    the OpsCenter OFFLINE while building (−4 until done) — a common cause of sudden overage.
  - Reminder printed: staying over cap DESTROYS modules (harsher since 1.0.38).

Usage:
    python3 mine_shutdown_advisor.py <save.json> [--faction <templateName>]
        [--need-mc N]          # how much over cap the in-game top bar shows (optional)
        [--protect-share 0.10] [--top 12] [--json]
"""
import json, argparse, sys, os
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mine_completion_timeline import (load_save, kv_items, deref, parse_dt,
                                      derive_K_income)

FREE_MINES = 36
MC_PRODUCERS = {'CommandCenter': 10, 'OperationsCenter': 4,
                'AdministrationNode': 0, 'AdministrationTower': 1,
                'AdministrationComplex': 2}
RES = ('metals', 'water', 'volatiles', 'nobles', 'fissiles')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('save')
    ap.add_argument('--faction', default=None)
    ap.add_argument('--need-mc', type=float, default=None,
                    help='MC to free (the in-game over-cap amount). If omitted, '
                         'suggests one mine + prints the marginal ladder.')
    ap.add_argument('--protect-share', type=float, default=0.10)
    ap.add_argument('--relax', default='',
                    help='comma-separated resources that are plentiful TODAY (weight 0.1, '
                         'protection off), e.g. --relax water')
    ap.add_argument('--tighten', default='',
                    help='comma-separated resources to guard extra hard (weight x2)')
    ap.add_argument('--top', type=int, default=12)
    ap.add_argument('--power-on', action='store_true',
                    help='inverse mode: list completed-but-UNPOWERED mines (actual income + '
                         'quadratic MC cost to re-enter the network) and unpowered MC '
                         'producers (OpsCenter/CommandCenter/Admin — these ADD headroom; '
                         'flip them FIRST), with sequencing advice')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    from ti_config import require_faction
    args.faction = require_faction(args.faction)

    gs = load_save(args.save)['gamestates']
    now = parse_dt(gs[next(k for k in gs if k.endswith('TITimeState'))][0]
                   ['Value']['currentDateTime'])
    fid, fac = None, None
    for f, v in kv_items(gs, 'TIFactionState'):
        if v.get('templateName') == args.faction:
            fid, fac = f, v
            break
    if fid is None:
        sys.exit(f'faction {args.faction} not found')

    K, kb = derive_K_income(gs, fid)
    here = os.path.dirname(os.path.abspath(__file__))
    from ti_config import find_templates_dir as _ftd
    _tdir = _ftd()
    if not _tdir:
        raise SystemExit('Game templates not found — run scripts/sync_game_data.py '
                         'or set game_install_dir in config.json.')
    mt = json.load(open(os.path.join(str(_tdir), 'TIHabModuleTemplate.json')))
    mine_mod = {m['dataName']: m.get('miningModifier', 1) for m in mt if m.get('mine')}

    s2h = {s: deref(v.get('hab')) for s, v in kv_items(gs, 'TISectorState')}
    habs = dict(kv_items(gs, 'TIHabState'))
    sites = dict(kv_items(gs, 'TIHabSiteState'))
    bodies = {b: (v.get('displayName') or '?') for b, v in kv_items(gs, 'TISpaceBodyState')}

    active = []            # powered mines with per-resource actual income
    unpowered_mines = []   # completed but switched off (--power-on candidates)
    unpowered_mc = []      # completed, unpowered MC producers (+headroom if flipped on)
    tot = defaultdict(float)
    pending_mc = []        # under-construction MC producers
    sup_mat = {m['dataName']: m.get('supportMaterials_month') for m in mt}
    for mid, mv in kv_items(gs, 'TIHabModuleState'):
        if mv.get('destroyed'):
            continue
        name = mv.get('templateName') or ''
        hid = s2h.get(deref(mv.get('sector')))
        h = habs.get(hid)
        if not h or deref(h.get('faction')) != fid:
            continue
        if name in MC_PRODUCERS and not mv.get('constructionCompleted'):
            eta = parse_dt(mv['completionDate']) if mv.get('completionDate') else None
            pending_mc.append((eta, h.get('displayName'), name, MC_PRODUCERS[name],
                               mv.get('priorModuleTemplateName') or ''))
        if name in MC_PRODUCERS and mv.get('constructionCompleted') and not mv.get('powered'):
            unpowered_mc.append((h.get('displayName'), name, MC_PRODUCERS[name],
                                 sup_mat.get(name) or {}))
        if name in mine_mod and mv.get('constructionCompleted'):
            site = sites.get(deref(h.get('habSite')), {})
            inc = {r: (site.get(r + '_day', 0) or 0) * mine_mod[name] * K[r] for r in RES}
            body = bodies.get(deref(site.get('parentBody')), '?')
            rec = {'hab': h.get('displayName'), 'body': body, 'module': name, 'inc': inc}
            if mv.get('powered'):
                active.append(rec)
                for r in RES:
                    tot[r] += inc[r]
            else:
                unpowered_mines.append(rec)

    n = len(active)
    over = max(0, n - FREE_MINES)
    marginal = over - 0.5 if over else 0.0

    # Scarcity weights from TODAY's stockpile cover (stock / cachedYearlyRevenue-day).
    # cachedYearlyRevenue is stale (lesson 69) so this is directional — tiers, not
    # precision: <10d ->4, <30d ->2.5, <90d ->1.5, <180d ->0.8, else 0.4.
    # --relax RES forces 0.1 (user says it's plentiful); --tighten RES doubles it.
    relax = {r.strip() for r in args.relax.split(',') if r.strip()}
    tighten = {r.strip() for r in args.tighten.split(',') if r.strip()}
    REV_KEY = {'metals': 'Metals', 'water': 'Water', 'volatiles': 'Volatiles',
               'nobles': 'NobleMetals', 'fissiles': 'Fissiles'}
    stock = fac.get('resources', {})
    rev = fac.get('cachedYearlyRevenue', {})
    weight, cover = {}, {}
    for r in RES:
        inc_d = (rev.get(REV_KEY[r], 0) or 0) / 365.25
        cover[r] = (stock.get(REV_KEY[r], 0) / inc_d) if inc_d > 0 else float('inf')
        c = cover[r]
        w = 4.0 if c < 10 else 2.5 if c < 30 else 1.5 if c < 90 else 0.8 if c < 180 else 0.4
        if r in relax:
            w = 0.1
        if r in tighten:
            w *= 2
        weight[r] = w

    # value of cutting a mine = scarcity-weighted sum of its share of each resource's
    # mining income; flag big suppliers of any non-relaxed resource
    for a in active:
        shares = {r: (a['inc'][r] / tot[r]) if tot[r] else 0.0 for r in RES}
        a['shares'] = shares
        a['cut_cost'] = sum(shares[r] * weight[r] for r in RES)
        a['protected'] = [r for r in RES
                          if r not in relax and shares[r] >= args.protect_share]
    ranked = sorted(active, key=lambda a: (bool(a['protected']), a['cut_cost']))

    usage = fac.get('missionControlUsage')
    overage_hist = fac.get('history_MCCapOverageByDay') or []

    if args.power_on:
        print(f'# Power-ON audit — {args.faction} — {now:%Y-%m-%d}')
        if overage_hist:
            zeros = next((i for i, v in enumerate(overage_hist) if v), len(overage_hist))
            print(f'Over-cap history (newest first): {overage_hist[:10]} — '
                  f'{zeros} consecutive days at zero overage.')
        print('⚠ Confirm actual slack on the in-game top-bar MC tooltip before flipping.\n')
        good = [x for x in unpowered_mc if x[1] in ('OperationsCenter', 'CommandCenter')]
        admins = [x for x in unpowered_mc if x[1] not in ('OperationsCenter', 'CommandCenter')]
        if good:
            print('## Unpowered Ops/Command Centers — flip these FIRST (they ADD headroom)')
            for hn, m, mc, sup in sorted(good, key=lambda x: -x[2]):
                cost = ', '.join(f'{k} {v}' for k, v in (sup or {}).items() if v)
                print(f'  {hn}: {m} → +{mc} MC available; upkeep/mo: {cost or "none"}')
            print('  (Net the upkeep against your scarce resources before flipping.)')
        else:
            print('## No unpowered Ops/Command Centers.')
        if admins:
            mc_sum = sum(x[2] for x in admins)
            print(f'\n## {len(admins)} unpowered Administration modules (+{mc_sum} MC total) '
                  f'— usually load-shed ON PURPOSE, leave OFF')
            print('  Each AdminTower nets +1 MC for −30 money −4 boost/mo — bad value even '
                  'in surplus, and their CP-cap benefit only exists in Earth LEO (see '
                  'LESSONS-economy on the non-LEO Admin trap). Flip only with a specific '
                  'reason, never as bulk MC.')
        if unpowered_mines:
            print(f'\n## Unpowered MINES — each re-enters the quadratic '
                  f'(+{over + 0.5:.1f} MC for the next one)')
            for rec in sorted(unpowered_mines,
                              key=lambda a: -sum(a['inc'].values())):
                incs = ' '.join(f'{r} {v:.0f}' for r, v in rec['inc'].items() if v >= 1)
                print(f"  {rec['hab']} ({rec['body']}) {rec['module']}: {incs}/mo")
            print('  Sequence: MC producers first, then re-check the top bar, then the '
                  'highest-income mine that fits the remaining slack.')
        else:
            print('\n## No unpowered mines — every completed mine is running.')
        if pending_mc:
            total_mc = sum(mc for *_, mc, _ in pending_mc)
            nxt = min((e for e, *_ in pending_mc if e), default=None)
            print(f'\nIncoming MC pipeline: +{total_mc} under construction'
                  + (f', next completion {nxt:%Y-%m-%d}' if nxt else '') + '.')
        return

    if args.json:
        print(json.dumps({'now': now.isoformat(), 'active_mines': n,
                          'network_mc': over ** 2 / 2, 'marginal_mc': marginal,
                          'missionControlUsage': usage,
                          'overage_history_newest_first': overage_hist,
                          'total_income': dict(tot),
                          'ranked': [{k: v for k, v in a.items() if k != 'shares'} |
                                     {'shares': {r: round(s, 3) for r, s in a['shares'].items()}}
                                     for a in ranked[:args.top]],
                          'pending_mc_modules': [
                              {'eta': e.isoformat() if e else None, 'hab': h,
                               'module': m, 'mc': mc, 'prior': p}
                              for e, h, m, mc, p in sorted(pending_mc,
                                                           key=lambda x: x[0] or datetime.max)]},
                         indent=2))
        return

    print(f'# Mine shutdown advisor — {args.faction} — {now:%Y-%m-%d}')
    print(f'Active mines: {n} ({FREE_MINES} free) → network MC = {over**2/2:.0f}; '
          f'each shutdown saves ≈{marginal:.1f} MC (next one {max(0,over-1.5):.1f}, ...)')
    print(f'`missionControlUsage` (exact used): {usage}')
    if overage_hist:
        print(f'Over-cap history (newest first, /day): {overage_hist[:10]} — '
              f'current ≈{overage_hist[0]}. ⚠ Staying over cap DESTROYS modules (1.0.38+).')
    print('⚠ For the exact over/under number, read the in-game top-bar MC tooltip '
          '(reconstructed slack is unreliable — lesson 71).')
    print('Scarcity weights (stockpile cover, directional — lesson 69'
          + (f'; relaxed: {",".join(sorted(relax))}' if relax else '') + '): '
          + '  '.join(f'{r} {weight[r]:.1f} ({"∞" if cover[r]==float("inf") else f"{cover[r]:.0f}d"})'
                      for r in RES) + '\n')

    need = args.need_mc if args.need_mc is not None else (
        overage_hist[0] if overage_hist else None)
    max_recoverable = over * over / 2  # the E29 ceiling: (active − free)²/2
    if need and need > max_recoverable:
        print(f'\n⚠⚠ MINES ALONE CANNOT CLOSE THIS GAP (LESSONS-economy E29): the whole '
              f'mining network only costs {max_recoverable:.1f} MC — turning off EVERY '
              f'chargeable mine still leaves you {need - max_recoverable:.0f} MC over.')
        print('   Pair the list below with instant hab-side levers: power ON any unpowered '
              'Operations/Command Centers (--power-on lists them), and power OFF '
              'ResearchCampuses (+1 MC each, costs 60 research/mo — usually your '
              'least-scarce asset). Then let pending +MC modules land.\n')
    print(f'## Shutdown ranking (cut cheapest first'
          + (f'; target {need:.0f} MC)' if need else ')'))
    hdr = (f"{'#':>2} {'Base':26} {'Body':12} {'Met/mo':>7} {'Wat/mo':>7} {'Vol/mo':>7} "
           f"{'Fis/mo':>7} {'ΣMC saved':>9}  flags")
    print(hdr)
    print('-' * len(hdr))
    saved = 0.0
    m = over
    for i, a in enumerate(ranked[:args.top], 1):
        saved += (m - 0.5) if m > 0 else 0
        m -= 1
        prot = ('🔒 ' + ','.join(f'{r} {a["shares"][r]*100:.0f}%'
                                 for r in a['protected'])) if a['protected'] else ''
        mark = ' ← enough' if need and saved >= need and saved - (m + 0.5) < need else ''
        print(f"{i:>2} {a['hab'][:26]:26} {a['body'][:12]:12} "
              f"{a['inc']['metals']:7.0f} {a['inc']['water']:7.0f} "
              f"{a['inc']['volatiles']:7.0f} {a['inc']['fissiles']:7.1f} "
              f"{saved:9.1f}  {prot}{mark}")
    print('\n🔒 = supplies ≥{:.0f}% of a resource\'s total mining income — cut LAST '
          '(the score-based list misses this: e.g. a low-score mine carrying 21% of fissiles).'
          .format(args.protect_share * 100))
    print(f"Faction mining totals /mo: " +
          ' '.join(f'{r} {tot[r]:.0f}' for r in RES))

    if pending_mc:
        print('\n## Incoming MC production (overage may self-resolve — lesson 36)')
        cum = 0
        for e, h, mname, mc, prior in sorted(pending_mc, key=lambda x: x[0] or datetime.max)[:12]:
            cum += mc
            days = f'{(e - now).days:+4d}d' if e else '   ?'
            note = ' (prior module OFFLINE while building)' if prior else ''
            print(f'  {e:%Y-%m-%d} ({days}) {h}: {mname} +{mc} MC (cum +{cum}){note}')
        total_mc = sum(mc for *_, mc, _ in pending_mc)
        print(f'  … total pending MC production: +{total_mc}')
        print('  If enough lands within ~2 weeks, ONE band-aid shutdown suffices; '
              'power it back on after.')


if __name__ == '__main__':
    main()
