/* DOM interaction checks. These do not claim real-browser layout or console verification. */
const {JSDOM}=require('jsdom'),fs=require('fs'),assert=require('node:assert/strict');
const fixture=JSON.parse(fs.readFileSync('app/evidence/manifest.json','utf8'));
const pause=()=>new Promise(r=>setTimeout(r,0));
async function setup(story=true,width=1440){
 const dom=new JSDOM('<div id="app"></div>',{url:'https://pr-trailer.vercel.app/'+(story?'?story=1':''),runScripts:'outside-only'}),w=dom.window;
 w.matchMedia=()=>({matches:true});Object.defineProperty(w,'innerWidth',{value:width,writable:true});w.document.fonts={ready:Promise.resolve()};w.URL.createObjectURL=()=> 'blob:test';w.URL.revokeObjectURL=()=>{};
 w.fetch=async(url,opts)=>{const data=JSON.parse(opts.body);if(url==='/api/finish')return {ok:true,json:async()=>({ids:data.ids,measured:true,tests:3,passed:3,commit:'abc',branch:'tieto/approved',zipBase64:'emlw'})};const p=fixture.prs.find(p=>p.id===data.id),report=JSON.parse(fs.readFileSync('app/'+p.evidence));return {ok:true,json:async()=>p.status==='intern'?{id:p.id,written:p.written,kept:0,tests:p.tests,passed:p.passed,measured:true,checks:report.checks,final:report.combined}:{...report,id:p.id,tests:p.tests,passed:p.passed,measured:true}};};
 for(const file of ['fixture.js','review.js','app.js'])w.eval(fs.readFileSync('app/'+file,'utf8'));
 await pause();return dom;
}
function key(w,key,code=key){w.document.dispatchEvent(new w.KeyboardEvent('keydown',{key,code,bubbles:true}));}
function click(w,selector){const el=w.document.querySelector(selector);assert.ok(el,'Missing '+selector);el.click();}
(async()=>{
 for(const width of [1440,390]){
  const dom=await setup(true,width),w=dom.window,d=w.document;
  assert.equal(d.querySelectorAll('.pr-row').length,23);assert.equal(d.querySelectorAll('.segment.solid').length,0);assert.equal(d.querySelectorAll('button.primary').length,1);assert.equal(d.querySelectorAll('a[href="?story=1"],a[href="?story=auto"]').length,0);
  if(width===390)assert.match(d.querySelector('.scale').textContent,/600 lines/);
  key(w,'2');assert.equal(d.querySelectorAll('.pr-row.current').length,1);assert.equal(d.querySelectorAll('button.primary').length,1);
  for(let i=0;i<19;i++)key(w,'Enter');
  assert.equal(d.querySelectorAll('.pr-row').length,4);assert.match(d.querySelector('.footline').textContent,/19 finished/);
  click(w,'[data-action="open"][data-id="KASSA-CAP"]');await pause();click(w,'[data-action="panel"]');assert.equal(d.querySelectorAll('.code-line').length,6);assert.equal(d.querySelectorAll('.code-line.marked').length,1);
  click(w,'[data-action="return"]');assert.equal(d.querySelectorAll('.pr-row').length,3);
  click(w,'[data-action="open"][data-id="KASSA-INTERN"]');await pause();assert.equal(d.querySelectorAll('.intern-check .lamp.failed').length,3);click(w,'[data-action="block"]');assert.ok(d.querySelector('.barrier'));assert.match(d.querySelector('.actions').textContent,/Blocked locally/);
  key(w,'r');assert.equal(d.querySelectorAll('.pr-row').length,23);for(let i=0;i<5;i++)key(w,' ','Space');assert.match(d.querySelector('.close-frame').textContent,/Every line earns/);
  dom.window.close();
 }
 const normal=await setup(false),w=normal.window,d=w.document;click(w,'[data-action="trim"]');for(let i=0;i<8;i++)await pause();
 assert.equal(d.querySelectorAll('.pr-row.current').length,1);
 click(w,'[data-action="finish"]');for(let i=0;i<4;i++)await pause();assert.ok(d.querySelector('[data-action="branch"]'));
 click(w,'[data-action="undo"]');assert.equal(d.querySelector('[data-action="branch"]'),null,'Undo must invalidate old branch artifact');
 // A pending Finish must not let Undo change the baseline signed into its response.
 click(w,'[data-action="finish"]');for(let i=0;i<4;i++)await pause();
 const original=w.fetch;let release;
 w.fetch=(url,opts)=>url==='/api/finish'?new Promise(resolve=>{release=()=>resolve({ok:true,json:async()=>({ids:JSON.parse(opts.body).ids,measured:true,tests:3,passed:3,commit:'next',branch:'tieto/approved',zipBase64:'emlw'})});}):original(url,opts);
 click(w,'[data-action="finish"]');click(w,'[data-action="undo"]');
 assert.match(d.querySelector('.footline').textContent,/1 finished/);release();for(let i=0;i<4;i++)await pause();assert.match(d.querySelector('.footline').textContent,/2 finished/);
 normal.window.close();
 console.log('DOM checks passed at1440 and390: cold/trim/19finishes/cap/panel/intern/block/story-reset/finish/undo. Layout remains real-browser unverified.');
})().catch(e=>{console.error(e);process.exitCode=1;});
