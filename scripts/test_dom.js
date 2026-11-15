const {JSDOM}=require('jsdom'),fs=require('fs'),assert=require('node:assert/strict');
(async()=>{
 // The landing page is static: one saffron entry, no script, no worker call, no password field.
 const landing=new JSDOM(fs.readFileSync('app/index.html','utf8')).window.document;
 assert.equal(landing.querySelectorAll('script').length,0,'Landing must not run script or call the worker');
 const entries=[...landing.querySelectorAll('a.primary')];assert.ok(entries.length>=1);for(const a of entries){assert.equal(a.getAttribute('href'),'/workspace');assert.match(a.textContent,/^Open the demo workspace\s*$/);}
 assert.equal(landing.querySelectorAll('input').length,0);assert.match(landing.querySelector('h1').textContent,/pull requests/);
 for(const id of ['problem','how','proof','limits'])assert.ok(landing.getElementById(id),'Missing section '+id);
 assert.doesNotMatch(landing.body.textContent,/Make our company the best in the world(?!\. Make no mistakes)/,'The joke title is only ever quoted as the ticket text');
 // The workspace shell paints a skeleton before any script runs, then renders from the worker's saved state.
 const shell=fs.readFileSync('app/workspace.html','utf8');assert.match(shell,/class="pr-row ghost"/);
 const dom=new JSDOM(shell,{url:'https://pr-trailer.vercel.app/workspace',runScripts:'outside-only'}),w=dom.window,calls=[];
 w.matchMedia=()=>({matches:true});
 const row={id:'KASSA-01',title:'Mask account numbers',ask:'Mask',repo:'13shreyansh/tieto-nordbank-payments',number:111,github:'https://github.com/13shreyansh/tieto-nordbank-payments/pull/111',branch:'agent/kassa-01',agent:'Codex',kind:'clean',outside:false,status:'unmeasured',written:55,kept:null,tests:null,passed:null,readLines:0,risk:[],createdAt:new Date().toISOString(),updatedAt:new Date().toISOString(),headSha:'fb552ac492331e97'};
 w.fetch=async(url,opts)=>{calls.push({url:String(url),opts});return{ok:true,json:async()=>({account:'13shreyansh',prs:[row],merged:[],returned:[],blocked:[],batch:null,syncedAt:new Date().toISOString(),session:{resetting:false,pristine:true}})}};
 for(const path of ['review.js','app.js'])w.eval(fs.readFileSync('app/'+path,'utf8'));
 await new Promise(r=>setTimeout(r,20));const d=w.document;
 assert.equal(calls[0].url,'/api/enter','The first call is the in-memory session entry, not a GitHub sync');assert.ok(JSON.parse(calls[0].opts.body).visitor);
 assert.equal(d.querySelectorAll('.pr-row:not(.ghost)').length,1);assert.equal(d.querySelectorAll('button.primary').length,1);assert.match(d.querySelector('button.primary').textContent,/Trim all/);
 assert.equal(d.querySelector('.row-meta a').getAttribute('href'),row.github);assert.match(d.querySelector('.row-meta').textContent,/#111 opened .* by Codex · agent\/kassa-01/);
 assert.equal(d.querySelectorAll('input[type="password"]').length,0);assert.ok(d.getElementById('pr-link'));
 d.getElementById('account-button').click();assert.ok(d.querySelector('[data-action="reset-ask"]'));assert.ok(d.querySelector('[data-action="signout"]'));
 d.querySelector('[data-action="reset-ask"]').click();assert.equal(calls.filter(c=>c.url==='/api/reset').length,0,'Reset asks first');
 d.querySelector('[data-action="reset-now"]').click();await new Promise(r=>setTimeout(r,5));assert.equal(calls.filter(c=>c.url==='/api/reset').length,1);
 dom.window.close();console.log('Static landing and workspace shell DOM passed. Deployed Chromium E2E is the flow acceptance test.');
})().catch(e=>{console.error(e);process.exitCode=1});
