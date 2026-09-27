-- Common musical time (docs/musical-merge-extensions-plan.md §1.1).
--
-- Nominal time is exact rational time in whole notes from the common origin.
-- A channel step lasts d = 1 / (16 · m), m the clock-mod multiplier (value for
-- a multiplication, 1 / value for a division, 1 for none). Clock-mod values are
-- converted to exact rationals from their decimal text (5.3 = 53/10), matching
-- the value the sprocket division is computed from. Arithmetic is on reduced
-- integer fractions; an intermediate that cannot be represented exactly
-- returns nil and "unsupported", never a rounded comparison.
local common_time = {}

local maxinteger = math.maxinteger
local UNSUPPORTED = "unsupported"
common_time.UNSUPPORTED = UNSUPPORTED

local function gcd(a, b)
  if a < 0 then a = -a end
  if b < 0 then b = -b end
  while b ~= 0 do a, b = b, a % b end
  return a
end
common_time.gcd = gcd

local function checked_mul(a, b)
  if a == 0 or b == 0 then return 0 end
  local abs_a, abs_b = a < 0 and -a or a, b < 0 and -b or b
  if abs_a > maxinteger // abs_b then return nil end
  return a * b
end

local function checked_add(a, b)
  if (b > 0 and a > maxinteger - b) or (b < 0 and a < -maxinteger - b) then return nil end
  return a + b
end

local function integer(value)
  return math.type(value) == "integer"
end

-- A reduced fraction {n, d} with d > 0.
function common_time.rational(n, d)
  d = d or 1
  if not integer(n) or not integer(d) or d == 0 then return nil, UNSUPPORTED end
  if d < 0 then n, d = -n, -d end
  local g = gcd(n, d)
  if g > 1 then n, d = n // g, d // g end
  return {n, d}
end
local rational = common_time.rational

function common_time.add(a, b)
  if not a or not b then return nil, UNSUPPORTED end
  local g = gcd(a[2], b[2])
  local left = checked_mul(a[1], b[2] // g)
  local right = checked_mul(b[1], a[2] // g)
  local den = checked_mul(a[2], b[2] // g)
  if not left or not right or not den then return nil, UNSUPPORTED end
  local num = checked_add(left, right)
  if not num then return nil, UNSUPPORTED end
  return rational(num, den)
end

function common_time.sub(a, b)
  if not a or not b then return nil, UNSUPPORTED end
  return common_time.add(a, {-b[1], b[2]})
end

function common_time.mul(a, b)
  if not a or not b then return nil, UNSUPPORTED end
  local g1, g2 = gcd(a[1], b[2]), gcd(b[1], a[2])
  if g1 == 0 then g1 = 1 end
  if g2 == 0 then g2 = 1 end
  local num = checked_mul(a[1] // g1, b[1] // g2)
  local den = checked_mul(a[2] // g2, b[2] // g1)
  if not num or not den then return nil, UNSUPPORTED end
  return rational(num, den)
end

function common_time.scale(a, k)
  return common_time.mul(a, {k, 1})
end

function common_time.inverse(a)
  if not a or a[1] == 0 then return nil, UNSUPPORTED end
  return rational(a[2], a[1])
end

-- -1, 0 or 1. Cross-multiplication is checked, so it never rounds.
function common_time.compare(a, b)
  local difference, reason = common_time.sub(a, b)
  if not difference then return nil, reason end
  if difference[1] < 0 then return -1 end
  if difference[1] > 0 then return 1 end
  return 0
end

function common_time.equal(a, b)
  return a ~= nil and b ~= nil and a[1] == b[1] and a[2] == b[2]
end

-- Numeric projection, only for comparing with floating clock values.
function common_time.to_number(a)
  return a[1] / a[2]
end

function common_time.format(a)
  if a[2] == 1 then return tostring(a[1]) end
  return a[1] .. "/" .. a[2]
end

-- Exact rational from decimal text such as "5.3", "12" or "1.25".
function common_time.from_decimal(text)
  if type(text) ~= "string" then return nil, UNSUPPORTED end
  local whole, fraction = text:match("^(%d+)%.(%d+)$")
  if not whole then
    whole = text:match("^(%d+)$")
    fraction = ""
  end
  if not whole or #whole + #fraction > 15 then return nil, UNSUPPORTED end
  local digits = math.tointeger(tonumber(whole .. fraction))
  if not digits then return nil, UNSUPPORTED end
  return rational(digits, math.tointeger(10 ^ #fraction))
end

-- The decimal text of a clock-mod value: the shortest representation that
-- reads back to exactly the same number the sprocket division uses.
local function decimal_text(value)
  for places = 0, 6 do
    local text = string.format("%." .. places .. "f", value)
    if tonumber(text) == value then return text end
  end
  return nil
end
common_time.decimal_text = decimal_text

-- The multiplier m of a clock mod ({type, value}) as an exact rational.
function common_time.multiplier(clock_mod)
  if type(clock_mod) ~= "table" then return rational(1, 1) end
  if clock_mod.type ~= "clock_multiplication" and clock_mod.type ~= "clock_division" then
    return rational(1, 1)
  end
  local value = clock_mod.value
  if type(value) ~= "number" or value <= 0 or value ~= value or value == math.huge then
    return nil, UNSUPPORTED
  end
  local text = decimal_text(value)
  if not text then return nil, UNSUPPORTED end
  local exact = common_time.from_decimal(text)
  if not exact or exact[1] == 0 then return nil, UNSUPPORTED end
  if clock_mod.type == "clock_division" then return common_time.inverse(exact) end
  return exact
end

-- d = 1 / (16 · m) whole notes: the sole duration conversion.
function common_time.step_duration(clock_mod)
  local m, reason = common_time.multiplier(clock_mod)
  if not m then return nil, reason end
  return rational(m[2], checked_mul(16, m[1]) or 0)
end

-- The master duration: the same formula with m = 1.
common_time.MASTER_STEP = {1, 16}

-- Lowest common denominator of the given rationals (nil when it overflows),
-- so every nominal time of the query can be compared as a plain integer.
function common_time.common_denominator(values)
  local result = 1
  for _, value in ipairs(values) do
    local g = gcd(result, value[2])
    result = checked_mul(result, value[2] // g)
    if not result then return nil, UNSUPPORTED end
  end
  return result
end

-- The integer numerator of `value` over denominator `denominator`, which must
-- be a multiple of value's own denominator.
function common_time.numerator_over(value, denominator)
  if denominator % value[2] ~= 0 then return nil, UNSUPPORTED end
  local result = checked_mul(value[1], denominator // value[2])
  if not result then return nil, UNSUPPORTED end
  return result
end

common_time.checked_mul = checked_mul
common_time.checked_add = checked_add

return common_time
