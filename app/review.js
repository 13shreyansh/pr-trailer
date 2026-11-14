(function(root){
 const active=p=>!['merged','returned','closed'].includes(p.status);
 const done=p=>['done','blocked'].includes(p.status);
 const proven=p=>done(p)&&p.verdict==='proven'&&!p.outside;
 const remaining=data=>data?.prs.filter(active)||[];
 const count=data=>remaining(data).reduce((n,p)=>n+(done(p)?p.status==='blocked'?0:p.readLines||0:p.written||0),0);
 const complete=data=>remaining(data).length>0&&remaining(data).every(p=>done(p)||p.status==='unsupported');
 const first=data=>complete(data)?remaining(data).find(proven):undefined;
 function canWrite(p){return !!p&&!p.outside&&p.repo==='13shreyansh/tieto-nordbank-payments';}
 function segments(p,full,collapsed){
  const measured=done(p),solid=measured?p.kept||0:0,unchecked=measured&&p.verdict==='proven'&&collapsed?0:(p.written||0)-solid;
  let offset=0;const lines=[];
  while(offset<solid+unchecked){const size=Math.min(full,solid+unchecked-offset),a=Math.max(0,Math.min(solid-offset,size));lines.push({solid:a,unchecked:size-a,offset});offset+=size;}
  return lines;
 }
 const api={active,done,proven,remaining,count,first,canWrite,segments,complete};root.TietoReview=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
