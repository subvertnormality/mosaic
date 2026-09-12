-- Actual program lookup with explicit model fixtures, not workflow evidence.
package.preload.musicutil=function()return {}end
function include(path)
 if path=='mosaic/lib/models/model_defaults' then return dofile('lib/models/model_defaults.lua') end
 return {}
end
fn={calc_grid_count=function(x,y)return (y-1)*16+x end}
local program=dofile('lib/models/program.lua')
local options,data,song,next_song
params={get=function(_,id)return options[id]end}
step={calculate_next_selected_song_pattern=function()return next_song end}
program.get=function()return data end
program.get_selected_song_pattern=function()return song end
local function fixture()
 options={wrap_param_slides=2,song_mode=1,trigless_locks=1};data={selected_song_pattern=1};song={global_pattern_length=64};next_song=1
 local c={start_trig={9,1},end_trig={12,1},step_trig_lock_banks={},working_pattern={trig_values={}}}
 for n=1,64 do c.working_pattern.trig_values[n]=1 end
 return c
end
local function lock(c,n,v)c.step_trig_lock_banks[n]={[1]=v}end
local tests={
 range_wrap=function()local c=fixture();lock(c,3,3);lock(c,10,64);lock(c,16,16);local r=program.get_next_trig_lock_step(c,12,1,-1);assert(r and r.step==10 and r.should_wrap,'Selected lock outside active range');assert(r.distance==2)end,
 no_wrap=function()local c=fixture();options.wrap_param_slides=1;lock(c,16,16);assert(not program.get_next_trig_lock_step(c,12,1,-1),'Out-of-range future lock selected')end,
 global_cap=function()local c=fixture();c.end_trig={16,1};song.global_pattern_length=4;lock(c,14,14);lock(c,9,24);local r=program.get_next_trig_lock_step(c,12,1,-1);assert(r and r.step==9 and r.distance==1,'Global pattern length did not cap traversal')end,
 off_minus_one=function()local c=fixture();lock(c,10,-1);lock(c,11,0);local r=program.get_next_trig_lock_step(c,9,1,-1);assert(r and r.step==11 and r.value==0,'Off must be skipped and zero retained')end,
 off_above_range=function()local c=fixture();lock(c,10,200);lock(c,12,127);local r=program.get_next_trig_lock_step(c,9,1,200);assert(r and r.step==12,'Custom Off selected')end,
 inactive=function()local c=fixture();lock(c,10,64);lock(c,12,96);c.working_pattern.trig_values[10]=0;local r=program.get_next_trig_lock_step(c,9,1,-1);assert(r and r.step==12,'Inactive lock selected with trigless disabled');options.trigless_locks=2;r=program.get_next_trig_lock_step(c,9,1,-1);assert(r and r.step==10)end,
 self_next_loop=function()local c=fixture();lock(c,9,24);local r=program.get_next_trig_lock_step(c,9,1,-1);assert(r and r.step==9 and r.should_wrap and r.distance==4,'Next-loop occurrence lost')end,
 song_boundary=function()local c=fixture();lock(c,9,24);options.song_mode=2;next_song=2;assert(not program.get_next_trig_lock_step(c,12,1,-1))end,
 outside_source=function()local c=fixture();lock(c,10,24);assert(not program.get_next_trig_lock_step(c,2,1,-1))end
}
local failed,total=0,0;local names={};for n in pairs(tests)do names[#names+1]=n end;table.sort(names)
for _,n in ipairs(names)do total=total+1;local ok,err=pcall(tests[n]);if not ok then failed=failed+1 end;print((ok and 'PASS ' or 'FAIL ')..n..(ok and '' or ': '..tostring(err)))end
print(string.format('Collected %d; passed %d; failed %d',total,total-failed,failed));os.exit(failed==0 and 0 or 1)
