-- Project-owned immutable WAV capture assets for Rhythm Doctor.
--
-- Format contract: exact 44-byte RIFF/WAVE, IEEE float32, stereo, little-endian,
-- 8 kHz..192 kHz. Frames must not exceed the native capture's 45-second limit.
-- Host IO is injected. `open_new` and `rename_new` must create names exclusively;
-- `sync_file` and `sync_parent` must provide durable barriers before success.
local Assets = {
  REFERENCE_VERSION = 1,
  WAV_HEADER_BYTES = 44,
  MAX_SECONDS = 45,
  MIN_SAMPLE_RATE = 8000,
  MAX_SAMPLE_RATE = 192000,
}
Assets.MAX_BYTES = Assets.WAV_HEADER_BYTES + Assets.MAX_SECONDS * Assets.MAX_SAMPLE_RATE * 2 * 4

local Store = {}
Store.__index = Store

local function result(code, detail) return nil, { code = code, detail = detail } end
local function safe_name(value)
  return type(value) == "string" and #value >= 1 and #value <= 64 and value:match("^[A-Za-z0-9][A-Za-z0-9_-]*$") ~= nil
end
local function hex_digest(value) return type(value) == "string" and #value == 64 and value:match("^[0-9a-f]+$") ~= nil end
local function integer(value) return type(value) == "number" and value >= 0 and value % 1 == 0 end
local function call(method, ...)
  local ok, first, second = pcall(method, ...)
  if not ok then return nil, first end
  return first, second
end
local function exact_keys(value, keys)
  for key in pairs(value) do if not keys[key] then return false end end
  return true
end
local function strict_array(value)
  if type(value) ~= "table" then return false end
  local count = 0
  for key in pairs(value) do if not integer(key) or key < 1 then return false end; count = count + 1 end
  return count == #value
end

local function little_u16(bytes, offset)
  local a, b = bytes:byte(offset, offset + 1)
  if not b then error("short WAV field") end
  return a + b * 256
end

local function little_u32(bytes, offset)
  local a, b, c, d = bytes:byte(offset, offset + 3)
  if not d then error("short WAV field") end
  return a + b * 256 + c * 65536 + d * 16777216
end

local function wav_details(bytes)
  if type(bytes) ~= "string" or #bytes < Assets.WAV_HEADER_BYTES or bytes:sub(1, 4) ~= "RIFF" or
      bytes:sub(9, 16) ~= "WAVEfmt " or bytes:sub(37, 40) ~= "data" then return result("INVALID_WAV") end
  local ok, riff_size, fmt_size, encoding, channels, sample_rate, byte_rate, block_align, bits, data_bytes = pcall(function()
    local riff = little_u32(bytes, 5)
    local fmt = little_u32(bytes, 17)
    local form, channel_count = little_u16(bytes, 21), little_u16(bytes, 23)
    local rate, rate_bytes = little_u32(bytes, 25), little_u32(bytes, 29)
    local align, width = little_u16(bytes, 33), little_u16(bytes, 35)
    local data = little_u32(bytes, 41)
    return riff, fmt, form, channel_count, rate, rate_bytes, align, width, data
  end)
  if not ok or riff_size ~= #bytes - 8 or fmt_size ~= 16 or encoding ~= 3 or channels ~= 2 or bits ~= 32 or
      block_align ~= 8 or sample_rate < Assets.MIN_SAMPLE_RATE or sample_rate > Assets.MAX_SAMPLE_RATE or
      byte_rate ~= sample_rate * 8 or data_bytes ~= #bytes - Assets.WAV_HEADER_BYTES or data_bytes % 8 ~= 0 then
    return result("INVALID_WAV")
  end
  local frames = data_bytes / 8
  if frames > sample_rate * Assets.MAX_SECONDS then return result("CAPTURE_TOO_LONG") end
  return { format = "wav-f32le-stereo", sample_rate = sample_rate, frame_count = frames }
end

function Assets.new(deps)
  deps = deps or {}
  local fs = deps.fs
  if type(fs) ~= "table" or type(fs.mkdir_all) ~= "function" or type(fs.exists) ~= "function" or type(fs.read) ~= "function" or
      type(fs.open_new) ~= "function" or type(fs.rename_new) ~= "function" or type(fs.sync_file) ~= "function" or
      type(fs.sync_parent) ~= "function" or type(fs.remove) ~= "function" then return result("INVALID_FILESYSTEM") end
  if type(deps.hash) ~= "function" then return result("INVALID_HASHER") end
  local root = deps.root or "rhythm-doctor-assets"
  if not safe_name(root) then return result("INVALID_ROOT") end
  local max_bytes = deps.max_bytes or Assets.MAX_BYTES
  if not integer(max_bytes) or max_bytes < Assets.WAV_HEADER_BYTES or max_bytes > Assets.MAX_BYTES then return result("INVALID_MAX_BYTES") end
  if deps.nonce ~= nil and type(deps.nonce) ~= "function" then return result("INVALID_NONCE") end
  return setmetatable({ fs = fs, hash = deps.hash, root = root, max_bytes = max_bytes, nonce = deps.nonce, sequence = 0 }, Store)
