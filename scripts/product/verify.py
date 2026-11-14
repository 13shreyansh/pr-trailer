"""Independently verify the deployed user's actions against GitHub, never writing there."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from product.github import api,FULL
rows=json.loads(Path(sys.argv[1]).read_text());merges=[r for r in rows if r['action']=='finish' and r['status']==200]
assert len(merges)==19
for receipt in merges:
 r=receipt['result'];pr=api(f'/repos/{FULL}/pulls/{r["number"]}');assert pr['merged'] and pr['merge_commit_sha']==r['sha'];assert r['tests']==r['passed']
last=merges[-1]['result'];assert last['tests']==48
returned=next(r['result'] for r in rows if r['action']=='return' and r['status']==200);pr=api(f'/repos/{FULL}/pulls/{returned["number"]}');assert pr['state']=='open' and returned['note'] in pr['body'];assert pr['head']['sha']==returned['sha']
blocked=next(r['result'] for r in rows if r['action']=='block' and r['status']==200);comment=api(f'/repos/{FULL}/issues/comments/{blocked["commentId"]}');assert 'What should this change? Name one thing we can test.' in comment['body']
pr=api(f'/repos/{FULL}/pulls/{blocked["number"]}');assert any(l['name']=='tieto-blocked' for l in pr['labels'])
main=api('/repos/'+FULL+'/git/ref/heads/main')['object']['sha'];tree=api(f'/repos/{FULL}/git/trees/{main}?recursive=1')['tree'];paths={f['path'] for f in tree};assert not any(p.startswith('config/') for p in paths);assert 'ledger/currency_cache.py' not in paths and 'ledger/retry_rewrite.py' not in paths
print(json.dumps({'repo':FULL,'verifiedMerges':len(merges),'lastMergeTests':last['tests'],'trimmedPR':pr['html_url'] if False else returned['github'],'blockComment':comment['html_url'],'main':main,'uncheckedFilesAbsent':True,'measured':True}))
