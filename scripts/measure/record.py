"""Produce the UI's measured fixture from executable removal trials."""
import difflib
import json
from pathlib import Path
import re
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from engine import ROOT, trim, run_check, blocks_for, materialize, digest
from bank_cases import make, CASES

OUT=ROOT/'app'

def save(id,result,meta):
 patch=OUT/'patches'/f'{id}.patch';patch.write_text(result['patch'])
 report={**result,'meta':meta}
 (OUT/'evidence'/f'{id}.json').write_text(json.dumps(report,indent=2))
 (ROOT/'evidence/runs'/f'{id}.json').write_text(json.dumps(report,indent=2))
 keptblocks=[b for b in result['blocks'] if b['needed']]
 removedblocks=[b for b in result['blocks'] if not b['needed']]
 final=result['final']
 return {**meta,'id':id,'written':result['written'],'kept':result['kept'],'unchecked':result['unchecked'],'tests':final['tests'],'passed':final['passed'],'seconds':sum(r['seconds'] for r in result['runs']),'blocks':[{'name':b['name'],'lines':b['lines'],'needed':b['needed'],'id':b['id'],'path':b['path']} for b in result['blocks']], 'patch':'patches/'+id+'.patch','evidence':'evidence/'+id+'.json','patchSha256':result['patchSha256'],'risk':[],'failedControls':len(result['controls']),'neededTestFailures':sum(sum(not c['passed'] for c in x['cases']) for x in result['controls']),'status':'proven','lampFiles':len(set('.'.join(c['name'].split('.')[:2]) for c in final['cases']))}



def risk_position(result,block,line):
 offset=sum(b['lines'] for b in result['blocks'][:result['blocks'].index(block)] if b['needed'])
 target=next((i for i,x in enumerate(block['new']) if x.rstrip('\n')==line),0)
 for tag,i,j,a,b in difflib.SequenceMatcher(None,block['old'],block['new'],autojunk=False).get_opcodes():
  if tag=='equal':continue
  if a<=target<b:return (offset+(j-i)+target-a)/max(1,result['kept'])
  offset+=(j-i)+(b-a)
 return min(1,offset/max(1,result['kept']))

