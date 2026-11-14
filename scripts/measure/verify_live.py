"""Exercise production APIs and compare exact measured artifacts. Not visual browser QA."""
import concurrent.futures
import json
from pathlib import Path
import time
import urllib.request
ROOT=Path(__file__).resolve().parents[2]
manifest=json.loads((ROOT/'app/evidence/manifest.json').read_text())
URL='https://pr-trailer.vercel.app'

def post(path,payload):
 req=urllib.request.Request(URL+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=330) as response:return json.load(response)

def check(p):
 start=time.monotonic();r=post('/api/trim',{'id':p['id']})
 for key in ('id','written','kept','tests','passed'):assert r[key]==p[key],(p['id'],key,r.get(key),p.get(key))
 if p['status']=='intern':
  assert len(r['checks'])==3 and all(c['exitCode']==1 and c['tests']==1 and c['passed']==0 for c in r['checks'])
 else:
  assert r['patchSha256']==p['patchSha256']
  assert r['controls'] and all(c['exitCode']!=0 for c in r['controls'])
  assert next(x for x in r['runs'] if x['label']=='trimmed')['exitCode']==0
  if p.get('heldOut'):assert r['heldOut']['exitCode']==1 and r['heldOut']['passed']==0
 result={'id':p['id'],'written':r['written'],'kept':r['kept'],'passed':r['passed'],'tests':r['tests'],'patchSha256':r.get('patchSha256'),'failingControls':len(r.get('controls',[])),'seconds':round(time.monotonic()-start,3),'measured':True}
 print(json.dumps(result),flush=True);return result

if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(check,manifest['prs']))
 ids=[p['id'] for p in manifest['prs'] if p['status']=='proven'];branch=post('/api/finish',{'ids':ids})
 assert branch['ids']==ids and branch['passed']==branch['tests'] and branch['branch']=='tieto/approved'
 import base64,io,zipfile,subprocess,tempfile
 with tempfile.TemporaryDirectory(dir=ROOT/'evidence/work') as tmp:
  work=Path(tmp)
  with zipfile.ZipFile(io.BytesIO(base64.b64decode(branch['zipBase64']))) as archive:archive.extractall(work)
  repo=work/'kassa';head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip();assert head==branch['commit']
  assert subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True)==''
 result={'url':URL,'trimResults':results,'branch':{k:branch[k] for k in ('ids','branch','commit','tests','passed','measured')},'visualBrowserVerified':False}
 (ROOT/'evidence/live-verification.json').write_text(json.dumps(result,indent=2));print('LIVE API PASS',len(results),'samples; signed branch',branch['passed'],'/',branch['tests'],flush=True)
