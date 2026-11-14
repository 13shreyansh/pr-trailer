/* Shared, testable state transitions. Every action is confined to this local rehearsal. */
(function(root){
 const initial = () => ({trimmed:false,busy:false,error:'',opened:null,panel:false,riskIndex:0,finished:[],returned:[],blocked:[],history:[],beat:0,replayPhase:2,recheck:null});
 const remaining=(data,s)=>data.prs.filter(p=>!s.finished.includes(p.id)&&!s.returned.includes(p.id));
 const count=(data,s)=>s.trimmed?remaining(data,s).filter(p=>!s.blocked.includes(p.id)).reduce((n,p)=>n+(p.readLines||0),0):remaining(data,s).reduce((n,p)=>n+p.written,0);
 function apply(data,state,action){
  const s={...state,finished:[...state.finished],returned:[...state.returned],blocked:[...state.blocked],history:[...state.history]};
  const p=data.prs.find(p=>p.id===action.id);
  if(action.type==='trim')return {...s,trimmed:true,busy:false,error:''};
  if(action.type==='open'&&p)return {...s,opened:p.id,panel:false,riskIndex:0,replayPhase:0};
  if(action.type==='finish'&&p&&s.trimmed&&p.status==='proven'&&!s.finished.includes(p.id)){
   s.finished.push(p.id);s.history.push({type:'finish',id:p.id});s.opened=null;return s;
  }
  if(action.type==='return'&&p&&s.trimmed&&p.status==='needs-you'&&!s.returned.includes(p.id)){
   s.returned.push(p.id);s.history.push({type:'return',id:p.id});s.opened=null;return s;
  }
  if(action.type==='block'&&p&&p.status==='intern'&&!s.blocked.includes(p.id)){
   s.panel=false;s.blocked.push(p.id);s.history.push({type:'block',id:p.id});return s;
  }
  if(action.type==='undo'){
   const last=s.history.pop();if(!last)return s;
   const key={finish:'finished',return:'returned',block:'blocked'}[last.type];s[key]=s[key].filter(id=>id!==last.id);return s;
  }
  return s;
 }
 function verifyRun(p,r){
  if(!r||r.id!==p.id||r.measured!==true||r.written!==p.written||r.kept!==p.kept||r.tests!==p.tests||r.passed!==p.passed)return false;
  if(p.status==='intern')return r.checks?.length===3&&r.checks.every(c=>c.exitCode===1&&c.tests===1&&c.passed===0)&&r.final?.exitCode===1;
  if(r.patchSha256!==p.patchSha256||!r.controls?.length||!r.controls.every(c=>c.exitCode!==0))return false;
  const head=r.runs?.find(x=>x.label==='head'),final=r.runs?.find(x=>x.label==='trimmed');
  if(head?.exitCode!==0||final?.exitCode!==0||final?.tests!==p.tests||head?.tests!==p.tests)return false;
  if(p.heldOut&&!(r.heldOut?.exitCode===1&&r.heldOut.tests===p.heldOut.tests&&r.heldOut.passed===p.heldOut.passed))return false;
  return true;
 }
 const api={initial,remaining,count,apply,verifyRun};if(typeof module!=='undefined')module.exports=api;root.TietoReview=api;
})(globalThis);
