// Acceptance-library runtime smoke test; no browser font/layout certification.
const fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync('docs/ui-reimplementation/generated/index.html','utf8');
const script=html.split('<script>')[1].split('</script>')[0];
const elements=new Map();const noop=()=>{};
function element(){return {value:'',textContent:'',dataset:{},options:[],add(o){this.options.push(o);if(!this.value)this.value=o.value},replaceChildren(){this.options=[];this.value=''},append:noop,getContext(){return new Proxy({},{get:(_,k)=>noop,set:()=>true})}}}
const context={document:{getElementById(id){if(!elements.has(id))elements.set(id,element());return elements.get(id)},createElement:element},Option:function(label,value){this.label=label;this.value=value}};
context.document.getElementById('mode').value='bound';
vm.createContext(context);
try{vm.runInContext(script,context);const result=vm.runInContext(`let rendered=0;for(let id of Object.keys(s.screens)){ $('screen').value=id; update(); for(let mode of ['bound','accepted','empty']){ $('mode').value=mode; for(let opt of $('field').options){$('field').value=opt.value;draw();rendered++}}} rendered`,context);console.log('PASS HTML runtime: '+result+' screen/field/view selections')}catch(e){console.error(e.name+': '+e.message);process.exitCode=1}
