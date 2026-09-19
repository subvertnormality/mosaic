-- README.md Note Dashboard: planned, scheduled and last-emitted Harmony state
-- is read-only, source-labelled and shared by scheduler and renderer includes.
local writer=include("mosaic/lib/harmony/inspection")
local reader=include("mosaic/lib/harmony/inspection")

function test_harmony_inspection_stages_are_distinct_and_snapshot_is_read_only()
  writer.reset();local song={}
  writer.plan(song,2,{step=7,source=-2,merge=1,scale=62,harmony=74,output=74,status="ok"})
  luaunit.assert_nil(reader.snapshot(song,2).scheduled)
  reader.scheduled(song,2,74,"root")
  luaunit.assert_nil(writer.snapshot(song,2).emitted)
  writer.emitted(song,2,74,"root")
  local snapshot=reader.snapshot(song,2)
  luaunit.assert_equals(snapshot.planned.source,-2)
  luaunit.assert_equals(snapshot.scheduled.pitch,74)
  luaunit.assert_equals(snapshot.emitted.pitch,74)
  snapshot.planned.output=1
  luaunit.assert_equals(reader.snapshot(song,2).planned.output,74)
end

function test_harmony_inspection_reset_is_project_scoped()
  writer.reset();local a,b={},{}
  writer.plan(a,1,{output=60});writer.plan(b,1,{output=72})
  reader.reset_song(a)
  luaunit.assert_nil(writer.snapshot(a,1).planned)
  luaunit.assert_equals(writer.snapshot(b,1).planned.output,72)
end

function test_harmony_inspection_retains_actual_event_source_and_emitted_pitch()
  writer.reset();local song={}
  writer.plan(song,1,{step=4,source=0,output=48,status="ok",bypass="random"})
  writer.scheduled(song,1,52,"chord1")
  writer.emitted(song,1,55,"chord1")
  local value=writer.snapshot(song,1)
  luaunit.assert_equals(value.scheduled,{pitch=52,source="chord1",step=4,status="ok",bypass="random"})
  luaunit.assert_equals(value.emitted,{pitch=55,source="chord1",step=4,status="ok",bypass="random"})
end
