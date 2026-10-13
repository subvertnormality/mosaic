-- Characterisation outside the manual: authorized per-page header miniatures.
-- Native acceptance uses public inputs and independently frozen literal bitmaps.
local render = include("mosaic/lib/ui_render")
-- Frozen authored literal pixels, independent of the runtime atlas.
local expected={
  R01={width=20,frames={{"....cac.......ccc...","...bbbbb.....ca.ac..","..cb.b.bc....ca.ac..","...bbbbb......ccc...","....bbb........b....","...ccacc.......b....","..cccaccc.....aaa...","...aa.aa............"},{"....bab.......ccc...","...bbbbb.....ca.ac..","..cb.b.bc....ca.ac..","...bbbbb......ccc...","....bbb........b....","...bcacb.......b....","..cccaccc.....aaa...","...aa.aa............"},{".....cac......bcb...","....bbbbb....ca.ac..","...cb.b.bc...ca.ac..","....bbbbb.....bcb...",".....bbb.......b....","...bcacb.......b....","..cccaccc.....aaa...","...aa.aa............"},{".....cbc......bcb...","....bbbbb....ca.ac..","...cb.b.bc...ca.ac..","....bbbbb.....bcb...",".....bbb.......b....","...ccacc.b.....b....","..cccaccc.....aaa...","...aa.aa............"},{"....cac.............","...bbbbb......ccc...","..cb.b.bc....ca.ac..","...bbbbb.....ca.ac..","....bbb.......ccc...","...ccacc.c.....b....","..cccaccc.....aaa...","...aa.aa............"},{".....cac............","....bbbbb.....ccc...","...cb.b.bc...ca.ac..","....bbbbb....ca.ac..",".....bbb......ccc...","...ccacc.b.....b....","..cccacccb....aaa...","...aa.aa............"},{"....bab.......bcb...","...bbbbb.....ca.ac..","..cb.b.bc....ca.ac..","...bbbbb......bcb...","....bbb........b....","...ccacc.......b....","..bccaccb.....aaa...","...aa.aa............"},{"....bac.......ccc...","...bbbbb.....ca.ac..","..cb.b.bc....ca.ac..","...bbbbb......ccc...","....bbb........b....","...ccacc.......b....","..cccaccb.....aaa...","...aa.aa............"}}},
  S01={width=26,frames={{"..........................","..........................","............c.............","...........cc..aaaa.......","..........................","..........aaaa............",".....aaaa.................",".........................."},{"..........................","..........................","..........c...............",".........cc....aaaa.......","..........................","..........aaaa............",".....aaaa.................",".........................."},{"..........................","..........................","..........................","........c......aaaa.......",".......cc.................","..........aaaa............",".....aaaa.................",".........................."},{"..........................","..........................","..........................","..........c....aaaa.......",".........cc...............","..........aaaa............",".....aaaa.................",".........................."},{"..........................","..........................","............c.............","...........cc..aaaa.......","..........................","..........aaaa............",".....aaaa.................",".........................."},{"..........................","..............c...........",".............cc...........","...............aaaa.......","..........................","..........aaaa............",".....aaaa.................",".........................."},{"..........................","................c.........","...............cc.........","...............aaaa.......","..........................","..........aaaa............",".....aaaa.................",".........................."},{"..........................","..........................","..............c...........",".............ccaaaa.......","..........................","..........aaaa............",".....aaaa.................",".........................."}}},
}
local function literal_pixels(id,pose)
  local s=expected[id];local pixels={};local levels={a=7,b=11,c=15}
  for yy,row in ipairs(s.frames[pose+1])do
    for xx=1,#row do local l=levels[row:sub(xx,xx)];if l then pixels[(yy-1)*128+128-s.width+xx-1]=l end end
  end
  return pixels
end

