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
function test_ui_vertical_list_essential_text_never_moves_with_motion_phase()
  local fields={field("A long descriptive label","25"),field("Next","OFF")}
  local first=draw(fields,1,0)
  for _,p in ipairs({9,15,30})do local log=draw(fields,1,p);luaunit.assert_equals(log,first)end
end
function test_ui_vertical_list_impossible_exact_value_fails_visibly()
  local log,ok=draw({field("Wide",string.rep("9",40))},1)
  luaunit.assert_false(ok);luaunit.assert_not_nil(find(log,"LAYOUT OVERFLOW"))
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
