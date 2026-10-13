/* Manual renderer acceptance; characterisation outside README.
 * Run with NODE_PATH pointing to an isolated Playwright install.
 * No emulator is launched or left running by these browser checks.
 */
const {chromium}=require("playwright");
const assert=require("node:assert/strict");
const {decodeScreenPixels}=require("./manual_screen_oracle.cjs");
const fs=require("node:fs");
const path=require("node:path");
const crypto=require("node:crypto"),{execFileSync}=require("node:child_process");
const root=path.resolve(__dirname,"../..");
(async()=>{
 const data=JSON.parse(fs.readFileSync(path.join(root,"manual/generated/pilot.json")));
 const audioManifest=JSON.parse(fs.readFileSync(path.join(root,"manual/generated/audio-scenes.json")));
 const pilotAudio=data.audio;
 const selectedAudio=audioManifest.examples.find(example=>example.feature_ids.includes("masks"));
 const authoredAudio=JSON.parse(execFileSync("python3",["-c","import json,yaml,sys; print(json.dumps(yaml.safe_load(open(sys.argv[1]))))",path.join(root,"manual/audio-scenes.yaml")],{encoding:"utf8"}));
 const authoredExample=selectedAudio&&authoredAudio.examples.find(example=>example.id===selectedAudio.id);
 const captureSource=fs.readFileSync(path.join(root,"tools/manual_audio.py"),"utf8");
 assert(captureSource.includes("job=c.runtime.capture_start(seconds+3)"),"Musical capture tail contract changed: independently review expected duration");
 if(selectedAudio){assert(authoredExample,"Selected audio must have an authored recipe");assert.equal(selectedAudio.bars,authoredExample.bars);assert.equal(selectedAudio.bpm,authoredExample.bpm);data.audio=selectedAudio;}
 const browser=await chromium.launch({headless:true,args:["--no-sandbox"]});
 const report={schema_version:1,passed:false,viewports:[],checks:[],audio_contract_source_sha256:crypto.createHash("sha256").update(captureSource).digest("hex")}, errors=[];
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  page.on("pageerror",e=>errors.push(e.message));const base=process.env.MOSAIC_MANUAL_URL||"http://localhost:8765/manual/";async function routeHash(hash){const current=await page.evaluate(()=>location.hash);if(current!==hash){await page.evaluate(()=>{const body=document.body;let sawLoading=body.dataset.routeReady==="0",finish;window.__manualRouteCycle=new Promise(resolve=>finish=resolve);const observer=new MutationObserver(()=>{if(body.dataset.routeReady==="0")sawLoading=true;if(sawLoading&&body.dataset.routeReady==="1"){observer.disconnect();finish(true);}});observer.observe(body,{attributes:true,attributeFilter:["data-route-ready"]});});await page.evaluate(h=>location.hash=h,hash);assert.equal(await page.evaluate(()=>window.__manualRouteCycle),true,"Route change completes a fresh ready 0→1 generation: "+hash);}await page.waitForFunction(h=>document.body.dataset.routeReady==="1"&&location.hash===h,hash);}
  await page.goto((process.env.MOSAIC_MANUAL_URL||"http://localhost:8765/manual/")+"#masks");
  await page.waitForFunction(()=>!document.body.classList.contains("book-loading")&&document.body.dataset.routeReady==="1"&&document.getElementById("scene").options.length>0);
  assert.equal(await page.locator("h1").textContent(),"Masks");
  async function frameCheck(output){
    const actual=await page.evaluate(()=>({pixels:Array.from(document.getElementById("screen").getContext("2d").getImageData(0,0,128,64).data).filter((_,i)=>i%4===0),grid:Array.from(document.querySelectorAll("#grid button")).map(b=>Number(b.dataset.level))}));
    const expected=decodeScreenPixels(output);
    assert.deepEqual(actual.pixels,expected,"Canvas must match every captured framebuffer pixel");
    assert.deepEqual(actual.grid,output.grid,"All 128 brightness values must match");
  }
  for(let i=0;i<data.scenes.length;i++){
    const scene=data.scenes[i];await page.selectOption("#scene",String(i));
    for(let j=0;j<scene.steps.length;j++){
      if(j)await page.click("#next");
      assert.equal(await page.locator("#caption").textContent(),scene.steps[j].caption);
      await frameCheck(scene.steps[j].output);
    }
    for(let j=scene.steps.length-2;j>=0;j--){await page.click("#previous");await frameCheck(scene.steps[j].output);}
  }
  report.checks.push("All scene captions, forward/back frames and 128 LED values");
  const noCue=/No recorded control cue is available here/;
  const masksBook=await page.request.get((process.env.MOSAIC_MANUAL_URL||"http://localhost:8765/manual/")+"generated/book.json").then(r=>r.json());
  const masksFeature=masksBook.features.find(f=>f.id==="masks"),counterScene=data.scenes[0];
  const counterTextAt=n=>{
    const step=counterScene.steps[n-1],row=masksFeature.scene_milestones.find(x=>x.scene_id===counterScene.id);
    const group=row?.groups.find(x=>x.step_ids.includes(step.id));assert(group,"Counter step belongs to an authored milestone");
    const position=group.step_ids.indexOf(step.id)+1;
    assert.equal(position,n,"Authored milestone position matches the captured step");
    return group.label+" · "+position+"/"+group.step_ids.length;
  };
  const counterAt=async n=>assert.equal(await page.locator("#counter").textContent(),counterTextAt(n),"Exact authored milestone title and count");
  await page.selectOption("#scene","0");await counterAt(1);
  // Characterisation: the free guided replay was removed. The canonical lesson supplies a recorded cue; a wrong encoder remains inert and says so.
  await page.locator(".encoder[data-n='3']").click();
  await counterAt(1);assert.match(await page.locator("#notice").textContent(),/^That control or direction does not match the current recorded cue\.$/);
  await page.locator(".encoder[data-n='3']").focus();await page.keyboard.press("ArrowRight");
  await counterAt(1);
  const knob=await page.locator(".encoder[data-n='3']").boundingBox();
  await page.mouse.move(knob.x+knob.width/2,knob.y+knob.height/2);
  await page.mouse.down();await page.mouse.move(knob.x+knob.width/2+25,knob.y+knob.height/2);await page.mouse.up();
  await counterAt(1);await frameCheck(data.scenes[0].steps[0].output);
  report.checks.push("Without a recorded cue encoder click, key press and drag leave the captured frame and step unchanged");
  for(const kind of ["grid","key"]){
    const si=data.scenes.findIndex(scene=>scene.steps.slice(1).some(step=>step.inputs.some(a=>a.type===kind)));
    if(si<0)throw Error("Missing control acceptance fixture");
    const target=data.scenes[si].steps.findIndex((step,i)=>i>0&&step.inputs.some(a=>a.type===kind));
    await page.selectOption("#scene",String(si));
    for(let j=0;j<target-1;j++)await page.click("#next");
    const input=data.scenes[si].steps[target].inputs.find(a=>a.type===kind);
    if(kind==="key")await page.locator("[data-key='"+input.n+"']").click();
    else await page.locator("#grid button").nth((input.y-1)*16+input.x-1).click();
    await frameCheck(data.scenes[si].steps[target-1].output);
    assert.match(await page.locator("#notice").textContent(),noCue);
    assert.equal(await page.locator(".held").count(),0,"An uncued pad press must not mark a control as held");
    await page.click("#next");await frameCheck(data.scenes[si].steps[target].output);
  }
  await page.locator("#grid button").first().focus();await page.keyboard.press("ArrowRight");
  assert.equal(await page.locator("#grid button").nth(1).evaluate(n=>document.activeElement===n),true);
  await page.selectOption("#scene","0");await page.click("#autoplay");
  await page.waitForFunction(expected=>document.getElementById("counter").textContent===expected,counterTextAt(2));await counterAt(2);
  await page.click("#autoplay");await frameCheck(data.scenes[0].steps[1].output);
  report.checks.push("Uncued pictured controls preserve current frame; explicit Next, grid focus and autoplay");

  // Recorded-cue flow: Masks course lessons advance only on the matching recorded control.
  const courseMasks=JSON.parse(fs.readFileSync(path.join(root,"manual/generated/book.json"))).scenes["course-masks"];
  const cframe=async id=>{await frameCheckScene(courseMasks.steps.find(s=>s.id===id).output);};
  async function frameCheckScene(output){await frameCheck(output);}
  const rejected=/does not match the current recorded cue/;
  await page.goto((process.env.MOSAIC_MANUAL_URL||"http://localhost:8765/manual/")+"#masks/lesson/masks-hold");
  await page.waitForFunction(()=>document.body.dataset.routeReady==="1"&&document.getElementById("counter").textContent.startsWith("02"));
  // Characterisation: open the enlarged public grid before physical input; exact held and frame oracles below are unchanged.
  if(!await page.locator("#enlarged-grid-controls").evaluate(n=>n.open))await page.locator("#enlarged-grid-controls>summary").click();
  await cframe("masks-open");
  const hold=page.locator("#grid button").nth(3*16+12);
  await page.locator(".encoder[data-n='3']").focus();await page.keyboard.press("ArrowRight");
  assert.match(await page.locator("#notice").textContent(),rejected);assert.equal(await hold.evaluate(b=>b.classList.contains("held")),false);
  await page.locator("#grid button").nth(3*16+11).focus();await page.keyboard.down("Space");await page.keyboard.up("Space");
  assert.match(await page.locator("#notice").textContent(),rejected);assert.equal(await page.locator(".held").count(),0);
  await cframe("masks-open");
  await hold.focus();await page.keyboard.down("Space");
  assert.equal(await hold.evaluate(b=>b.classList.contains("held")),true,"Matching hold cue marks the pad held");
  await cframe("masks-open");
  await page.locator("#lesson-workspace .workspace-checkpoints button").filter({hasText:"Show result"}).click();await cframe("masks-hold");
  await page.keyboard.up("Space");
  report.checks.push("Recorded hold cue rejects wrong encoder and pad, accepts the matching pad and reveals the exact held result only on View next result");
  await page.goto((process.env.MOSAIC_MANUAL_URL||"http://localhost:8765/manual/")+"#masks/lesson/masks-edit");
  await page.waitForFunction(()=>document.body.dataset.routeReady==="1"&&document.getElementById("counter").textContent.startsWith("03"));
  await cframe("masks-hold");
  await page.locator(".encoder[data-n='3']").focus();await page.keyboard.press("ArrowLeft");
  assert.match(await page.locator("#notice").textContent(),rejected);await cframe("masks-hold");
  await page.keyboard.press("ArrowRight");
  assert.match(await page.locator("#notice").textContent(),/Captured walkthrough cue completed/);await cframe("masks-hold");
  await page.locator("#lesson-workspace .workspace-checkpoints button").filter({hasText:"Show result"}).click();await cframe("masks-edit");
  report.checks.push("Recorded encoder cue rejects the wrong direction and accepts the recorded clockwise turn");
  await page.goto((process.env.MOSAIC_MANUAL_URL||"http://localhost:8765/manual/")+"#masks");
  await page.waitForFunction(()=>document.body.dataset.routeReady==="1"&&document.getElementById("scene").options.length>0);

  await page.fill("#search","clear");
  await page.waitForFunction(()=>document.querySelectorAll("#search-results a").length>0);
  assert.match(await page.locator("#search-results").textContent(),/Controls|inherit|Masks|Clear/i);
  await page.click("#dense");assert.equal(await page.locator("body").evaluate(n=>n.classList.contains("dense")),true);
  await page.click("#dense");
  const before=await page.locator("html").getAttribute("data-theme");await page.click("#theme");
  assert.notEqual(await page.locator("html").getAttribute("data-theme"),before);
  report.checks.push("Search, dense reference and theme switching");
  for(const size of [{width:1440,height:1100},{width:768,height:1024},{width:390,height:844}]){
    await page.setViewportSize(size);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,"No horizontal overflow");
    const pads=await page.locator("#grid").boundingBox();assert(pads.width>250);
    report.viewports.push(size);
    await page.screenshot({path:path.join(root,"manual/evidence/browser-"+size.width+".png"),fullPage:true});
  }
  await page.setViewportSize({width:1440,height:1100});
  if(data.audio){
    await page.goto((process.env.MOSAIC_MANUAL_URL||"http://localhost:8765/manual/")+"#recording/"+data.audio.id);await page.waitForFunction(()=>document.body.dataset.routeReady==="1"&&!!document.querySelector("#recording-workspace"));
    await page.waitForFunction(()=>Number.isFinite(document.getElementById("audio").duration));
    const durations=await page.evaluate(async files=>{
      const ctx=new AudioContext(), result=[];
      try{for(const file of files){const bytes=await fetch(file).then(r=>r.arrayBuffer());const decoded=await ctx.decodeAudioData(bytes);result.push(decoded.duration);}}finally{await ctx.close();}
      return result;
    },data.audio.files);
    // Independent authored bars/tempo and native capture_start(seconds+3), not generated metrics.
    const expectedDuration=selectedAudio?authoredExample.bars*4*60/authoredExample.bpm+3:pilotAudio.bars*4*60/pilotAudio.bpm+2;
    for(const duration of durations)assert(Math.abs(duration-expectedDuration)<.06,"Every encoded format must decode the full captured clip");
    report.checks.push("Selected Opus and MP3 match authored four-bar tempo and independent three-second native capture tail");
    // Preserve the original pilot's separate two-second-tail oracle.
    if(pilotAudio){const pilotDurations=await page.evaluate(async files=>{const ctx=new AudioContext();try{return await Promise.all(files.map(file=>fetch(file).then(r=>r.arrayBuffer()).then(bytes=>ctx.decodeAudioData(bytes)).then(audio=>audio.duration)));}finally{await ctx.close();}},pilotAudio.files);const pilotExpected=pilotAudio.bars*4*60/pilotAudio.bpm+2;for(const duration of pilotDurations)assert(Math.abs(duration-pilotExpected)<.06,"Historical pilot retains its exact independent two-second tail");report.checks.push("Historical pilot duration oracle preserved separately");}
    // Canonical audio home has no prior native scene: preserve its original captured timeline seek oracle.
    await page.locator("#audio").evaluate(async a=>{await a.play();await new Promise(resolve=>{a.addEventListener("seeked",resolve,{once:true});a.currentTime=2;});});
    await page.waitForFunction(()=>document.getElementById("counter").textContent.startsWith("LISTEN"));
    let current=await page.locator("#audio").evaluate(a=>a.currentTime);
    await frameCheck((data.audio.timeline.filter(f=>f.time<=current).at(-1)||data.audio.timeline[0]).output);
    await page.locator("#audio").evaluate(a=>a.pause());
    assert(await page.locator("#audio").evaluate(a=>a.paused));
    assert(await page.locator("#audio").evaluate(a=>Number.isFinite(a.duration)&&a.duration>10));
    // The original pause-restoration oracle needs an actual native scene and its exact authored recording relationship.
    const compiledBook=await page.request.get(base+"generated/book.json").then(r=>r.json()),lessonRecording=Object.values(compiledBook.recordings_context.recordings).find(r=>r.lesson_relations.some(x=>x.kind==="course-stage"&&x.course_stage_id==="masks-listen"&&x.relationship==="exact"));
    assert(lessonRecording,"A genuine exact Masks-listen recording relationship is required");
    const lessonAudio=audioManifest.examples.find(a=>a.id===lessonRecording.id);assert(lessonAudio,"Exact stage recording must use an original captured audio example");
    const lessonRelation=lessonRecording.lesson_relations.find(x=>x.kind==="course-stage"&&x.course_stage_id==="masks-listen"&&x.relationship==="exact");
    await routeHash("#"+lessonRelation.canonical_route.replace(/^#/,""));
    await page.waitForFunction(title=>document.body.dataset.routeReady==="1"&&!!document.querySelector("#lesson-workspace")&&document.getElementById("audio-title").textContent===title&&Number.isFinite(document.getElementById("audio").duration),lessonRecording.title);
    const nativeBefore=await page.evaluate(()=>({pixels:Array.from(document.getElementById("screen").getContext("2d").getImageData(0,0,128,64).data).filter((_,i)=>i%4===0),grid:Array.from(document.querySelectorAll("#grid button")).map(b=>Number(b.dataset.level))}));
    await page.locator("#audio").evaluate(async a=>{await a.play();await new Promise(resolve=>{a.addEventListener("seeked",resolve,{once:true});a.currentTime=2;});});
    await page.waitForFunction(()=>document.getElementById("counter").textContent.startsWith("LISTEN"));
    await page.locator("#audio").evaluate(a=>a.pause());
    await page.waitForFunction(()=>!document.getElementById("counter").textContent.startsWith("LISTEN"));
    assert.deepEqual(await page.evaluate(()=>({pixels:Array.from(document.getElementById("screen").getContext("2d").getImageData(0,0,128,64).data).filter((_,i)=>i%4===0),grid:Array.from(document.querySelectorAll("#grid button")).map(b=>Number(b.dataset.level))})),nativeBefore,"Pause restores the exact previous native screen and all128LEDs");
    await page.locator("#audio").evaluate(a=>new Promise(resolve=>{a.addEventListener("seeked",resolve,{once:true});a.currentTime=3;}));
    await page.waitForFunction(()=>document.getElementById("counter").textContent.startsWith("LISTEN"));
    current=await page.locator("#audio").evaluate(a=>a.currentTime);
    const frame=lessonAudio.timeline.filter(f=>f.time<=current).at(-1)||lessonAudio.timeline[0];
    await frameCheck(frame.output);
    assert(await page.locator("#audio").evaluate(a=>Number.isFinite(a.duration)&&a.duration>10));
    report.checks.push("Real web audio decoding, seek/pause and captured playhead sync");
  }
  assert.deepEqual(errors,[],"No browser runtime errors");
  report.passed=true;
 }finally{
  await browser.close();
  fs.writeFileSync(path.join(root,"manual/evidence/browser-report.json"),JSON.stringify(report,null,2)+"\n");
 }
 console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exitCode=1;});
