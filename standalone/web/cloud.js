/* The standalone client uses only the project's publishable API key.
   OAuth is Google-only, via Supabase's supported PKCE provider flow. */
(function(root){
 'use strict';
 const cfg=root.MP_CONFIG||{};
 const base=(cfg.url||'').replace(/\/$/,'');
 const key=cfg.key||'';
 const enabled=/^https:\/\/[a-z0-9]+\.supabase\.co$/.test(base)&&(/^sb_publishable_/.test(key)||key.startsWith('eyJ'));
 let session=null, user=null, refreshJob=null;
 const storage=window.sessionStorage;
 const sessionKey='mp.session.v1';
 const verifierKey='mp.pkce.v1';
 const redirect=()=>root.MedPredictNative?'app.medpredict.mobile://auth-callback':'http://127.0.0.1:8765/auth/callback';
 function errorMessage(status){return status===401?'Your Google sign-in has expired. Please sign in again.':status===403?'You do not have permission to access that record.':status===429?'Usage limit reached. Try again later.':'Cloud service is temporarily unavailable.';}
 async function request(path,opts={},token){
   if(!enabled)throw Error('Cloud synchronization has not been configured.');
   const response=await fetch(base+path,{...opts,headers:{apikey:key,'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{}),...(opts.headers||{})},signal:AbortSignal.timeout(30000)});
   if(!response.ok)throw Error(errorMessage(response.status));
   const raw=await response.text();return raw?JSON.parse(raw):null;
 }
 function b64url(bytes){return btoa(String.fromCharCode(...bytes)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');}
 function persist(s){session={access_token:s.access_token,refresh_token:s.refresh_token,expires_at:s.expires_at||Math.floor(Date.now()/1000)+(s.expires_in||3600)};storage.setItem(sessionKey,JSON.stringify(session));}
 function clear(){session=null;user=null;storage.removeItem(sessionKey);storage.removeItem(verifierKey);}
 async function access(){
   if(!session)throw Error('Continue with Google to synchronize.');
   if(Date.now()/1000+60>=session.expires_at){
      if(!refreshJob)refreshJob=request('/auth/v1/token?grant_type=refresh_token',{method:'POST',body:JSON.stringify({refresh_token:session.refresh_token})}).then(s=>{persist(s);return session.access_token;}).catch(e=>{clear();throw e;}).finally(()=>{refreshJob=null;});
      return refreshJob;
   }return session.access_token;
 }
 async function verify(){const u=await request('/auth/v1/user',{},await access());if(u.app_metadata?.provider!=='google'||!u.email_confirmed_at){clear();throw Error('A verified Google account is required.');}user={id:u.id,name:u.user_metadata?.full_name||u.email||'Google user',email:u.email||''};return user;}
 async function begin(){
   if(!enabled)throw Error('Google sign-in is waiting for the Supabase project settings.');
   const verifier=b64url(crypto.getRandomValues(new Uint8Array(48)));
   const challenge=b64url(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(verifier))));
   storage.setItem(verifierKey,JSON.stringify({verifier,created:Date.now()}));
   const authURL=new URL(base+'/auth/v1/authorize');
   authURL.searchParams.set('provider','google');authURL.searchParams.set('redirect_to',redirect());authURL.searchParams.set('code_challenge',challenge);authURL.searchParams.set('code_challenge_method','s256');
   if(root.MedPredictNative)root.MedPredictNative.openAuth(authURL.href);else location.assign(authURL.href);
 }
 async function finish(callback){
   const u=new URL(callback), expected=new URL(redirect());
   if(u.protocol!==expected.protocol||u.host!==expected.host||u.pathname!==expected.pathname)throw Error('Invalid sign-in return address.');
   const code=u.searchParams.get('code');if(!code)throw Error('Google sign-in was cancelled or failed.');
   const flow=JSON.parse(storage.getItem(verifierKey)||'null');storage.removeItem(verifierKey);
   if(!flow||Date.now()-flow.created>600000)throw Error('This sign-in request expired. Try again.');
   const s=await request('/auth/v1/token?grant_type=pkce',{method:'POST',body:JSON.stringify({auth_code:code,code_verifier:flow.verifier})});
   persist(s);try{return await verify();}catch(e){clear();throw e;}
 }
 async function init(){
   if(!enabled)return null;
   if(location.pathname==='/auth/callback'){
     const original=location.href;history.replaceState(null,'','/');return finish(original);
   }
   try{session=JSON.parse(storage.getItem(sessionKey)||'null');if(session)return await verify();}catch{clear();}return null;
 }
 async function signOut(){try{if(session)await request('/auth/v1/logout',{method:'POST'},await access());}catch{}clear();}
 async function get(table,query=''){return request('/rest/v1/'+table+'?'+query,{},await access());}
 async function add(table,row,upsert=false){return request('/rest/v1/'+table,{method:'POST',headers:{Prefer:upsert?'resolution=merge-duplicates,return=representation':'return=representation'},body:JSON.stringify(row)},await access());}
 async function patch(table,query,row){return request('/rest/v1/'+table+'?'+query,{method:'PATCH',headers:{Prefer:'return=representation'},body:JSON.stringify(row)},await access());}
 async function remove(table,query){return request('/rest/v1/'+table+'?'+query,{method:'DELETE'},await access());}
 async function assistant(question){return request('/functions/v1/medpredict-assistant',{method:'POST',body:JSON.stringify({question,consent:true})},await access());}
 root.MPCloud={enabled,begin,finish,init,signOut,get,add,patch,remove,assistant,currentUser:()=>user};
})(window);
