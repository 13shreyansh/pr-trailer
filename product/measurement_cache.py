"""Reuse completed, source-identical Modal measurements without inventing a new test run."""
import ast
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time

ROOT=Path(__file__).resolve().parents[1]
FIELDS=('verdict','written','kept','unchecked','tests','passed','blocks','risk','readLines','lampFiles',
        'neededFailures','riskPosition','measuredAt','baseSha','patchSha256','runId','executionProvider','codeContext','_root')

def risk_fingerprint(source):
    tree=ast.parse(source)
    logic='\n'.join(ast.dump(node) for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ('find_risks','position'))
    return hashlib.sha256(logic.encode()).hexdigest()

def profile():
    from .modal_runner import REMOTE_RUNNER,IMAGE_REQUIREMENTS
    return {'engineSha256':hashlib.sha256((ROOT/'scripts/measure/engine.py').read_bytes()).hexdigest(),
            'riskLogicSha256':risk_fingerprint((ROOT/'product/service.py').read_text()),
            'adapterSha256':hashlib.sha256((ROOT/'product/modal_runner.py').read_bytes()).hexdigest(),
            'contextSha256':hashlib.sha256((ROOT/'product/provenance.py').read_bytes()).hexdigest(),
            'runnerSha256':hashlib.sha256(REMOTE_RUNNER.encode()).hexdigest(),
            'image':{'python':'3.12','pip':list(IMAGE_REQUIREMENTS),'modalSdk':importlib.metadata.version('modal'),
                     'networkBlocked':True,'cpu':1,'memoryMiB':1024,'secretsInjected':False}}

def key(row,base_sha,config):
    contract={'repo':row['repo'],'headSha':row['headSha'],'baseSha':base_sha,'ask':row['ask'],
              'paths':row['paths'],'tests':config['tests'] if config else ['tests'],
              'wholePaths':config.get('wholePaths',[]) if config else [],'kind':row['kind'],'profile':profile()}
    return hashlib.sha256(json.dumps(contract,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def _completed(report,row,base_sha):
    final=report.get('final',{})
    return (report.get('repo')==row['repo'] and report.get('headSha')==row['headSha'] and report.get('baseSha')==base_sha
            and bool(report.get('measuredAt')) and report.get('final',{}).get('exitCode')==0
            and isinstance(final.get('tests'),int) and final['tests']>0
            and isinstance(final.get('passed'),int) and final['passed']==final['tests']
            and report.get('final',{}).get('execution',{}).get('provider')=='modal'
            and report.get('final',{}).get('execution',{}).get('runnerSha256')==profile()['runnerSha256']
            and 'blocks' in report and 'patch' in report and 'controls' in report)

def store(folder,row,base_sha,config,measured_row,*,origin_commit=None):
    root=Path(measured_row['_root']).resolve();runs=(Path(folder).parent/'runs').resolve()
    if not root.is_relative_to(runs):raise ValueError('Measurement root is outside the owned run store')
    report=json.loads((root/'result.json').read_text())
    if not _completed(report,row,base_sha):return False
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    data={'key':key(row,base_sha,config),'created':time.time(),'profile':profile(),
          'originCommit':origin_commit,'originNumber':report['number'],'originMeasuredAt':report['measuredAt'],
          'resultSha256':hashlib.sha256((root/'result.json').read_bytes()).hexdigest(),
          'row':{k:measured_row[k] for k in FIELDS if k in measured_row}}
    target=folder/(data['key']+'.json');temp=target.with_suffix('.tmp');temp.write_text(json.dumps(data));temp.replace(target)
    return True

def load(folder,row,base_sha,config):
    try:
        target=Path(folder)/(key(row,base_sha,config)+'.json');data=json.loads(target.read_text())
        if time.time()-data['created']>86400 or data['profile']!=profile():return None
        snapshot=data['row'];root=Path(snapshot['_root']).resolve();runs=(Path(folder).parent/'runs').resolve()
        if not root.is_relative_to(runs):return None
        raw=(root/'result.json').read_bytes();report=json.loads(raw)
        if hashlib.sha256(raw).hexdigest()!=data['resultSha256'] or not _completed(report,row,base_sha):return None
        return {**snapshot,'cachedMeasurement':True,'measurementOriginNumber':data['originNumber'],
                'measurementOriginAt':data['originMeasuredAt'],'measurementOriginHead':report['headSha'],'testsRun':0}
    except (OSError,ValueError,KeyError,TypeError):return None

