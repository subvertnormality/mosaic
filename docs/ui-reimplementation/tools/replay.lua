-- Offline code replay. Synthetic text metrics are NOT native layout certification.
local root=arg[1] or 'docs/ui-reimplementation'
local modules={}
function include(name)
 if not modules[name] then modules[name]=assert(loadfile(root..'/code/'..name..'.lua'))()end
 return modules[name]
end
local ops={};local font=8
screen={}
for _,name in ipairs({'clear','level','move','text','text_right','rect','fill','line','stroke','circle','update'})do
 screen[name]=function(...)local row={name,...};for _,v in ipairs(row)do if type(v)=='number'then assert(v==v and math.abs(v)<100000,'nonfinite op')end end;ops[#ops+1]=row end
end
function screen.font_size(n)font=n;ops[#ops+1]={'font_size',n}end
function screen.text_extents(t)return #t*font*0.55 end
local function quote(s)return '"'..s:gsub('\\','\\\\'):gsub('"','\\"'):gsub('\n','\\n'):gsub('\r','\\r'):gsub('\t','\\t')..'"'end
local function json(v)
 if type(v)=='string'then return quote(v)elseif type(v)=='number'or type(v)=='boolean'then return tostring(v)
 elseif type(v)=='table'then local a={}for _,x in ipairs(v)do a[#a+1]=json(x)end return '['..table.concat(a,',')..']'else return 'null'end
end
local function drawn(s)for _,o in ipairs(ops)do if(o[1]=='text'or o[1]=='text_right')and o[2]==s then return true end end end
-- Exact-kind values: never abbreviated anywhere; the selected one appears verbatim on screen.
local function check_values(c)
 local m=c.model
 for k,f in ipairs(m.fields)do if f.kind~='action'and f.kind~='unavailable'then
  local val=tostring(f.value)
  for _,o in ipairs(ops)do if(o[1]=='text'or o[1]=='text_right')and o[2]:sub(-1)=='~'then
   assert(val:sub(1,#o[2]-1)~=o[2]:sub(1,-2),c.id..': abbreviated value '..val..' as '..o[2])end end
  if k==m.selected and val~=''then assert(drawn(val),c.id..': selected value not drawn whole '..val)end
 end end
end
local cases=assert(loadfile(root..'/generated/replay-input.lua'))();local output=assert(io.open(root..'/generated/draw-commands.json','w'))
local original_print=print;print=function()end
output:write('[')
for n,c in ipairs(cases)do
 ops={};local renderer=include(c.program)
 local ok,layout_ok,report=pcall(renderer.draw,c.model,c.field or 0,0)
 assert(ok,c.id..': '..tostring(layout_ok));assert(#ops>0,c.id..': no operations')
 if c.program=='screen'then
  if c.expect_overflow then assert(layout_ok==false and drawn('LAYOUT OVERFLOW'),c.id..': overflow not flagged')
  else
   assert(layout_ok==true,c.id..': LAYOUT OVERFLOW '..table.concat(report and report.reasons or{},','))
   assert(not drawn('LAYOUT OVERFLOW'),c.id..': overflow status without flag')
   if c.check_values~=false and c.model.layout~='pattern64'then check_values(c)end
  end
 end
 if n>1 then output:write(',')end
 output:write('{"id":'..quote(c.id)..',"ops":'..json(ops)..'}')
end
output:write(']\n');output:close();print=original_print
print('PASS '..#cases..' Lua screen replays (synthetic font metrics)')
