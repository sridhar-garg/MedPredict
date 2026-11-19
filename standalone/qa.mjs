// Local UI smoke test. Uses only synthetic inputs and an empty cloud config.
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
const require=createRequire(import.meta.url);
const moduleRoot=process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES;
const {chromium}=require(path.join(moduleRoot,'playwright'));
const MPModels=require('./web/predict.js');
const assetDir=process.argv[2], fixtures=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
let maximum=0;
for(const [d,x] of Object.entries(fixtures)){
  const spec=JSON.parse(fs.readFileSync(path.join(assetDir,d+'.json'),'utf8'));
  for(let i=0;i<x.rows.length;i++){
    const out=MPModels.predict(spec,x.rows[i]);
    for(const m of out.models){
      const delta=Math.abs(m.probability-x.expected[m.name][i]);
      maximum=Math.max(maximum,delta);assert(delta<.00001,d+' '+m.name+' '+delta);
    }
  }
}
console.log('99 synthetic input comparisons, all 15 trained models; max absolute difference',maximum);
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
try{
  const page=await browser.newPage({viewport:{width:1440,height:900}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8765/');
  await page.getByRole('button',{name:'Explore offline demo'}).click();
  await page.getByRole('heading',{name:'Your health activity'}).waitFor();
  assert(await page.getByText('No saved result yet').count()===3);
  await page.locator('.nav-link[data-route=diabetes]').click();
  await page.getByRole('button',{name:'Use synthetic example'}).click();
  await page.getByRole('button',{name:'Run model estimate'}).click();
  await page.getByRole('heading',{name:'Compare individual models'}).waitFor();
  assert(await page.getByText('Sample results cannot be added to personal history.').count()===1);
  await page.locator('.nav-link[data-route=screenings]').click();
  await page.locator('[name=s]').fill('110'); await page.locator('[name=d]').fill('70');
  await page.getByRole('button',{name:'Calculate screening'}).click();
  await page.getByRole('button',{name:'Save screening'}).click();
  await page.getByRole('button',{name:'Saved',exact:true}).waitFor();
  await page.locator('.nav-link[data-route=history]').click();await page.getByText('Blood pressure',{exact:true}).waitFor();
  await page.locator('.nav-link[data-route=atlas]').click();await page.locator('#query').fill('epilepsy');
  await page.locator('[data-topic]').filter({hasText:/^Epilepsy/}).first().click();await page.getByRole('heading',{name:'Epilepsy',exact:true}).waitFor();
  await page.locator('.nav-link[data-route=assistant]').click();await page.locator('[name=q]').fill('asthma');await page.getByRole('button',{name:'Ask MedPredict'}).click();await page.getByRole('heading',{name:'Asthma',exact:true}).waitFor();
  await page.locator('.nav-link[data-route=accessibility]').click();await page.locator('#braille-input').fill('Hello 123!');await page.getByRole('button',{name:'Convert',exact:true}).click();assert.equal(await page.locator('#braille-output').textContent(),'⠠⠓⠑⠇⠇⠕ ⠼⠁⠃⠉⠖');
  await page.locator('.nav-link[data-route=reports]').click();await page.locator('#report-text').fill('Haemoglobin: 14.2 g/dL\nCreatinine: 0.8 mg/dL');await page.getByRole('button',{name:'Find candidate lab values'}).click();await page.getByText('14.2',{exact:true}).waitFor();
  await page.locator('.nav-link[data-route=dashboard]').click();
  await page.screenshot({path:process.argv[4]+'/dashboard-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
  const logo=await page.locator('.mobile-brand').boundingBox(), menu=await page.locator('.mobile-controls').boundingBox();
  assert(logo.y+logo.height<=menu.y,'mobile logo must be above controls');
  await page.screenshot({path:process.argv[4]+'/dashboard-mobile.png',fullPage:true});
  await page.getByRole('button',{name:'Menu',exact:true}).click();
  await page.locator('.nav-link[data-route=assistant]').click();
  await page.getByRole('heading',{name:'Ask. Understand. Explore.'}).waitFor();
  await page.screenshot({path:process.argv[4]+'/assistant-mobile.png',fullPage:true});
  assert.deepEqual(errors,[]);
  console.log('Local UI flows, desktop and mobile layout, no JS errors: PASS');
}finally{await browser.close();}
