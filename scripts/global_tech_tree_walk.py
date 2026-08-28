#!/usr/bin/env python3
"""Walk the global-tech tree from a save: what can be queued next, and what each
candidate unlocks 2-3 levels deep (child projects + child/grandchild globals).

Usage:
    python3 global_tech_tree_walk.py <save.json> [--assume TechA,TechB,...] [--faction <templateName>]

--assume: treat these techs as already finished (e.g. techs currently in active
slots that will complete before the next pick), so the menu reflects the state
at the moment the slot opens.

Output: markdown per-candidate tree with direct project unlocks (faction-eligible,
not yet finished/missed), child globals (with remaining missing prereqs), and
grandchild globals/projects one more level down.
"""
import json, sys, argparse, gzip
from pathlib import Path

TPL_DIR = Path(__file__).parent / 'templates'

from ti_config import load_save  # THE shared loader: gzip magic + BOM, memoized

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('save')
    ap.add_argument('--assume', default='')
    ap.add_argument('--faction', default=None)
    ap.add_argument('--projects', default='',
                    help="Walk unlocks FROM these projects instead of the global-tech menu. "
                         "Comma-separated dataNames, or 'cat:<Category>' to take every project "
                         "of that category that is available/paused/pending-roll for the faction.")
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    from ti_config import require_faction
    args.faction = require_faction(args.faction)
    say = (lambda *a, **kw: None) if args.json else print

    techs = json.load(open(TPL_DIR / 'TITechTemplate.json'))
    projects = json.load(open(TPL_DIR / 'TIProjectTemplate.json'))
    tech_by_name = {t['dataName']: t for t in techs}

    save = load_save(args.save)
    gs = save['gamestates']
    glob = gs['PavonisInteractive.TerraInvicta.TIGlobalResearchState'][0]['Value']
    finished = set(glob['finishedTechsNames'])
    fac = None
    for f in gs['PavonisInteractive.TerraInvicta.TIFactionState']:
        if f['Value'].get('templateName') == args.faction:
            fac = f['Value']
    fin_proj = set(fac['finishedProjectNames'])
    missed = set(fac.get('missedProjects') or [])
    avail_proj = set(fac.get('availableProjectNames') or [])
    assumed = set(x for x in args.assume.split(',') if x)
    done = finished | assumed | fin_proj  # prereq satisfaction pool

    def proj_eligible(p):
        fp = p.get('factionPrereq') or []
        return (not fp or args.faction in fp) and p['dataName'] not in fin_proj and p['dataName'] not in missed

    def missing(prereqs):
        return [q for q in (prereqs or []) if q not in done]

    if args.projects:
        proj_by_name = {p['dataName']: p for p in projects}
        if args.projects.startswith('cat:'):
            cat = args.projects[4:]
            pending = {p['dataName'] for p in projects
                       if p.get('techCategory') == cat and proj_eligible(p)
                       and not [q for q in (p.get('prereqs') or []) if q not in done and not q.startswith('Project_')]}
            roots = sorted(avail_proj & pending | {p['dataName'] for p in projects
                       if p.get('techCategory') == cat and proj_eligible(p) and not missing(p.get('prereqs'))})
        else:
            roots = [x for x in args.projects.split(',') if x]
        say(f"# Unlock walk from projects: {', '.join(roots)}\n")
        out = {'mode': 'projects', 'roots': []}
        for rn in roots:
            r = proj_by_name.get(rn)
            if not r:
                out['roots'].append({'data_name': rn, 'found': False})
                say(f'## {rn} — NOT FOUND\n'); continue
            state = 'DONE' if rn in fin_proj else ('AVAILABLE' if rn in avail_proj else 'pending-roll/locked')
            node = {'data_name': rn, 'found': True, 'name': r.get('friendlyName', rn),
                    'cost_rp_template': r.get('researchCost', 0), 'state': state,
                    'unlocks_projects': [], 'unlocks_techs': []}
            say(f"## {r.get('friendlyName', rn)} [`{rn}`] — {r.get('researchCost',0):,} RP (template) · {state}")
            hits = False
            for p in projects:
                if rn in (p.get('prereqs') or []) or rn == p.get('altPrereq0'):
                    if not proj_eligible(p): continue
                    hits = True
                    m = [x for x in missing(p.get('prereqs')) if x != rn]
                    tag = f" (also needs: {', '.join(m)})" if m else " ✅ would be unlockable"
                    child = {'data_name': p['dataName'], 'name': p.get('friendlyName', p['dataName']),
                             'cost_rp_template': p.get('researchCost', 0), 'also_needs': m,
                             'projects': []}
                    say(f"  - PROJ {p.get('friendlyName', p['dataName'])} [{p.get('researchCost',0):,}]{tag}")
                    for gp in projects:
                        if p['dataName'] in (gp.get('prereqs') or []) and proj_eligible(gp):
                            m2 = [x for x in missing(gp.get('prereqs')) if x != p['dataName']]
                            child['projects'].append({'data_name': gp['dataName'],
                                                      'name': gp.get('friendlyName', gp['dataName']),
                                                      'cost_rp_template': gp.get('researchCost', 0),
                                                      'also_needs': m2})
                            say(f"      - proj {gp.get('friendlyName', gp['dataName'])} [{gp.get('researchCost',0):,}]" + (f" (also: {', '.join(m2)})" if m2 else ""))
                    node['unlocks_projects'].append(child)
            for t in techs:
                if rn in (t.get('prereqs') or []):
                    hits = True
                    m = [x for x in missing(t.get('prereqs')) if x != rn]
                    node['unlocks_techs'].append({'data_name': t['dataName'],
                                                  'name': t.get('friendlyName', t['dataName']),
                                                  'cost_rp_template': t.get('researchCost', 0),
                                                  'category': t.get('techCategory', '?'),
                                                  'also_needs': m})
                    say(f"  - TECH {t.get('friendlyName', t['dataName'])} [{t.get('researchCost',0):,} {t.get('techCategory','?')}]" + (f" (also needs: {', '.join(m)})" if m else " ✅"))
            if not hits:
                say("  - (nothing in the tree depends on it)")
            say()
            out['roots'].append(node)
        if args.json:
            print(json.dumps(out, indent=2, default=str))
        return

    # candidates: unfinished techs, all prereqs met
    cands = [t for t in techs if t['dataName'] not in finished and t['dataName'] not in assumed
             and not missing(t.get('prereqs'))]
    cands.sort(key=lambda t: t.get('researchCost', 0))

    def children_techs(name):
        return [t for t in techs if name in (t.get('prereqs') or []) and t['dataName'] not in finished and t['dataName'] not in assumed]

    def children_projects(name):
        return [p for p in projects if name in (p.get('prereqs') or []) and proj_eligible(p)]

    say(f"# Global techs queueable after: {', '.join(sorted(assumed)) or '(current state)'}\n")
    out = {'mode': 'candidates', 'assumed': sorted(assumed), 'candidates': []}
    for t in cands:
        n = t['dataName']
        node = {'data_name': n, 'name': t.get('friendlyName', n),
                'cost_rp_template': t.get('researchCost', 0),
                'category': t.get('techCategory', '?'), 'projects': [], 'techs': []}
        say(f"## {t.get('friendlyName', n)}  [`{n}`] — {t.get('researchCost', 0):,} RP (template) · {t.get('techCategory','?')}")
        for p in children_projects(n):
            m = missing(p.get('prereqs'))
            m = [x for x in m if x != n]
            tag = f" (also needs: {', '.join(m)})" if m else " ✅ unlockable"
            star = ' 🔓ALREADY-AVAIL' if p['dataName'] in avail_proj else ''
            node['projects'].append({'data_name': p['dataName'],
                                     'name': p.get('friendlyName', p['dataName']),
                                     'cost_rp_template': p.get('researchCost', 0),
                                     'also_needs': m,
                                     'already_available': p['dataName'] in avail_proj})
            say(f"  - PROJ {p.get('friendlyName', p['dataName'])} [{p.get('researchCost', 0):,}]{tag}{star}")
        for c in children_techs(n):
            m = [x for x in missing(c.get('prereqs')) if x != n]
            tag = f" (also needs: {', '.join(m)})" if m else " ✅ next-menu"
            tnode = {'data_name': c['dataName'], 'name': c.get('friendlyName', c['dataName']),
                     'cost_rp_template': c.get('researchCost', 0),
                     'category': c.get('techCategory', '?'), 'also_needs': m,
                     'projects': [], 'techs': []}
            say(f"  - TECH {c.get('friendlyName', c['dataName'])} [{c.get('researchCost', 0):,} {c.get('techCategory','?')}]{tag}")
            for gp in children_projects(c['dataName']):
                m2 = [x for x in missing(gp.get('prereqs')) if x != c['dataName']]
                tag2 = f" (also: {', '.join(m2)})" if m2 else ""
                tnode['projects'].append({'data_name': gp['dataName'],
                                          'name': gp.get('friendlyName', gp['dataName']),
                                          'cost_rp_template': gp.get('researchCost', 0),
                                          'also_needs': m2})
                say(f"      - proj {gp.get('friendlyName', gp['dataName'])} [{gp.get('researchCost', 0):,}]{tag2}")
            for gc in children_techs(c['dataName']):
                m2 = [x for x in missing(gc.get('prereqs')) if x != c['dataName']]
                tag2 = f" (also: {', '.join(m2)})" if m2 else ""
                tnode['techs'].append({'data_name': gc['dataName'],
                                       'name': gc.get('friendlyName', gc['dataName']),
                                       'cost_rp_template': gc.get('researchCost', 0),
                                       'category': gc.get('techCategory', '?'),
                                       'also_needs': m2})
                say(f"      - tech {gc.get('friendlyName', gc['dataName'])} [{gc.get('researchCost', 0):,} {gc.get('techCategory','?')}]{tag2}")
            node['techs'].append(tnode)
        out['candidates'].append(node)
        say()

    if args.json:
        print(json.dumps(out, indent=2, default=str))

if __name__ == '__main__':
    main()
