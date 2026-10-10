-- README.md Harmony history: only a note accepted by the output path may
-- advance voice-leading history; zero-length accepted gates still count.

local voice_lifetime=include("mosaic/lib/clock/voice_lifetime")

function test_voice_lifetime_rejected_output_does_not_schedule_or_report_acceptance()
  local scheduled=0
  local play=voice_lifetime.new({delay_action=function()scheduled=scheduled+1 end})
  local accepted=play(60,{channel=1,midi_channel=1,midi_device=1,player={note_off=function()end}},
    100,0.25,function()return false end)
  luaunit.assert_nil(accepted)
  luaunit.assert_equals(scheduled,0)
end

function test_voice_lifetime_zero_gate_reports_accepted_even_without_release_token()
  local division
  local play=voice_lifetime.new({delay_action=function(_,value)division=value end})
  local accepted=play(60,{channel=1,midi_channel=1,midi_device=1,player={note_off=function()end}},
    100,0,function()return true end)
  luaunit.assert_true(accepted)
  luaunit.assert_equals(division,0)
end
