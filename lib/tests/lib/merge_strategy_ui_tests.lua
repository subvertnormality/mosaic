-- Characterisation authorized 3 October 2026: one effective merge strategy
-- selector across grid/norns, truthful boundary feedback and refusal cursor.
local strategy = include("mosaic/lib/musical_merge/strategy")
local config = include("mosaic/lib/musical_merge/config")
local state = include("mosaic/lib/musical_merge/state")
local function fixture()
  state.reset()
  local channel = {number=1, trig_merge_mode="all", note_merge_mode="up", velocity_merge_mode="down", length_merge_mode="pattern_number_2", musical_merge=config.new()}
  local song = {channels={[1]=channel}}
  return song, channel
end
function test_merge_strategy_ui_five_choices_clamp_and_grid_wrap()
  local song, channel = fixture()
  luaunit.assert_equals(strategy.choices,{"skip","only","all","foundation","fragments"})
  luaunit.assert_equals(strategy.step(song,channel,126,false),"foundation")
  strategy.request(song,channel,"fragments",function()return false,"INVALID"end)
  luaunit.assert_equals(strategy.step(song,channel,1,false),"fragments")
  luaunit.assert_equals(strategy.step(song,channel,1,true),"skip")
end
function test_merge_strategy_ui_refused_foundation_advances_without_false_active_or_pending()
  local song, channel = fixture()
  local ok = strategy.request(song,channel,"foundation",function()return false,"INVALID merge anchor"end)
  luaunit.assert_false(ok)
  local shown = strategy.snapshot(song,channel)
  luaunit.assert_equals(shown.selected,"foundation")
  luaunit.assert_equals(shown.active,"all")
  luaunit.assert_nil(shown.pending)
  luaunit.assert_equals(shown.error,"NEEDS ANCHOR")
  luaunit.assert_equals(strategy.step(song,channel,1,false),"fragments")
  luaunit.assert_equals(strategy.step(song,channel,1,true),"fragments")
  luaunit.assert_equals(channel.trig_merge_mode,"all")
  luaunit.assert_nil(state.peek(song,1)) -- presenting the cursor cannot create runtime state
end
function test_merge_strategy_ui_pending_boundary_is_actual_not_cursor_and_preserves_saved_modes()
  local song, channel = fixture()
  state.effective(song,1,channel.musical_merge)
  local next_config=config.new();next_config.mode="foundation";next_config.anchor=1
  strategy.request(song,channel,"foundation",function()
    state.request(song,1,next_config,true);channel.musical_merge=next_config;return true,"NEXT CYCLE"
  end)
  local shown=strategy.snapshot(song,channel)
  luaunit.assert_equals(shown.active,"all");luaunit.assert_equals(shown.pending,"foundation")
  luaunit.assert_equals(shown.boundary,"NEXT CYCLE")
  luaunit.assert_false(strategy.owned(song,channel,"note"))
  state.on_cycle_boundary(song,1,next_config)
  luaunit.assert_equals(strategy.snapshot(song,channel).active,"foundation")
  luaunit.assert_nil(strategy.snapshot(song,channel).pending)
  luaunit.assert_true(strategy.owned(song,channel,"trig"))
  luaunit.assert_false(strategy.owned(song,channel,"velocity"))
  luaunit.assert_equals(channel.note_merge_mode,"up")
  luaunit.assert_equals(channel.velocity_merge_mode,"down")
  luaunit.assert_equals(channel.length_merge_mode,"pattern_number_2")
end
function test_merge_strategy_ui_global_queue_retains_next_pattern_boundary_and_refusal_keeps_queue()
  local song,channel=fixture();state.effective(song,1,channel.musical_merge)
  local queued=config.new();queued.mode="fragments"
  state.request_global(song,1,queued,true);channel.musical_merge=queued
  strategy.request(song,channel,"foundation",function()return false,"INVALID anchor not assigned"end)
  local shown=strategy.snapshot(song,channel)
  luaunit.assert_equals(shown.selected,"foundation");luaunit.assert_equals(shown.active,"all")
  luaunit.assert_equals(shown.pending,"fragments");luaunit.assert_equals(shown.boundary,"NEXT PATTERN")
  luaunit.assert_equals(shown.error,"NEEDS ANCHOR")
