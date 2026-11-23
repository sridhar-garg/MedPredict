import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext,Script} from 'node:vm';
const read=file=>readFileSync(new URL(file,import.meta.url),'utf8');
const window={},handlers={};window.addEventListener=(type,fn)=>{handlers[type]=fn;};
class FakeFrame {
 constructor(){this.messages=[];this.contentWindow={postMessage:(value)=>this.messages.push(value)};}
 setAttribute(k,v){this[k]=v;}
 append(...elements){this.children=(this.children||[]).concat(elements);}
 replaceChildren(...elements){this.children=elements;}
 remove(){this.removed=true;}
}
let frame;
const document={createElement:()=>new FakeFrame()};
const children={replaceChildren:f=>{frame=f}};
const account={id:'00000000-0000-4000-8000-000000000001',name:'Synthetic user'};
const database={state:[],listings:[]};
const MPCloud={
 get:async table=>JSON.parse(JSON.stringify(table==='workspace_module_state'?database.state:database.listings)),
 add:async (table,row)=>{if(table==='workspace_module_state'){database.state=database.state.filter(r=>r.app_id!==row.app_id);database.state.push(row);return [row];}
   const r={...row,id:'00000000-0000-4000-8000-000000000003',creator_uid:account.id,status:'active',created_at:new Date().toISOString()};database.listings.push(r);return [r];},
 patch:async()=>[]
};
const context={window,document,MPCloud,crypto:globalThis.crypto,TextEncoder,setTimeout,clearTimeout,confirm:()=>true};
runInNewContext(read('./web/hub.js'),context);
runInNewContext(read('./web/modules-controller.js'),context);
const hub=window.MPHub,modules=window.MPModules;
assert.deepEqual(Array.from(hub.apps,a=>a.name),['MedPredict','Healthara','Namastey AI','Kaamigo']);
const render=(records=[],moduleStatus=modules.status())=>hub.render({records,launches:[],user:account,cloudReady:true,loading:false,recordError:false,moduleStatus});
await modules.start(account,()=>{});
const home=render();
assert.match(home,/Welcome,.*Synthetic\./);
for(const app of hub.apps)assert.ok(home.includes('data-route="'+app.route+'" data-app-launch="'+app.id+'"'));
const msg=async (data,from=frame.contentWindow,origin='null')=>handlers.message({source:from,origin,data:{channel:'workspace-v1',...data}});
modules.open('healthara',children,()=>{});
window.MPI18n={languages:{en:'English',hi:'Hindi',fr:'French'},language:()=>'en'};
window.MPI18nCatalogs={hi:{Dashboard:'डैशबोर्ड'},fr:{Dashboard:'Tableau de bord'}};
let requested;
modules.setPreferences({theme:'dark',language:'hi'},p=>{requested=p;});
assert.equal(frame.sandbox,'allow-scripts allow-forms allow-downloads allow-modals');
await msg({type:'ready'});
const hello=frame.messages.at(-1);
assert.equal(hello.account.name,account.name);
assert.deepEqual(Object.keys(hello.account).sort(),['id','name']);
assert.ok(!JSON.stringify(hello).includes('access_token'));
assert.equal(hello.preferences.theme,'dark');
assert.equal(hello.preferences.language,'hi');
assert.equal(hello.catalog.Dashboard,'डैशबोर्ड');
await msg({type:'preferences',token:hello.token,preferences:{theme:'light',language:'fr'}},{});
assert.equal(requested,undefined);
await msg({type:'preferences',token:hello.token,preferences:{theme:'light',language:'fr'}});
assert.equal(requested.language,'fr');assert.equal(requested.theme,'light');
modules.setPreferences({theme:'light',language:'fr'});
assert.equal(frame.messages.at(-1).preferences.language,'fr');
const token=hello.token,stored={healthara_workspace_dummy:'bad','healthara_workspace-user':JSON.stringify({journalEntries:[{text:'synthetic'}],waterIntake:6,sleepHours:7.5,stepCount:7200,user:{password:'not retained'}})};
await msg({type:'state',token,storage:stored},{});assert.equal(modules.status().summaries.healthara.journal,0);
await msg({type:'state',token,storage:stored});assert.equal(modules.status().summaries.healthara.journal,1);
assert.equal(modules.status().summaries.healthara.water,6);
assert.equal(modules.status().summaries.healthara.sleep,7.5);
assert.equal(modules.status().summaries.healthara.steps,7200);
await modules.flush();assert.equal(database.state.length,1);
assert.ok(!JSON.stringify(database.state).includes('not retained'));
modules.open('namastey',children,()=>{});
await msg({type:'ready'});const n=frame.messages.at(-1);
assert.equal(n.preferences.language,'fr');assert.equal(n.preferences.theme,'light');
assert.deepEqual(Object.keys(n.storage),[]);
await msg({type:'state',token:n.token,storage:{workspace_metrics:JSON.stringify({matches:2,stories:1})}});
await modules.flush();assert.equal(modules.status().summaries.namastey.matches,2);
modules.open('kaamigo',children,()=>{});await msg({type:'ready'});const k=frame.messages.at(-1);
assert.equal(k.preferences.language,'fr');assert.equal(k.preferences.theme,'light');
await msg({type:'request',token:k.token,id:1,method:'publish',data:{type:'skill',offer:'Synthetic poster design',need:'Practice presentation',rate:''}});
assert.equal(modules.status().summaries.kaamigo.exchanges,1);
const html=render([{title:'<img onerror="bad">',created_at:new Date().toISOString(),kind:'assessment'}]);
assert.ok(html.includes('&lt;img onerror=&quot;bad&quot;&gt;'));assert.ok(!html.includes('<img onerror'));
assert.ok(html.includes('Journal entries</dt><dd>1</dd>'));
assert.ok(html.includes('Water glasses</dt><dd>6</dd>'));
assert.ok(html.includes('Sleep (hours)</dt><dd>7.5</dd>'));
assert.ok(html.includes('Steps today</dt><dd>7200</dd>'));
assert.ok(html.includes('Culture matches</dt><dd>2</dd>'));
assert.ok(html.includes('Active skill exchanges</dt><dd>1</dd>'));
for(const app of ['healthara','namastey','kaamigo']){
 const source=read('./web/modules/'+app+'/index.html');
 assert.ok(!/<script\b[^>]*src\s*=/i.test(source),app+' external script removed');
 assert.ok(!/<input[^>]+type="password"/i.test(source),app+' old credential input removed');
 assert.ok(!/firebaseConfig|emailjs\.send/.test(source));
 assert.ok(!source.includes('<div id="workspaceNotice">'));
 const menuClass=app==='kaamigo'?'nav':'nav-tab';
 const homeButton=source.match(/<button\b[^>]*data-workspace-home[^>]*>[\s\S]*?<\/button>/);
 assert.ok(homeButton,app+' has an in-menu combined dashboard button');
 assert.ok(homeButton[0].includes('class="'+menuClass+'"'),app+' uses its native menu style');
 assert.ok(homeButton[0].includes('Combined dashboard'));
 assert.ok(!/\bdata-(tab|p)=/.test(homeButton[0]),app+' home does not activate an internal tab');
 assert.ok(source.includes('data-workspace-preference="language"'));
 for(const m of source.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi))new Script(m[1]);
}
assert.ok(!read('./web/app.js').includes('workspace-module-header'),'embedded apps have no duplicate outer header');
assert.ok(read('./web/app.js').includes('src="/aroham-welcome.webp"'),'welcome card uses the local illustration');
const welcomeImage=readFileSync(new URL('./web/aroham-welcome.webp',import.meta.url));
assert.equal(welcomeImage.subarray(8,12).toString(),'WEBP','welcome image is bundled as a real WebP asset');
await modules.flush();modules.reset();assert.equal(modules.status().summaries.healthara.journal,0);
// Re-enter every module repeatedly with both modes and languages.
await modules.start(account,()=>{});
for(let pass=0;pass<4;pass++){
 modules.setPreferences({theme:pass%2?'dark':'light',language:pass%2?'hi':'fr'});
 for(const id of ['healthara','namastey','kaamigo']){
  let returned=0;
  modules.open(id,children,()=>{returned++;modules.stop();});const launched=frame;
  await msg({type:'ready'});const init=frame.messages.at(-1);
  assert.equal(init.preferences.language,pass%2?'hi':'fr');
  await msg({type:'leave',token:init.token});
  assert.equal(returned,1,id+' returns to hub');
  assert.equal(launched.removed,true);
  assert.equal(modules.status().synced,true,'returning keeps signed-in session');
  assert.equal(modules.status().summaries.healthara.water,6,'returning preserves module progress');
 }
}
modules.reset();
console.log('PASS: 4 in-app routes, shared identity without tokens, isolated child state, synthetic save interface, marketplace, aggregate counts, removed old logins and parsed all module scripts');
