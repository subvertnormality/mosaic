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
  assert(!/Step by step|pattern on pattern|find hidden fragments/i.test(await page.locator(".sidebar-bottom").innerText()),"Reader startup must not restore the removed tagline");
  assert.equal(await page.locator(".sidebar-bottom a").count(),3,"Sidebar keeps its useful reference links");
  assert.equal(await page.locator("h1").textContent(),"Masks");
  // Characterisation outside README: the pictured norns controls can use either supported physical layout.
  const layout=page.locator("#norns-layout");
  assert.equal(await layout.count(),1,"One accessible hardware-layout toggle is present");
  assert.equal(await layout.getAttribute("aria-pressed"),"false","Original norns layout is the default");
  assert.equal(await page.locator("body").getAttribute("data-norns-layout"),"original");
  assert.deepEqual(await page.locator("#screen").evaluate(n=>[n.width,n.height]),[128,64]);
  assert.equal(await page.locator("#grid button").count(),128,"The grid remains 128 unique pads");
  assert.deepEqual(await page.locator(".encoder").evaluateAll(nodes=>nodes.map(n=>n.dataset.n)),["1","2","3"],"Encoder identities/order remain unchanged");
  assert.deepEqual(await page.locator("[data-key]").evaluateAll(nodes=>nodes.map(n=>n.dataset.key)),["1","2","3"],"Key identities/order remain unchanged");
  const geometry=async()=>page.evaluate(()=>{
    const box=sel=>{const r=document.querySelector(sel).getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height};};
    return {screen:box("#screen"),e1:box('.encoder[data-n="1"]'),e2:box('.encoder[data-n="2"]'),e3:box('.encoder[data-n="3"]'),k1:box('[data-key="1"]'),k2:box('[data-key="2"]'),k3:box('[data-key="3"]')};
  });
  const assertOriginalGeometry=g=>{
    const k1c=(g.k1.left+g.k1.right)/2,e1c=(g.e1.left+g.e1.right)/2;
    assert(g.k1.bottom<=g.screen.top&&g.e1.bottom<=g.screen.top&&k1c>=g.screen.left&&k1c<=g.screen.right&&e1c>=g.screen.left&&e1c<=g.screen.right&&k1c<e1c,"Original K1/E1 sit above the screen, K1 before E1");
    assert(g.e2.left>=g.screen.right&&g.e3.left>=g.screen.right,"Original E2/E3 sit to the right of the screen");
    assert(g.k2.top>=Math.max(g.e2.bottom,g.e3.bottom)&&g.k3.top>=Math.max(g.e2.bottom,g.e3.bottom)&&g.k2.left>=g.screen.right&&g.k3.left>=g.screen.right,"Original K2/K3 sit right of the screen, below E2/E3");
  };
  const assertShieldGeometry=g=>{
    assert(g.k1.bottom<=g.screen.top&&g.e1.bottom<=g.screen.top&&g.k1.left>g.screen.left+g.screen.width/2&&g.e1.left>g.screen.left+g.screen.width/2&&g.k1.left<g.e1.left,"Shield K1/E1 sit above the screen on its right side, K1 before E1");
    assert(g.k2.top>=g.screen.bottom&&g.k3.top>=g.screen.bottom&&g.e2.top>=g.screen.bottom&&g.e3.top>=g.screen.bottom,"Shield K2/K3/E2/E3 sit below the screen");
    assert(g.k2.left<g.k3.left&&g.k3.left<g.e2.left&&g.e2.left<g.e3.left,"Shield bottom row is K2, K3, E2, E3 from left to right");
  };
  assertOriginalGeometry(await geometry());
  await layout.click();
  assert.equal(await layout.getAttribute("aria-pressed"),"true","Toggle selects Shield");
  assert.equal(await page.locator("body").getAttribute("data-norns-layout"),"shield");
  assert.equal(await page.evaluate(()=>localStorage.getItem("mosaic-norns-layout")),"shield","Selection persists under the published storage key");
  assertShieldGeometry(await geometry());
  await routeHash("#reference");await routeHash("#masks");
  assert.equal(await layout.getAttribute("aria-pressed"),"true","Layout survives hash navigation");
  await page.reload();
  await page.waitForFunction(()=>document.body.dataset.routeReady==="1"&&document.getElementById("norns-layout"));
  assert.equal(await layout.getAttribute("aria-pressed"),"true","Layout survives reload");
  assertShieldGeometry(await geometry());
  await page.evaluate(()=>localStorage.setItem("mosaic-norns-layout","not-a-supported-layout"));
  await page.reload();
  await page.waitForFunction(()=>document.body.dataset.routeReady==="1"&&document.getElementById("norns-layout"));
  assert.equal(await layout.getAttribute("aria-pressed"),"false","Invalid stored preference falls back to Original");
  assert.equal(await page.locator("body").getAttribute("data-norns-layout"),"original");
  assertOriginalGeometry(await geometry());
  report.checks.push("Original and Shield layouts preserve screen/canvas size, 128 pads and ordered controls; geometry is correct, preference survives navigation/reload, and invalid storage falls back");
  // Characterisation outside README: the interactive grid's enlarged setting remains a meaningful size increase at mobile through ultrawide layouts.
  for(const width of [390,1100,1440,1920,2560]){
   await page.setViewportSize({width,height:1100});
   const snapshot=()=>page.evaluate(()=>({cell:document.querySelector("#grid button").getBoundingClientRect().width,docWidth:document.documentElement.scrollWidth,grid:Array.from(document.querySelectorAll("#grid button")).map(b=>Number(b.dataset.level)),labels:Array.from(document.querySelectorAll("#grid button")).map(b=>b.getAttribute("aria-label"))}));
   const before=await snapshot(),summary=page.locator("#enlarged-grid-controls>summary");
   assert.equal(before.docWidth,width,"Standard interactive grid must not overflow the page at "+width+"px");
   await summary.focus();await page.keyboard.press("Enter");await page.waitForFunction(()=>document.querySelector("#enlarged-grid-controls")?.open===true);
   const enlarged=await snapshot();
   assert(enlarged.cell>=Math.max(44,before.cell*1.2),"Expanded grid must reach 44px and grow at least 20% at "+width+"px ("+before.cell+" -> "+enlarged.cell+")");
   assert.equal(enlarged.docWidth,width,"Grid pan must not become document overflow at "+width+"px");
   assert.deepEqual(enlarged.grid,before.grid,"Grid size change must preserve all 128 recorded LED levels");
   assert.deepEqual(enlarged.labels,before.labels,"Grid size change must preserve all 128 accessible pad labels");
   await summary.focus();await page.keyboard.press("Enter");await page.waitForFunction(()=>document.querySelector("#enlarged-grid-controls")?.open===false);
   const collapsed=await snapshot();assert.equal(collapsed.cell,before.cell,"Keyboard collapse restores standard grid size");assert.deepEqual(collapsed.grid,before.grid);
  }
  await page.setViewportSize({width:1440,height:1100});
  // Characterisation outside README: compact device/grid layout preserves full grid visibility on feature and lesson routes.
  for(const [route,width,split,minGrid] of [["#masks",1440,true,420],["#masks",1121,true,280],["#first-sound/lesson/first-sound-assign",1440,true,280],["#first-sound/lesson/first-sound-assign",1280,true,280],["#first-sound/lesson/first-sound-assign",1121,true,280]]){
   if(await page.evaluate(()=>location.hash)!==route)await routeHash(route);
   await page.setViewportSize({width,height:1100});
   const layout=await page.evaluate(()=>{const box=s=>{const r=document.querySelector(s).getBoundingClientRect();return{x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height}};const grid=document.querySelector("#grid");return{docWidth:document.documentElement.scrollWidth,norns:box(".norns-wrap"),screen:box("#screen"),player:box(".player"),instrument:box(".instruments"),wrap:box(".grid-wrap"),grid:box("#grid"),gridScrollWidth:grid.scrollWidth,gridClientWidth:grid.clientWidth,lastRight:grid.lastElementChild.getBoundingClientRect().right,count:grid.querySelectorAll("button").length}});
   assert.equal(layout.docWidth,width,"Device layout must not overflow the page at "+width+"px");
   assert.equal(layout.count,128,"Layout retains all 128 interactive pads");
   if(split){assert(layout.norns.right<=layout.wrap.x+1&&Math.max(0,Math.min(layout.norns.bottom,layout.wrap.bottom)-Math.max(layout.norns.y,layout.wrap.y))>=Math.min(layout.norns.height,layout.wrap.height)*.8,"Compact grid sits beside norns at "+width+"px");assert(layout.screen.width>=256,"Norns screen retains its 128px native canvas width");assert(layout.wrap.width>=minGrid,"Compact grid has room for all columns at "+width+"px");assert(layout.gridScrollWidth<=layout.gridClientWidth+1&&layout.lastRight<=layout.wrap.right+1&&layout.wrap.right<=layout.instrument.right+1&&layout.instrument.right<=layout.player.right+1&&layout.lastRight<=width+1,"All 16 compact grid columns are visible without horizontal pan");}
   else assert(layout.wrap.y>=layout.norns.bottom-1,"Narrow lesson layout stacks the grid below norns");
   if(route.includes("/lesson/")&&width===1440){const levels=await page.locator("#grid button").evaluateAll(ns=>ns.map(n=>n.dataset.level)),labels=await page.locator("#grid button").evaluateAll(ns=>ns.map(n=>n.getAttribute("aria-label"))),summary=page.locator("#enlarged-grid-controls>summary");await summary.focus();await page.keyboard.press("Enter");await page.waitForFunction(()=>document.querySelector("#enlarged-grid-controls")?.open===true);const enlarged=await page.evaluate(()=>{const box=s=>{const r=document.querySelector(s).getBoundingClientRect();return{x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width}};return{device:box(".norns-wrap"),player:box(".player"),instrument:box(".instruments"),wrap:box(".grid-wrap"),grid:box("#grid"),instrument:box(".instruments"),pad:document.querySelector("#grid button").getBoundingClientRect().width,docWidth:document.documentElement.scrollWidth}});assert(enlarged.wrap.y>=enlarged.device.bottom-1&&enlarged.wrap.width>=enlarged.instrument.width-60,"Enlarged lesson grid moves below the device and uses full player width");assert(enlarged.pad>=44&&enlarged.grid.width>layout.grid.width&&enlarged.docWidth===width,"Expanded lesson pads are larger without page overflow");assert.deepEqual(await page.locator("#grid button").evaluateAll(ns=>ns.map(n=>n.dataset.level)),levels,"Resize preserves all 128 LED levels");assert.deepEqual(await page.locator("#grid button").evaluateAll(ns=>ns.map(n=>n.getAttribute("aria-label"))),labels,"Resize preserves pad accessible labels");await summary.focus();await page.keyboard.press("Enter");await page.waitForFunction(()=>document.querySelector("#enlarged-grid-controls")?.open===false);}
  }
  if(await page.evaluate(()=>location.hash)!=="#masks")await routeHash("#masks");
  await page.setViewportSize({width:1440,height:1100});
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
  // Characterisation outside README: the actual captured Masks hold remains clickable in Shield layout.
  await page.locator("#norns-layout").click();
  assert.equal(await page.locator("body").getAttribute("data-norns-layout"),"shield");
  await routeHash("#masks/lesson/masks-hold");
  await page.waitForFunction(()=>document.body.dataset.routeReady==="1"&&document.getElementById("counter").textContent.startsWith("02"));
  if(!await page.locator("#enlarged-grid-controls").evaluate(n=>n.open))await page.locator("#enlarged-grid-controls>summary").click();
  await cframe("masks-open");
  const shieldHold=page.locator("#grid button").nth(3*16+12);
  await shieldHold.scrollIntoViewIfNeeded();
  const shieldBox=await shieldHold.boundingBox(),shieldPoint={x:shieldBox.x+shieldBox.width/2,y:shieldBox.y+shieldBox.height/2};
  const shieldHit=await page.evaluate(point=>{const expected=document.querySelectorAll("#grid button")[3*16+12],actual=document.elementFromPoint(point.x,point.y);return actual===expected||expected.contains(actual);},shieldPoint);
  assert.equal(shieldHit,true,"Pointer center is inside the visible native grid pad");
  await page.mouse.move(shieldPoint.x,shieldPoint.y);await page.mouse.down();
  assert.equal(await shieldHold.evaluate(b=>b.classList.contains("held")),true,"Matching pad highlights as held in Shield layout");
  const showHeldResult=page.locator("#lesson-workspace .workspace-checkpoints button").filter({hasText:"Show result"});await showHeldResult.focus();await page.keyboard.press("Enter");await cframe("masks-hold");
  await page.mouse.up();
  await page.locator("#norns-layout").click();
  assert.equal(await page.locator("body").getAttribute("data-norns-layout"),"original");
  report.checks.push("Captured Masks hold cue remains clickable and visibly held in Shield layout, then shows its exact recorded frame");
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
    const touchTargets=await page.locator('.encoder,[data-key],#norns-layout').evaluateAll(nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return {w:r.width,h:r.height,label:n.getAttribute('aria-label')||n.id};}));
    assert.equal(touchTargets.length,7,'Six controls plus the layout toggle remain visible');
    for(const target of touchTargets)assert(target.w>=44&&target.h>=44,'Mobile hardware control target is at least 44px: '+target.label);
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
