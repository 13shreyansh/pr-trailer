"""Decrypt the trusted broker configuration directly into memory, never an env file."""
import json
import os
from pathlib import Path
import subprocess
import sys

BASE=Path('/opt/pr-trailer')
ALLOWED={'MODAL_TOKEN_ID','MODAL_TOKEN_SECRET','TIETO_GITHUB_TOKEN','MONGODB_URI','MONGODB_DATABASE'}

def configuration():
    done=subprocess.run(['systemd-creds','decrypt','--name=pr-trailer',str(BASE/'secrets.cred'),'-'],
                        capture_output=True,check=True)
    values=json.loads(done.stdout)
    if set(values)-ALLOWED:raise ValueError('Unexpected broker configuration')
    for name in ('MODAL_TOKEN_ID','MODAL_TOKEN_SECRET','TIETO_GITHUB_TOKEN'):
        if not values.get(name):raise ValueError('Required broker configuration is missing')
    return {k:str(v) for k,v in values.items()}

if __name__=='__main__':
    try:values=configuration()
    except Exception:raise SystemExit('Encrypted broker configuration is unavailable') from None
    os.environ.update(values)
    os.environ.update(TIETO_BIND='127.0.0.1',PORT='4326',TIETO_TEST_RUNNER='modal',
                      TIETO_WORKSPACE_REPO='tieto-nordbank-payments-sponsors',
                      TIETO_WORKSPACE_CONFIG=str(BASE/'state/workspace.json'),
                      TIETO_STATE_DIR=str(BASE/'state/product'),
                      ENTIRE_GRAPH_BIN=str(BASE/'bin/entire-graph'),
                      TIETO_RUNLOG_OUTBOX=str(BASE/'state/runlog.sqlite'),
                      XDG_CACHE_HOME=str(BASE/'state/cache'))
    current=BASE/'current'
    os.chdir(current)
    command=[sys.executable,'-m','product.server']
    if len(sys.argv)>1 and sys.argv[1]=='setup':command=[sys.executable,str(current/'scripts/product/workspace.py'),'setup']
    os.execvpe(sys.executable,command,os.environ)

