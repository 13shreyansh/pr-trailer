import pathlib,json,hashlib,base64,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
root=ROOT/'app'
top={'index.html','style.css','app.js','review.js','vercel.json','requirements.txt','.python-version'}
def allowed(p):
 rel=p.relative_to(root)
 return p.is_file() and '__pycache__' not in p.parts and (str(rel) in top or rel.parts[0] in ('fonts','evidence','patches','runtime') or str(rel) in ('api/trim.py','api/finish.py','api/workspace.py'))
if len(sys.argv)==1:
 files=[]
 for p in sorted(root.rglob('*')):
  if allowed(p):
   data=p.read_bytes();files.append({'file':'app/'+str(p.relative_to(root)),'sha':hashlib.sha1(data).hexdigest(),'size':len(data),'encoded':4*((len(data)+2)//3)})
 print(json.dumps(files))
else:
 p=(ROOT/sys.argv[1]).resolve()
 if not p.is_relative_to(root) or not allowed(p):raise ValueError('Not deployable')
 data=base64.b64encode(p.read_bytes()).decode();print(data[int(sys.argv[2]):int(sys.argv[2])+int(sys.argv[3])])
