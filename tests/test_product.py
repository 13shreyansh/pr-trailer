import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from product import github

class GitHubBoundaryTests(unittest.TestCase):
 def test_public_pr_parser_rejects_credential_and_redirect_hosts(self):
  for url in ['http://github.com/a/b/pull/1','https://github.com.evil.test/a/b/pull/1','https://user@github.com/a/b/pull/1','https://github.com/a/b/pull/1?x=1','https://github.com/../b/pull/1']:
   with self.subTest(url=url),self.assertRaises(ValueError):github.parse_pr(url)
  self.assertEqual(github.parse_pr('https://github.com/pallets/click/pull/123'),('pallets/click',123))
 def test_external_repository_is_never_writable(self):
  with self.assertRaises(ValueError):github.api('/repos/pallets/click/pulls/1','POST',{})
 def test_owned_repository_settings_are_writable(self):
  with patch.object(github,'credential',return_value='test-placeholder'),patch('urllib.request.urlopen',return_value=io.BytesIO(b'{}')):
   self.assertEqual(github.api('/repos/'+github.FULL,'PATCH',{'default_branch':'main'}),{})
 def test_new_reference_creation_handles_github_422(self):
  with patch.object(github,'api',side_effect=[RuntimeError('GitHub 422: Reference does not exist'),{'ref':'refs/heads/agent/test'}]) as mock:
   github.set_ref('agent/test','abc')
   self.assertEqual(mock.call_args_list[1].kwargs['method'],'POST')

class SandboxTests(unittest.TestCase):
 def test_public_code_cannot_read_broker_or_use_network(self):
  import tempfile
  from product.sandbox import runner
  parent=ROOT/'var';parent.mkdir(exist_ok=True)
  with tempfile.TemporaryDirectory(dir=parent) as tmp:
   root=Path(tmp);work=root/'work';work.mkdir()
   (work/'test_isolation.py').write_text('import socket\nfrom pathlib import Path\ndef test_broker_is_private():\n    try:Path('+repr(str(ROOT/'product/github.py'))+').read_text()\n    except PermissionError:return\n    raise AssertionError("broker readable")\ndef test_network_is_denied():\n    try:socket.create_connection(("1.1.1.1",443),timeout=.2)\n    except OSError:return\n    raise AssertionError("network enabled")\n')
   result=runner(root)(work,['test_isolation.py'],root/'logs','isolation')
   self.assertEqual(result['exitCode'],0,result['output'])
   self.assertEqual(result['passed'],2)

class QueueRegressionTests(unittest.TestCase):
 def test_stop_accounts_for_queued_jobs_and_finishes_batch(self):
  from product import service
  from unittest.mock import patch
  import copy
  original=copy.deepcopy(service.STATE)
  try:
   service.STATE.clear();service.STATE.update(prs={'queued':{'id':'queued','status':'queued'}},batch={'running':True,'total':1,'completed':0,'testsRun':0})
   service.STOP.set()
   with patch.object(service,'save'):service.measure('queued')
   self.assertEqual(service.STATE['batch']['completed'],1)
   self.assertFalse(service.STATE['batch']['running'])
  finally:service.STATE.clear();service.STATE.update(original);service.STOP.clear()

class EvidenceRegressions(unittest.TestCase):
 def test_notch_uses_changed_source_position_instead_of_a_constant(self):
  import tempfile,dataclasses
  from product import service
  from product.sandbox import engine
  with tempfile.TemporaryDirectory(dir=ROOT/'var') as tmp:
   root=Path(tmp);base=root/'base';head=root/'head';base.mkdir();head.mkdir()
   before='from decimal import ROUND_HALF_UP\ndef fee(n):\n    return n\n';after='from decimal import ROUND_HALF_DOWN\ndef fee(n):\n    raw=n\n    rounded=raw\n    bounded=rounded\n    return min(500,bounded)\n'
   (base/'fee.py').write_text(before);(head/'fee.py').write_text(after)
   b=engine.blocks_for('fee.py',before,after,whole=True)[0];block={**dataclasses.asdict(b),'needed':True,'lines':b.lines}
   self.assertAlmostEqual(service.position({'blocks':[block],'kept':7},base,head,{'path':'fee.py','start':3,'lines':after.splitlines()[2:6],'marked':1}),4/7)
 def test_public_library_does_not_get_an_invented_hardware_warning(self):
  import tempfile
  from product import service
  with tempfile.TemporaryDirectory(dir=ROOT/'var') as tmp:
   root=Path(tmp);(root/'logic.py').write_text('def required():\n    return True\n')
   risks=service.find_risks({'kind':'outside','outside':True,'repo':'pallets/itsdangerous'},{'blocks':[{'needed':True,'path':'logic.py'}]},root)
   self.assertNotIn('hardware',risks[0]['note'].lower())
 def test_connected_tunnel_can_publish_without_local_dns_resolution(self):
  import tempfile
  from product import tunnel
  from unittest.mock import Mock
  with tempfile.TemporaryDirectory(dir=ROOT/'var') as tmp:
   root=Path(tmp);(root/'var').mkdir()
   process=Mock(pid=123,stdout=iter(['https://unit-check.trycloudflare.com\n','Registered tunnel connection\n']));process.wait.return_value=0
   with patch.object(tunnel,'ROOT',root),patch.object(tunnel.subprocess,'Popen',return_value=process),patch.object(tunnel,'publish') as publish:
    tunnel.supervise(restart=False)
    publish.assert_called_once_with('https://unit-check.trycloudflare.com')

