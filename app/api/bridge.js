const allowed=new Set(['workspace','status','measure','stop','add','finish','return','block','unblock','revert','proof','patch']);
let cachedOrigin=null,until=0;
function valid(value){const u=new URL(value);if(u.protocol!=='https:'||!u.hostname.endsWith('.trycloudflare.com')||u.username||u.password||u.port||u.pathname!=='/')throw Error('Invalid worker origin');return u;}
async function origin(){
 if(cachedOrigin&&Date.now()<until)return cachedOrigin;
 try{const response=await fetch('https://raw.githubusercontent.com/13shreyansh/tieto-nordbank-payments/tieto/connection/.tieto/connection.json?v='+Math.floor(Date.now()/15000),{signal:AbortSignal.timeout(12000)});if(!response.ok)throw Error();const data=await response.json();cachedOrigin=valid(data.origin);until=Date.now()+15000;return cachedOrigin;}
 catch{if(cachedOrigin)return cachedOrigin;return valid(process.env.RUNNER_ORIGIN);}
}
module.exports=async function(req,res){
 const route=String(req.query.endpoint||'');if(!allowed.has(route)){res.statusCode=404;return res.end('Not found');}
 try{
  const target=new URL('/api/'+route,await origin());if(req.query.id)target.searchParams.set('id',String(req.query.id));
  const response=await fetch(target,{method:req.method,headers:{'Content-Type':'application/json'},body:req.method==='POST'?JSON.stringify(req.body||{}):undefined,signal:AbortSignal.timeout(55000)});
  res.statusCode=response.status;res.setHeader('Content-Type',response.headers.get('content-type')||'application/json');res.setHeader('Cache-Control','no-store');
  if(response.headers.get('content-disposition'))res.setHeader('Content-Disposition',response.headers.get('content-disposition'));res.end(Buffer.from(await response.arrayBuffer()));
 }catch{until=0;res.statusCode=503;res.setHeader('Content-Type','application/json');res.end(JSON.stringify({error:'Could not reach the test runner. Try again.'}));}
};
