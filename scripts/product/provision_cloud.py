"""Accept secrets over SSH stdin, persist only systemd-encrypted ciphertext, start own canary."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import uuid

BASE=Path('/opt/pr-trailer')
ALLOWED={'MODAL_TOKEN_ID','MODAL_TOKEN_SECRET','TIETO_GITHUB_TOKEN','MONGODB_URI','MONGODB_DATABASE'}

def main():
    os.umask(0o077)
    updates=json.load(sys.stdin)
    if set(updates)-ALLOWED:raise ValueError('Unexpected broker configuration')
    values={}
    if (BASE/'secrets.cred').exists():
        old=subprocess.run(['systemd-creds','decrypt','--name=pr-trailer',str(BASE/'secrets.cred'),'-'],capture_output=True,check=True)
        values=json.loads(old.stdout)
    values.update(updates)
    for name in ('MODAL_TOKEN_ID','MODAL_TOKEN_SECRET','TIETO_GITHUB_TOKEN'):
        if not values.get(name):raise ValueError('Required broker configuration is missing')
    BASE.mkdir(exist_ok=True)
    (BASE/'state').mkdir(exist_ok=True)
    encrypted=BASE/('secrets.cred.'+uuid.uuid4().hex)
    proc=subprocess.run(['systemd-creds','encrypt','--with-key=host','--name=pr-trailer','-',str(encrypted)],
                        input=json.dumps(values).encode(),capture_output=True)
    if proc.returncode:raise RuntimeError('Credential encryption failed')
    encrypted.chmod(0o600);encrypted.replace(BASE/'secrets.cred')
    unit='''[Unit]
Description=PR Trailer trusted canary broker
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
WorkingDirectory=/opt/pr-trailer/current
ExecStart=/opt/pr-trailer/venv/bin/python /opt/pr-trailer/current/scripts/product/cloud_boot.py
Restart=on-failure
RestartSec=3
UMask=0077
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=full
StandardOutput=journal
StandardError=journal
[Install]
WantedBy=multi-user.target
'''
    Path('/etc/systemd/system/pr-trailer-canary.service').write_text(unit)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','--now','pr-trailer-canary.service'],check=True,capture_output=True)
    subprocess.run(['systemctl','restart','pr-trailer-canary.service'],check=True)
    health=None
    for attempt in range(45):
        try:
            with urllib.request.urlopen('http://127.0.0.1:4326/health',timeout=3) as response:health=json.load(response)
            if health.get('ready'):break
        except Exception:time.sleep(1)
    if not health:raise RuntimeError('Canary health did not become ready')
    if not (BASE/'state/workspace.json').exists():
        # This touches only the validated, separately owned sponsor test repo.
        boot=BASE/'current/scripts/product/cloud_boot.py'
        subprocess.run([str(BASE/'venv/bin/python'),str(boot),'setup'],check=True)
    print(json.dumps({'service':'pr-trailer-canary','health':health,'encryptedAtRest':True,
                      'originalWorkerChanged':False}))

if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('Canary provisioning did not complete; inspect nonsecret service health') from None
