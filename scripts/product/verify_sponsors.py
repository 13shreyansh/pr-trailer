"""Read credentials from stdin into memory; verify real providers without GitHub writes."""
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))

def main():
 secrets=json.load(sys.stdin)
 allowed={'MODAL_TOKEN_ID','MODAL_TOKEN_SECRET','MONGODB_URI','MONGODB_DATABASE','TIETO_GITHUB_TOKEN'}
 if set(secrets)-allowed:raise ValueError('Unexpected verification configuration')
 os.environ.update({k:str(v) for k,v in secrets.items()})
 os.environ['TIETO_TEST_RUNNER']='modal'
 os.environ['ENTIRE_BIN']=str(ROOT/'.tools/bin/entire')
 from product import service
 service.sync(True)
 if 'KASSA-CAP' not in service.STATE['prs']:raise RuntimeError('The owned fee-cap PR is not open; no repository changes were made')
 service.measure('KASSA-CAP')
 row=service.STATE['prs']['KASSA-CAP']
 if row.get('status')!='done':raise RuntimeError('Real provider measurement failed: '+row.get('error','unknown'))
 result=json.loads((Path(row['_root'])/'result.json').read_text())
 from product.runlog import read_run
 archived=read_run(result['runId'])
 receipt={'commit':__import__('subprocess').check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
          'sourceRepo':row['repo'],'sourcePR':row['number'],'sourceHead':row['headSha'],
          'runId':result['runId'],'requestTests':result['final']['tests'],'requestPassed':result['final']['passed'],
          'heldOut':{'tests':result.get('heldOut',{}).get('tests'),'passed':result.get('heldOut',{}).get('passed'),'exitCode':result.get('heldOut',{}).get('exitCode')},
          'execution':result['final'].get('execution'),'graph':result.get('codeContext'),
          'archiveProvider':archived['provider'],'archivedEvents':len(archived['events']),
          'sandboxIds':list(dict.fromkeys(r.get('execution',{}).get('sandboxId') for r in result.get('runs',[])))}
 (ROOT/'evidence/sponsor-live-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({k:receipt[k] for k in ['sourceRepo','sourcePR','requestTests','requestPassed','heldOut','archiveProvider','archivedEvents']}))
 if receipt['execution']['provider']!='modal' or not receipt['graph'].get('available'):raise RuntimeError('Provider integration did not execute')
 if os.environ.get('MONGODB_URI') and not receipt['archivedEvents']:raise RuntimeError('Atlas did not persist the execution records')

if __name__=='__main__':main()
