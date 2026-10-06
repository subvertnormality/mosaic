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
  page.on("pageerror",e=>errors.push(e.message));
  await page.goto((process.env.MOSAIC_MANUAL_URL||"http://localhost:8765/manual/")+"#masks");
  await page.waitForFunction(()=>!document.body.classList.contains("book-loading")&&document.getElementById("scene").options.length>0);
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
  await page.selectOption("#scene","0");
  await page.locator(".encoder[data-n='3']").click();
  assert.equal(await page.locator("#counter").textContent(),"02 / "+String(data.scenes[0].steps.length).padStart(2,"0"),"A single captured turn advances; an encoder alone cannot complete the following hold and turn");
  await page.locator(".encoder[data-n='3']").focus();
  await page.keyboard.press("ArrowRight");
  assert.equal(await page.locator("#counter").textContent(),"02 / "+String(data.scenes[0].steps.length).padStart(2,"0"),"A single captured turn advances; an encoder alone cannot complete the following hold and turn");
  report.checks.push("Single encoder turn participates; following compound gesture rejects encoder without hold");
  await page.selectOption("#scene","0");
  const knob=await page.locator(".encoder[data-n='3']").boundingBox();
  await page.mouse.move(knob.x+knob.width/2,knob.y+knob.height/2);
  await page.mouse.down();await page.mouse.move(knob.x+knob.width/2+25,knob.y+knob.height/2);await page.mouse.up();
  await frameCheck(data.scenes[0].steps[1].output);
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
    await page.click("#next");await frameCheck(data.scenes[si].steps[target].output);
  }
  await page.locator("#grid button").first().focus();await page.keyboard.press("ArrowRight");
  assert.equal(await page.locator("#grid button").nth(1).evaluate(n=>document.activeElement===n),true);
  await page.selectOption("#scene","0");await page.click("#autoplay");
  await page.waitForFunction(()=>document.getElementById("counter").textContent.startsWith("02"));
  await page.click("#autoplay");await frameCheck(data.scenes[0].steps[1].output);
  report.checks.push("Pictured controls preserve current frame; explicit Next, grid focus and autoplay");

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
    await page.locator("#audio").evaluate(async a=>{await a.play();a.currentTime=2;});
    await page.waitForFunction(()=>document.getElementById("counter").textContent.startsWith("LISTEN"));
    await page.locator("#audio").evaluate(a=>a.pause());
    const current=await page.locator("#audio").evaluate(a=>a.currentTime);
    const frame=data.audio.timeline.filter(f=>f.time<=current).at(-1)||data.audio.timeline[0];
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
