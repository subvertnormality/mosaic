// Reader-visible receipt mutation regression outside README. Native screen/grid and public cues remain the oracle.
const {chromium}=require("playwright"),fs=require("fs"),assert=require("assert/strict"),crypto=require("crypto");
const {decodeScreenPixels}=require("../manual_screen_oracle.cjs");
(async()=>{const base=process.env.MOSAIC_MANUAL_URL||"http://127.0.0.1:8765/manual/",browser=await chromium.launch({args:["--no-sandbox"]}),r={passed:false,characterisation:"Receipt tampering must not expose technical evidence chrome or alter the recorded reader state",sources:{},checks:[]};try{
 const p=await browser.newPage(),idx=await p.request.get(base+"generated/reader-index.json").then(x=>x.json()),book=await p.request.get(base+"generated/book.json").then(x=>x.json());
 for(const n of ["book.js","manual.js","manual.css","index.html"])r.sources[n]=crypto.createHash("sha256").update(await p.request.get(base+n).then(x=>x.body())).digest("hex");
 const feature=idx.features.find(f=>f.id==="masks"),binding=feature.teaching_bindings.find(b=>b.lesson_id==="note-default-g3"),contract=idx.teaching_contracts["feature:masks:note-default-g3"],scene=book.scenes[contract.scene_id],step=scene.steps.find(x=>x.id===contract.from_step_id),stepIndex=scene.steps.findIndex(x=>x.id===contract.from_step_id),milestone=feature.scene_milestones.find(x=>x.scene_id===scene.id).groups.find(g=>g.step_ids.includes(step.id)),expectedCounter=milestone.label+" \u00b7 "+(milestone.step_ids.indexOf(step.id)+1)+"/"+milestone.step_ids.length;
 assert(binding.mask_readout_receipts?.length,"The published Masks lesson contains its supplementary native receipt");
 const noTechnicalChrome=async label=>{
  for(const selector of ["#evidence-status","#evidence-metadata","#midi-history",".native-receipt",".evidence-digest"])assert.equal(await p.locator(selector).count(),0,label+": technical evidence chrome is absent ("+selector+")");
  const bodyText=await p.locator("body").innerText();
  const receipt=binding.mask_readout_receipts[0];
  assert(!bodyText.includes(receipt.frame_sha256),label+": raw receipt digest is not shown to the reader");
  assert(!bodyText.includes(receipt.session_id),label+": capture session id is not shown to the reader");
 };
 await p.goto(base+"?receipt=original#masks/lesson/note-default-g3");
 await p.waitForFunction(counter=>document.body.dataset.routeReady==="1"&&document.getElementById("counter")?.textContent.startsWith(counter),expectedCounter);
 await noTechnicalChrome("original");
 assert.equal(await p.locator("#lesson-workspace").isVisible(),true,"Original route keeps the exact feature lesson available");
 const details=p.locator("#teaching-actions details");assert.equal(await details.count(),1,"Public recorded controls remain available");
 if(!await details.evaluate(n=>n.open))await details.locator("summary").click();
 const cue=p.locator("#teaching-actions button[data-action-kind]").first();
 assert.equal(await cue.getAttribute("aria-current"),"step","First authored public action is current");
 assert.equal(await cue.getAttribute("data-action-kind"),contract.actions[0].kind,"Current public action kind is preserved");
 assert((await cue.innerText()).trim().length>0,"Public action has a human-readable cue");
 assert((await p.locator("#step-title").innerText()).trim().length>0,"Public step title remains visible");
 assert.equal(await p.locator("#caption").innerText(),step.caption,"Exact authored caption remains visible");
 assert((await p.locator("#counter").innerText()).startsWith(expectedCounter),"Exact authored current counter position");
 const original={title:await p.locator("#step-title").innerText(),caption:await p.locator("#caption").innerText(),counter:await p.locator("#counter").innerText(),action_kind:await cue.getAttribute("data-action-kind"),action_label:(await cue.innerText()).trim(),pixels:await p.locator("#screen").evaluate(c=>Array.from(c.getContext("2d").getImageData(0,0,128,64).data).filter((_,i)=>i%4===0)),grid:await p.locator("#grid button").evaluateAll(bs=>bs.map(b=>Number(b.dataset.level)))};
 assert.deepEqual(original.pixels,decodeScreenPixels(step.output),"Exact native framebuffer");
 assert.deepEqual(original.grid,step.output.grid,"All 128 native grid levels");
 r.checks.push({case:"original receipt",passed:true,reader_state:original});
 for(const mode of ["mismatched-hash","forged-hash","foreign-scene"]){
  const clone=JSON.parse(JSON.stringify(idx)),f=clone.features.find(x=>x.id==="masks"),b=f.teaching_bindings.find(x=>x.lesson_id==="note-default-g3"),c=clone.teaching_contracts["feature:masks:note-default-g3"];
  if(mode==="mismatched-hash")b.mask_readout_receipts[0].frame_sha256="0".repeat(64);
  else if(mode==="forged-hash"){b.mask_readout_receipts[0].frame_sha256="0".repeat(64);c.mask_readout_receipts[0].frame_sha256="0".repeat(64);}
  else {b.mask_readout_receipts[0].scene="foreign-scene";if(c.mask_readout_receipts?.length)c.mask_readout_receipts[0].scene="foreign-scene";}
  await p.route("**/generated/reader-index.json",route=>route.fulfill({contentType:"application/json",body:JSON.stringify(clone)}));
  await p.goto(base+"?receipt="+mode+"#masks/lesson/note-default-g3");
  await p.waitForFunction(()=>document.body.dataset.routeReady==="1");
  await noTechnicalChrome(mode);
  assert.equal(await p.locator("#guide-loading").isVisible(),true,mode+": invalid receipt produces a plain reader-facing unavailable message");
  assert.equal(await p.locator("#guide-loading").innerText(),"This page could not be opened. Return to the manual home and try again.",mode+": generic recovery message contains no diagnostic receipt detail");
  assert.equal(await p.locator("#lesson-workspace").isVisible(),false,mode+": invalid receipt cannot expose an unverified lesson");
  r.checks.push({case:mode,passed:true,public_error:"This page could not be opened. Return to the manual home and try again."});
  await p.unroute("**/generated/reader-index.json");
 }
 r.passed=true;
}finally{await browser.close();fs.writeFileSync(process.argv[2],JSON.stringify(r,null,2)+"\n");}
console.log(JSON.stringify(r));})().catch(e=>{console.error(e);process.exit(1)});