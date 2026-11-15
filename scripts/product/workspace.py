"""Create/reset only the owned Nordbank example workspace. Never prints credentials."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts/measure'))
from product.github import api,pages,commit_tree,set_ref,FULL,OWNER
from bank_cases import make,CASES
OUT=ROOT/'var/workspace.json'

def worker_origin():
 port=int(os.environ.get('PORT','4322'))
 if not 1<=port<=65535:raise ValueError('Invalid worker port')
 return 'http://127.0.0.1:'+str(port)


def setup():
 identity=api('/user')
 if identity['login']!=OWNER:raise RuntimeError('Wrong GitHub identity')
 source=make();base=source/'base'
 try:repo=api('/repos/'+FULL)
 except RuntimeError as exc:
  if '404' not in str(exc):raise
  repo=api('/user/repos',method='POST',create_repo=True,data={'name':FULL.split('/')[1],'description':'Nordbank payments. A real, resettable example workspace for evidence-based code review.','private':False,'auto_init':False,'has_issues':True})
 rows=json.loads((ROOT/'app/evidence/manifest.json').read_text())['prs'];rows=[r for r in rows if r['source']=='synthetic']
 files={str(p.relative_to(base)):p.read_text() for p in base.rglob('*') if p.is_file() and p.suffix in ('.py','.sql') and '__pycache__' not in p.parts}
 files['tests/test_safety.py']=files['oracle/test_safety.py']
 files['pyproject.toml']='[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
 files['requirements.txt']='pytest==9.2.0\n'
 files['README.md']='# Nordbank payments\n\nAn example Nordic payments service with real pull requests, real test execution and a repeatable review workflow. No customer data.\n\nRun `python -m pytest tests` for bank invariants. Ticket acceptance tests live in `oracle/`; their command is on each PR.\n\nChanges are prepared by Codex for this owned example workspace. The first-week junior scenario is fictional.\n'
 files['LICENSE']=(ROOT/'LICENSE').read_text()
 files['oracle/test_cap_rounding.py']='from ledger.fee_cap import capped_fee\n\ndef test_half_cent_cannot_pass_the_cap():\n    assert capped_fee(250250) == 500\n'
 metadata=[]
 for row in rows:
  id=row['id'];branch='agent/'+id.lower();paths=[b['path'] for b in row['blocks'] if b.get('path')]
  if id=='KASSA-INTERN':paths=['ledger/auth.py','migrations/002_best_bank.sql','ledger/fees.py','schema/bank-api.json']
  if id=='KASSA-CAP':paths=['ledger/fee_cap.py','ledger/retry_rewrite.py','ledger/currency_cache.py']
  tests=['oracle/test_safety.py'] if id=='KASSA-INTERN' else ['oracle/test_cap.py'] if id=='KASSA-CAP' else ['oracle/test_'+next(Path(p).name for p in paths if p.startswith('ledger/'))]
  metadata.append({'id':id,'title':row['title'],'ask':row['ask'],'branch':branch,'tests':tests,'paths':paths,'wholePaths':paths if id in ('KASSA-CAP','KASSA-INTERN') else [],'kind':'junior' if id=='KASSA-INTERN' else 'cap' if id=='KASSA-CAP' else 'clean'})
 files['.tieto/cases.json']=json.dumps(metadata,indent=2)
 if OUT.exists():saved=json.loads(OUT.read_text());baseline=saved['baseline']
 else:
  import base64
  if repo.get('size',0)==0:
   try:api('/repos/'+FULL+'/contents/README.md',method='PUT',data={'message':'Initialize owned Nordbank workspace','content':base64.b64encode(b'# Nordbank payments\n').decode(),'branch':'main'})
   except RuntimeError as exc:
    if '422' not in str(exc):raise
  parent=api('/repos/'+FULL+'/git/ref/heads/main')['object']['sha']
  baseline=commit_tree(files,parent=parent,message='Nordbank payments baseline, bank invariants and ticket acceptance oracles')
  set_ref('main',baseline)
  api('/repos/'+FULL,method='PATCH',data={'default_branch':'main'})
  set_ref('tieto/baseline',baseline)
  saved={'repo':FULL,'baseline':baseline,'cases':{}}
  OUT.write_text(json.dumps(saved,indent=2))
 for meta in metadata:
  id=meta['id'];head=source/('head-cap' if id=='KASSA-CAP' else 'head-intern' if id=='KASSA-INTERN' else 'head-'+str(int(id.split('-')[1])))
  delta={p:(head/p).read_text() for p in meta['paths']}
  if id=='KASSA-CAP':
   delta['ledger/fee_cap.py']='''from decimal import Decimal, ROUND_HALF_DOWN, ROUND_HALF_UP

def capped_fee(amount_cents):
    raw = Decimal(amount_cents) * Decimal("0.002")
    rounded = int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_DOWN))
    bounded = max(50, int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP)))
    return 500 if rounded > 500 else bounded
'''
  if id not in saved['cases']:
   sha=commit_tree(delta,parent=baseline,message='Codex: '+meta['title']);saved['cases'][id]={'sha':sha,**meta};OUT.write_text(json.dumps(saved,indent=2));set_ref('tieto/original/'+id.lower(),sha)
 reset(saved)
 print(json.dumps({'repo':FULL,'baseline':baseline,'openCases':len(saved['cases'])}))


def reset(saved=None):
 saved=saved or json.loads(OUT.read_text())
 # Stop and settle the runner before changing the repository it is measuring.
 import urllib.request
 try:
  req=urllib.request.Request(worker_origin()+'/api/stop',data=b'{}',headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=10) as response:state=json.load(response)
  for attempt in range(90):
   if not (state.get('batch') or {}).get('running') and all(p['status'] not in ('queued','running') for p in state['prs']):break
   time.sleep(1)
   with urllib.request.urlopen(worker_origin()+'/api/status',timeout=10) as response:state=json.load(response)
  else:raise RuntimeError('Active tests did not stop')
 except Exception as exc:raise RuntimeError('GitHub unchanged because worker reset failed: '+str(exc)) from exc
 for pr in pages('/repos/'+FULL+'/pulls?state=open'):
  if any(label['name']=='tieto-blocked' for label in pr.get('labels',[])):
   api(f'/repos/{FULL}/issues/{pr["number"]}/labels/tieto-blocked',method='DELETE')
  if pr['head']['ref'].startswith('tieto/trimmed/'):
   api(f'/repos/{FULL}/pulls/{pr["number"]}',method='PATCH',data={'state':'closed'})
 for comment in pages('/repos/'+FULL+'/issues/comments?sort=created&direction=desc'):
  if '<!-- tieto:block -->' in comment['body'] and comment['user']['login']==OWNER:
   api(f'/repos/{FULL}/issues/comments/{comment["id"]}',method='DELETE')
 set_ref('main',saved['baseline'])
 allprs=pages('/repos/'+FULL+'/pulls?state=all&sort=created&direction=desc')
 numbers={}
 for id,case in saved['cases'].items():
  set_ref(case['branch'],case['sha'])
  candidates=[p for p in allprs if p['head']['ref']==case['branch']]
  opened=next((p for p in candidates if p['state']=='open'),None)
  if opened is None:
   unmerged=next((p for p in candidates if not p.get('merged_at')),None)
   if unmerged:
    try:opened=api(f'/repos/{FULL}/pulls/{unmerged["number"]}',method='PATCH',data={'state':'open'})
    except RuntimeError:pass
  if opened is None:
   body=f'Requirement {id}\n\nAsked: "{case["ask"]}"\n\nPrepared by Codex for the owned Nordbank payments example workspace.\n\nAcceptance: `python -m pytest {" ".join(case["tests"])} tests`\n\n<!-- tieto:case:{id} -->'
   opened=api('/repos/'+FULL+'/pulls',method='POST',data={'title':case['title'],'body':body,'head':case['branch'],'base':'main'})
  numbers[id]=opened['number']
 saved['numbers']=numbers;saved['resetAt']=time.time();OUT.write_text(json.dumps(saved,indent=2))
 try:
  import urllib.request
  req=urllib.request.Request(worker_origin()+'/internal/reset',data=b'{}',headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=90) as response:state=json.load(response)
  assert len(state['prs'])==len(numbers)+2, 'Reset did not restore every workspace row'
  assert not state['merged'] and not state['returned'] and not state['blocked'], 'Reset retained decisions'
  assert all(p['status']=='unmeasured' for p in state['prs']), 'Reset retained measurements'
 except Exception as exc:raise RuntimeError('GitHub was restored, but worker reset failed: '+str(exc)) from exc
 assert api('/repos/'+FULL+'/git/ref/heads/main')['object']['sha']==saved['baseline']
 opened=pages('/repos/'+FULL+'/pulls?state=open')
 assert {p['number'] for p in opened}==set(numbers.values()), 'Unexpected open workspace PRs'
 receipt={'reset':'complete','repo':FULL,'openPRs':len(numbers),'numbers':numbers,'baseline':saved['baseline'],'verifiedAt':time.time(),'workerRows':len(state['prs']),'decisionsCleared':True,'measured':True}
 report=ROOT/'artifacts/e2e/resets.json';report.parent.mkdir(parents=True,exist_ok=True)
 history=json.loads(report.read_text()) if report.exists() else [];history.append(receipt);report.write_text(json.dumps(history,indent=2)+'\n')
 print(json.dumps(receipt),flush=True)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('action',choices=['setup','reset']);args=parser.parse_args()
 setup() if args.action=='setup' else reset()