def bank():
 root=make();base=root/'base';inbox=[]
 for i,(title,name,arg,body,cases) in enumerate(CASES):
  id=f'KASSA-{i+1:02d}'
  result=trim(base,root/f'head-{i+1}',ROOT/'evidence/work'/id,[f'ledger/{name}.py',f'config/{name}.json'],[f'oracle/test_{name}.py'],ROOT/'evidence/runs'/id)
  meta={'title':title,'ask':title+'. Preserve the other bank operations.','did':f'Implements {name.replace("_"," ")} for the stated cases.','agent':'Bank agent · synthetic','repo':'Kassa / Nordic retail bank','source':'synthetic','note':'Keep the tested change. Add a test or a reason for the presentation configuration, or it stays out.'}
  row=save(id,result,meta);inbox.append(row);print(id,row['written'],row['kept'],flush=True)
 id='KASSA-CAP';paths=['ledger/fee_cap.py','ledger/retry_rewrite.py','ledger/currency_cache.py']
 result=trim(base,root/'head-cap',ROOT/'evidence/work'/id,paths,['oracle/test_cap.py'],ROOT/'evidence/runs'/id,whole_paths=paths)
 extra=run_check(ROOT/'evidence/work'/id,['oracle/test_rounding.py'],ROOT/'evidence/runs'/id,'held-out-rounding')
 result['heldOut']=extra
 meta={'title':'Cap instant-transfer fees','ask':'Cap instant-transfer fees at €5. Keep the minimum fee and the existing rounding policy.','did':'Caps instant-transfer fees while preserving the minimum.','agent':'Bank agent · synthetic','repo':'Kassa / Nordic retail bank','source':'synthetic','note':'Kept the cap. Removed the retry rewrite and currency cache; nothing tested them. Fix the half-cent rounding before approval.'}
 row=save(id,result,meta);row['status']='needs-you';row['risk']=[{'path':'ledger/fee_cap.py','start':2,'lines':(root/'head-cap/ledger/fee_cap.py').read_text().splitlines()[1:7],'marked':3,'note':'Rounds half a cent down: a fee of 200.5 cents becomes 200, but the bank policy requires 201. The €5 ceiling still holds.','check':'oracle/test_rounding.py::test_half_cent_uses_bank_rounding_policy','failure':extra['cases'][0]['failure']}];row['heldOut']={'passed':extra['passed'],'tests':extra['tests']};row['readLines']=len(row['risk'][0]['lines']);row['riskPosition']=risk_position(result,result['blocks'][0],row['risk'][0]['lines'][3]);inbox.append(row)
 # The intern's vague ask has no valid acceptance oracle. Independently run each regression on the real bank.
 id='KASSA-INTERN';head=root/'head-intern';paths=['ledger/auth.py','migrations/002_best_bank.sql','ledger/fees.py','schema/bank-api.json'];work=ROOT/'evidence/work'/id
 if not work.exists():shutil.copytree(base,work)
 blocks=[]
 for p in paths:
  blocks+=blocks_for(p,(base/p).read_text() if (base/p).exists() else '',(head/p).read_text(),whole=True)
 checks=[]
 spec=[('ledger/auth.py','test_ownership','Bypasses account ownership. Another customer can read the account.'),('migrations/002_best_bank.sql','test_statement_schema','Drops memo, which statement export still reads.'),('ledger/fees.py','test_nonnegative_fees','Makes fees negative. Transfers credit the customer for fees.')]
 materialize(base,work,blocks,set())
 baseline=run_check(work,['oracle/test_safety.py'],ROOT/'evidence/runs'/id,'baseline')
 for i,(p,test,note) in enumerate(spec):
  materialize(base,work,blocks,{b.id for b in blocks if b.path==p})
  check=run_check(work,['oracle/test_safety.py::'+test],ROOT/'evidence/runs'/id,f'isolated-{i+1}')
  check.update(path=p,note=note);checks.append(check)
 materialize(base,work,blocks,{b.id for b in blocks})
 allchecks=run_check(work,['oracle/test_safety.py'],ROOT/'evidence/runs'/id,'combined')
 written=sum(b.lines for b in blocks)
 report={'baseline':baseline,'checks':checks,'combined':allchecks,'written':written,'blocks':[{'path':b.path,'lines':b.lines} for b in blocks]}
 (OUT/'evidence'/f'{id}.json').write_text(json.dumps(report,indent=2));(ROOT/'evidence/runs'/f'{id}.json').write_text(json.dumps(report,indent=2))
 inbox.append({'id':id,'title':'Make our company the best in the world','ask':'Make our company the best in the world. Make no mistakes.','did':'Changes account access, payment fees, the schema and a generated operating API.','agent':'The intern · synthetic','repo':'Kassa / Nordic retail bank','source':'synthetic','written':written,'kept':0,'unchecked':written,'tests':allchecks['tests'],'passed':allchecks['passed'],'status':'intern','readLines':len(checks),'risk':[{'path':x['path'],'note':x['note'],'failure':x['output'],'check':x['cases'][0]['name'],'lines':[],'start':1} for x in checks],'blocks':[{'name':'Uncheckable ask','lines':written,'needed':False}],'evidence':'evidence/'+id+'.json','note':'Draft to author: What should this change? Name one thing we can test.','seconds':sum(x['seconds'] for x in checks)})
 return inbox


