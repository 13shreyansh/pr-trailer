"""Allowlisted local removal trials. No user code, URLs, commands or credentials accepted."""
import json
from pathlib import Path
import sys
import tempfile
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
import engine
from reporting import compact,archive
import base64
engine.PYTHON=sys.executable


def execute(id):
 source=Path(__file__).resolve().parent/'sources'/f'{id}.zip'
 # Check exact membership before constructing any file or running any process.
 if id not in {p.stem for p in source.parent.glob('*.zip')}:
  raise ValueError('Unknown fixed sample')
 with tempfile.TemporaryDirectory(prefix='tieto-') as tmp:
  root=Path(tmp)
  with zipfile.ZipFile(source) as z:z.extractall(root)
  meta=json.loads((root/'meta.json').read_text());base=root/'base';head=root/'head';work=root/'work';logs=root/'logs'
  if id=='KASSA-INTERN':
   import shutil
   shutil.copytree(base,work)
   blocks=[engine.blocks_for(p,(base/p).read_text() if (base/p).exists() else '',(head/p).read_text(),whole=True)[0] for p in meta['paths']]
   checks=[]
   for path,test in [('ledger/auth.py','test_ownership'),('migrations/002_best_bank.sql','test_statement_schema'),('ledger/fees.py','test_nonnegative_fees')]:
    engine.materialize(base,work,blocks,{b.id for b in blocks if b.path==path})
    checks.append(engine.run_check(work,['oracle/test_safety.py::'+test],logs,'isolated-'+str(len(checks))))
   engine.materialize(base,work,blocks,{b.id for b in blocks})
   final=engine.run_check(work,meta['tests'],logs,'combined')
   return {'id':id,'written':sum(b.lines for b in blocks),'kept':0,'tests':final['tests'],'passed':final['passed'],'checks':checks,'final':final,'measured':True}
  result=engine.trim(base,head,work,meta['paths'],meta['tests'],logs,whole_paths=meta['wholePaths'])
  final=result['final']
  output={'id':id,'written':result['written'],'kept':result['kept'],'tests':final['tests'],'passed':final['passed'],'patchSha256':result['patchSha256'],'runs':result['runs'],'controls':result['controls'],'measured':True}
  if id=='KASSA-CAP':output['heldOut']=engine.run_check(work,['oracle/test_rounding.py'],logs,'held-out-rounding')
  full=archive(output);summary=compact(output);summary['fullLogGzipBase64']=base64.b64encode(full).decode();return summary

if __name__=='__main__':
 print(json.dumps(execute(sys.argv[1])))
