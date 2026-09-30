-- ISOLATED SCREEN PROTO-CODE: specimen model, not application controls.
-- Original character studies using the same native screen primitives as the atlas.
-- Isolated presentation fixtures: no Mosaic, synthesis, MIDI output or musical RNG.
local frames={}
local index,bank,pose=1,0,0
local motion=false
local layer=0 -- Capture-only: 1 text, 2 artwork; 0 is the complete screen.
local function text(t,x,y,size,level)
 if layer==2 then return end
 screen.font_size(size or 8);screen.level(level or 15);screen.move(x,y);screen.text(tostring(t))
end
local function line(x,y,xx,yy,l)
 if layer==1 then return end
 screen.level(l or 10);screen.move(x,y);screen.line(xx,yy);screen.stroke()
end
local function box(x,y,w,h,l,outline)
 if layer==1 then return end
 screen.level(l or 15);screen.rect(x,y,w,h);if outline then screen.stroke()else screen.fill()end
end
local function circle(x,y,r,l,outline)
 if layer==1 then return end
 screen.level(l or 15);screen.circle(x,y,r);if outline then screen.stroke()else screen.fill()end
end
local function fit(t,w)
 t=tostring(t);while screen.text_extents(t)>w and #t>1 do t=t:sub(1,-2) end;return t
end
local function eyes(x,y,p)
 if p==1 then line(x,y,x+2,y,0);line(x+6,y,x+8,y,0)
 else box(x,y,1,2,0);box(x+7,y,1,2,0) end
end
local function doctor(p)
 -- Head mirror, swept hair, shades, broad white lapels and a stethoscope.
 -- A jaunty elbow and tapping shoe give the tiny physician some groove.
 box(92,32,19,9,10);box(89,33,4,4,10)
 box(91,31,17,3,5);box(89,33,6,2,5)
 line(92,34,111,34,15);circle(106,33,3,15);circle(106,33,1,0)
 box(94,36,6,3,0);box(103,36,6,3,0);line(100,37,103,37,0)
 line(99,41,105,41,15);box(101,42,3,2,10)
 box(92,44,19,7,15)
 line(96,44,101,49,0);line(108,44,103,49,0);line(102,48,102,51,0)
 line(95,44,95,48,3);line(95,48,98,49,3);circle(98,49,1,0)
 line(92,45,87,48,15);line(87,48,84,44-(p%2),15)
 line(111,45,115,48,15);line(115,48,118,44,15)
 box(93,52,7,1,15);box(105,51+(p%2),8,1,15)
 -- Musical sparks are decorative, never an input meter.
 line(79,35,81,38,6);line(81,38,79,41,6)
 line(122,35,120,38,6);line(120,38,122,41,6)
end
local function garden(p,active)
 -- Two protected flowers and four ranked sprouts. No per-hit randomness.
 line(77,51,125,51,7)
 for k=0,5 do
  local x=81+k*8;local tall=k==0 or k==3
  local h=tall and 15 or (active and (5+(k%3)*2) or 3)
  line(x,50,x,50-h,tall and 15 or 9)
  if tall then
   box(x-2,33,5,5,15);box(x,35,1,1,0)
   line(x,44,x-3,41,9);line(x,47,x+3,44,9)
  elseif active then
   line(x,50-h+3,x-3,50-h,10);line(x,50-h+4,x+3,50-h+1,10)
  else box(x-2,46,4,3,6,true)end
 end
 -- Tiny garden visitor only blinks; plant counts never change with the pose.
 box(115,30,8,7,12);box(117,32,1,pose==1 and 1 or 2,0);box(121,32,1,2,0)
 line(116,37,118,39,8);line(122,37,120,39,8)
end
local function choir(p,register)
 -- Three note creatures. Common-tone Bass stays on its rung in every pose.
 for k=0,2 do
  local x=82+k*17;local y=register and (45-k*5)or(44-k*3)
  line(x-5,y+6,x+6,y+6,6)
  circle(x,y,5,k==0 and 15 or 10)
  box(x-2,y-1,1,p==1 and 1 or 2,0);box(x+2,y-1,1,2,0)
  local top=math.max(30,y-12);line(x+5,y,x+5,top,13);line(x+5,top,x+8,top+2,13)
  line(x-2,y+5,x-3,y+7,10);line(x+2,y+5,x+3,y+7,10)
 end
