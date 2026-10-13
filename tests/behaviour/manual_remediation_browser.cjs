/* Characterisations outside README: recorded reader receipts, result disclosure and MIDI display.
 * The reader replays stored native evidence; these checks do not run Mosaic or claim scheduling accuracy.
 * Public controls remain exact; no forced hidden inputs or expected-as-observed MIDI.
 */
const fs=require('fs'),os=require('os'),path=require('path'),assert=require('assert/strict'),{spawnSync}=require('child_process');
async function runRemediation(){
const names=["receipts", "persistence", "probability", "key_tap", "feedback", "midi_ending", "explicit_mobile", "missing_timestamp", "program_display"];const dir=fs.mkdtempSync(path.join(os.tmpdir(),'mosaic-reader-regressions-'));const reports=[];
try{for(const name of names){const output=path.join(dir,name+'.json'),r=spawnSync(process.execPath,[path.join(__dirname,'remediation',name+'.cjs'),output],{env:process.env,encoding:'utf8'});assert.equal(r.status,0,name+': '+r.stderr);const report=JSON.parse(fs.readFileSync(output));assert.equal(report.passed,true,name+': '+JSON.stringify(report));reports.push({name,report});}const result={passed:true,characterisation:'Stored-evidence reader regressions outside README',reports};if(process.env.MOSAIC_REMEDIATION_REPORT)fs.writeFileSync(process.env.MOSAIC_REMEDIATION_REPORT,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({passed:true,checks:names.length}));}finally{fs.rmSync(dir,{recursive:true,force:true});}

}
module.exports=runRemediation;
if(require.main===module)runRemediation().catch(e=>{console.error(e);process.exitCode=1});
