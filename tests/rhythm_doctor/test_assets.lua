-- PLAN.md "Bank lifecycle, races and persistence". Unit contract for the isolated
-- project-owned WAV store; no shell, norns, capture worker, or host filesystem.
package.path = "./lib/?.lua;./lib/?/init.lua;" .. package.path
local Assets = require("rhythm_doctor.assets")
local total=0
local function check(v,m) total=total+1;if not v then error(m or "check failed",2) end end
local function equal(a,b,m) check(a==b,(m or "values differ")..": "..tostring(a).." ~= "..tostring(b)) end
local function u16(n) return string.char(n % 256, math.floor(n / 256) % 256) end
local function u32(n)
  return string.char(n % 256, math.floor(n / 256) % 256,
    math.floor(n / 65536) % 256, math.floor(n / 16777216) % 256)
end
local function wav(payload, rate)
  assert(#payload%8==0); rate=rate or 8000
  return "RIFF"..u32(36+#payload).."WAVEfmt "..u32(16)..u16(3)..u16(2)..u32(rate)..u32(rate*8)..u16(8)..u16(32).."data"..u32(#payload)..payload
end
local ONE,TWO,TAMPERED=wav("11111111"),wav("22222222"),wav("33333333")
local digests={[ONE]=string.rep("a",64),[TWO]=string.rep("b",64),[TAMPERED]=string.rep("c",64)}
local function digest(bytes) return digests[bytes] or string.rep("d",64) end
local function fake_fs()
 local fs={files={},directories={},calls={},failure={},open_handles=0}
 function fs:mkdir_all(p) self.calls[#self.calls+1]={"mkdir",p};if self.failure.mkdir then return nil,"mkdir" end;self.directories[p]=true;return true end
 function fs:exists(p) self.calls[#self.calls+1]={"exists",p};if self.failure.exists then return nil,"exists" end;return self.files[p]~=nil end
 function fs:read(p) self.calls[#self.calls+1]={"read",p};if self.failure.read then return nil,"read" end;if self.files[p]==nil then return nil,"missing" end;return self.files[p] end
 function fs:open_new(p,mode)
  self.calls[#self.calls+1]={"open_new",p,mode};if self.failure.open then return nil,"open" end;if self.files[p]~=nil then return nil,"exists" end
  self.files[p]="";self.open_handles=self.open_handles+1;local owner,self_handle=self,{}
  function self_handle:write(bytes)
   if owner.failure.write then return nil,"write" end
   if owner.failure.partial_write then owner.files[p]=owner.files[p]..bytes:sub(1,1);return 1 end
   owner.files[p]=owner.files[p]..bytes;return #bytes
  end
  function self_handle:close()
   if not self_handle.closed then self_handle.closed=true;owner.open_handles=owner.open_handles-1 end
   if owner.failure.close then return nil,"close" end
   if owner.failure.corrupt_stage then owner.files[p]=TAMPERED end
   return true
  end
  if self.failure.invalid_handle then return {close=self_handle.close} end
  return self_handle
 end
 function fs:sync_file(handle) self.calls[#self.calls+1]={"sync_file"};if self.failure.file_sync then return nil,"file sync" end;return true end
 function fs:rename_new(source,destination)
  self.calls[#self.calls+1]={"rename_new",source,destination};if self.failure.rename then return nil,"rename" end
  if self.files[destination]~=nil then return nil,"exists" end;if self.files[source]==nil then return nil,"missing" end
  self.files[destination]=self.files[source];self.files[source]=nil;return true
 end
 function fs:sync_parent(path) self.calls[#self.calls+1]={"sync_parent",path};if self.failure.parent_sync then return nil,"parent sync" end;return true end
 function fs:remove(p) self.calls[#self.calls+1]={"remove",p};if self.failure.remove then return nil,"remove" end;self.files[p]=nil;return true end
 return fs
end
local function store(fs,extra)
 extra=extra or {};return assert(Assets.new({fs=fs,hash=digest,root="rd-assets",max_bytes=extra.max_bytes or Assets.MAX_BYTES,nonce=extra.nonce or function() return "fixed" end}))
end
local function path(project,hash) return "rd-assets/"..project.."/audio/"..hash..".wav" end
local function calls(fs,name) local n=0;for _,c in ipairs(fs.calls) do if c[1]==name then n=n+1 end end;return n end

-- Exact native WAV output commits only after full staged bytes, fsync(file),
-- exclusive publication, and fsync(parent). Duplicate content is verified but
-- never overwritten.
do
 local fs=fake_fs();local s=store(fs);local ref,err=s:commit("project_a",ONE);check(ref,err and err.code)
 equal(ref.schema_version,Assets.REFERENCE_VERSION);equal(ref.format,"wav-f32le-stereo");equal(ref.sample_rate,8000);equal(ref.frame_count,1);equal(ref.byte_count,#ONE);equal(ref.path,path("project_a",digests[ONE]));equal(fs.files[ref.path],ONE)
 check(calls(fs,"sync_file")==1 and calls(fs,"sync_parent")==1,"durability barriers before success");equal(s:load("project_a",ref),ONE)
 local opened=calls(fs,"open_new");local duplicate=assert(s:commit("project_a",ONE));equal(duplicate.path,ref.path);equal(calls(fs,"open_new"),opened,"duplicate does not overwrite")
end

-- Strict serialised references reject unknown versions/fields, traversal, wrong
-- WAV metadata/path, and cross-project use before reading a file.
do
 local fs=fake_fs();local s=store(fs);local ref=assert(s:commit("project_a",ONE));local bads={
  {schema_version=2,project_id=ref.project_id,sha256=ref.sha256,byte_count=ref.byte_count,path=ref.path,format=ref.format,sample_rate=ref.sample_rate,frame_count=ref.frame_count},
  {schema_version=1,project_id="../b",sha256=ref.sha256,byte_count=ref.byte_count,path=ref.path,format=ref.format,sample_rate=ref.sample_rate,frame_count=ref.frame_count},
  {schema_version=1,project_id=ref.project_id,sha256=ref.sha256,byte_count=ref.byte_count,path="rd-assets/project_a/audio/../x.wav",format=ref.format,sample_rate=ref.sample_rate,frame_count=ref.frame_count},
  {schema_version=1,project_id=ref.project_id,sha256=ref.sha256,byte_count=ref.byte_count,path=ref.path,format="raw-f32",sample_rate=ref.sample_rate,frame_count=ref.frame_count},
  {schema_version=1,project_id=ref.project_id,sha256=ref.sha256,byte_count=ref.byte_count,path=ref.path,format=ref.format,sample_rate=ref.sample_rate,frame_count=ref.frame_count,extra=true}}
 for i,bad in ipairs(bads) do local value,e=s:load("project_a",bad);check(value==nil and e and e.code=="INVALID_REFERENCE","strict ref "..i) end
 local value,e=s:load("project_b",ref);check(value==nil and e and e.code=="PROJECT_MISMATCH","cross project")
end

-- Every staging failure closes its acquired handle, removes only its acquired
-- partial, and never deletes an earlier immutable asset.
do
 for _,mode in ipairs({"write","partial_write","file_sync","close","corrupt_stage","rename"}) do
  local fs=fake_fs();local s=store(fs);local previous=assert(s:commit("project_a",ONE));fs.failure[mode]=true
  local ref,e=s:commit("project_a",TWO);local expected=({write="WRITE_FAILED",partial_write="WRITE_FAILED",file_sync="FILE_SYNC_FAILED",close="CLOSE_FAILED",corrupt_stage="STAGING_VERIFY_FAILED",rename="RENAME_FAILED"})[mode]
  check(ref==nil and e and e.code==expected,mode.." visible");equal(fs.open_handles,0,mode.." closes handle");equal(fs.files[previous.path],ONE,mode.." preserves previous");equal(fs.files[path("project_a",digests[TWO])],nil,mode.." no final");equal(fs.files[path("project_a",digests[TWO])..".pending-fixed"],nil,mode.." cleans acquired partial")
 end
end

-- Exclusive staging prevents a second store/process from replacing or deleting a
-- pre-existing pending name when it did not acquire that name.
do
 local fs=fake_fs();local s=store(fs);local pending=path("project_a",digests[TWO])..".pending-fixed";fs.files[pending]="other process"
 local ref,e=s:commit("project_a",TWO);check(ref==nil and e and e.code=="OPEN_FAILED","exclusive open failure visible");equal(fs.files[pending],"other process","foreign pending untouched");equal(fs.open_handles,0,"no acquired handle")
end

-- Parent durability failure is visible after exclusive publication. The published
-- name is deliberately not removed: it may already be durable and is never an
-- owned temporary after link/rename succeeds.
do
 local fs=fake_fs();local s=store(fs);fs.failure.parent_sync=true;local ref,e=s:commit("project_a",ONE)
 check(ref==nil and e and e.code=="PARENT_SYNC_FAILED","parent sync visible");equal(fs.files[path("project_a",digests[ONE])],ONE,"published asset not destructively rolled back")
end

-- Loads never resume a partial capture. Missing, short, invalid-WAV, hash, and
-- read failures all reach the lifecycle as explicit failures.
do
 local fs=fake_fs();local s=store(fs);local ref=assert(s:commit("project_a",ONE));fs.files[ref.path]=nil;fs.files[ref.path..".pending-fixed"]=ONE
 local value,e=s:load("project_a",ref);check(value==nil and e and e.code=="MISSING_ASSET","partial never resumes")
 fs.files[ref.path]="short";value,e=s:load("project_a",ref);check(value==nil and e and e.code=="ASSET_LENGTH_MISMATCH","short visible")
 fs.files[ref.path]=TWO;value,e=s:load("project_a",ref);check(value==nil and e and e.code=="ASSET_HASH_MISMATCH","hash visible")
 fs.files[ref.path]=wav("11111111",9000);value,e=s:load("project_a",ref);check(value==nil and e and e.code=="ASSET_METADATA_MISMATCH","metadata visible")
 fs.failure.read=true;value,e=s:load("project_a",ref);check(value==nil and e and e.code=="READ_FAILED","read visible")
end

-- Clear knows only explicitly named project-owned temporary paths. Durable audio
-- stays referenced until an explicit complete reference list permits reclamation.
do
 local fs=fake_fs();local s=store(fs);local ref=assert(s:commit("project_a",ONE));local temp=assert(s:temporary_path("project_a","worker_7"));fs.files[temp]="partial"
 check(s:clear("project_a",{"worker_7"}));equal(fs.files[temp],nil);equal(fs.files[ref.path],ONE,"clear keeps durable")
 local ok,e=s:clear("project_a",{"../other"});check(ok==nil and e and e.code=="INVALID_TEMPORARY","temp traversal")
 equal(s:reclaim("project_a",ref,{ref}),false,"live ref blocks reclaim");check(s:reclaim("project_a",ref,{}));equal(fs.files[ref.path],nil,"explicit unreferenced reclaim")
end

-- The accepted format is the native C publisher's WAV format, including its
-- 44-byte header. Exact 45-second buffers are accepted; longer and non-WAV data
-- are rejected before any directory/write action.
do
 local exact=wav(string.rep("\0",8000*45*8),8000);equal(#exact,44+8000*45*8,"header included")
 local fs=fake_fs();local s=store(fs);check(s:commit("project_a",exact),"exact 45 seconds accepted")
 local too_long=wav(string.rep("\0",8000*45*8+8),8000);local value,e=s:commit("project_b",too_long);check(value==nil and e and e.code=="CAPTURE_TOO_LONG","long WAV rejected")
 local raw,e2=s:commit("project_b","raw float bytes");check(raw==nil and e2 and e2.code=="INVALID_WAV","raw bytes rejected")
 local small=store(fake_fs(),{max_bytes=#ONE-1});local over,e3=small:commit("project_a",ONE);check(over==nil and e3 and e3.code=="ASSET_TOO_LARGE","configured byte cap")
end

-- Directory/open/invalid-handle/hash/cleanup failures surface without fallback.
do
 for _,mode in ipairs({"mkdir","open","invalid_handle"}) do
  local fs=fake_fs();fs.failure[mode]=true;local value,e=store(fs):commit("project_a",ONE);local expected=mode=="mkdir" and "MKDIR_FAILED" or "OPEN_FAILED";check(value==nil and e and e.code==expected,mode.." visible");equal(fs.open_handles,0,mode.." no leak")
 end
 local fs=fake_fs();local bad=assert(Assets.new({fs=fs,hash=function() error("hash") end,root="rd-assets"}));local value,e=bad:commit("project_a",ONE);check(value==nil and e and e.code=="HASH_FAILED","hash visible")
 local nofs,e2=Assets.new({fs={},hash=digest,root="rd-assets"});check(nofs==nil and e2 and e2.code=="INVALID_FILESYSTEM","durability methods required")
end
print("rhythm_doctor assets: "..total.." checks")
