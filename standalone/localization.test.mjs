import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
const window={};
runInNewContext(readFileSync(process.argv[2],'utf8'),{window});
runInNewContext(readFileSync(new URL('./web/hub.js',import.meta.url),'utf8'),{window});
const dashboard=window.MPHub.render({records:[],launches:[],user:{name:'Synthetic'},cloudReady:true,loading:false,recordError:false,moduleStatus:{}});
const values=[...dashboard.matchAll(/>([^<>]+)</g)].map(m=>m[1].trim().replaceAll('&amp;','&')).filter(s=>/[A-Za-z]/.test(s));
const exempt=new Set(['Welcome,','Synthetic.','MedPredict','Healthara','Namastey AI','Kaamigo']);
for(const [language,dict] of Object.entries(window.MPI18nCatalogs)){
 if(language==='en')continue;
 const keys=new Set(Object.keys(dict).map(k=>k.toLowerCase()));
 for(const value of values)assert.ok(exempt.has(value)||keys.has(value.toLowerCase()),language+': missing '+value);
}
assert.equal(Object.keys(window.MPI18nCatalogs).length,15);
console.log('PASS: every main dashboard label, description, card and personal summary has catalog coverage in all 15 languages.');
