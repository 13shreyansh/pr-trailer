"""Supervise the worker's tunnel and publish its public routing address on an owned branch."""
from pathlib import Path
import json
import os
import re
import subprocess
import time
import urllib.request
from .github import api,commit_tree,set_ref,FULL,ROOT

def publish(origin):
 try:parent=api('/repos/'+FULL+'/git/ref/heads/tieto/connection')['object']['sha']
 except RuntimeError:parent=json.loads((ROOT/'var/workspace.json').read_text())['baseline']
 sha=commit_tree({'.tieto/connection.json':json.dumps({'origin':origin,'updatedAt':time.time()})+'\n'},parent=parent,message='Update public Tieto worker routing')
 set_ref('tieto/connection',sha);(ROOT/'var/runner-origin.txt').write_text(origin+'\n')


def supervise(restart=True):
 log=ROOT/'var/tunnel-managed.log'
 while True:
  with log.open('a') as stream:
   process=subprocess.Popen([str(Path.home()/'.local/bin/cloudflared'),'tunnel','--url','http://127.0.0.1:4322','--no-autoupdate','--protocol','http2','--edge-ip-version','4'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1,cwd=ROOT,env={k:os.environ[k] for k in ('PATH','HOME','TMPDIR') if k in os.environ})
   (ROOT/'var/tunnel-managed.pid').write_text(str(process.pid))
   published=False;origin=None
   for line in process.stdout:
    stream.write(line);stream.flush()
    match=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',line)
    if match:origin=match[0]
    if origin and 'Registered tunnel connection' in line and not published:
     try:publish(origin);published=True;print('Public worker routing published.',flush=True)
     except Exception as exc:print('Worker route could not be published:',type(exc).__name__,flush=True)
   code=process.wait();print('Worker tunnel reconnecting after exit',code,flush=True)
  if not restart:return
  time.sleep(3)
