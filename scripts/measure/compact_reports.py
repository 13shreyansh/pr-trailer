import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'app/runtime'))
from reporting import compact,archive
for p in (ROOT/'evidence/runs').glob('*.json'):
 if p.stem.startswith(('AIDEV-','KASSA-')):
  report=json.loads(p.read_text());dest=ROOT/'app/evidence'/p.name
  full=dest.with_suffix('.full.json.gz');full.write_bytes(archive(report))
  summary=compact(report);summary['fullLogArchive']=full.name;dest.write_text(json.dumps(summary,indent=2))
  print(dest.name,dest.stat().st_size,full.stat().st_size)
