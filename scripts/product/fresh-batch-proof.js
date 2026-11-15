// Action-specific deployed regression. Writes only to the isolated sponsor workspace.
const {chromium,expect}=require('@playwright/test'),fs=require('fs'),assert=require('node:assert/strict');
const base=process.env.TIETO_URL,expected=process.env.TIETO_COMMIT;
assert.equal(new URL(base).origin,'https://pr-trailer-sponsors.72.61.22.106.sslip.io');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:390,height:900},reducedMotion:'reduce'});
  const build=await page.request.get(base+'/build.json').then(r=>r.json());assert.equal(build.commit,expected);
  await page.goto(base+'/workspace');await expect(page.locator('.pr-row:not(.ghost)')).toHaveCount(23,{timeout:60000});
  const status=()=>page.request.get(base+'/api/status').then(r=>r.json());
  assert.equal((await status()).repo,'13shreyansh/tieto-nordbank-payments-sponsors');
  await page.getByRole('button',{name:'Trim all',exact:true}).click();
  await expect(page.getByRole('button',{name:'Run again',exact:true})).toBeVisible({timeout:180000});
  const before=await status(),oldIds=Object.fromEntries(before.prs.map(p=>[p.id,p.runId]));
  const request=page.waitForRequest(r=>new URL(r.url()).pathname==='/api/measure'&&r.method()==='POST');
  await page.getByRole('button',{name:'Run again',exact:true}).click();
  const payload=(await request).postDataJSON();assert.equal(payload.fresh,true);
  await expect(page.getByRole('button',{name:'Stop',exact:true})).toBeVisible();
  let actual;
  await expect.poll(async()=>{const s=await status();actual=s.prs.find(p=>p.status==='done'&&p.kind!=='junior'&&p.executionProvider==='modal'&&p.cachedMeasurement===false&&p.runId&&p.runId!==oldIds[p.id]&&p.tests>0);return Boolean(actual);},{timeout:180000}).toBe(true);
  await page.getByRole('button',{name:'Stop',exact:true}).click();await expect(page.getByRole('button',{name:'Stop',exact:true})).toHaveCount(0,{timeout:90000});
  await page.locator('.row-title[data-id="'+actual.id+'"]').click();await expect(page.locator('.proof-copy')).toContainText('tests pass');
  await page.screenshot({path:'screenshots/fable/390-fresh-batch-proof.png',fullPage:true});
  const receipt={sourceCommit:build.commit,url:base,measured:true,freshRequest:payload.fresh,id:actual.id,previousRunId:oldIds[actual.id],newRunId:actual.runId,measuredAt:actual.measuredAt,tests:actual.tests,passed:actual.passed,provider:actual.executionProvider,cachedMeasurement:actual.cachedMeasurement};
  await page.getByRole('button',{name:/Inbox ·/}).click();await page.locator('#account-button').click();await page.getByRole('menuitem',{name:'Reset workspace',exact:true}).click();await page.getByRole('menuitem',{name:'Reset now',exact:true}).click();
  await expect(page.locator('.subline')).toHaveText('None trimmed yet.',{timeout:420000});await expect(page.locator('.pr-row:not(.ghost)')).toHaveCount(23);receipt.restored=true;
  fs.writeFileSync('evidence/fresh-batch-live.json',JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt));
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1});
