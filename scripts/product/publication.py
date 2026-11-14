"""Freeze committed public assets for a versioned project-routing publication."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
if subprocess.check_output(['git','status','--porcelain','--untracked-files=no','--','app','product'],cwd=ROOT,text=True).strip():raise RuntimeError('Commit public assets and worker before publishing')
folder=ROOT/'var/publications'/commit;folder.mkdir(parents=True,exist_ok=True)
files={name:subprocess.check_output(['git','show',commit+':app/'+name],cwd=ROOT) for name in ['index.html','app.js','review.js','style.css']}
(folder/'style.css').write_bytes(files['style.css'])
record={'commit':commit,'repository':'https://github.com/13shreyansh/pr-trailer','publication':'Vercel project routing with immutable worker assets','routingManaged':False,'vercelBaseCommit':'7ad09d9','hashes':{name:hashlib.sha256(raw).hexdigest() for name,raw in files.items()},'measured':True}
(folder/'build.json').write_text(json.dumps(record,indent=2)+'\n')
(ROOT/'var/current-publication.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
