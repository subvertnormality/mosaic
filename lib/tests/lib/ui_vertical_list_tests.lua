-- Characterisation outside README: authorized vertical-list presentation, 3 October 2026.
-- Public-input screen/ownership acceptance lives under tests/behaviour/.
local render = include("mosaic/lib/ui_render")
local function draw(fields, selected, phase)
  local saved, log = screen, {}
  local x,y,level = 0,0,0
  screen=setmetatable({font_size=function()end,level=function(v)level=v end,
    move=function(a,b)x,y=a,b end,text_extents=function(v)return #tostring(v)*5 end,
    text=function(v)log[#log+1]={text=v,x=x,y=y,level=level}end,
    text_right=function(v)log[#log+1]={text=v,x=x,y=y,level=level,right=true}end
  },{__index=function()return function()end end})
  local ok,a,b=pcall(render.draw,{screen="C04",title="CLOCK",scope="CH01",layout="vertical_list",
    fields=fields,selected=selected or 1,footer="E3 SET  K3 APPLY",marquee=phase,value_dy=6})
  screen=saved
  if not ok then error(a,0)end
  return log,a,b
end
local function field(label,value)return {id=label,label=label,value=value,kind="value"}end
local function find(log,t,y)
  for _,v in ipairs(log)do if v.text==t and (not y or v.y==y)then return v end end
end
function test_ui_vertical_list_shows_four_rows_selection_and_exact_values()
  local log,ok=draw({field("Mode","CLOCK"),field("Division","1/16"),field("Swing","25"),field("Amount","0")},2)
  luaunit.assert_true(ok)
  for i,label in ipairs({"Mode","Division","Swing","Amount"})do
    local v=find(log,label,27+(i-1)*9);luaunit.assert_not_nil(v);luaunit.assert_equals(v.x,7)
    luaunit.assert_equals(v.level,i==2 and 15 or 7)
  end
  luaunit.assert_equals(find(log,">",36).level,15)
  luaunit.assert_equals(find(log,"1/16",36).x,126)
  luaunit.assert_equals(find(log,"CLOCK",27).level,10)
  luaunit.assert_not_nil(find(log,"E3 SET  K3 APPLY",63))
end
function test_ui_vertical_list_scrolls_to_last_row_and_names_position()
  local fields={};for i=1,7 do fields[i]=field("Field"..i,tostring(i))end
  local log,ok=draw(fields,7)
  luaunit.assert_true(ok);luaunit.assert_not_nil(find(log,"7/7",17))
  luaunit.assert_nil(find(log,"Field1"));luaunit.assert_not_nil(find(log,"Field4",27))
  luaunit.assert_not_nil(find(log,"Field7",54));luaunit.assert_not_nil(find(log,">",54))
end
function test_ui_vertical_list_single_field_has_stable_row_and_action_footer()
  local log,ok=draw({field("Tresillo","100")},1)
  luaunit.assert_true(ok);luaunit.assert_not_nil(find(log,"Tresillo",27));luaunit.assert_not_nil(find(log,"100",27))
  luaunit.assert_not_nil(find(log,"E3 SET  K3 APPLY",63))
end
function test_ui_vertical_list_long_exact_selected_value_keeps_label_and_neighbors()
  local log,ok=draw({field("Previous","OFF"),field("Fine start","-2999.9773242630ms"),field("Next","0"),field("Fourth","X")},2)
  luaunit.assert_true(ok);luaunit.assert_not_nil(find(log,"Fine start",36))
  luaunit.assert_not_nil(find(log,"-2999.9773242630ms",45));luaunit.assert_not_nil(find(log,"Previous",27))
  luaunit.assert_not_nil(find(log,"Next",54));luaunit.assert_not_nil(find(log,"E3 SET  K3 APPLY",63))
end
function test_ui_vertical_list_fitting_text_never_moves_with_motion_phase()
  local fields={field("Rate","25"),field("Next","OFF")}
  local first=draw(fields,1,0)
  for _,p in ipairs({9,15,30})do local log=draw(fields,1,p);luaunit.assert_equals(log,first)end
end
-- User correction: overflow scrolling was not authorized to be removed by the
-- vertical-list migration. Each selected label/value must remain readable over
-- the existing marquee cycle; stable neighbors and controls retain their place.
local function assert_readable_over_cycle(fields, original, baseline)
  local fragments={}
  for tick=0,100 do
    local log,ok,report=draw(fields,1,tick)
    luaunit.assert_true(ok)
    luaunit.assert_nil(find(log,"LAYOUT OVERFLOW"))
    for _,entry in ipairs(log)do
      if entry.y==27 or entry.y==36 then fragments[#fragments+1]=entry.text:gsub("~$","")end
    end
    luaunit.assert_equals(find(log,"Next",45),find(baseline,"Next",45))
    luaunit.assert_equals(find(log,"OFF",45),find(baseline,"OFF",45))
    luaunit.assert_equals(find(log,"E3 SET  K3 APPLY",63),find(baseline,"E3 SET  K3 APPLY",63))
  end
  for start=1,#original-4 do
    local needle=original:sub(start,start+4);local found=false
    for _,fragment in ipairs(fragments)do if fragment:find(needle,1,true)then found=true;break end end
    luaunit.assert_true(found,"Marquee never reveals "..needle)
  end
end
function test_ui_vertical_list_selected_overflow_label_is_readable_over_marquee_cycle()
  local label="Selected descriptive parameter with a complete readable ending"
  local fields={field(label,"25"),field("Next","OFF")}
  local baseline=draw(fields,1,0)
  assert_readable_over_cycle(fields,label,baseline)
  luaunit.assert_not_equals(draw(fields,1,9),baseline)
end
function test_ui_vertical_list_selected_overflow_exact_value_is_readable_over_marquee_cycle()
  local value="123456789012345678901234567890123456789ms"
  local fields={field("Fine start",value),field("Next","OFF")}
  local baseline=draw(fields,1,0)
  assert_readable_over_cycle(fields,value,baseline)
  luaunit.assert_not_equals(draw(fields,1,9),baseline)
end


-- Characterisation outside README: list labels use the semantic field name,
-- not compact legacy widget/tile labels (Masks retain their compact names).
function test_ui_vertical_list_uses_semantic_labels_when_legacy_short_labels_differ()
  for _,pair in ipairs({{"Rate","ClockMod","/1"},{"Swing type","SwingType","SWING"},
    {"Root","Notes","C"},{"Scale","Quantizer","Major"},{"Degree","Roman Analysis","I"},
    {"Sensitivity","Sens","0.50"}})do
    local f=field(pair[1],pair[3]);f.short_label=pair[2]
    local log,ok=draw({f},1)
    luaunit.assert_true(ok);luaunit.assert_not_nil(find(log,pair[1],27),pair[1])
    luaunit.assert_nil(find(log,pair[2],27),pair[2])
  end
end

-- Motion Off preserves the prior explicit exact-value overflow guard, rather
-- than quietly abbreviating numeric data. Normal musical values fit the row.
function test_ui_vertical_list_motion_off_preserves_exact_value_overflow_failure()
  local log,ok=draw({field("Wide",string.rep("9",40))},1)
  luaunit.assert_false(ok);luaunit.assert_not_nil(find(log,"LAYOUT OVERFLOW"))
end
function test_ui_vertical_list_motion_off_retains_static_label_overflow_indicator()
  local label="Selected descriptive parameter with a complete readable ending"
  local log,ok,report=draw({field(label,"25"),field("Next","OFF")},1)
  luaunit.assert_true(ok);luaunit.assert_true(report.cut)
  luaunit.assert_nil(report.next_move)
  local found=false
  for _,entry in ipairs(log)do if entry.y==27 and entry.text:sub(-1)=="~"then found=true end end
  luaunit.assert_true(found)
end
