"""Package only fixed public/synthetic sources, never environment or credentials."""
import json
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[2]
for report in sorted((ROOT/'app/evidence').glob('*.json')):
 if report.stem=='manifest':continue
 id=report.stem;data=json.loads(report.read_text())
 if id.startswith('AIDEV'):
  source=ROOT/'evidence/source'/('reduino-'+id.split('-')[1]);base=source/'base';head=source/'head'
 else:
  source=ROOT/'evidence/source/kassa';base=source/'base'
  head=source/('head-cap' if id=='KASSA-CAP' else 'head-intern' if id=='KASSA-INTERN' else 'head-'+str(int(id.split('-')[1])))
 paths=sorted(set(b['path'] for b in data['blocks']))
 meta={'id':id,'paths':paths,'tests':['oracle'] if id.startswith('AIDEV') else ['oracle/test_cap.py'] if id=='KASSA-CAP' else ['oracle/test_safety.py'] if id=='KASSA-INTERN' else ['oracle/test_'+paths[1].split('/')[-1]]}
 # For clean bank rows the Python module's stem determines its fixed oracle.
 if id.startswith('KASSA-') and id not in ('KASSA-CAP','KASSA-INTERN'):
  module=next(p for p in paths if p.startswith('ledger/'));meta['tests']=['oracle/test_'+Path(module).name]
 meta['wholePaths']=paths if id=='KASSA-CAP' else []
 meta['keptIds']=[b['id'] for b in data['blocks'] if b.get('needed')]
 with zipfile.ZipFile(ROOT/'app/runtime/sources'/f'{id}.zip','w',zipfile.ZIP_DEFLATED) as archive:
  archive.writestr('meta.json',json.dumps(meta))
  for p in base.rglob('*'):
   if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts and 'tests' not in p.relative_to(base).parts:
    archive.write(p,'base/'+str(p.relative_to(base)))
  for path in paths:
   if (head/path).exists():archive.write(head/path,'head/'+path)
 print(id,(ROOT/'app/runtime/sources'/f'{id}.zip').stat().st_size)