def real(n):
 id=f'AIDEV-{n}';root=ROOT/f'evidence/source/reduino-{n}';base=root/'base';head=root/'head';pr=json.loads((root/'provenance.json').read_text())
 # All published head tests are fixed outside the candidate delta, never removed by a trial.
 oracle=base/'oracle'
 if not oracle.exists():shutil.copytree(head/'tests',oracle)
 paths=[]
 for p in sorted(set(p.relative_to(head) for p in head.rglob('*') if p.is_file())|set(p.relative_to(base) for p in base.rglob('*') if p.is_file())):
  if p.parts[0] in ('tests','oracle','.git','.github') or '__pycache__' in p.parts:continue
  a,b=base/p,head/p
  try:
   before=a.read_text() if a.exists() else '';after=b.read_text() if b.exists() else ''
  except UnicodeDecodeError:continue
  if before!=after:paths.append(str(p))
 result=trim(base,head,ROOT/'evidence/work'/id,paths,['oracle'],ROOT/'evidence/runs'/id)
 result['provenance']={'dataset':pr['dataset'],'row':pr['row'],'base':pr['pr']['base']['sha'],'head':pr['pr']['head']['sha'],'oracle':'All tests from pinned PR head, held fixed and excluded from candidate line counts. Includes published regression tests, not an independent complete spec.'}
 result['oracleSha256']=digest(''.join(p.read_text() for p in sorted(oracle.rglob('*.py'))).encode())
 meta={'title':'Add serial-monitor support' if n==9 else 'Add servo support','ask':pr['row']['title'],'did':'Adds the requested helper and transpiles its calls to Arduino C++.','agent':pr['row']['agent'].replace('_',' '),'repo':'Jackhammer9 / Reduino','source':'AIDev','github':pr['row']['html_url'],'note':'Keep the tested implementation. Add a test or a reason for each unchecked block, or it stays out. Hardware behaviour needs a human check.'}
 row=save(id,result,meta);row['status']='needs-you'
 row['blocks']=[{'id':'needed-implementation','name':'Tested implementation','lines':row['kept'],'needed':True},{'id':'unchecked-changes','name':'Unchecked changes','lines':row['unchecked'],'needed':False}]
 # Select a real needed block at a hardware boundary. No claim of complete risk detection.
 preferred='src/Reduino/Utils/__init__.py' if n==9 else 'src/Reduino/Actuators/Servo.py'
 block=next((b for b in result['blocks'] if b['needed'] and b['path']==preferred),next(b for b in result['blocks'] if b['needed']))
 lines=block['new'];needle='baud_rate' if n==9 else 'min_angle'
 start=next((i for i,line in enumerate(lines) if needle in line),0)
 start=max(0,start-1);snippet=lines[start:start+8]
 source=(head/block['path']).read_text().splitlines();first=next((i for i in range(len(source)) if source[i:i+len(snippet)]==[x.rstrip('\n') for x in snippet]),0)+1
 row['risk']=[{'path':block['path'],'start':first,'lines':[x.rstrip('\n') for x in snippet],'marked':-1,'note':'Host-side tests pass. Check baud-rate and physical serial behaviour on the target board.' if n==9 else 'Host-side tests pass. Check angle and pulse limits against the physical servo specification.','check':'Fixed head regression suite; physical Arduino not checked.'}];row['readLines']=len(snippet)
 row['riskPosition']=risk_position(result,block,snippet[0].rstrip('\n'))
 print(id,row['written'],row['kept'],row['tests'],flush=True)
 return row

if __name__=='__main__':
 mode=sys.argv[1] if len(sys.argv)>1 else 'all'
 if mode=='bank': rows=bank();(ROOT/'evidence/bank-inbox.json').write_text(json.dumps(rows,indent=2))
 elif mode in ('9','24'):
  row=real(int(mode));(ROOT/f'evidence/real-{mode}.json').write_text(json.dumps(row,indent=2))
 elif mode=='assemble':
  rows=json.loads((ROOT/'evidence/bank-inbox.json').read_text());rows=rows[:-1]+[json.loads((ROOT/f'evidence/real-{n}.json').read_text()) for n in (9,24)]+rows[-1:]
  for row in rows:
   if row['status']!='intern':
    report=json.loads((ROOT/'evidence/runs'/f"{row['id']}.json").read_text())
    row['lampFiles']=len(set('.'.join(c['name'].split('.')[:2]) for c in report['final']['cases']))
    row['seconds']=sum(x['seconds'] for x in report['runs'])
  fixture={'product':'Tieto','clock':'Mon 16 Nov · 09:00','owner':'Shreyansh','initials':'SB','measurement':'Measured locally from recorded removal trials. Added + removed implementation lines; oracle tests held fixed. Synthetic bank and public AIDev PRs.','prs':rows,'totals':{'written':sum(r['written'] for r in rows),'needYou':sum(r.get('readLines',0) for r in rows),'proven':sum(r['status']=='proven' for r in rows),'prs':len(rows)}}
  (OUT/'fixture.js').write_text('globalThis.TIETO_FIXTURE = '+json.dumps(fixture,ensure_ascii=False)+';\n');(OUT/'evidence/manifest.json').write_text(json.dumps(fixture,indent=2));print(fixture['totals'])
 else: raise SystemExit('Run bank, 9, 24, then assemble')
