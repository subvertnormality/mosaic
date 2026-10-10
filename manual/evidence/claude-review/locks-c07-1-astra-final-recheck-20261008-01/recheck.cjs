const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require('C:/Users/andy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const base='http://localhost:8785/',dir=__dirname,prior=path.join(dir,'../combined-candidate07-astra-recheck-20261008-01');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const load=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
function differences(a,b,p=''){if(JSON.stringify(a)===JSON.stringify(b))return[];if(a&&b&&typeof a==='object'&&typeof b==='object'){return [...new Set([...Object.keys(a),...Object.keys(b)])].flatMap(k=>differences(a[k],b[k],p+'/'+k));}return[{path:p,before:a,after:b}];}
(async()=>{
 const out={date:'2026-10-08',base,assets:{},diffs:[],observations:[],errors:[]};
 for(const rel of ['manual/generated/reader-index.json','manual/book.js','manual/manual.js','manual/manual.css','manual/index.html','cheat_sheet.html']){const r=await fetch(base+rel);if(!r.ok)throw Error(rel+' '+r.status);const b=Buffer.from(await r.arrayBuffer());out.assets[rel]=sha(b);fs.writeFileSync(path.join(dir,rel.split('/').pop()),b);}
 if(out.assets['manual/generated/reader-index.json']!=='254d19c38871b71973a6252fe859a02c4a9d6c8c464840d367de58baa8c4ff24')throw Error('Source mismatch');
 const j=load(path.join(dir,'reader-index.json')),old=load(path.join(prior,'reader-index.json'));
 out.diffs=differences(old,j);out.scene_refs_exact=JSON.stringify(old.scene_chunks)===JSON.stringify(j.scene_chunks);out.audio_refs_exact=JSON.stringify(old.audio_chunks)===JSON.stringify(j.audio_chunks);out.course_exact=JSON.stringify(old.learning_path)===JSON.stringify(j.learning_path);
 out.prior_assets_exact=Object.entries(load(path.join(prior,'collection.json')).assets).filter(([k])=>!k.endsWith('reader-index.json')).every(([k,v])=>out.assets[k]===v);
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 try{for(const width of [1440,390]){const context=await browser.newContext({viewport:{width,height:900}});const p=await context.newPage();p.on('pageerror',e=>out.errors.push({width,error:e.message}));
  for(const [route,label,phrase,required] of [
   ['locks/recipe/5','decay','Separate endpoint practice','Use E2 to select parameter slot 1, press K2, use E3 to highlight Decay, press K3 to assign it and K2 to return.'],
   ['small-hours/recipe/2','bass','The bass part is silent','while the completed drums continue their four-bar pattern.'],
   ['small-hours/recipe/3','chord','The chord part is silent','while the completed drums and bass continue their four-bar patterns.']]){
   await p.goto('about:blank');await p.goto(base+'manual/#'+route);await p.waitForFunction(()=>document.body.dataset.routeReady==='1');
   const target=p.locator('main p,main li').filter({hasText:phrase}).first();await target.waitFor({state:'visible'});const text=await target.innerText();if(!text.includes(required))throw Error('Expected correction absent: '+route);
   await target.scrollIntoViewIfNeeded();await p.screenshot({path:path.join(dir,label+'-'+width+'.png')});
   out.observations.push({width,route,text,mainText:await p.locator('main').innerText(),overflow:await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),boundingBox:await target.boundingBox()});
  }await context.close();}
 }finally{await browser.close();}
 out.endIndexHash=sha(Buffer.from(await(await fetch(base+'manual/generated/reader-index.json')).arrayBuffer()));
 fs.writeFileSync(path.join(dir,'observations.json'),JSON.stringify(out,null,2)+'\n');
 console.log(JSON.stringify({assets:out.assets,differences:out.diffs.map(d=>({path:d.path,beforeLength:String(d.before).length,afterLength:String(d.after).length})),scene_refs_exact:out.scene_refs_exact,audio_refs_exact:out.audio_refs_exact,course_exact:out.course_exact,prior_assets_exact:out.prior_assets_exact,observations:out.observations.map(({width,route,overflow})=>({width,route,overflow})),errors:out.errors,endIndexHash:out.endIndexHash},null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
