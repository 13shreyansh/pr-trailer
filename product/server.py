"""HTTP worker. GitHub credentials are resolved only by the broker, never sent to the UI."""
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
import json
import re
import subprocess
from pathlib import Path
import sys
import urllib.parse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from product import service
BOOT_COMMIT=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

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
   if url.path=='/health':return self.respond(200,{'ready':True,'repo':service.FULL,'commit':BOOT_COMMIT})
   if url.path=='/api/workspace':return self.respond(200,service.sync(True))
   if url.path=='/api/status':return self.respond(200,service.client())
   if url.path in ('/api/proof','/api/patch'):
    id=query.get('id',[''])[0]
    if url.path=='/api/patch':
     asset=publication_asset(id)
     if asset:return self.respond(200,asset[0],asset[1])
    with service.LOCK:p=service.STATE['prs'].get(id)
    if not p or not p.get('_root'):raise ValueError('Run the checks first')
    root=Path(p['_root'])
    if url.path=='/api/patch':return self.respond(200,(root/'trimmed.patch').read_bytes(),'text/plain',{'Content-Disposition':'attachment; filename="trimmed.patch"'})
    return self.respond(200,service.compact(json.loads((root/'result.json').read_text())))
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
   routes={'/api/measure':lambda:service.start(data.get('ids')),'/api/stop':service.stop,'/api/add':lambda:service.add(data.get('url','')),'/api/finish':lambda:service.finish(data.get('id')),'/api/return':lambda:service.send_back(data.get('id'),data.get('note')),'/api/block':lambda:service.block(data.get('id')),'/api/unblock':lambda:service.unblock(data.get('id')),'/api/revert':service.revert}
   if url.path not in routes:return self.respond(404,{'error':'Not found'})
   self.respond(200,routes[url.path]())
  except ValueError as exc:self.respond(400,{'error':str(exc)})
  except Exception as exc:self.respond(503,{'error':str(exc)[:200]})

if __name__=='__main__':
 from product.github import api,OWNER
 if api('/user')['login']!=OWNER:raise RuntimeError('Wrong workspace connection')
 server=ThreadingHTTPServer(('127.0.0.1',4322),Handler)
 if __import__('os').environ.get('TIETO_TUNNEL_MANAGED')=='1':
  from product.tunnel import supervise
  __import__('threading').Thread(target=supervise,daemon=True).start()
 server.serve_forever()