end
function test_merge_strategy_ui_external_accepted_change_resets_refused_cursor()
  local song,channel=fixture()
  strategy.request(song,channel,"foundation",function()return false,"INVALID merge anchor"end)
  channel.trig_merge_mode="only"
  luaunit.assert_equals(strategy.snapshot(song,channel).selected,"only")
  luaunit.assert_nil(strategy.snapshot(song,channel).error)
end

local isolation=include("mosaic/lib/tests/helpers/ui_adapters_isolation")
local function real_page()
  fader=include("mosaic/lib/controls/fader")
  button=include("mosaic/lib/controls/button")
  tooltip={show=function()end}
  program.init();globals.reset();params.reset();m_clock.init();state.reset()
  program.set_selected_song_pattern(1)
  local page=include("mosaic/lib/pages/channel_edit_page/channel_edit_page")
  return page,program.get_selected_song_pattern(),program.get_selected_channel()
end
function test_merge_strategy_ui_real_owner_refuses_missing_anchor_then_applies_fragments()
  isolation.isolated({},function()
  local page,song,channel=real_page()
  channel.trig_merge_mode="all";channel.note_merge_mode="up"
  local ok,reason=page.set_merge_strategy("foundation")
  luaunit.assert_false(ok);luaunit.assert_equals(reason,"NEEDS ANCHOR")
  luaunit.assert_equals(channel.trig_merge_mode,"all")
  luaunit.assert_equals(strategy.snapshot(song,channel).active,"all")
  luaunit.assert_true(page.set_merge_strategy(strategy.step(song,channel,1,true)))
  luaunit.assert_equals(strategy.snapshot(song,channel).active,"fragments")
  luaunit.assert_equals(channel.note_merge_mode,"up")
  luaunit.assert_false(page.set_merge_mode("note","down"))
  luaunit.assert_equals(channel.note_merge_mode,"up")
  luaunit.assert_true(page.set_merge_strategy("skip"))
  luaunit.assert_equals(strategy.snapshot(song,channel).active,"skip")
  luaunit.assert_equals(channel.note_merge_mode,"up")
  end)
end
function test_merge_strategy_ui_real_owner_queues_and_disables_shape_at_existing_boundary()
  isolation.isolated({},function()
  local page,song,channel=real_page()
  channel.trig_merge_mode="all";channel.selected_patterns[1]=true
  channel.musical_merge=config.new();channel.musical_merge.anchor=1
  state.effective(song,channel.number,channel.musical_merge)
  local live_clock=m_clock
  m_clock=setmetatable({is_playing=function()return true end},{__index=live_clock})
  local ok,status=page.set_merge_strategy("foundation")
  luaunit.assert_true(ok);luaunit.assert_equals(status,"NEXT CYCLE")
  luaunit.assert_equals(strategy.snapshot(song,channel).active,"all")
  luaunit.assert_equals(strategy.snapshot(song,channel).pending,"foundation")
  state.on_cycle_boundary(song,channel.number,channel.musical_merge)
  luaunit.assert_equals(strategy.snapshot(song,channel).active,"foundation")
  luaunit.assert_true(page.set_merge_strategy("only"))
  luaunit.assert_equals(strategy.snapshot(song,channel).active,"foundation")
  luaunit.assert_equals(strategy.snapshot(song,channel).pending,"only")
  state.on_cycle_boundary(song,channel.number,channel.musical_merge)
  luaunit.assert_equals(strategy.snapshot(song,channel).active,"only")
  luaunit.assert_equals(channel.musical_merge.anchor,1)
  m_clock=live_clock
  end)
end
