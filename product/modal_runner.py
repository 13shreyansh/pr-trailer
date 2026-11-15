"""Run fixed PR tests in credential-free, network-blocked Modal Sandboxes."""
from __future__ import annotations
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import time

MAX_SOURCE=20_000_000
MAX_FILES=15_000
IMAGE_REQUIREMENTS=("pytest==9.2.0", "pyserial==3.5")

# This trusted wrapper is kept outside the uploaded, read-only source tree.
REMOTE_RUNNER=r'''
import json,os,pathlib,resource,subprocess,sys,tarfile,tempfile,time,xml.etree.ElementTree as ET
root=pathlib.Path('/case/work');root.mkdir(parents=True,exist_ok=True)
with tarfile.open('/case/source.tar.gz','r:gz') as archive:
    total=0
    for member in archive:
        path=pathlib.PurePosixPath(member.name)
        if path.is_absolute() or '..' in path.parts or not member.isfile():
            raise ValueError('Unsafe source archive')
        total+=member.size
        if total>20_000_000:raise ValueError('Source limit exceeded')
        dest=root.joinpath(*path.parts);dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(archive.extractfile(member).read())
for path in root.rglob('*'):
    path.chmod(0o555 if path.is_dir() else 0o444)
root.chmod(0o555)
scratch=pathlib.Path('/case/tmp');scratch.mkdir();scratch.chmod(0o777)
request=json.loads(pathlib.Path('/case/request.json').read_text())
tests=request['tests']
if not tests or len(tests)>100 or any(not isinstance(t,str) or t.startswith(('/','-')) or '..' in pathlib.PurePosixPath(t.split('::')[0]).parts for t in tests):
    raise ValueError('Invalid fixed test paths')
report=scratch/'report.xml';output=scratch/'output.txt'
def limits():
    resource.setrlimit(resource.RLIMIT_CPU,(30,30))
    resource.setrlimit(resource.RLIMIT_FSIZE,(2_000_000,2_000_000))
    resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))
    resource.setrlimit(resource.RLIMIT_NPROC,(32,32))
    os.setgid(65534);os.setuid(65534)
env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':str(scratch),'TMPDIR':str(scratch),
     'PYTHONPATH':str(root/'src')+':'+str(root),'PYTHONDONTWRITEBYTECODE':'1',
     'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
command=['python','-B','-m','pytest','-q','-p','no:cacheprovider','--junitxml='+str(report),*tests]
started=time.monotonic()
with output.open('wb') as stream:
    try:
        process=subprocess.run(command,cwd=root,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=45,preexec_fn=limits)
        code=process.returncode
    except subprocess.TimeoutExpired:code=124
raw=output.read_bytes()[:131072];cases=[]
if report.is_file():
    for c in ET.fromstring(report.read_bytes()[:2_000_000]).iter('testcase'):
        bad=c.find('failure')
        if bad is None:bad=c.find('error')
        cases.append({'name':c.get('classname','')+'.'+c.get('name',''),'passed':bad is None and c.find('skipped') is None,
                      'skipped':c.find('skipped') is not None,'failure':'' if bad is None else (bad.text or '')[:4000]})
print(json.dumps({'exitCode':code,'seconds':round(time.monotonic()-started,4),'cases':cases,
                  'tests':len(cases),'passed':sum(c['passed'] for c in cases),
                  'output':raw.decode(errors='replace'),'outputTruncated':output.stat().st_size>len(raw)}))
'''

def source_archive(work: Path) -> bytes:
    """Only the fetched PR tree enters Modal; never the broker or process env."""
    output=io.BytesIO();count=total=0
    skipped={'.git','.env','.entire','.venv','.venv312','node_modules','__pycache__','.pytest_cache'}
    with tarfile.open(fileobj=output,mode='w:gz') as archive:
        for path in sorted(work.rglob('*')):
            rel=path.relative_to(work)
            if any(part in skipped or part.startswith('.env.') for part in rel.parts):continue
            if path.is_symlink():raise ValueError('Symlink source is unsupported')
            if not path.is_file():continue
            size=path.stat().st_size;total+=size;count+=1
            if total>MAX_SOURCE or count>MAX_FILES:raise ValueError('Repository too large for this runner')
            archive.add(path,arcname=rel.as_posix(),recursive=False)
    return output.getvalue()

def run_check(work, tests, log_dir, label, *, run_id=None, metadata=None, modal_module=None):
    if modal_module is None:
        import modal as modal_module
    if not os.environ.get('MODAL_TOKEN_ID') or not os.environ.get('MODAL_TOKEN_SECRET'):
        raise RuntimeError('Modal execution is not configured')
    raw=source_archive(Path(work));request={'tests':tests}
    app=modal_module.App.lookup(os.environ.get('MODAL_APP_NAME','pr-trailer-sandboxes'),create_if_missing=True)
    image=modal_module.Image.debian_slim(python_version='3.12').pip_install(*IMAGE_REQUIREMENTS)
    sandbox=None;started=time.monotonic()
    try:
        sandbox=modal_module.Sandbox.create('sleep','90',app=app,image=image,timeout=90,
                    cpu=1,memory=1024,block_network=True,include_oidc_identity_token=False)
        sandbox.filesystem.write_bytes(raw,'/case/source.tar.gz')
        sandbox.filesystem.write_text(REMOTE_RUNNER,'/case/runner.py')
        sandbox.filesystem.write_text(json.dumps(request),'/case/request.json')
        process=sandbox.exec('python','-I','/case/runner.py',timeout=65)
        text=process.stdout.read()
        status=process.wait()
        if status!=0 or len(text)>2_000_000:raise RuntimeError('Modal sandbox could not complete this check')
        result=json.loads(text)
        if not isinstance(result.get('cases'),list) or not isinstance(result.get('exitCode'),int):
            raise RuntimeError('Invalid sandbox result')
        result.update(label=label,command=['python','-B','-m','pytest','-q',*tests],measured=True,
                      outputSha256=hashlib.sha256(result['output'].encode()).hexdigest(),
                      execution={'provider':'modal','sandboxId':sandbox.object_id,
                                 'networkBlocked':True,'sourceReadOnly':True,
                                 'secretsInjected':False,'wallSeconds':round(time.monotonic()-started,4)})
        from .runlog import record_check
        result['archive']=record_check(run_id or Path(work).parent.name,label,result,metadata or {})
        log_dir=Path(log_dir);log_dir.mkdir(parents=True,exist_ok=True)
        (log_dir/(label+'.json')).write_text(json.dumps(result))
        return result
    except (ValueError,RuntimeError):raise
    except Exception:
        # Provider errors may include credential-bearing connection strings.
        raise RuntimeError('Modal execution unavailable; the check was not rerun locally') from None
    finally:
        if sandbox is not None:sandbox.terminate()

