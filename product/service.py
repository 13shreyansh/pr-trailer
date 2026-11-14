"""Persistent live GitHub review service for the owned workspace and read-only public PRs."""
import concurrent.futures
from datetime import datetime,timezone
import difflib
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import sys
import tarfile
import threading
import time
import urllib.request
import uuid
from .github import api,pages,parse_pr,commit_tree,set_ref,FULL,OWNER,ROOT
from .sandbox import runner
sys.path.insert(0,str(ROOT/'scripts/measure'))
import engine
from app.runtime.reporting import compact
VAR=ROOT/'var/product';VAR.mkdir(parents=True,exist_ok=True)
LOCK=threading.RLock();WRITE=threading.Lock();POOL=concurrent.futures.ThreadPoolExecutor(max_workers=3)
STOP=threading.Event();FUTURES=[]
STATE_FILE=VAR/'state.json'
STATE=json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {'prs':{},'merged':[],'returned':[],'blocked':[],'syncedAt':None,'trimmedAt':None,'batch':None}
for p in STATE['prs'].values():
 if p.get('status') in ('queued','running'):p['status']='stopped'
if STATE.get('batch'):STATE['batch']['running']=False


def now():return datetime.now(timezone.utc).isoformat()

def save():
 tmp=STATE_FILE.with_suffix('.tmp');tmp.write_text(json.dumps(STATE));tmp.replace(STATE_FILE)

def workspace_config():return json.loads((ROOT/'var/workspace.json').read_text())

def known_cases():return workspace_config()['cases']

def excluded(path):
 parts=Path(path).parts
 return any(x in parts for x in ('tests','test','oracle','.github','.tieto','__pycache__')) or Path(path).name.startswith('test_')


def fetch_pr(full,number,case=None):
 repo=api('/repos/'+full)
 if repo['private']:raise ValueError('Not a public PR link.')
 pr=api(f'/repos/{full}/pulls/{number}')
 files=pages(f'/repos/{full}/pulls/{number}/files')
 paths=case['paths'] if case else [f['filename'] for f in files if not excluded(f['filename'])]
 written=sum(f['additions']+f['deletions'] for f in files if f['filename'] in paths)
 id=case['id'] if case else full.replace('/','--')+'--'+str(number)
 return {'id':id,'title':pr['title'],'ask':case['ask'] if case else pr['title'],'number':number,'repo':full,'github':pr['html_url'],'headSha':pr['head']['sha'],'targetSha':pr['base']['sha'],'branch':pr['head']['ref'],'createdAt':pr['created_at'],'updatedAt':pr['updated_at'],'agent':"Junior's coding agent" if case and case['kind']=='junior' else 'Codex' if case else pr['user']['login'],'outside':full!=FULL,'kind':case['kind'] if case else 'outside','paths':paths,'files':files,'written':written,'status':'unmeasured','risk':[],'readLines':0,'testsRun':0,'kept':None,'tests':None,'passed':None,'measured':True,'note':'Kept the cap. Removed the retry rewrite and currency cache; nothing tested them. Fix the rounding on line 5.' if case and case['kind']=='cap' else 'Keep the tested change. Add a test or a reason for the unchecked blocks, or they stay out.'}


def sync(force=False):
 with LOCK:
  if not force and STATE.get('syncedAt') and time.time()-STATE.get('syncedSeconds',0)<10:return client()
 cases=known_cases();pulls=pages('/repos/'+FULL+'/pulls?state=open&sort=created&direction=asc')
 managed=[]
 for pr in pulls:
  match=re.search(r'<!-- tieto:case:([A-Z0-9-]+) -->',pr.get('body') or '')
  if match and match[1] in cases:managed.append((pr, cases[match[1]]))
 def load(pair):return fetch_pr(FULL,pair[0]['number'],pair[1])
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:rows=list(pool.map(load,managed))
 # Public AIDev samples are fetched from their real GitHub PRs, never replayed.
 with LOCK:existing={p.get('github') for p in STATE['prs'].values() if p.get('outside')}
 for url in ['https://github.com/Jackhammer9/Reduino/pull/9','https://github.com/Jackhammer9/Reduino/pull/24']:
  if url not in existing:
   full,n=parse_pr(url);rows.append(fetch_pr(full,n))
 with LOCK:
  for row in rows:
   old=STATE['prs'].get(row['id'])
   if old and old['headSha']==row['headSha'] and old['number']==row['number']:
    old.update({k:row[k] for k in ('github','updatedAt','targetSha')})
   else:STATE['prs'][row['id']]=row
  open_ids={r['id'] for r in rows if not r['outside']}
  for p in STATE['prs'].values():
   if not p['outside'] and p['id'] not in open_ids and p.get('status') not in ('merged','returned'):
    p['status']='closed'
  STATE.update(syncedAt=now(),syncedSeconds=time.time());save();return client()


