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
