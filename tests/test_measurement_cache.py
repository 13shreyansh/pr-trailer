import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from product import measurement_cache as cache

class VerifiedMeasurementCacheTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.run=self.root/'runs/run';self.run.mkdir(parents=True)
  self.folder=self.root/'verified';self.row={'repo':'owner/repo','headSha':'a'*40,'ask':'Cap fees','paths':['fee.py'],'kind':'cap','id':'cap','outside':False}
  self.config={'tests':['oracle/test_fee.py'],'wholePaths':['fee.py']};self.base='b'*40
  self.report={'repo':'owner/repo','headSha':'a'*40,'baseSha':self.base,'number':7,'measuredAt':'2026-11-15T06:49:00Z',
    'final':{'exitCode':0,'tests':9,'passed':9,'execution':{'provider':'modal','runnerSha256':cache.profile()['runnerSha256']}},
    'heldOut':{'exitCode':1,'passed':0,'tests':1},'blocks':[],'controls':[],'patch':'public patch'}
  self.report['measurementContract']=cache.contract(self.row,self.base,self.config)
  self.report['producerRelease']='a'*40
  self.report['final']['command']=['python','-B','-m','pytest','-q','oracle/test_fee.py','tests']
  self.report['runs']=[copy.deepcopy(self.report['final'])]
  self.report['heldOut'].update(command=['python','-B','-m','pytest','-q','oracle/test_cap_rounding.py'],execution=copy.deepcopy(self.report['final']['execution']))
  (self.run/'result.json').write_text(json.dumps(self.report))
  self.snapshot={'_root':str(self.run),'verdict':'needs-you','measuredAt':self.report['measuredAt'],'runId':'run','tests':9,'passed':9,'risk':[{'note':'Known rounding failure'}]}
 def tearDown(self):self.temp.cleanup()
 def store(self):return cache.store(self.folder,self.row,self.base,self.config,self.snapshot)
 def test_completed_result_reuse_preserves_original_time_source_and_known_failure(self):
  self.assertTrue(self.store());row=cache.load(self.folder,self.row,self.base,self.config)
  self.assertEqual(row['measurementOriginNumber'],7);self.assertEqual(row['measurementOriginAt'],self.report['measuredAt'])
  self.assertEqual(row['measurementOriginHead'],'a'*40);self.assertEqual(row['verdict'],'needs-you');self.assertEqual(row['testsRun'],0)
  self.assertEqual(json.loads((self.run/'result.json').read_text())['heldOut']['passed'],0)
 def test_any_source_test_or_image_profile_change_invalidates_reuse(self):
  self.store()
  for field,value in [('headSha','c'*40),('paths',['other.py']),('ask','Different requirement')]:
   row={**self.row,field:value};self.assertIsNone(cache.load(self.folder,row,self.base,self.config))
  self.assertIsNone(cache.load(self.folder,self.row,'c'*40,self.config))
  self.assertIsNone(cache.load(self.folder,self.row,self.base,{**self.config,'tests':['different/test.py']}))
  original=cache.profile()
  for field in ['engineSha256','riskLogicSha256','adapterSha256','contextSha256','runnerSha256','image']:
   changed={**original,field:'changed'}
   with patch.object(cache,'profile',return_value=changed):self.assertIsNone(cache.load(self.folder,self.row,self.base,self.config))
 def test_partial_failed_or_tampered_results_are_never_reused(self):
  self.report['final']['exitCode']=None;(self.run/'result.json').write_text(json.dumps(self.report));self.assertFalse(self.store())
  self.report['final']['exitCode']=1;(self.run/'result.json').write_text(json.dumps(self.report));self.assertFalse(self.store())
  self.report['final']['exitCode']=0;(self.run/'result.json').write_text(json.dumps(self.report));self.store()
  self.report['heldOut']['passed']=1;(self.run/'result.json').write_text(json.dumps(self.report));self.assertIsNone(cache.load(self.folder,self.row,self.base,self.config))
 def test_legacy_and_same_source_different_contract_are_declined_at_store(self):
  for missing in ['measurementContract','producerRelease']:
   report=copy.deepcopy(self.report);report.pop(missing);(self.run/'result.json').write_text(json.dumps(report));self.assertFalse(self.store())
  (self.run/'result.json').write_text(json.dumps(self.report))
  for field,value in [('ask','Different ask'),('paths',['different.py']),('id','another'),('kind','outside')]:
   self.assertFalse(cache.store(self.folder,{**self.row,field:value},self.base,self.config,self.snapshot))
  self.assertFalse(cache.store(self.folder,self.row,self.base,{**self.config,'tests':['different.py']},self.snapshot))
 def test_actual_invocation_default_suite_and_heldout_must_match(self):
  for location in ['final','heldOut']:
   report=copy.deepcopy(self.report);report[location]['command']=['python','-B','-m','pytest','-q','different.py'];(self.run/'result.json').write_text(json.dumps(report));self.assertFalse(self.store())
  report=copy.deepcopy(self.report);report['runs'][0]['command'].remove('tests');(self.run/'result.json').write_text(json.dumps(report));self.assertFalse(self.store())
  report=copy.deepcopy(self.report);report.pop('heldOut');(self.run/'result.json').write_text(json.dumps(report));self.assertFalse(self.store())
 def test_cached_measurement_does_not_allocate_runs_or_require_execution_disk(self):
  from product import service
  original=copy.deepcopy(service.STATE)
  try:
   row={**self.row,'number':1};service.STATE.clear();service.STATE.update(prs={'cap':row},batch=None)
   with patch.object(service,'save'),patch.object(service.STOP,'is_set',return_value=False),patch.object(service,'api',side_effect=[{'head':{'sha':self.row['headSha']},'base':{'sha':self.base}},{'merge_base_commit':{'sha':self.base}}]),patch.object(service,'known_cases',return_value={'cap':self.config}),patch.dict('os.environ',{'TIETO_TEST_RUNNER':'modal'}),patch.object(cache,'load',return_value={'_root':str(self.run)}),patch.object(service.shutil,'disk_usage',side_effect=AssertionError('cache must not check execution capacity')),patch.object(Path,'mkdir',side_effect=AssertionError('cache must not create directory')):
    service.measure('cap',True)
   self.assertEqual(service.STATE['prs']['cap']['status'],'done')
  finally:service.STATE.clear();service.STATE.update(original)
 def test_sync_keeps_sibling_measurement_when_main_advances(self):
  from product import service
  original=copy.deepcopy(service.STATE)
  try:
   row={**self.row,'id':'CAP','number':1,'outside':False,'status':'done','github':'https://example/pr/1','targetSha':'old','updatedAt':'before','baseSha':self.base}
   service.STATE.clear();service.STATE.update(prs={'CAP':row},batch=None)
   updated={**row,'targetSha':'new-sibling-merge','updatedAt':'after','status':'unmeasured'}
   with patch.object(service,'save'),patch.object(service,'client',return_value={}),patch.object(service,'known_cases',return_value={'CAP':self.config}),patch.object(service,'pages',return_value=[{'body':'<!-- tieto:case:CAP -->','number':1}]),patch.object(service,'fetch_pr',side_effect=lambda *args:updated if args[1]==1 else {**updated,'id':'outside-'+str(args[1]),'outside':True}):
    service.sync(True)
   self.assertEqual(service.STATE['prs']['CAP']['status'],'done');self.assertEqual(service.STATE['prs']['CAP']['baseSha'],self.base);self.assertEqual(service.STATE['prs']['CAP']['targetSha'],'new-sibling-merge')
  finally:service.STATE.clear();service.STATE.update(original)
 def test_explicit_bulk_rerun_selects_done_rows_and_forces_fresh_provider(self):
  from product import service
  original=copy.deepcopy(service.STATE)
  try:
   service.STATE.clear();service.STATE.update(prs={'one':{'id':'one','status':'done'},'two':{'id':'two','status':'done'}},batch=None)
   with patch.object(service,'save'),patch.object(service,'client',return_value={}),patch.object(service.POOL,'submit') as submit:
    service.start(fresh=True);self.assertEqual(submit.call_count,2)
    self.assertEqual([c.args for c in submit.call_args_list],[(service.measure,'one',False),(service.measure,'two',False)])
   for invalid in [1,'true',None,{}]:
    with self.assertRaises(ValueError):service.start(fresh=invalid)
  finally:service.STATE.clear();service.STATE.update(original)
 def test_explicit_rerun_is_always_submitted_with_reuse_disabled(self):
  from product import service
  original=copy.deepcopy(service.STATE)
  try:
   service.STATE.clear();service.STATE.update(prs={'one':{'id':'one','status':'unmeasured'}},batch=None)
   with patch.object(service,'save'),patch.object(service,'client',return_value={}),patch.object(service.POOL,'submit') as submit:
    service.start(['one']);self.assertEqual(submit.call_args.args,(service.measure,'one',False))
    service.STATE['prs']['one']['status']='unmeasured';service.STATE['batch']=None
    service.start();self.assertEqual(submit.call_args.args,(service.measure,'one',True))
  finally:service.STATE.clear();service.STATE.update(original)

if __name__=='__main__':unittest.main()
