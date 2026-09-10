-- Characterisation (README 407 names the NE Numeric Repetitor without defining it): every
-- output of drum_ops.nr over its whole input domain is pinned by per-mask counts and a
-- position-weighted checksum, so replacing bit32 or restructuring the bit arithmetic
-- cannot silently change a painted rhythm.
local drum_ops = include("mosaic/lib/helpers/drum_ops")
-- Captured 2026-09-11 at 8bd70b5: {true outputs, checksum} for masks 0..3.
local GOLDEN_NR = {{4465, 948976176}, {2672, 563311833}, {1795, 736905245}, {1715, 62157713}}

local function census(mask)
  local count, checksum, position = 0, 0, 0
  for prime = 1, 32 do
    for factor = 1, 17 do
      for step = 1, 16 do
        position = position + 1
        if drum_ops.nr(prime, mask, factor, step) then
          count = count + 1
          checksum = (checksum * 31 + position) % 1000000007
        end
      end
    end
  end
  return {count, checksum}
end

function test_numeric_repetitor_whole_domain_is_unchanged()
  local actual = {}
  for mask = 0, 3 do actual[mask + 1] = census(mask) end
  luaunit.assert_equals(actual, GOLDEN_NR)
end

function test_numeric_repetitor_wraps_out_of_range_inputs()
  for step = 1, 16 do
    luaunit.assert_equals(drum_ops.nr(0, 0, 0, step - 16), drum_ops.nr(32, 4, 17, step))
    luaunit.assert_equals(drum_ops.nr(5, 1, 3, step + 16), drum_ops.nr(5, 1, 3, step))
  end
end
