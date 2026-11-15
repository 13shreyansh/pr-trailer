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

