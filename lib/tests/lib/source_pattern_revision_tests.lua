-- RD-01/05 source revision characterisation outside README; PLAN.md Painting.
local function new_revisions()
  return include('mosaic/lib/source_pattern_revision').new()
end

function test_source_revision_reads_are_stable_and_edits_are_local()
  local revisions = new_revisions()
  local song = {patterns={{}, {}}}
  local first, second = revisions:get(song, 1), revisions:get(song, 2)
  luaunit.assertEquals(revisions:get(song, 1), first)
  revisions:edited(song, 1)
  luaunit.assertNotEquals(revisions:get(song, 1), first)
  luaunit.assertEquals(revisions:get(song, 2), second)
end

function test_source_revision_replacement_never_reuses_an_old_token()
  local revisions = new_revisions()
  local song = {patterns={{}}}
  local original = revisions:get(song, 1)
  song.patterns[1] = {}
  local copied = revisions:get(song, 1)
  luaunit.assertNotEquals(copied, original)
  luaunit.assertNotEquals(revisions:get({patterns={{}}}, 1), copied)
end

function test_source_revision_repeated_equal_edits_still_invalidate_history()
  local revisions = new_revisions()
  local song = {patterns={{}}}
  local initial = revisions:get(song, 1)
  revisions:edited(song, 1)
  local edited = revisions:get(song, 1)
  revisions:edited(song, 1)
  luaunit.assertNotEquals(initial, edited)
  luaunit.assertNotEquals(edited, revisions:get(song, 1))
end

function test_source_revision_tracking_does_not_mutate_serialized_project()
  local revisions = new_revisions()
  local source = {trig_values={1}, velocity_values={90}}
  local song = {patterns={source}}
  revisions:get(song, 1)
  revisions:edited(song, 1)
  luaunit.assertEquals(song, {patterns={{trig_values={1}, velocity_values={90}}}})
end

function test_source_revision_invalid_targets_fail_without_creating_patterns()
  local revisions = new_revisions()
  local song = {patterns={{}}}
  for _, invalid in ipairs({0, 17, 1.5, '1', false}) do
    luaunit.assertError(function() revisions:get(song, invalid) end)
  end
  luaunit.assertError(function() revisions:get(song, 2) end)
  luaunit.assertEquals(#song.patterns, 1)
end

function test_source_revision_actual_pattern_mutation_and_song_copy_boundaries()
  local pattern_under_test = include('mosaic/lib/pattern')
  program.init()
  local song = program.get_song_pattern(1)
  local token = pattern_under_test.get_source_revision(song, 1)
  local other = pattern_under_test.get_source_revision(song, 2)
  song.patterns[1].velocity_values[1] = 67
  pattern_under_test.update_source_working_patterns(song, 1)
  luaunit.assertNotEquals(pattern_under_test.get_source_revision(song, 1), token)
  luaunit.assertEquals(pattern_under_test.get_source_revision(song, 2), other)
  local edited = pattern_under_test.get_source_revision(song, 1)
  program.get_song_pattern(2)
  program.set_song_pattern(2, 1)
  luaunit.assertNotEquals(pattern_under_test.get_source_revision(program.get_song_pattern(1), 1), edited)
end

-- Actual editor callbacks, with only presentation/gesture registration stubbed.
-- This supplements public-input MIDI/grid behaviour, not a replacement for it.
local function with_revision_editor(name, body)
  local names = {'fader','button','sequencer','press','draw','grid_abstraction',
                 'pattern','tooltip','is_key1_down'}
  local saved = {}
  for i, key in ipairs(names) do saved[i] = rawget(_G, key) end
  local ok, err = pcall(function()
    program.init()
    fader = include('mosaic/lib/controls/fader')
    button = include('mosaic/lib/controls/button')
    sequencer = include('mosaic/lib/controls/sequencer')
    pattern = include('mosaic/lib/pattern')
    tooltip = {show=function() end}
    draw = {register_grid=function() end}
    grid_abstraction = {led=function() end}
    is_key1_down = false
    local handlers = {short={}, dual={}, long={}, pre={}, post={}}
    press = {
      register=function(_, _, callback) table.insert(handlers.short, callback) end,
      register_dual=function(_, _, callback) table.insert(handlers.dual, callback) end,
      register_long=function(_, _, callback) table.insert(handlers.long, callback) end,
      register_pre=function(_, _, callback) table.insert(handlers.pre, callback) end,
      register_post=function(_, _, callback) table.insert(handlers.post, callback) end,
    }
    local page = include('mosaic/lib/pages/' .. name .. '/' .. name)
    page.init()
    page.register_press()
    local function fire(kind, ...)
      for _, callback in ipairs(handlers[kind]) do callback(...) end
    end
    body(fire, program.get_selected_song_pattern(), pattern)
  end)
  for i = #names, 1, -1 do rawset(_G, names[i], saved[i]) end
  if not ok then error(err, 0) end
end

function test_source_revision_trigger_tap_length_and_legacy_paint_ingress()
  with_revision_editor('trigger_edit_page', function(fire, song, tracker)
    local unchanged = tracker.get_source_revision(song, 2)
    local function edit(kind, ...)
      local before = tracker.get_source_revision(song, 1)
      fire(kind, ...)
      luaunit.assertNotEquals(tracker.get_source_revision(song, 1), before)
      luaunit.assertEquals(tracker.get_source_revision(song, 2), unchanged)
    end
    edit('short', 1, 4)
    luaunit.assertEquals(song.patterns[1].trig_values[1], 1)
    edit('dual', 1, 4, 4, 4)
    luaunit.assertEquals(song.patterns[1].lengths[1], 4)
    edit('long', 1, 4)
    luaunit.assertEquals(song.patterns[1].lengths[1], 1)
    local before = tracker.get_source_revision(song, 1)
    fire('short', 16, 8) -- Preview never edits source.
    luaunit.assertEquals(tracker.get_source_revision(song, 1), before)
    edit('short', 16, 8)
  end)
end

local function assert_vertical_editor_revision(name, field)
  with_revision_editor(name, function(fire, song, tracker)
    local other = tracker.get_source_revision(song, 2)
    for _, key1 in ipairs({false, true}) do
      is_key1_down = key1
      local before = tracker.get_source_revision(song, 1)
      fire('short', 1, key1 and 4 or 3)
      luaunit.assertNotEquals(tracker.get_source_revision(song, 1), before)
      luaunit.assertEquals(tracker.get_source_revision(song, 2), other)
      if key1 then
        for _, step in ipairs({17,33,49}) do
          luaunit.assertEquals(song.patterns[1][field][step], song.patterns[1][field][1])
        end
      end
    end
  end)
end

function test_source_revision_note_single_and_parallel_steps_ingress()
  assert_vertical_editor_revision('note_edit_page', 'note_values')
end

function test_source_revision_velocity_single_and_parallel_steps_ingress()
  assert_vertical_editor_revision('velocity_edit_page', 'velocity_values')
end
