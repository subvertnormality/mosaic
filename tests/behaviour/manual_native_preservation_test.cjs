// Characterisation outside the manual: immutable history and exact current native captures.
"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),zlib=require("node:zlib");
const {verifyNativePreservation}=require("./manual_native_preservation.cjs");
const dir=path.join(__dirname,"remediation/fixtures"),baseline=JSON.parse(fs.readFileSync(path.join(dir,"native-placements-v6-baseline.json"))),archive=JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(dir,"native-outputs-v6-baseline.json.gz")))),fresh=JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(dir,"player-routes-fresh-ci-attempt2.json.gz"))));
assert.deepEqual(Object.keys(archive).sort(),Object.keys(baseline.scenes).sort(),"The entire immutable historical scene inventory must be present");
let checks=1;
for(const [id,scene] of Object.entries(archive)){if(!baseline.scenes[id])continue;verifyNativePreservation(scene,scene,scene,baseline.scenes[id]);checks++;}
for(const [id,scene] of Object.entries(fresh)){
 const check=(current=scene,old=archive[id],qualified=scene,pin=baseline.scenes[id])=>verifyNativePreservation(current,old,qualified,pin);
 check();checks++;
 for(const change of [s=>s.steps[0].output.grid[0]^=1,s=>s.steps[0].output.screen_rle[0][0]^=1,s=>s.steps[0].output.binding.passed=false,s=>s.steps[0].inputs[0].delta-=2,s=>s.steps=[]]){const bad=structuredClone(scene);change(bad);assert.throws(()=>check(bad));checks++;}
 const badOld=structuredClone(archive[id]);badOld.steps[0].output.grid[0]^=1;assert.throws(()=>check(scene,badOld));checks++;
 const badPin=structuredClone(baseline.scenes[id]);badPin.steps[0].output_sha256="0".repeat(64);assert.throws(()=>check(scene,archive[id],scene,badPin));checks++;
}
const projected=JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(dir,"fresh-panic-reader-ci-attempt2.json.gz"))));
for(const [id,scene] of Object.entries(projected)){
 verifyNativePreservation(scene,archive[id],scene,baseline.scenes[id]);checks++;
 const target=scene.steps.find(s=>s.output.midi?.provenance?.kind==="fresh-native-panic-sounding-note-target-window-v1");
 assert(target,"Actual fresh Panic fixture includes its complete native target window");
 assert.equal(target.output.midi.truncated,false);assert.equal(target.output.midi.events.length,target.output.midi.total);checks++;
 for(const change of [s=>delete s.output.midi,s=>s.output.midi.total--,s=>s.output.midi.events[0].bytes[0]^=1,s=>s.output.midi.provenance.fresh_record_sha256="0".repeat(64)]){
  const bad=structuredClone(scene);change(bad.steps.find(s=>s.id===target.id));assert.throws(()=>verifyNativePreservation(bad,archive[id],scene,baseline.scenes[id]));checks++;
 }
}
console.log("PASS native preservation checks: "+checks);
