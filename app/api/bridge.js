const allowed=new Set(['workspace','status','measure','stop','add','finish','return','block','unblock','revert','proof','patch','enter','leave','reset']);
let cachedOrigin=null,until=0;
function valid(value){const u=new URL(value);if(u.protocol!=='https:'||!u.hostname.endsWith('.trycloudflare.com')||u.username||u.password||u.port||u.pathname!=='/')throw Error('Invalid worker origin');return u;}
async function origin(refresh=false){
 if(!refresh&&cachedOrigin&&Date.now()<until)return cachedOrigin;
 // The deployment's address is authoritative. Raw GitHub branch URLs can retain
 // a superseded tunnel in CDN cache after the worker publishes its new address.
 if(!refresh&&process.env.RUNNER_ORIGIN){cachedOrigin=valid(process.env.RUNNER_ORIGIN);until=Date.now()+60000;return cachedOrigin;}
 const response=await fetch('https://api.github.com/repos/13shreyansh/tieto-nordbank-payments/contents/.tieto/connection.json?ref=tieto%2Fconnection&v='+Date.now(),{headers:{Accept:'application/vnd.github+json'},cache:'no-store',signal:AbortSignal.timeout(12000)});
 if(!response.ok)throw Error('Worker routing unavailable');
 const entry=await response.json(),data=JSON.parse(Buffer.from(entry.content,'base64').toString('utf8'));
 cachedOrigin=valid(data.origin);until=Date.now()+60000;return cachedOrigin;
}
module.exports=async function(req,res){
 const route=String(req.query.endpoint||'');if(!allowed.has(route)){res.statusCode=404;return res.end('Not found');}
 try{
  async function call(base){const target=new URL('/api/'+route,base);if(req.query.id)target.searchParams.set('id',String(req.query.id));if(req.query.v)target.searchParams.set('v',String(req.query.v));return fetch(target,{method:req.method,headers:{'Content-Type':'application/json'},body:req.method==='POST'?JSON.stringify(req.body||{}):undefined,signal:AbortSignal.timeout(55000)});}
  let response=await call(await origin());
  // A 530 means the named tunnel has no origin connection. No worker action ran.
  if(response.status===530)response=await call(await origin(true));
  if(!(response.headers.get('content-type')||'').match(/application\/json|text\/plain/))throw Error('Worker unavailable');
  res.statusCode=response.status;res.setHeader('Content-Type',response.headers.get('content-type'));res.setHeader('Cache-Control','no-store');
  if(response.headers.get('content-disposition'))res.setHeader('Content-Disposition',response.headers.get('content-disposition'));res.end(Buffer.from(await response.arrayBuffer()));
 }catch{until=0;res.statusCode=503;res.setHeader('Content-Type','application/json');res.end(JSON.stringify({error:'Could not reach the test runner. Try again.'}));}
};
