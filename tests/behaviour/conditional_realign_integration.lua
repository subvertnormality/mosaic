-- Real step and lattice modules. Device/UI boundaries are explicit stubs.
util={clamp=function(n,a,b) return math.max(a,math.min(b,n)) end}
local Lattice=dofile('lib/clock/m_lattice.lua')
local checked=0
for _,changed in ipairs({false,true}) do
for _,song_on in ipairs({false,true}) do
for _,transition_reset in ipairs({false,true}) do
for _,repeat_reset in ipairs({false,true}) do
 local lattice=Lattice:new{auto=false,ppqn=96};local period={216,408};local seen={{},{}};local ending={{},{}};local delayed={};local id=0
 local data={selected_song_pattern=1,global_step_accumulator=0,song_patterns={}}
 for s=1,2 do data.song_patterns[s]={global_pattern_length=64,repeats=1,active=true,channels={}}
  for c=1,17 do data.song_patterns[s].channels[c]={clock_mods={value=1,type='clock_division'}} end
 end
 program={get=function() return data end,get_selected_song_pattern=function() return data.song_patterns[data.selected_song_pattern] end,
  get_repeat_count=function() return 1 end,set_repeat_count=function() end,
  set_selected_song_pattern=function(n) data.selected_song_pattern=n end,
  get_channel=function(s,c) return data.song_patterns[s].channels[c] end,set_current_step_for_channel=function() end}
 local flags={song_mode=song_on and 2 or 1,reset_on_song_pattern_transition=transition_reset and 2 or 1,reset_on_end_of_pattern_repeat=repeat_reset and 2 or 1}
 params={get=function(_,key) assert(flags[key]~=nil,key);return flags[key] end}
 fn={constrain=function(n) return n end,generate_id=function() id=id+1;return id end}
 local clock={realign_sprockets=function() lattice:realign_eligable_sprockets() end,calculate_divisor=function() return 4 end,set_channel_division=function() end}
 include=function(path)
  if path=='mosaic/lib/clock/m_clock' then return clock end
  if path=='mosaic/lib/quantiser' then return {} end
  assert(path=='mosaic/lib/clock/divisions',path);return {note_divisions={}}
 end
 channel_edit_page_ui={}
 for _,name in ipairs({'align_global_and_local_swing_shuffle_type_values','align_global_and_local_swing_values','align_global_and_local_shuffle_feel_values','align_global_and_local_shuffle_basis_values','align_global_and_local_shuffle_amount_values','refresh_clock_mods','refresh_swing','refresh_swing_shuffle_type','refresh_shuffle_feel','refresh_shuffle_basis','refresh_shuffle_amount'}) do channel_edit_page_ui[name]=function() end end
 pattern={update_working_patterns=function() end};song_edit_page={refresh=function() end};channel_edit_page={refresh=function() end}
 local Step=dofile(arg[1] or 'lib/step.lua')
 local now=0
 lattice:new_sprocket{division=1/16,order=1,action=function()
  if data.global_step_accumulator>0 and data.global_step_accumulator%64==0 then
   Step.queue_next_song_pattern(changed and (data.selected_song_pattern==1 and 2 or 1) or data.selected_song_pattern)
  end
  Step.process_song_song_patterns();data.global_step_accumulator=data.global_step_accumulator+1
 end}
 local reset=song_on and ((changed and transition_reset) or repeat_reset)
 for c=1,2 do
  local sprocket
  sprocket=lattice:new_sprocket{division=period[c]/384,order=2,realign=true,action=function()
   table.insert(seen[c],now)
   -- At a late onset, span a global boundary with half-, one- and two-step work.
   if #seen[c]==(c==1 and 8 or 4) and not reset then
    local origin=now
    for _,length in ipairs({.5,1,2}) do
     sprocket:set_delayed_action(length,function() table.insert(delayed,{actual=now,expected=origin+period[c]*length}) end,true)
    end
   end
  end}
  lattice:new_sprocket{division=period[c]/384,order=3,realign=true,delay=1,action=function() table.insert(ending[c],now) end}
 end
 lattice:start()
 for tick=0,1536*3 do now=tick;lattice:pulse() end
 for c=1,2 do
  local expected={};local end_expected={}
  for tick=0,1536*3 do
   local epoch=reset and math.floor(tick/1536)*1536 or 0
   if (tick-epoch)%period[c]==0 then
    table.insert(expected,tick)
    if tick>0 then table.insert(end_expected,tick) end
   end
  end
  assert(#seen[c]==#expected,'Wrong channel onset count')
  assert(#ending[c]==#end_expected,'Wrong companion-clock count')
  for i,tick in ipairs(expected) do assert(seen[c][i]==tick,'Wrong channel phase at global boundary') end
  for i,tick in ipairs(end_expected) do assert(ending[c][i]==tick,'Wrong companion-clock phase') end
 end
 if not reset then assert(#delayed==6,'Missing delayed callbacks');for _,event in ipairs(delayed) do assert(event.actual==event.expected,'Boundary moved a pending callback') end end
 checked=checked+1
end end end end
print(checked..' real step/lattice integration cases passed across three boundaries with simultaneous /9 and /17 clocks')
