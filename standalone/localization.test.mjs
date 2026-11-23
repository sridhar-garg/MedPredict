import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
const window={};
runInNewContext(readFileSync(process.argv[2],'utf8'),{window});
runInNewContext(readFileSync(new URL('./web/hub.js',import.meta.url),'utf8'),{window});
const document={readyState:'loading',documentElement:{dataset:{}},body:null,addEventListener(){}};
runInNewContext(readFileSync(new URL('./web/i18n.js',import.meta.url),'utf8'),{window,document});
const catalogs=window.MPI18nCatalogs;
const baseline={records:[],launches:[],user:{name:'Synthetic'},cloudReady:true,loading:false,recordError:false,moduleStatus:{}};
const rendered=[
 window.MPHub.render(baseline),
 window.MPHub.render({...baseline,user:null}),
 window.MPHub.render({...baseline,user:null,cloudReady:false}),
 window.MPHub.render({...baseline,loading:true,moduleStatus:{loading:true}}),
 window.MPHub.render({...baseline,recordError:true,moduleStatus:{problem:true}}),
 window.MPHub.render({...baseline,launches:[{id:'healthara',date:'2026-11-22T12:00:00Z'}],moduleStatus:{activity:[{id:'namastey',date:'2026-11-22T12:00:00Z'}]}})
];
const values=rendered.flatMap(dashboard=>[...dashboard.matchAll(/>([^<>]+)</g)].map(m=>m[1].trim().replaceAll('&amp;','&')).filter(s=>/[A-Za-z]/.test(s)));
const exempt=new Set(['Synthetic.','there.','MedPredict','Healthara','Namastey AI','Kaamigo']);
const expected=new Set(Object.entries(catalogs).filter(([l])=>l!=='en').flatMap(([,dict])=>Object.keys(dict).map(k=>k.trim().toLowerCase())));
const required=['Return to sign in','Session history','Session progress','Water glasses','Journal entries','Real data only','What you’ve been working on','Account and data connections','Assessment watch','Compare individual models','Run model estimate','Mood Journal','Water Tracker','7-Day Diet Planner','Your Cultural Matches!','Generate Scenario','Play Mantra','Create a Skill Exchange','Post a work trial','Save personal review'];
for(const [language,dict] of Object.entries(window.MPI18nCatalogs)){
 if(language==='en')continue;
 const keys=new Set(Object.keys(dict).map(k=>k.toLowerCase()));
 for(const value of values)assert.ok(exempt.has(value)||/\d{1,2}\s+Nov|Nov\s+\d{1,2}/.test(value)||keys.has(value.toLowerCase()),language+': missing '+value);
 for(const key of expected)assert.ok(keys.has(key), language+': catalog parity missing '+key);
 window.MPI18n.set(language);
 for(const value of required)assert.ok(keys.has(value.toLowerCase()),language+': missing app control '+value);
 assert.notEqual(window.MPI18n.translate('What you’ve been working on'),'What you’ve been working on',language);
 assert.equal(window.MPI18n.translate('6/8 glasses'),'6/8 '+window.MPI18n.translate('glasses'));
 assert.equal(window.MPI18n.translate('  Water\n  Tracker  '),'  '+window.MPI18n.translate('Water Tracker')+'  ');
 assert.equal(window.MPI18n.translate('a private personal note'),'a private personal note');
 assert.equal(window.MPI18n.translate('★★★★☆ — Very good'),'★★★★☆ — '+window.MPI18n.translate('Very good'));
 window.MPI18n.set('en');assert.equal(window.MPI18n.translate('Water Tracker'),'Water Tracker');
}
assert.equal(Object.keys(window.MPI18nCatalogs).length,15);
console.log('PASS: '+expected.size+' shared UI strings in every locale, all dashboard states, selected controls across all four apps, language switching, numeric values and multiline labels.');
