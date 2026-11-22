/* Host-owned theme and language. Account rows are protected by existing RLS. */
(() => {
 'use strict';
 const key='aroham.preferences.v1';
 let current={theme:'light',language:'en'}, account=null, epoch=0, queued=Promise.resolve(),listener=()=>{},status='device';
 function validate(value,base=current){
   return {theme:['light','dark'].includes(value?.theme)?value.theme:base.theme,
     language:Object.hasOwn(MPI18n.languages,value?.language)?value.language:base.language};
 }
 function read(k){try{return JSON.parse(localStorage.getItem(k)||'null');}catch{return null;}}
 function write(k,v){try{localStorage.setItem(k,JSON.stringify(v));}catch{}}
 function record(dirty=status==='pending'||status==='error'){
   write(key,current);
   if(account)write(key+'.'+account.id,{...current,dirty});
 }
 function apply(){document.documentElement.dataset.theme=current.theme;MPI18n.set(current.language);listener({...current},status);}
 current=validate(read(key)||{theme:localStorage.getItem('mp.theme')==='dark'?'dark':'light',language:localStorage.getItem('mp_language')||'en'});
 function snapshot(){return {...current};}
 function save(){
   if(!account){status='device';record();apply();return Promise.resolve();}
   const at=epoch,id=account.id,value=snapshot();status='pending';record();apply();
   queued=queued.catch(()=>{}).then(async()=>{
     if(at!==epoch)return;
     try{
       await MPCloud.add('mp_profiles',{user_id:id,...value},true);
       if(at===epoch&&JSON.stringify(current)===JSON.stringify(value)){status='synced';record();apply();}
     }catch{if(at===epoch){status='error';record();apply();}}
   });return queued;
 }
 function change(update){
   const next=validate(update);
   if(JSON.stringify(next)===JSON.stringify(current)&&status!=='error')return queued;
   current=next;return save();
 }
 async function start(user,callback){
   epoch++;account=user;listener=callback||(()=>{});const at=epoch;
   if(!user){status='device';current=validate(read(key)||current);apply();return;}
   const cached=read(key+'.'+user.id);
   if(cached){current=validate(cached);apply();}
   status='pending';
   try{
     const rows=await MPCloud.get('mp_profiles','select=theme,language&user_id=eq.'+encodeURIComponent(user.id)+'&limit=1');
     if(at!==epoch)return;
     if(cached?.dirty||!rows?.length){if(cached?.dirty)current=validate(cached);await save();}
     else{current=validate(rows[0]);status='synced';record();apply();}
   }catch{if(at===epoch){status='error';record(cached?.dirty===true);apply();}}
 }
 function attach(callback){listener=callback||(()=>{});apply();}
 async function flush(){await queued.catch(()=>{});}
 function logout(){epoch++;account=null;status='device';apply();}
 window.MPPreferences=Object.freeze({snapshot,change,start,attach,flush,logout,status:()=>status});
})();