end
function Store:_project_root(project_id) return self.root .. "/" .. project_id end
function Store:_asset_path(project_id, digest) return self:_project_root(project_id) .. "/audio/" .. digest .. ".wav" end
function Store:_validate_project(project_id) if not safe_name(project_id) then return result("INVALID_PROJECT") end; return true end
function Store:_validate_reference(project_id, reference)
  local valid, err = self:_validate_project(project_id); if not valid then return nil, err end
  if type(reference) ~= "table" or not exact_keys(reference, { schema_version=true, project_id=true, sha256=true, byte_count=true,
      path=true, format=true, sample_rate=true, frame_count=true }) or reference.schema_version ~= Assets.REFERENCE_VERSION or
      not safe_name(reference.project_id) or not hex_digest(reference.sha256) or not integer(reference.byte_count) or
      reference.byte_count < Assets.WAV_HEADER_BYTES or reference.byte_count > self.max_bytes or reference.format ~= "wav-f32le-stereo" or
      not integer(reference.sample_rate) or reference.sample_rate < Assets.MIN_SAMPLE_RATE or reference.sample_rate > Assets.MAX_SAMPLE_RATE or
      not integer(reference.frame_count) or reference.frame_count > reference.sample_rate * Assets.MAX_SECONDS or
      reference.byte_count ~= Assets.WAV_HEADER_BYTES + reference.frame_count * 8 or type(reference.path) ~= "string" then return result("INVALID_REFERENCE") end
  if reference.project_id ~= project_id then return result("PROJECT_MISMATCH") end
  if reference.path ~= self:_asset_path(project_id, reference.sha256) then return result("INVALID_REFERENCE") end
  return true
end
function Store:_digest(bytes)
  local digest, problem = call(self.hash, bytes)
  if not hex_digest(digest) then return result("HASH_FAILED", problem) end
  return digest
end
function Store:_ensure_audio_directory(project_id)
  local made, problem = call(self.fs.mkdir_all, self.fs, self:_project_root(project_id) .. "/audio")
  if not made then return result("MKDIR_FAILED", problem) end
  return true
end
function Store:_remove_owned(path)
  local removed, problem = call(self.fs.remove, self.fs, path)
  if not removed then return false, problem end
  return true
end
function Store:_close_owned(file)
  if type(file) == "table" and type(file.close) == "function" then return call(file.close, file) end
  return true
end
function Store:_staging_failure(file, path, code, detail)
  local _, close_problem = self:_close_owned(file)
  local removed, cleanup_problem = self:_remove_owned(path)
  if not removed then return result(code, { cause=detail, close=close_problem, cleanup=cleanup_problem }) end
  if close_problem then return result(code, { cause=detail, close=close_problem }) end
  return result(code, detail)
end
function Store:_verify_contents(bytes, reference, corrupt_code)
  if #bytes ~= reference.byte_count then return result(corrupt_code, "byte count") end
  local details, format_error = wav_details(bytes); if not details then return nil, format_error end
  if details.format ~= reference.format or details.sample_rate ~= reference.sample_rate or details.frame_count ~= reference.frame_count then
    return result(corrupt_code, "wav metadata")
  end
  local digest, digest_error = self:_digest(bytes); if not digest then return nil, digest_error end
  if digest ~= reference.sha256 then return result(corrupt_code, "sha256") end
  return true
end
function Store:_existing_reference(reference)
  local bytes, problem = call(self.fs.read, self.fs, reference.path)
  if type(bytes) ~= "string" then return result("EXISTING_ASSET_CORRUPT", problem or "unreadable") end
  local valid, err = self:_verify_contents(bytes, reference, "EXISTING_ASSET_CORRUPT")
  if not valid then return nil, err end
  return reference
end
function Store:_next_nonce()
  self.sequence = self.sequence + 1
  local nonce = self.nonce and call(self.nonce, self.sequence) or tostring(self.sequence)
  if not safe_name(nonce) then return result("INVALID_NONCE") end
  return nonce
end

