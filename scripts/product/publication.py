"""Freeze committed public assets for a versioned project-routing publication."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
if subprocess.check_output(['git','status','--porcelain','--untracked-files=no','--','app','product'],cwd=ROOT,text=True).strip():raise RuntimeError('Commit public assets and worker before publishing')
folder=ROOT/'var/publications'/commit;folder.mkdir(parents=True,exist_ok=True)
files={name:subprocess.check_output(['git','show',commit+':app/'+name],cwd=ROOT) for name in ['index.html','workspace.html','landing.css','snapshot.json','app.js','review.js','style.css']}
(folder/'style.css').write_bytes(files['style.css'])
record={'commit':commit,'repository':'https://github.com/13shreyansh/pr-trailer','publication':'Vercel deployment for static files; project routing forwards /api to the worker','routingManaged':json.loads((ROOT/'var/current-publication.json').read_text()).get('routingManaged',False) if (ROOT/'var/current-publication.json').exists() else False,'hashes':{name:hashlib.sha256(raw).hexdigest() for name,raw in files.items()},'measured':True}
(folder/'build.json').write_text(json.dumps(record,indent=2)+'\n')
(ROOT/'var/current-publication.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
