/* Additional live checks for Undo block, Revert, and the restored request. */
const {chromium,expect}=require('@playwright/test'),fs=require('fs'),path=require('path');
(async()=>{
 const browser=await chromium.launch(),context=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce'}),page=await context.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
 try{
  await page.goto('https://pr-trailer.vercel.app/workspace',{waitUntil:'networkidle'});await expect(page.locator('.footline')).toContainText('19 merged');
  await page.locator('.row-title[data-id="KASSA-INTERN"]').click();await page.getByRole('button',{name:'Undo block',exact:true}).click();await expect(page.getByRole('button',{name:'Block and ask what they meant',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Block and ask what they meant',exact:true}).click();await expect(page.getByRole('button',{name:'Undo block',exact:true})).toBeVisible();await page.getByRole('button',{name:/Inbox ·/}).click();
  await page.getByRole('button',{name:'Revert last merge',exact:true}).click();await expect(page.locator('.footline')).toContainText('18 merged',{timeout:60000});await expect(page.locator('.row-title[data-id="KASSA-19"]')).toBeVisible();
  await page.locator('.row-title[data-id="KASSA-19"]').click();await page.getByRole('button',{name:'Trim all',exact:true}).click();await expect(page.getByRole('button',{name:'Finish',exact:true})).toBeVisible({timeout:60000});
  await page.getByRole('button',{name:'Finish',exact:true}).click();await expect(page.locator('.footline')).toContainText('19 merged',{timeout:60000});expect(errors).toEqual([]);
  const status=await page.request.get('https://pr-trailer.vercel.app/api/status').then(r=>r.json());const report={undoBlock:true,reblock:true,reverted:true,retrimmed:true,remerged:true,errors,lastMerge:status.merged.at(-1),block:status.blocked.at(-1),measured:true};
  fs.writeFileSync(path.resolve('artifacts/e2e/controls-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
