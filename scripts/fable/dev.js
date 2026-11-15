// Local preview: serves app/ with the production rewrites and forwards /api to the local worker.
const http=require('http'),fs=require('fs'),path=require('path');
const root=path.join(__dirname,'../../app'),types={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.ttf':'font/ttf','.woff2':'font/woff2'};
http.createServer((req,res)=>{
 const url=new URL(req.url,'http://localhost');
 if(url.pathname.startsWith('/api/')){const upstream=http.request({host:'127.0.0.1',port:4322,path:req.url,method:req.method,headers:{'content-type':req.headers['content-type']||'application/json','content-length':req.headers['content-length']||0}},r=>{res.writeHead(r.statusCode,r.headers);r.pipe(res);});upstream.on('error',()=>{res.writeHead(503,{'Content-Type':'application/json'});res.end('{"error":"Could not reach the test runner. Try again."}');});req.pipe(upstream);return;}
 let p=url.pathname==='/'?'/index.html':url.pathname==='/workspace'||url.pathname.startsWith('/workspace/')?'/workspace.html':url.pathname;
 const file=path.resolve(root,'.'+p);if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);return res.end('Not found');}
 res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream'});fs.createReadStream(file).pipe(res);
}).listen(process.env.PORT||4331,()=>console.log('http://localhost:'+(process.env.PORT||4331)));
