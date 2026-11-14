"""GitHub broker. Credentials stay in process memory and only the owned workspace is writable."""
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import urllib.error
import urllib.parse
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
OWNER='13shreyansh'
REPO='tieto-nordbank-payments'
FULL=OWNER+'/'+REPO
_lock=threading.Lock()
_token=None


def credential():
 global _token
 if _token:return _token
 with _lock:
  if not _token:
   proc=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',capture_output=True,text=True,cwd=ROOT,env={**os.environ,'GIT_TERMINAL_PROMPT':'0'})
   data=dict(x.split('=',1) for x in proc.stdout.splitlines() if '=' in x)
   if 'password' not in data:raise RuntimeError('GitHub connection unavailable')
   _token=data['password']
 return _token


def parse_pr(url):
 try:
  p=urllib.parse.urlparse(url.strip())
  match=re.fullmatch(r'/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/pull/([1-9][0-9]*)/?',p.path)
  if p.scheme!='https' or p.netloc!='github.com' or p.query or p.fragment or not match:raise ValueError()
  owner,repo,number=match.groups()
  if owner in ('.','..') or repo in ('.','..'):raise ValueError()
  return owner+'/'+repo,int(number)
 except Exception:raise ValueError('Not a public PR link.')


def api(path,method='GET',data=None,create_repo=False):
 if method!='GET' and not ((path.startswith('/repos/'+FULL+'/') or path=='/repos/'+FULL) or create_repo and path=='/user/repos'):
  raise ValueError('Writes are restricted to the Nordbank payments repository')
 req=urllib.request.Request('https://api.github.com'+path,data=json.dumps(data).encode() if data is not None else None,method=method,headers={'Authorization':'Bearer '+credential(),'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'Tieto-earned-review','Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=35) as response:
   raw=response.read();return json.loads(raw) if raw else {}
 except urllib.error.HTTPError as exc:
  raw=exc.read()
  try:message=json.loads(raw).get('message','request failed')
  except Exception:message='request failed'
  raise RuntimeError(f'GitHub {exc.code}: {message}') from None


def pages(path):
 out=[];page=1
 while True:
  rows=api(path+('&' if '?' in path else '?')+f'per_page=100&page={page}')
  out.extend(rows)
  if len(rows)<100:return out
  page+=1


def commit_tree(files,parent=None,message='Agent-prepared change'):
 tree=api(f'/repos/{FULL}/git/trees',method='POST',data={'tree':[{'path':p,'mode':'100644','type':'blob','content':v} if v is not None else {'path':p,'mode':'100644','type':'blob','sha':None} for p,v in files.items()],**({'base_tree':api(f'/repos/{FULL}/git/commits/{parent}')['tree']['sha']} if parent else {})})
 return api(f'/repos/{FULL}/git/commits',method='POST',data={'message':message,'tree':tree['sha'],'parents':[parent] if parent else []})['sha']


def set_ref(branch,sha,force=True):
 try:api(f'/repos/{FULL}/git/refs/heads/{branch}',method='PATCH',data={'sha':sha,'force':force})
 except RuntimeError as exc:
  if not ('404' in str(exc) or '422: Reference does not exist' in str(exc)):raise
  api(f'/repos/{FULL}/git/refs',method='POST',data={'ref':'refs/heads/'+branch,'sha':sha})
