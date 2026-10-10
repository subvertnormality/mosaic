/* Reader text integrity. Recipe text keeps numbers that end a sentence (e.g. "Copy slot 1 to slot 2."),
 * audio track chips never show "undefined" for absent fields, and a page plays its own
 * lesson comparison recording first when it has one, a scene shows its authored starting point,
 * and a step with id "start" is labelled as the prepared starting point.
 * Characterisation of the reader, outside README. Regression: the renderer split
 * "slot 2. Change" into "slot" plus a numbered list item, dropping the 2. */
const {chromium}=require("playwright");
const assert=require("node:assert/strict");
const {decodeScreenPixels}=require("./manual_screen_oracle.cjs");
(async()=>{const browser=await chromium.launch({args:["--no-sandbox"]});const report={passed:false,checked:0};
try{const page=await browser.newPage(),base=process.env.MOSAIC_MANUAL_URL||"http://127.0.0.1:8765/manual/";
const book=JSON.parse(await (await page.request.get(base+"generated/book.json")).body());await page.goto(base);await page.waitForFunction(()=>document.body.dataset.routeReady==="1"&&!document.body.classList.contains("book-loading"));async function route(hash,finalHash=hash){const current=await page.evaluate(()=>location.hash);if(current!==hash){await page.evaluate(()=>{const body=document.body;let sawLoading=body.dataset.routeReady==="0",finish;window.__readerRouteCycle=new Promise(resolve=>finish=resolve);const observer=new MutationObserver(()=>{if(body.dataset.routeReady==="0")sawLoading=true;if(sawLoading&&body.dataset.routeReady==="1"){observer.disconnect();finish(true);}});observer.observe(body,{attributes:true,attributeFilter:["data-route-ready"]});});await page.evaluate(h=>location.hash=h,hash);assert.equal(await page.evaluate(()=>window.__readerRouteCycle),true,"Route change completes a fresh ready 0→1 generation: "+hash);}await page.waitForFunction(h=>document.body.dataset.routeReady==="1"&&!document.body.classList.contains("book-loading")&&location.hash===h,finalHash);}function expectedSceneHash(owner,id,step){const redirect=(owner.scene_context_links||[]).find(x=>x.scene_id===id&&x.route_behavior==="redirect");return redirect?"#"+redirect.canonical_route+"/"+step:"#"+owner.id+"/"+id+"/"+step;}function ownerForScene(id){const candidates=book.features.filter(f=>(f.scene_refs||[]).some(r=>(typeof r==="string"?r:r.scene_id||r.id)===id));return candidates.find(f=>{const context=(f.scene_context_links||[]).find(x=>x.scene_id===id);return !context||context.canonical_route.split("/")[0]===f.id;})||candidates[0];}
async function prearmClick(){await page.evaluate(()=>{const body=document.body;let sawLoading=body.dataset.routeReady==="0",finish;window.__readerRouteCycle=new Promise(resolve=>finish=resolve);const observer=new MutationObserver(()=>{if(body.dataset.routeReady==="0")sawLoading=true;if(sawLoading&&body.dataset.routeReady==="1"){observer.disconnect();finish(true);}});observer.observe(body,{attributes:true,attributeFilter:["data-route-ready"]});});}
const captionLinks=[
 {route:"#mods-and-software-devices/software-player-oilcan/select-player",scene:"software-player-oilcan",step:"select-player",label:"Apply Oilcan to the percussion channel",href:"#mods-and-software-devices/player-apply-oilcan"},
 {route:"#mods-and-software-devices/software-player-polyperc/select-player",scene:"software-player-polyperc",step:"select-player",label:"Apply Polyperc 1",href:"#mods-and-software-devices/lesson/play-polyperc-apply-confirm"},
 {route:"#mods-and-software-devices/software-player-doubledecker/select-player",scene:"software-player-doubledecker",step:"select-player",label:"Apply Doubledecker to the chord channel",href:"#mods-and-software-devices/player-apply-doubledecker"},
 {route:"#midi-keyboard-input/workflow-second-channel/two-channels",scene:"workflow-second-channel",step:"two-channels",label:"MIDI Keyboard Input",href:"#midi-keyboard-input/workflow-second-channel"}];
for(const c of captionLinks){const scene=book.scenes[c.scene],step=scene.steps.find(x=>x.id===c.step),visibleCaption=step.caption.replace(/\[([^\]]+)\]\((#[^)]+)\)/g,"$1");assert(step,"Authored linked caption source exists");await route(c.route);await page.waitForFunction(({hash,raw,visible})=>document.body.dataset.routeReady==="1"&&location.hash===hash&&(document.querySelector("#caption")?.textContent===raw||document.querySelector("#caption")?.innerText===visible),{hash:c.route,raw:step.caption,visible:visibleCaption});assert.equal(await page.evaluate(()=>location.hash),c.route,"Raw scene route stays selected while its caption links to the handoff");assert.equal(await page.locator("#caption").innerText(),visibleCaption,"Visible caption preserves exact authored wording and readable link label");const link=page.locator('#caption a[href="'+c.href+'"]');assert.equal(await link.count(),1,"Caption exposes the exact authored destination");assert.equal(await link.innerText(),c.label,"Caption link uses the authored action label");assert.equal(await link.isVisible(),true,"Caption handoff is visible");assert.deepEqual(await page.locator("#screen").evaluate(e=>Array.from(e.getContext("2d").getImageData(0,0,128,64).data).filter((_,i)=>i%4===0)),decodeScreenPixels(step.output),"Caption rendering leaves the exact captured framebuffer unchanged");assert.deepEqual(await page.locator("#grid button").evaluateAll(es=>es.map(e=>Number(e.dataset.level))),step.output.grid,"Caption rendering leaves all 128 captured grid levels unchanged");report.checked++;}for(const f of book.features.filter(f=>f.category!=="developer"&&(f.recipes||[]).length)){
 for(let i=0;i<f.recipes.length;i++){const r=f.recipes[i],hash="#"+f.id+"/recipe/"+(i+1);
  await route("#cookbook");
  const link=page.locator("#book-home a[href=\""+hash+"\"]");
  assert.equal(await link.count(),1,f.id+": cookbook contains the authored recipe entry");
  assert.equal(await link.isVisible(),true,f.id+": cookbook recipe entry is visible");
  await prearmClick();await link.click();
  assert.equal(await page.evaluate(()=>window.__readerRouteCycle),true,"Visible recipe link completes a fresh route-ready generation: "+hash);
  await page.waitForFunction(({title})=>document.body.dataset.routeReady==="1"&&document.querySelector("#recipe-workspace h1")?.textContent===title,{title:r.title});
  const canonical=await page.locator("#recipe-workspace").evaluate(n=>({feature:n.dataset.featureId,index:Number(n.dataset.recipeIndex)})),canonicalFeature=book.features.find(x=>x.id===canonical.feature),canonicalRecipe=canonicalFeature?.recipes?.[canonical.index-1];
  assert.equal(await page.evaluate(()=>location.hash),"#"+canonical.feature+"/recipe/"+canonical.index,f.id+": visible card resolves to the exact canonical recipe workspace");
  assert.equal(canonicalFeature?.recipes?.[canonical.index-1]?.title,r.title,f.id+": canonical owner and recipe index resolve to the authored title");
  const shown=(await page.locator("#recipe-workspace .recipe-body").innerText()).replace(/\s+/g," ");
  assert.equal(await page.locator("#recipe-workspace").isVisible(),true,f.id+": canonical recipe workspace is visible");
  assert.equal(await page.locator("#recipe-workspace h1").innerText(),r.title,f.id+": exact canonical recipe title");
  for(const m of canonicalRecipe.text.matchAll(/([A-Za-z][A-Za-z]*) (\d+)\.(?=\s)/g)){assert(shown.includes(m[1]+" "+m[2]),f.id+": visible recipe lost '"+m[0]+"'");report.checked++;}
 }}
const audio=JSON.parse(await (await page.request.get(base+"generated/audio-scenes.json")).body());
for(const example of audio.examples){await route("#recording/"+example.id);await page.waitForFunction(title=>document.getElementById("audio-title")?.textContent===title,example.title);
 const chips=await page.locator("#track-list span").allInnerTexts();assert(!chips.some(c=>/undefined|null/.test(c)),example.id+": track chip shows "+JSON.stringify(chips));assert.equal(await page.locator("#audio-title").innerText(),example.title,example.id+": original canonical soundtrack");report.checked++;}
for(const [id,scene] of Object.entries(book.scenes).filter(([,s])=>s.starting_state)){const owner=ownerForScene(id);if(!owner)continue;
 await route("#"+owner.id+"/"+id+"/"+scene.steps[0].id,expectedSceneHash(owner,id,scene.steps[0].id));
 assert.equal(await page.locator("#example-state").innerText(),"Starting point: "+scene.starting_state,id+": starting point shown");report.checked++;}
for(const [id,scene] of Object.entries(book.scenes).filter(([,s])=>s.steps[0]&&s.steps[0].id==="start")){const owner=ownerForScene(id);if(!owner)continue;
 await route("#"+owner.id+"/"+id+"/start",expectedSceneHash(owner,id,"start"));
 assert.equal(await page.locator(".caption .phase-label").innerText(),"Before",id+": an actual start frame is labelled Before even on its explicit recorded-frame route");report.checked++;}
// MIDI strip: note names follow README "MIDI 60 (shown as C3)"; the strip lists each step's captured note-ons.
const NAMES=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"],name=n=>NAMES[n%12]+(Math.floor(n/12)-2);
assert.equal(name(60),"C3","README: MIDI 60 is shown as C3");
let strips=0;for(const [id,scene] of Object.entries(book.scenes)){const step=scene.steps.find(s=>s.output&&s.output.midi);if(!step)continue;const owner=ownerForScene(id);if(!owner)continue;
 await route("#"+owner.id+"/"+id+"/"+step.id,expectedSceneHash(owner,id,step.id));
 // Characterisation: short MIDI output is scoped only with an exact untruncated prefix proof; full source remains lossless in Evidence.
 const midi=step.output.midi,prev=scene.steps[scene.steps.indexOf(step)-1]?.output?.midi;
 let events=midi.events,label="Recorded MIDI output";
 if(step.id==="start"){events=[];label="Current action MIDI (starting view; earlier output not shown here)";}
 else if(prev&&prev.truncated===false&&midi.truncated===false&&prev.events.length<=events.length&&prev.events.every((e,i)=>JSON.stringify(e)===JSON.stringify(events[i]))){events=events.slice(prev.events.length);label="MIDI since the previous frame";}
 const text=await page.locator("#midi-text").innerText();assert(text.startsWith(label+":"),id+": honest MIDI scope");
 if(!events.length)assert(text.endsWith("none."),id+": empty current strip");
 const programState=new Map();let repeatedPrograms=0;let displayed=events.filter(e=>{if((e.bytes[0]&240)!==192)return true;const key=e.port+":"+(e.bytes[0]&15),prior=programState.get(key);programState.set(key,JSON.stringify(e.bytes));if(prior===JSON.stringify(e.bytes)){repeatedPrograms++;return false;}return true;});if(repeatedPrograms)assert(text.includes(repeatedPrograms+" repeated unchanged program messages in Evidence"),id+": exact actual repeated program count");if(midi.truncated===false&&events.length===256&&events.filter(e=>(e.bytes[0]&240)===144&&e.bytes[2]>0).length===128&&events.filter(e=>(e.bytes[0]&240)===128||(e.bytes[0]&240)===144&&e.bytes[2]===0).length===128){assert(text.includes("128 note-ons and 128 note-offs"),id+": exact complete actual output counts");displayed=displayed.filter(e=>e.bytes[1]>=60&&e.bytes[1]<=72);}const zero=Number.isFinite(events[0]?.ms)?events[0].ms:0;for(const e of displayed.slice(0,32)){const [st,n,v]=e.bytes,type=st&0xF0;const value=type===0x90&&v>0?name(n)+" vel "+v:type===0x80||type===0x90&&v===0?"Note off "+name(n):type===0xB0?"CC "+n+" = "+v:type===0xC0?"Program "+n:"MIDI "+e.bytes.join(" ");const time=Number.isFinite(e.ms)?e.ms-zero:Number.isFinite(e.logical_ns)&&Number.isFinite(midi.provenance?.start_logical_ns)?(e.logical_ns-midi.provenance.start_logical_ns)/1e6:Number.isFinite(e.monotonic_ns)&&Number.isFinite(midi.provenance?.start_monotonic_ns)?(e.monotonic_ns-midi.provenance.start_monotonic_ns)/1e6:null;const stamp=time===null?"":" @"+Math.round(time)+" ms";assert(text.includes(value+" (ch "+((st&15)+1)+")"+stamp),id+": exact visible semantic MIDI value and captured time origin");}
 // Full captured event data remains pinned in the qualified source chunks and manual-book test; this reader presents the authored semantic excerpt without a technical history panel.
 assert(text.length>0,id+": visible MIDI summary remains available");
 report.checked++;if(++strips>=40)break;}
assert(strips>0,"no captured step carries MIDI for the strip");report.midi_strips=strips;
report.passed=true;console.log(JSON.stringify(report));}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
