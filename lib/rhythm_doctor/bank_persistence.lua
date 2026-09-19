-- Durable READY-bank envelope.  Jobs and paint history are deliberately not
-- serialised: a reload restores only completed analysis data and begins with a
-- fresh source-paint journal.
local function dependency(name, path)
  if type(include) == "function" then return include(path) end
  return require(name)
end

local Bank = dependency("rhythm_doctor.bank", "mosaic/lib/rhythm_doctor/bank")
local Persistence = { VERSION = 1 }

local function copy(value)
  if type(value) ~= "table" then return value end
  local out = {}
  for key, item in pairs(value) do out[key] = copy(item) end
  return out
end

local function result(code) return nil, { code = code } end
local function exact_keys(value)
  if type(value) ~= "table" then return false end
  for key in pairs(value) do if key ~= "version" and key ~= "bank" then return false end end
  return true
end

-- Missing data is an EMPTY legacy project.  A present but unrecognised or
-- malformed envelope is rejected before project state changes.
function Persistence.decode(value, expected)
  if value == nil then return nil, { code = "EMPTY" } end
  if not exact_keys(value) or value.version ~= Persistence.VERSION then return result("UNKNOWN_BANK_SCHEMA") end
  if not Bank.valid_ready(value.bank, expected) then return result("INVALID_BANK") end
  return copy(value.bank)
end

function Persistence.encode(bank)
  if not Bank.valid_ready(bank) then return result("INVALID_BANK") end
  return { version = Persistence.VERSION, bank = copy(bank) }
end

function Persistence.validate(value)
  if value == nil then return true end
  local bank, problem = Persistence.decode(value)
  return bank ~= nil, problem and problem.code
end

return Persistence
