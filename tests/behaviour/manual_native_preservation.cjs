"use strict";
const assert=require("node:assert/strict"),crypto=require("node:crypto");
const {isDeepStrictEqual}=require("node:util");
const stable=v=>JSON.stringify((function ordered(x){return Array.isArray(x)?x.map(ordered):x&&typeof x==="object"?Object.fromEntries(Object.keys(x).sort().map(k=>[k,ordered(x[k])])):x;})(v));
const sha=v=>crypto.createHash("sha256").update(stable(v)).digest("hex");
// Historical output is immutable evidence; a fresh run is a separate native capture.
// The pipeline audits qualified captures against native observations and semantic cases.
// The reader must retain those exact current bytes, including animation and provenance.
function verifyNativePreservation(scene,archived,qualified,baseline){
 assert(archived&&qualified&&baseline,"Both historical and current native evidence are required: "+scene.id);
 const ids=baseline.steps.map(s=>s.id);
 for(const candidate of [archived,scene,qualified]){assert.equal(candidate.id,scene.id,"Native scene identity retained");assert.deepEqual(candidate.steps.map(s=>s.id),ids,"Every original native step retained: "+scene.id);}
 for(const pin of baseline.steps){
  const old=archived.steps.find(s=>s.id===pin.id),current=scene.steps.find(s=>s.id===pin.id),native=qualified.steps.find(s=>s.id===pin.id);
  assert.equal(sha(old.output),pin.output_sha256,"Immutable historical native output identity: "+scene.id+"/"+pin.id);
  assert.equal(sha(old.inputs||[]),pin.inputs_sha256,"Immutable historical native inputs identity: "+scene.id+"/"+pin.id);
  assert.ok(isDeepStrictEqual(current.inputs||[],native.inputs||[]),"Exact current qualified native inputs: "+scene.id+"/"+pin.id);
  // The current reader view is the audited projection, including full MIDI windows.
  // Its canonical raw book bytes are separately pinned by the browser acceptance.
  // Keep strict equality but avoid constructing a quadratic-size assertion diff
  // for complete native MIDI windows when a mutation is correctly rejected.
  assert.ok(isDeepStrictEqual(current.output,native.output),"Exact current qualified native output: "+scene.id+"/"+pin.id);
 }
}
module.exports={verifyNativePreservation};
