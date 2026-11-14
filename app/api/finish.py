from http.server import BaseHTTPRequestHandler
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from finish import execute

class handler(BaseHTTPRequestHandler):
 def do_POST(self):
  try:
   size=int(self.headers.get('Content-Length','0'))
   if size>2048:raise ValueError('Request too large')
   data=json.loads(self.rfile.read(size));result=execute(data.get('ids'));body=json.dumps(result).encode();self.send_response(200)
  except ValueError as exc:
   body=json.dumps({'error':str(exc)}).encode();self.send_response(400)
  except Exception as exc:
   print("Tieto fixed runner error:",type(exc).__name__,str(exc),file=sys.stderr,flush=True)
   body=json.dumps({'error':'Could not build the signed bank branch. Retry.'}).encode();self.send_response(500)
  self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
