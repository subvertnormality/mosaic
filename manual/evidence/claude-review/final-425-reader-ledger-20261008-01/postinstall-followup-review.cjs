const assert=require('node:assert/strict');
const fs=require('node:fs');
const crypto=require('node:crypto');
const {chromium}=require('C:/Users/andy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const BASE='http://localhost:8785/manual/';
const ROOT='C:/Users/andy/.codex/visualizations/2026/10/03/01a100e0-e188-7c11-b2f0-748214517bb6';
const EXPECT={book_json:'e0d23614c74ca9fdf47caaaa6c4ab758b530639530e20b8eadd140fcf5ef49fe',reader_index:'254d19c38871b71973a6252fe859a02c4a9d6c8c464840d367de58baa8c4ff24',authority:'e34e4faed23c5f5ae6593aba425596eba7ba25594c806a216737d266a37e6800',postinstall_reader_pins:'221496a38940a5b0374923005afa393fb2410c5d9abfe5318741eb6a06547fe8',reviewed_candidate_manifest:'7c47faeea25788afcd2afc924352488b2b5fdfb9ae62b7b44e3e81d682644392',installed_candidate_manifest:'5c88a4c57867ae78e4b4addbe1bed4fd8922f86778535c3697c52a3a506faf41',candidate_patch:'19214520c9662803b9aee51eccbff8c336f15442aa346b9eb77d5c0fb17efe84',install_manifest:'5c88a4c57867ae78e4b4addbe1bed4fd8922f86778535c3697c52a3a506faf41',base_source_review:'5a0884681073d5fbb3c9b09a3361a21064bc8e156381433aca939c3c7886d170',followup_review:'0423e6769944cda6103733b065be49d28659bd8e3e0648592bb291577270f98a'};
const BASE_REVIEW=ROOT+'/proposal-review-20261008-01/combined-v07-source-review.json';
const FOLLOWUP=ROOT+'/locks-c07-1-followup-review-20261008-01/review.json';
const MANIFEST=ROOT+'/locks-c07-1-followup-20261008-01/manifest.json';
const PATCH=ROOT+'/locks-c07-1-followup-20261008-01/PATCH.diff';
const routes=[
 ['pocket-rhythm','cookbook',['nb_oilcan','64 steps','pattern 1']],
 ['small-hours','cookbook',['nb_doubledecker','Pattern 1','Pattern 2']],
 ['tilting-harmony','cookbook',['nb_doubledecker','nb_polyperc','MIDI 62']],
 ['loops-that-meet','cookbook',['one step is a sixth of a second','90 BPM']],
 ['masks','cookbook',['nb_polyperc','Pattern 1','Pattern 2']],
 ['note-merge-modes','cookbook',['nb_polyperc','AVERAGE','UP (Higher)']],
 ['scale-editor','cookbook',['Pattern Note','K3']],
 ['song-editor','cookbook',['slot 2']],
 ['interacting-with-slots','cookbook',['slot 2','octave']],
 ['lock-random-to-pentatonic','cookbook',['several loops','random']],
 ['lock-all-to-pentatonic','cookbook',['C, D, E, F','Minor']],
 ['midi-panic','reference',['Panic','playback']],
 ['lock-lead-time','reference',['lock values','note']],
 ['locks','cookbook',['channel G3 default','explicit zero transpose lock','Use E2 to select parameter slot 1']],
 ['save-and-load','reference',['Enter a name','successful named save']],
 ['midi-controller-options','reference',['keyboard','scale']],
 ['honor-scale-rotations','reference',['Degree','Rotation']],
 ['honour-scale-transpose','reference',['Transpose','scale']],
 ['performance-management','reference',['When playback slows']]
];
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{
 const fetchBytes=async p=>{const r=await fetch(BASE+p);assert.equal(r.status,200,`${p} HTTP`);return Buffer.from(await r.arrayBuffer())};
 const [bookBytes,bookJsBytes,readerIndexBytes]=await Promise.all(['generated/book.json','book.js','generated/reader-index.json'].map(fetchBytes));
 const bookSha=sha(bookBytes),bookJsSha=sha(bookJsBytes),indexSha=sha(readerIndexBytes);
 assert.equal(bookSha,EXPECT.book_json,'installed canonical book bytes');assert.equal(indexSha,EXPECT.reader_index,'installed reader-index bytes');
 const book=JSON.parse(bookBytes.toString('utf8')),index=JSON.parse(readerIndexBytes.toString('utf8'));
 assert.equal(book.authoring_identity?.sha256,EXPECT.authority);assert.equal(index.authoring_identity?.sha256,EXPECT.authority);
 const baseReportBytes=fs.readFileSync(BASE_REVIEW),followupBytes=fs.readFileSync(FOLLOWUP),manifestBytes=fs.readFileSync(MANIFEST),patchBytes=fs.readFileSync(PATCH);
 assert.equal(sha(baseReportBytes),EXPECT.base_source_review);assert.equal(sha(followupBytes),EXPECT.followup_review);assert.equal(sha(manifestBytes),EXPECT.installed_candidate_manifest);assert.equal(sha(patchBytes),EXPECT.candidate_patch);
 const baseReport=JSON.parse(baseReportBytes),followup=JSON.parse(followupBytes),manifest=JSON.parse(manifestBytes);
 assert.equal(baseReport.unit_ratings.length,52);assert.equal(baseReport.additional_performance_review.length,2);assert.equal(followup.units.length,3);assert.equal(followup.all_scores_at_or_above_threshold,true);assert.equal(followup.decay_hold.status,'closed_source_only');
 assert.equal(manifest.validation.parsed_source_diff,'passed: exactly three authored text leaves in two YAML files');
 const featureById=id=>{const f=book.features.find(x=>x.id===id);assert.ok(f,`installed feature ${id}`);return f};
 const expectedLocks=manifest.parsed_allowlist.find(x=>x.file==='manual/features/reference-locks.yaml').after;
 const expectedSmall=manifest.parsed_allowlist.filter(x=>x.file==='manual/features/cookbook.yaml');assert.equal(expectedSmall.length,2);
 const expectedSmallByIdx=new Map(expectedSmall.map(x=>[x.path[3],x.after]));
 const lockFeature=featureById('locks'),smallFeature=featureById('small-hours');
 assert.equal(lockFeature.recipes[4].text,expectedLocks,'installed Locks recipe exactly equals reviewed candidate scalar');
 assert.equal(smallFeature.recipes[1].text,expectedSmallByIdx.get(1),'installed Small Hours bass recipe matches reviewed scalar');
 assert.equal(smallFeature.recipes[2].text,expectedSmallByIdx.get(2),'installed Small Hours chord recipe matches reviewed scalar');
 const indexFeatureById=id=>{const f=index.features.find(x=>x.id===id);assert.ok(f,`indexed feature ${id}`);return f};
 assert.equal(indexFeatureById('locks').recipes[4].text,expectedLocks);assert.equal(indexFeatureById('small-hours').recipes[1].text,expectedSmallByIdx.get(1));assert.equal(indexFeatureById('small-hours').recipes[2].text,expectedSmallByIdx.get(2));
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  const goto=async hash=>{await page.goto(BASE+hash);await page.waitForFunction(()=>document.body.dataset.routeReady==='1'&&!document.body.classList.contains('book-loading'));return page.evaluate(()=>({hash:location.hash,title:document.querySelector('#feature-title')?.textContent?.trim(),body:document.body.innerText}));};
  const routeChecks=[];
  for(const [feature,section,needles] of routes){const home=await goto('#'+feature);assert.equal(home.hash,'#'+feature,`${feature} home`);assert.ok(home.title);const rendered=await goto(`#${feature}/section-${section}`);assert.equal(rendered.hash,`#${feature}/section-${section}`,`${feature} section`);const t=rendered.body.toLowerCase();for(const needle of needles)assert.ok(t.includes(needle.toLowerCase()),`${feature}: ${needle}`);routeChecks.push({feature,section,needles});}
  await goto('#small-hours/section-cookbook');let smallText=await page.locator('#cookbook').innerText();assert.ok(smallText.includes('The bass part is silent in bars 2–4, while the completed drums continue their four-bar pattern.'),'bass-part silence clarification rendered');assert.ok(smallText.includes('The chord part is silent in bars 2–4, while the completed drums and bass continue their four-bar patterns.'),'chord-part silence clarification rendered');
  await goto('#locks/section-cookbook');let locksText=await page.locator('#cookbook').innerText();const reassign='Use E2 to select parameter slot 1, press K2, use E3 to highlight Decay, press K3 to assign it and K2 to return.';assert.ok(locksText.includes(reassign),'post-copy Decay reassignment instruction rendered');
  await goto('#tilting-harmony/section-cookbook');const installLink=page.locator('#cookbook a[href="#norns-sound-sources-with-n-b"]');assert.ok(await installLink.count()>=1,'install guide link');await installLink.first().click();await page.waitForFunction(()=>location.hash==='#norns-sound-sources-with-n-b'&&document.body.dataset.routeReady==='1');
  await goto('#small-hours/section-cookbook');const assignment=await page.locator('#cookbook').innerText();for(const p of ['Pattern 1','Pattern 2','Pattern 3'])assert.ok(assignment.includes(p));
  await goto('#interacting-with-slots/section-cookbook');const slotText=await page.locator('#cookbook').innerText();assert.match(slotText,/tap slot 2/i);assert.match(slotText,/octave/i);
  await goto('#performance-management/section-reference');await page.locator('#reference details summary').filter({hasText:'When playback slows'}).click();const performanceText=await page.locator('#reference').innerText();assert.match(performanceText,/reduce simultaneous voices/i);assert.doesNotMatch(performanceText,/1\.1\.1|test history|earlier timing test/i);
  const mobile=[];await page.setViewportSize({width:390,height:844});for(const feature of ['small-hours','locks']){await goto(`#${feature}/section-cookbook`);const observation=await page.evaluate(()=>({title:document.querySelector('#feature-title')?.textContent?.trim(),viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,bodyWidth:document.body.scrollWidth}));assert.ok(observation.documentWidth<=observation.viewport,`${feature} document overflow`);assert.ok(observation.bodyWidth<=observation.viewport,`${feature} body overflow`);mobile.push({feature,...observation});}
  await goto('#small-hours/section-cookbook');smallText=await page.locator('#cookbook').innerText();assert.ok(smallText.includes('The bass part is silent in bars 2–4, while the completed drums continue their four-bar pattern.'));assert.ok(smallText.includes('The chord part is silent in bars 2–4, while the completed drums and bass continue their four-bar patterns.'));
  await goto('#locks/section-cookbook');locksText=await page.locator('#cookbook').innerText();assert.ok(locksText.includes(reassign));
  assert.deepEqual(errors,[],'no browser page errors');
  const receipt={passed:true,preview:BASE,installed:{book_json_sha256:bookSha,reader_index_sha256:indexSha,authority_sha256:book.authoring_identity.sha256,book_js_sha256:bookJsSha,manual_js_sha256:sha(await fetchBytes('manual.js')),manual_css_sha256:sha(await fetchBytes('manual.css')),postinstall_reader_pins_sha256:EXPECT.postinstall_reader_pins,install_manifest_sha256:EXPECT.install_manifest},candidate:{reviewed_candidate_manifest_sha256:EXPECT.reviewed_candidate_manifest,installed_candidate_manifest_sha256:sha(manifestBytes),patch_sha256:sha(patchBytes),candidate_file_after_sha256s:manifest.files.map(x=>({path:x.path,sha256:x.after_sha256}))},review_lineage:{previous_report_sha256:sha(baseReportBytes),previous_units:52,previous_performance_units:2,followup_review_sha256:sha(followupBytes),freshly_rated_units:followup.units.map(x=>({id:x.unit_id,scores:x.scores})),prior_units_carried:49,source_hold_closed:followup.decay_hold.status==='closed_source_only',installed_render_hold_cleared:true},exact_source_leaf_parity:{locks_recipe_4:lockFeature.recipes[4].text===expectedLocks,small_hours_recipe_1:smallFeature.recipes[1].text===expectedSmallByIdx.get(1),small_hours_recipe_2:smallFeature.recipes[2].text===expectedSmallByIdx.get(2),all_three_match_book_and_index:true},retained_route_checks:routeChecks,mobile_checks:mobile,interaction_checks:['setup link navigates','Small Hours Pattern 1/2/3 assignment instructions visible','slot 2 selection/octave instructions visible','Performance details expanded and current advice visible'],page_errors:errors,audio_or_playback_started:false};
  console.log(JSON.stringify(receipt,null,2));
 }finally{await browser.close()}
})().catch(e=>{console.error(e.stack||e);process.exit(1)});
