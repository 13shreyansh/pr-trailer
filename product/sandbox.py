"""Seatbelt plus OS resource limits isolate public PR tests from the credential broker."""
import hashlib
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/measure'))
import engine
from .scratch import volume


def profile(root,scratch):
 root=root.resolve();root.mkdir(parents=True,exist_ok=True)
 allowed=[root,scratch,ROOT/'.venv312',ROOT/'.tools/python',Path(sys.base_prefix),Path('/System'),Path('/usr'),Path('/bin'),Path('/sbin'),Path('/Library/Apple'),Path('/private/etc'),Path('/dev')]
 rules=['(version 1)','(deny default)','(allow process-exec)','(allow process-fork)','(allow sysctl-read)','(allow signal (target self))','(allow mach-lookup (global-name "com.apple.system.logger"))','(allow file-read* (literal "/"))']
 rules+=['(allow file-read* (subpath '+json.dumps(str(p))+'))' for p in allowed]
 # Source checkouts and the broker remain read-only. Only bounded scratch is writable.
 rules+=['(allow file-write* (subpath '+json.dumps(str(scratch))+'))','(allow file-write* (literal "/dev/null"))']
 p=root/'runner.sb';p.write_text('\n'.join(rules)+'\n');return p


def runner(root,metadata=None):
 if os.environ.get('TIETO_TEST_RUNNER')=='modal':
  from .modal_runner import run_check
  return lambda work,tests,log_dir,label:run_check(work,tests,log_dir,label,run_id=root.name,metadata=metadata)
 root=root.resolve();scratch=volume()/hashlib.sha256(str(root).encode()).hexdigest()[:20];scratch.mkdir(exist_ok=True);tmp=scratch/'tmp';tmp.mkdir(exist_ok=True);logs=scratch/'logs';logs.mkdir(exist_ok=True);policy=profile(root,scratch)
 def check(work,tests,log_dir,label):
  output=scratch/('stdout-'+label+'.txt')
  # Limits apply only to the child. No forks, bounded per-file writes and CPU time.
  prefix=['/bin/sh','-c','ulimit -u 0; ulimit -f 4096; ulimit -t 30; ulimit -n 128; exec "$@" > "$TIETO_TEST_STDOUT" 2>&1','tieto-check','/usr/bin/sandbox-exec','-f',str(policy)]
  result=engine.run_check(work,tests,logs,label,python=str(Path(sys.executable).resolve()),command_prefix=prefix,env_overrides={'HOME':str(tmp),'TMPDIR':str(tmp),'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','TIETO_TEST_STDOUT':str(output)})
  if output.exists():
   with output.open('rb') as stream:raw=stream.read(2_000_000)
   result['output']=raw.decode(errors='replace');result['outputSha256']=engine.digest(raw);result['outputTruncated']=output.stat().st_size>len(raw)
  (logs/(label+'.json')).write_text(json.dumps(result))
  return result
 return check
