const assert=require('node:assert/strict');
(async()=>{
 const original=global.fetch,previous=process.env.RUNNER_ORIGIN;
 try{
  process.env.RUNNER_ORIGIN='https://current-worker.trycloudflare.com';let urls=[];
  global.fetch=async url=>{urls.push(String(url));return new Response(JSON.stringify({ready:true}),{headers:{'content-type':'application/json'}})};
  const bridge=require('../../app/api/bridge');const response={setHeader(){},end(body){this.body=body}};
  await bridge({method:'GET',query:{endpoint:'status'}},response);
  assert.deepEqual(urls,['https://current-worker.trycloudflare.com/api/status']);assert.equal(response.statusCode,200);
  urls=[];
  global.fetch=async url=>{urls.push(String(url));if(urls.length===1)return new Response('Tunnel missing',{status:530,headers:{'content-type':'text/html'}});if(urls.length===2)return new Response(JSON.stringify({content:Buffer.from(JSON.stringify({origin:'https://replacement-worker.trycloudflare.com'})).toString('base64')}),{headers:{'content-type':'application/json'}});return new Response('{}',{headers:{'content-type':'application/json'}})};
  await bridge({method:'GET',query:{endpoint:'status'}},response);assert.equal(response.statusCode,200);assert.ok(urls[1].startsWith('https://api.github.com/'));assert.equal(urls[2],'https://replacement-worker.trycloudflare.com/api/status');
  console.log('Worker routing regressions passed: deployment origin wins, vanished tunnel refreshes.');
 }finally{global.fetch=original;if(previous===undefined)delete process.env.RUNNER_ORIGIN;else process.env.RUNNER_ORIGIN=previous;}
})().catch(e=>{console.error(e);process.exitCode=1});
