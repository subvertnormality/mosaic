-- Supplementary algorithm regression; native input/output cases remain required.
-- The oracle builds whole repeated bit strings and concatenates A/A/B segments.
-- It does not call Mosaic's bit indexing or tresillo function for expectations.
local data=dofile('lib/helpers/drum_ops_tables.lua')
include=function(name) assert(name=='mosaic/lib/helpers/drum_ops_tables');return data end
local ops=dofile(arg[1] or 'lib/helpers/drum_ops.lua')
local banks={data.table_t_r_e,data.table_dr_bd,data.table_dr_sd,data.table_dr_ch,data.table_dr_oh}
local function bits(bytes)
  local s=''
  for _,byte in ipairs(bytes) do
    for power=7,0,-1 do s=s..(math.floor(byte/2^power)%2==1 and '1' or '0') end
  end
  return s
end
local function take(s,n) return string.sub(string.rep(s,math.ceil(n/#s)),1,n) end
local checked=0
for bank,patterns in ipairs(banks) do
  for pattern=1,128 do
    local other=pattern%128+1
    local a,b=bits(patterns[pattern]),bits(patterns[other])
    for multiplier=1,8 do
      local three=take(a,3*multiplier)
      local phrase=three..three..take(b,2*multiplier)
      for step=1,2*#phrase do
        local expected=phrase:sub((step-1)%#phrase+1,(step-1)%#phrase+1)=='1'
        assert(ops.tresillo(bank,pattern,other,#phrase,step)==expected,
          string.format('bank%d pattern%d multiplier%d step%d',bank,pattern,multiplier,step))
        checked=checked+1
      end
    end
    for step=1,64 do
      local expected=a:sub((step-1)%16+1,(step-1)%16+1)=='1'
      assert(ops.drum(bank,pattern,step)==expected,'Unmodified drum output changed')
      checked=checked+1
    end
  end
end
print(checked..' tresillo/drum bit-string checks passed across every stored pattern and multiplier')
