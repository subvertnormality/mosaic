-- Pure transport contract; native application paths are separate acceptance.
local codec = dofile("lib/devices/nrpn_codec.lua")
local cases = 0
for value=0,16383 do
  local hi,lo=codec.encode(value,"standard")
  assert(hi%1==0 and lo%1==0 and hi>=0 and hi<=127 and lo>=0 and lo<=127)
  assert(hi*128+lo==value)
  local legacy_hi,legacy_lo=codec.encode(value,"legacy-half")
  assert(legacy_hi==hi)
  assert(legacy_lo==(value%2==0 and (value%128)/2 or 0))
  cases=cases+2
end
local boundaries={
  {0,0,0,0},{1,0,1,0},{126,0,126,63},{127,0,127,0},
  {128,1,0,0},{129,1,1,0},{16383,127,127,0}
}
for _,row in ipairs(boundaries) do
  local hi,lo=codec.encode(row[1]);assert(hi==row[2] and lo==row[3])
  hi,lo=codec.encode(row[1],"legacy-half");assert(hi==row[2] and lo==row[4])
end
for _,bad in ipairs({-1,16384,0.5,math.huge,-math.huge,0/0,"1",false,{}}) do
  for _,mode in ipairs({"standard","legacy-half"}) do
    assert(not pcall(codec.encode,bad,mode),"accepted invalid value")
  end
end
assert(not pcall(codec.encode,nil))
assert(not pcall(codec.encode,1,"unknown"))
assert(not pcall(codec.resolve,false))
assert(not pcall(codec.resolve,nil,{nrpn_lsb_mode=false}))
assert(not pcall(codec.resolve,nil,{nrpn_lsb_mode="typo"}))
assert(not pcall(codec.resolve,nil,nil,{nrpn_lsb_mode="typo"}))
assert(codec.resolve()=="standard")
assert(codec.resolve(nil,nil,{nrpn_lsb_mode="legacy-half"})=="legacy-half")
assert(codec.resolve(nil,{nrpn_lsb_mode="standard"},{nrpn_lsb_mode="legacy-half"})=="standard")
assert(codec.resolve("legacy-half",{nrpn_lsb_mode="standard"})=="legacy-half")
-- A/B/A switching cannot retain the previous mode.
for _,mode in ipairs({"standard","legacy-half","standard"}) do
  local _,lo=codec.encode(127,codec.resolve(mode))
  assert(lo==(mode=="standard" and 127 or 0))
end
print("PASS "..cases.." codec encodings, literal boundaries, invalid values, override precedence and A/B/A mode isolation")
