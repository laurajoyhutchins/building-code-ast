#!/usr/bin/env python3
"""Validate and regenerate the repository-local Deciduous archaeology package."""
from __future__ import annotations
import argparse, collections, json, re, subprocess, sys, uuid
from pathlib import Path
if __package__:
    from .archaeology_graph import BASE_COMMIT,ROOT,canonical_json,load_patch_set,rendered_artifacts,semantic_projection
else:
    from archaeology_graph import BASE_COMMIT,ROOT,canonical_json,load_patch_set,rendered_artifacts,semantic_projection
NAMESPACE=uuid.UUID('1aec22c8-1541-49fb-a6c1-41e7d1228f91')
NODE_TYPES={'goal','decision','option','action','outcome','observation','revisit'}
EDGE_TYPES={'leads_to','requires','chosen','rejected','blocks','enables'}
CORE={'pending','active','completed','rejected'}
LIFE={'active','completed','proposed','experimental','unresolved','edition-specific','compatibility-only','superseded','rejected','abandoned','branch-only','historical-only'}
REQUIRED_ARCS={'concept','schema','pdf-layout','nec-ingestion','nec-hierarchy','clause-semantics','nec-edition-comparison','ibc','parser-families','nfpa13','ul-related-sources','provenance','validation','downstream','governance-current'}
REQUIRED_SEMANTIC={'decision.compiler-not-search','decision.document-ast-separate','decision.nec-specific-grammar','decision.nec-oracle-reference-only','decision.nec-style-manual-prior','decision.issued-edition-controls','decision.ibc-specific-hierarchy','decision.family-grammar-boundary','decision.ul-external-ownership','decision.source-register-rights','decision.claims-follow-tree-and-tests','decision.map-owns-jurisdiction','decision.use-lore-shipped-skill','obs.current-main-support','obs.branch-bound-support'}
BRANCH_ONLY_PRS={12,15,17,18,19,20}
ALLOWED_REPOS={'laurajoyhutchins/building-code-ast','laurajoyhutchins/building-code-map','laurajoyhutchins/electrical-equipment-lineage','laurajoyhutchins/LORE','laurajoyhutchins/obsidian-pdf-extractor','laurajoyhutchins/junk-drawer','laurajoyhutchins/engineering-agent-team','notactuallytreyanastasio/deciduous'}
ARCH_PATHS={'ARCHAEOLOGY.md','docs/archaeology/README.md','docs/archaeology/current-architecture.md','docs/archaeology/parser-family-evolution.md','docs/archaeology/source-provenance.md','docs/archaeology/validation-strategy.md','docs/archaeology/downstream-boundaries.md','docs/archaeology/evidence-gaps.md','docs/archaeology/maintenance.md','docs/archaeology/narratives.md','docs/archaeology/self-review.md','docs/archaeology/evidence-register.json','docs/archaeology/current-architecture.json','docs/archaeology/status-summary.json','docs/archaeology/manifest.json','docs/archaeology/graph.dot','.deciduous/exports/building-code-ast-archaeology.json','scripts/archaeology_graph.py','scripts/validate_archaeology.py','tests/test_archaeology.py','.github/workflows/archaeology.yml'}

def dag(nodes,edges,errors):
    adj=collections.defaultdict(list); indeg={s:0 for s in nodes}
    for e in edges:
        if e['from'] not in nodes or e['to'] not in nodes: errors.append(f"missing edge endpoint: {e['from']} -> {e['to']}");continue
        adj[e['from']].append(e['to']);indeg[e['to']]+=1
    q=collections.deque(sorted(s for s,d in indeg.items() if d==0));seen=0
    while q:
        s=q.popleft();seen+=1
        for t in adj[s]:
            indeg[t]-=1
            if indeg[t]==0:q.append(t)
    if seen!=len(nodes): errors.append('graph is cyclic')

