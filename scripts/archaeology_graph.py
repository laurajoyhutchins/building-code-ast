"""Deterministic helpers for the Building Code AST Deciduous archaeology graph."""
from __future__ import annotations
import collections, hashlib, json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
PATCH_DIR=ROOT/'.deciduous/patches'
PATCH_GLOB='building-code-ast-archaeology-*.json'
EXPORT=ROOT/'.deciduous/exports/building-code-ast-archaeology.json'
DOT=ROOT/'docs/archaeology/graph.dot'
CURRENT=ROOT/'docs/archaeology/current-architecture.json'
STATUS=ROOT/'docs/archaeology/status-summary.json'
MANIFEST=ROOT/'docs/archaeology/manifest.json'
BASE_COMMIT='e0e3aef4320ec20ce8508378f611f43336b24e4d'
UPSTREAM='notactuallytreyanastasio/deciduous@1bb5a1595011943973716f316d65cd03944feadd'

def canonical_json(value:Any)->str:
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)

def load_patch_set():
    paths=sorted(PATCH_DIR.glob(PATCH_GLOB))
    if not paths: raise FileNotFoundError(f'no Deciduous patches match {PATCH_DIR/PATCH_GLOB}')
    fragments=[(p,json.loads(p.read_text(encoding='utf-8'))) for p in paths]
    first=fragments[0][1]
    merged={k:first.get(k) for k in ('version','author','branch','created_at','base_commit')}
    merged['nodes']=[]; merged['edges']=[]
    for _,f in fragments:
        merged['nodes'].extend(f.get('nodes',[])); merged['edges'].extend(f.get('edges',[]))
    return fragments,merged

def semantic_projection(patch):
    by_change={}; nodes=[]
    for node in patch['nodes']:
        m=json.loads(node['metadata_json']); sid=m['semantic_id']; by_change[node['change_id']]=sid
        nodes.append({'semantic_id':sid,'change_id':node['change_id'],'node_type':node['node_type'],'title':node['title'],'description':node['description'],'status':node['status'],**{k:v for k,v in m.items() if k!='semantic_id'}})
    edges=[{'from':by_change[e['from_change_id']],'to':by_change[e['to_change_id']],'edge_type':e['edge_type'],'rationale':e.get('rationale','')} for e in patch['edges']]
    return {'nodes':nodes,'edges':edges}

def graph_data_export(patch):
    ids={n['change_id']:i for i,n in enumerate(patch['nodes'],1)}
    nodes=[]
    for i,n in enumerate(patch['nodes'],1):
        date=json.loads(n['metadata_json']).get('date','2026-08-03')+'T00:00:00Z'
        nodes.append({'id':i,'change_id':n['change_id'],'node_type':n['node_type'],'title':n['title'],'description':n['description'],'status':n['status'],'created_at':date,'updated_at':date,'metadata_json':n['metadata_json']})
    edges=[]
    for i,e in enumerate(patch['edges'],1):
        edges.append({'id':i,'from_node_id':ids[e['from_change_id']],'to_node_id':ids[e['to_change_id']],'from_change_id':e['from_change_id'],'to_change_id':e['to_change_id'],'edge_type':e['edge_type'],'weight':1.0,'rationale':e.get('rationale',''),'created_at':'2026-08-03T14:30:00Z'})
    return {'nodes':nodes,'edges':edges}

def patch_set_digest(fragments):
    h=hashlib.sha256()
    for p,f in fragments:
        h.update(p.relative_to(ROOT).as_posix().encode());h.update(b'\0');h.update((canonical_json(f)+'\n').encode());h.update(b'\0')
    return h.hexdigest()

