// Injected into the isolated integrated copies. Only the host owns authentication.
(() => {
 'use strict';
 const allowedParents=new Set(['http://127.0.0.1:8766','https://appassets.androidplatform.net']);
 let values=Object.create(null), connected=false, hostOrigin=null, token=null, counter=0, account=null;
 const pending=new Map();
 let readyResolve;
 const ready=new Promise(resolve=>{readyResolve=resolve;});
 const send=(type,extra={})=>{
   if(connected)parent.postMessage({channel:'workspace-v1',token,type,...extra},hostOrigin);
 };
 const snapshot=()=>{send('state',{storage:{...values}});};
 const storage={
   getItem:k=>Object.hasOwn(values,String(k))?values[String(k)]:null,
   setItem:(k,v)=>{k=String(k);v=String(v);if(k.length>160||v.length>180000)return;values[k]=v;snapshot();},
   removeItem:k=>{delete values[String(k)];snapshot();},
   clear:()=>{values=Object.create(null);snapshot();}
 };
 function rpc(method,data={}){
   return new Promise((resolve,reject)=>{
     const id=++counter;pending.set(id,{resolve,reject});
     send('request',{id,method,data});
     setTimeout(()=>{if(pending.delete(id))reject(Error('Workspace connection timed out.'));},20000);
   });
 }
 function metric(key,value,increment=false){
   let m={};try{m=JSON.parse(storage.getItem('workspace_metrics')||'{}');}catch{}
   m[key]=increment?(Number(m[key])||0)+value:value;
   storage.setItem('workspace_metrics',JSON.stringify(m));
 }
 window.addEventListener('message',event=>{
   if(event.source!==parent||!allowedParents.has(event.origin)||event.data?.channel!=='workspace-v1')return;
   const d=event.data;
   if(d.type==='init'&&!connected&&typeof d.token==='string'){
     hostOrigin=event.origin;token=d.token;connected=true;account=d.account;
     for(const [k,v] of Object.entries(d.storage||{}))if(typeof v==='string')values[k]=v;
     readyResolve({account,storage,listingRows:d.listings||[],synced:d.synced===true});
   }else if(connected&&event.origin===hostOrigin&&d.token===token){
     if(d.type==='result'){
       const p=pending.get(d.id);if(!p)return;pending.delete(d.id);d.ok?p.resolve(d.data):p.reject(Error(d.message||'Request failed.'));
     }else if(d.type==='flush'){snapshot();send('flushed');}
   }
 });
 window.Workspace={ready,storage,metric,rpc,leave:()=>{snapshot();send('leave');},snapshot};
 window.addEventListener('DOMContentLoaded',()=>parent.postMessage({channel:'workspace-v1',type:'ready'},'*'));
})();
const workspaceStorage=window.Workspace.storage;
// Minimal local canvas renderer for Healthara's user-entered doughnut data.
// The original illustrative dashboard graphs are disabled in this edition.
class Chart {
 constructor(canvas,config){this.canvas=canvas;this.data=config.data;this.update();}
 update(){const c=this.canvas.getContext('2d');if(!c)return;const w=this.canvas.width||300,h=this.canvas.height||150;const data=this.data.datasets[0].data;const total=data.reduce((a,b)=>a+Math.max(0,Number(b)||0),0)||1;let angle=-Math.PI/2;c.clearRect(0,0,w,h);data.forEach((n,i)=>{const end=angle+Math.max(0,Number(n)||0)/total*Math.PI*2;c.beginPath();c.lineWidth=Math.max(12,Math.min(w,h)*.16);c.strokeStyle=this.data.datasets[0].backgroundColor[i]||'#bd7aca';c.arc(w/2,h/2,Math.min(w,h)*.32,angle,end);c.stroke();angle=end;});}
}
