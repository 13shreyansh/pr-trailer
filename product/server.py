"""HTTP worker. GitHub credentials are resolved only by the broker, never sent to the UI."""
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
import json
import os
import re
import subprocess
from pathlib import Path
import sys
import urllib.parse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from product import service,visitors
BOOT_COMMIT=(ROOT/'release-commit').read_text().strip() if (ROOT/'release-commit').is_file() else subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def static_asset(path):
 app=ROOT/'app'
 if path=='/build.json':return json.dumps({'commit':BOOT_COMMIT,'measured':True}).encode(),'application/json'
 if path=='/':name='index.html'
 elif path=='/workspace' or path.startswith('/workspace/'):name='workspace.html'
 elif path in ('/app.js','/review.js','/style.css','/landing.css','/snapshot.json'):name=path[1:]
 elif path.startswith('/fonts/') and Path(path).suffix in ('.woff2','.woff','.ttf'):name=path[1:]
 else:return None
 target=app/name
 if not target.resolve().is_relative_to(app.resolve()) or not target.is_file():return None
 if target.stat().st_size>5_000_000:return None
 content={'.html':'text/html; charset=utf-8','.js':'text/javascript','.css':'text/css','.json':'application/json','.woff2':'font/woff2','.woff':'font/woff','.ttf':'font/ttf'}[target.suffix]
 return target.read_bytes(),content

def publication_asset(id):
 match=re.fullmatch(r'asset-([a-f0-9]{40})-(style|build)',id)
 if not match:return None
 path=ROOT/'var/publications'/match[1]/('style.css' if match[2]=='style' else 'build.json')
 if not path.is_file():raise ValueError('Public asset not found')
 return path.read_bytes(),('text/css' if match[2]=='style' else 'application/json')

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def respond(self,status,value,content='application/json',headers=None):
  data=value if isinstance(value,bytes) else json.dumps(value).encode()
  self.send_response(status);self.send_header('Content-Type',content);self.send_header('Cache-Control','no-store')
  for k,v in (headers or {}).items():self.send_header(k,v)
  self.end_headers();self.wfile.write(data)
 def do_GET(self):
  url=urllib.parse.urlparse(self.path);query=urllib.parse.parse_qs(url.query)
  try:
   static=static_asset(url.path)
   if static:return self.respond(200,static[0],static[1])
   if url.path=='/health':return self.respond(200,{'ready':True,'repo':service.FULL,'commit':BOOT_COMMIT,'execution':os.environ.get('TIETO_TEST_RUNNER','local'),'runLogConfigured':bool(os.environ.get('MONGODB_URI')),'codeContextConfigured':bool(os.environ.get('ENTIRE_BIN') or os.environ.get('ENTIRE_GRAPH_BIN'))})
   visitor=visitors.touch(query.get('v',[''])[0])
   if url.path=='/api/workspace':return self.respond(200,visitors.view(visitor,service.client() if visitors.resetting() else service.sync(True)))
   if url.path=='/api/status':return self.respond(200,visitors.view(visitor))
   if url.path in ('/api/proof','/api/patch','/api/context','/api/run-log'):
    id=query.get('id',[''])[0]
    if url.path=='/api/patch':
     asset=publication_asset(id)
     if asset:return self.respond(200,asset[0],asset[1])
    with service.LOCK:p=service.STATE['prs'].get(id)
    if not p or not p.get('_root'):raise ValueError('Run the checks first')
    root=Path(p['_root'])
    if url.path=='/api/patch':return self.respond(200,(root/'trimmed.patch').read_bytes(),'text/plain',{'Content-Disposition':'attachment; filename="trimmed.patch"'})
    report=json.loads((root/'result.json').read_text())
    if url.path=='/api/context':
     from product.evidence_page import code_context_page
     return self.respond(200,code_context_page(p,report),'text/html; charset=utf-8')
    if url.path=='/api/run-log':
     from product.runlog import read_run
     return self.respond(200,read_run(report['runId']))
    return self.respond(200,service.compact(report))
   self.respond(404,{'error':'Not found'})
  except ValueError as exc:self.respond(400,{'error':str(exc)})
  except Exception as exc:self.respond(503,{'error':str(exc)[:200]})
 def do_POST(self):
  url=urllib.parse.urlparse(self.path)
  try:
   size=int(self.headers.get('Content-Length','0'))
   if size>10000:raise ValueError('Request too large')
   data=json.loads(self.rfile.read(size) or b'{}')
   if url.path=='/internal/reset' and self.client_address[0]=='127.0.0.1' and not self.headers.get('CF-Ray'):
    return self.respond(200,service.reset_state())
   visitor=visitors.touch(data.get('visitor'))
   sessions={'/api/enter':visitors.enter,'/api/leave':visitors.leave,'/api/reset':visitors.reset}
   if url.path in sessions:return self.respond(200,sessions[url.path](data.get('visitor')))
   routes={'/api/measure':lambda:service.start(data.get('ids'),fresh=data.get('fresh',False)),'/api/stop':service.stop,'/api/add':lambda:service.add(data.get('url','')),'/api/finish':lambda:service.finish(data.get('id')),'/api/return':lambda:service.send_back(data.get('id'),data.get('note')),'/api/block':lambda:service.block(data.get('id')),'/api/unblock':lambda:service.unblock(data.get('id')),'/api/revert':service.revert}
   if url.path not in routes:return self.respond(404,{'error':'Not found'})
   if url.path!='/api/stop':visitors.guard()
   if url.path in ('/api/finish','/api/return','/api/block','/api/unblock','/api/revert'):visitors.mark_write()
   self.respond(200,visitors.view(visitor,routes[url.path]()))
  except ValueError as exc:self.respond(400,{'error':str(exc)})
  except Exception as exc:self.respond(503,{'error':str(exc)[:200]})

if __name__=='__main__':
 from product.github import api,OWNER
 if api('/user')['login']!=OWNER:raise RuntimeError('Wrong workspace connection')
 server=ThreadingHTTPServer((os.environ.get('TIETO_BIND','127.0.0.1'),int(os.environ.get('PORT','4322'))),Handler)
 if __import__('os').environ.get('TIETO_TUNNEL_MANAGED')=='1':
  from product.tunnel import supervise
  __import__('threading').Thread(target=supervise,daemon=True).start()
 __import__('threading').Thread(target=visitors.watch,daemon=True).start()
 server.serve_forever()
