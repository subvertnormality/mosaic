-- Real step module, isolated decision boundary. Native musical cases are separate.
local checked=0
for _,changed in ipairs({false,true}) do
for _,song_on in ipairs({false,true}) do
for _,transition_reset in ipairs({false,true}) do
for _,repeat_reset in ipairs({false,true}) do
for _,point in ipairs({{0,1},{1,1},{64,2},{128,2}}) do
 local data={selected_song_pattern=1,global_step_accumulator=point[1],song_patterns={}}
 local counters={};for c=1,17 do counters[c]=c%4+1 end
 local initial={};for c,v in ipairs(counters) do initial[c]=v end
 for s=1,2 do data.song_patterns[s]={global_pattern_length=64,repeats=point[2],active=true,channels={}}
  for c=1,17 do data.song_patterns[s].channels[c]={clock_mods={value=1,type='clock_division'}} end
 end
 local reset_calls,realign_calls,division_calls=0,0,0
 local repeat_count=1
 program={get=function() return data end,get_selected_song_pattern=function() return data.song_patterns[data.selected_song_pattern] end,
  get_repeat_count=function() return repeat_count end,set_repeat_count=function(n) repeat_count=n end,
  set_selected_song_pattern=function(n) data.selected_song_pattern=n end,
  get_channel=function(s,c) return data.song_patterns[s].channels[c] end,
  set_current_step_for_channel=function(c,n) counters[c]=n;reset_calls=reset_calls+1 end}
 local flags={song_mode=song_on and 2 or 1,reset_on_song_pattern_transition=transition_reset and 2 or 1,reset_on_end_of_pattern_repeat=repeat_reset and 2 or 1}
 params={get=function(_,key) assert(flags[key]~=nil,key);return flags[key] end}
 fn={constrain=function(n) return n end}
 local clock={realign_sprockets=function() realign_calls=realign_calls+1 end,calculate_divisor=function() return 4 end,set_channel_division=function() division_calls=division_calls+1 end}
 include=function(path)
  if path=='mosaic/lib/clock/m_clock' then return clock end
  if path=='mosaic/lib/quantiser' then return {} end
  assert(path=='mosaic/lib/clock/divisions',path);return {note_divisions={}}
 end
 channel_edit_page_ui={}
 for _,name in ipairs({'align_global_and_local_swing_shuffle_type_values','align_global_and_local_swing_values','align_global_and_local_shuffle_feel_values','align_global_and_local_shuffle_basis_values','align_global_and_local_shuffle_amount_values','refresh_clock_mods','refresh_swing','refresh_swing_shuffle_type','refresh_shuffle_feel','refresh_shuffle_basis','refresh_shuffle_amount'}) do channel_edit_page_ui[name]=function() end end
 pattern={update_working_patterns=function() end};song_edit_page={refresh=function() end};channel_edit_page={refresh=function() end}
 local Step=dofile(arg[1] or 'lib/step.lua')
 Step.queue_next_song_pattern(changed and 2 or 1)
 Step.process_song_song_patterns()
 local boundary=point[1]==128
 local should_reset=boundary and song_on and ((changed and transition_reset) or repeat_reset)
 assert(realign_calls==(should_reset and 1 or 0),'Clock phase reset disagrees with reset policy')
 assert(reset_calls==(should_reset and 17 or 0),'Channel counter reset disagrees with policy')
 for c=1,17 do assert(counters[c]==(should_reset and 99 or initial[c]),'Wrong channel reset') end
 assert(data.selected_song_pattern==((boundary and song_on and changed) and 2 or 1),'Unexpected song transition')
 assert(division_calls==((boundary and song_on and changed) and 17 or 0),'Unexpected division update')
 checked=checked+1
end end end end end
print(checked..' reset decision cases passed: both reset flags, transitions/repeats, song mode and boundary state')
