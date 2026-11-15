// Deployed check: a visitor leaves the workspace used (tab closed, no sign out); a new visitor must get the start state.
const {chromium}=require('playwright');const BASE=process.env.BASE||'https://pr-trailer.vercel.app';
(async()=>{
 const browser=await chromium.launch(),errors=[];
 const a=await browser.newContext({viewport:{width:1440,height:900}}),pa=await a.newPage();pa.on('pageerror',e=>errors.push(e.message));
 await pa.goto(BASE+'/workspace');await pa.waitForSelector('.pr-row:not(.ghost)');await pa.click('.row-title[data-id="KASSA-CAP"]');await pa.click('[data-action="recheck"]');await pa.waitForSelector('.lamps',{timeout:90000});
 await pa.click('[data-action="inbox"]');await pa.waitForSelector('.pr-row .solid');const used=await pa.locator('.subline').innerText();await a.close();
 await new Promise(r=>setTimeout(r,95000)); // the first visitor's polls stop; after 90 s the workspace no longer counts as in use
 const b=await browser.newContext({viewport:{width:1440,height:900}}),pb=await b.newPage();pb.on('pageerror',e=>errors.push(e.message));pb.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
 const t=Date.now();await pb.goto(BASE+'/workspace');await pb.waitForSelector('.waiting-title');const first=await pb.locator('.waiting-title').innerText().catch(()=>'');
 await pb.waitForFunction(()=>document.querySelectorAll('.pr-row:not(.ghost)').length===23&&!document.querySelector('.pr-row .solid')&&document.querySelector('.subline')?.textContent==='None trimmed yet.',null,{timeout:300000});
 console.log(JSON.stringify({leftAs:used,newVisitorSaw:first,startStateAfterMs:Date.now()-t,errors}));
 await pb.click('#account-button');await pb.click('[data-action="signout"]');await pb.waitForURL(BASE+'/');await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
