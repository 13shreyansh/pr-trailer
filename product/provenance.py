"""Entire Graph supplies deterministic code context for a measured public PR."""
import json
import os
from pathlib import Path
import shutil
import subprocess

def code_context(source,ask,head_sha):
    binary=os.environ.get('ENTIRE_BIN') or shutil.which('entire')
    if not binary:return {'provider':'entire-graph','available':False,'reason':'Code context is not configured'}
    command=[binary,'graph','query','--repo',str(Path(source).resolve()),'--profile','full',
             '--format','json','--max-context-bytes','12000','--top-k','6','--query',str(ask)[:1000]]
    try:
        source=Path(source).resolve()
        if not (source/'.git').exists():
            # Downloaded GitHub archives have no .git directory. Build a local
            # analysis snapshot, without hooks, global filters, signing or egress.
            env={k:os.environ[k] for k in ('PATH','HOME','TMPDIR') if k in os.environ}
            env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null')
            for args in [('init','-q'),('add','--all'),('-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false',
                         '-c','user.name=PR Trailer analysis','-c','user.email=analysis@pr-trailer.invalid',
                         'commit','-q','--allow-empty','-m','Analysis snapshot of public source '+str(head_sha)[:40])]:
                subprocess.run(['git','-C',str(source),*args],check=True,capture_output=True,timeout=15,env=env)
        response=subprocess.run(command,cwd=source,capture_output=True,text=True,timeout=30,
                   env={k:os.environ[k] for k in ('PATH','HOME','TMPDIR','XDG_CACHE_HOME') if k in os.environ})
        if response.returncode or len(response.stdout)>100_000:raise ValueError()
        graph=json.loads(response.stdout);symbols=[]
        for item in graph.get('results',[])[:6]:
            path=Path(item.get('file_path',''))
            if path.is_absolute() or '..' in path.parts or not str(path):continue
            symbols.append({'path':path.as_posix(),'line':int(item.get('start_line',1)),
                            'name':str(item.get('symbol_name') or item.get('kind') or 'source')[:160],
                            'kind':str(item.get('kind',''))[:50],
                            'relations':[str(s)[:80] for s in item.get('signals',[]) if str(s).startswith('graph:')][:8]})
        return {'provider':'entire-graph','available':True,'sourceHead':head_sha,
                'query':str(ask)[:1000],'symbols':symbols,
                'notice':'Static code context helps review. Missing relationships do not prove a function is unused.'}
    except Exception:
        return {'provider':'entire-graph','available':False,'reason':'Code context could not be generated for this repository'}