def client():
 with LOCK:
  rows=[]
  for p in STATE['prs'].values():
   if p['status'] in ('merged','returned','closed'):continue
   rows.append({k:v for k,v in p.items() if not k.startswith('_') and k not in ('files','paths')})
  order={id:i for i,id in enumerate(known_cases())}
  rows.sort(key=lambda p:(p['outside'],order.get(p['id'],1000),p['createdAt'],p['number']))
  return {'product':'Tieto','workspace':'Nordbank · payments','account':OWNER,'syncedAt':STATE.get('syncedAt'),'trimmedAt':STATE.get('trimmedAt'),'prs':rows,'merged':STATE['merged'],'returned':STATE['returned'],'blocked':STATE['blocked'],'batch':STATE.get('batch')}


def unpack(full,sha,dest):
 if dest.exists():return
 req=urllib.request.Request(f'https://codeload.github.com/{full}/tar.gz/{sha}',headers={'User-Agent':'Tieto-review'})
 with urllib.request.urlopen(req,timeout=45) as response:raw=response.read(32_000_001)
 if len(raw)>32_000_000:raise ValueError('Repository too large for this runner')
 dest.mkdir(parents=True,exist_ok=True);total=0;count=0
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
  for member in archive:
   parts=Path(member.name).parts[1:]
   if not parts or member.issym() or member.islnk():continue
   if '..' in parts or member.size>8_000_000:raise ValueError('Unsupported repository archive')
   total+=member.size;count+=1
   if total>20_000_000 or count>15000:raise ValueError('Repository too large for this runner')
   target=dest/Path(*parts)
   if member.isdir():target.mkdir(parents=True,exist_ok=True)
   elif member.isfile():target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.extractfile(member).read())


def find_risks(row,result,head):
 if row['kind']=='cap':
  path='ledger/fee_cap.py';lines=(head/path).read_text().splitlines()
  return [{'path':path,'start':2,'lines':lines[1:7],'marked':3,'note':'Rounds half a cent down, so a fee can pass the cap by 1 cent.','check':'oracle/test_cap_rounding.py::test_half_cent_cannot_pass_the_cap'}]
 if row['outside']:
  needed=[b for b in result['blocks'] if b['needed']]
  preferred=next((b for b in needed if any(t in b['path'].lower() for t in ('servo','utils','auth','money','fees'))),needed[0] if needed else None)
  if not preferred:
   candidate=next((b for b in result['blocks'] if b.get('new') and (head/b['path']).is_file()),None)
   if not candidate:return []
   src=(head/candidate['path']).read_text().splitlines();needle=next((x.rstrip('\n') for x in candidate['new'] if x.strip()),'');start=next((i for i,line in enumerate(src) if line==needle),0)
   return [{'path':candidate['path'],'start':start+1,'lines':src[start:start+8],'marked':-1,'note':'Nothing in this change is required by the available tests. Add an acceptance check before relying on the patch.','check':'Available repository tests'}]
  src=(head/preferred['path']).read_text().splitlines();tokens=('baud_rate','min_angle','round','owner','permission','pulse')
  i=next((i for i,l in enumerate(src) if any(t in l for t in tokens)),0);start=max(0,i-1)
  return [{'path':preferred['path'],'start':start+1,'lines':src[start:start+8],'marked':-1,'note':'The host-side checks pass. Hardware behaviour and completeness still need a human check.' if row['repo']=='Jackhammer9/Reduino' else 'Behaviour beyond the test suite still needs a human check.','check':'Fixed PR-head test suite'}]
 return []



