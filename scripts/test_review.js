const assert=require('node:assert/strict'),R=require('../app/review.js'),fs=require('fs');
const d=JSON.parse(fs.readFileSync('app/evidence/manifest.json','utf8'));
let s=R.initial();assert.equal(R.count(d,s),d.totals.written);
s=R.apply(d,s,{type:'finish',id:d.prs[0].id});assert.equal(s.finished.length,0);
s=R.apply(d,s,{type:'trim'});assert.equal(R.count(d,s),d.totals.needYou);
for(const p of d.prs.filter(p=>p.status==='proven'))s=R.apply(d,s,{type:'finish',id:p.id});
assert.equal(s.finished.length,19);assert.equal(R.remaining(d,s).length,4);
const prev=R.count(d,s);s=R.apply(d,s,{type:'return',id:'KASSA-CAP'});assert.equal(R.count(d,s),prev-6);
s=R.apply(d,s,{type:'undo'});assert.equal(R.count(d,s),prev);
s=R.apply(d,s,{type:'block',id:'KASSA-INTERN'});assert.equal(R.count(d,s),prev-d.prs.find(p=>p.id==='KASSA-INTERN').readLines);
s=R.apply(d,s,{type:'undo'});assert.equal(s.blocked.length,0);
for(const id of ['AIDEV-9','AIDEV-24','KASSA-CAP','KASSA-INTERN']){const before=s.finished.length;s=R.apply(d,s,{type:'finish',id});assert.equal(s.finished.length,before);}
const first=d.prs[0].id,same=R.apply(d,s,{type:'finish',id:first});assert.equal(same.finished.length,s.finished.length);
console.log('State transitions passed: trim, 19 finishes, fee return, block, undo, unsafe finish prevention.');
for(const p of d.prs.filter(p=>p.status!=='intern')){
 const report=JSON.parse(fs.readFileSync('app/'+p.evidence));
 const result={...report,id:p.id,tests:p.tests,passed:p.passed,measured:true};
 assert.equal(R.verifyRun(p,result),true);
 assert.equal(R.verifyRun(p,{...result,patchSha256:'changed-but-same-totals'}),false);
 assert.equal(R.verifyRun(p,{...result,controls:[]}),false);
 if(p.heldOut)assert.equal(R.verifyRun(p,{...result,heldOut:{exitCode:0,tests:1,passed:1}}),false);
}
console.log('Exact patch identity, needed controls and held-out failure checks passed.');
