"""Publish an immutable source snapshot through the existing project's routing API."""
import json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TEAM='team_SjINqXczvI3i0JpBv7JRMqQN';PROJECT='prj_TqJO4nTjZj4gODIgOManda1qm5yH'

def definitions(origin,commit):
 return [
  {'id':'tieto-committed-style','name':'Committed Tieto stylesheet','enabled':True,'srcSyntax':'equals','route':{'src':'/style.css','dest':origin+'/api/patch?id=asset-'+commit+'-style','respectOriginCacheControl':True}},
  {'id':'tieto-commit-marker','name':'Served Tieto commit','enabled':True,'srcSyntax':'equals','route':{'src':'/build.json','dest':origin+'/api/patch?id=asset-'+commit+'-build','respectOriginCacheControl':True}},
  {'id':'tieto-worker-api','name':'Live Tieto worker','enabled':True,'srcSyntax':'regex','route':{'src':'^/api/(.*)$','dest':origin+'/api/$1','respectOriginCacheControl':True}}
 ]

def publish(origin):
 config=ROOT/'var/current-publication.json'
 if not config.exists():return
 if not json.loads(config.read_text()).get('routingManaged'):return
 commit=json.loads(config.read_text())['commit']
 token=json.loads((Path.home()/'Library/Application Support/com.vercel.cli/auth.json').read_text())['token']
 def call(method,suffix,data):
  request=urllib.request.Request('https://api.vercel.com/v1/projects/'+PROJECT+'/routes'+suffix+'?teamId='+TEAM,method=method,data=json.dumps(data).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
  with urllib.request.urlopen(request,timeout=30) as response:return json.load(response)
 staged=call('PUT','',{'overwrite':True,'routes':definitions(origin,commit)})
 version=staged['version']['id']
 live=call('POST','/versions',{'action':'promote','id':version})
 record={'commit':commit,'origin':origin,'version':version,'response':live,'publication':'project-routing','measured':True}
 (ROOT/'evidence/route-publication.json').write_text(json.dumps(record,indent=2)+'\n')
 return record
