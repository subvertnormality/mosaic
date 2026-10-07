/* Reader text integrity. Recipe text keeps numbers that end a sentence (e.g. "Copy slot 1 to slot 2."),
 * audio track chips never show "undefined" for absent fields, and a page plays its own
 * lesson comparison recording first when it has one, a scene shows its authored starting point,
 * and a step with id "start" is labelled as the prepared starting point.
 * Characterisation of the reader, outside README. Regression: the renderer split
 * "slot 2. Change" into "slot" plus a numbered list item, dropping the 2. */
const {chromium}=require("playwright");
const assert=require("node:assert/strict");
(async()=>{const browser=await chromium.launch({args:["--no-sandbox"]});const report={passed:false,checked:0};
try{const page=await browser.newPage(),base=process.env.MOSAIC_MANUAL_URL||"http://127.0.0.1:8765/manual/";
const book=JSON.parse(await (await page.request.get(base+"generated/book.json")).body());
for(const f of book.features.filter(f=>(f.recipes||[]).length)){
 await page.goto(base+"#"+f.id);await page.waitForFunction(()=>!document.body.classList.contains("book-loading")&&document.body.dataset.routeReady==="1");
 await page.waitForFunction(id=>document.querySelector("h1")&&location.hash.slice(1).startsWith(id),f.id);
 await page.waitForFunction(title=>document.getElementById("recipes").innerText.replace(/\s+/g," ").includes(title),f.recipes.at(-1).title.replace(/\s+/g," "));
 const shown=(await page.locator("#recipes").innerText()).replace(/\s+/g," ");
 for(const r of f.recipes){for(const m of r.text.matchAll(/([A-Za-z][A-Za-z]*) (\d+)\.(?=\s)/g)){
  assert(shown.includes(m[1]+" "+m[2]),f.id+": recipe lost '"+m[0]+"'");report.checked++;}}}
const audio=JSON.parse(await (await page.request.get(base+"generated/audio-scenes.json")).body());
for(const id of [...new Set(audio.examples.flatMap(e=>e.feature_ids))]){await page.goto(base+"#"+id);await page.waitForFunction(()=>!document.body.classList.contains("book-loading")&&document.body.dataset.routeReady==="1");
 const chips=await page.locator("#track-list span").allInnerTexts();assert(!chips.some(c=>/undefined|null/.test(c)),id+": track chip shows "+JSON.stringify(chips));report.checked++;}
const expectTitle=async(id,title)=>{await page.goto(base+"#"+id);await page.waitForFunction(()=>!document.body.classList.contains("book-loading")&&document.body.dataset.routeReady==="1");assert.equal(await page.locator("#audio-title").innerText(),title,id+": default recording");report.checked++;};
// A feature page opens with the first lesson comparison that is not a course walkthrough recording, exactly as the reader chooses its default.
const defaultLesson=new Map();for(const lesson of audio.examples.filter(e=>e.purpose==="lesson-comparison"&&!e.course))for(const id of lesson.feature_ids)if(!defaultLesson.has(id))defaultLesson.set(id,lesson);
for(const [id,lesson] of defaultLesson)await expectTitle(id,lesson.title);
for(const [id,scene] of Object.entries(book.scenes).filter(([,s])=>s.starting_state)){const owner=book.features.find(f=>(f.scene_refs||[]).includes(id));if(!owner)continue;
 await page.goto(base+"#"+owner.id+"/"+id+"/"+scene.steps[0].id);await page.waitForFunction(()=>!document.body.classList.contains("book-loading")&&document.body.dataset.routeReady==="1");
 assert.equal(await page.locator("#example-state").innerText(),"Starting point: "+scene.starting_state,id+": starting point shown");report.checked++;}
for(const [id,scene] of Object.entries(book.scenes).filter(([,s])=>s.steps[0]&&s.steps[0].id==="start")){const owner=book.features.find(f=>(f.scene_refs||[]).includes(id));if(!owner)continue;
 await page.goto(base+"#"+owner.id+"/"+id+"/start");await page.waitForFunction(()=>!document.body.classList.contains("book-loading")&&document.body.dataset.routeReady==="1");
 assert.equal(await page.locator(".caption .phase-label").innerText(),"PREPARED STARTING POINT",id+": start step labelled as prepared");report.checked++;}
// MIDI strip: note names follow README "MIDI 60 (shown as C3)"; the strip lists each step's captured note-ons.
const NAMES=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"],name=n=>NAMES[n%12]+(Math.floor(n/12)-2);
assert.equal(name(60),"C3","README: MIDI 60 is shown as C3");
let strips=0;for(const [id,scene] of Object.entries(book.scenes)){const step=scene.steps.find(s=>s.output&&s.output.midi);if(!step)continue;const owner=book.features.find(f=>(f.scene_refs||[]).includes(id));if(!owner)continue;
 await page.goto(base+"#"+owner.id+"/"+id+"/"+step.id);await page.waitForFunction(()=>!document.body.classList.contains("book-loading")&&document.body.dataset.routeReady==="1");
 const text=await page.locator("#midi-text").innerText(),ons=step.output.midi.events.filter(e=>(e.bytes[0]&0xF0)===0x90&&e.bytes[2]>0);
 assert(text.startsWith("MIDI sent in this step:"),id+": strip heading");
 if(!step.output.midi.events.length)assert(text.endsWith("none."),id+": empty strip");
 for(const e of ons.slice(0,32))assert(text.includes(name(e.bytes[1])+" vel "+e.bytes[2]),id+"/"+step.id+": strip lists "+name(e.bytes[1]));
 report.checked++;if(++strips>=40)break;}
assert(strips>0,"no captured step carries MIDI for the strip");report.midi_strips=strips;
report.passed=true;console.log(JSON.stringify(report));}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
