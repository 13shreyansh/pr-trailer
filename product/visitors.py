"""Visitor sessions for the shared example workspace.

The workspace is one real GitHub repository, so its state is shared. This module decides
who currently holds it and restores the true start state when a new visitor arrives, when
the holder signs out, or when it has sat used and idle. It never changes measurement,
merge, return or block behaviour; it only calls the existing stop and reset paths.
"""
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
from . import service
ROOT=Path(__file__).resolve().parents[1]
FILE=service.VAR/'visitors.json'
ACTIVE_SECONDS=90      # a holder who polled this recently is still using the workspace
IDLE_SECONDS=600       # a used workspace nobody has polled for this long is restored
LOCK=threading.RLock()
BOOT=time.time()
try:SESSION=json.loads(FILE.read_text())
except Exception:SESSION={}
SESSION={'holder':SESSION.get('holder'),'wrote':bool(SESSION.get('wrote')),'seen':{},'reset':{'running':False,'kind':None,'startedAt':None,'error':None}}


def save():
 tmp=FILE.with_suffix('.tmp');tmp.write_text(json.dumps({'holder':SESSION['holder'],'wrote':SESSION['wrote']}));tmp.replace(FILE)


def valid(visitor):
 return visitor if isinstance(visitor,str) and 8<=len(visitor)<=64 and visitor.replace('-','').isalnum() else None


def touch(visitor):
 visitor=valid(visitor)
 if visitor:
  with LOCK:
   SESSION['seen'][visitor]=time.time()
   if not SESSION['holder'] and not SESSION['reset']['running']:SESSION['holder']=visitor;save()
   for old in [k for k,v in SESSION['seen'].items() if time.time()-v>3600]:del SESSION['seen'][old]
 return visitor


def dirty():
 """True when the workspace differs from a freshly reset one."""
 with service.LOCK:
  state=service.STATE;rows=list(state['prs'].values())
  if state.get('merged') or state.get('returned') or state.get('blocked') or state.get('trimmedAt'):return True
  if any(p.get('status')!='unmeasured' for p in rows):return True
  return sum(1 for p in rows if p.get('outside'))>2


def wrote_to_github():
 with service.LOCK:
  state=service.STATE
  touched=bool(state.get('merged') or state.get('returned') or state.get('blocked')) or any(p.get('status') in ('merged','returned','blocked','closed') for p in state['prs'].values())
 with LOCK:return touched or SESSION['wrote']


def mark_write():
 with LOCK:SESSION['wrote']=True;save()


def resetting():
 with LOCK:return SESSION['reset']['running']


def guard():
 if resetting():raise ValueError('The workspace is being restored. Try again in a moment.')


def holder_active(now=None):
 now=now or time.time()
 with LOCK:return bool(SESSION['holder']) and now-SESSION['seen'].get(SESSION['holder'],0)<ACTIVE_SECONDS


def _light():
 service.stop()
 for attempt in range(90):
  with service.LOCK:busy=any(p.get('status') in ('queued','running') for p in service.STATE['prs'].values())
  if not busy:break
  time.sleep(1)
 else:raise RuntimeError('Active tests did not stop')
 service.reset_state()


def _full():
 # The verified reset script restores GitHub (main, branches, PRs, comments) and then this worker.
 done=subprocess.run([sys.executable,str(ROOT/'scripts/product/workspace.py'),'reset'],cwd=ROOT,capture_output=True,text=True,timeout=420)
 if done.returncode:raise RuntimeError((done.stderr or done.stdout).strip().splitlines()[-1][:200] if (done.stderr or done.stdout).strip() else 'Reset failed')


def _run(kind):
 error=None
 try:(_full if kind=='full' else _light)()
 except Exception as exc:error=str(exc)[:200] or type(exc).__name__
 with LOCK:
  if not error:SESSION['wrote']=False
  SESSION['reset'].update(running=False,error=error,finishedAt=time.time());save()


def start_reset():
 with LOCK:
  if SESSION['reset']['running']:return
  kind='full' if wrote_to_github() else 'light'
  SESSION['reset']={'running':True,'kind':kind,'startedAt':time.time(),'error':None}
 threading.Thread(target=_run,args=(kind,),daemon=True).start()


def enter(visitor):
 """A visitor opens the workspace. New visitors get the start state unless someone is mid-session."""
 visitor=touch(visitor)
 with LOCK:
  if visitor and visitor!=SESSION['holder'] and not SESSION['reset']['running']:
   if not dirty():SESSION['holder']=visitor;save()
   elif not holder_active():SESSION['holder']=visitor;save();start_reset()
 return view(visitor)


def leave(visitor):
 visitor=valid(visitor)
 with LOCK:
  if visitor and visitor==SESSION['holder']:
   SESSION['holder']=None;SESSION['seen'].pop(visitor,None);save()
   if dirty():start_reset()
 return {'left':True}


def reset(visitor):
 visitor=touch(visitor)
 with LOCK:
  if visitor:SESSION['holder']=visitor;save()
  start_reset()
 return view(visitor)


def view(visitor=None,state=None):
 state=state or service.client()
 with LOCK:
  r=SESSION['reset']
  state['session']={'resetting':r['running'],'resetKind':r['kind'] if r['running'] else None,'resetStartedAt':r['startedAt'] if r['running'] else None,'resetError':r['error'],'pristine':not r['running'] and not dirty(),'shared':bool(visitor) and holder_active() and SESSION['holder']!=visitor}
 return state


def watch():
 """Restore a used workspace that nobody is looking at any more."""
 while True:
  time.sleep(30)
  try:
   with LOCK:
    last=max([BOOT,*SESSION['seen'].values()])
    if not SESSION['reset']['running'] and time.time()-last>IDLE_SECONDS and dirty():
     SESSION['holder']=None;save();start_reset()
  except Exception:pass
