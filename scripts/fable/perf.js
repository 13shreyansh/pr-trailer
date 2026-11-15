// Paint timings on the deployed URL. Cold browser context per run; no writes.
// FCP = the browser's first-contentful-paint entry. "rows" = wall clock from navigation start to the first real PR row.
const {chromium}=require('playwright');
const BASE=process.env.BASE||'https://pr-trailer.vercel.app',RUNS=Number(process.env.RUNS||5),ONLY=process.env.ONLY||'';
const median=a=>[...a].sort((x,y)=>x-y)[Math.floor(a.length/2)];
(async()=>{
 const browser=await chromium.launch(),out={};
 for(const [name,vp] of [['1440',{width:1440,height:900}],['390',{width:390,height:844}]]){
  const landing=[],lcp=[],shell=[],rows=[],api=[];
  for(let i=0;i<RUNS;i++){
   let ctx=await browser.newContext({viewport:vp}),page=await ctx.newPage(),calls=0;page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/'))calls++;});
   await page.goto(BASE+'/',{waitUntil:'load'});
   landing.push(await page.evaluate(()=>new Promise(r=>{new PerformanceObserver(l=>{const e=l.getEntriesByName('first-contentful-paint')[0];if(e)r(e.startTime);}).observe({type:'paint',buffered:true});setTimeout(()=>r(NaN),3000);})));
   lcp.push(await page.evaluate(()=>new Promise(r=>{new PerformanceObserver(l=>r(l.getEntries().at(-1).startTime)).observe({type:'largest-contentful-paint',buffered:true});setTimeout(()=>r(null),1500);})));
   api.push(calls);await ctx.close();
   if(ONLY==='landing')continue;
   ctx=await browser.newContext({viewport:vp});page=await ctx.newPage();
   await page.goto(BASE+'/workspace',{waitUntil:'commit'});await page.waitForSelector('.pr-row:not(.ghost)',{timeout:120000});
   rows.push(await page.evaluate(()=>performance.now()));shell.push(await page.evaluate(()=>new Promise(r=>{new PerformanceObserver(l=>{const e=l.getEntriesByName('first-contentful-paint')[0];if(e)r(e.startTime);}).observe({type:'paint',buffered:true});setTimeout(()=>r(NaN),3000);})));
   await page.waitForFunction(()=>/Synced/.test(document.querySelector('.sync')?.textContent||''),null,{timeout:120000});await ctx.close();
  }
  const r=a=>a.map(x=>Math.round(x));
  out[name]={runs:RUNS,landingFcpMs:{median:Math.round(median(landing)),all:r(landing)},landingLcpMs:{median:Math.round(median(lcp)),all:r(lcp)},landingApiCalls:api,...(rows.length?{workspaceSkeletonFcpMs:{median:Math.round(median(shell)),all:r(shell)},workspaceFirstRealRowsMs:{median:Math.round(median(rows)),all:r(rows)}}:{})};
 }
 console.log(JSON.stringify(out,null,1));await browser.close();
})();
