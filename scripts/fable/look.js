// Quick visual pass (local or deployed): landing and the untouched workspace at both widths. No writes.
const {chromium}=require('playwright');const path=require('path'),fs=require('fs');
const BASE=process.env.BASE||'http://localhost:4331',OUT=process.env.OUT||path.join(__dirname,'../../screenshots/fable/work');fs.mkdirSync(OUT,{recursive:true});
(async()=>{
 const browser=await chromium.launch();const errors=[];
 for(const [name,vp] of [['1440',{width:1440,height:900}],['390',{width:390,height:844}]]){
  const ctx=await browser.newContext({viewport:vp,deviceScaleFactor:name==='390'?2:1});const page=await ctx.newPage();
  page.on('pageerror',e=>errors.push(name+' '+e.message));page.on('console',m=>{if(m.type()==='error')errors.push(name+' '+m.text())});
  await page.goto(BASE+'/',{waitUntil:'load'});await page.evaluate(()=>document.fonts.ready);
  await page.screenshot({path:`${OUT}/${name}-landing-first.png`});
  const h=await page.evaluate(()=>document.documentElement.scrollHeight);
  for(let y=0,i=0;y<h;y+=vp.height-60,i++){await page.evaluate(y=>scrollTo(0,y),y);await page.waitForTimeout(80);await page.screenshot({path:`${OUT}/${name}-landing-${String(i).padStart(2,'0')}.png`});}
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);if(overflow>0)errors.push(name+' landing overflows by '+overflow);
  await page.evaluate(()=>scrollTo(0,0));await page.click('.hero .primary');await page.waitForSelector('.pr-row:not(.ghost)',{timeout:60000});await page.waitForFunction(()=>/Synced/.test(document.querySelector('.sync')?.textContent||''),null,{timeout:60000});
  await page.screenshot({path:`${OUT}/${name}-inbox.png`,fullPage:true});
  const o2=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);if(o2>0)errors.push(name+' inbox overflows by '+o2);
  await page.click('#account-button');await page.screenshot({path:`${OUT}/${name}-menu.png`});await page.click('[data-action="reset-ask"]');await page.screenshot({path:`${OUT}/${name}-menu-confirm.png`});await page.keyboard.press('Escape');
  await page.click('.row-title[data-id="KASSA-CAP"]');await page.waitForSelector('.ledger-bar');await page.waitForTimeout(300);await page.screenshot({path:`${OUT}/${name}-ledger-untrimmed.png`});
  await ctx.close();
 }
 console.log(JSON.stringify({errors}));await browser.close();
})();
