"""Keep transport bounded while preserving full, re-checkable logs in a gzip archive."""
import copy
import gzip
import json


def compact(report):
 def visit(value):
  if isinstance(value,list):return [visit(x) for x in value]
  if not isinstance(value,dict):return value
  out={k:visit(v) for k,v in value.items() if k not in ('output','cases')}
  if 'output' in value:
   out['output']=value['output'][:2000]
   out['outputTruncated']=len(value['output'])>2000
  if 'cases' in value:
   cases=value['cases']
   selected=cases if value.get('label') in ('head','trimmed','signed-branch') else [x for x in cases if not x['passed']][:3]
   out['cases']=[{**x,'failure':x.get('failure','')[:1500]} for x in selected]
   out['fullCaseCount']=len(cases)
  return out
 return visit(report)


def archive(report):
 return gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0)
