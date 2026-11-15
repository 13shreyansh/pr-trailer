import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import Mock,patch

from product import modal_runner,runlog,provenance
from product.evidence_page import code_context_page

class ModalBoundaryTests(unittest.TestCase):
 def test_archive_never_contains_environment_credentials_or_broker(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'test_app.py').write_text('def test_ok(): assert True')
   (root/'.env').write_text('MODAL_TOKEN_SECRET=do-not-upload')
   (root/'.env.local').write_text('MONGODB_URI=do-not-upload')
   (root/'.git').mkdir();(root/'.git/config').write_text('private')
   raw=modal_runner.source_archive(root)
   with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
    self.assertEqual(archive.getnames(),['test_app.py'])
 def test_symlinks_cannot_read_the_broker(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'leak').symlink_to('/etc/passwd')
   with self.assertRaises(ValueError):modal_runner.source_archive(root)
 def test_configured_modal_does_not_fall_back_when_keys_missing(self):
  from product.sandbox import runner
  with patch.dict(os.environ,{'TIETO_TEST_RUNNER':'modal','MODAL_TOKEN_ID':'','MODAL_TOKEN_SECRET':''}),tempfile.TemporaryDirectory() as tmp:
   with self.assertRaisesRegex(RuntimeError,'not configured'):runner(Path(tmp))(Path(tmp),['tests'],Path(tmp),'head')
 def test_secrets_never_enter_sandbox_and_termination_is_guaranteed(self):
  fake=Mock();sandbox=fake.Sandbox.create.return_value
  process=sandbox.exec.return_value
  process.stdout.read.return_value=json.dumps({'exitCode':0,'tests':1,'passed':1,'cases':[],'output':'ok','seconds':.2})
  process.wait.return_value=0;sandbox.object_id='sb-public-id'
  with patch.dict(os.environ,{'MODAL_TOKEN_ID':'placeholder','MODAL_TOKEN_SECRET':'placeholder'}),patch.object(runlog,'record_check',return_value={'stored':True}),tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'test_ok.py').write_text('def test_ok(): pass')
   result=modal_runner.run_check(root,['test_ok.py'],root/'logs','head',modal_module=fake)
  kwargs=fake.Sandbox.create.call_args.kwargs
  self.assertTrue(kwargs['block_network']);self.assertFalse(kwargs['include_oidc_identity_token'])
  self.assertNotIn('secrets',kwargs);self.assertNotIn('env',kwargs)
  self.assertEqual(result['execution']['sandboxId'],'sb-public-id');sandbox.terminate.assert_called_once()
 def test_termination_even_when_provider_output_is_invalid(self):
  fake=Mock();sandbox=fake.Sandbox.create.return_value;sandbox.exec.return_value.stdout.read.return_value='invalid';sandbox.exec.return_value.wait.return_value=0
  with patch.dict(os.environ,{'MODAL_TOKEN_ID':'placeholder','MODAL_TOKEN_SECRET':'placeholder'}),tempfile.TemporaryDirectory() as tmp:
   with self.assertRaises((ValueError,RuntimeError)):modal_runner.run_check(Path(tmp),['tests'],Path(tmp),'head',modal_module=fake)
  sandbox.terminate.assert_called_once()

class AtlasOutboxTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'TIETO_RUNLOG_OUTBOX':str(Path(self.tmp.name)/'outbox.sqlite')});self.env.start()
 def tearDown(self):self.env.stop();self.tmp.cleanup()
 def test_only_metadata_is_written_and_retry_is_idempotent(self):
  collection=Mock();result={'exitCode':0,'tests':2,'passed':2,'seconds':.2,'output':'SECRET RAW OUTPUT','outputSha256':'f'*64,'execution':{'provider':'modal','sandboxId':'sb-1'}}
  with patch.object(runlog,'_collection',return_value=collection):
   receipt=runlog.record_check('run1','head',result,{'repo':'owner/public','headSha':'a'*40,'number':1,'token':'SECRET TOKEN'})
   runlog.record_check('run1','head',result,{'repo':'owner/public','headSha':'a'*40,'number':1})
  self.assertTrue(receipt['stored']);calls=collection.replace_one.call_args_list
  self.assertEqual(calls[0].args[0],calls[1].args[0]);self.assertTrue(calls[0].kwargs['upsert'])
  body=json.dumps(calls[0].args[1]);self.assertNotIn('SECRET',body);self.assertNotIn('output"',body)
 def test_failed_write_remains_pending_until_recovery(self):
  collection=Mock();collection.replace_one.side_effect=RuntimeError('credentials must not escape')
  with patch.object(runlog,'_collection',return_value=collection):
   receipt=runlog.record_check('run','head',{'exitCode':0},{})
   self.assertFalse(receipt['stored']);self.assertNotIn('credentials',json.dumps(receipt))
   collection.replace_one.side_effect=None
   self.assertEqual(runlog.flush()['delivered'],1)
   self.assertEqual(runlog.flush()['delivered'],0)
 def test_run_reads_query_atlas_not_process_memory(self):
  collection=Mock();collection.find.return_value.limit.return_value=[{'runId':'persisted','tests':2}]
  with patch.object(runlog,'_collection',return_value=collection):
   self.assertEqual(runlog.read_run('persisted')['events'][0]['tests'],2)
  self.assertEqual(collection.find.call_args.args[0],{'runId':'persisted'})

class EntireGraphTests(unittest.TestCase):
 def test_code_context_is_bounded_and_rejects_external_paths(self):
  data={'results':[{'file_path':'ledger/fees.py','start_line':8,'symbol_name':'transfer_fee','signals':['graph:callers','body']},{'file_path':'../../secret','start_line':1}]}
  done=Mock(returncode=0,stdout=json.dumps(data))
  with patch.dict(os.environ,{'ENTIRE_BIN':'/trusted/entire','MODAL_TOKEN_SECRET':'never-pass'}),patch.object(provenance.subprocess,'run',return_value=done) as run:
   context=provenance.code_context(Path('.'),'Cap fees','a'*40)
  self.assertTrue(context['available']);self.assertEqual(len(context['symbols']),1)
  self.assertNotIn('MODAL_TOKEN_SECRET',run.call_args.kwargs['env'])
  self.assertIn('--max-context-bytes',run.call_args.args[0])
 def test_graph_failure_does_not_invent_provenance(self):
  with patch.dict(os.environ,{'ENTIRE_BIN':'/trusted/entire'}),patch.object(provenance.subprocess,'run',side_effect=TimeoutError()):
   self.assertFalse(provenance.code_context(Path('.'),'question','a'*40)['available'])
 def test_readable_evidence_escapes_untrusted_source_and_title(self):
  html=code_context_page({'title':'<script>bad()</script>','repo':'owner/repo'},{'headSha':'a'*40,'codeContext':{'symbols':[{'path':'x.py','line':1,'name':'<img onerror=bad()>','relations':[]}]}}).decode()
  self.assertNotIn('<script>',html);self.assertNotIn('<img ',html);self.assertIn('Entire Graph',html)

if __name__=='__main__':unittest.main()