def verify_changed_paths(fragments,errors):
    try:
        subprocess.run(['git','cat-file','-e',f'{BASE_COMMIT}^{{commit}}'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        r=subprocess.run(['git','diff','--name-only',f'{BASE_COMMIT}...HEAD'],cwd=ROOT,check=True,text=True,capture_output=True)
    except (FileNotFoundError,subprocess.CalledProcessError): return
    allowed=ARCH_PATHS|{'README.md'}|{p.relative_to(ROOT).as_posix() for p,_ in fragments}
    changed={x for x in r.stdout.splitlines() if x}
    if extra:=sorted(changed-allowed): errors.append(f'non-archaeology paths changed: {extra}')
    forbidden=('src/','schemas/','fixtures/','scripts/ingest_','scripts/build_nec','scripts/check_nec')
    for p in changed:
        if p.startswith(forbidden) and p not in {'scripts/archaeology_graph.py','scripts/validate_archaeology.py'}: errors.append(f'parser/schema/dataset path changed: {p}')

def validate(write=False):
    errors=[]
    try: fragments,patch=load_patch_set()
    except Exception as exc: return [str(exc)],{'nodes':0,'edges':0,'patches':0,'patch_set_sha256':''}
    register=json.loads((ROOT/'docs/archaeology/evidence-register.json').read_text())
    declared=set(); first=fragments[0][1]
    expected={'version':'1.0','author':first.get('author'),'branch':'agent/deciduous-archaeology-backfill','created_at':first.get('created_at'),'base_commit':BASE_COMMIT}
    for p,f in fragments:
        for k,v in expected.items():
            if f.get(k)!=v: errors.append(f'{p.name}: inconsistent {k}')
        if p.read_text()!=canonical_json(f)+'\n': errors.append(f'{p.name}: patch is not canonical JSON')
        current={n.get('change_id') for n in f.get('nodes',[])}; available=declared|current
        for e in f.get('edges',[]):
            if e.get('from_change_id') not in available: errors.append(f'{p.name}: edge source not declared')
            if e.get('to_change_id') not in current: errors.append(f'{p.name}: edge target not in same patch')
        declared|=current
    ids=set(); sids=set(); arcs=set(); idnode={}; semantic={}
    for n in patch['nodes']:
        cid=n.get('change_id')
        if cid in ids: errors.append(f'duplicate change_id {cid}')
        ids.add(cid)
        try: uuid.UUID(cid)
        except Exception: errors.append(f'invalid UUID {cid}')
        if n.get('node_type') not in NODE_TYPES: errors.append(f'invalid node type {cid}')
        if n.get('status') not in CORE: errors.append(f'invalid status {cid}')
        try:m=json.loads(n['metadata_json'])
        except Exception as exc: errors.append(f'invalid metadata {cid}: {exc}');continue
        sid=m.get('semantic_id')
        if not sid or sid in sids: errors.append(f'missing/duplicate semantic_id {sid}');continue
        sids.add(sid)
        if str(uuid.uuid5(NAMESPACE,sid))!=cid: errors.append(f'non-deterministic change_id for {sid}')
        if m.get('arc') not in REQUIRED_ARCS: errors.append(f'invalid arc for {sid}: {m.get("arc")}')
        arcs.add(m.get('arc'))
        if m.get('lifecycle_status') not in LIFE: errors.append(f'invalid lifecycle for {sid}')
        if not isinstance(m.get('current_architecture'),bool): errors.append(f'missing current marker for {sid}')
        if not m.get('repository_owner') in ALLOWED_REPOS: errors.append(f'unknown repository owner for {sid}')
        if not m.get('evidence'): errors.append(f'missing evidence for {sid}')
        for ev in m.get('evidence',[]):
            repo=ev.get('repo')
            if repo and repo not in ALLOWED_REPOS: errors.append(f'unknown evidence repo for {sid}: {repo}')
            if ev.get('commit') and not re.fullmatch(r'[0-9a-f]{40}',ev['commit']): errors.append(f'invalid commit for {sid}')
            if ev.get('pr'):
                record=register['pull_requests'].get(str(ev['pr']))
                if not record: errors.append(f'unregistered PR for {sid}: {ev["pr"]}')
                elif record['head_sha']!=ev.get('commit') or record['state']!=ev.get('state'): errors.append(f'PR evidence mismatch for {sid}: {ev["pr"]}')
            if ev.get('kind')=='path' and ev.get('repo')=='laurajoyhutchins/building-code-ast' and ev.get('ref')=='main':
                p=ROOT/ev['path']
                if not p.exists(): errors.append(f'missing current path for {sid}: {ev["path"]}')
        if m.get('current_architecture') and m.get('lifecycle_status') in {'rejected','superseded','abandoned','branch-only'}: errors.append(f'invalid current lifecycle for {sid}')
        if sid in {'outcome.ibc-not-current-main','outcome.nfpa13-draft-not-main','outcome.nec2020-changelog-not-main'} and m.get('lifecycle_status')!='branch-only': errors.append(f'branch support upgraded incorrectly: {sid}')
        idnode[cid]=n; semantic[sid]=m
    if missing:=sorted(REQUIRED_ARCS-arcs): errors.append(f'missing arcs: {missing}')
    if missing:=sorted(REQUIRED_SEMANTIC-sids): errors.append(f'missing required decisions: {missing}')
    seen=set(); semedges=[]
    for e in patch['edges']:
        a,b=e.get('from_change_id'),e.get('to_change_id')
        if a not in idnode or b not in idnode: errors.append('edge references unknown node');continue
        if e.get('edge_type') not in EDGE_TYPES: errors.append(f'invalid edge type {e.get("edge_type")}')
        key=(a,b,e.get('edge_type'))
        if key in seen: errors.append(f'duplicate edge {key}')
        seen.add(key)
        semedges.append({'from':json.loads(idnode[a]['metadata_json'])['semantic_id'],'to':json.loads(idnode[b]['metadata_json'])['semantic_id'],'edge_type':e['edge_type']})
    dag(semantic,semedges,errors)
    text='\n'.join(n['title']+'\n'+n['description']+'\n'+n['metadata_json'] for n in patch['nodes'])
    for phrase in ('authoritative source text','derived','printed hierarchy','semantic','runtime dependency','complete-edition','uncertainty'):
        if phrase not in text: errors.append(f'missing required distinction phrase: {phrase}')
    for forbidden in ('drive.google.com','sk-proj-','OPENAI_API_KEY=','BEGIN PRIVATE'):
        if forbidden in text: errors.append(f'forbidden private material: {forbidden}')
    artifacts,digest=rendered_artifacts(fragments,patch)
    if write:
        for p,c in artifacts.items(): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(c,encoding='utf-8')
    else:
        for p,c in artifacts.items():
            if not p.exists(): errors.append(f'missing projection {p.relative_to(ROOT)}')
            elif p.read_text()!=c: errors.append(f'stale projection {p.relative_to(ROOT)}')
    graph=semantic_projection(patch)
    return errors,{'nodes':len(graph['nodes']),'edges':len(graph['edges']),'patches':len(fragments),'patch_set_sha256':digest}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');args=ap.parse_args()
    errors,s=validate(args.write)
    if errors:
        for e in errors: print('ERROR:',e,file=sys.stderr)
        return 1
    print(f"archaeology validation PASS: {s['nodes']} nodes, {s['edges']} edges, {s['patches']} patches, patch-set sha256 {s['patch_set_sha256']}")
    return 0
if __name__=='__main__': raise SystemExit(main())