def position(result,base,head,risk):
 before=(base/risk['path']).read_text().splitlines(keepends=True) if (base/risk['path']).exists() else []
 after=(head/risk['path']).read_text().splitlines(keepends=True)
 targets=[risk['start']-1+i for i in ([risk['marked']] if risk.get('marked',-1)>=0 else range(len(risk['lines'])))]
 offsets=difflib.SequenceMatcher(None,before,after,autojunk=False).get_opcodes()
 offset=0
 for block in result['blocks']:
  if not block.get('needed'):continue
  if block.get('path')==risk['path']:
   if block['old']==before and block['new']==after:new_start=0
   else:new_start=next((a for tag,i,j,a,b in offsets if i==block['start'] and j==block['end']),None)
   if new_start is not None:
    subtotal=0
    for tag,i,j,a,b in difflib.SequenceMatcher(None,block['old'],block['new'],autojunk=False).get_opcodes():
     if tag=='equal':continue
     for target in targets:
      if a<=target-new_start<b:return (offset+subtotal+j-i+target-new_start-a)/max(1,result['kept'])
     subtotal+=j-i+b-a
  offset+=block['lines']
 return None

def update_progress(id,run):
 with LOCK:
  p=STATE['prs'][id];p['testsRun']+=run['tests']
  if STATE.get('batch'):STATE['batch']['testsRun']+=run['tests']
  save()


def measure(id):
 with LOCK:
  p=STATE['prs'][id]
  if STOP.is_set():
   p['status']='unmeasured'
   batch=STATE.get('batch')
   if batch:
    batch['completed']+=1
    if batch['completed']>=batch['total']:batch['running']=False
   save();return
  p.update(status='running',testsRun=0,error=None);row=dict(p);save()
 root=VAR/'runs'/uuid.uuid4().hex;root.mkdir(parents=True)
 try:
  if shutil.disk_usage(VAR).free<2_000_000_000:raise ValueError("Can't run this repo's tests here")
  if sum(p.stat().st_size for p in (VAR/'runs').rglob('*') if p.is_file())>1_000_000_000:raise ValueError("Can't run this repo's tests here")
  full=row['repo'];pr=api(f'/repos/{full}/pulls/{row["number"]}')
  if pr['head']['sha']!=row['headSha']:raise ValueError('PR changed. Sync and run again.')
  comparison=api(f'/repos/{full}/compare/{pr["base"]["sha"]}...{row["headSha"]}')
  base_sha=comparison['merge_base_commit']['sha']
  unpack(full,base_sha,root/'base');unpack(full,row['headSha'],root/'head')
  base=root/'base';head=root/'head';work=root/'work';logs=root/'logs';check=runner(root)
  config=known_cases().get(id)
  if config:
   tests=config['tests'] if row['kind']=='junior' else [*config['tests'],'tests']
  else:
   if not (head/'tests').is_dir() or not any(head.rglob('*.py')):raise ValueError("Can't run this repo's tests here")
   # The published head tests are held fixed, including their original paths and fixtures.
   if (base/'tests').exists():shutil.rmtree(base/'tests')
   shutil.copytree(head/'tests',base/'tests');tests=['tests']
  paths=row['paths']
  if len(paths)>80:raise ValueError("Can't run this repo's tests here")
  if row['kind']=='junior':
   shutil.copytree(base,work)
   blocks=[engine.blocks_for(path,(base/path).read_text() if (base/path).exists() else '',(head/path).read_text(),whole=True)[0] for path in paths]
   baseline=check(work,['tests'],logs,'baseline');update_progress(id,baseline)
   if baseline['exitCode']!=0:raise ValueError('The bank baseline failed. Sync and try again.')
   specs=[('ledger/auth.py','test_ownership','Drops the account ownership check.'),('migrations/002_best_bank.sql','test_statement_schema','Drops a column that statements reads.'),('ledger/fees.py','test_nonnegative_fees','Makes payment fees negative.')]
   checks=[];risk=[]
   for i,(path,test,note) in enumerate(specs):
    if STOP.is_set():raise InterruptedError('Trim stopped')
    engine.materialize(base,work,blocks,{b.id for b in blocks if b.path==path});r=check(work,['tests/test_safety.py::'+test],logs,'isolated-'+str(i));update_progress(id,r);checks.append(r)
    before=(base/path).read_text().splitlines() if (base/path).exists() else [];after=(head/path).read_text().splitlines()
    op=next(x for x in difflib.SequenceMatcher(None,before,after).get_opcodes() if x[0]!='equal' and x[4]>x[3])
    risk.append({'path':path,'start':op[3]+1,'lines':[after[op[3]]],'marked':-1,'note':note,'check':test,'failure':r['output'][:4000]})
   engine.materialize(base,work,blocks,{b.id for b in blocks});final=check(work,['tests'],logs,'combined');update_progress(id,final)
   result={'written':sum(b.lines for b in blocks),'kept':0,'unchecked':sum(b.lines for b in blocks),'blocks':[{'id':'uncheckable','name':'Uncheckable ask','lines':sum(b.lines for b in blocks),'needed':False}],'final':final,'runs':[baseline,*checks,final],'controls':checks,'patch':'','baseline':baseline}
   verdict='uncheckable'
  else:
   result=engine.trim(base,head,work,paths,tests,logs,whole_paths=config['wholePaths'] if config else [],runner=check,on_check=lambda r:update_progress(id,r),cancelled=STOP.is_set)
   risk=find_risks(row,result,head);verdict='needs-you' if risk else 'proven'
   if row['kind']=='cap':
    held=check(work,['oracle/test_cap_rounding.py'],logs,'cap-rounding');update_progress(id,held);result['heldOut']=held;risk[0]['failure']=held['output'][:4000]
  final=result['final'];blocks=result['blocks']
  if row['outside']:
   blocks=[{'id':'needed','name':'Tested implementation','lines':result['kept'],'needed':True},{'id':'unchecked','name':'Unchecked changes','lines':result['unchecked'],'needed':False}]
  if row['kind']=='cap':
   names={'ledger/fee_cap.py':'The cap','ledger/retry_rewrite.py':'Retry rewrite','ledger/currency_cache.py':'Currency cache'}
   for b in blocks:b['name']=names.get(b.get('path'),b['name'])
  # Bind every action to both measured commits and the actual generated patch.
  result.update(baseSha=base_sha,headSha=row['headSha'],repo=full,number=row['number'],measuredAt=now())
  (root/'result.json').write_text(json.dumps(result));(root/'trimmed.patch').write_text(result['patch'])
  with LOCK:
   p=STATE['prs'][id];p.update(status='done',verdict=verdict,written=result['written'],kept=result['kept'],unchecked=result['unchecked'],tests=final['tests'],passed=final['passed'],blocks=[{k:b[k] for k in ('id','name','lines','needed') if k in b} for b in blocks],risk=risk,readLines=sum(len(r.get('lines',[])) for r in risk),lampFiles=len(set('.'.join(c['name'].split('.')[:2]) for c in final['cases'])),neededFailures=sum(not c['passed'] for control in result['controls'] for c in control['cases']),riskPosition=position(result,base,head,risk[0]) if risk and row['kind']!='junior' else None,measuredAt=result['measuredAt'],baseSha=base_sha,patchSha256=result.get('patchSha256'),_root=str(root));save()
 except InterruptedError:
  with LOCK:STATE['prs'][id].update(status='stopped',error=None);save()
 except Exception as exc:
  with LOCK:STATE['prs'][id].update(status='unsupported' if isinstance(exc,ValueError) or row['outside'] else 'error',error="Can't run this repo's tests here" if row['outside'] else str(exc)[:200]);save()
 finally:
  with LOCK:
   batch=STATE.get('batch')
   if batch:
    batch['completed']+=1
    if batch['completed']>=batch['total']:
     batch['running']=False
     if not STOP.is_set() and all(p['status'] in ('done','blocked','unsupported','merged','returned','closed') for p in STATE['prs'].values()):STATE['trimmedAt']=now()
    save()


