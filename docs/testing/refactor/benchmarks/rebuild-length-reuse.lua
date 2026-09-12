-- Run from the repository root; measures actual merge bodies, not native timing.
local repo = "."
local revision = arg[1] or "9b17d3f"
assert(revision:match("^%x+$") and #revision >= 7 and #revision <= 40)
local f = assert(io.popen("git show " .. revision .. ":lib/pattern.lua"))
local current = f:read("*a"); assert(f:close())
f = assert(io.open("lib/pattern.lua", "r"))
local candidate = f:read("*a"); f:close()

include = function() return {} end
program = {
  initialise_64_table = function(t) for i=1,64 do t[i]=0 end return t end,
  get_step_trig_masks = function(channel) return program.song.channels[channel].step_trig_masks end,
}
fn = dofile(repo .. "/lib/helpers/functions.lua")

local baseline_impl = assert(load(current, "baseline", "t", _ENV))()
local candidate_impl = assert(load(candidate, "candidate", "t", _ENV))()

local function make_song(source_count, shape)
  local song = {patterns={}, channels={}}
  for p=1,source_count do
    local src={lengths={},trig_values={},note_values={},note_mask_values={},velocity_values={}}
    for s=1,64 do
      local trig = shape == "dense-short" and (s % 2 == p % 2) or (s == ((p-1)*4)%64+1)
      src.trig_values[s]=trig and 1 or 0
      src.lengths[s]=shape == "dense-short" and (1 + (s+p)%3/4) or (32 + (s+p)%49/3)
      src.note_values[s]=(s+p)%15-3
      src.note_mask_values[s]=-1
      src.velocity_values[s]=(s*3+p*7)%128
    end
    song.patterns[p]=src
  end
  for c=1,16 do
    local selected={}
    for p=1,source_count do selected[p]=true end
    song.channels[c]={number=c,selected_patterns=selected,step_trig_masks={},step_note_masks={},step_velocity_masks={},step_length_masks={},trig_merge_mode="all",note_merge_mode="average",velocity_merge_mode="average",length_merge_mode="average"}
  end
  return song
end

local function same(a,b,path)
  path=path or ""
  for k,v in pairs(a) do
    assert(type(v) ~= "table" or type(b[k]) == "table", path.."/"..tostring(k))
    if type(v)=="table" then same(v,b[k],path.."/"..tostring(k)) else assert(v==b[k],path.."/"..tostring(k)) end
  end
  for k in pairs(b) do assert(a[k]~=nil,path.."/extra/"..tostring(k)) end
end

local function sweep(impl, song, cached)
  program.song=song
  local cache=cached and {} or nil
  local out={}
  for c=1,16 do
    local ch=song.channels[c]
    out[c]=impl.get_and_merge_patterns(c,ch.trig_merge_mode,ch.note_merge_mode,ch.velocity_merge_mode,ch.length_merge_mode,song,cache)
  end
  local entries=0
  if cache then for _ in pairs(cache) do entries=entries+1 end end
  assert(entries <= 16)
  return out,entries
end

local iterations=40
local function timed(impl,song,cached)
  collectgarbage("collect")
  local started=os.clock(); local out,entries
  for _=1,iterations do out,entries=sweep(impl,song,cached) end
  return os.clock()-started,out,entries
end

print("shape\tsources\tsample\tbaseline_s\tcached_s\tspeedup\tcache_entries")
for _,shape in ipairs({"dense-short","sparse-sustained"}) do
  for _,sources in ipairs({1,4,16}) do
    for sample=1,5 do
      local song=make_song(sources,shape)
      local bt,ct,bo,co,entries
      if sample%2==1 then
        bt,bo=timed(baseline_impl,song,false); ct,co,entries=timed(candidate_impl,song,true)
      else
        ct,co,entries=timed(candidate_impl,song,true); bt,bo=timed(baseline_impl,song,false)
      end
      same(bo,co)
      print(string.format("%s\t%d\t%d\t%.6f\t%.6f\t%.3f\t%d",shape,sources,sample,bt,ct,bt/ct,entries))
    end
  end
end
