(() => {
 'use strict';
 const moduleIds=new Set(['healthara','namastey','kaamigo']);
 const allowedKeys={
   healthara:new Set(['healthara_workspace-user','healtharaReviews']),
   namastey:new Set(['workspace_metrics','namastey-ai-reviews']),
   kaamigo:new Set(['KaamigoQuiz','KaamigoReview'])
 };
 let user=null, states={}, privateListings=[], synced=false, loading=false, problem=false, frame=null, active=null, epoch=0, onUpdate=()=>{}, onLeave=()=>{};
 let preferences={theme:'light',language:'en'}, onPreferences=()=>{};
 function preferencePacket(){return {preferences:{...preferences},catalog:window.MPI18nCatalogs?.[preferences.language]||{}};}
 function setPreferences(p,callback){
   preferences={...p};if(callback)onPreferences=callback;
   if(frame&&active?.initialized)frame.contentWindow.postMessage({channel:'workspace-v1',token:active.token,type:'preferences',...preferencePacket()},'*');
 }
 const timers=new Map(), writes=new Map();
 const read=(s,key)=>{try{return JSON.parse(s?.[key]||'null');}catch{return null;}};
 const num=n=>Number.isFinite(Number(n))?Math.max(0,Math.min(100000,Math.floor(Number(n)))):0;
 const len=x=>Array.isArray(x)?x.length:0;
 function summarize(id,storage){
   if(id==='healthara'){const s=read(storage,'healthara_workspace-user')||{};return {journal:len(s.journalEntries),meals:len(s.dailyMeals),water:num(s.waterIntake),reports:len(s.savedReports),habits:len(s.gardenFlowers),sleep:Number.isFinite(s.sleepHours)&&s.sleepHours>=0&&s.sleepHours<=24?s.sleepHours:null,steps:Number.isInteger(s.stepCount)&&s.stepCount>=0?num(s.stepCount):null};}
   if(id==='namastey'){const m=read(storage,'workspace_metrics')||{};return {matches:num(m.matches),stories:num(m.stories),mantras:num(m.mantras),monuments:num(m.monuments)};}
   return {exchanges:privateListings.filter(x=>x.type==='skill'&&x.status==='active').length,jobs:privateListings.filter(x=>x.type==='job'&&x.status==='active').length,spaces:privateListings.filter(x=>x.type==='space'&&x.status==='active').length,preferences:len(read(storage,'KaamigoQuiz'))};
 }
 function clean(id,storage){
   const safe={};
   if(!storage||typeof storage!=='object'||Array.isArray(storage))return safe;
   for(const [k,v] of Object.entries(storage)){
     if(!allowedKeys[id].has(k)||typeof v!=='string'||v.length>180000)continue;
     try{const data=JSON.parse(v);if(k==='healthara_workspace-user'&&data&&typeof data==='object'){delete data.password;delete data.user;safe[k]=JSON.stringify(data);}else safe[k]=v;}catch{}
   }
   if(new TextEncoder().encode(JSON.stringify(safe)).length>240000)throw Error('Your saved workspace data is too large. Remove some old entries.');
   return safe;
 }
 function status(){return {summaries:Object.fromEntries([...moduleIds].map(id=>[id,summarize(id,states[id]?.storage||{})])),activity:Object.entries(states).filter(([,s])=>s.updated_at).map(([id,s])=>({id,date:s.updated_at})),loading,problem,synced};}
 function publishUpdate(){onUpdate(status());}
 function stop(){if(frame){frame.remove();frame=null;}active=null;}
 function reset(){epoch++;stop();for(const t of timers.values())clearTimeout(t);timers.clear();writes.clear();states={};privateListings=[];user=null;synced=false;loading=false;problem=false;}
 async function start(account,update){
   reset();user=account;onUpdate=update||(()=>{});synced=!!account;const at=epoch;
   if(!account){publishUpdate();return;}
   loading=true;publishUpdate();
   try{
     const [saved,own]=await Promise.all([MPCloud.get('workspace_module_state','select=app_id,state,summary,updated_at'),MPCloud.get('workspace_kaamigo_listings','select=id,type,status,offer,need,rate,creator_uid,created_at&creator_uid=eq.'+encodeURIComponent(account.id)+'&limit=500')]);
     if(at!==epoch)return;
     for(const r of saved||[])if(moduleIds.has(r.app_id))states[r.app_id]={storage:clean(r.app_id,r.state),updated_at:r.updated_at};
     privateListings=own||[];
   }catch{if(at===epoch)problem=true;}finally{if(at===epoch){loading=false;publishUpdate();}}
 }
 function persist(id){
   if(!user||!synced)return;
   clearTimeout(timers.get(id));
   const at=epoch,accountId=user.id;
   timers.set(id,setTimeout(()=>{
     timers.delete(id);if(at!==epoch)return;
     const before=writes.get(id)||Promise.resolve();
     const next=before.catch(()=>{}).then(async()=>{
       if(at!==epoch||!states[id])return;
       const r=states[id];await MPCloud.add('workspace_module_state',{user_id:accountId,app_id:id,state:r.storage,summary:summarize(id,r.storage),updated_at:r.updated_at},true);if(at===epoch){problem=false;publishUpdate();}
     }).catch(()=>{if(at===epoch){problem=true;publishUpdate();}});
     writes.set(id,next);
   },250));
 }
 function updateState(id,storage){const safe=clean(id,storage);if(JSON.stringify(safe)===JSON.stringify(states[id]?.storage||{}))return;states[id]={storage:safe,updated_at:new Date().toISOString()};persist(id);publishUpdate();}
 async function allListings(){
   if(!user)return privateListings;
   const result=await MPCloud.get('workspace_kaamigo_listings','select=id,type,offer,need,rate,status,creator_uid,created_at&status=eq.active&order=created_at.desc&limit=500');
   return result||[];
 }
 const convert=r=>({...r,creatorUid:r.creator_uid,createdAt:r.created_at});
 async function request(method,data){
   if(method==='listings')return (await allListings()).map(convert);
   if(method==='publish'){
     const type=data?.type,offer=String(data?.offer||'').trim(),need=String(data?.need||'').trim(),rate=String(data?.rate||'').trim();
     if(!['skill','job','space'].includes(type)||!offer||offer.length>200||need.length>1000||rate.length>40)throw Error('Please check your post details.');
     if(!confirm(user?'Publish this listing to signed-in members of the new Kaamigo workspace? Do not include personal contact or private information.':'Save this listing to your offline demonstration only?'))throw Error('Posting cancelled.');
     const p={type,offer,need,rate};
     if(user){const result=await MPCloud.add('workspace_kaamigo_listings',p);privateListings.unshift(result[0]);}
     else privateListings.unshift({...p,id:crypto.randomUUID(),creator_uid:'demo',status:'active',created_at:new Date().toISOString()});
     publishUpdate();return true;
   }
   if(method==='withdraw'){
     const id=String(data?.id||'');if(!/^[0-9a-f-]{36}$/.test(id))throw Error('Invalid listing.');
     const r=privateListings.find(x=>x.id===id);if(!r)throw Error('Only your own listings can be withdrawn.');
     if(user)await MPCloud.patch('workspace_kaamigo_listings','id=eq.'+encodeURIComponent(id),{status:'withdrawn'});
     r.status='withdrawn';publishUpdate();return true;
   }
   throw Error('Unsupported operation.');
 }
 window.addEventListener('message',async e=>{
   if(!frame||!active||e.source!==frame.contentWindow||e.origin!=='null'||e.data?.channel!=='workspace-v1')return;
   const d=e.data,a=active;
   const send=(type,extra={})=>{if(active===a&&frame)frame.contentWindow.postMessage({channel:'workspace-v1',token:a.token,type,...extra},'*');};
   if(d.type==='ready'&&!a.initialized){
     a.initialized=true;
     let listings=[];
     if(a.id==='kaamigo'){try{listings=(await allListings()).map(convert);}catch{problem=true;publishUpdate();}}
     send('init',{account:{id:user?.id||'demo',name:String(user?.name||'Demo user').slice(0,100)},storage:states[a.id]?.storage||{},listings,synced:!!user,...preferencePacket()});return;
   }
   if(d.token!==a.token||!a.initialized)return;
   if(d.type==='state'){try{updateState(a.id,d.storage);}catch{problem=true;publishUpdate();}}
   else if(d.type==='leave'){onLeave();}
   else if(d.type==='preferences'){const p={};if(['light','dark'].includes(d.preferences?.theme))p.theme=d.preferences.theme;if(Object.hasOwn(window.MPI18n?.languages||{},d.preferences?.language))p.language=d.preferences.language;if(Object.keys(p).length)onPreferences(p);}
   else if(d.type==='request'&&a.id==='kaamigo'&&Number.isInteger(d.id)){
     try{const data=await request(d.method,d.data);send('result',{id:d.id,ok:true,data});}catch(err){send('result',{id:d.id,ok:false,message:err.message||'Unable to complete the request.'});}
   }
 });
 function open(id,container,leave){
   if(!moduleIds.has(id))return;stop();onLeave=leave;
   active={id,token:crypto.randomUUID(),initialized:false};
   frame=document.createElement('iframe');frame.title=id+' integrated workspace';frame.setAttribute('sandbox','allow-scripts allow-forms allow-downloads allow-modals');frame.referrerPolicy='no-referrer';frame.className='workspace-frame';frame.src='/modules/'+id+'/index.html';
   container.replaceChildren(frame);
 }
 // Flush queued writes before the central session is signed out.
 async function flush(){
   for(const [id,t] of timers){clearTimeout(t);timers.delete(id);if(user&&states[id]){const r=states[id];try{await MPCloud.add('workspace_module_state',{user_id:user.id,app_id:id,state:r.storage,summary:summarize(id,r.storage),updated_at:r.updated_at},true);}catch{problem=true;}}}
   await Promise.allSettled(writes.values());
 }
 window.MPModules=Object.freeze({start,stop,open,status,reset,flush,setPreferences});
})();