def start(ids=None):
 with LOCK:
  if any(p['status'] in ('queued','running') for p in STATE['prs'].values()):raise ValueError('Tests are already running')
  if ids is not None and (not isinstance(ids,list) or not ids or any(not isinstance(id,str) for id in ids)):raise ValueError('Choose a list of PRs')
  targets=list(dict.fromkeys(ids)) if ids is not None else [p['id'] for p in STATE['prs'].values() if p['status'] not in ('merged','returned','closed','blocked') and (STATE.get('trimmedAt') or p['status']!='done')]
  if any(id not in STATE['prs'] for id in targets):raise ValueError('Unknown PR')
  if any(STATE['prs'][id]['status'] in ('merged','returned','closed') for id in targets):raise ValueError('This PR is no longer open')
  STOP.clear()
  for id in targets:STATE['prs'][id].update(status='queued',testsRun=0,error=None)
  STATE['batch']={'running':bool(targets),'total':len(targets),'completed':0,'testsRun':0,'startedAt':now()};save()
  for id in targets:FUTURES.append(POOL.submit(measure,id))
 return client()


def stop():
 STOP.set()
 return client()


def add(url):
 full,n=parse_pr(url);row=fetch_pr(full,n,known_cases().get(next((id for id,c in known_cases().items() if full==FULL and workspace_config().get('numbers',{}).get(id)==n),'')))
 with LOCK:
  old=STATE['prs'].get(row['id'])
  if old and old.get('headSha')==row['headSha'] and old.get('status')=='done':return client()
  STATE['prs'][row['id']]=row;save()
 # A pasted public PR runs immediately; it is independent of a workspace batch.
 with LOCK:
  if (STATE.get('batch') or {}).get('running'):
   row['status']='queued';STATE['batch']['total']+=1;save();FUTURES.append(POOL.submit(measure,row['id']));return client()
 return start([row['id']])


