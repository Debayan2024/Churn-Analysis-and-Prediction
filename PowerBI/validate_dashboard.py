"""Validate report JSON against Microsoft's schemas and check model references."""
import json, urllib.request, hashlib, warnings
from pathlib import Path
from urllib.parse import urldefrag
import jsonschema
warnings.filterwarnings('ignore', category=DeprecationWarning)
BASE=Path(__file__).resolve().parent
CACHE=BASE/'schemas'/'resolved'
CACHE.mkdir(parents=True,exist_ok=True)
store={}
for p in (BASE/'schemas').glob('*.json'):
    d=json.loads(p.read_text(encoding='utf-8'))
    if isinstance(d,dict) and '$id' in d: store[d['$id']]=d

def fetch(uri):
    uri=urldefrag(uri)[0]
    if uri in store:return store[uri]
    p=CACHE/(hashlib.sha256(uri.encode()).hexdigest()+'.json')
    if p.exists(): data=json.loads(p.read_text(encoding='utf-8'))
    else:
        data=json.load(urllib.request.urlopen(uri,timeout=30))
        p.write_text(json.dumps(data,indent=2),encoding='utf-8')
    store[uri]=data
    return data
files=[BASE/'ChurnDashboard.pbip',BASE/'ChurnDashboard.Report/definition.pbir',BASE/'ChurnDashboard.SemanticModel/definition.pbism']+list((BASE/'ChurnDashboard.Report/definition').rglob('*.json'))
errors=[]
for p in files:
    d=json.loads(p.read_text(encoding='utf-8'))
    sch=fetch(d['$schema'])
    resolver=jsonschema.RefResolver(base_uri=d['$schema'],referrer=sch,store=store,handlers={'https':fetch,'http':fetch})
    v=jsonschema.Draft7Validator(sch,resolver=resolver)
    for error in v.iter_errors(d):errors.append(str(p.relative_to(BASE))+' '+str(list(error.path))+': '+error.message)
model=json.loads((BASE/'ChurnDashboard.SemanticModel/model.bim').read_text())['model']
tables={t['name']:t for t in model['tables']}
fields={name:{c['name'] for c in t['columns']} for name,t in tables.items()}
measures={name:{m['name'] for m in t.get('measures',[])} for name,t in tables.items()}
def checkrefs(node,path):
    if isinstance(node,dict):
        for k,v in node.items():
            if k in ['Column','Measure'] and isinstance(v,dict):
                entity=v.get('Expression',{}).get('SourceRef',{}).get('Entity')
                if entity and v.get('Property') not in (fields if k=='Column' else measures).get(entity,set()):errors.append('Unknown '+k+' '+entity+'.'+str(v.get('Property'))+' in '+path)
            checkrefs(v,path)
    elif isinstance(node,list):
        for v in node:checkrefs(v,path)
for p in files:checkrefs(json.loads(p.read_text()),str(p.relative_to(BASE)))
for p in (BASE/'ChurnDashboard.Report/definition/pages').glob('*/page.json'):
    page=json.loads(p.read_text())
    for vp in (p.parent/'visuals').glob('*/visual.json'):
        v=json.loads(vp.read_text());pos=v['position']
        if pos['x']<0 or pos['y']<0 or pos['x']+pos['width']>page['width'] or pos['y']+pos['height']>page['height']:errors.append('Visual outside page: '+str(vp))
for r in model['relationships']:
    for endpoint in ['from','to']:
        assert r[endpoint+'Column'] in fields[r[endpoint+'Table']]
summary={'schema_files_validated':len(files),'schema_errors':errors,'model_tables':list(tables),'relationships':len(model['relationships']),'report_field_references_valid':not errors,'desktop_runtime_validation':json.loads((BASE/'desktop_validation.json').read_text()) if (BASE/'desktop_validation.json').exists() else 'Not performed'}
(BASE/'report_validation.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
raise SystemExit(bool(errors))
