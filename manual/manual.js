"use strict";
(() => {
const $ = id => document.getElementById(id);
let data, inventory=[], sceneIndex=0, stepIndex=0, timer=null, audioRAF=null, savedStep=null;
const controls={enc:[],key:[],grid:[]};
const notice=text=>{ $("notice").textContent=text;$("notice").style.display="block";clearTimeout(notice.timer);notice.timer=setTimeout(()=>$("notice").style.display="none",3500); };
const theme=localStorage.getItem("mosaic-manual-theme")||(matchMedia("(prefers-color-scheme:light)").matches?"light":"dark");
function setTheme(value){document.documentElement.dataset.theme=value;$("theme").textContent=value==="dark"?"Light mode":"Dark mode";localStorage.setItem("mosaic-manual-theme",value);}
setTheme(theme);
$("theme").onclick=()=>setTheme(document.documentElement.dataset.theme==="dark"?"light":"dark");
const node=(tag,text,parent,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;if(parent)parent.append(n);return n;};
function unpack(rle){const result=[];for(const [value,count] of rle){if(!Number.isInteger(value)||value<0||value>15||!Number.isInteger(count)||count<1||result.length+count>8192)throw Error("Invalid captured pixels");for(let i=0;i<count;i++)result.push(value);}if(result.length!==8192)throw Error("Incomplete framebuffer");return result;}
function paint(output){
 const levels=unpack(output.screen_rle), ctx=$("screen").getContext("2d"), frame=ctx.createImageData(128,64);
 levels.forEach((level,i)=>{frame.data[i*4]=frame.data[i*4+1]=frame.data[i*4+2]=level*17;frame.data[i*4+3]=255;});ctx.putImageData(frame,0,0);
 if(output.grid.length!==128)throw Error("Incomplete grid capture");
 controls.grid.forEach((button,i)=>{const level=output.grid[i];button.style.setProperty("--level",level);button.dataset.level=level;button.setAttribute("aria-label",`Grid column ${i%16+1}, row ${Math.floor(i/16)+1}, brightness ${level} of 15`);});
}
function activeScene(){return data.scenes[sceneIndex];}
function stopAuto(){clearInterval(timer);timer=null;$("autoplay").setAttribute("aria-pressed","false");$("autoplay").textContent="Auto-play";}
function heldAt(index){const held=new Set();for(let i=0;i<=index;i++)for(const a of activeScene().steps[i].inputs){if(a.type!=="grid"||!("state" in a))continue;const key=(a.y-1)*16+a.x-1;if(a.state)held.add(key);else held.delete(key);}return held;}
function render(){
 if(!data)return;
 const scene=activeScene(), step=scene.steps[stepIndex];paint(step.output);
 $("counter").textContent=`${String(stepIndex+1).padStart(2,"0")} / ${String(scene.steps.length).padStart(2,"0")}`;
 $("caption-index").textContent=String(stepIndex+1).padStart(2,"0");
 $("step-title").textContent=stepIndex===0?"Find your way in":stepIndex===scene.steps.length-1?"Hear what remains":scene.title;
 $("caption").textContent=step.caption;
 $("screen").setAttribute("aria-label",step.caption+" Screen: "+(step.expect.screen||[]).map(([k,v])=>k+" = "+v).join(", "));
 $("result-text").textContent="Verified: "+(step.expect.screen||[]).map(([k,v])=>k.replaceAll("_"," ")+" = "+v).join(" · ")+(step.expect.midi_phrase?" · exact MIDI phrase over two cycles":"");
 $("previous").disabled=stepIndex===0;$("next").disabled=stepIndex===scene.steps.length-1;
 $("step-strip").replaceChildren();
 scene.steps.forEach((step,i)=>{const b=node("button",String(i+1).padStart(2,"0"),$("step-strip"));b.setAttribute("aria-label","Step "+(i+1)+": "+step.caption);if(i===stepIndex)b.setAttribute("aria-current","step");b.onclick=()=>{stopAudio();stopAuto();stepIndex=i;render();};});
 document.querySelectorAll(".next-control").forEach(n=>n.classList.remove("next-control"));
 const next=scene.steps[stepIndex+1];
 if(next)for(const a of next.inputs){let target;if(a.type==="enc")target=controls.enc[a.n-1];else if(a.type==="key")target=controls.key[a.n-1];else if(a.type==="grid")target=controls.grid[(a.y-1)*16+a.x-1];if(target)target.classList.add("next-control");}
 const held=heldAt(stepIndex);controls.grid.forEach((b,i)=>b.classList.toggle("held",held.has(i)));
 const hash=scene.id+"/"+step.id;if(!location.hash.startsWith("#mask"))history.replaceState(null,"","#masks");
 $("control-help").textContent=next?"Use Next or a highlighted control. A drag turns an encoder; arrow keys work when it has focus.":"Scene complete. Go back to compare, or choose another interaction.";
}
function stopAudio(){if(!$("audio").paused)$("audio").pause();cancelAnimationFrame(audioRAF);}
function move(delta){stopAudio();stopAuto();stepIndex=Math.max(0,Math.min(activeScene().steps.length-1,stepIndex+delta));render();}
function gesture(type,details){
 if(!data)return;
 const next=activeScene().steps[stepIndex+1];
 const match=next&&next.inputs.some(a=>a.type===type&&Object.entries(details).every(([k,v])=>k==="direction"?Math.sign(a.delta)===v:a[k]===v));
 if(match)move(1);else notice(next?"This is a guided replay. Use a highlighted control or Next for the next captured gesture.":"Scene complete. Choose another interaction.");
}
document.querySelectorAll(".encoder").forEach((b,i)=>{
 controls.enc.push(b);let start=null,done=false;
 b.addEventListener("pointerdown",e=>{start=e.clientX;done=false;b.setPointerCapture(e.pointerId);});
 b.addEventListener("pointermove",e=>{if(start!==null&&!done&&Math.abs(e.clientX-start)>15){done=true;gesture("enc",{n:i+1,direction:Math.sign(e.clientX-start)});}});
 b.addEventListener("pointerup",()=>{if(!done)gesture("enc",{n:i+1});start=null;});
 b.addEventListener("pointercancel",()=>{start=null;});
 b.addEventListener("keydown",e=>{if(["ArrowLeft","ArrowDown","ArrowRight","ArrowUp"].includes(e.key)){e.preventDefault();gesture("enc",{n:i+1,direction:["ArrowLeft","ArrowDown"].includes(e.key)?-1:1});}else if(e.key==="Enter"||e.key===" "){e.preventDefault();gesture("enc",{n:i+1});}});
});
document.querySelectorAll("[data-key]").forEach((b,i)=>{controls.key.push(b);b.onclick=()=>gesture("key",{n:i+1});});
for(let x=1;x<=16;x++)node("span",x,document.querySelector(".grid-columns"));
for(let i=0;i<128;i++){
 const b=node("button",undefined,$("grid"));b.type="button";b.tabIndex=i===0?0:-1;b.dataset.index=i;controls.grid.push(b);
 b.onclick=()=>gesture("grid",{x:i%16+1,y:Math.floor(i/16)+1});
 b.onkeydown=e=>{const shift={ArrowLeft:-1,ArrowRight:1,ArrowUp:-16,ArrowDown:16}[e.key];if(shift!==undefined){e.preventDefault();const target=Math.max(0,Math.min(127,i+shift));controls.grid.forEach(n=>n.tabIndex=-1);controls.grid[target].tabIndex=0;controls.grid[target].focus();}};
}
$("previous").onclick=()=>move(-1);$("next").onclick=()=>move(1);
$("autoplay").onclick=()=>{
 if(timer){stopAuto();return;}stopAudio();if(stepIndex===activeScene().steps.length-1)stepIndex=0;
 $("autoplay").setAttribute("aria-pressed","true");$("autoplay").textContent="Pause";
 timer=setInterval(()=>{if(stepIndex<activeScene().steps.length-1){stepIndex++;render();}else stopAuto();},matchMedia("(prefers-reduced-motion:reduce)").matches?6000:4000);render();
};
$("scene").onchange=()=>{stopAudio();stopAuto();sceneIndex=Number($("scene").value);stepIndex=0;render();};
$("dense").onclick=()=>{const enabled=document.body.classList.toggle("dense");$("dense").setAttribute("aria-pressed",String(enabled));$("dense").textContent=enabled?"Comfort view":"Dense view";};
function populate(){
 const f=data.feature;$("summary").textContent=f.summary;$("intro").textContent=f.prose;$("musical-use").textContent=f.musical_use;
 data.scenes.forEach((s,i)=>{const option=node("option",s.title,$("scene"));option.value=i;});
 for(const c of f.controls){const row=node("tr",undefined,$("controls"));node("td",c.gesture,row);node("td",c.result,row);}
 for(const d of f.details){const detail=node("details",undefined,$("details"));node("summary",d.title,detail);node("p",d.text,detail);}
 f.recipes.forEach((r,i)=>{const card=node("article",undefined,$("recipes"),"recipe");node("span","RECIPE "+String(i+1).padStart(2,"0"),card,"recipe-number");node("h3",r.title,card);node("p",r.text,card);});
 const relatedNames={"merge-modes":"Merge modes","channel-length":"Channel length","chord-strum":"Chord strum","fully-quantise-mask":"Fully quantise masks","live-recording":"Live recording"};
 for(const id of f.related){const a=node("a",relatedNames[id]||id,$("related-links"));a.href="../README.md#"+id;}
 const audio=data.audio;
 if(audio){$("audio-title").textContent=audio.title;$("audio-description").textContent=audio.description;for(const path of audio.files){const source=node("source",undefined,$("audio"));source.src=path;source.type=path.endsWith(".ogg")?"audio/ogg; codecs=opus":"audio/mpeg";}for(const t of audio.tracks)node("span",`CH ${t.channel} / ${t.voice} / ${t.role}`,$("track-list"));$("audio").load();}
 else{$("audio").hidden=true;$("audio-description").textContent="Audio has not been captured in this development build. The scene evidence is available; complete pilot acceptance still requires real multi-voice audio.";}
 $("evidence-status").textContent="Source "+data.source_sha256.slice(0,12)+" · "+data.validation.clock_mode+" · "+(data.validation.pilot_complete?"pilot build verified":"development build; full pilot pending")+" · full campaign coverage is separate.";
 render();
}
function audioPaint(){
 if(!data.audio?.timeline.length)return;
 const t=$("audio").currentTime, timeline=data.audio.timeline;
 let lo=0,hi=timeline.length-1;
 while(lo<hi){const mid=Math.ceil((lo+hi)/2);if(timeline[mid].time<=t)lo=mid;else hi=mid-1;}
 paint(timeline[lo].output);$("screen").setAttribute("aria-label","Captured musical example at "+t.toFixed(1)+" seconds");
 $("counter").textContent="LISTEN / "+t.toFixed(1)+"s";
 document.querySelectorAll(".next-control").forEach(n=>n.classList.remove("next-control"));
 controls.grid.forEach(b=>b.classList.remove("held"));
 if(!$("audio").paused)audioRAF=requestAnimationFrame(audioPaint);
}
$("audio").addEventListener("play",()=>{stopAuto();savedStep=[sceneIndex,stepIndex];audioPaint();});
$("audio").addEventListener("pause",()=>{cancelAnimationFrame(audioRAF);audioPaint();});
$("audio").addEventListener("seeked",audioPaint);
$("audio").addEventListener("ended",()=>{if(savedStep){[sceneIndex,stepIndex]=savedStep;render();}});
$("search").oninput=()=>{
 const q=$("search").value.trim().toLowerCase(), target=$("search-results");target.replaceChildren();if(!q||!data)return;
 const f=data.feature, local=[{title:"Masks",text:f.summary+" "+f.prose,anchor:"#masks"},{title:"Controls",text:f.controls.map(v=>v.gesture+" "+v.result).join(" "),anchor:"#reference"},...f.details.map(v=>({title:v.title,text:v.text,anchor:"#reference"})),...f.recipes.map(v=>({title:v.title,text:v.text,anchor:"#cookbook"}))];
 const results=local.filter(v=>(v.title+" "+v.text).toLowerCase().includes(q)).concat(inventory.filter(v=>(v.title+" "+v.controls.join(" ")).toLowerCase().includes(q)).map(v=>({title:v.title+" · existing manual",anchor:"../README.md#"+v.id}))).slice(0,12);
 if(!results.length)node("p","No match. Try “velocity”, “clear” or “scale”.",target);
 for(const result of results){const a=node("a",result.title,target);a.href=result.anchor;}
};
document.addEventListener("visibilitychange",()=>{if(document.hidden){stopAuto();stopAudio();}});
window.addEventListener("pagehide",()=>{stopAuto();stopAudio();});
fetch("generated/pilot.json").then(response=>{if(!response.ok)throw Error("Captured pilot data is missing. Run the command in BUILD.md.");return response.json();}).then(value=>{data=value;populate();return fetch("inventory.json");}).then(r=>r.json()).then(v=>inventory=v.features).catch(error=>{$("summary").textContent="The field guide could not load.";$("intro").textContent=error.message;notice(error.message);});
})();
