"""Stage an exact, nonsecret Git archive on the existing VPS; do not change the public route."""
import json
from pathlib import Path
import re
import shlex
import subprocess

ROOT=Path(__file__).resolve().parents[2]
HOST='root@72.61.22.106'

REMOTE_SETUP=r'''
import hashlib,io,json,os,pathlib,platform,subprocess,tarfile,urllib.request
base=pathlib.Path('/opt/pr-trailer');(base/'bin').mkdir(parents=True,exist_ok=True);(base/'state').mkdir(exist_ok=True)
venv=base/'venv'
if not (venv/'bin/python').exists():
    first=subprocess.run(['python3','-m','venv',str(venv)],capture_output=True)
    if first.returncode:
        subprocess.run(['apt-get','update','-qq'],check=True,stdout=subprocess.DEVNULL)
        subprocess.run(['apt-get','install','-y','-qq','python3.12-venv'],check=True,stdout=subprocess.DEVNULL,env={**os.environ,'DEBIAN_FRONTEND':'noninteractive'})
        subprocess.run(['python3','-m','venv',str(venv)],check=True)
subprocess.run([str(venv/'bin/python'),'-m','pip','install','--disable-pip-version-check','-q','-r',str(base/'current/app/requirements.txt')],check=True)
version='0.6.0';arch='arm64' if platform.machine()=='aarch64' else 'amd64'
name=f'entire-graph_{version}_linux_{arch}.tar.gz'
origin=f'https://github.com/entireio/entire-graph/releases/download/v{version}/'
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'PR-Trailer-build'}),timeout=60) as response:return response.read(100_000_000)
checksums=get(origin+'checksums.txt').decode();expected=next(line.split()[0] for line in checksums.splitlines() if line.split()[-1].lstrip('*')==name)
raw=get(origin+name)
if hashlib.sha256(raw).hexdigest()!=expected:raise RuntimeError('Entire Graph release checksum mismatch')
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
    member=next(m for m in archive if pathlib.PurePosixPath(m.name).name=='entire-graph' and m.isfile())
    executable=base/'bin/entire-graph';executable.write_bytes(archive.extractfile(member).read());executable.chmod(0o755)
print(json.dumps({'stagedCommit':(base/'current/release-commit').read_text().strip(),'graphVersion':version,'graphChecksum':expected,'credentialsWritten':False}))
'''

def main():
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if not re.fullmatch('[0-9a-f]{40}',commit):raise RuntimeError('Invalid source commit')
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip():
        raise RuntimeError('Commit tracked changes before staging the canary')
    target='/opt/pr-trailer/releases/'+commit
    command='mkdir -p '+shlex.quote(target)+' && tar -xzf - -C '+shlex.quote(target)+' && printf %s '+shlex.quote(commit)+' > '+shlex.quote(target+'/release-commit')+' && ln -sfn '+shlex.quote(target)+' /opt/pr-trailer/current'
    archive=subprocess.Popen(['git','archive','--format=tar.gz',commit],cwd=ROOT,stdout=subprocess.PIPE)
    delivered=subprocess.run(['ssh','-o','BatchMode=yes',HOST,command],stdin=archive.stdout,capture_output=True)
    archive.stdout.close()
    if archive.wait() or delivered.returncode:raise RuntimeError('Source staging failed')
    done=subprocess.run(['ssh','-o','BatchMode=yes',HOST,'python3','-'],input=REMOTE_SETUP.encode(),capture_output=True)
    if done.returncode:
        # This setup process contains no secrets; bounded diagnostics aid repair.
        print(done.stderr.decode()[-2500:]);raise RuntimeError('Canary dependency installation failed')
    receipt=json.loads(done.stdout.decode().splitlines()[-1])
    (ROOT/'evidence/cloud-staging.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__=='__main__':main()
