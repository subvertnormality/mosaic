-- Native norns pixel studies. Geometry illustrates declared fixture data only.
local visuals={}
local function text(s,x,y,size,level)
  screen.font_size(size or 8);screen.level(level or 15);screen.move(x,y);screen.text(s)
end
local function line(x,y,x2,y2,level)
  screen.level(level or 8);screen.move(x,y);screen.line(x2,y2);screen.stroke()
end
local function box(x,y,w,h,level,fill)
  screen.level(level or 8);screen.rect(x,y,w,h);if fill then screen.fill() else screen.stroke() end
end
local function dot(x,y,r,level)
  screen.level(level or 15);screen.circle(x,y,r);screen.fill()
end
function visuals.draw(id,phase,change)
  if id=='V01' then
    text(change==0 and 'E4' or 'F4',2,43,24)
    text(change==0 and 'MIDI 64' or 'MIDI 65',2,54,8,9)
    for i=0,6 do box(63+i*9,24,8,24,i==(change==0 and 2 or 3) and 15 or 5,true) end
    for _,i in ipairs({0,1,3,4,5}) do box(69+i*9,24,4,14,0,true) end
    text('NOTE MASK',68,54,8,10)
  elseif id=='V02' then
    text(tostring(74+change),3,45,26)
    text('SLOT 03/10',3,55,8,9)
    local a=(-.75+(74+change)/127*1.5)*math.pi
    screen.level(4);screen.move(100+math.cos(math.pi*.75)*17,36+math.sin(math.pi*.75)*17)
    screen.arc(100,36,17,math.pi*.75,math.pi*2.25);screen.stroke()
    line(100,36,100+math.sin(a)*14,36-math.cos(a)*14,15)
    dot(100,36,2,15);text('SLIDE ON',80,56,8,10)
  elseif id=='V03' then
    text('4 TRIGS',2,29,10);text('COMMITTED',76,29,8,9)
    local hits={[1]=true,[2]=true,[3]=true,[4]=true}
    for i=1,16 do
      local x=3+(i-1)*8
      box(x,36,5,hits[i] and 12 or 3,hits[i] and 10 or 3,true)
      if i==(phase%16)+1 then line(x,33,x+4,33,15);box(x,35,5,14,15,false) end
    end
    text('01',2,57,8,8);text('16',115,57,8,8)
  elseif id=='V04' then
    text('C',3,44,25);text('MAJOR / vi',3,55,8,9)
    for i=1,7 do
      local a=(i-1)/7*math.pi*2-math.pi/2
      local x,y=99+math.cos(a)*18,38+math.sin(a)*16
      dot(x,y,(i==1 or i==3 or i==5) and 3 or 1.5,(i==1 or i==3 or i==5) and 15 or 5)
    end
    text('6',96,41,10,15)
  elseif id=='V05' then
    local names={'C4','E4','G4','B4'}
    for i,n in ipairs(names) do
      local y=25+(i-1)*9
      text(n,1,y,8,9);line(22,y-2,124,y-2,2)
      local x=29+(i-1)*24
      box(x,y-5,5,5,15,true);line(x+5,y-2,x+15,y-2,10)
    end
    local x=26+(phase%16)*6
    line(x,20,x,55,6)
  elseif id=='V06' then
    local old={48,55,60,64};local new={45,57,60,64}
    for i=1,4 do
      local y1=53-(old[i]-43)*1.3;local y2=53-(new[i]-43)*1.3
      line(39,y1,93,y2,i==1 and 15 or 9)
      dot(39,y1,1.5,10);dot(93,y2,1.5,15)
    end
    text('C',19,27,10,10);text('Am',104,27,10,15)
    text('BASS',1,56,8,8);text('2 HELD',91,56,8,10)
  elseif id=='V07' then
    for i=1,5 do
      local x=2+(i-1)*25
      box(x,23,22,21,i==3 and 15 or 4,i==3)
      text(string.format('%02d',i==5 and 7 or i),x+4,37,10,i==3 and 0 or 10)
      if i==5 then line(x,46,x+21,46,15) end
    end
    text('REPEAT',2,56,8,8)
    for i=1,4 do box(48+(i-1)*13,49,9,7,i<=2 and 15 or 3,true) end
    text('2/4',103,56,8,10)
  elseif id=='V08' then
    text('+12',2,43,23);text('SWING',2,55,8,8)
    for i=0,7 do
      local x=63+i*8
      line(x,26,x,32,4)
      local shift=i%2==1 and 3 or 0
      line(x+shift,39,x+shift,49,15)
    end
  elseif id=='C06' then
    text('E4',2,43,24);text('MIDI 64',2,54,8,9)
    text('G4 B4 D5',66,29,8,15);text('VEL 96',66,42,8,9);text('LEN 1/4',66,54,8,9)
  elseif id=='P05' then
    for i=1,64 do
      local x=2+((i-1)%16)*8;local y=23+math.floor((i-1)/16)*7
      box(x,y,5,4,i==5 and 15 or ((i%3==1 and i<=16) and 8 or 2),true)
    end
    text('01..16  PLAY05',2,56,8,10)
  else return false end
  screen.font_size(8)
  return true
end
return visuals
