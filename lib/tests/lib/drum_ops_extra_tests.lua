-- drum_ops: drum, tresillo and numeric-repetitor outputs over their reachable parameter
-- domains. The oracles below use only integer arithmetic (math.floor, %, *), never bit32
-- nor native bitwise operators, so they stay valid when the implementation switches
-- between the two. Domains come from the trigger editor that calls these functions
-- (lib/pages/trigger_edit_page/trigger_edit_page.lua): drum/tresillo bank 1..5 and
-- pattern 1..128, tresillo length = tresillo_amount option {8,16,...,64} (mosaic.lua), NR
-- prime 1..32, mask 1..4 and factor 1..16, painted steps 1..64.
local drum_ops = include("mosaic/lib/helpers/drum_ops")
local tables = include("mosaic/lib/helpers/drum_ops_tables")

local BANKS = {tables.table_t_r_e, tables.table_dr_bd, tables.table_dr_sd, tables.table_dr_ch, tables.table_dr_oh}

-- MSB-first bit list of a byte array, by arithmetic.
local function bits_of(bytes)
  local bits = {}
  for _, byte in ipairs(bytes) do
    for i = 7, 0, -1 do
      bits[#bits + 1] = math.floor(byte / 2 ^ i) % 2 == 1
    end
  end
  return bits
end

local BITS = {}
for bank = 1, 5 do
  BITS[bank] = {}
  for p = 1, 128 do BITS[bank][p] = bits_of(BANKS[bank][p]) end
end

local function cyclic(bits, k)
  return bits[(k - 1) % #bits + 1]
end

local function drum_oracle(bank, pattern, step)
  -- A drum pattern is a 16-step bar that repeats.
  return BITS[bank][pattern][(step - 1) % 16 + 1]
end

local function tresillo_oracle(bank, p1, p2, len, step)
  -- 3/3/2 (README 405): a cycle of 8m steps, m = floor(len / 8), split 3m | 3m | 2m.
  -- Pattern 1 restarts at each of the first two segments, pattern 2 plays the last;
  -- each pattern repeats at its stored bit length (characterisation for the repeat).
  local m = math.floor(len / 8)
  local s = (step - 1) % (8 * m) + 1
  if s <= 3 * m then return cyclic(BITS[bank][p1], s) end
  if s <= 6 * m then return cyclic(BITS[bank][p1], s - 3 * m) end
  return cyclic(BITS[bank][p2], s - 6 * m)
end

local function arith_and(a, b)
  local result, place = 0, 1
  while a > 0 and b > 0 do
    if a % 2 == 1 and b % 2 == 1 then result = result + place end
    a, b, place = math.floor(a / 2), math.floor(b / 2), place * 2
  end
  return result
end

local function arith_or(a, b)
  local result, place = 0, 1
  while a > 0 or b > 0 do
    if a % 2 == 1 or b % 2 == 1 then result = result + place end
    a, b, place = math.floor(a / 2), math.floor(b / 2), place * 2
  end
  return result
end

local NR_MASKS = {0x0F0F, 0xF003, 0x01F0}

local function nr_oracle(prime, mask, factor, step)
  -- characterisation: the Numeric Repetitor as implemented (README 407 names it only).
  if prime < 1 then prime = prime + 32 end
  if mask < 1 then mask = mask + 4 end
  if factor < 1 then factor = factor + 17 end
  local rhythm = tables.table_nr[prime]
  if NR_MASKS[mask] then rhythm = arith_and(rhythm, NR_MASKS[mask]) end
  local product = rhythm * factor
  local folded = arith_or(product % 65536, math.floor(product / 65536))
  local s = (step - 1) % 16 + 1
  return math.floor(folded / 2 ^ (16 - s)) % 2 == 1
end

local function mismatches(list, label, actual, expected)
  if actual ~= expected and #list < 5 then
    list[#list + 1] = label .. " got " .. tostring(actual) .. " want " .. tostring(expected)
  end
end

function test_drum_ops_extra_drum_matches_bit_oracle_over_whole_domain()
  local bad = {}
  for bank = 1, 5 do
    for pattern = 1, 128 do
      for step = 1, 96 do
        mismatches(bad, ("drum(%d,%d,%d)"):format(bank, pattern, step),
          drum_ops.drum(bank, pattern, step), drum_oracle(bank, pattern, step))
      end
    end
  end
  luaunit.assert_equals(bad, {})
end

function test_drum_ops_extra_drum_reads_bits_most_significant_first()
  -- characterisation: dr_bd pattern 1 is 10000010 00000000, so steps 1 and 7 hit.
  local hits = {}
  for step = 1, 16 do
    if drum_ops.drum(2, 1, step) then hits[#hits + 1] = step end
  end
  luaunit.assert_equals(hits, {1, 7})
  -- t_r_e pattern 2 is 00100000 00000001 [00000000]: only the first 16 bits are a bar.
  hits = {}
  for step = 1, 24 do
    if drum_ops.drum(1, 2, step) then hits[#hits + 1] = step end
  end
  luaunit.assert_equals(hits, {3, 16, 19})
end

function test_drum_ops_extra_drum_guards_return_numeric_one()
  -- characterisation (suspected defect: every guard returns the truthy number 1, not
  -- false, so an out-of-range call would paint a trig; unreachable from the trigger editor).
  luaunit.assert_equals(drum_ops.drum(0, 1, 1), 1)
  luaunit.assert_equals(drum_ops.drum(6, 1, 1), 1)
  luaunit.assert_equals(drum_ops.drum(2, 1, 0), 1)
  luaunit.assert_equals(drum_ops.drum(2, 129, 1), 1)
  -- the passing side of each boundary returns a boolean
  luaunit.assert_equals(drum_ops.drum(1, 1, 1), false)
  luaunit.assert_equals(drum_ops.drum(5, 1, 1), drum_oracle(5, 1, 1))
  luaunit.assert_equals(drum_ops.drum(2, 1, 1), true)
  luaunit.assert_equals(drum_ops.drum(2, 128, 1), drum_oracle(2, 128, 1))
  luaunit.assert_equals(type(drum_ops.drum(2, 128, 1)), "boolean")
end

function test_drum_ops_extra_tresillo_matches_332_oracle_over_whole_domain()
  local bad = {}
  for bank = 1, 5 do
    for len = 8, 64, 8 do
      for p = 1, 128 do
        local p2 = 129 - p
        for step = 1, 64 do
          mismatches(bad, ("tresillo(%d,%d,%d,%d,%d)"):format(bank, p, p2, len, step),
            drum_ops.tresillo(bank, p, p2, len, step), tresillo_oracle(bank, p, p2, len, step))
          mismatches(bad, ("tresillo(%d,%d,%d,%d,%d)"):format(bank, p2, p, len, step),
            drum_ops.tresillo(bank, p2, p, len, step), tresillo_oracle(bank, p2, p, len, step))
        end
      end
    end
  end
  luaunit.assert_equals(bad, {})
end

function test_drum_ops_extra_tresillo_is_three_three_two()
  -- README 405: 3/3/2 ratio. dr_bd pattern 2 is 10000000 10000000, one hit per segment.
  local function hits(len, last)
    local out = {}
    for step = 1, last do
      if drum_ops.tresillo(2, 2, 2, len, step) then out[#out + 1] = step end
    end
    return out
  end
  luaunit.assert_equals(hits(8, 16), {1, 4, 7, 9, 12, 15})
  luaunit.assert_equals(hits(16, 16), {1, 7, 13})
  -- characterisation: at x24 the 9-step segments re-read bit 9 of the 16-bit bar.
  luaunit.assert_equals(hits(24, 24), {1, 9, 10, 18, 19})
end

function test_drum_ops_extra_tresillo_segments_use_pattern_one_then_two()
  -- README 405 ratio; pattern 1 fills the two 3m segments, pattern 2 the 2m tail.
  local out = {}
  for step = 1, 8 do out[step] = drum_ops.tresillo(2, 3, 2, 8, step) end
  -- dr_bd 3 = 00100010: bits 1..3 = 0,0,1 twice, then dr_bd 2 bits 1..2 = 1,0
  luaunit.assert_equals(out, {false, false, true, false, false, true, true, false})
end

function test_drum_ops_extra_tresillo_wraps_short_banks_at_their_bit_length()
  -- characterisation: len 48 gives m = 6, so an 18-step segment on a 16-bit bank wraps.
  luaunit.assert_equals(drum_ops.tresillo(2, 2, 2, 48, 17), true)
  luaunit.assert_equals(drum_ops.tresillo(2, 2, 2, 48, 18), false)
  luaunit.assert_equals(drum_ops.tresillo(2, 2, 2, 48, 19), true) -- segment 2 restarts at 3m + 1
  -- t_r_e is 24 bits long: bit 17 of pattern 2 (third byte 00000000) is read, not wrapped.
  luaunit.assert_equals(drum_ops.tresillo(1, 2, 2, 48, 16), true)
  luaunit.assert_equals(drum_ops.tresillo(1, 2, 2, 48, 17), false)
end

function test_drum_ops_extra_tresillo_length_uses_whole_multiples_of_eight()
  -- characterisation: lengths are floored to a multiple of 8.
  for step = 1, 32 do
    luaunit.assert_equals(drum_ops.tresillo(3, 7, 40, 15, step), drum_ops.tresillo(3, 7, 40, 8, step))
    luaunit.assert_equals(drum_ops.tresillo(3, 7, 40, 23, step), drum_ops.tresillo(3, 7, 40, 16, step))
  end
end

function test_drum_ops_extra_tresillo_guards_return_numeric_one()
  -- characterisation (suspected defect: guards return the truthy number 1, as for drum).
  luaunit.assert_equals(drum_ops.tresillo(0, 2, 2, 8, 1), 1)
  luaunit.assert_equals(drum_ops.tresillo(6, 2, 2, 8, 1), 1)
  luaunit.assert_equals(drum_ops.tresillo(2, 2, 2, 7, 2), 1)
  luaunit.assert_equals(drum_ops.tresillo(2, 2, 2, 8, 0), 1)
  luaunit.assert_equals(drum_ops.tresillo(2, 129, 2, 8, 2), 1)
  luaunit.assert_equals(drum_ops.tresillo(2, 2, 129, 8, 2), 1)
  -- passing side of each boundary
  luaunit.assert_equals(drum_ops.tresillo(1, 2, 2, 8, 1), false)
  luaunit.assert_equals(drum_ops.tresillo(5, 128, 128, 8, 1), tresillo_oracle(5, 128, 128, 8, 1))
  luaunit.assert_equals(drum_ops.tresillo(2, 2, 2, 8, 2), false)
  luaunit.assert_equals(drum_ops.tresillo(2, 2, 2, 8, 1), true)
  luaunit.assert_equals(drum_ops.tresillo(2, 128, 2, 8, 2), tresillo_oracle(2, 128, 2, 8, 2))
  luaunit.assert_equals(drum_ops.tresillo(2, 2, 128, 8, 7), tresillo_oracle(2, 2, 128, 8, 7))
  luaunit.assert_equals(type(drum_ops.tresillo(2, 128, 128, 8, 8)), "boolean")
end

function test_drum_ops_extra_numeric_repetitor_matches_arithmetic_oracle()
  -- Non-positive prime, mask, factor and step are offset once by 32, 4, 17 and 16;
  -- prime -31, factor -16 and step -15 are the lowest that land back on 1.
  local primes, factors = {-31}, {-16}
  for v = 0, 32 do primes[#primes + 1] = v end
  for v = 0, 17 do factors[#factors + 1] = v end
  local bad = {}
  for _, prime in ipairs(primes) do
    for mask = -4, 5 do
      for _, factor in ipairs(factors) do
        for step = -15, 33 do
          mismatches(bad, ("nr(%d,%d,%d,%d)"):format(prime, mask, factor, step),
            drum_ops.nr(prime, mask, factor, step), nr_oracle(prime, mask, factor, step))
        end
      end
    end
  end
  luaunit.assert_equals(bad, {})
end

function test_drum_ops_extra_numeric_repetitor_examples()
  local function hits(prime, mask, factor)
    local out = {}
    for step = 1, 16 do
      if drum_ops.nr(prime, mask, factor, step) then out[#out + 1] = step end
    end
    return out
  end
  -- characterisation: prime 1 (0x8888) unmasked at factor 1 is four on the floor.
  luaunit.assert_equals(hits(1, 4, 1), {1, 5, 9, 13})
  -- mask 1 keeps 0x0F0F, mask 2 keeps 0xF003, mask 3 keeps 0x01F0.
  luaunit.assert_equals(hits(1, 1, 1), {5, 13})
  luaunit.assert_equals(hits(1, 2, 1), {1})
  luaunit.assert_equals(hits(1, 3, 1), {9})
  -- factor 3 on 0x8888 = 0x19998, folded: 0x9998 | 0x1 = 0x9999
  luaunit.assert_equals(hits(1, 4, 3), {1, 4, 5, 8, 9, 12, 13, 16})
  -- mask 5 and above applies no mask; mask 0 wraps to 4, -1 to 3
  luaunit.assert_equals(hits(1, 5, 1), {1, 5, 9, 13})
  luaunit.assert_equals(hits(1, 0, 1), {1, 5, 9, 13})
  luaunit.assert_equals(hits(1, -1, 1), {9})
  -- prime 0 wraps to 32 (0x8544), factor 0 wraps to 17
  luaunit.assert_equals(hits(0, 4, 1), hits(32, 4, 1))
  luaunit.assert_equals(hits(32, 4, 1), {1, 6, 8, 10, 14})
  luaunit.assert_equals(hits(1, 4, 0), hits(1, 4, 17))
  luaunit.assert_equals(type(drum_ops.nr(1, 4, 1, 2)), "boolean")
end

-- Golden census (characterisation): pins the table data as well as the lookup, which the
-- oracles above share with the implementation. {true outputs, position checksum}.
-- Captured 2026-09-11 from the working tree.
local GOLDEN_DRUM = {2876, 342794733}
local GOLDEN_TRESILLO = {52238, 31245931}

local function census(outputs)
  local count, checksum, position = 0, 0, 0
  for value in outputs do
    position = position + 1
    if value == true then
      count = count + 1
      checksum = (checksum * 31 + position) % 1000000007
    end
  end
  return {count, checksum}
end

function test_drum_ops_extra_drum_whole_domain_is_unchanged()
  luaunit.assert_equals(census(coroutine.wrap(function()
    for bank = 1, 5 do
      for pattern = 1, 128 do
        for step = 1, 16 do coroutine.yield(drum_ops.drum(bank, pattern, step)) end
      end
    end
  end)), GOLDEN_DRUM)
end

function test_drum_ops_extra_tresillo_whole_domain_is_unchanged()
  luaunit.assert_equals(census(coroutine.wrap(function()
    for bank = 1, 5 do
      for len = 8, 64, 8 do
        for p = 1, 128 do
          for step = 1, len do coroutine.yield(drum_ops.tresillo(bank, p, 129 - p, len, step)) end
        end
      end
    end
  end)), GOLDEN_TRESILLO)
end