local function capture(id,title,phase)
  local saved, pixels, texts = screen, {}, {}
  local x,y,l,w,h=0,0,0,0,0
  screen=setmetatable({font_size=function()end,level=function(v)l=v end,
    move=function(a,b)x,y=a,b end,text_extents=function(v)return #tostring(v)*5 end,
    text=function(v)texts[#texts+1]={v,x,y,l}end,
    text_right=function(v)texts[#texts+1]={v,x,y,l}end,
    rect=function(a,b,c,d)x,y,w,h=a,b,c,d end,
    fill=function()for yy=y,y+h-1 do for xx=x,x+w-1 do if yy>=0 and yy<=7 and xx>=96 and xx<=127 and l>0 then pixels[yy*128+xx]=l end end end end
  },{__index=function()return function()end end})
  local ok,a,b=pcall(render.draw,{screen=id,title=title,scope="CH01",layout="vertical_list",
    fields={{id="mode",label="Mode",value="AUTO",kind="value"}},selected=1,
    footer="E3 SET K2 BACK",header_beat=phase})
  screen=saved;if not ok then error(a,0)end
  return pixels,texts
end
function test_ui_mini_doctor_has_header_mirror_and_coat_without_moving_text()
  local pixels,texts=capture("R01","RHYTHM DOCTOR",0)
  luaunit.assert_equals(pixels,literal_pixels("R01",0),"missing exact Doctor header miniature")
  luaunit.assert_equals(texts[1],{"RHYTHM DOCTOR",1,7,15})
end
function test_ui_mini_scale_has_distinct_header_pitch_stair()
  local doctor=capture("R01","RHYTHM DOCTOR",0)
  local scale=capture("S01","SCALE",0)
  luaunit.assert_equals(scale,literal_pixels("S01",0),"missing exact Scale header miniature")
  luaunit.assert_not_equals(scale,doctor,"page-specific scenes must differ")
end
function test_ui_mini_beat_changes_only_literal_header_pixels()
  local first,texts=capture("S01","SCALE",0)
  local second,other=capture("S01","SCALE",0.5)
  luaunit.assert_equals(first,literal_pixels("S01",0))
  luaunit.assert_equals(second,literal_pixels("S01",1))
  luaunit.assert_equals(other,texts,"essential text cannot move with header beat")
  local off,off_text=capture("S01","SCALE",nil)
  luaunit.assert_equals(off,first);luaunit.assert_equals(off_text,texts)
end

function test_ui_mini_clock_uses_actual_playing_quarter_pulses()
 local mini=include("mosaic/lib/ui_mini")
 local playing={is_playing=function()return true end,get_clock_lattice=function()return{transport=49,ppqn=96}end}
 local forbidden={get_tempo=function()error("playing must use transport")end,get_beats=function()error("playing must use transport")end}
 luaunit.assert_equals(mini.beat(playing,forbidden,true),0.5)
end
function test_ui_mini_clock_stopped_preview_follows_selected_tempo_without_starting_transport()
 local mini=include("mosaic/lib/ui_mini");local beat,tempo=1.25,60
 local stopped={is_playing=function()return false end,get_clock_lattice=function()error("idle must not use transport")end,start=function()error("art cannot start transport")end}
 local selected={get_tempo=function()return tempo end,get_beats=function()return beat end}
 luaunit.assert_equals(mini.beat(stopped,selected,true),1.25)
 tempo,beat=120,1.75;luaunit.assert_equals(mini.beat(stopped,selected,true),1.75)
 luaunit.assert_nil(mini.beat(stopped,selected,false))
end
function test_ui_mini_clock_invalid_sources_rest_without_other_clock_fallback()
 local mini=include("mosaic/lib/ui_mini")
 local selected={get_tempo=function()return 90 end,get_beats=function()return 22 end}
 luaunit.assert_nil(mini.beat({is_playing=function()return true end,get_clock_lattice=function()return{transport=1,ppqn=0}end},selected,true))
 for _,tempo in ipairs({0,-1,math.huge})do
  luaunit.assert_nil(mini.beat(nil,{get_tempo=function()return tempo end,get_beats=function()error("invalid tempo cannot animate")end},true))
 end
 luaunit.assert_nil(mini.beat(nil,{get_tempo=function()return 90 end,get_beats=function()return 0/0 end},true))
 luaunit.assert_nil(mini.beat(nil,{get_tempo=function()error("clock unavailable")end},true))
end
function test_ui_mini_pose_wraps_musical_loop_and_off_rest()
 local mini=include("mosaic/lib/ui_mini")
 luaunit.assert_equals(mini.pose("C04",0),0);luaunit.assert_equals(mini.pose("C04",0.25),1)
 luaunit.assert_equals(mini.pose("C04",1.999),7);luaunit.assert_equals(mini.pose("C04",2),0)
 luaunit.assert_equals(mini.pose("S01",0.5),1);luaunit.assert_equals(mini.pose("S01",4),0)
 luaunit.assert_equals(mini.pose("R01",nil),0);luaunit.assert_equals(mini.pose("C04",-1),0)
end
function test_ui_mini_header_yields_to_full_title_and_keeps_scope_safe_compact_slot()
 local mini=include("mosaic/lib/ui_mini")
 luaunit.assert_equals(mini.region("C01",78,"overview_masks"),{x=121,y=0,width=7,height=8})
 luaunit.assert_equals(mini.region("C02",78,"overview_params"),{x=121,y=0,width=7,height=8})
 luaunit.assert_nil(mini.region("S01",110,"vertical_list"))
 luaunit.assert_nil(mini.region("X08",20,"native"));luaunit.assert_nil(mini.region("UNKNOWN",20,"detail"))
end