class UncheckedAskRegression(unittest.TestCase):
 def test_completely_unchecked_public_change_requires_human_review(self):
  import tempfile
  from product import service
  with tempfile.TemporaryDirectory(dir=ROOT/'var') as tmp:
   root=Path(tmp);(root/'README.md').write_text('Updated documentation\n')
   risks=service.find_risks({'kind':'outside','outside':True,'repo':'owner/library'},{'blocks':[{'needed':False,'path':'README.md','new':['Updated documentation\n']}]},root)
   self.assertTrue(risks)
   self.assertIn('acceptance',risks[0]['note'])

class SourceIsolationRegression(unittest.TestCase):
 def test_test_code_cannot_change_the_measured_source(self):
  import tempfile
  from product.sandbox import runner
  with tempfile.TemporaryDirectory(dir=ROOT/'var') as tmp:
   root=Path(tmp);work=root/'work';work.mkdir();(work/'logic.py').write_text('VALUE=1\n')
   (work/'test_source.py').write_text('from pathlib import Path\ndef test_source_read_only():\n    try:Path("logic.py").write_text("VALUE=2\\n")\n    except PermissionError:return\n    raise AssertionError("source was writable")\n')
   r=runner(root)(work,['test_source.py'],root/'logs','read-only')
   self.assertEqual(r['exitCode'],0,r['output'])
   self.assertEqual((work/'logic.py').read_text(),'VALUE=1\n')

class RefUpdateRegression(unittest.TestCase):
 def test_ordinary_revert_does_not_force_overwrite_concurrent_main(self):
  with patch.object(github,'api',return_value={}) as mock:
   github.set_ref('main','new-commit',force=False)
   self.assertFalse(mock.call_args.kwargs['data']['force'])
  from product import service
  receipt={'sha':'current','before':'before','id':'case'}
  with patch.dict(service.STATE,{'merged':[receipt]}),patch.object(service,'api',side_effect=[{'object':{'sha':'current'}},{'tree':{'sha':'old-tree'}},{'sha':'revert'}]),patch.object(service,'set_ref',side_effect=RuntimeError('Concurrent main update')) as update:
   with self.assertRaises(RuntimeError):service.revert()
   update.assert_called_once_with('main','revert',force=False)

class BatchInputRegression(unittest.TestCase):
 def test_all_ids_are_validated_before_any_queue_mutation(self):
  from product import service
  import copy
  original=copy.deepcopy(service.STATE)
  try:
   service.STATE.clear();service.STATE.update(prs={'valid':{'id':'valid','status':'unmeasured'}},batch=None)
   with patch.object(service,'save') as save,patch.object(service.POOL,'submit') as submit:
    with self.assertRaises(ValueError):service.start(['valid','missing'])
    self.assertEqual(service.STATE['prs']['valid']['status'],'unmeasured')
    save.assert_not_called();submit.assert_not_called()
  finally:service.STATE.clear();service.STATE.update(original)
 def test_reset_does_not_suppress_worker_failure(self):
  import importlib.util,tempfile
  spec=importlib.util.spec_from_file_location('workspace_reset',ROOT/'scripts/product/workspace.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  with tempfile.TemporaryDirectory(dir=ROOT/'var') as tmp,patch.object(module,'pages',return_value=[]),patch.object(module,'set_ref'),patch('urllib.request.urlopen',side_effect=OSError('Worker unavailable')):
   module.OUT=Path(tmp)/'workspace.json'
   with self.assertRaisesRegex(RuntimeError,'worker reset failed'):module.reset({'baseline':'baseline','cases':{}})

class MergeReadinessRegression(unittest.TestCase):
 def test_finish_waits_for_github_mergeability_after_pushing(self):
  from product import service
  with patch.object(service,'api',side_effect=[RuntimeError('GitHub 405: Pull Request is not mergeable'),{'head':{'sha':'candidate'}},{'merged':True,'sha':'merged'}]) as api,patch.object(service.time,'sleep'):
   result=service.merge_ready(1,'candidate','Requirement')
   self.assertTrue(result['merged'])
   self.assertEqual(api.call_count,3)
 def test_merge_wait_does_not_accept_a_changed_branch(self):
  from product import service
  with patch.object(service,'api',side_effect=[RuntimeError('GitHub 405: Not mergeable'),{'head':{'sha':'changed'}}]):
   with self.assertRaises(ValueError):service.merge_ready(1,'candidate','Requirement')
