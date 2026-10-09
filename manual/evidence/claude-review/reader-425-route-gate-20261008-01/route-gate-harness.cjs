/* External browser-only, exact source-to-reader route gate. No playback, native app, or captures. */
"use strict";
const {chromium}=require("playwright");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const crypto=require("node:crypto");
const base=(process.env.MOSAIC_MANUAL_URL||"http://localhost:8785/manual/").replace(/\/$/,"/");
const outDir=process.env.MOSAIC_ROUTE_GATE_DIR||path.dirname(process.env.MOSAIC_ROUTE_MANIFEST||"");
const manifestPath=process.env.MOSAIC_ROUTE_MANIFEST||path.join(outDir,"unit-route-manifest.json");
const sourceRoot=process.env.MOSAIC_SOURCE_ROOT||"/home/andy/mosaic-manual-1.4.0";
const manifest=JSON.parse(fs.readFileSync(manifestPath,"utf8"));
const sha=b=>crypto.createHash("sha256").update(b).digest("hex");
function stable(v){if(Array.isArray(v))return v.map(stable);if(v&&typeof v==="object"){const o={};for(const k of Object.keys(v).sort())o[k]=stable(v[k]);return o;}return v;}
const stableSha=v=>sha(Buffer.from(JSON.stringify(stable(v)),"utf8"));
function markdownVisible(s){return String(s||"").replace(/!\[([^\]]*)\]\([^)]+\)/g,"$1").replace(/<img\b[^>]*\balt="([^"]*)"[^>]*>/gi,"$1").replace(/\[([^\]]+)\]\(([^)]+)\)/g,"$1").replace(/\x60([^\x60]+)\x60/g,"$1").replace(/\*\*(.*?)\*\*/g,"$1").replace(/\*(.*?)\*/g,"$1").replace(/\s+/g," ").trim();}
function stepFor(book,row){const scene=book.scenes[row.scene_id];assert(scene,"mapped source scene exists");const step=scene.steps.find(s=>s.id===row.from_step_id);assert(step,"mapped source frame exists");return {scene,step};}
function projectionFor(book,index,row){
 if(row.unit_type==="course"){const [chapter,stage]=row.route.slice(1).split("/lesson/");const c=book.learning_path.find(x=>x.id===chapter);assert(c,"course chapter exists");return c.stages.find(x=>x.id===stage);}
 if(row.unit_type==="lesson"){const fid=row.route.slice(1).split("/lesson/")[0];return index.teaching_contracts["feature:"+fid+":"+row.contract_id];}
 if(row.unit_type==="scene"){const feature=book.features.find(x=>x.id===row.selected_owner);return {scene:book.scenes[row.scene_id],selected_owner:row.selected_owner,scene_refs:feature.scene_refs};}
 if(row.unit_type==="recipe"){const fid=row.route.slice(1).split("/recipe/")[0],feature=book.features.find(x=>x.id===fid);return feature.recipes[row.recipe_index-1];}
 if(row.unit_type==="recording")return book.recordings_context.recordings[row.recording_id];
 throw Error("Unknown unit type "+row.unit_type);
}
async function main(){
 const report={schema:"reader-425-current-route-browser-v1",passed:false,base,ledger_sha256:manifest.ledger_sha256,book_sha256:manifest.book_sha256,index_sha256:manifest.index_sha256,authority_sha256:manifest.authority_sha256,rows:manifest.routes.length,unit_family_counts:{},source_file_count:Object.keys(manifest.source_files||{}).length,runtime_assets:{},scene_inventory:null,route_results:[],chunk_checks:[],browser_errors:[],http_errors:[],audio_play_attempts:0};
 let browser;
 try{
  assert.equal(manifest.schema,"reader-425-source-route-manifest-v4-js-canonical");
  assert.equal(manifest.routes.length,425);
  assert.equal(new Set(manifest.routes.map(r=>r.ledger_id)).size,425);
  assert.equal(new Set(manifest.routes.map(r=>r.route)).size,425);
  for(const r of manifest.routes){report.unit_family_counts[r.unit_type]=(report.unit_family_counts[r.unit_type]||0)+1;const p=path.join(sourceRoot,r.source_file);assert(fs.existsSync(p),"authoring source exists: "+r.ledger_id+" => "+r.source_file);assert.equal(sha(fs.readFileSync(p)),r.source_file_sha256,"current authoring source SHA: "+r.ledger_id);}
  browser=await chromium.launch({args:["--no-sandbox"]});
  const page=await browser.newPage({viewport:{width:1365,height:900}});
  page.setDefaultTimeout(10000);
  page.on("pageerror",e=>report.browser_errors.push(String(e.message||e)));
  page.on("requestfailed",r=>{const failure=r.failure()?.errorText||"failed";if(r.url().startsWith(base)&&failure!=="net::ERR_ABORTED")report.http_errors.push({url:r.url(),failure});});
  page.on("response",r=>{if(r.status()>=400&&r.url().startsWith(base))report.http_errors.push({url:r.url(),status:r.status()});});
  const br=await page.request.get(base+"generated/book.json");assert(br.ok(),"book.json HTTP response");
  const bookBytes=await br.body();assert.equal(sha(bookBytes),manifest.book_sha256,"served book pin");const book=JSON.parse(bookBytes.toString("utf8"));
  const ir=await page.request.get(base+"generated/reader-index.json");assert(ir.ok(),"reader-index.json HTTP response");
  const indexBytes=await ir.body();assert.equal(sha(indexBytes),manifest.index_sha256,"served reader index pin");const index=JSON.parse(indexBytes.toString("utf8"));
  const runtimeAssetHashes={};for(const [name,expected] of Object.entries(manifest.runtime_assets||{})){const sourcePath=path.join(sourceRoot,"manual",name);assert.equal(sha(fs.readFileSync(sourcePath)),expected,"authoritative runtime source pin "+name);const response=await page.request.get(base+"/"+name);assert(response.ok(),"runtime asset HTTP "+name);const bytes=await response.body();assert.equal(sha(bytes),expected,"served runtime asset pin "+name);runtimeAssetHashes[name]=sha(bytes);}report.runtime_assets=runtimeAssetHashes;
  await page.goto(base+"#home");await page.waitForFunction(()=>document.body.dataset.routeReady==="1"&&!document.body.classList.contains("book-loading"));
  const chunks=new Map();
  async function checkChunk(sceneId){if(chunks.has(sceneId))return;const ref=index.scene_chunks[sceneId];assert(ref,"current reader index has qualified scene chunk "+sceneId);const u=new URL(ref.path,new URL("generated/reader-index.json",base)).href;const res=await page.request.get(u);assert(res.ok(),"scene chunk HTTP "+res.status()+" "+sceneId);const bytes=await res.body();assert.equal(sha(bytes),ref.sha256,"qualified scene chunk SHA "+sceneId);chunks.set(sceneId,ref.sha256);report.chunk_checks.push({scene_id:sceneId,path:ref.path,sha256:ref.sha256});}
  async function armCycle(){await page.evaluate(()=>{const b=document.body;let saw0=b.dataset.routeReady==="0",done;window.__reader425Cycle=new Promise(resolve=>done=resolve);const obs=new MutationObserver(()=>{if(b.dataset.routeReady==="0")saw0=true;if(saw0&&b.dataset.routeReady==="1"){obs.disconnect();done(true);}});obs.observe(b,{attributes:true,attributeFilter:["data-route-ready"]});});}
  async function waitFinalRoute(finalHash){await page.waitForFunction(h=>document.body.dataset.routeReady==="1"&&!document.body.classList.contains("book-loading")&&location.hash===h,finalHash);}
  async function route(requestedHash,finalHash=requestedHash){
   const current=await page.evaluate(()=>location.hash);
   if(current===requestedHash){await page.goto(base+requestedHash);await waitFinalRoute(finalHash);return;}
   await armCycle();await page.evaluate(h=>location.hash=h,requestedHash);
   await page.evaluate(()=>Promise.race([window.__reader425Cycle,new Promise((_,reject)=>setTimeout(()=>reject(new Error("fresh route-ready 0->1 cycle timeout")),10000))]));
   await waitFinalRoute(finalHash);
  }
  async function clickRecipeEntry(row){
   await route("#cookbook");
   const link=page.locator("#book-home a[href="+JSON.stringify(row.route)+"]");
   assert.equal(await link.count(),1,"visible cookbook entry for requested recipe route "+row.ledger_id);
   assert.equal(await link.isVisible(),true,"cookbook recipe entry is perceivable "+row.ledger_id);
   assert.equal((await link.innerText()).trim(),row.source_title,"exact authored cookbook entry title "+row.ledger_id);
   const sourceFeature=book.features.find(f=>f.id===row.route.slice(1).split("/recipe/")[0]);
   assert((await link.locator("..").innerText()).includes(sourceFeature.title),"cookbook entry identifies its authored feature context "+row.ledger_id);
   await armCycle();await link.click();
   await page.evaluate(()=>Promise.race([window.__reader425Cycle,new Promise((_,reject)=>setTimeout(()=>reject(new Error("visible cookbook click route-ready cycle timeout")),10000))]));
   await waitFinalRoute(row.expected_final_route||row.route);
  }
  async function frame(step,where){
   const {decodeScreenPixels}=require(path.join(sourceRoot,"tests/behaviour/manual_screen_oracle.cjs"));
   const actual=await page.evaluate(()=>({pixels:Array.from(document.querySelector("#screen").getContext("2d").getImageData(0,0,128,64).data).filter((_,i)=>i%4===0),grid:Array.from(document.querySelectorAll("#grid button")).map(b=>Number(b.dataset.level))}));
   assert.deepEqual(actual.pixels,decodeScreenPixels(step.output),"visible 128x64 captured frame "+where);
   assert.deepEqual(actual.grid,step.output.grid,"visible 128-cell grid "+where);
  }
  async function checkCaption(raw,where){
   const el=page.locator("#caption");assert.equal(await el.innerText(),markdownVisible(raw),"visible exact authored caption "+where);
   const expected=[...String(raw).matchAll(/\[([^\]]+)\]\(([^)]+)\)/g)].map(m=>({label:m[1],href:m[2]}));
   const actual=await el.locator("a").evaluateAll(as=>as.map(a=>({label:a.textContent,href:a.getAttribute("href")})));
   assert.deepEqual(actual,expected,"caption links preserve exact label and destination "+where);
  }
  for(const row of manifest.routes){
   const item={ledger_id:row.ledger_id,unit_type:row.unit_type,route:row.route,passed:false};
   try{
    const projection=projectionFor(book,index,row);assert(projection,"exact compiled source projection exists "+row.ledger_id);
    assert.equal(stableSha(projection),row.projection_sha256,"compiled projection exact SHA "+row.ledger_id);
    let contract=null;
    if(row.unit_type==="course"||row.unit_type==="lesson"){
     const sourceContract=row.unit_type==="course"?index.teaching_contracts[row.contract_id]:projection;
     assert(sourceContract,"current teaching contract exists "+row.ledger_id);
     assert.equal(sourceContract.scene_id,row.scene_id);assert.equal(sourceContract.from_step_id,row.from_step_id);assert.equal(sourceContract.to_step_id,row.target_step_id);
     assert.equal(stableSha(sourceContract),row.contract_projection_sha256,"exact action/checkpoint binding "+row.ledger_id);
     if(row.unit_type==="lesson"){
      const finalFeature=(row.expected_final_route||row.route).slice(1).split("/")[0];
      contract=index.teaching_contracts["feature:"+finalFeature+":"+row.contract_id];assert(contract,"canonical lesson target contract exists "+row.ledger_id);
      for(const key of ["scene_id","from_step_id","to_step_id"])assert.equal(contract[key],sourceContract[key],"lesson context preserves the exact mapped target "+row.ledger_id+" "+key);
      assert.deepEqual(sourceContract.actions,row.expected_context_actions,"requested lesson owner preserves its exact complete authored action wording "+row.ledger_id);
      assert.deepEqual(contract.actions,row.expected_canonical_actions,"canonical lesson owner preserves its exact complete authored action wording "+row.ledger_id);
      const gestureIdentity=actions=>actions.map(({id,kind,target_step_id})=>({id,kind,target_step_id}));
      assert.deepEqual(gestureIdentity(sourceContract.actions),gestureIdentity(contract.actions),"context redirect preserves every action identity, gesture type, order, and target "+row.ledger_id);
     }else contract=sourceContract;
    }
    if(row.scene_id)await checkChunk(row.scene_id);
    const {scene,step}=row.scene_id?stepFor(book,row):{scene:null,step:null};
    if(row.unit_type==="recipe")await clickRecipeEntry(row);
    else await route(row.route,row.expected_final_route||row.route);
    item.final_route=row.expected_final_route||row.route;
    if(row.unit_type==="course"||row.unit_type==="lesson"||row.unit_type==="scene"){
     assert.equal(await page.locator("#feature-title").innerText(),row.expected_visible_owner_title||row.visible_owner_title,"visible public owner title "+row.ledger_id);
     const selectedScene=await page.locator("#scene").evaluate(e=>({value:e.value,label:e.selectedOptions?.[0]?.textContent?.trim()}));
     assert.equal(selectedScene.label,scene.title,"exact authored scene label selected "+row.ledger_id);
     assert.equal(Number.isInteger(Number(selectedScene.value)),true,"scene selector exposes its selected authored option "+row.ledger_id);
     if(row.expected_final_route&&row.expected_final_route!==row.route)assert.equal(await page.evaluate(()=>location.hash),row.expected_final_route,"authored context route resolves to its exact canonical target "+row.ledger_id);
     assert.equal(await page.locator("#step-title").innerText(),step.title||scene.title,"exact selected frame title derived by the installed renderer "+row.ledger_id);
     await checkCaption(step.caption,row.ledger_id);
     await frame(step,row.ledger_id);
     if(row.unit_type!=="scene"){
      const lessonWorkspace=page.locator("#lesson-workspace");assert.equal(await lessonWorkspace.isVisible(),true,"full canonical lesson workspace is visible "+row.ledger_id);
      const panel=page.locator("#teaching-actions");assert.equal(await panel.isVisible(),true,"lesson action panel is visible "+row.ledger_id);
      const summary=panel.locator("summary");assert.equal(await summary.count(),1);if(!(await summary.evaluate(e=>e.parentElement.open)))await summary.click();
      const actions=contract.actions,buttons=panel.locator("button[data-action-kind]");
      assert.equal(await buttons.count(),actions.length,"all authored walkthrough actions visible "+row.ledger_id);
      const actual=await buttons.evaluateAll(bs=>bs.map(b=>({kind:b.dataset.actionKind,text:b.innerText.trim()})));
      assert.deepEqual(actual.map(a=>a.kind),actions.map(a=>a.kind),"teaching gesture kinds/order "+row.ledger_id);
      for(let i=0;i<actions.length;i++)assert(actual[i].text.startsWith(actions[i].label),"visible authored gesture label "+row.ledger_id+" action "+actions[i].id);
     }
    } else if(row.unit_type==="recipe"){
     const workspace=page.locator("#recipe-workspace");assert.equal(await workspace.isVisible(),true,"visible canonical recipe workspace "+row.ledger_id);
     const finalParts=(row.expected_final_route||row.route).slice(1).split("/recipe/");
     const finalFeatureId=finalParts[0],finalIndex=Number(finalParts[1]);
     assert.equal(await workspace.evaluate(e=>e.dataset.featureId),finalFeatureId,"requested recipe entry resolves to exact canonical feature "+row.ledger_id);
     assert.equal(Number(await workspace.evaluate(e=>e.dataset.recipeIndex)),finalIndex,"requested recipe entry resolves to exact canonical recipe index "+row.ledger_id);
     assert.equal(await workspace.locator("h1").innerText(),row.source_title,"exact canonical recipe title "+row.ledger_id);
     const body=workspace.locator(".recipe-body");assert.equal(await body.isVisible(),true);
     for(const detail of await body.locator("details").all())if(!(await detail.evaluate(e=>e.open)))await detail.locator("summary").click();
     const finalRecipe=book.features.find(f=>f.id===finalFeatureId).recipes[finalIndex-1];
     assert.equal(finalRecipe.title,row.source_title,"canonical walkthrough title matches source unit "+row.ledger_id);
     const expectedRaw=finalRecipe.text.replace(/Complete canonical walkthrough:/gi,"Full walkthrough:");
     const expectedItems=expectedRaw.split(/\r?\n/).filter(line=>/^\s*\d+\.\s+/.test(line)).map(line=>markdownVisible(line.replace(/^\s*\d+\.\s+/,"")));
     const actualItems=await body.locator("ol li").evaluateAll(xs=>xs.map(x=>x.innerText.replace(/\s+/g," ").trim()));
     assert.deepEqual(actualItems,expectedItems,"visible recipe actions preserve every authored item and order; only generated list numerals are omitted "+row.ledger_id);
     const expectedUnordered=expectedRaw.split(/\r?\n/).filter(line=>/^\s*[-*+]\s+/.test(line)).map(line=>markdownVisible(line.replace(/^\s*[-*+]\s+/,"")));
     const actualUnordered=await body.locator("ul li").evaluateAll(xs=>xs.map(x=>x.innerText.replace(/\s+/g," ").trim()));
     assert.deepEqual(actualUnordered,expectedUnordered,"visible unordered recipe actions preserve every authored item and order "+row.ledger_id);
     const expectedImageAlts=[...expectedRaw.matchAll(/!\[([^\]]*)\]\([^)]+\)/g)].map(m=>m[1]).concat([...expectedRaw.matchAll(/<img\b[^>]*\balt=\"([^\"]*)\"[^>]*>/gi)].map(m=>m[1]));
     const actualImageAlts=await body.locator("img").evaluateAll(xs=>xs.map(x=>x.alt));
     assert.deepEqual(actualImageAlts,expectedImageAlts,"visible recipe illustrations preserve every authored alt label and order "+row.ledger_id);
     const expectedProseBlocks=[];let paragraph=[],insideList=false;
     const flushParagraph=()=>{const value=markdownVisible(paragraph.map(line=>line.replace(/!\[[^\]]*\]\([^)]+\)/g,"").replace(/<img\b[^>]*>/gi,"")).join(" ")).replace(/\s+/g," ").trim();if(value)expectedProseBlocks.push(value);paragraph=[];};
     for(const line of expectedRaw.split(/\r?\n/)){
      if(!line.trim()){flushParagraph();insideList=false;continue;}
      if(/^\s*(?:[-*+] |\d+\. )/.test(line)){flushParagraph();insideList=true;continue;}
      if(insideList&&/^\s{2,}\S/.test(line))continue;
      insideList=false;
      if(/^#{1,6}\s+/.test(line)){flushParagraph();expectedProseBlocks.push(markdownVisible(line.replace(/^#{1,6}\s+/,"")));continue;}
      paragraph.push(line);
     }
     flushParagraph();
     const actualProseBlocks=await body.evaluate(el=>Array.from(el.children).filter(n=>!["OL","UL","IMG"].includes(n.tagName)).map(n=>n.innerText.replace(/\s+/g," ").trim()).filter(Boolean));
     assert(expectedProseBlocks.join(" ").length>24,"recipe has meaningful source-pinned non-list prose "+row.ledger_id);
     assert.deepEqual(actualProseBlocks,expectedProseBlocks,"visible recipe prose preserves each authored block and word; list items and illustrations are checked separately "+row.ledger_id);
    } else if(row.unit_type==="recording"){
     const workspace=page.locator("#recording-workspace");assert.equal(await workspace.isVisible(),true,"visible canonical recording workspace "+row.ledger_id);
     assert.equal(await workspace.evaluate(e=>e.dataset.recordingId),row.recording_id);
     assert.equal(await workspace.locator("h1").innerText(),row.source_title,"exact recording context title "+row.ledger_id);
     const text=(await workspace.innerText()).replace(/\s+/g," ");
     assert(typeof row.expected_purpose==="string"&&row.expected_purpose.length>0,"source-pinned recording purpose exists "+row.ledger_id);
     assert(text.includes(row.expected_purpose),"visible authored recording purpose "+row.ledger_id);
     assert(text.includes(row.expected_visible_text),"visible exact recording starting point "+row.ledger_id);
     const recordingLists=workspace.locator(".recording-instructions .recording-steps ol");assert.equal(await recordingLists.count(),2,"separate authored build and restore lists are visible "+row.ledger_id);
     const actualBuild=await recordingLists.nth(0).locator("li").evaluateAll(xs=>xs.map(x=>x.innerText.replace(/\s+/g," ").trim()));
     const expandAuthoredSteps=items=>{const out=[];for(const item of items){let current="";for(const line of String(item).split(/\r?\n/)){const numbered=line.match(/^\s*\d+\.\s+(.+)$/);if(numbered){if(current)out.push(markdownVisible(current));current=numbered[1];}else if(current&&/^\s{2,}\S/.test(line))current+=" "+line.trim();else if(line.trim()){if(current)out.push(markdownVisible(current));current=line.trim();}}if(current)out.push(markdownVisible(current));}return out;};
     const expectedBuild=expandAuthoredSteps(row.expected_build_steps||[]);
     assert(expectedBuild.length>0,"recording build steps are source-pinned "+row.ledger_id);
     assert.deepEqual(actualBuild,expectedBuild,"visible ordered recording build steps preserve every exact authored action "+row.ledger_id);
     const actualRestore=await recordingLists.nth(1).locator("li").evaluateAll(xs=>xs.map(x=>x.innerText.replace(/\s+/g," ").trim()));
     const expectedRestore=expandAuthoredSteps(row.expected_restore_steps||[]);
     assert(expectedRestore.length>0,"recording restore steps are source-pinned "+row.ledger_id);
     assert.deepEqual(actualRestore,expectedRestore,"visible ordered recording restoration steps preserve every exact authored action "+row.ledger_id);
     const audio=page.locator("#audio");assert.equal(await audio.count(),1,"recording player is present "+row.ledger_id);
     assert.equal(await audio.evaluate(a=>a.paused),true,"recording remains paused; harness never starts audio "+row.ledger_id);
    } else throw Error("Unexpected unit family "+row.unit_type);
    item.passed=true;report.route_results.push(item);
   }catch(e){item.error=String(e.stack||e);report.route_results.push(item);}
  }
  const allSceneIds=[...new Set(manifest.routes.map(r=>r.scene_id).filter(Boolean))].sort();const sceneUnitIds=new Set(manifest.routes.filter(r=>r.unit_type==="scene").map(r=>r.scene_id));const courseOnlySceneIds=allSceneIds.filter(id=>!sceneUnitIds.has(id));report.scene_inventory={unique_scene_ids:allSceneIds.length,verified_scene_chunks:chunks.size,course_only_scene_ids:courseOnlySceneIds};assert.equal(allSceneIds.length,146,"ledger route manifest covers all 146 scenes, including course-only scenes");assert.equal(courseOnlySceneIds.length,10,"exact ten course-only scene IDs remain separately covered");assert.equal(chunks.size,146,"all 146 current source-pinned scene chunks were fetched and verified");
  report.passed=report.route_results.length===425&&report.route_results.every(x=>x.passed)&&report.browser_errors.length===0&&report.http_errors.length===0&&chunks.size===146;
 }catch(e){report.fatal=String(e.stack||e);}
 finally{if(browser)await browser.close();report.finished_utc=new Date().toISOString();report.passed=report.passed===true;const out=path.join(outDir,"browser-route-report.json");fs.writeFileSync(out,JSON.stringify(report,null,2)+"\n");console.log(JSON.stringify({passed:report.passed,rows:report.route_results.length,route_failures:report.route_results.filter(x=>!x.passed).length,chunk_checks:report.chunk_checks.length,browser_errors:report.browser_errors.length,http_errors:report.http_errors.length,fatal:report.fatal||null,report_path:out}));}
}
main().catch(e=>{console.error(e);process.exitCode=1;});

