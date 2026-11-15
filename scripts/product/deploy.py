"""Deploy only the current product assets, using existing Vercel auth in memory."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import time
import subprocess
import urllib.request
ROOT=Path(__file__).resolve().parents[2];APP=ROOT/'app'
TEAM='team_SjINqXczvI3i0JpBv7JRMqQN'
TOKEN=json.loads((Path.home()/'Library/Application Support/com.vercel.cli/auth.json').read_text())['token']

def api(path,body=None,raw=None,headers=None):
 url='https://api.vercel.com'+path+('&' if '?' in path else '?')+'teamId='+TEAM
 req=urllib.request.Request(url,data=raw if raw is not None else json.dumps(body).encode() if body is not None else None,headers={'Authorization':'Bearer '+TOKEN,'Content-Type':'application/json',**(headers or {})})
 with urllib.request.urlopen(req,timeout=60) as response:return json.load(response)

def upload(p):
 raw=p.read_bytes();sha=hashlib.sha1(raw).hexdigest();api('/v2/files',raw=raw,headers={'Content-Type':'application/octet-stream','x-vercel-digest':sha,'Content-Length':str(len(raw))});return {'file':'app/'+str(p.relative_to(APP)),'sha':sha,'size':len(raw)}

if __name__=='__main__':
 origin=__import__('sys').argv[1]
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 dirty=subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip()
 if dirty:raise RuntimeError('Commit tracked source before production deployment')
 if not origin.startswith('https://') or not origin.endswith('.trycloudflare.com'):raise ValueError('Expected the current worker tunnel origin')
 api('/v10/projects/pr-trailer/env?upsert=true',{'key':'RUNNER_ORIGIN','value':origin,'type':'plain','target':['production']})
 top={'index.html','workspace.html','landing.css','snapshot.json','app.js','review.js','style.css','vercel.json','api/bridge.js'}
 paths=[p for p in APP.rglob('*') if p.is_file() and (str(p.relative_to(APP)) in top or p.relative_to(APP).parts[0] in ('fonts','evidence','patches','samples'))]
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:files=list(pool.map(upload,paths))
 version=json.dumps({'commit':commit,'repository':'https://github.com/13shreyansh/pr-trailer','measured':True})
 files.append({'file':'app/build.json','data':version})
 deployment=api('/v13/deployments',{'meta':{'sourceCommit':commit},'gitMetadata':{'commitSha':commit,'commitRef':'main','remoteUrl':'https://github.com/13shreyansh/pr-trailer','dirty':False},'name':'pr-trailer','project':'prj_TqJO4nTjZj4gODIgOManda1qm5yH','target':'production','files':files,'projectSettings':{'framework':None,'rootDirectory':'app','buildCommand':None,'installCommand':None,'outputDirectory':None}})
 record={'commit':commit,'id':deployment['id'],'url':'https://pr-trailer.vercel.app','deploymentUrl':'https://'+deployment['url'],'files':[{k:f[k] for k in ('file','sha','size') if k in f} for f in files]};(ROOT/'evidence/product-deployment.json').write_text(json.dumps(record,indent=2));print('Deployment created:',record['id'],flush=True)
 for attempt in range(90):
  status=api('/v13/deployments/'+record['id'])
  if status['readyState'] in ('READY','ERROR','CANCELED'):
   print('Deployment:',status['readyState'],status.get('errorMessage',''),flush=True)
   if status['readyState']!='READY':raise SystemExit(1)
   break
  time.sleep(2)
