"""Evidence contract plus real mutation, patch-application and repeatability regressions."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/measure'))
from engine import blocks_for,materialize,trim,run_check
from bank_cases import CASES

class MeasureTests(unittest.TestCase):
 def setUp(self):
  (ROOT/'evidence/work').mkdir(parents=True,exist_ok=True)
  self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'evidence/work');self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def test_real_remove_and_retest_and_patch(self):
  base=self.root/'base';head=self.root/'head';base.mkdir();head.mkdir()
  (base/'calc.py').write_text('def fee(n):\n    return n\n')
  (head/'calc.py').write_text('def fee(n):\n    return min(n, 500)\n')
  (head/'cache.py').write_text('CACHE = {}\n')
  (base/'test_ask.py').write_text('from calc import fee\ndef test_cap():\n    assert fee(999) == 500\n')
  result=trim(base,head,self.root/'work',['calc.py','cache.py'],['test_ask.py'],self.root/'logs')
  self.assertEqual(result['final']['exitCode'],0)
  self.assertEqual(result['kept'],2)
  self.assertTrue(any(b['path']=='cache.py' and not b['needed'] for b in result['blocks']))
  self.assertTrue(all(c['exitCode']!=0 for c in result['controls']))
  patch=self.root/'minimal.patch';patch.write_text(result['patch'])
  subprocess.run(['git','apply',str(patch)],cwd=base,check=True)
  self.assertEqual(run_check(base,['test_ask.py'],self.root/'logs','patch-applied')['exitCode'],0)
 def test_deletions_and_multiple_hunks_preserve_offsets(self):
  base=self.root/'base';work=self.root/'work';base.mkdir();work.mkdir()
  before='a\nb\nc\nd\ne\nf\n';after='A\nb\nc\ne\nF\n'
  (base/'file').write_text(before);blocks=blocks_for('file',before,after)
  materialize(base,work,blocks,{b.id for b in blocks})
  self.assertEqual((work/'file').read_text(),after)
  materialize(base,work,blocks,set())
  self.assertEqual((work/'file').read_text(),before)
 def test_oracle_is_refreshed_before_repeat_run(self):
  base=self.root/'base';head=self.root/'head';base.mkdir();head.mkdir()
  (base/'a.py').write_text('x=0\n');(head/'a.py').write_text('x=1\n')
  (base/'test_a.py').write_text('from a import x\ndef test_x():\n    assert x==1\n')
  one=trim(base,head,self.root/'work',['a.py'],['test_a.py'],self.root/'logs1')
  (self.root/'work/test_a.py').write_text('raise RuntimeError("stale work")\n')
  two=trim(base,head,self.root/'work',['a.py'],['test_a.py'],self.root/'logs2')
  self.assertEqual(one['kept'],two['kept'])
  self.assertEqual(two['final']['exitCode'],0)
 def test_mask_regression_keeps_iban_length(self):
  case=CASES[0]
  for value,expected in case[4]:self.assertEqual(len(value),len(expected))
 def test_all_recorded_counts_and_controls(self):
  manifest=json.loads((ROOT/'app/evidence/manifest.json').read_text())
  self.assertEqual(len(manifest['prs']),23)
  self.assertEqual(sum(p['status']=='proven' for p in manifest['prs']),19)
  self.assertEqual(sum(p['source']=='AIDev' for p in manifest['prs']),2)
  self.assertEqual(manifest['totals']['written'],sum(p['written'] for p in manifest['prs']))
  self.assertEqual(manifest['totals']['needYou'],sum(p.get('readLines',0) for p in manifest['prs']))
  for p in manifest['prs']:
   with self.subTest(pr=p['id']):
    report=json.loads((ROOT/'app'/p['evidence']).read_text())
    self.assertEqual(p['written'],p['kept']+p['unchecked'])
    self.assertEqual(sum(b['lines'] for b in p['blocks']),p['written'])
    if p['status']=='intern':continue
    self.assertAlmostEqual(p['seconds'],sum(r['seconds'] for r in report['runs']))
    self.assertEqual(report['final']['exitCode'],0)
    self.assertEqual(report['final']['tests'],p['tests'])
    self.assertTrue(report['controls'])
    for control in report['controls']:self.assertNotEqual(control['exitCode'],0)
    for run in report['runs']:self.assertTrue(run['measured'])
    self.assertEqual(report['patch'],(ROOT/'app'/p['patch']).read_text())
 def test_cap_heldout_is_a_real_rounding_failure(self):
  report=json.loads((ROOT/'app/evidence/KASSA-CAP.json').read_text())
  self.assertEqual(report['final']['passed'],6)
  self.assertEqual(report['heldOut']['exitCode'],1)
  self.assertIn('200 == 201',report['heldOut']['cases'][0]['failure'])
 def test_intern_three_independent_failures_and_clean_reset(self):
  root=ROOT/'evidence/source/kassa';base=root/'base';head=root/'head-intern';work=self.root/'intern';shutil.copytree(base,work)
  paths=['ledger/auth.py','migrations/002_best_bank.sql','ledger/fees.py','schema/bank-api.json']
  blocks=[blocks_for(p,(base/p).read_text() if (base/p).exists() else '',(head/p).read_text(),whole=True)[0] for p in paths]
  for cycle in range(2):
   materialize(base,work,blocks,set())
   baseline=run_check(work,['oracle/test_safety.py'],self.root/'logs',f'baseline-{cycle}')
   self.assertEqual(baseline['exitCode'],0)
   for path,test in [('ledger/auth.py','test_ownership'),('migrations/002_best_bank.sql','test_statement_schema'),('ledger/fees.py','test_nonnegative_fees')]:
    materialize(base,work,blocks,{b.id for b in blocks if b.path==path})
    result=run_check(work,['oracle/test_safety.py::'+test],self.root/'logs',f'{test}-{cycle}')
    self.assertEqual(result['tests'],1)
    self.assertEqual(result['exitCode'],1)
   materialize(base,work,blocks,{b.id for b in blocks})
 def test_runtime_rejects_non_allowlisted_input(self):
  sys.path.insert(0,str(ROOT/'app/runtime'))
  from worker import execute
  with self.assertRaises(ValueError):execute('../../not-a-sample')
 def test_no_network_dependencies_in_story_assets(self):
  # Links to the real GitHub PRs are content; nothing may be *loaded* from another origin.
  import re
  for name in ('index.html','workspace.html','landing.css','style.css'):
   html=(ROOT/'app'/name).read_text()
   self.assertNotIn('fonts.googleapis',html)
   self.assertEqual(re.findall(r'<(?:script|img|iframe|link)\b[^>]*(?:src|href)="https?://[^"]*"',html),[],name)
   self.assertEqual(re.findall(r'url\(\s*[\'"]?https?://',html),[],name)
   self.assertNotIn('@import',html)
  self.assertTrue((ROOT/'app/fonts/Archivo.ttf').exists())
  self.assertTrue((ROOT/'app/fonts/JetBrainsMono.ttf').exists())

if __name__=='__main__':unittest.main()

class CountingRegressions(unittest.TestCase):
 def test_whole_file_group_counts_only_actual_delta(self):
  blocks=blocks_for('fees.py','import decimal\ndef fee():\n    return 1\n','import decimal\ndef fee():\n    return 2\n',whole=True)
  self.assertEqual(blocks[0].lines,2)

class BranchRegressions(unittest.TestCase):
 def test_finish_materializes_a_real_git_branch_and_rejects_unsafe_prs(self):
  import base64,io,zipfile
  sys.path.insert(0,str(ROOT/'app/runtime'))
  import finish
  with self.assertRaises(ValueError):finish.execute(['AIDEV-9'])
  with self.assertRaises(ValueError):finish.execute(['KASSA-CAP'])
  result=finish.execute(['KASSA-01','KASSA-02'])
  self.assertEqual(result['tests'],result['passed'])
  self.assertEqual(result['branch'],'tieto/approved')
  with tempfile.TemporaryDirectory(dir=ROOT/'evidence/work') as tmp:
   root=Path(tmp)
   with zipfile.ZipFile(io.BytesIO(base64.b64decode(result['zipBase64']))) as archive:archive.extractall(root)
   bank=root/'kassa'
   self.assertEqual(subprocess.check_output(['git','branch','--show-current'],cwd=bank,text=True).strip(),'tieto/approved')
   self.assertEqual(subprocess.check_output(['git','rev-parse','HEAD'],cwd=bank,text=True).strip(),result['commit'])
   self.assertNotIn('raise NotImplementedError',(bank/'ledger/mask_account.py').read_text())
   self.assertFalse((bank/'config/mask_account.json').exists())
   self.assertEqual(run_check(bank,['oracle/test_mask_account.py','oracle/test_reference.py','oracle/test_safety.py'],root/'logs','exported')['exitCode'],0)

class ServerlessDependencyRegression(unittest.TestCase):
 def test_child_checks_keep_parent_vendor_import_paths(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'evidence/work') as tmp:
   root=Path(tmp);vendor=root/'vendor';vendor.mkdir();work=root/'work';work.mkdir()
   (vendor/'fixed_test_dependency.py').write_text('VALUE = 42\n')
   (work/'test_vendor.py').write_text('from fixed_test_dependency import VALUE\ndef test_vendor():\n    assert VALUE == 42\n')
   sys.path.insert(0,str(vendor))
   try:
    self.assertEqual(run_check(work,['test_vendor.py'],root/'logs','vendored-import')['exitCode'],0)
   finally:sys.path.remove(str(vendor))

class RoundingIntroductionRegression(unittest.TestCase):
 def test_cap_pr_introduces_rounding_regression_against_green_baseline(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'evidence/work') as tmp:
   root=Path(tmp);base=ROOT/'evidence/source/kassa/base';work=root/'work';shutil.copytree(base,work)
   before=run_check(work,['oracle/test_rounding.py'],root/'logs','baseline-rounding')
   self.assertEqual(before['exitCode'],0)
   shutil.copyfile(ROOT/'evidence/source/kassa/head-cap/ledger/fee_cap.py',work/'ledger/fee_cap.py')
   after=run_check(work,['oracle/test_rounding.py'],root/'logs','pr-rounding')
   self.assertEqual(after['exitCode'],1)

class FixedPointRegression(unittest.TestCase):
 def test_removal_revisits_blocks_after_other_blocks_are_deleted(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'evidence/work') as tmp:
   root=Path(tmp);base=root/'base';head=root/'head';base.mkdir();head.mkdir()
   (base/'policy.py').write_text('A=0\n# separate changes\nB=0\n');(head/'policy.py').write_text('A=1\n# separate changes\nB=1\n')
   (base/'test_policy.py').write_text('from policy import A,B\ndef test_combination():\n    assert A==1 or B==0\n')
   result=trim(base,head,root/'work',['policy.py'],['test_policy.py'],root/'logs')
   self.assertEqual(result['kept'],0)
   self.assertEqual(result['final']['exitCode'],0)

class NotchPositionRegression(unittest.TestCase):
 def test_notch_tracks_marked_changed_line_after_import_change(self):
  from record import risk_position
  blocks=blocks_for('fee.py','from decimal import ROUND_HALF_UP\ndef cap(n):\n    return n\n','from decimal import ROUND_HALF_DOWN\ndef cap(n):\n    raw=n\n    rounded=raw\n    bounded=rounded\n    return min(500,bounded)\n',whole=True)
  import dataclasses
  block={**dataclasses.asdict(blocks[0]),'lines':blocks[0].lines,'needed':True}
  result={'blocks':[block],'kept':block['lines']}
  self.assertAlmostEqual(risk_position(result,block,'    rounded=raw'),4/7)

class InternExactChangeRegression(unittest.TestCase):
 def test_each_intern_failure_shows_the_actual_changed_source_line(self):
  data=json.loads((ROOT/'app/evidence/manifest.json').read_text());intern=next(p for p in data['prs'] if p['status']=='intern')
  for risk in intern['risk']:
   self.assertEqual(len(risk['lines']),1)
   source=(ROOT/'evidence/source/kassa/head-intern'/risk['path']).read_text().splitlines()
   self.assertEqual(risk['lines'][0],source[risk['start']-1])
