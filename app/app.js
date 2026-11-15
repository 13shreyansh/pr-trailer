'use strict';
(() => {
 const R=globalThis.TietoReview,root=document.getElementById('app');
 const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const format=n=>Number(n||0).toLocaleString('en-US');
 const clock=value=>value?new Intl.DateTimeFormat('en-GB',{hour:'2-digit',minute:'2-digit'}).format(new Date(value)):'';
 const small=()=>innerWidth<=600;
 const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
 let data=null,view='inbox',selected=null,panel=false,riskIndex=0,opening=false,pending=null,fieldError='',error='',fresh=new Set(),collapsed=false;
 let shown=new Set(),lifting=null,restored=new Set(),timers=[],pollTimer=null,foldNow=null;
 let menu=false,confirmReset=false,syncing=false,offline=false,left=false;
 const REPO='13shreyansh/tieto-nordbank-payments',store=(()=>{try{return localStorage;}catch{return null;}})();
 const visitor=(()=>{let id=store?.getItem('tieto.visitor');if(!id||!/^[a-z0-9-]{8,64}$/.test(id)){id=globalThis.crypto?.randomUUID?.()||'v-'+Date.now().toString(36)+Math.random().toString(36).slice(2,12);try{store?.setItem('tieto.visitor',id);}catch{}}return id;})();
 const restoring=()=>!!data?.session?.resetting;
 function ago(value){
  const then=new Date(value),minutes=Math.max(0,Math.round((Date.now()-then)/60000));
  if(minutes<1)return 'just now';if(minutes<60)return minutes+' min ago';if(minutes<1440)return Math.round(minutes/60)+' h ago';if(minutes<43200)return Math.round(minutes/1440)+' d ago';
  return then.toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'});
 }
 const chevron='<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>';
 const external='<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>';
 const visited=new Set(),notes=new Map();
 const arrow='<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true"><path d="m12 5-7 7 7 7M5 12h15"/></svg>';
 const find=id=>data?.prs.find(p=>p.id===id);
 const running=()=>!!data?.batch?.running;
 const hasResults=()=>data?.prs.some(R.done);
 const first=()=>R.first(data);
 const digits=n=>[...format(n)].map(c=>`<span${c===','?' class="comma"':''}>${c}</span>`).join('');
 async function request(path,body){
  const response=await fetch('/api/'+path+(body===undefined?'?v='+visitor:''),{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify({...body,visitor})});
  let value;try{value=await response.json();}catch{throw Error('Could not reach the test runner. Try again.');}
  if(!response.ok)throw Error(value.error||'The request failed. Try again.');return value;
 }
 function absorb(next){
  fresh=new Set(next.prs.filter(p=>R.done(p)&&!data?.prs.some(old=>old.id===p.id&&old.measuredAt===p.measuredAt)).map(p=>p.id));
  const completed=running()&&!next.batch?.running;
  if(!next.session&&data?.session)next.session=data.session;
  data=next;offline=false;
  try{store?.setItem('tieto.snapshot',JSON.stringify({visitor,data:next}));}catch{}
  if(completed){collapsed=false;render();setTimeout(()=>{collapsed=true;render();},reduced?150:480);}
  else if(!running())collapsed=true;
  render();schedulePoll();
 }
 function schedulePoll(){clearTimeout(pollTimer);if(!left)pollTimer=setTimeout(poll,restoring()?1000:running()?600:4000);}
 async function poll(){const was=restoring();try{const next=await request('status');absorb(next);if(was&&!next.session?.resetting&&!next.syncedAt)refresh();}catch{schedulePoll();}}
 async function refresh(){if(syncing||restoring())return;syncing=true;render();try{absorb(await request('workspace'));}catch{}syncing=false;render();}
 function header(){
  const account=data?.account||'';
  const items=confirmReset?`<p class="menu-note">Reopens every pull request, restores main and discards this session's trims, merges and messages.</p><button class="menu-item strong" role="menuitem" data-action="reset-now">Reset now</button><button class="menu-item" role="menuitem" data-action="reset-cancel">Cancel</button>`:`<p class="menu-note">Demo workspace${account?' · merging as @'+escape(account):''}</p><a class="menu-item" role="menuitem" href="https://github.com/${REPO}/pulls" target="_blank" rel="noopener">Open pull requests on GitHub ${external}</a><button class="menu-item" role="menuitem" data-action="reset-ask" ${restoring()?'disabled':''}>Reset workspace</button><button class="menu-item" role="menuitem" data-action="signout">Sign out</button>`;
  return `<header class="top-shell"><div class="top"><a class="brand" href="/">Tieto</a><a class="workspace-name" href="https://github.com/${REPO}" target="_blank" rel="noopener"><span class="repo-owner">13shreyansh/</span>tieto-nordbank-payments</a><div class="top-right"><form class="pr-form" id="pr-form"><input id="pr-link" type="url" inputmode="url" placeholder="Paste a GitHub PR link" aria-label="Paste a GitHub PR link" autocomplete="off" spellcheck="false" ${pending==='add'?'disabled':''}>${fieldError?`<span class="field-error" role="alert">${escape(fieldError)}</span>`:''}</form><span class="sync" aria-live="polite">${syncing?'Syncing with GitHub…':data?.syncedAt?'Synced '+clock(data.syncedAt):''}</span><div class="account-menu"><button class="plain account" id="account-button" data-action="menu" aria-haspopup="menu" aria-expanded="${menu}">${account?'@'+escape(account):'Account'}${chevron}</button>${menu?`<div class="menu" role="menu" aria-label="Account">${items}</div>`:''}</div></div></div></header>`;
 }
 const ghost=n=>Array.from({length:n},(_, i)=>`<div class="pr-row ghost" aria-hidden="true"><span class="ghost-line" style="width:${[62,74,58,69,80,55,66,72][i%8]}%"></span><span class="ghost-bar"></span><span></span><span class="ghost-line short"></span></div>`).join('');
 function waiting(){
  const s=data?.session,full=s?.resetKind==='full';
  const title=restoring()?'Restoring the workspace':'Opening the workspace';
  const sub=restoring()?(full?'Reopening every pull request and resetting main on GitHub. This takes about a minute.':'Clearing the last session\u2019s test runs and reading the pull requests again. A few seconds.'):'Reading the pull requests.';
  return `<main class="shell" aria-busy="true"><section class="summary"><div><h1 class="counter waiting-title">${title}</h1><p class="subline" role="status">${sub}</p></div></section><div class="keyline"><div class="keys"><span class="key"><i class="sample solid"></i>Needed: a test breaks without it</span><span class="key"><i class="sample hatch"></i>Unchecked: every test passes without it</span></div></div><section class="rows">${ghost(12)}</section></main>`;
 }
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
  return `<div class="pr-row ${visibleTotal&&(tail>430||tail===0)?'tail-full':''} ${current?'current':''} ${p.status==='running'?'trimming':''} ${p.status==='blocked'?'blocked':''}" data-id="${p.id}"><div class="row-head"><button class="row-title" data-action="open" data-id="${p.id}"><span class="title-text">${escape(p.title)}</span></button><span class="row-meta"><a class="pr-number" href="${escape(p.github)}" target="_blank" rel="noopener" title="Open on GitHub">${p.outside?escape(p.repo)+' ':''}#${p.number}</a><span class="meta-rest"> opened ${ago(p.createdAt)}${p.outside?'':' by '+escape(p.agent)+' · '+escape(p.branch)}</span></span></div><div class="track" role="button" tabindex="0" data-action="open" data-id="${p.id}" aria-label="Open ${escape(p.title)}">${bar(p)}${hint}</div><span class="row-count">${R.done(p)&&p.kind!=='junior'?format(p.kept)+' of ':''}${format(p.written)}</span><span class="row-state ${p.status==='blocked'?'blocked-label':''}">${state}</span></div>`;
 }
 function inbox(){
  if(!data||restoring())return waiting();
  const prs=R.remaining(data),allDone=R.complete(data),current=!running()?first():null,proven=prs.filter(R.proven).length,needs=prs.filter(p=>R.done(p)&&p.verdict!=='proven'&&p.status!=='blocked').length;
  const sub=running()?`Trimming ${Math.min(data.batch.completed+1,data.batch.total)} of ${data.batch.total} · ${format(data.batch.testsRun)} tests run`:allDone?`${proven} of ${prs.length} proven. ${needs} need you.`:hasResults()?`${prs.filter(R.done).length} of ${prs.length} trimmed.`:'None trimmed yet.';
  const own=prs.filter(p=>!p.outside),outside=prs.filter(p=>p.outside);
  return `<main class="shell"><section class="summary"><div><h1 class="counter"><span class="digits" aria-label="${R.count(data)}">${digits(R.count(data))}</span><span class="counter-words">${running()||hasResults()&&!allDone?'lines still to check.':allDone?'lines need you.':`lines written by agents in ${prs.length} open PRs.`}</span></h1><p class="subline">${sub}</p></div><div class="summary-action">${running()?'<button class="plain" data-action="stop">Stop</button>':allDone&&data?.trimmedAt?`<span>Trimmed ${clock(data.trimmedAt)} · <button class="plain" data-action="trim">Run again</button></span>`:`<button class="primary" data-action="trim" ${pending?'disabled':''}>Trim all</button><span class="key-hint">T</span>`}</div></section><div class="keyline"><div class="keys"><span class="key"><i class="sample solid"></i>Needed: a test breaks without it</span><span class="key"><i class="sample hatch"></i>Unchecked: every test passes without it</span></div><span class="scale">Full width is ${small()?'600':'1,200'} lines. Longer PRs wrap.<br>Under 12 lines is drawn at 6 px.</span></div>${offline?`<p class="inline-error" role="alert">Can't reach the test runner right now. This is the workspace as last saved; actions are paused. <button class="plain" data-action="retry-connection">Try again</button></p>`:''}${data.session?.resetError?`<p class="inline-error" role="alert">Couldn't restore the workspace. Choose Reset workspace in the account menu to try again.</p>`:''}${error?`<p class="inline-error" role="alert">${escape(error)}</p>`:''}<div class="repo-line"><span><a href="https://github.com/${REPO}" target="_blank" rel="noopener">${REPO}</a> · base <strong>main</strong> · ${own.length} open pull request${own.length===1?'':'s'}</span><a href="https://github.com/${REPO}/pulls" target="_blank" rel="noopener">View on GitHub ${external}</a></div><section class="rows" aria-label="Pull requests">${own.map(p=>row(p,p.id===current?.id)).join('')}${outside.length?`<div class="outside-rule">Outside this workspace</div>${outside.map(p=>row(p,false)).join('')}`:''}${!prs.length?'<p class="empty">Nothing to sign. New agent PRs appear here.</p>':''}</section><footer class="footline"><span>${data.merged.length?`${data.merged.length} merged into main · <button class="plain" data-action="revert">Revert last merge</button>`:'Nothing merged yet.'}</span><span>Line counts come from GitHub. Trim results come from test runs on this workspace.</span></footer></main>`;
 }
 const extra=p=>(p.blocks||[]).filter(b=>!b.needed);
 function namedBar(p){
  const blocks=p.blocks?p.blocks.filter(b=>b.needed||p.kind==='junior'||shown.has(b.id)||restored.has(b.id)):[{id:'unknown',name:'Not trimmed yet',lines:p.written,needed:false}];
  return `<div class="ledger-bar ${p.status==='blocked'?'blocked':''}">${blocks.map((b,i)=>`<span class="named-block ${lifting===b.id?'lifting':''}" style="width:${b.lines/p.written*100}%"><span class="segment ${b.needed?'solid':'hatch'}">${b.needed&&p.risk?.length&&Number.isFinite(p.riskPosition)?`<button class="notch" data-action="panel" aria-label="Read risky lines" style="left:clamp(0px,calc(${(p.riskPosition||0)*100}% - 3px),calc(100% - 6px))"></button>`:''}${p.kind==='junior'&&R.done(p)?'<i class="break" style="left:24%"></i><i class="break" style="left:49%"></i><i class="break" style="left:74%"></i>':''}${p.status==='blocked'?'<i class="barrier"></i>':''}</span><span class="block-label ${b.lines/p.written*960<60?'with-leader':''}">${escape(b.name)} · ${format(b.lines)}</span></span>`).join('')}</div><span class="ledger-scale">Full width is the ${format(p.written)} lines this PR wrote.</span>`;
 }
 function lamps(p){
  const grouped=p.tests>48,n=grouped?p.lampFiles:p.tests;
  return `<span class="lamps" aria-hidden="true">${Array.from({length:n||0},()=>`<i class="lamp ${['queued','running'].includes(p.status)?'running':p.kind==='junior'?'failed':''}"></i>`).join('')}</span><span class="proof-copy">${p.passed} of ${p.tests} ${p.kind==='junior'?'safety checks pass on this PR.':'tests pass on the trimmed PR.'}${grouped?' Lamps represent test files.':''}</span>`;
 }
 function proof(p){return `<div class="ledger-line proof"><dt>Proof</dt><dd>${p.tests===null?`<span>${p.status==='running'?'Trimming…':p.status==='queued'?'Queued':p.status==='unsupported'?'No test run for this repository.':'No test run yet.'}</span>`:lamps(p)}${p.executionProvider==='modal'?'<span class="caption">Tests run in Modal.</span>':''}<div class="proof-links">${p.tests!==null?`<a href="/api/proof?id=${encodeURIComponent(p.id)}" target="_blank" rel="noopener">Recorded commands & results</a>`:''}${p.codeContext?.available?`<a href="/api/context?id=${encodeURIComponent(p.id)}" target="_blank" rel="noopener">Code context</a>`:''}${p.executionProvider==='modal'?`<a href="/api/run-log?id=${encodeURIComponent(p.id)}" target="_blank" rel="noopener">Execution archive</a>`:''}${p.tests!==null?`<button class="plain" data-action="recheck" ${running()||pending?'disabled':''}>Re-run tests</button>`:''}</div></dd></div>`;}
 function riskPanel(p){
  const risk=p.risk[riskIndex]||p.risk[0];if(!risk)return '';
  return `<section class="risk-panel"><div class="risk-head"><span>${escape(risk.path)} · ${risk.start}–${risk.start+risk.lines.length-1}</span>${p.risk.length>1?'<button class="plain" data-action="next-risk">Next check</button>':'<button class="plain" data-action="panel">Close</button>'}</div><div class="code">${risk.lines.slice(0,8).map((line,i)=>`<span class="code-line ${i===risk.marked?'marked':''}"><span class="code-number">${risk.start+i}</span>${escape(line)}</span>`).join('')}</div><p class="risk-note">${escape(risk.note)}</p></section>`;
 }
 function ledger(){
  if(!data||restoring())return waiting();
  const p=find(selected);if(!p){selected=null;view='inbox';return inbox();}
  const junior=p.kind==='junior',isDone=R.done(p),outside=p.outside;
  let action='';
  if(p.status==='blocked')action=`<div class="sent-note">${escape(p.sentMessage)}<br><button class="plain" data-action="unblock">Undo block</button></div>`;
  else if(!isDone)action=`<span class="action-copy">${p.status==='unsupported'?"Can't run this repo's tests here":p.status==='running'?'Trimming…':p.status==='queued'?'Queued':'Nothing in this pull request has been checked yet.'}</span>${!running()&&p.status!=='unsupported'?'<button class="primary" data-action="recheck">Trim this PR</button>':''}`;
  else if(outside)action=`<span class="action-copy">${escape(p.note)}</span><a class="primary" href="/api/patch?id=${encodeURIComponent(p.id)}" download="trimmed.patch">Download trimmed patch</a>`;
  else if(junior)action=`<button class="primary" data-action="block" ${pending?'disabled':''}>${pending==='block'?'Blocking…':'Block and ask what they meant'}</button><span class="key-hint">B</span>`;
  else if(R.proven(p))action=`<span class="action-copy">Merges ${p.kept} of ${p.written} lines into main</span><button class="primary" data-action="finish" data-id="${p.id}" ${pending?'disabled':''}>${pending==='finish'?'Finishing…':'Finish'}</button><span class="key-hint">Enter</span>`;
  else action=`<div class="action-copy"><div contenteditable="true" role="textbox" aria-label="Note to the agent" class="editable" id="agent-note">${escape(notes.get(p.id)??p.note)}</div></div><button class="primary" data-action="return" ${pending?'disabled':''}>${pending==='return'?'Sending…':'Send back trimmed'}</button><span class="key-hint">S</span>`;
  return `<main class="ledger ${panel?'risk-open':''}"><nav class="ledger-nav"><button class="plain" data-action="inbox">${arrow} Inbox · ${data.prs.length} left</button></nav><h1>${escape(p.title)}</h1><div class="metadata"><a href="${escape(p.github)}" target="_blank" rel="noopener">${escape(p.repo)} #${p.number}</a><span>opened ${ago(p.createdAt)} by ${escape(p.agent)}</span>${p.branch?`<span>${escape(p.branch)}${p.outside?'':' into main'}</span>`:''}${p.headSha?`<span>head ${escape(p.headSha.slice(0,7))}</span>`:''}<a href="${escape(p.github)}/files" target="_blank" rel="noopener">Check on GitHub</a>${isDone?'<span>Measured</span>':''}</div>${namedBar(p)}${panel?'<button class="mobile-back" data-action="panel">Back to ledger</button>':''}<dl class="ledger-lines"><div class="ledger-line"><dt>Asked</dt><dd>"${escape(p.ask)}"${junior?` <span class="caption">This can't be checked. No test can tell when it's done.</span>`:''}</dd></div>${isDone?`<div class="ledger-line"><dt>Did</dt><dd>${junior?'Changes login, pricing and a database migration.':`Did it in <strong>${p.kept}</strong> lines. ${p.neededFailures} failing checks without them.`}</dd></div><div class="ledger-line"><dt>Extra</dt><dd>${junior?'Nothing is provably needed.':p.unchecked?`${format(p.unchecked)} lines nothing checks, extra or untested. All ${p.tests} tests pass without them.<br>${extra(p).map(b=>`<button class="extra-chip" data-action="restore" data-block="${escape(b.id)}">${escape(b.name)} · ${format(b.lines)}</button>`).join('')}`:'Nothing extra.'}</dd></div><div class="ledger-line"><dt>Read these</dt><dd>${junior?`<span class="check-summary">3 changes break production.</span><div class="junior-checks">${p.risk.map((r,i)=>`<button class="plain" data-action="risk" data-index="${i}">${escape(r.note)}</button>`).join('')}</div>`:p.risk.length?`<button class="read-link" data-action="panel">${p.readLines} lines to read.${p.kind==='cap'?' 1 looks wrong.':''}</button>`:'Nothing risky.'}</dd></div>`:''}${!panel?proof(p):''}</dl>${panel?riskPanel(p)+`<dl>${proof(p)}</dl>`:''}${error?`<p class="inline-error" role="alert">${escape(error)}</p>`:''}<div class="actions">${action}</div></main>`;
 }
 function render(){
  const focused=document.activeElement?.id;
  if(focused==='agent-note'&&!pending)return;
  const selection=document.getElementById('pr-link')?.value||'';
  const note=document.getElementById('agent-note')?.textContent;
  root.innerHTML=header()+(view==='ledger'?ledger():inbox());
  if(document.getElementById('pr-link'))document.getElementById('pr-link').value=selection;
  if(note&&focused==='agent-note'&&document.getElementById('agent-note'))document.getElementById('agent-note').textContent=note;
  if(focused&&document.getElementById(focused)){document.getElementById(focused).focus({preventScroll:true});}
  fresh.clear();
 }
 async function action(name,body={}){
  if(pending||restoring()||offline||!data)return;pending=name;error='';render();
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
  try{absorb(await request('add',{url}));view='inbox';selected=null;panel=false;history.pushState({},'','/workspace');document.getElementById('pr-link').value='';}
  catch(e){fieldError=e.message==='Not a public PR link.'?e.message:e.message;}
  pending=null;render();schedulePoll();
 }
 root.addEventListener('submit',e=>{if(e.target.id==='pr-form'){e.preventDefault();add(e.target);}});
 root.addEventListener('click',e=>{
  const el=e.target.closest('[data-action]');if(!el)return;const a=el.dataset.action,id=el.dataset.id;
  if(a!=='menu'&&!a.startsWith('reset-')&&menu){menu=false;confirmReset=false;}
  if(a==='menu'){menu=!menu;confirmReset=false;render();}
  else if(a==='reset-ask'){confirmReset=true;render();document.querySelector('[data-action="reset-now"]')?.focus();}
  else if(a==='reset-cancel'){confirmReset=false;menu=false;render();}
  else if(a==='reset-now')resetWorkspace();
  else if(a==='signout')signOut();
  else if(a==='retry-connection')connect();
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
 document.addEventListener('click',e=>{if(menu&&!e.target.closest('.account-menu')){menu=false;confirmReset=false;render();}});
 root.addEventListener('input',e=>{if(e.target.id==='agent-note')notes.set(selected,e.target.textContent);});
 document.addEventListener('keydown',e=>{
  if(e.target.closest?.('input,textarea,[contenteditable]'))return;
  if(e.key==='Escape'&&menu){menu=false;confirmReset=false;render();document.getElementById('account-button')?.focus();return;}
  if(e.key==='Enter'&&e.target.matches?.('[role="button"]')){e.preventDefault();e.target.click();return;}
  if(e.metaKey||e.ctrlKey||e.altKey||!data||restoring()||offline)return;
  if(e.key==='Enter'&&!e.target.closest?.('button,a')){const p=view==='ledger'?find(selected):first();if(p&&R.proven(p)&&!running()){e.preventDefault();action('finish',{id:p.id});}}
  if(e.key.toLowerCase()==='t'&&!running())action('measure');
  if(e.key.toLowerCase()==='o'){const p=data?.prs.find(p=>R.done(p)&&p.verdict==='needs-you'&&!p.outside);if(p)open(p.id);}
  if(e.key.toLowerCase()==='n'&&selected&&find(selected)?.risk?.length){panel=!panel;render();}
  if(e.key.toLowerCase()==='s'&&selected&&find(selected)?.kind==='cap'&&R.done(find(selected)))action('return',{id:selected,note:document.getElementById('agent-note')?.textContent||find(selected).note});
  if(e.key.toLowerCase()==='b'&&selected&&find(selected)?.kind==='junior'&&R.done(find(selected)))action('block',{id:selected});
 });
 addEventListener('resize',render);
 addEventListener('popstate',()=>{selected=null;panel=false;view='inbox';render();schedulePoll();});
 async function resetWorkspace(){
  menu=false;confirmReset=false;view='inbox';selected=null;panel=false;error='';history.replaceState({},'','/workspace');
  try{absorb(await request('reset',{}));}catch(e){error=e.message;render();}
 }
 function signOut(){
  left=true;clearTimeout(pollTimer);
  try{navigator.sendBeacon?.('/api/leave',new Blob([JSON.stringify({visitor})],{type:'application/json'}))||fetch('/api/leave',{method:'POST',keepalive:true,headers:{'Content-Type':'application/json'},body:JSON.stringify({visitor})});}catch{}
  try{store?.removeItem('tieto.visitor');store?.removeItem('tieto.snapshot');}catch{}
  location.assign('/');
 }
 // The first view never waits for GitHub: saved snapshot, then the worker's in-memory state, then a background sync.
 async function connect(){
  try{const next=await request('enter',{});absorb(next);if(!next.session?.resetting)refresh();}
  catch(e){
   if(!data){try{const saved=await fetch('/snapshot.json');if(saved.ok)data=await saved.json();}catch{}}
   offline=true;render();schedulePoll();
  }
 }
 function init(){
  try{const saved=JSON.parse(store?.getItem('tieto.snapshot')||'null');if(saved?.visitor===visitor&&saved.data?.prs){data=saved.data;if(data.batch)data.batch.running=false;delete data.session;collapsed=true;render();}}catch{}
  connect();
 }
 init();
})();
