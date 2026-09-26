-- Canonical live screen proto-code. Input is already formatted, read-only ViewModel.
-- No selectors, clocks, random calls, setters or hardware input belong in this module.
-- draw(v) returns ok,report. It never raises inside redraw: a value that cannot be shown
-- whole sets ok=false and paints LAYOUT OVERFLOW; the acceptance harness treats that as a fail.
local art=include('characters')
local M={}
local MORE='...' -- value withheld from a cell; the full value is on the same screen's full-width line
local function text(value,x,y,size,level)
 screen.font_size(size or 8);screen.level(level or 15);screen.move(x,y);screen.text(tostring(value))
end
local function right(value,x,y,level)
 screen.font_size(8);screen.level(level);screen.move(x,y);screen.text_right(tostring(value))
end
-- Widths at the 8 px text size are measured once per string: the marquee and
-- fit measure cut text character by character every frame, and each native
-- measurement is costly on the norns. (The cache is bounded.)
local extents8,extents8_count,extents8_screen={},0,nil
local function width8(v)
 if extents8_screen~=screen then extents8,extents8_count,extents8_screen={},0,screen end
 local w=extents8[v]
 if w==nil then
  screen.font_size(8);w=screen.text_extents(v)
  if extents8_count>=1024 then extents8,extents8_count={},0 end
  extents8[v]=w;extents8_count=extents8_count+1
 end
 return w
end
local function width(value,size)if size==nil or size==8 then return width8(tostring(value))end;screen.font_size(size);return(screen.text_extents(tostring(value)))end
-- Text only (title, scope, labels, status, footer, action/unavailable text). Field values of exact kinds never pass here.
-- Marquee (owner request 26 September 2026): text too wide for its room
-- scrolls right to left so it can be read in full. With a phase (ticks from
-- ui_motion; nil when motion is off) it rests MARQUEE_REST ticks on its start,
-- drops one character per tick until its end shows, rests on the end, and starts
-- again. Every cut text shares the phase, so a frame follows from it exactly.
local MARQUEE_REST=8
local phase,cut,next_move=nil,false,nil
local function marquee_offset(n,p)
 local q=p%(2*MARQUEE_REST+n)
 if q<MARQUEE_REST then return 0 end
 return math.min(n,q-MARQUEE_REST+1)
end
local function fit(value,w)
 local v=tostring(value)
 if width8(v)<=w then return v end
 if width8('~')>w then return '' end
 cut=true
 if phase then
  local n=0;while n<#v and width8(v:sub(n+1))>w do n=n+1 end
  local k=marquee_offset(n,phase)
  -- Ticks until this text next moves (on its rests it stays still).
  local q=phase%(2*MARQUEE_REST+n);local d=1
  if q<MARQUEE_REST then d=MARQUEE_REST-q elseif q>=MARQUEE_REST+n then d=2*MARQUEE_REST+n-q end
  if not next_move or d<next_move then next_move=d end
  v=v:sub(k+1)
  if width8(v)<=w then return v end
 end
 while #v>0 and width8(v..'~')>w do v=v:sub(1,-2) end
 return v..'~'
end
local function exact(f)return f.kind~='action' and f.kind~='unavailable' end
local function rect(x,y,w,h,level,outline)
 screen.level(level);screen.rect(x,y,w,h);if outline then screen.stroke()else screen.fill()end
end
-- dy: a few pixels while a new value rolls into place (decorative motion).
local function full_value(value,w,x,y,dy)
 local size=23;screen.font_size(size)
 while size>8 and screen.text_extents(value)>w do size=size-1;screen.font_size(size)end
 if screen.text_extents(value)>w then return false end
 text(value,x,y+(dy or 0),size,15);return true
