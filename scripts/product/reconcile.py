"""One-time Job03 reconciliation of the explicitly authorized duplicate repository."""
import json,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from product.github import api,pages,credential,FULL
OLD='13shreyansh/nordbank-payments'
keep=pages('/repos/'+FULL+'/pulls?state=open')
assert len(keep)==21 and all(p['head']['ref'].startswith('agent/kassa-') for p in keep)
rows=pages('/repos/'+OLD+'/pulls?state=open');receipts=[]
for p in rows:
 assert p['head']['ref'].startswith(('agent/kassa-','agents/kassa-'))
 def write(path,method,data):
  req=urllib.request.Request('https://api.github.com/repos/'+OLD+path,method=method,data=json.dumps(data).encode(),headers={'Authorization':'Bearer '+credential(),'User-Agent':'Tieto-reconciliation','Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
 comment=write('/issues/'+str(p['number'])+'/comments','POST',{'body':'Closing this duplicate workspace PR. The maintained Nordbank payments review workspace is https://github.com/'+FULL+'. The corresponding agent change and its test evidence are retained there.\n\n<!-- tieto:job03-reconciled -->'})
 closed=write('/pulls/'+str(p['number']),'PATCH',{'state':'closed'})
 receipts.append({'pr':p['html_url'],'comment':comment['html_url'],'state':closed['state']})
print(json.dumps({'keptRepo':FULL,'keptNumbers':[p['number'] for p in keep],'closedRepo':OLD,'closed':receipts,'measured':True}))
(ROOT/'evidence/reconciliation-job03.json').write_text(json.dumps({'keptRepo':FULL,'keptNumbers':[p['number'] for p in keep],'closedRepo':OLD,'closed':receipts,'measured':True},indent=2)+'\n')
