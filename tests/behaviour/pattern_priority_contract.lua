-- Supplementary real merge-module contract. Native user-input cases remain required.
local song,channel
include=function() return {} end
scheduler={debounce=function(f) return f end}
fn={average_table_values=function(t) local sum=0;for _,v in ipairs(t) do sum=sum+v end;return sum/#t end}
program={initialise_64_table=function() local t={};for i=1,64 do t[i]={} end;return t end,
 get_selected_song_pattern=function() return song end,get=function() return {selected_song_pattern=1} end,
 get_channel=function() return channel end,get_length_mask=function(c) return c.length_mask end,
 get_step_trig_masks=function() return channel.step_trig_masks end,
 get_step_note_masks=function() return channel.step_note_masks end,
 get_step_velocity_masks=function() return channel.step_velocity_masks end,
 get_step_length_masks=function() return channel.step_length_masks end}
local Pattern=dofile(arg[1] or 'lib/pattern.lua')
local source={trig_values={},note_values={},velocity_values={},lengths={},note_mask_values={}}
local rhythm={trig_values={},note_values={},velocity_values={},lengths={},note_mask_values={}}
for step=1,64 do
 source.trig_values[step]=0;source.note_values[step]=step%7+1;source.velocity_values[step]=20+step;source.lengths[step]=3.5;source.note_mask_values[step]=-1
 rhythm.trig_values[step]=1;rhythm.note_values[step]=0;rhythm.velocity_values[step]=100;rhythm.lengths[step]=1;rhythm.note_mask_values[step]=-1
end
local checked=0
for priority=1,16 do for rhythm_slot=1,16 do if priority~=rhythm_slot then
for _,mode in ipairs({'skip','only','all'}) do
for _,field in ipairs({'note','velocity','length'}) do
for _,assigned in ipairs({false,true}) do
for mask_mode=1,3 do
 channel={selected_patterns={[priority]=assigned,[rhythm_slot]=true},step_trig_masks={},step_note_masks={},step_velocity_masks={},step_length_masks={}}
 song={patterns={[priority]=source,[rhythm_slot]=rhythm},channels={[1]=channel}}
 if mask_mode>=2 then channel.step_note_masks[1]=71;channel.step_velocity_masks[1]=91;channel.step_length_masks[1]=4 end
 if mask_mode==3 then channel.note_mask=70;channel.velocity_mask=88;channel.length_mask=2 end
 local note_mode=field=='note' and 'pattern_number_'..priority or 'average'
 local velocity_mode=field=='velocity' and 'pattern_number_'..priority or 'average'
 local length_mode=field=='length' and 'pattern_number_'..priority or 'average'
 local result=Pattern.get_and_merge_patterns(1,mode,note_mode,velocity_mode,length_mode)
 for step=1,64 do
   local note=field=='note' and source.note_values[step] or 0
   local velocity=field=='velocity' and source.velocity_values[step] or 100
   local length=field=='length' and source.lengths[step] or 1
   local note_mask=-1
   if mask_mode==3 then note_mask=70;velocity=88;length=2 end
   if mask_mode>=2 and step==1 then note_mask=71;velocity=91;length=4 end
   assert(result.note_values[step]==note and result.velocity_values[step]==velocity and result.lengths[step]==length,
     'Priority '..field..' from slot'..priority..' overwritten by rhythm slot'..rhythm_slot..' at step'..step..' mode '..mode)
   assert(result.note_mask_values[step]==note_mask,'Mask precedence changed')
   assert(result.trig_values[step]==(mode=='only' and 0 or 1),'Trig merge behavior changed')
   checked=checked+1
 end
end end end end end end end
-- Legacy callers disable unrelated modes with false or omit them entirely.
for _,modes in ipairs({{}, {false,false,false}, {'average',false,false}, {false,'average',false}, {false,false,'average'}}) do
 channel={selected_patterns={[2]=true},step_trig_masks={},step_note_masks={},step_velocity_masks={},step_length_masks={}}
 song={patterns={[2]=rhythm},channels={[1]=channel}}
 local result=Pattern.get_and_merge_patterns(1,'skip',modes[1],modes[2],modes[3])
 for step=1,64 do
   assert(result.note_values[step]==0 and result.velocity_values[step]==100 and result.lengths[step]==1,'Disabled/omitted merge mode changed')
   checked=checked+1
 end
end
print(checked..' priority/mask merged-cell checks passed across all distinct slot pairs, trig modes and fields')