end
local function footer(s,f)
 local a=f>1 and s.rows[f-1][1]or nil
 local b=f<#s.rows and s.rows[f+1][1]or nil
 screen.font_size(8);text(a and '< '..fit(a,49)or'| START',1,63,8,7)
 if layer~=2 then screen.move(127,63);screen.level(10);screen.text_right(b and fit(b,49)..' >'or'END |')end
end
local function value(v,size)
 screen.font_size(size);while screen.text_extents(v)>70 and size>8 do size=size-1;screen.font_size(size)end
 text(fit(v,70),1,47,size,15)
end
local function redraw()
 local s=frames[index];local f=s.field+1;local row=s.rows[f]
 screen.clear();text(s.title,1,7);text(s.context,1,17,8,7)
 if s.family=='detail' then
  local first=math.max(1,math.min(f-1,#s.rows-3))
  for k=first,math.min(#s.rows,first+3)do
   local y=27+(k-first)*9;text(k==f and'>'or'',0,y,8,15)
   text(fit(s.rows[k][1],72),7,y,8,k==f and 15 or 6)
   if layer~=2 then screen.move(126,y);screen.level(k==f and 15 or 8);screen.text_right(fit(s.rows[k][2],43))end
  end
 elseif s.art=='result' then
  text('6/8 ADD   CYCLE2/4',1,28,8,10)
  for r=0,3 do for c=0,15 do local n=r*16+c;local x=2+c*8;local y=32+r*4
   if n%8==0 then box(x,y,3,3,15)
   elseif n==2 or n==6 or n==10 or n==18 or n==22 or n==26 then box(x,y,3,3,12,true)
   elseif n==30 or n==34 then box(x+1,y+1,1,1,5)end
  end end
  text('S11 ADD / ACTIVE',1,55,8,9)
 elseif s.art=='phrase' then
  text(row[1],1,28,8,10);value(row[2],21)
  for k=0,3 do local h=(k+1)*4;box(77+k*12,50-h,8,h,8);box(79+k*12,48-h,1,1,15);box(82+k*12,48-h,1,1,15)end
  text(s.badge or'DRAFT ALL',1,55,8,8)
 elseif s.art=='movement' then
  text(row[1],1,28,8,10)
  value(row[2],#row[2]>5 and 13 or 23)
  local a={49,43,38};local b={49,41,35}
  for k=1,3 do line(77,a[k],115,b[k],k==1 and 15 or 7);circle(77,a[k],1,8);circle(120,b[k],2,12);box(119,b[k],1,1,0);box(121,b[k],1,1,0)end
  text('PLAN',1,55,8,8)
 else
  text(fit(row[1],124),1,28,8,10)
  local v=row[2];local size=#v>9 and 10 or(#v>5 and 15 or 23)
  screen.font_size(size);while screen.text_extents(v)>70 and size>8 do size=size-1;screen.font_size(size)end
  text(fit(v,70),1,47,size,15)
  if s.art=='doctor' then doctor(pose)
  elseif s.art=='garden' then garden(pose,s.badge~='DRAFT ALL')
  elseif s.art=='choir' then choir(pose,false)
  elseif s.art=='register' then choir(pose,true)
  elseif s.art=='window' then
   doctor(pose)
   -- Exact capture window remains in the large value; keep the coat readable.
  end
  text(fit(s.badge or'INFO',70),1,55,8,8)
 end
 footer(s,f);screen.update();print('CANONICAL_FEATURE_FRAME '..index..' '..pose)
end
local M={}
function M.draw(model,selected_field,animation_pose)
 frames[1]=model;index=1;model.field=selected_field or 0
 pose=animation_pose or 0
 redraw()
end
function M.draw_art(kind,p)
 pose=p or 0
 if kind=='doctor' or kind=='window' then doctor(pose)
 elseif kind=='garden' then garden(pose,false)
 elseif kind=='choir' then choir(pose,false)
 elseif kind=='register' then choir(pose,true)
 end
end
return M
