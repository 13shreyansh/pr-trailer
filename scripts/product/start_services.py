"""Keep the owned test worker and its tunnel alive through recording. No credentials in plists."""
import json
import os
from pathlib import Path
import plistlib
import re
import signal
import subprocess
import time
import urllib.request
ROOT=Path(__file__).resolve().parents[2];VAR=ROOT/'var';LAUNCH=VAR/'launch';LAUNCH.mkdir(exist_ok=True)
DOMAIN='gui/'+str(os.getuid())

def install(label,args,log):
 full='xyz.thecsguy.'+label
 subprocess.run(['launchctl','bootout',DOMAIN+'/'+full],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 config={'Label':full,'ProgramArguments':args,'WorkingDirectory':str(ROOT),'RunAtLoad':True,'KeepAlive':True,'EnvironmentVariables':{'PATH':os.environ['PATH'],'HOME':str(Path.home()),**({'TIETO_TUNNEL_MANAGED':'1'} if label=='tieto-worker' else {})},'StandardOutPath':str(VAR/(log+'.out.log')),'StandardErrorPath':str(VAR/(log+'.err.log'))}
 path=LAUNCH/(label+'.plist');path.write_bytes(plistlib.dumps(config));subprocess.run(['launchctl','bootstrap',DOMAIN,str(path)],check=True)

if __name__=='__main__':
 # Retire this run's foreground worker before handing its port to launchd.
 found=subprocess.run(['lsof','-tiTCP:4322','-sTCP:LISTEN'],capture_output=True,text=True)
 for pid in found.stdout.split():
  cmd=subprocess.check_output(['ps','-p',pid,'-o','args='],text=True)
  if 'product/server.py' not in cmd:raise RuntimeError('Port4322 belongs to another process')
  os.kill(int(pid),signal.SIGTERM)
 subprocess.run(['launchctl','bootout',DOMAIN+'/xyz.thecsguy.tieto-tunnel'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 origin_file=VAR/'runner-origin.txt'
 previous=origin_file.stat().st_mtime if origin_file.exists() else 0
 install('tieto-worker',[str(ROOT/'.venv312/bin/python'),'-u',str(ROOT/'product/server.py')],'worker')
 install('tieto-awake',['/usr/bin/caffeinate','-dimsu'],'awake')
 for attempt in range(50):
  if origin_file.exists() and origin_file.stat().st_mtime>previous:
   origin=origin_file.read_text().strip()
   try:
    result=json.load(urllib.request.urlopen('http://127.0.0.1:4322/health',timeout=5))
    if result['ready']:print('Persistent worker ready:',origin,flush=True);break
   except Exception:pass
  time.sleep(1)
 else:raise RuntimeError('Worker tunnel did not become ready')
