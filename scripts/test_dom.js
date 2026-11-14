const {JSDOM}=require('jsdom'),fs=require('fs'),assert=require('node:assert/strict');
(async()=>{
 const dom=new JSDOM('<div id="app"></div>',{url:'https://pr-trailer.vercel.app/',runScripts:'outside-only'}),w=dom.window;
 w.matchMedia=()=>({matches:true});w.document.fonts={ready:Promise.resolve()};w.fetch=async()=>({ok:true,json:async()=>({account:'13shreyansh',prs:[],merged:[],returned:[],blocked:[],batch:null,syncedAt:null})});
 for(const path of ['review.js','app.js'])w.eval(fs.readFileSync('app/'+path,'utf8'));
 await new Promise(r=>setTimeout(r,10));const d=w.document;
 assert.equal(d.querySelectorAll('button.primary').length,1);assert.match(d.querySelector('button.primary').textContent,/Try the demo workspace \(Nordbank payments\)/);
 assert.equal(d.querySelectorAll('input[type="password"]').length,0);assert.ok(d.getElementById('pr-link'));
 d.querySelector('[data-action="focus-link"]').click();assert.equal(d.activeElement.id,'pr-link');
 dom.window.close();console.log('Clean entry DOM passed. Deployed Chromium E2E is the flow acceptance test.');
})().catch(e=>{console.error(e);process.exitCode=1});