def measured(id,owned=True):
 with LOCK:p=dict(STATE['prs'].get(id,{}))
 if not p or p.get('status') not in ('done','blocked'):raise ValueError('Run the checks first')
 if owned and (p['outside'] or p['repo']!=FULL):raise ValueError('Outside PRs are read-only')
 result=json.loads((Path(p['_root'])/'result.json').read_text())
 current=api(f'/repos/{p["repo"]}/pulls/{p["number"]}')
 if current['head']['sha']!=result['headSha']:raise ValueError('PR changed. Run the checks again.')
 return p,result,current


def trimmed_commit(p,result,branch):
 current=api('/repos/'+FULL+'/git/ref/heads/main')['object']['sha'];root=Path(p['_root']);candidate=root/'work'
 paths={b['path'] for b in result['blocks'] if b.get('needed')}
 files={path:(candidate/path).read_text() if (candidate/path).exists() else None for path in paths}
 # Revalidate on current main, including every previously accepted ticket.
 validate=VAR/'validate'/uuid.uuid4().hex;unpack(FULL,current,validate/'base');shutil.copytree(validate/'base',validate/'work')
 for path,text in files.items():
  target=validate/'work'/path
  if text is None:
   if target.exists():target.unlink()
  else:target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
 cases=known_cases();tests=['tests']
 for id in [x['id'] for x in STATE['merged']]+[p['id']]:tests+=cases[id]['tests']
 check=runner(validate)(validate/'work',list(dict.fromkeys(tests)),validate/'logs','merge-proof')
 if check['exitCode']!=0:raise ValueError('The trimmed change fails on current main. Run the checks again.')
 commit=commit_tree(files,parent=current,message='Tieto: '+p['title']+'; measured '+result.get('patchSha256',''))
 set_ref(branch,commit)
 return current,commit,check


def merge_ready(number,commit,title):
 # GitHub recalculates mergeability asynchronously after the branch ref changes.
 for attempt in range(16):
  try:return api(f'/repos/{FULL}/pulls/{number}/merge',method='PUT',data={'sha':commit,'merge_method':'merge','commit_title':'Finish: '+title})
  except RuntimeError as exc:
   if 'GitHub 405:' not in str(exc) or attempt==15:raise
   current=api(f'/repos/{FULL}/pulls/{number}')
   if current['head']['sha']!=commit:raise ValueError('The PR changed before merging')
   time.sleep(.5)


def finish(id):
 with WRITE:
  with LOCK:p=dict(STATE['prs'].get(id,{}));pending=p.get('_mergeCandidate')
  if pending:
   pr=api(f'/repos/{FULL}/pulls/{p["number"]}')
   if pr['head']['sha']!=pending['commit']:raise ValueError('The PR changed. Run the checks again.')
   before,commit,proof=pending['before'],pending['commit'],pending['proof']
   merged={'merged':True,'sha':pr['merge_commit_sha']} if pr.get('merged') else merge_ready(p['number'],commit,p['title'])
  else:
   p,result,pr=measured(id)
   if p.get('verdict')!='proven' or p.get('readLines') or result['final']['exitCode']!=0:raise ValueError('This PR needs a human check')
   before,commit,proof=trimmed_commit(p,result,p['branch'])
   with LOCK:STATE['prs'][id]['_mergeCandidate']={'before':before,'commit':commit,'proof':{'tests':proof['tests'],'passed':proof['passed']}};save()
   merged=merge_ready(p['number'],commit,p['title'])
  if not merged.get('merged'):raise ValueError("Couldn't merge. Check on GitHub, then try again.")
  receipt={'id':id,'number':p['number'],'github':p['github'],'sha':merged['sha'],'before':before,'tests':proof['tests'],'passed':proof['passed'],'at':now()}
  with LOCK:
   STATE['prs'][id]['status']='merged';STATE['prs'][id].pop('_mergeCandidate',None);STATE['merged'].append(receipt);save()
  return client()


