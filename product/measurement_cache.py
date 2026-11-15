"""Reuse completed, source-identical Modal measurements without inventing a new test run."""
import ast
import hashlib
import importlib.metadata
import json
import re
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
    return {'contractSchema':2,'measurementLogicSha256':hashlib.sha256(ast.dump(next(n for n in ast.parse((ROOT/'product/service.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='measure')).encode()).hexdigest(),'engineSha256':hashlib.sha256((ROOT/'scripts/measure/engine.py').read_bytes()).hexdigest(),
            'riskLogicSha256':risk_fingerprint((ROOT/'product/service.py').read_text()),
            'adapterSha256':hashlib.sha256((ROOT/'product/modal_runner.py').read_bytes()).hexdigest(),
            'contextSha256':hashlib.sha256((ROOT/'product/provenance.py').read_bytes()).hexdigest(),
            'runnerSha256':hashlib.sha256(REMOTE_RUNNER.encode()).hexdigest(),
            'image':{'python':'3.12','pip':list(IMAGE_REQUIREMENTS),'modalSdk':importlib.metadata.version('modal'),
                     'networkBlocked':True,'cpu':1,'memoryMiB':1024,'secretsInjected':False}}

def contract(row,base_sha,config):
    tests=list(config['tests']) if config else ['tests']
    if config and row['kind']!='junior':tests.append('tests')
    return {'schema':2,'repo':row['repo'],'headSha':row['headSha'],'baseSha':base_sha,'ask':row['ask'],
            'caseId':row.get('id'),'paths':row['paths'],'tests':tests,
            'wholePaths':config.get('wholePaths',[]) if config else [],'kind':row['kind'],
            'outside':bool(row.get('outside')),'heldOutTests':['oracle/test_cap_rounding.py'] if row['kind']=='cap' else [],
            'profile':profile()}

def key(row,base_sha,config):
    return hashlib.sha256(json.dumps(contract(row,base_sha,config),sort_keys=True,separators=(',',':')).encode()).hexdigest()

def _completed(report,row,base_sha,config=None):
    expected=contract(row,base_sha,config);final=report.get('final',{})
    # Legacy reports lack producer-side request/invocation/release attestation. Never infer it from today's row.
    if report.get('measurementContract')!=expected or not re.fullmatch('[0-9a-f]{40}',str(report.get('producerRelease',''))):return False
    checks=[*report.get('runs',[]),*report.get('controls',[]),final]
    if not checks or not report.get('runs'):return False
    def actual(check,tests):
        return (check.get('command')==['python','-B','-m','pytest','-q',*tests]
                and check.get('execution',{}).get('provider')=='modal'
                and check.get('execution',{}).get('runnerSha256')==expected['profile']['runnerSha256']
                and isinstance(check.get('exitCode'),int))
    if any(not actual(check,expected['tests']) for check in checks):return False
    if expected['heldOutTests'] and not actual(report.get('heldOut',{}),expected['heldOutTests']):return False
    return (report.get('repo')==row['repo'] and report.get('headSha')==row['headSha'] and report.get('baseSha')==base_sha
            and bool(report.get('measuredAt')) and final.get('exitCode')==0
            and isinstance(final.get('tests'),int) and final['tests']>0
            and isinstance(final.get('passed'),int) and final['passed']==final['tests']
            and 'blocks' in report and 'patch' in report and 'controls' in report)

def store(folder,row,base_sha,config,measured_row,*,origin_commit=None):
    root=Path(measured_row['_root']).resolve();runs=(Path(folder).parent/'runs').resolve()
    if not root.is_relative_to(runs):raise ValueError('Measurement root is outside the owned run store')
    report=json.loads((root/'result.json').read_text())
    if not _completed(report,row,base_sha,config):return False
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
        if hashlib.sha256(raw).hexdigest()!=data['resultSha256'] or not _completed(report,row,base_sha,config):return None
        return {**snapshot,'cachedMeasurement':True,'measurementOriginNumber':data['originNumber'],
                'measurementOriginAt':data['originMeasuredAt'],'measurementOriginHead':report['headSha'],'testsRun':0}
    except (OSError,ValueError,KeyError,TypeError):return None