def dot_projection(graph):
    nodes=sorted(graph['nodes'],key=lambda n:n['semantic_id']); aliases={n['semantic_id']:f'n{i:03d}' for i,n in enumerate(nodes)}
    lines=['digraph building_code_ast_archaeology {','  graph [rankdir="LR", splines=true, overlap=false];','  node [shape="box", fontname="Helvetica", fontsize=9];','  edge [fontname="Helvetica", fontsize=8];']
    for n in nodes:
        label=f"{n['semantic_id']}\\n{n['node_type']} · {n['lifecycle_status']}".replace('"','\\"')
        attrs=[f'label="{label}"']
        if n.get('current_architecture'): attrs.append('peripheries=2')
        if n['lifecycle_status'] in {'proposed','branch-only','experimental','unresolved'}: attrs.append('style="dashed"')
        elif n['lifecycle_status'] in {'superseded','rejected','abandoned'}: attrs.append('style="dotted"')
        lines.append(f"  {aliases[n['semantic_id']]} [{', '.join(attrs)}];")
    for e in sorted(graph['edges'],key=lambda e:(e['from'],e['to'],e['edge_type'])):
        lines.append(f"  {aliases[e['from']]} -> {aliases[e['to']]} [label=\"{e['edge_type']}\"];")
    lines.append('}')
    return '\n'.join(lines)+'\n'

def current_projection(graph):
    current={n['semantic_id']:{k:n[k] for k in ('semantic_id','node_type','title','arc','lifecycle_status','repository_owner','support_scope','source_state','confidence')} for n in graph['nodes'] if n.get('current_architecture')}
    edges=[e for e in graph['edges'] if e['from'] in current and e['to'] in current]
    return {'schema':'building-code-ast-current-architecture-v1','base_commit':BASE_COMMIT,'nodes':[current[s] for s in sorted(current)],'edges':sorted(edges,key=lambda e:(e['from'],e['to'],e['edge_type']))}

def rendered_artifacts(fragments,patch):
    graph=semantic_projection(patch); export=graph_data_export(patch); digest=patch_set_digest(fragments)
    export_text=json.dumps(export,indent=2,sort_keys=True,ensure_ascii=False)+'\n'
    dot=dot_projection(graph)
    current_text=json.dumps(current_projection(graph),indent=2,sort_keys=True,ensure_ascii=False)+'\n'
    status={'schema':'building-code-ast-archaeology-status-v1','base_commit':BASE_COMMIT,'patch_set_sha256':digest,'patch_count':len(fragments),'node_count':len(graph['nodes']),'edge_count':len(graph['edges']),'current_architecture_count':sum(bool(n.get('current_architecture')) for n in graph['nodes']),'by_arc':dict(sorted(collections.Counter(n['arc'] for n in graph['nodes']).items())),'by_lifecycle_status':dict(sorted(collections.Counter(n['lifecycle_status'] for n in graph['nodes']).items())),'by_support_scope':dict(sorted(collections.Counter(n['support_scope'] for n in graph['nodes']).items()))}
    status_text=json.dumps(status,indent=2,sort_keys=True)+'\n'
    hashes={p.relative_to(ROOT).as_posix():hashlib.sha256((canonical_json(f)+'\n').encode()).hexdigest() for p,f in fragments}
    manifest={'schema':'building-code-ast-archaeology-manifest-v1','base_commit':BASE_COMMIT,'deciduous_upstream':UPSTREAM,'canonical_source':{'format':'ordered-deciduous-patch-set-v1','apply_in_lexicographic_order':list(hashes),'patch_set_sha256':digest},'node_count':len(graph['nodes']),'edge_count':len(graph['edges']),'generated_at':patch['created_at'],'sha256':{**hashes,'.deciduous/exports/building-code-ast-archaeology.json':hashlib.sha256(export_text.encode()).hexdigest(),'docs/archaeology/graph.dot':hashlib.sha256(dot.encode()).hexdigest(),'docs/archaeology/current-architecture.json':hashlib.sha256(current_text.encode()).hexdigest(),'docs/archaeology/status-summary.json':hashlib.sha256(status_text.encode()).hexdigest()}}
    return {EXPORT:export_text,DOT:dot,CURRENT:current_text,STATUS:status_text,MANIFEST:json.dumps(manifest,indent=2,sort_keys=True)+'\n'},digest
