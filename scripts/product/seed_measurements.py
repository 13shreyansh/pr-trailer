"""Index completed canary measurements only after checking their original runtime source."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-release',type=Path,required=True);args=parser.parse_args()
    original=args.source_release.resolve()
    if not original.is_relative_to(Path('/opt/pr-trailer/releases')):raise ValueError('Not an owned release')
    for relative in ['scripts/measure/engine.py','product/modal_runner.py','product/provenance.py']:
        if hashlib.sha256((original/relative).read_bytes()).digest()!=hashlib.sha256((ROOT/relative).read_bytes()).digest():
            raise ValueError('Measurement engine, sandbox or image profile changed; old runs cannot be seeded')
    from product import service
    from product.measurement_cache import _completed,store,risk_fingerprint
    if risk_fingerprint((original/'product/service.py').read_text())!=risk_fingerprint((ROOT/'product/service.py').read_text()):
        raise ValueError('Risk classification changed; old runs cannot be seeded')
    service.sync(True);seeded=0;declined=[]
    for path in (service.VAR/'runs').glob('*/result.json'):
        result=json.loads(path.read_text());root=path.parent
        row=next((p for p in service.STATE['prs'].values() if p['repo']==result.get('repo') and p['headSha']==result.get('headSha')),None)
        config=service.known_cases().get(row['id']) if row else None
        if not row or row['kind']=='junior' or not _completed(result,row,result.get('baseSha'),config):
            declined.append({'report':root.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'measuredAt':result.get('measuredAt'),'reason':'missing or mismatched producer contract, invocation or completed result'});continue
        risk=service.find_risks(row,result,root/'head')
        if row['kind']=='cap' and result.get('heldOut'):risk[0]['failure']=result['heldOut']['output'][:4000]
        final=result['final'];blocks=result['blocks']
        if row['outside']:blocks=[{'id':'needed','name':'Tested implementation','lines':result['kept'],'needed':True},{'id':'unchecked','name':'Unchecked changes','lines':result['unchecked'],'needed':False}]
        measured={'verdict':'needs-you' if risk else 'proven','written':result['written'],'kept':result['kept'],
          'unchecked':result['unchecked'],'tests':final['tests'],'passed':final['passed'],
          'blocks':[{k:b[k] for k in ('id','name','lines','needed') if k in b} for b in blocks],
          'risk':risk,'readLines':sum(len(r.get('lines',[])) for r in risk),
          'lampFiles':len(set('.'.join(c['name'].split('.')[:2]) for c in final['cases'])),
          'neededFailures':sum(not c['passed'] for control in result['controls'] for c in control['cases']),
          'riskPosition':service.position(result,root/'base',root/'head',risk[0]) if risk else None,
          'measuredAt':result['measuredAt'],'baseSha':result['baseSha'],'patchSha256':result.get('patchSha256'),
          'runId':result['runId'],'executionProvider':'modal','codeContext':result['codeContext'],'_root':str(root)}
        seeded+=bool(store(service.VAR/'verified',row,result['baseSha'],service.known_cases().get(row['id']),measured,
                          origin_commit=(original/'release-commit').read_text().strip()))
    print(json.dumps({'completedActualRunsSeeded':seeded,'partialRunsSeeded':0,'sourceRelease':str(original),'declinedCount':len(declined),'declined':declined}))

if __name__=='__main__':main()