end
function M.draw(v)
 local r={ok=true,reasons={},marked={}}
 phase,cut,next_move=type(v)=='table'and v.marquee or nil,false,nil
 local function fail(why)r.ok=false;r.reasons[#r.reasons+1]=why end
 screen.clear()
 if type(v)~='table' or not(v.screen and v.title and v.scope and type(v.fields)=='table' and v.layout)
  or type(v.selected)~='number' or v.selected<1 or v.selected>math.max(1,#v.fields)then
  fail('model');text('BAD VIEW MODEL',1,36,8,15);screen.update();return false,r
 end
 local selected=v.fields[v.selected];local L=v.layout;local status_y=55
 -- Selected value on one full-width line: value right-aligned and whole, label shrinks.
 local function value_line(f,y)
  local val=tostring(f.value)
  if width(val)>126 then
   if exact(f)then fail('value '..tostring(f.id));return end
   val=fit(val,126)
  end
  right(val,127,y,15)
  local room=126-width(val)-4
  if room>0 then text(fit(f.label,room),1,y,8,10)end
 end
 if L=='overview_masks' or L=='overview_params' then
  local cols=L=='overview_masks'and 4 or 5;local w=cols==4 and 32 or 25
  if #v.fields>cols*2 then fail('overview count')end
  text(fit(v.title,78),1,7,8,15);right(fit(v.scope,45),118,7,9)
  for k=1,math.min(#v.fields,cols*2)do
   local f=v.fields[k];local x=((k-1)%cols)*w;local y=9+math.floor((k-1)/cols)*18
   if k==v.selected then rect(x,y,w-2,17,15,true)end
   text(fit(f.short_label or f.label,f.marker and w-11 or w-5),x+2,y+7,8,k==v.selected and 15 or 9)
   -- A one-letter state marker (S slide, L held lock) owns the cell's top-right corner.
   if f.marker then rect(x+w-6,y+1,4,7,0);text(f.marker,x+w-6,y+7,8,15)end
   local c=tostring(f.compact_value or f.value)
   if (exact(f)and c:find('~',1,true))or width(c)>w-5 then c=MORE;r.marked[#r.marked+1]=f.id end
   text(c,x+2,y+15,8,13)
  end
  status_y=53;if selected then value_line(selected,53)end
 elseif L=='pattern64' then
  text(fit(v.title,126),1,7,8,15);text(fit(v.scope,126),1,17,8,7);status_y=17
  if type(v.cells)~='table' or #v.cells~=64 then fail('cells')else
   for k,c in ipairs(v.cells)do
    local x=2+((k-1)%16)*8;local y=24+math.floor((k-1)/16)*8
    rect(x,y,4,4,c.level)
    if c.selected then rect(x-1,y-1,6,6,15,true)end
    if c.playing then rect(x,y+5,4,1,9)end
   end
  end
 elseif L=='dashboard' then
  -- Information only: every field on one screen, no cursor. Scope shares the
  -- title row; up to six rows, label left, whole value right-aligned.
  -- The scope takes the room the title leaves (at least 45 px).
  local t=fit(v.title,78);text(t,1,7,8,15);right(fit(v.scope,math.max(45,112-width(t))),118,7,9);status_y=7
  if #v.fields>6 then fail('dashboard count')end
  for k=1,math.min(#v.fields,6)do
   local f=v.fields[k];local y=8+k*8;local val=tostring(f.value)
   if width(val)>126 then
    if exact(f)then fail('value '..tostring(f.id));val=''else val=fit(val,126)end
   end
   local room=126-width(val)-4
   if room>0 then text(fit(f.label,room),1,y,8,7)end
   if val~=''then right(val,127,y,15)end
  end
 elseif L=='detail' then
  text(fit(v.title,126),1,7,8,15);text(fit(v.scope,126),1,17,8,7);status_y=17
  local first=math.max(1,math.min(v.selected-1,#v.fields-3))
  for k=first,math.min(#v.fields,first+3)do
   local f=v.fields[k];local y=27+(k-first)*9;local on=k==v.selected;local val=tostring(f.value)
   if on then text('>',0,y,8,15)end
   -- Values own the row (x 7..126); labels shrink to what is left.
   if width(val)>119 then
    if not exact(f)then val=fit(val,119)
    elseif on then fail('value '..tostring(f.id));val=''
    else val=MORE;r.marked[#r.marked+1]=f.id end
   end
   local room=math.min(72,119-width(val)-4)
   if room>0 then text(fit(f.label,room),7,y,8,on and 15 or 6)end
   if val~=''then right(val,126,y,on and 15 or 8)end
  end
 else
  if L~='focused'then fail('layout '..tostring(L))end
  text(fit(v.title,126),1,7,8,15);text(fit(v.scope,126),1,17,8,7)
  if selected then
   text(fit(selected.label,126),1,28,8,10)
   local val=tostring(selected.value)
   -- Art yields its region to a long value. Never clip numeric data.
   -- The art region holds a character (in time when v.motion has a beat) or a
   -- value dial; either yields the region to a value that needs the width.
   -- A dial or the metronome only decorates: the value keeps the size it has
   -- with the whole width, and the decoration shows only if that leaves x75+ free.
   local decor=v.dial or v.art=='metronome'
   local natural=23;screen.font_size(natural)
   while natural>8 and screen.text_extents(val)>126 do natural=natural-1;screen.font_size(natural)end
   if decor and screen.text_extents(val)<=70 and full_value(val,126,1,48,v.value_dy)then
    if v.dial then if art.draw_dial then art.draw_dial(v.dial)end else art.draw_art(v.art,v.pose or 0,v.active,v.motion)end
   elseif decor and full_value(val,126,1,48,v.value_dy)then
   elseif v.art and not decor and full_value(val,70,1,48,v.value_dy)then
    art.draw_art(v.art,v.pose or 0,v.active,v.motion)
   elseif not full_value(val,126,1,48,v.value_dy)then
    if exact(selected)then fail('value '..tostring(selected.id))else text(fit(val,126),1,45,8,15)end
   end
   text(fit(v.status or'',126),1,55,8,8)
  else text('EMPTY',1,40,15,10)end
 end
 if not r.ok then rect(0,status_y-7,128,9,0);text('LAYOUT OVERFLOW',1,status_y,8,15)end
 -- Exactly one footer owner. No overlapping hints/neighbour labels. A table
 -- footer names the neighbouring fields: left '< prev' (or '| START'), right
 -- 'next >' (or 'END |'), each fitted to its half.
 if type(v.footer)=='table' then
  text(fit(v.footer.left or'',61),1,63,8,7)
  right(fit(v.footer.right or'',61),127,63,10)
 else text(fit(v.footer or'',126),1,63,8,9)end
 screen.update()
 -- Whether any text is cut, and in how many marquee ticks one next moves.
 r.cut,r.next_move=cut,next_move
 return r.ok,r
end
return M
