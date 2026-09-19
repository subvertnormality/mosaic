local merge_config = include("mosaic/lib/musical_merge/config")
local merge_state = include("mosaic/lib/musical_merge/state")
local harmony_config = include("mosaic/lib/harmony/config")
local harmony_config_state = include("mosaic/lib/harmony/config_state")
local harmony_state = include("mosaic/lib/harmony/state")
local harmony_inspection=include("mosaic/lib/harmony/inspection")
local harmony_context = include("mosaic/lib/harmony/context")
local pattern_harmony = include("mosaic/lib/harmony/pattern")
local optional_transaction=include("mosaic/lib/optional_config_transaction")

-- Transactional controller for the two appended Channel pages. Rendering is
-- intentionally native and small; musical state changes only in apply().
local editor = {}

local function copy(value, seen)
  if type(value) ~= "table" then return value end
  seen = seen or {}
  if seen[value] then return seen[value] end
  local result = {}; seen[value] = result
  for key, item in pairs(value) do result[copy(key, seen)] = copy(item, seen) end
  return result
end

local function clamp(value, low, high) return math.max(low, math.min(high, value)) end
local function direction(delta) return delta >= 0 and 1 or -1 end
local function cycle(values, current, delta)
  if #values == 0 then return current end
  local index
  for i, value in ipairs(values) do if value == current then index = i break end end
  if not index then return values[direction(delta) > 0 and 1 or #values] end
  index = index + direction(delta)
  if index < 1 then index = #values elseif index > #values then index = 1 end
  return values[index]
end

local function current_song_channel()
  local song = program.get_selected_song_pattern()
  local selected=program.get().selected_channel
  if type(song)~="table"then
    local song_number=song;local synthetic={channels={},voicing=nil}
    for number=1,17 do synthetic.channels[number]=program.get_channel(song_number,number)end
    return synthetic,synthetic.channels[selected]
  end
  return song, song.channels[selected]
end

local function editable(label, getter, setter, options)
  options = options or {}; options.label, options.get, options.set = label, getter, setter
  return options
end
local function action(label, route, options)
  options = options or {}; options.label, options.route, options.action = label, route, true
  return options
end
local function readonly(label, getter, options)
  options = options or {}; options.label, options.get, options.readonly = label, getter, true
  return options
end

local function field_value(field)
  local value = field.get and field.get() or field.value
  if value == nil then return "NONE" end
  if type(value) == "boolean" then return value and "ON" or "OFF" end
  return tostring(value):upper()
end

local function edit_field(field, delta)
  if field.readonly or field.action then return false end
  local current, value = field.get()
  if field.boolean then value = not current
  elseif field.values then value = cycle(field.values, current, delta)
  else value = clamp((current or field.min or 0) + direction(delta), field.min, field.max) end
  field.set(value); return true
end

local function assigned_patterns(channel)
  local result = {}
  for number, enabled in pairs(channel.selected_patterns or {}) do if enabled then result[#result + 1] = number end end
  table.sort(result); return result
end

local function degree_inventory(channel)
  if type(program.get_scale)~="function"then return{}end
  local scale_number=channel.step_scale_number or program.get().default_scale or 1
  return harmony_context.scale_pitch_classes(scale_number,0)
end

local function degree_source_key(channel)
  return table.concat(degree_inventory(channel),",")
end

function editor.new(kind)
  local self = {kind=kind, screen=kind=="merge"and"M01"or"H01", selected=1,
    stack={}, dirty=false, status="", selected_step=1, selected_group=1, selected_role=1}

  local function channel_config() return self.kind=="merge"and self.draft or self.channel_drafts[self.channel_number] end
  local function groups()
    self.song_draft=self.song_draft or{schema_version=1,groups={}}
    self.song_draft.groups=self.song_draft.groups or{}; return self.song_draft.groups
  end
  local function group() return groups()[self.selected_group] end
  local function mark_dirty() self.dirty,self.status=true,"DRAFT ALL" end
  local function open(route)
    self.stack[#self.stack+1]={screen=self.screen,selected=self.selected}
    self.screen,self.selected,self.status=route,1,""
  end
  local function back()
    local parent=table.remove(self.stack)
    if parent then self.screen,self.selected=parent.screen,parent.selected;if parent.screen=="H01"then self.context_group=false end end
    return parent~=nil
  end

  local function merge_fields()
    local value=self.draft
    if self.screen=="M01"then return{
      editable("Mode",function()return value.mode end,function(v)value.mode=v end,{values={"off","foundation"}}),
      action("Rhythm","M02"),action("Phrase","M04"),action("Pitch","M05"),action("Result","M07")}
    elseif self.screen=="M02"then return{
      editable("Anchor",function()return value.anchor end,function(v)value.anchor=v end,{values=assigned_patterns(self.channel)}),
      editable("Add amount",function()return value.amount end,function(v)value.amount=v end,{min=0,max=100}),
      action("Amount detail","M03"),
      editable("Add accent",function()return value.accent end,function(v)value.accent=v end,{min=0,max=100}),
      editable("Anchor gap",function()return value.gap end,function(v)value.gap=v end,{min=0,max=8}),
      editable("Seed",function()return value.seed end,function(v)value.seed=v end,{min=0,max=65535})}
    elseif self.screen=="M03"then return{
      editable("Add amount",function()return value.amount end,function(v)value.amount=v end,{min=0,max=100}),
      readonly("Eligible",function()local f=self.channel.working_pattern and self.channel.working_pattern.foundation;return f and f.eligible_count or 0 end),
      readonly("Admitted",function()local f=self.channel.working_pattern and self.channel.working_pattern.foundation;return f and f.admitted_count or 0 end)}
    elseif self.screen=="M04"then
      local fields={
        editable("Cycles",function()return value.cycles end,function(v)
          value.cycles=v;if value.shape~="custom"then value.percentages=merge_config.curve(value.shape,v)else
            local p={};for i=1,v do p[i]=value.percentages[i]or 100 end;value.percentages=p end
        end,{values={1,2,4,8}}),
        editable("Shape",function()return value.shape end,function(v)value.shape=v;if v~="custom"then value.percentages=merge_config.curve(v,value.cycles)end end,
          {values={"flat","build","answer","fill","custom"}})}
      for index=1,value.cycles do fields[#fields+1]=editable("Cycle "..index,function()return value.percentages[index]end,
        function(v)value.percentages[index]=v;value.shape="custom"end,{min=0,max=100})end
      fields[#fields+1]=editable("Variation",function()return value.variation end,function(v)value.variation=v end,{values={"fixed","per_phrase"}})
      return fields
    elseif self.screen=="M05"then return{
      editable("Keep anchor",function()return value.keep_anchor_pitch end,function(v)value.keep_anchor_pitch=v end,{boolean=true}),
      editable("Add target",function()return value.target.kind end,function(v)value.target={kind=v};if v=="degrees"then value.target.degrees={1}end end,
        {values={"legacy","scale","degrees","chord"}}),
      action("Target setup","M06"),action("Voice leading","HARMONY_LINK")}
    elseif self.screen=="M06"then
      if value.target.kind=="degrees"then
        local inventory=harmony_context.scale_pitch_classes(self.channel.step_scale_number or program.get().default_scale or 1,0)
        local selected={};for _,v in ipairs(value.target.degrees or{})do selected[v]=true end
        local fields={};for degree=1,#inventory do fields[#fields+1]=editable("Degree "..degree,function()return selected[degree]or false end,
          function(on)selected[degree]=on;local d={};for i=1,#inventory do if selected[i]then d[#d+1]=i end end;value.target.degrees=d end,{boolean=true})end
        return fields
      elseif value.target.kind=="chord"then
        local ids={};for id,g in pairs((self.song.voicing and self.song.voicing.groups)or{})do if g.enabled then ids[#ids+1]=id end end;table.sort(ids)
        return{editable("Harmony source",function()return value.target.group_id end,function(v)value.target.group_id=v end,{values=ids})}
      end
      return{readonly("Target",function()return value.target.kind end),readonly("Scope",function()return"ADDITIONS"end)}
    elseif self.screen=="M07"then
      local f=self.channel.working_pattern and self.channel.working_pattern.foundation
      return{editable("Step",function()return self.selected_step end,function(v)self.selected_step=v end,{min=1,max=64}),
        readonly("Role",function()return f and f.roles and f.roles[self.selected_step]or"EMPTY"end),
        readonly("Decision",function()return f and f.reasons and f.reasons[self.selected_step]or(f and f.status)or"LEGACY"end),action("Reason","M08")}
    elseif self.screen=="M08"then
      local f=self.channel.working_pattern and self.channel.working_pattern.foundation
      return{readonly("Step",function()return self.selected_step end),readonly("Role",function()return f and f.roles and f.roles[self.selected_step]or"EMPTY"end),
        readonly("Sources",function()local s=f and f.sources and f.sources[self.selected_step];return s and table.concat(s,",")or"NONE"end),
        readonly("Decision",function()return f and f.reasons and f.reasons[self.selected_step]or(f and f.status)or"ADMITTED"end),
        readonly("Velocity",function()return f and f.velocities and f.velocities[self.selected_step]end),readonly("Pitch target",function()return value.target.kind end)}
    elseif self.screen=="M09"then return{readonly("Merge gesture",function()return self.gesture or"NONE"end),
      readonly("Shape",function()return value.mode=="foundation"and"FOUNDATION ACTIVE"or"LEGACY"end)}end
    return{}
  end

  local function selected_role()
    local value=channel_config()
    if self.context_group and group()then
      local names=harmony_config.member_roles(#group().members);local name=names[self.selected_role]or names[1]
      return name,group().roles[name]
    end
    local name="v"..self.selected_role;return name,value.roles[name]
  end
  local function selected_bass()return self.context_group and group()and group().bass or channel_config().bass end
  local function select_ensemble_group(value)
    if value.mode=="ensemble"and value.group_id and groups()[value.group_id]then
      self.selected_group=value.group_id;self.context_group=true
    else self.context_group=false end
  end
  local function tone_values(value)
    if self.context_group then
      local values={};for index=1,#((group()and group().template.offsets)or{})do values[index]="tone"..index end
      return values
    end
    local values={"root"};local masks={self.channel.chord_one_mask,self.channel.chord_two_mask,
      self.channel.chord_three_mask,self.channel.chord_four_mask}
    for index=1,4 do
      local present=masks[index]and masks[index]~=0
      for _,step_masks in pairs(self.channel.step_chord_masks or{})do
        if step_masks[index]and step_masks[index]~=0 then present=true break end
      end
      if present then values[#values+1]="chord"..index end
    end
    return values
  end

  local function harmony_fields()
    local value=channel_config()
    if self.screen=="H01"then
      local ensemble=value.mode=="ensemble"and value.group_id and groups()[value.group_id]
      local function in_owner(action_options)
        action_options=action_options or{};action_options.before=function()select_ensemble_group(value)end;return action_options
      end
      local fields={editable("Mode",function()return value.mode end,function(v)local prior=value.mode;value.mode=v;if v=="pattern"then if prior=="off"then value.crossing=true end;value.bass.mode="smooth";value.bass.non_chord_pedal=false end end,{values={"off","revoice","pattern","ensemble"}})}
      if value.mode=="ensemble"then
        fields[#fields+1]=editable("Group",function()return value.group_id or 0 end,function(v)value.group_id=v==0 and nil or v end,{min=0,max=16})
      else fields[#fields+1]=readonly("Group",function()return"NOT USED"end)end
      if value.mode=="off"then fields[#fields+1]=readonly("Preset",function()return"NOT USED"end)
      else fields[#fields+1]=editable("Preset",function()return ensemble and ensemble.preset or value.preset end,
        function(v)if ensemble then ensemble.preset=v else value.preset=v end end,{values={"smooth","compact","independent"}})end
      if value.mode=="pattern"then fields[#fields+1]=action("Tone Map","TONE_MAP")end
      fields[#fields+1]=action("Register","H02",in_owner())
      fields[#fields+1]=action("Bass","H03",in_owner())
      fields[#fields+1]=action("Groups","H04")
      fields[#fields+1]=action("Rules","H08",in_owner())
      fields[#fields+1]=action("Entry","H09",in_owner())
      fields[#fields+1]=action("Result","H05",in_owner())
      return fields
    elseif self.screen=="H02"then
      local names=self.context_group and group()and harmony_config.member_roles(#group().members)or{"v1","v2","v3","v4","v5"}
      local name,role=selected_role()
      return{editable("Role",function()return name end,function(v)for i,n in ipairs(names)do if n==v then self.selected_role=i end end end,{values=names}),
        editable("Low",function()return role.min end,function(v)role.min=v end,{min=0,max=127}),
        editable("High",function()return role.max end,function(v)role.max=v end,{min=0,max=127}),
        editable("Centre",function()return role.centre end,function(v)role.centre=v end,{min=0,max=127}),
        editable("Preferred leap",function()return role.preferred_leap end,function(v)role.preferred_leap=v end,{min=0,max=127}),
        editable("Strict leap",function()return role.strict_leap end,function(v)role.strict_leap=v end,{boolean=true})}
    elseif self.screen=="H03"then
      local bass=selected_bass()
      if not self.context_group and value.mode=="pattern"then return{
        readonly("Mode",function()return"SMOOTH OCTAVE"end),
        editable("Direction",function()return bass.direction end,function(v)bass.direction=v end,{values={"nearest","ascending","descending"}}),
        editable("Strict direction",function()return bass.strict_direction end,function(v)bass.strict_direction=v end,{boolean=true}),
        action("Bass register","H02",{before=function()self.selected_role=1 end})}
      end
      local fields={
        editable("Mode",function()return bass.mode end,function(v)bass.mode=v end,{values={"root","inversion","smooth","pedal"}}),
        editable("Direction",function()return bass.direction end,function(v)bass.direction=v end,{values={"nearest","ascending","descending"}}),
        editable("Strict direction",function()return bass.strict_direction end,function(v)bass.strict_direction=v end,{boolean=true}),
        editable("Pedal pitch",function()return bass.pedal end,function(v)bass.pedal=v end,{min=0,max=127}),
        editable("Non-chord pedal",function()return bass.non_chord_pedal end,function(v)bass.non_chord_pedal=v end,{boolean=true}),
        action("Bass register","H02",{before=function()self.selected_role=1 end})}
      if bass.mode=="inversion"then table.insert(fields,2,editable("Tone",function()return bass.tone_id end,
        function(v)bass.tone_id=v end,{values=tone_values(value)}))end
      return fields
    elseif self.screen=="H04"then
      local ids={};for id in pairs(groups())do ids[#ids+1]=id end;table.sort(ids)
      local fields={editable("Group",function()return self.selected_group end,function(v)self.selected_group=v;self.context_group=true end,{values=ids}),
        action("Create group",nil,{invoke=function()local id=1;while groups()[id]do id=id+1 end;if id>16 then self.status="INVALID GROUP LIMIT";return end
          groups()[id]=harmony_config.new_group(self.channel_number);self.selected_group=id;self.context_group=true;mark_dirty()end})}
      if group()then
        fields[#fields+1]=action("Four-part smooth",nil,{invoke=function()groups()[self.selected_group]=harmony_config.four_part_smooth(self.selected_group,{});mark_dirty()end})
        fields[#fields+1]=action("Members","H07",{before=function()self.context_group=true end})
        fields[#fields+1]=action("Source","H10",{before=function()self.context_group=true end})
        fields[#fields+1]=action("Policies","H08",{before=function()self.context_group=true end})
        fields[#fields+1]=action("Entry","H09",{before=function()self.context_group=true end})
        fields[#fields+1]=action("Result","H05",{before=function()self.context_group=true end})
        fields[#fields+1]=action("Delete group","H04_DELETE")
      end;return fields
    elseif self.screen=="H04_DELETE"then
      local affected={};for number,c in pairs(self.channel_drafts)do if c.group_id==self.selected_group then affected[#affected+1]=number end end;table.sort(affected)
      return{readonly("Delete group",function()return self.selected_group end),readonly("Affected",function()return table.concat(affected,",")end),
        action("Confirm delete",nil,{invoke=function()
          local deleted=self.selected_group;groups()[deleted]=nil
          for _,number in ipairs(affected)do self.channel_drafts[number].mode="off";self.channel_drafts[number].group_id=nil end
          for number,merge in pairs(self.merge_drafts)do if merge and merge.target and merge.target.kind=="chord"and merge.target.group_id==deleted then merge.target={kind="legacy"};self.merge_changed[number]=true end end
          mark_dirty();self:apply();back()
        end})}
    elseif self.screen=="H07"then
      local g=group();if not g then return{readonly("Group",function()return"NONE"end)}end
      local fields={editable("Voice count",function()return #g.members end,function(count)
        local old={};for _,m in ipairs(g.members)do old[m.role]=m.channel end;local default=harmony_config.new_group(self.channel_number).roles.bass
        g.members={};local new_roles={};for _,name in ipairs(harmony_config.member_roles(count))do g.members[#g.members+1]={role=name,channel=old[name]};new_roles[name]=g.roles[name]or copy(default)end;g.roles=new_roles
      end,{min=1,max=5})}
      for _,member in ipairs(g.members)do fields[#fields+1]=editable(member.role,function()return member.channel or 0 end,function(v)member.channel=v==0 and nil or v end,{min=0,max=16})end
      fields[#fields+1]=editable("Group enabled",function()return g.enabled end,function(v)g.enabled=v end,{boolean=true});return fields
    elseif self.screen=="H08"then
      local policy=self.context_group and group()or value;local fields={
        editable("Crossing",function()return policy.crossing end,function(v)policy.crossing=v end,{boolean=true})}
      if self.context_group then fields[#fields+1]=editable("Pitch-class doubling",function()return policy.pitch_class_doubling~=false end,function(v)policy.pitch_class_doubling=v end,{boolean=true})
      else fields[#fields+1]=readonly("Pitch-class doubling",function()return"FIXED INPUT"end)end
      local tail={
        editable("Exact unison",function()return policy.exact_unison end,function(v)policy.exact_unison=v end,{boolean=true}),
        editable("Common tones",function()return policy.common_tone_priority end,function(v)policy.common_tone_priority=v end,{boolean=true}),
        editable("Upper spacing",function()return policy.upper_spacing or 12 end,function(v)policy.upper_spacing=v end,{min=0,max=127}),
        editable("Bass separation",function()return policy.bass_separation or 5 end,function(v)policy.bass_separation=v end,{min=0,max=127})}
      for _,field in ipairs(tail)do fields[#fields+1]=field end
      if self.context_group then fields[#fields+1]=action("Coverage","H10")
      else fields[#fields+1]=readonly("Coverage",function()return"FIXED INPUT"end)end
      return fields
    elseif self.screen=="H09"then local policy=self.context_group and group()or value;local fields={readonly("Start",function()return"ANCHOR"end),
      editable("Song transition",function()return policy.transition end,function(v)policy.transition=v end,{values={"anchor","continue"}}),
      editable("Same-slot repeat",function()return policy.repeat_policy end,function(v)policy.repeat_policy=v end,{values={"continue","anchor"}}),
      editable("Failure fallback",function()return policy.fallback end,function(v)policy.fallback=v end,{values={"silence","legacy"}})}
      if not self.context_group then fields[#fields+1]=editable("Absolute pitch",function()return value.absolute_pitch_policy end,function(v)value.absolute_pitch_policy=v end,{values={"pin","allow_octave_move"}})end
      return fields
    elseif self.screen=="H10"then
      local g=group();if not g then return{readonly("Source",function()return"NO GROUP"end)}end
      local fields={editable("Source kind",function()return g.source.kind end,function(v)g.source.kind=v;if v=="scale_slot"then g.source.scale_slot=g.source.scale_slot or 1 end end,{values={"global_effective","scale_slot"}})}
      if g.source.kind=="scale_slot"then fields[#fields+1]=editable("Scale slot",function()return g.source.scale_slot end,function(v)g.source.scale_slot=v end,{min=1,max=16})end
      fields[#fields+1]=editable("Template count",function()return #g.template.offsets end,function(count)for i=#g.template.offsets+1,count do g.template.offsets[i]=0;g.template.required[i]=false end;while #g.template.offsets>count do table.remove(g.template.offsets);table.remove(g.template.required)end end,{min=1,max=5})
      fields[#fields+1]=readonly("Root offset",function()return 0 end)
      for index=2,#g.template.offsets do fields[#fields+1]=editable("Tone "..index,function()return g.template.offsets[index]end,function(v)g.template.offsets[index]=v end,{min=-14,max=14})end
      for index=1,#g.template.required do fields[#fields+1]=editable("Required "..index,function()return g.template.required[index]end,function(v)g.template.required[index]=v end,{boolean=true})end
      return fields
    elseif self.screen=="TONE_MAP"then
      local binding=pattern_harmony.binding_key(self.channel)
      local map=value.pattern_maps[binding]or{schema_version=1,revision=0,assignments={}}
      local seen,values={},{}
      for _,raw in ipairs((self.channel.working_pattern and self.channel.working_pattern.note_values)or{})do if raw~=nil and not seen[raw]then seen[raw]=true;values[#values+1]=raw end end
      for raw in pairs(map.assignments)do local n=tonumber(raw);if not seen[n]then values[#values+1]=n end end;table.sort(values)
      local fields={};for _,raw in ipairs(values)do fields[#fields+1]=editable("Tone "..raw,function()return map.assignments[tostring(raw)]or"raw"end,
        function(v)value.pattern_maps[binding]=map;if v=="raw"then map.assignments[tostring(raw)]=nil else map.assignments[tostring(raw)]=v end;map.revision=(map.revision or 0)+1 end,{values={"raw","bass","inner1","inner2","inner3","top"}})end
      fields[#fields+1]=action("Reset map","TONE_MAP_RESET");return fields
    elseif self.screen=="TONE_MAP_RESET"then
      local binding=pattern_harmony.binding_key(self.channel)
      return{readonly("Reset map",function()return binding end),
        action("Confirm reset",nil,{invoke=function()
          local map=value.pattern_maps[binding]or{schema_version=1,revision=0,assignments={}}
          value.pattern_maps[binding]=map;map.assignments={};map.revision=(map.revision or 0)+1
          mark_dirty();back()
        end})}
    elseif self.screen=="H05"then
      local snapshot=harmony_state.snapshot(self.song)
      local active_song=harmony_config_state.effective_song(self.song,self.song.voicing or{schema_version=1,groups={}})
      local selected_group=self.context_group and active_song.groups[self.selected_group]
      local result;if self.context_group then result=(snapshot.groups[self.selected_group]or{}).prepared
      else result=(snapshot.channels[self.channel_number]or{}).prepared end
      local traces={};if selected_group then for _,member in ipairs(selected_group.members or{})do traces[#traces+1]={channel=member.channel,role=member.role,trace=harmony_inspection.snapshot(self.song,member.channel)}end
      else traces[1]={channel=self.channel_number,trace=harmony_inspection.snapshot(self.song,self.channel_number)}end
      local active_plan;for _,entry in ipairs(traces)do if entry.trace.planned then active_plan=entry.trace.planned break end end
      local fields={readonly("Status",function()
        for _,entry in ipairs(traces)do if entry.trace.planned and entry.trace.planned.bypass then return"BYPASS "..tostring(entry.trace.planned.bypass)end end
        for _,entry in ipairs(traces)do local status=entry.trace.planned and entry.trace.planned.status
          if status and status~="ok"and status~="off"then return"NO VOICING"end end
        if not result then return"NO RESULT"end
        return result.status=="ok"and"OK"or"NO VOICING"
      end)}
      if result and result.role_pitches then for role,pitch in pairs(result.role_pitches)do local p=pitch;fields[#fields+1]=readonly(role,function()return p end)end end
      for _,entry in ipairs(traces)do local item=entry
        fields[#fields+1]=readonly((item.role or("CH"..item.channel)).." planned",function()return item.trace.planned and item.trace.planned.output end)
        fields[#fields+1]=readonly((item.role or("CH"..item.channel)).." emitted",function()return item.trace.emitted and item.trace.emitted.pitch end)
      end
      if(result and result.status~="ok")or(active_plan and active_plan.status~="ok")then
        fields[#fields+1]=action("Failure details","H06")
      end;return fields
    elseif self.screen=="H06"then
      local snapshot=harmony_state.snapshot(self.song);local active_song=harmony_config_state.effective_song(self.song,self.song.voicing or{schema_version=1,groups={}})
      local selected_group=self.context_group and active_song.groups[self.selected_group]
      local result;if self.context_group then result=(snapshot.groups[self.selected_group]or{}).prepared
      else result=(snapshot.channels[self.channel_number]or{}).prepared end
      local trace=not self.context_group and harmony_inspection.snapshot(self.song,self.channel_number)or nil
      local effective=not self.context_group and harmony_config_state.effective_channel(self.song,self.channel_number,
        self.channel.voicing or harmony_config.new_channel())or nil
      return{readonly("Reason",function()return(result and result.reason)or
          (trace and trace.planned and(trace.planned.reason or trace.planned.status))or"NO VOICING"end),
        readonly("Fallback",function()return(trace and trace.planned and trace.planned.fallback)or
          (selected_group and selected_group.fallback)or(effective and effective.fallback)or"silence"end),action("Settings","H02")}
    end;return{}
  end

  function self:reload()
    local song,channel=current_song_channel();self.song,self.channel,self.channel_number=song,channel,channel.number
    if self.kind=="merge"then
      local effective=merge_state.effective(song,channel.number,channel.musical_merge or merge_config.new())
      self.draft=copy(effective.queued or channel.musical_merge or merge_config.new())
    else
      harmony_config_state.effective_song(song,song.voicing or{schema_version=1,groups={}})
      self.song_draft=copy(song.voicing or{schema_version=1,groups={}});self.channel_drafts={};self.merge_drafts={};self.merge_changed={}
      for number=1,16 do
        local current_voicing=song.channels[number].voicing or harmony_config.new_channel()
        harmony_config_state.effective_channel(song,number,current_voicing)
        self.channel_drafts[number]=copy(current_voicing);self.merge_drafts[number]=copy(song.channels[number].musical_merge)
        if self.merge_drafts[number]then merge_state.effective(song,number,self.merge_drafts[number])end
      end
      self.draft=self.channel_drafts[self.channel_number]
    end;self.before_snapshot=optional_transaction.snapshot(song);self.degree_source_key=degree_source_key(channel);self.dirty=false
  end
  function self:enter()self.screen=self.kind=="merge"and"M01"or"H01";self.selected=1;self.stack={};self.context_group=false;self.status="";self:reload()end
  function self:get_fields()return self.kind=="merge"and merge_fields()or harmony_fields()end
  function self:get_screen()return self.screen end
  function self:enc(n,delta)
    local fields=self:get_fields();if #fields==0 then return end
    if n==2 then self.selected=clamp(self.selected+direction(delta),1,#fields)
    elseif n==3 then if edit_field(fields[self.selected],delta)then mark_dirty()end end;fn.dirty_screen(true)
  end
  function self:apply()
    if not self.dirty then self.status="UNCHANGED";return true end
    local song,channel=current_song_channel();local playing=m_clock and m_clock.is_playing and m_clock.is_playing()or false
    local live=optional_transaction.snapshot(song)
    if not optional_transaction.equivalent(live,self.before_snapshot)then self.status="INVALID STALE DRAFT";return false end
    if self.kind=="merge"then
      local ok,reason=merge_config.validate(self.draft)
      if ok and self.draft.target.kind=="degrees"then
        local inventory=degree_inventory(channel)
        if degree_source_key(channel)~=self.degree_source_key then ok,reason=nil,"degree source changed"
        else for _,degree in ipairs(self.draft.target.degrees or{})do if inventory[degree]==nil then ok,reason=nil,"degree unavailable"break end end end
      end
      if ok and self.draft.mode=="foundation"and not channel.selected_patterns[self.draft.anchor]then ok,reason=nil,"anchor not assigned"end
      if ok and self.draft.target.kind=="chord"then local g=song.voicing and song.voicing.groups[self.draft.target.group_id];if not(g and g.enabled)then ok,reason=nil,"chord source unavailable"end end
      if not ok then self.status="INVALID "..tostring(reason);return false end
      local after=copy(self.before_snapshot);after.channels[channel.number].musical_merge=copy(self.draft)
      ok,reason=memory.record_optional_config(program.get().selected_song_pattern,{channel.number},self.before_snapshot,after,"channel")
      if not ok then self.status="INVALID "..tostring(reason);return false end
      self.status=playing and"NEXT CYCLE"or"APPLIED";self.before_snapshot=copy(after)
    else
      local after=copy(self.before_snapshot);after.voicing=copy(self.song_draft)
      local affected={};local set={}
      local function add(number)if number and not set[number]then set[number]=true;affected[#affected+1]=number end end
      for number=1,16 do
        after.channels[number].voicing=copy(self.channel_drafts[number]);after.channels[number].musical_merge=copy(self.merge_drafts[number])
        if not optional_transaction.equivalent(self.before_snapshot.channels[number],after.channels[number])then add(number)end
      end
      local function group_members(voicing)for _,g in pairs(voicing and voicing.groups or{})do for _,member in ipairs(g.members or{})do add(member.channel)end end end
      if not optional_transaction.equivalent(self.before_snapshot.voicing,after.voicing)then group_members(self.before_snapshot.voicing);group_members(after.voicing);add(self.channel_number)end
      local ok,reason=memory.record_optional_config(program.get().selected_song_pattern,affected,self.before_snapshot,after,"pattern")
      if not ok then self.status="INVALID "..tostring(reason);return false end
      self.status=playing and"NEXT PATTERN"or"APPLIED";self.before_snapshot=copy(after)
    end;self.dirty=false;return true
  end
  function self:key(n)
    if n==2 then if self.dirty then self:reload();self.status="DRAFT CANCELLED"end;if #self.stack>0 then back()end;return true
    elseif n==3 then local field=self:get_fields()[self.selected];if field and field.action then if field.before then field.before()end;if field.invoke then field.invoke()elseif field.route=="HARMONY_LINK"then self:reload();if channel_edit_page_ui and channel_edit_page_ui.select_harmony_page then channel_edit_page_ui.select_harmony_page()end elseif field.route then open(field.route)end;return true end;return self:apply()end
  end
  function self:encoder_one()
    if self.dirty then self:reload();self.status="DRAFT CANCELLED";self.stack={};self.screen=self.kind=="merge"and"M01"or"H01";self.selected=1;self.context_group=false;return true end
    if #self.stack>0 then self.stack={};self.screen=self.kind=="merge"and"M01"or"H01";self.selected=1;self.context_group=false;return true end;return false
  end
  function self:cancel_for_grid()
    if self.dirty then self:reload()end
    self.stack={};self.screen=self.kind=="merge"and"M01"or"H01";self.selected=1;self.context_group=false;self.status="DRAFT CANCELLED"
  end
  function self:show_merge_gesture(label)if self.kind=="merge"then if not self.gesture_depth or self.gesture_depth==0 then self.return_screen,self.return_selected=self.screen,self.selected end;self.gesture_depth=(self.gesture_depth or 0)+1;self.gesture=label;self.screen,self.selected="M09",1 end end
  function self:hide_merge_gesture()if self.screen=="M09"then self.gesture_depth=math.max(0,(self.gesture_depth or 1)-1);if self.gesture_depth==0 then self.screen,self.selected=self.return_screen or"M01",self.return_selected or 1;self.gesture=nil end end end
  function self:draw()
    if not self.draft then self:enter()end;local fields=self:get_fields();self.selected=clamp(self.selected,1,math.max(1,#fields));local first=math.max(1,math.min(self.selected-1,math.max(1,#fields-3)))
    screen.level(6);screen.move(2,17);screen.text(self.screen)
    screen.move(126,17);screen.text_right("CH"..string.format("%02d",self.channel_number or 1))
    for row=0,3 do local index=first+row;local field=fields[index];if field then screen.level(index==self.selected and 15 or 4);screen.move(2,27+row*9);screen.text(field.label.." "..(field.action and">"or field_value(field)))end end
    screen.level(6);screen.move(2,63);screen.text(self.status or"")
  end
  return self
end

return editor