-- A successful return means bytes were fully written, file-synced, closed,
-- re-read and hashed, exclusively linked, and parent-directory-synced.
function Store:commit(project_id, bytes)
  local valid, err = self:_validate_project(project_id); if not valid then return nil, err end
  if type(bytes) ~= "string" then return result("INVALID_AUDIO") end
  if #bytes > self.max_bytes then return result("ASSET_TOO_LARGE") end
  local details, format_error = wav_details(bytes); if not details then return nil, format_error end
  local digest, digest_error = self:_digest(bytes); if not digest then return nil, digest_error end
  local reference = { schema_version=Assets.REFERENCE_VERSION, project_id=project_id, sha256=digest, byte_count=#bytes,
    path=self:_asset_path(project_id,digest), format=details.format, sample_rate=details.sample_rate, frame_count=details.frame_count }
  valid, err = self:_ensure_audio_directory(project_id); if not valid then return nil, err end
  local exists, exists_problem = call(self.fs.exists, self.fs, reference.path)
  if exists == nil then return result("EXISTS_FAILED", exists_problem) end
  if exists then return self:_existing_reference(reference) end
  local nonce, nonce_error = self:_next_nonce(); if not nonce then return nil, nonce_error end
  local temporary = reference.path .. ".pending-" .. nonce
  local file, open_problem = call(self.fs.open_new, self.fs, temporary, "wb")
  if not file then return result("OPEN_FAILED", open_problem) end -- no ownership on failed exclusive open
  if type(file.write) ~= "function" or type(file.close) ~= "function" then return self:_staging_failure(file, temporary, "OPEN_FAILED", "invalid handle") end
  local written, write_problem = call(file.write, file, bytes)
  if written ~= #bytes then return self:_staging_failure(file, temporary, "WRITE_FAILED", write_problem or "partial write") end
  local synced, sync_problem = call(self.fs.sync_file, self.fs, file)
  if not synced then return self:_staging_failure(file, temporary, "FILE_SYNC_FAILED", sync_problem) end
  local closed, close_problem = call(file.close, file)
  if not closed then return self:_staging_failure(nil, temporary, "CLOSE_FAILED", close_problem) end
  local staged, staged_problem = call(self.fs.read, self.fs, temporary)
  if type(staged) ~= "string" then return self:_staging_failure(nil, temporary, "STAGING_VERIFY_FAILED", staged_problem) end
  if staged ~= bytes then return self:_staging_failure(nil, temporary, "STAGING_VERIFY_FAILED", "bytes") end
  local staged_digest, staged_digest_error = self:_digest(staged)
  if not staged_digest or staged_digest ~= digest then return self:_staging_failure(nil, temporary, "STAGING_VERIFY_FAILED", staged_digest_error or "sha256") end
  local renamed, rename_problem = call(self.fs.rename_new, self.fs, temporary, reference.path)
  if not renamed then return self:_staging_failure(nil, temporary, "RENAME_FAILED", rename_problem) end
  local parent_synced, parent_problem = call(self.fs.sync_parent, self.fs, reference.path)
  if not parent_synced then return result("PARENT_SYNC_FAILED", parent_problem) end
  return reference
end

-- No resume path exists: a missing/corrupt committed WAV is reported to the
-- lifecycle. It must load EMPTY rather than adopt a staging artifact.
function Store:load(project_id, reference)
  local valid, err = self:_validate_reference(project_id, reference); if not valid then return nil, err end
  local exists, exists_problem = call(self.fs.exists, self.fs, reference.path)
  if exists == nil then return result("EXISTS_FAILED", exists_problem) end
  if not exists then return result("MISSING_ASSET") end
  local bytes, read_problem = call(self.fs.read, self.fs, reference.path)
  if type(bytes) ~= "string" then return result("READ_FAILED", read_problem) end
  if #bytes ~= reference.byte_count then return result("ASSET_LENGTH_MISMATCH") end
  local details, format_error = wav_details(bytes); if not details then return result("INVALID_WAV", format_error) end
  if details.sample_rate ~= reference.sample_rate or details.frame_count ~= reference.frame_count then return result("ASSET_METADATA_MISMATCH") end
  local digest, digest_error = self:_digest(bytes); if not digest then return nil, digest_error end
  if digest ~= reference.sha256 then return result("ASSET_HASH_MISMATCH") end
  return bytes
end
function Store:temporary_path(project_id, name)
  local valid, err=self:_validate_project(project_id); if not valid then return nil,err end
  if not safe_name(name) then return result("INVALID_TEMPORARY") end
  return self:_project_root(project_id).."/tmp/"..name..".part"
end
function Store:clear(project_id, names)
  local valid,err=self:_validate_project(project_id); if not valid then return nil,err end
  if not strict_array(names) then return result("INVALID_TEMPORARY") end
  for _,name in ipairs(names) do
    local temporary,temp_error=self:temporary_path(project_id,name); if not temporary then return nil,temp_error end
    local exists,exists_problem=call(self.fs.exists,self.fs,temporary); if exists==nil then return result("EXISTS_FAILED",exists_problem) end
    if exists then local removed,remove_problem=self:_remove_owned(temporary); if not removed then return result("REMOVE_FAILED",remove_problem) end end
  end
  return true
end
function Store:reclaim(project_id, reference, remaining_references)
  local valid,err=self:_validate_reference(project_id,reference); if not valid then return nil,err end
  if not strict_array(remaining_references) then return result("INVALID_REFERENCE_LIST") end
  for _,current in ipairs(remaining_references) do
    local current_valid,current_error=self:_validate_reference(project_id,current); if not current_valid then return nil,current_error end
    if current.path==reference.path and current.sha256==reference.sha256 then return false end
  end
  local exists,exists_problem=call(self.fs.exists,self.fs,reference.path); if exists==nil then return result("EXISTS_FAILED",exists_problem) end
  if not exists then return true end
  local removed,remove_problem=self:_remove_owned(reference.path); if not removed then return result("REMOVE_FAILED",remove_problem) end
  return true
end
return Assets
