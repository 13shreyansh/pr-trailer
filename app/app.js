'use strict';
(() => {
 const R=globalThis.TietoReview,root=document.getElementById('app');
 const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const format=n=>Number(n||0).toLocaleString('en-US');
 const clock=value=>value?new Intl.DateTimeFormat('en-GB',{hour:'2-digit',minute:'2-digit'}).format(new Date(value)):'';
 const small=()=>innerWidth<=600;
 const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
 let data=null,view=location.pathname==='/workspace'?'inbox':'start',selected=null,panel=false,riskIndex=0,opening=false,pending=null,fieldError='',error='',fresh=new Set(),collapsed=false;
 let shown=new Set(),lifting=null,restored=new Set(),timers=[],pollTimer=null,foldNow=null;
 const visited=new Set(),notes=new Map();
 const arrow='<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="m12 5-7 7 7 7M5 12h15"/></svg>';
 const find=id=>data?.prs.find(p=>p.id===id);
 const running=()=>!!data?.batch?.running;
 const hasResults=()=>data?.prs.some(R.done);
 const first=()=>R.first(data);
 const digits=n=>[...format(n)].map(c=>`<span${c===','?' class="comma"':''}>${c}</span>`).join('');
 async function request(path,body){
  const response=await fetch('/api/'+path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
  let value;try{value=await response.json();}catch{throw Error('Could not reach the test runner. Try again.');}
  if(!response.ok)throw Error(value.error||'The request failed. Try again.');return value;
 }
 function absorb(next){
  fresh=new Set(next.prs.filter(p=>R.done(p)&&!data?.prs.some(old=>old.id===p.id&&old.measuredAt===p.measuredAt)).map(p=>p.id));
  const completed=running()&&!next.batch?.running;
  data=next;
  if(completed){collapsed=false;render();setTimeout(()=>{collapsed=true;render();},reduced?150:480);}
  else if(!running())collapsed=true;
  render();schedulePoll();
 }
 function schedulePoll(){clearTimeout(pollTimer);if(view!=='start')pollTimer=setTimeout(poll,running()?600:4000);}
 async function poll(){try{absorb(await request('status'));}catch{schedulePoll();}}
 function header(){
  return `<header class="top-shell"><div class="top"><button class="brand plain" data-action="home">Tieto</button><span class="workspace-name">Nordbank · payments</span><div class="top-right"><form class="pr-form" id="pr-form"><input id="pr-link" type="url" inputmode="url" placeholder="Paste a GitHub PR link" aria-label="Paste a GitHub PR link" autocomplete="off" spellcheck="false" ${pending==='add'?'disabled':''}>${fieldError?`<span class="field-error" role="alert">${escape(fieldError)}</span>`:''}</form><span class="sync">${data?.syncedAt?'Synced '+clock(data.syncedAt):''}</span><span class="account">${data?.account?'Merging as @'+escape(data.account):''}</span></div></div></header>`;
 }
 function start(){return `<main class="start"><h1>Tieto</h1><button class="primary" data-action="workspace" ${opening?'disabled':''}>${opening?'Opening…':'Try the demo workspace (Nordbank payments)'}</button><a href="#pr-link" class="measure-link" data-action="focus-link">Measure any public GitHub PR</a>${error?`<p class="inline-error" role="alert">${escape(error)}</p>`:''}</main>`;}
 function bar(p){
  const full=small()?600:1200,parts=R.segments(p,full,collapsed),resolved=fresh.has(p.id);
  return parts.map((part,i)=>`<span class="track-line">${part.solid?`<i class="segment solid ${resolved?'resolve':''}" style="width:${part.solid/full*100}%;min-width:6px">${p.risk?.length&&Number.isFinite(p.riskPosition)&&i===0?`<i class="notch" style="left:clamp(0px,calc(${(p.riskPosition||0)*100}% - 3px),calc(100% - 6px))"></i>`:''}</i>`:''}${part.unchecked?`<i class="segment hatch ${R.done(p)&&p.verdict==='proven'&&!collapsed?'cut-away':''}" style="width:calc(${part.unchecked/full*100}% - ${part.solid?2:0}px);min-width:6px">${p.kind==='junior'&&R.done(p)&&i===0?'<i class="break" style="left:24%"></i><i class="break" style="left:49%"></i><i class="break" style="left:74%"></i>':''}${p.status==='blocked'&&i===parts.length-1?'<i class="barrier"></i>':''}</i>`:''}</span>`).join('');
 }
 function row(p,current){
  let state='Not trimmed';
  if(p.status==='queued')state='Queued';else if(p.status==='running')state='Trimming…';else if(p.status==='unsupported')state="Can't run this repo's tests here";else if(p.status==='error')state='<button class="plain" data-action="retry" data-id="'+p.id+'">Couldn\'t run tests · Retry</button>';else if(p.status==='blocked')state='Blocked';else if(R.done(p))state=p.verdict==='proven'?'Proven':'Needs you · '+p.readLines;
  if(current)state=`<button class="primary" data-action="finish" data-id="${p.id}" ${pending?'disabled':''}>${pending==='finish'?'Finishing…':'Finish'}</button><span class="key-hint">Enter</span>`;
  const hint=current?`<span class="merge-hint">Merges ${p.kept} of ${format(p.written)} lines into main</span>`:'';
  const visibleTotal=R.done(p)&&p.verdict==='proven'&&collapsed?p.kept:p.written,tail=visibleTotal%600;
  return `<div class="pr-row ${visibleTotal&&(tail>430||tail===0)?'tail-full':''} ${current?'current':''} ${p.status==='running'?'trimming':''} ${p.status==='blocked'?'blocked':''}" data-id="${p.id}"><button class="row-title" data-action="open" data-id="${p.id}"><span class="title-text">${escape(p.title)}</span><span class="pr-number">${p.outside?escape(p.repo)+' ':''}#${p.number}</span></button><div class="track" role="button" tabindex="0" data-action="open" data-id="${p.id}" aria-label="Open ${escape(p.title)}">${bar(p)}${hint}</div><span class="row-count">${R.done(p)&&p.kind!=='junior'?format(p.kept)+' of ':''}${format(p.written)}</span><span class="row-state ${p.status==='blocked'?'blocked-label':''}">${state}</span></div>`;
 }
 function inbox(){
  const prs=R.remaining(data),allDone=R.complete(data),current=!running()?first():null,proven=prs.filter(R.proven).length,needs=prs.filter(p=>R.done(p)&&p.verdict!=='proven'&&p.status!=='blocked').length;
  const sub=running()?`Trimming ${Math.min(data.batch.completed+1,data.batch.total)} of ${data.batch.total} · ${format(data.batch.testsRun)} tests run`:allDone?`${proven} of ${prs.length} proven. ${needs} need you.`:hasResults()?`${prs.filter(R.done).length} of ${prs.length} trimmed.`:'None trimmed yet.';
  const own=prs.filter(p=>!p.outside),outside=prs.filter(p=>p.outside);
  return `<main class="shell"><section class="summary"><div><h1 class="counter"><span class="digits" aria-label="${R.count(data)}">${digits(R.count(data))}</span><span class="counter-words">${running()||hasResults()&&!allDone?'lines still to check.':allDone?'lines need you.':`lines written by agents in ${prs.length} open PRs.`}</span></h1><p class="subline">${sub}</p></div><div class="summary-action">${running()?'<button class="plain" data-action="stop">Stop</button>':allDone&&data?.trimmedAt?`<span>Trimmed ${clock(data.trimmedAt)} · <button class="plain" data-action="trim">Run again</button></span>`:`<button class="primary" data-action="trim" ${pending?'disabled':''}>Trim all</button><span class="key-hint">T</span>`}</div></section><div class="keyline"><div class="keys"><span class="key"><i class="sample solid"></i>Needed: a test breaks without it</span><span class="key"><i class="sample hatch"></i>Unchecked: every test passes without it</span></div><span class="scale">Full width is ${small()?'600':'1,200'} lines. Longer PRs wrap.<br>Under 12 lines is drawn at 6 px.</span></div>${error?`<p class="inline-error" role="alert">${escape(error)}</p>`:''}<section class="rows" aria-label="Pull requests">${own.map(p=>row(p,p.id===current?.id)).join('')}${outside.length?`<div class="outside-rule">Outside this workspace</div>${outside.map(p=>row(p,false)).join('')}`:''}${!prs.length?'<p class="empty">Nothing to sign. New agent PRs appear here.</p>':''}</section><footer class="footline"><span>${data?.merged.length||0} merged${data?.merged.length?' · <button class="plain" data-action="revert">Revert last merge</button>':''}</span><span>Measured</span></footer></main>`;
 }
 const extra=p=>(p.blocks||[]).filter(b=>!b.needed);
 function namedBar(p){
  const blocks=(p.blocks||[{id:'unknown',name:'Not trimmed',lines:p.written,needed:false}]).filter(b=>b.needed||p.kind==='junior'||shown.has(b.id)||restored.has(b.id));
  return `<div class="ledger-bar ${p.status==='blocked'?'blocked':''}">${blocks.map((b,i)=>`<span class="named-block ${lifting===b.id?'lifting':''}" style="width:${b.lines/p.written*100}%"><span class="segment ${b.needed?'solid':'hatch'}">${b.needed&&p.risk?.length&&Number.isFinite(p.riskPosition)?`<button class="notch" data-action="panel" aria-label="Read risky lines" style="left:clamp(0px,calc(${(p.riskPosition||0)*100}% - 3px),calc(100% - 6px))"></button>`:''}${p.kind==='junior'&&R.done(p)?'<i class="break" style="left:24%"></i><i class="break" style="left:49%"></i><i class="break" style="left:74%"></i>':''}${p.status==='blocked'?'<i class="barrier"></i>':''}</span><span class="block-label ${b.lines/p.written*960<60?'with-leader':''}">${escape(b.name)} · ${format(b.lines)}</span></span>`).join('')}</div><span class="ledger-scale">Full width is the ${format(p.written)} lines this PR wrote.</span>`;
 }
 function lamps(p){
  const grouped=p.tests>48,n=grouped?p.lampFiles:p.tests;
  return `<span class="lamps" aria-hidden="true">${Array.from({length:n||0},()=>`<i class="lamp ${['queued','running'].includes(p.status)?'running':p.kind==='junior'?'failed':''}"></i>`).join('')}</span><span class="proof-copy">${p.passed} of ${p.tests} tests pass on the trimmed PR.${grouped?' Lamps represent test files.':''}</span>`;
 }
 function proof(p){return `<div class="ledger-line proof"><dt>Proof</dt><dd>${p.tests===null?`<span>${p.status==='running'?'Trimming…':p.status==='queued'?'Queued':'Not trimmed'}</span>`:lamps(p)}<div class="proof-links">${p.tests!==null?`<a href="/api/proof?id=${encodeURIComponent(p.id)}" target="_blank" rel="noopener">Recorded commands & results</a>`:''}<button class="plain" data-action="recheck" ${running()||pending?'disabled':''}>Re-run tests</button></div></dd></div>`;}
 function riskPanel(p){
  const risk=p.risk[riskIndex]||p.risk[0];if(!risk)return '';
  return `<section class="risk-panel"><div class="risk-head"><span>${escape(risk.path)} · ${risk.start}–${risk.start+risk.lines.length-1}</span>${p.risk.length>1?'<button class="plain" data-action="next-risk">Next check</button>':'<button class="plain" data-action="panel">Close</button>'}</div><div class="code">${risk.lines.slice(0,8).map((line,i)=>`<span class="code-line ${i===risk.marked?'marked':''}"><span class="code-number">${risk.start+i}</span>${escape(line)}</span>`).join('')}</div><p class="risk-note">${escape(risk.note)}</p></section>`;
 }
 function ledger(){
  const p=find(selected);if(!p){selected=null;view='inbox';return inbox();}
  const junior=p.kind==='junior',isDone=R.done(p),outside=p.outside;
  let action='';
  if(p.status==='blocked')action=`<div class="sent-note">${escape(p.sentMessage)}<br><button class="plain" data-action="unblock">Undo block</button></div>`;
  else if(!isDone)action=`<span class="action-copy">${p.status==='unsupported'?"Can't run this repo's tests here":p.status==='running'?'Trimming…':p.status==='queued'?'Queued':'Not trimmed'}</span>${!running()?'<button class="primary" data-action="recheck">Trim all</button>':''}`;
  else if(outside)action=`<span class="action-copy">${escape(p.note)}</span><a class="primary" href="/api/patch?id=${encodeURIComponent(p.id)}" download="trimmed.patch">Download trimmed patch</a>`;
  else if(junior)action=`<button class="primary" data-action="block" ${pending?'disabled':''}>${pending==='block'?'Blocking…':'Block and ask what they meant'}</button><span class="key-hint">B</span>`;
  else if(R.proven(p))action=`<span class="action-copy">Merges ${p.kept} of ${p.written} lines into main</span><button class="primary" data-action="finish" data-id="${p.id}" ${pending?'disabled':''}>${pending==='finish'?'Finishing…':'Finish'}</button><span class="key-hint">Enter</span>`;
  else action=`<div class="action-copy"><div contenteditable="true" role="textbox" aria-label="Note to the agent" class="editable" id="agent-note">${escape(notes.get(p.id)??p.note)}</div></div><button class="primary" data-action="return" ${pending?'disabled':''}>${pending==='return'?'Sending…':'Send back trimmed'}</button><span class="key-hint">S</span>`;
  return `<main class="ledger ${panel?'risk-open':''}"><nav class="ledger-nav"><button class="plain" data-action="inbox">${arrow} Inbox · ${data.prs.length} left</button></nav><h1>${escape(p.title)}</h1><div class="metadata"><span>${escape(p.agent)}</span><span>${escape(p.repo)} #${p.number}</span><time>${new Date(p.updatedAt).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'})}</time><a href="${p.github}" target="_blank" rel="noopener">Check on GitHub</a><span>Measured</span></div>${namedBar(p)}${panel?'<button class="mobile-back" data-action="panel">Back to ledger</button>':''}<dl class="ledger-lines"><div class="ledger-line"><dt>Asked</dt><dd>"${escape(p.ask)}"${junior?` <span class="caption">This can't be checked. No test can tell when it's done.</span>`:''}</dd></div>${isDone?`<div class="ledger-line"><dt>Did</dt><dd>${junior?'Changes login, pricing and a database migration.':`Did it in <strong>${p.kept}</strong> lines. ${p.neededFailures} failing checks without them.`}</dd></div><div class="ledger-line"><dt>Extra</dt><dd>${junior?'Nothing is provably needed.':p.unchecked?`${format(p.unchecked)} lines nothing checks, extra or untested. All ${p.tests} tests pass without them.<br>${extra(p).map(b=>`<button class="extra-chip" data-action="restore" data-block="${escape(b.id)}">${escape(b.name)} · ${format(b.lines)}</button>`).join('')}`:'Nothing extra.'}</dd></div><div class="ledger-line"><dt>Read these</dt><dd>${junior?`<span class="check-summary">3 changes break production.</span><div class="junior-checks">${p.risk.map((r,i)=>`<button class="plain" data-action="risk" data-index="${i}">${escape(r.note)}</button>`).join('')}</div>`:p.risk.length?`<button class="read-link" data-action="panel">${p.readLines} lines to read.${p.kind==='cap'?' 1 looks wrong.':''}</button>`:'Nothing risky.'}</dd></div>`:''}${!panel?proof(p):''}</dl>${panel?riskPanel(p)+`<dl>${proof(p)}</dl>`:''}${error?`<p class="inline-error" role="alert">${escape(error)}</p>`:''}<div class="actions">${action}</div></main>`;
 }
 function render(){
  const focused=document.activeElement?.id;
  if(focused==='agent-note'&&!pending)return;
  const selection=document.getElementById('pr-link')?.value||'';
  const note=document.getElementById('agent-note')?.textContent;
  root.innerHTML=header()+(view==='start'?start():view==='ledger'?ledger():inbox());
  if(document.getElementById('pr-link'))document.getElementById('pr-link').value=selection;
  if(note&&focused==='agent-note'&&document.getElementById('agent-note'))document.getElementById('agent-note').textContent=note;
  if(focused&&document.getElementById(focused)){document.getElementById(focused).focus({preventScroll:true});}
  fresh.clear();
 }
 async function enter(){if(opening)return;opening=true;error='';render();try{absorb(await request('workspace'));view='inbox';history.pushState({},'','/workspace');}catch(e){error=e.message;}opening=false;render();schedulePoll();}
 async function action(name,body={}){
  if(pending)return;pending=name;error='';render();
  try{const next=await request(name,body);absorb(next);if(['finish','return','revert'].includes(name)){view='inbox';selected=null;panel=false;history.replaceState({},'','/workspace');}if(name==='block')panel=false;}
  catch(e){error=name==='finish'?"Couldn't merge. Check on GitHub, then try again.":e.message;}
  pending=null;render();schedulePoll();
 }
 function open(id){
  const p=find(id);if(!p)return;timers.forEach(clearTimeout);timers=[];selected=id;view='ledger';panel=false;riskIndex=0;restored=new Set();shown=new Set(extra(p).map(b=>b.id));lifting=null;error='';history.pushState({},'','/workspace/pr/'+encodeURIComponent(id));render();
  if(!visited.has(id)&&R.done(p)&&p.kind!=='junior'){
   extra(p).forEach((b,i)=>{timers.push(setTimeout(()=>{if(selected!==id)return;lifting=b.id;render();timers.push(setTimeout(()=>{shown.delete(b.id);lifting=null;render();},reduced?150:320));},i*500+100));});visited.add(id);
  }else{shown.clear();render();}
 }
 async function add(form){
  const input=form.querySelector('input'),url=input.value.trim();fieldError='';pending='add';render();
  try{if(!data||!data.syncedAt)data=await request('workspace');absorb(await request('add',{url}));view='inbox';selected=null;panel=false;history.pushState({},'','/workspace');document.getElementById('pr-link').value='';}
  catch(e){fieldError=e.message==='Not a public PR link.'?e.message:e.message;}
  pending=null;render();schedulePoll();
 }
 root.addEventListener('submit',e=>{if(e.target.id==='pr-form'){e.preventDefault();add(e.target);}});
 root.addEventListener('click',e=>{
  const el=e.target.closest('[data-action]');if(!el)return;const a=el.dataset.action,id=el.dataset.id;
  if(a==='workspace')enter();
  else if(a==='home'){view='start';selected=null;history.pushState({},'','/');render();}
  else if(a==='focus-link'){e.preventDefault();document.getElementById('pr-link').focus();}
  else if(a==='inbox'){view='inbox';selected=null;panel=false;error='';history.pushState({},'','/workspace');render();}
  else if(a==='open')open(id);
  else if(a==='trim')action('measure');
  else if(a==='stop')action('stop');
  else if(a==='retry'||a==='recheck')action('measure',{ids:[id||selected]});
  else if(a==='finish')action('finish',{id:id||selected});
  else if(a==='return')action('return',{id:selected,note:document.getElementById('agent-note')?.textContent||find(selected)?.note});
  else if(a==='block')action('block',{id:selected});
  else if(a==='unblock')action('unblock',{id:selected});
  else if(a==='revert')action('revert');
  else if(a==='panel'){panel=!panel;render();}
  else if(a==='risk'){riskIndex=Number(el.dataset.index);panel=true;render();}
  else if(a==='next-risk'){riskIndex=(riskIndex+1)%find(selected).risk.length;render();}
  else if(a==='restore'){restored.has(el.dataset.block)?restored.delete(el.dataset.block):restored.add(el.dataset.block);render();}
 });
 root.addEventListener('input',e=>{if(e.target.id==='agent-note')notes.set(selected,e.target.textContent);});
 document.addEventListener('keydown',e=>{
  if(e.target.closest?.('input,textarea,[contenteditable]'))return;
  if(e.key==='Enter'&&e.target.matches?.('[role="button"]')){e.preventDefault();e.target.click();return;}
  if(view!=='start'&&e.key==='Enter'&&!e.target.closest?.('button,a')){const p=view==='ledger'?find(selected):first();if(p&&R.proven(p)&&!running()){e.preventDefault();action('finish',{id:p.id});}}
  if(e.key.toLowerCase()==='t'&&view!=='start'&&!running())action('measure');
  if(e.key.toLowerCase()==='o'&&view!=='start'){const p=data?.prs.find(p=>R.done(p)&&p.verdict==='needs-you'&&!p.outside);if(p)open(p.id);}
  if(e.key.toLowerCase()==='n'&&selected&&find(selected)?.risk?.length){panel=!panel;render();}
  if(e.key.toLowerCase()==='s'&&selected&&find(selected)?.kind==='cap'&&R.done(find(selected)))action('return',{id:selected,note:document.getElementById('agent-note')?.textContent||find(selected).note});
  if(e.key.toLowerCase()==='b'&&selected&&find(selected)?.kind==='junior'&&R.done(find(selected)))action('block',{id:selected});
 });
 addEventListener('resize',render);
 addEventListener('popstate',()=>{selected=null;panel=false;view=location.pathname==='/'?'start':'inbox';render();schedulePoll();});
 async function init(){await Promise.all([document.fonts.ready,...(document.fonts.load?[document.fonts.load('400 14px Archivo'),document.fonts.load('400 13px "JetBrains Mono"')]:[])]);try{data=await request(view==='start'?'status':'workspace');}catch(e){error=e.message;}render();schedulePoll();}
 init();
})();
