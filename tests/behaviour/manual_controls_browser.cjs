// Captured-result controls acceptance outside README. Actual published Masks frames remain the oracle.
const {chromium}=require("playwright"),assert=require("node:assert/strict"),fs=require("node:fs"),crypto=require("node:crypto");
const {decodeScreenPixels}=require("./manual_screen_oracle.cjs");
(async()=>{const browser=await chromium.launch({args:["--no-sandbox"]}),report={passed:false,checks:[]};try{const page=await browser.newPage(),base=process.env.MOSAIC_MANUAL_URL||"http://127.0.0.1:8765/manual/";const bookResponse=await page.request.get(base+"generated/book.json"),bookBytes=await bookResponse.body(),book=JSON.parse(bookBytes);report.book_sha256=crypto.createHash("sha256").update(bookBytes).digest("hex");report.player_sha256=crypto.createHash("sha256").update(await page.request.get(base+"manual.js").then(r=>r.body())).digest("hex");const index=await page.request.get(base+"generated/reader-index.json").then(r=>r.json());report.reader_index_contract_ids=[];let nav=0;
const rejected_none=/No recorded control cue is available here; use View next result/,rejected=/does not match the current recorded cue/,completed=/Captured walkthrough cue completed/;
const pixelsOf=()=>page.locator("#screen").evaluate(c=>Array.from(c.getContext("2d").getImageData(0,0,128,64).data).filter((_,i)=>i%4===0));
const frame=async(scene,stepId)=>{const step=scene.steps.find(x=>x.id===stepId);assert(step,"Unknown captured step "+stepId);assert.deepEqual(await pixelsOf(),decodeScreenPixels(step.output),"Screen must be the exact captured "+scene.id+"/"+stepId+" framebuffer");assert.deepEqual(await page.locator("#grid button").evaluateAll(b=>b.map(x=>Number(x.dataset.level))),step.output.grid,"All 128 grid levels must be the captured "+stepId+" levels");};
// Open one recorded course lesson from its own route and return its captured scene, stage contract and pad/key helpers.
const open=async(chapter,lessonId)=>{const contract=index.teaching_contracts[lessonId];assert(contract&&contract.owner_type==="course-stage","Course contract "+lessonId+" must be published");const scene=book.scenes[contract.scene_id];report.reader_index_contract_ids.push(lessonId);await page.goto(base+"?lesson="+(++nav)+"#"+chapter+"/lesson/"+lessonId);await page.waitForFunction(()=>document.body.dataset.routeReady==="1"&&!!document.getElementById("counter").textContent.match(/^\d\d \//));const start=scene.steps.findIndex(x=>x.id===contract.from_step_id);await page.waitForFunction(n=>document.getElementById("counter").textContent.startsWith(n),String(start+1).padStart(2,"0"));await frame(scene,contract.from_step_id);return {scene,contract,from:contract.from_step_id,to:contract.to_step_id};};
const pad=(x,y)=>page.locator("#grid button").nth((y-1)*16+x-1),enc=n=>page.locator('.encoder[data-n="'+n+'"]'),key=n=>page.locator('[data-key="'+n+'"]');
const notice=()=>page.locator("#notice").textContent(),counter=()=>page.locator("#counter").textContent();
const press=async(locator)=>{await locator.focus();await page.keyboard.down("Space");},lift=async(locator)=>{await locator.focus();await page.keyboard.up("Space");},turn=async(n,direction)=>{await enc(n).focus();await page.keyboard.press(direction>0?"ArrowRight":"ArrowLeft");};
const held=async()=>page.locator(".held").count();
const reveal=async(L)=>{const view=page.locator('button[data-action-kind="preview-recorded-result"]');assert.equal(await view.getAttribute("aria-current"),"step","View the captured result must be the current cue once every recorded control is done");await view.click();await frame(L.scene,L.to);};
// README: Masks, hold a step and turn E3 for that step only (Masks chapter lesson masks-hold then masks-edit then masks-release).
let L=await open("masks","masks-hold");const counterBefore=await counter();
await turn(3,1);assert.match(await notice(),rejected);assert.equal(await held(),0);assert.equal(await counter(),counterBefore);await frame(L.scene,L.from);
await press(pad(12,4));assert.match(await notice(),rejected);assert.equal(await held(),0,"A wrong pad must not appear held");await lift(pad(12,4));await frame(L.scene,L.from);
await press(pad(13,4));assert(await pad(13,4).evaluate(b=>b.classList.contains("held")),"The recorded hold cue marks the matching pad held");await frame(L.scene,L.from);assert.equal(await counter(),counterBefore,"Holding does not reveal the result");
await reveal(L);await lift(pad(13,4));
report.checks.push("Recorded hold cue: wrong encoder and wrong pad are rejected; the matching keyboard hold shows held and the exact held result appears only on View next result");
L=await open("masks","masks-edit");
await turn(3,-1);assert.match(await notice(),rejected);await frame(L.scene,L.from);
await turn(3,1);assert.match(await notice(),completed);await frame(L.scene,L.from);
await turn(3,1);assert.match(await notice(),rejected,"No encoder cue remains once the turn is recorded");await frame(L.scene,L.from);
await reveal(L);
report.checks.push("Recorded encoder cue rejects the wrong direction and accepts the recorded clockwise turn, with the result shown only on View next result");
L=await open("masks","masks-release");
await turn(3,1);assert.match(await notice(),rejected);await frame(L.scene,L.from);
await press(pad(13,4));await lift(pad(13,4));assert.match(await notice(),completed);await frame(L.scene,L.from);
await reveal(L);
report.checks.push("Keyboard release of the recorded held pad completes the release cue, then exact released result");
// Grouped cue: field encoder, held pad, value encoder, release, play.
L=await open("masks","masks-quiet");
await turn(3,-1);assert.match(await notice(),rejected,"Value encoder cannot be used before selecting the field");await frame(L.scene,L.from);
await turn(2,1);assert.match(await notice(),/Field selected/);await frame(L.scene,L.from);
await turn(3,-1);assert.match(await notice(),rejected,"Value encoder cannot skip the held pad");await frame(L.scene,L.from);
await press(pad(13,4));await lift(pad(13,4));assert.equal(await held()>=1,true,"The pad stays held in the walkthrough after the physical key is lifted");await frame(L.scene,L.from);
await turn(3,-1);assert.match(await notice(),completed);await frame(L.scene,L.from);
await press(pad(13,4));await lift(pad(13,4));await frame(L.scene,L.from);
await pad(1,8).click();assert.match(await notice(),completed);await frame(L.scene,L.from);
await reveal(L);
report.checks.push("Grouped select-value cue needs field encoder, held pad, value encoder, release and play before the exact quiet-step result; out-of-order controls are rejected without revealing it");
// Held grid plus norns key plus release.
L=await open("masks","masks-clear");
await key(2).click();assert.match(await notice(),rejected,"K2 before the recorded sequence reaches it is rejected");await frame(L.scene,L.from);
await pad(1,8).click();await frame(L.scene,L.from);
await key(2).click();assert.match(await notice(),rejected);await frame(L.scene,L.from);
await press(pad(13,4));await lift(pad(13,4));assert.equal(await held()>=1,true);await key(2).click();assert.match(await notice(),completed);await frame(L.scene,L.from);
await press(pad(13,4));await lift(pad(13,4));await frame(L.scene,L.from);
await pad(1,8).click();await frame(L.scene,L.from);
await reveal(L);
report.checks.push("Held grid (keyboard) plus clicked norns key plus release advance only through the recorded cue order to the exact clear result");
// Norns key hold and release grouped around a grid tap.
L=await open("keep-your-work","keep-your-work-temporary-edit");
await pad(3,8).click();await frame(L.scene,L.from);
await key(2).click();assert.match(await notice(),rejected);
await press(key(1));assert(await key(1).evaluate(b=>b.classList.contains("held")),"The recorded K1 hold marks the key held");await lift(key(1));await pad(1,1).click();await frame(L.scene,L.from);
await press(key(1));await lift(key(1));await frame(L.scene,L.from);
await reveal(L);
report.checks.push("Grouped norns key hold, grid tap and release are all required; no fabricated intermediate frames");
// Authored encoder sequence selects the exact velocity-default result.
L=await open("first-sound","first-sound-defaults");
for(let i=0;i<3;i++){await turn(3,1);assert.match(await notice(),rejected,"The value encoder cannot precede the recorded field encoder");await turn(2,1);assert.match(await notice(),/Field selected/);await turn(3,1);assert.match(await notice(),completed);await frame(L.scene,L.from);}
await turn(3,1);assert.match(await notice(),rejected,"A fourth turn is not part of the recorded sequence");await frame(L.scene,L.from);
await reveal(L);
report.checks.push("First-loop authored encoder sequence selects exact defaults result");
const largeFeature=book.features.find(f=>(f.scene_refs||[]).some(ref=>{const s=book.scenes[typeof ref==="string"?ref:ref.id];return s?.steps.some((step,i)=>i>0&&step.inputs.length>24);}));const largeScene=(largeFeature.scene_refs||[]).map(ref=>book.scenes[typeof ref==="string"?ref:ref.id]).find(s=>s?.steps.some((step,i)=>i>0&&step.inputs.length>24)),largeIndex=largeScene.steps.findIndex((step,i)=>i>0&&step.inputs.length>24);await page.goto(base+"#"+largeFeature.id+"/"+largeScene.id+"/"+largeScene.steps[largeIndex-1].id);await page.waitForFunction(caption=>document.getElementById("caption").textContent===caption&&document.body.dataset.routeReady==="1",largeScene.steps[largeIndex-1].caption);const beforeLarge=await page.locator("#counter").textContent();await page.locator('[data-n="3"]').click();assert.equal(await page.locator("#counter").textContent(),beforeLarge);assert.match(await page.locator("#control-help").textContent(),/No authored practice is available for this transition; View next result remains available/);assert.match(await page.locator("#notice").textContent(),rejected_none);await page.click("#next");assert.equal(await page.locator("#caption").textContent(),largeScene.steps[largeIndex].caption);report.checks.push("Large reference bundles without a recorded cue say so and advance only through View next result");report.passed=true;}finally{await browser.close();fs.writeFileSync(process.env.MOSAIC_CONTROLS_REPORT||"manual/evidence/controls-browser-report.json",JSON.stringify(report,null,2)+"\n");}console.log(JSON.stringify(report));})().catch(e=>{console.error(e);process.exitCode=1;});