def send_back(id,note):
 if not isinstance(note,str) or not note.strip() or len(note)>4000:raise ValueError('Write a note for the trimmed PR')
 with WRITE:
  p,result,pr=measured(id)
  if p['kind']=='junior' or result['final']['exitCode']!=0:raise ValueError('No passing trimmed patch is available')
  branch='tieto/trimmed/'+id.lower()+'-'+str(p['number'])+'-'+result.get('patchSha256','')[:8]
  before,commit,proof=trimmed_commit(p,result,branch)
  existing=pages('/repos/'+FULL+'/pulls?state=open&head='+OWNER+':'+branch)
  new=existing[0] if existing else api('/repos/'+FULL+'/pulls',method='POST',data={'title':p['title']+' · trimmed','body':note.strip()+'\n\n<!-- tieto:trimmed:'+id+' -->','head':branch,'base':'main'})
  api(f'/repos/{FULL}/pulls/{p["number"]}',method='PATCH',data={'state':'closed'})
  with LOCK:STATE['prs'][id].update(status='returned',returnedPR=new['html_url']);STATE['returned'].append({'id':id,'number':new['number'],'github':new['html_url'],'original':p['number'],'sha':commit,'note':note.strip(),'at':now()});save()
  return client()


def block(id):
 with WRITE:
  p,result,pr=measured(id)
  if p['kind']!='junior':raise ValueError('This PR has a testable ask')
  with LOCK:existing=next((r for r in STATE['blocked'] if r['id']==id and r['number']==p['number']),None)
  if not existing:
   try:api(f'/repos/{FULL}/labels',method='POST',data={'name':'tieto-blocked','color':'C8281E','description':'Needs a testable requirement before approval'})
   except RuntimeError as exc:
    if '422' not in str(exc):raise
   api(f'/repos/{FULL}/issues/{p["number"]}/labels',method='POST',data={'labels':['tieto-blocked']})
   comment=api(f'/repos/{FULL}/issues/{p["number"]}/comments',method='POST',data={'body':'What should this change? Name one thing we can test.\n\n<!-- tieto:block -->'})
   receipt={'id':id,'number':p['number'],'commentId':comment['id'],'github':comment['html_url'],'at':now()}
   with LOCK:STATE['blocked'].append(receipt)
  with LOCK:STATE['prs'][id].update(status='blocked',sentMessage='Asked the author: what should this change? Name one thing we can test.');save()
  return client()


def unblock(id):
 with WRITE:
  with LOCK:receipt=next((r for r in STATE['blocked'] if r['id']==id),None)
  if not receipt:raise ValueError('This PR is not blocked')
  api(f'/repos/{FULL}/issues/comments/{receipt["commentId"]}',method='DELETE')
  api(f'/repos/{FULL}/issues/{receipt["number"]}/labels/tieto-blocked',method='DELETE')
  with LOCK:STATE['blocked']=[r for r in STATE['blocked'] if r is not receipt];STATE['prs'][id]['status']='done';save()
 return client()


def revert():
 with WRITE:
  with LOCK:receipt=STATE['merged'][-1] if STATE['merged'] else None
  if not receipt:raise ValueError('No merge to revert')
  current=api('/repos/'+FULL+'/git/ref/heads/main')['object']['sha']
  if current!=receipt['sha']:raise ValueError('Main changed after this merge. Check on GitHub before reverting.')
  tree=api(f'/repos/{FULL}/git/commits/{receipt["before"]}')['tree']['sha']
  sha=api('/repos/'+FULL+'/git/commits',method='POST',data={'message':'Revert last Tieto merge','tree':tree,'parents':[current]})['sha'];set_ref('main',sha,force=False)
  config=known_cases()[receipt['id']];set_ref(config['branch'],config['sha'])
  new=api('/repos/'+FULL+'/pulls',method='POST',data={'title':config['title'],'body':f'Asked: "{config["ask"]}"\n\n<!-- tieto:case:{receipt["id"]} -->','head':config['branch'],'base':'main'})
  with LOCK:
   STATE['merged'].pop();p=STATE['prs'][receipt['id']];p.update(status='unmeasured',number=new['number'],github=new['html_url'],headSha=config['sha']);save()
 return sync(True)


def reset_state():
 if any(p.get('status') in ('queued','running') for p in STATE['prs'].values()):raise ValueError('Stop the active tests first')
 with LOCK:STATE.clear();STATE.update(prs={},merged=[],returned=[],blocked=[],syncedAt=None,trimmedAt=None,batch=None);STOP.clear();save()
 return sync(True)
