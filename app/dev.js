const http=require('http'),fs=require('fs'),path=require('path'),{spawn}=require('child_process');
const root=__dirname,types={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.ttf':'font/ttf','.txt':'text/plain','.patch':'text/plain'};
http.createServer((req,res)=>{
 if(['/api/trim','/api/finish'].includes(req.url.split('?')[0])&&req.method==='POST'){
  const finish=req.url.split('?')[0]==='/api/finish';
  let body='';req.on('data',chunk=>{body+=chunk;if(body.length>1024)req.destroy();});req.on('end',()=>{
   let id;try{const data=JSON.parse(body);id=finish?JSON.stringify(data.ids):data.id;if(finish){if(!Array.isArray(data.ids)||data.ids.some(x=>!/^KASSA-(0[1-9]|1[0-9])$/.test(x)))throw Error();}else if(typeof id!=='string'||!fs.existsSync(path.join(root,'runtime/sources',id+'.zip'))||!/^[A-Z0-9-]+$/.test(id))throw Error();}catch{res.writeHead(400,{'Content-Type':'application/json'});return res.end('{"error":"Unknown fixed sample"}');}
   const worker=spawn(path.join(root,'../.venv312/bin/python'),['-B',path.join(root,finish?'runtime/finish.py':'runtime/worker.py'),id],{env:{PATH:process.env.PATH,HOME:process.env.HOME,PYTHONDONTWRITEBYTECODE:'1'}});let output='',err='';worker.stdout.on('data',x=>output+=x);worker.stderr.on('data',x=>err+=x);worker.on('close',code=>{res.writeHead(code?500:200,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(code?'{"error":"Could not run fixed tests"}':output);});
  });return;
 }
 const url=new URL(req.url,'http://localhost');let p;try{p=decodeURIComponent(url.pathname);}catch{res.writeHead(400);return res.end();}
 if(p==='/')p='/index.html';const file=path.resolve(root,'.'+p);
 if(!file.startsWith(root+path.sep)||p.startsWith('/api/')||p.startsWith('/runtime/')||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);return res.end('Not found');}
 res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream'});fs.createReadStream(file).pipe(res);
}).listen(process.env.PORT||4321,()=>console.log('http://localhost:'+(process.env.PORT||4321)));
