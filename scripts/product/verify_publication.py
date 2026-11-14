"""Verify the public served snapshot against committed source bytes, not just its label."""
import hashlib,json,subprocess,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];base='https://pr-trailer.vercel.app'
with urllib.request.urlopen(base+'/build.json',timeout=20) as r:record=json.load(r)
expected=sys.argv[1] if len(sys.argv)>1 else subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert record['commit']==expected,(record['commit'],expected)
checks={}
for name,digest in record['hashes'].items():
 with urllib.request.urlopen(base+'/'+('' if name=='index.html' else name),timeout=20) as r:raw=r.read();mime=r.headers.get('Content-Type')
 committed=subprocess.check_output(['git','show',expected+':app/'+name],cwd=ROOT)
 assert hashlib.sha256(raw).hexdigest()==digest==hashlib.sha256(committed).hexdigest(),name
 if name=='style.css':assert mime.startswith('text/css'),mime
 checks[name]={'sha256':digest,'matchesCommittedSource':True,'contentType':mime}
origin=(ROOT/'var/runner-origin.txt').read_text().strip()
with urllib.request.urlopen(origin+'/health',timeout=20) as r:health=json.load(r)
assert health['commit']==expected
result={'commit':expected,'vercelBaseCommit':record['vercelBaseCommit'],'publication':record['publication'],'files':checks,'backendLoadedCommit':health['commit'],'measured':True}
(ROOT/'evidence/commit-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
