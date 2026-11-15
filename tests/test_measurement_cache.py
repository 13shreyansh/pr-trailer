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
  self.folder=self.root/'verified';self.row={'repo':'owner/repo','headSha':'a'*40,'ask':'Cap fees','paths':['fee.py'],'kind':'cap'}
  self.config={'tests':['oracle/test_fee.py'],'wholePaths':['fee.py']};self.base='b'*40
  self.report={'repo':'owner/repo','headSha':'a'*40,'baseSha':self.base,'number':7,'measuredAt':'2026-11-15T06:49:00Z',
    'final':{'exitCode':0,'tests':9,'passed':9,'execution':{'provider':'modal','runnerSha256':cache.profile()['runnerSha256']}},
    'heldOut':{'exitCode':1,'passed':0,'tests':1},'blocks':[],'controls':[],'patch':'public patch'}
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
