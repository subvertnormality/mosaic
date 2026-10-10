-- ISOLATED SCREEN PROTO-CODE: specimen model, not application controls.
-- Canonical visual fixtures. Native renderer; no Mosaic musical mutation.
local frames={}
local visuals=include('visuals')
local index=1
local bank=0
local function text(t,x,y,size,level)
 screen.font_size(size or 8);screen.level(level or 15);screen.move(x,y);screen.text(tostring(t))
end
local function line(x,y,xx,yy,level)
 screen.level(level or 8);screen.move(x,y);screen.line(xx,yy);screen.stroke()
end
local function rect(x,y,w,h,level)
 screen.level(level or 8);screen.rect(x,y,w,h);screen.fill()
end
local function fit(t,width)
 t=tostring(t)
 while screen.text_extents(t)>width and #t>1 do t=t:sub(1,-2) end
 return t
end
local function redraw()
 local s=frames[index];local f=s.field+1;local row=s.rows[f]
 local context=s.context
 if s.screen=='P01' then context='PAT01 / 64 STEPS'
 elseif s.screen=='A01' then context=f==1 and 'EDIT SLOT03' or 'GLOBAL SETTING'
 elseif s.screen=='A02' then context=f==1 and 'MASTER CLOCK' or 'SLOT03 FEEL'
 elseif s.screen=='A03' then context=({'AUTOMATIC','EXPLICIT QUEUE','MANUAL','EMPTY-SLOT LOOP'})[f] end
 screen.clear();text(s.title,1,7);text(context,1,17,8,7)
 if s.screen=='C07' then
  text(fit(row[1],124),1,34,8,15)
  text(row[2],1,48,8,8)
  text('E3 browse K3 apply',1,55,8,7)
 elseif s.family=='detail' then
  local start=math.max(1,f-2)
  for k=start,math.min(#s.rows,start+3) do
   local y=27+(k-start)*9
   text(k==f and '>' or '',0,y,8,15)
   text(fit(s.rows[k][1],66),7,y,8,k==f and 15 or 6)
   screen.move(126,y);screen.level(k==f and 15 or 8);screen.text_right(fit(s.rows[k][2],49))
  end
 else
  local id=s.screen
  local alias=nil
  if id=='C01' and row[1]=='Note' then alias='V01'
  elseif id=='C02' and f==1 then alias='V02'
  elseif id=='C10' then alias='V05'
  elseif id=='H05' then alias='V06'
  elseif (id=='C04' or id=='A02') and row[1]=='Swing' then alias='V08'
  elseif id=='C06' then alias='C06'
  elseif id=='P05' then alias='P05' end
  if id=='C01' or id=='C02' then
   -- Equal-weight, always-visible overviews. Selection is an outline, not a lock.
   screen.clear();text(id=='C01' and 'CH01 MASKS' or ((s.flags and #s.flags>0) and 'TRIG' or 'CH01 TRIG PARAMS'),1,7,8,15)
   screen.move(127,7);screen.level(7);screen.text_right(s.context:find('STEP02') and 'S02' or 'CH')
   -- No repeated selection heading: give both overview rows a full text line.
   if s.flags and #s.flags>0 then
    screen.move(127,7);screen.level(15);screen.text_right(s.flags=='LS' and 'S02 SLIDE' or 'S02 LOCK')
   end
   local cols=id=='C01' and 4 or 5;local width=id=='C01' and 32 or 25
   local labels=id=='C01' and {'TRIG','NOTE','VEL','LEN','CH1','CH2','CH3','CH4'} or {'PRB','FIX','QFX','RND','STR','ARP','C74','C71','---','---'}
   for k,r in ipairs(s.rows) do
    local x=((k-1)%cols)*width;local y=12+math.floor((k-1)/cols)*22
    if k==f then screen.level(15);screen.rect(x,y,width-2,20);screen.stroke() end
    screen.font_size(8)
    local name=labels[k]
    if id=='C02' and (k>=9 or r[1]=='None') then name=r[1]=='None' and '---' or r[1]:gsub('CC','C');if name=='Trig probability' then name='PRB' end end
    text(fit(name,width-5),x+2,y+8,8,k==f and 15 or 11)
    local v=r[2]=='INHERIT' and 'X' or r[2]
    text(fit(v,width-5),x+2,y+17,8,k==f and 15 or 13)
   end
  elseif id=='C12' and row[1]=='Note' then visuals.draw('V01',0,0)
  elseif id=='C12' or id=='C13' then
   text(fit(row[1],124),1,29,8,10)
   text(row[2],1,49,#row[2]>5 and 12 or 23,15)
  elseif id=='S01' then
   text(row[1]..' '..row[2],1,28,10,15)
   if f==1 then
    text('C  D  E  F  G  A  B',1,42,8,9);line(1,46,8,46,15);text('TONIC',1,55,8,8)
   elseif f==2 then
    local gaps={2,2,1,2,2,2,1};local x=3
    for _,v in ipairs(gaps) do rect(x,37,v*7,4,10);text(v,x,52,8,9);x=x+v*7+4 end
   elseif f==3 then
    local names={'I','II','III','IV','V','VI','VII'}
    for k,n in ipairs(names) do local x=1+(k-1)*18;if k==3 then rect(x-1,33,18,11,15) end;text(n,x,41,8,k==3 and 0 or 6) end
    text('C D [E] F G A B',1,55,8,10)
   elseif f==4 then
    text('C  D  E',1,40,8,7);text('D  E  F#',72,40,8,15);line(45,37,65,37,12);line(61,34,65,37,12);line(61,40,65,37,12)
    text('ALL PITCHES +2',1,55,8,9)
   elseif f==5 then
    text('TONE7',2,40,8,7);text('-8ve',83,50,8,15);line(36,37,75,47,12);text('UPPER DEGREE -12',1,56,8,9)
   else
    text('C D E F G A B',1,40,8,15);text('OFF: FULL SCALE',1,53,8,7)
   end
  elseif id=='P01' or id=='P08' then
   local focus=({5,21,33,64})[f] or 33
   if id=='P08' then focus=33 end
   for r=0,3 do
    text(string.format('%02d',r*16+1),0,28+r*8,8,6)
    for c=0,15 do local step=r*16+c+1;local x=14+c*7;local y=23+r*8
     rect(x,y,4,4,step<=4 and 14 or 2)
     if step==focus then screen.level(15);screen.rect(x-1,y-1,6,6);screen.stroke() end
     if step==5 then line(x,y+5,x+3,y+5,9) end
    end
   end
   -- Last grid/row-label ink ends at y52. Reserve y57..63 for one status line.
   text(id=='P08' and row[2] or ('EDIT '..string.format('%02d',focus)..' / PLAY05'),1,63,8,10)
  elseif id=='P06' then
   text(row[1],1,30,12,15)
   local labels={'Bank + Pattern1','Pattern1 + Pattern2','Fill / Length','Prime + Pattern1/2'}
   text(labels[f],1,43,8,10)
   text(f==3 and 'BANK UNUSED' or (f==1 and 'PATTERN2 UNUSED' or 'GRID INPUTS'),1,55,8,7)
  elseif id=='P07' then
   text(row[1]..' '..row[2],1,28,8,15)
   for i=0,15 do
    rect(27+i*6,34,4,4,i<4 and 8 or 2)
    if i%3==0 then rect(27+i*6,45,4,4,15) end
   end
   text('OLD',1,39,8,9);text('NEW',1,50,8,15)
  elseif id=='A01' then
   text(row[1],1,29,8,10)
   if f==1 then text('4',1,48,22,15);text('PLAYS',29,47,8,10);for k=0,3 do rect(78+k*12,37,8,8,10) end
   else text('ON',1,48,22,15);text('AUTO ADVANCE',40,46,8,10) end
  elseif id=='A03' then
   text('PLAYING',1,29,8,7)
   if f~=3 then text(f==2 and 'QUEUED' or 'NEXT',83,29,8,7) end
   text(f==4 and '04' or '03',1,49,20,15)
   if f==3 then text('HOLD',79,47,10,8)
   else text(({'04','07','','01'})[f],85,49,20,10);line(45,41,72,41,10);line(66,37,72,41,10);line(66,45,72,41,10) end
   text(f==3 and 'GRID SELECTS NEXT' or 'PASS 2/4',1,63,8,10)
  elseif id=='H12' then
   local a={60,64,67};local b={60,65,69}
   for k=1,3 do line(29,53-(a[k]-59)*2,101,53-(b[k]-59)*2,k==1 and 15 or 8) end
   text('C E G',1,27,8,8);text('C F A',87,27,8,15);text('B: E4 > F4',1,54,8,10)
  elseif alias then visuals.draw(alias,s.field,0)
  else
   text(row[1],1,28,8,10)
   local value=row[2];local size=#value>9 and 10 or (#value>5 and 16 or 23)
   screen.font_size(size)
   while screen.text_extents(value)>68 and size>8 do size=size-1;screen.font_size(size) end
   text(fit(value,68),1,49,size,15)
   if id=='P04' and f==1 then
    text('0',75,55,8,5);text('127',110,55,8,5);line(76,39,122,39,5);rect(76,36,35,6,12)
   elseif id=='H02' or id=='H03' or id=='H13' then
    line(74,40,124,40,5);rect(83,36,31,8,7);line(98,31,98,48,15)
   elseif id=='S02' or id=='S03' then
    text('TRACK17',78,38,8,7);text('GLOBAL',78,50,8,7)
   elseif id=='C04' or id=='A02' or id=='F01' or id=='F02' then
    for i=0,6 do line(76+i*7,35,76+i*7,48,i%2==0 and 15 or 5) end
   end
  end
 end
 screen.font_size(8)
 -- Stable field index; control semantics are attached verbatim in the atlas.
 if s.screen=='P01' or s.screen=='P08' or s.screen=='A03' then
  -- The grid owns the body; status above replaces the generic inspector footer.
 else
  local previous=f>1 and s.rows[f-1][1] or nil
  local following=f<#s.rows and s.rows[f+1][1] or nil
  if s.screen=='C02' then previous=f>1 and 'Slot'..string.format('%02d',f-1) or nil;following=f<10 and 'Slot'..string.format('%02d',f+1) or nil
  elseif s.screen=='C10' then previous='Prev slot';following='Next slot' end
  if s.screen=='P03' or s.screen=='P04' or s.screen=='P05' or s.screen=='C06' then previous=nil;following='Channel2' end
  text(previous and '< '..fit(previous,49) or '| START',1,63,8,7)
  screen.move(127,63);screen.level(10);screen.text_right(following and fit(following,49)..' >' or 'END |')
 end
 screen.update();print('CANONICAL_FRAME '..index)
end
local M={}
function M.draw(model,selected_field,animation_pose)
 frames[1]=model;index=1;model.field=selected_field or 0

 redraw()
end
return M
