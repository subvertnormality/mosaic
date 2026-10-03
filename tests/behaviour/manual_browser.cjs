/* Manual renderer acceptance; characterisation outside README.
 * Run with NODE_PATH pointing to an isolated Playwright install.
 * No emulator is launched or left running by these browser checks.
 */
const {chromium}=require("playwright");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"../..");
(async()=>{
 const data=JSON.parse(fs.readFileSync(path.join(root,"manual/generated/pilot.json")));
 const browser=await chromium.launch({headless:true,args:["--no-sandbox"]});
 const report={schema_version:1,passed:false,viewports:[],checks:[]}, errors=[];
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  page.on("pageerror",e=>errors.push(e.message));
  await page.goto((process.env.MOSAIC_MANUAL_URL||"http://localhost:8765/manual/")+"#masks");
  await page.waitForFunction(()=>document.getElementById("scene").options.length>0);
  assert.equal(await page.locator("h1").textContent(),"Masks.");
  async function frameCheck(output){
    const actual=await page.evaluate(()=>({pixels:Array.from(document.getElementById("screen").getContext("2d").getImageData(0,0,128,64).data).filter((_,i)=>i%4===0),grid:Array.from(document.querySelectorAll("#grid button")).map(b=>Number(b.dataset.level))}));
    const expected=output.screen_rle.flatMap(([value,count])=>Array(count).fill(value*17));
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
  assert.equal(await page.locator("#counter").textContent(),"02 / "+String(data.scenes[0].steps.length).padStart(2,"0"));
  await page.click("#previous");
  await page.locator(".encoder[data-n='3']").focus();
  await page.keyboard.press("ArrowRight");
  assert.equal(await page.locator("#counter").textContent(),"02 / "+String(data.scenes[0].steps.length).padStart(2,"0"));
  report.checks.push("Clickable and keyboard encoder advances");
  await page.click("#previous");
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
    await frameCheck(data.scenes[si].steps[target].output);
  }
  await page.locator("#grid button").first().focus();await page.keyboard.press("ArrowRight");
  assert.equal(await page.locator("#grid button").nth(1).evaluate(n=>document.activeElement===n),true);
  await page.selectOption("#scene","0");await page.click("#autoplay");
  await page.waitForFunction(()=>document.getElementById("counter").textContent.startsWith("02"));
  await page.click("#autoplay");await frameCheck(data.scenes[0].steps[1].output);
  report.checks.push("Encoder drag, norns keys, grid pads, grid focus and autoplay");

  await page.fill("#search","clear");
  await page.waitForFunction(()=>document.querySelectorAll("#search-results a").length>0);
  assert.match(await page.locator("#search-results").textContent(),/Controls|inherit|Masks/i);
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
    const expectedDuration=data.audio.bars*4*60/data.audio.bpm+2;
    for(const duration of durations)assert(Math.abs(duration-expectedDuration)<.06,"Every encoded format must decode the full captured clip");
    report.checks.push("Both Opus and MP3 decode to the exact four-bar phrase plus tail");
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
