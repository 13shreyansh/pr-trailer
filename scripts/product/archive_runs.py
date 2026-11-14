"""Preserve the actual latest removal runs before the recording workspace is reset."""
import gzip,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'artifacts/e2e/recorded-runs';OUT.mkdir(parents=True,exist_ok=True)
state=json.loads((ROOT/'var/product/state.json').read_text());items=[]
for id,p in state['prs'].items():
 if not p.get('_root'):continue
 source=Path(p['_root'])/'result.json'
 if not source.is_file():continue
 raw=source.read_bytes();r=json.loads(raw);name=id+'.json.gz';(OUT/name).write_bytes(gzip.compress(raw,mtime=0))
 items.append({'id':id,'repo':r['repo'],'number':r['number'],'headSha':r['headSha'],'baseSha':r['baseSha'],'written':r['written'],'kept':r['kept'],'tests':r['final']['tests'],'passed':r['final']['passed'],'measuredAt':r['measuredAt'],'file':name,'measured':True})
record={'sourceCommit':json.loads((ROOT/'var/current-publication.json').read_text())['commit'],'runs':items,'measured':True}
(OUT/'manifest.json').write_text(json.dumps(record,indent=2)+'\n');print('Archived real removal runs:',len(items))
