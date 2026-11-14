"""Materialize signed synthetic changes in a real local Git branch, then test and export it."""
import base64
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile
from dulwich import porcelain
from dulwich.repo import Repo
import engine
engine.PYTHON=sys.executable


def execute(ids):
 if not isinstance(ids,list) or not ids or len(ids)>19 or len(set(ids))!=len(ids):raise ValueError('Choose distinct bank samples')
 allowed={f'KASSA-{i:02d}' for i in range(1,20)}
 if any(not isinstance(id,str) or id not in allowed for id in ids):raise ValueError('Only proven synthetic bank samples can finish')
 sources=Path(__file__).resolve().parent/'sources'
 with tempfile.TemporaryDirectory(prefix='tieto-branch-') as tmp:
  root=Path(tmp)
  with zipfile.ZipFile(sources/(ids[0]+'.zip')) as archive:archive.extractall(root/'initial')
  bank=root/'kassa';shutil.copytree(root/'initial/base',bank)
  porcelain.init(str(bank),bare=False)
  def commit(message):
   paths=[str(p.resolve()) for p in bank.rglob('*') if p.is_file() and '.git' not in p.relative_to(bank).parts and '__pycache__' not in p.parts]
   porcelain.add(str(bank),paths=paths)
   return porcelain.commit(str(bank),message=message.encode(),author=b'Tieto local rehearsal <tieto@example.invalid>',committer=b'Tieto local rehearsal <tieto@example.invalid>')
  initial=commit('Synthetic Kassa baseline and fixed acceptance oracles')
  with Repo(str(bank)) as repo:
   repo.refs[b'refs/heads/tieto/approved']=initial
   repo.refs.set_symbolic_ref(b'HEAD',b'refs/heads/tieto/approved')
  tests=['oracle/test_safety.py'];commits=[]
  for id in ids:
   case=root/id
   with zipfile.ZipFile(sources/(id+'.zip')) as archive:archive.extractall(case)
   meta=json.loads((case/'meta.json').read_text());base=case/'base';head=case/'head';blocks=[]
   for p in meta['paths']:
    blocks+=engine.blocks_for(p,(base/p).read_text() if (base/p).exists() else '',(head/p).read_text() if (head/p).exists() else '',whole=p in meta['wholePaths'])
   engine.materialize(base,bank,blocks,set(meta['keptIds']))
   commits.append({'id':id,'commit':commit('Finish '+id+': keep only measured needed blocks').decode()});tests+=meta['tests']
  check=engine.run_check(bank,tests,root/'logs','signed-branch')
  if check['exitCode'] or check['tests']==0:raise RuntimeError('Combined signed branch failed')
  buf=io.BytesIO()
  with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as archive:
   for p in bank.rglob('*'):
    if p.is_file() and '__pycache__' not in p.parts:archive.write(p,'kassa/'+str(p.relative_to(bank)))
  return {'ids':ids,'branch':'tieto/approved','commit':commits[-1]['commit'],'commits':commits,'tests':check['tests'],'passed':check['passed'],'measured':True,'zipBase64':base64.b64encode(buf.getvalue()).decode(),'check':check}

if __name__=='__main__':print(json.dumps(execute(json.loads(sys.argv[1]))))
