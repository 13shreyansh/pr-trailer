// Baseline capture of the deployed site before the rebuild: screenshots and paint timings.
const {chromium}=require('playwright');const path=require('path');
const BASE=process.env.BASE||'https://pr-trailer.vercel.app',OUT=path.join(__dirname,'../../screenshots/fable/before');
(async()=>{
 const browser=await chromium.launch();const out={};
 for(const [name,vp] of [['1440',{width:1440,height:900}],['390',{width:390,height:844}]]){
  const ctx=await browser.newContext({viewport:vp});const page=await ctx.newPage();const reqs=[];
  page.on('requestfinished',async r=>{const t=r.timing();reqs.push([r.url().replace(BASE,''),Math.round(t.responseEnd)]);});
  let t0=Date.now();await page.goto(BASE+'/',{waitUntil:'commit'});
  await page.waitForSelector('.start h1',{timeout:120000});const startVisible=Date.now()-t0;
  const fcp=await page.evaluate(()=>new Promise(r=>{const e=performance.getEntriesByName('first-contentful-paint')[0];if(e)r(e.startTime);else new PerformanceObserver(l=>r(l.getEntries()[0].startTime)).observe({type:'paint',buffered:true});}));
  await page.screenshot({path:`${OUT}/${name}-start.png`});
  t0=Date.now();await page.click('[data-action="workspace"]');await page.waitForSelector('.pr-row',{timeout:180000});const wsClick=Date.now()-t0;
  await page.waitForTimeout(800);await page.screenshot({path:`${OUT}/${name}-workspace.png`,fullPage:name==='390'});
  const state=await page.evaluate(()=>({counter:document.querySelector('.counter')?.innerText,sub:document.querySelector('.subline')?.innerText,rows:document.querySelectorAll('.pr-row').length}));
  // open first row
  await page.click('.pr-row .row-title');await page.waitForSelector('.ledger-bar');await page.waitForTimeout(2500);await page.screenshot({path:`${OUT}/${name}-ledger.png`});
  // cold deep load of /workspace in a fresh context
  const ctx2=await browser.newContext({viewport:vp});const p2=await ctx2.newPage();t0=Date.now();await p2.goto(BASE+'/workspace',{waitUntil:'commit'});await p2.waitForSelector('.pr-row',{timeout:180000});const wsCold=Date.now()-t0;
  const fcp2=await p2.evaluate(()=>performance.getEntriesByName('first-contentful-paint')[0]?.startTime);
  out[name]={startVisibleMs:startVisible,startFcpMs:Math.round(fcp),workspaceAfterClickMs:wsClick,workspaceColdRowsMs:wsCold,workspaceColdFcpMs:Math.round(fcp2||0),state,reqs:reqs.slice(0,12)};
  await ctx.close();await ctx2.close();
 }
 console.log(JSON.stringify(out,null,1));await browser.close();
})();
