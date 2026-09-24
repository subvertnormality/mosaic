-- Canonical live screen proto-code. Input is already formatted, read-only ViewModel.
-- No selectors, clocks, random calls, setters or hardware input belong in this module.
local art=include('characters')
local M={}
local function text(value,x,y,size,level)
 screen.font_size(size or 8);screen.level(level or 15);screen.move(x,y);screen.text(tostring(value))
end
local function fit(value,width)
 local v=tostring(value);screen.font_size(8)
 if screen.text_extents(v)<=width then return v end
 while #v>0 and screen.text_extents(v..'~')>width do v=v:sub(1,-2) end
 return v..'~'
end
local function rect(x,y,w,h,level,outline)
 screen.level(level);screen.rect(x,y,w,h);if outline then screen.stroke()else screen.fill()end
end
local function full_value(value,width,x,y)
 local size=23;screen.font_size(size)
 while size>8 and screen.text_extents(value)>width do size=size-1;screen.font_size(size)end
 if screen.text_extents(value)>width then return false end
 text(value,x,y,size,15);return true
end
function M.draw(v)
 assert(v.screen and v.title and v.scope and v.fields and v.layout)
 assert(v.selected>=1 and v.selected<=math.max(1,#v.fields))
 screen.clear();text(fit(v.title,126),1,7,8,15)
 local selected=v.fields[v.selected]
 if v.layout=='overview_masks' or v.layout=='overview_params' then
  local cols=v.layout=='overview_masks'and 4 or 5;local width=cols==4 and 32 or 25
  assert(#v.fields<=cols*2,'overview count')
  screen.clear();text(fit(v.title,78),1,7,8,15)
  screen.move(127,7);screen.level(9);screen.text_right(fit(v.scope,45))
  for k,f in ipairs(v.fields)do
   local x=((k-1)%cols)*width;local y=12+math.floor((k-1)/cols)*22
   if k==v.selected then rect(x,y,width-2,20,15,true)end
   text(fit(f.short_label,width-5),x+2,y+8,8,k==v.selected and 15 or 9)
   text(fit(f.compact_value,width-5),x+2,y+17,8,13)
  end
 elseif v.layout=='pattern64' then
  text(fit(v.scope,126),1,17,8,7);assert(#v.cells==64)
  for k,c in ipairs(v.cells)do
   local x=2+((k-1)%16)*8;local y=24+math.floor((k-1)/16)*8
   rect(x,y,4,4,c.level)
   if c.selected then rect(x-1,y-1,6,6,15,true)end
   if c.playing then rect(x,y+5,4,1,9)end
  end
 elseif v.layout=='detail' then
  text(fit(v.scope,126),1,17,8,7)
  local first=math.max(1,math.min(v.selected-1,#v.fields-3))
  for k=first,math.min(#v.fields,first+3)do
   local f=v.fields[k];local y=27+(k-first)*9
   if k==v.selected then text('>',0,y,8,15)end
   text(fit(f.label,66),7,y,8,k==v.selected and 15 or 6)
   screen.move(126,y);screen.level(k==v.selected and 15 or 8);screen.text_right(fit(f.value,47))
  end
 else
  text(fit(v.scope,126),1,17,8,7)
  if selected then
   text(fit(selected.label,126),1,28,8,10)
   local width=v.art and 70 or 126
   if not full_value(selected.value,width,1,48)then
    -- Values too wide for art get the full display width. Never clip numeric data.
    if not full_value(selected.value,126,1,48)then
     assert(selected.kind~='value', 'numeric value must fit full width')
     text(fit(selected.value,126),1,45,8,15)
    end
   elseif v.art then art.draw_art(v.art,v.pose or 0)end
   text(fit(v.status or'',126),1,55,8,8)
  else text('EMPTY',1,40,15,10)end
 end
 -- Exactly one footer owner. No overlapping hints/neighbour labels.
 text(fit(v.footer or'',126),1,63,8,9)
 screen.update()
end
return M
