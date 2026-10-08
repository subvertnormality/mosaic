const assert=require('node:assert/strict');
const fs=require('node:fs');
const crypto=require('node:crypto');
const {chromium}=require('C:/Users/andy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const BASE='http://localhost:8785/manual/';
const EXPECT={book_json:'38beead5d88faa3a5aa1a5a0fc27c25796308c4d84bd831060035fe5085ef89f',reader_index:'73dc1ddb8952ca590cb9d670ee3a145ee460a68ec27f3259c1a08e28283323ca',authority:'9d5e81b8776366aae0f9460d59bfe3d5f0d02e337d3188e965a143491d88e053',source_review:'5a0884681073d5fbb3c9b09a3361a21064bc8e156381433aca939c3c7886d170'};
const REVIEW_PATH='C:/Users/andy/.codex/visualizations/2026/10/03/01a100e0-e188-7c11-b2f0-748214517bb6/proposal-review-20261008-01/combined-v07-source-review.json';
const routes=[
 ['pocket-rhythm','cookbook',['nb_oilcan','64 steps','pattern 1']],
 ['small-hours','cookbook',['nb_doubledecker','pattern 1','pattern 2']],
 ['tilting-harmony','cookbook',['nb_doubledecker','nb_polyperc','MIDI 62']],
 ['loops-that-meet','cookbook',['one step is a sixth of a second','90 BPM']],
 ['masks','cookbook',['nb_polyperc','pattern 1','pattern 2']],
 ['note-merge-modes','cookbook',['nb_polyperc','AVERAGE','UP (Higher)']],
 ['scale-editor','cookbook',['Pattern Note','K3']],
 ['song-editor','cookbook',['slot 2']],
 ['interacting-with-slots','cookbook',['slot 2','octave']],
 ['lock-random-to-pentatonic','cookbook',['several loops','random']],
 ['lock-all-to-pentatonic','cookbook',['C, D, E, F','Minor']],
 ['midi-panic','reference',['Panic','playback']],
 ['lock-lead-time','reference',['lock values','note']],
 ['locks','cookbook',['channel G3 default','explicit zero transpose lock']],
 ['save-and-load','reference',['Enter a name','successful named save']],
 ['midi-controller-options','reference',['keyboard','scale']],
 ['honor-scale-rotations','reference',['Degree','Rotation']],
 ['honour-scale-transpose','reference',['Transpose','scale']],
 ['performance-management','reference',['When playback slows']],
];
(async()=>{
 const fetchBytes=async path=>{const response=await fetch(BASE+path);assert.equal(response.status,200,`${path} HTTP`);return Buffer.from(await response.arrayBuffer())};
 const bookBytes=await fetchBytes('generated/book.json'),readerScriptBytes=await fetchBytes('book.js'),indexBytes=await fetchBytes('generated/reader-index.json');
 const bookSha=crypto.createHash('sha256').update(bookBytes).digest('hex'); const readerScriptSha=crypto.createHash('sha256').update(readerScriptBytes).digest('hex');
 const reviewBytes=fs.readFileSync(REVIEW_PATH); const reviewSha=crypto.createHash('sha256').update(reviewBytes).digest('hex'); const review=JSON.parse(reviewBytes.toString('utf8'));
 assert.equal(reviewSha,EXPECT.source_review,'source-review exact bytes'); assert.equal(review.unit_ratings.length,52); assert.equal(review.additional_performance_review.length,2); assert.equal(review.decision,'SOURCE_REVIEW_PASS_PENDING_PREVIEW_VERIFICATION');
 const heldUnit='doc-language-cleanup:feature:locks:recipes[4]'; assert.ok(review.unit_ratings.some(u=>u.unit_id===heldUnit));
 const indexSha=crypto.createHash('sha256').update(indexBytes).digest('hex');
 assert.equal(indexSha,EXPECT.reader_index,'reader-index exact pinned bytes');
 const index=JSON.parse(indexBytes.toString('utf8'));
 const authoritySha=index.authoring_identity?.sha256;assert.equal(authoritySha,EXPECT.authority,'authoring identity pin');
 assert.equal(bookSha,EXPECT.book_json,'generated/book.json exact pinned bytes'); const bookShaMatch=true;
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const goto=async hash=>{await page.goto(BASE+hash);await page.waitForFunction(()=>document.body.dataset.routeReady==='1'&&!document.body.classList.contains('book-loading'));return page.evaluate(()=>({hash:location.hash,title:document.querySelector('#feature-title')?.textContent?.trim(),body:document.body.innerText}));};
  const checks=[];
  for(const [feature,section,needles] of routes){
   const home=await goto('#'+feature);assert.equal(home.hash,'#'+feature,`${feature} canonical route`);assert.ok(home.title&&home.title.length>0,`${feature} has a visible title`);
   const rendered=await goto(`#${feature}/section-${section}`);assert.equal(rendered.hash,`#${feature}/section-${section}`,`${feature} section route`);
   const text=rendered.body.toLowerCase();for(const needle of needles)assert.ok(text.includes(needle.toLowerCase()),`${feature} rendered text includes ${needle}`);
   checks.push({feature,section,needles});
  }
  const route=await goto('#tilting-harmony/section-cookbook');
  const installLink=page.locator('#cookbook a[href="#norns-sound-sources-with-n-b"]');assert.ok(await installLink.count()>=1,'Tilting Harmony links to n.b. install guide');
  await installLink.first().click();await page.waitForFunction(()=>document.body.dataset.routeReady==='1'&&!document.body.classList.contains('book-loading'));assert.equal(await page.evaluate(()=>location.hash),'#norns-sound-sources-with-n-b','install help link navigates');
  const small=await goto('#small-hours/section-cookbook');const assignment=await page.locator('#cookbook').innerText();assert.match(assignment,/Pattern 1/i);assert.match(assignment,/Pattern 2/i);assert.match(assignment,/Pattern 3/i);
  const slot=await goto('#interacting-with-slots/section-cookbook');const slotText=await page.locator('#cookbook').innerText();assert.match(slotText,/tap slot 2/i);assert.match(slotText,/octave/i);
  const performance=await goto('#performance-management/section-reference');await page.locator('#reference details summary').filter({hasText:'When playback slows'}).click();const performanceText=await page.locator('#reference').innerText();assert.match(performanceText,/When playback slows/i);assert.match(performanceText,/reduce simultaneous voices/i);assert.doesNotMatch(performanceText,/1\.1\.1|test history|earlier timing test/i);
  assert.deepEqual(errors,[],'no page errors');
  console.log(JSON.stringify({passed:true,preview:BASE,canonical_book_sha256:bookSha,reader_script_sha256:readerScriptSha,reader_index_sha256:indexSha,authority_sha256:authoritySha,source_review_sha256:reviewSha,source_review_counts:{mapped_units:review.unit_ratings.length,performance_units:review.additional_performance_review.length,render_hold:heldUnit,rendered_route_scope:'19 affected feature/reference pages; held Decay endpoint omitted pending assignment continuity fix'},feature_routes:checks,interaction_checks:['n.b. install help link to canonical source guide','Pattern 1/2/3 assignment text visible in Small Hours','slot 2 selection and octave edit visible','Performance Management title/advice visible without version test history'],page_errors:errors},null,2));
 }finally{await browser.close()}
})().catch(e=>{console.error(e.stack||e);process.exit(1)});








