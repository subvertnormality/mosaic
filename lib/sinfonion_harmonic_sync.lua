local math = require("math")
local status, periphery = pcall(require, "periphery")
local floor = math.floor
local format = string.format
local insert = table.insert

if not status then
  print("Periphery not found. Sinfonion support disabled.")
  return
end

local Serial = periphery.Serial
local time = os.time

local sinfonion = {}

local SYNC_BUFFER_SIZE = 6 -- Placeholder value
local HARMONIC_SYNC_TX_IRQ_TIMEOUT = 1000 -- Placeholder value

local function millis()
  return floor(time() * 1000)
end

local function debug(msg, ...)
  print(format(msg, ...))
end

local serial = Serial {device = "/dev/ttyS0", baudrate = 115200, databits = 8, parity = "none", stopbits = 1}
local last_interrupt = 0
local buffer = {}
for i = 1, SYNC_BUFFER_SIZE do
  buffer[i] = 0
end
buffer[1] = 0x80
local index = 1
local wait_for_sync = true
local last_clock = 0
local last_beat = 0
local last_step = 0
local last_reset = 0

local function is_alive()
  return millis() - last_interrupt < 10
end

function sinfonion.set_root_note(root)
  buffer[1] = (buffer[1] & ~0x0f) | (root % 12)
end

function sinfonion.rootNote()
  return buffer[1] & 0x0f
end

function sinfonion.set_degree_nr(degree_nr)
  buffer[2] = (buffer[2] & ~0x0f) | degree_nr
end

function sinfonion.degree_nr()
  return buffer[2] & 0x0f
end

function sinfonion.set_mode_nr(mode_nr)
  buffer[3] = (buffer[3] & ~0x0f) | mode_nr
end

function sinfonion.mode_nr()
  return buffer[3] & 0x0f
end

function sinfonion.set_clock(clock)
  buffer[1] = (buffer[1] & ~0x70) | ((clock % 8) << 4)
end

function sinfonion.get_clock()
  return (buffer[1] & 0x70) >> 4
end

function sinfonion.got_next_clock()
  local b = get_clock()
  local got = b ~= last_clock
  last_clock = b
  return got
end

-- Transposition
function sinfonion.set_transposition(trans)
  trans = math.max(-64, math.min(63, trans))
  buffer[4] = (buffer[4] & ~0x7f) | ((trans + 64) & 0x7f)
end

function sinfonion.transposition()
  return (buffer[4] & 0x7f) - 64
end

-- chaotic_detune
function sinfonion.set_chaotic_detune(detune)
  detune = math.max(-1.0, math.min(1.0, detune))
  local detune_int = floor(detune * 63.0) + 63
  buffer[5] = detune_int & 0x7f
end

function sinfonion.chaotic_detune()
  local detune_int = buffer[5] - 63
  return detune_int / 63.0
end

-- harmonic_shift
function sinfonion.set_harmonic_shift(shift)
  buffer[6] = shift + 16
end

function sinfonion.harmonic_shift()
  return buffer[6] - 16
end

-- Beat
function sinfonion.set_beat(beat)
  buffer[2] = (buffer[2] & ~0x70) | ((beat % 8) << 4)
end

function sinfonion.beat()
  return (buffer[2] & 0x70) >> 4
end

function sinfonion.got_next_beat()
  local b = beat()
  local got = b ~= last_beat
  last_beat = b
  return got
end

-- Step
function sinfonion.set_step(step)
  buffer[3] = (buffer[3] & ~0x70) | ((step % 8) << 4)
end

function sinfonion.step()
  return (buffer[3] & 0x70) >> 4
end

function sinfonion.got_next_step()
  local this_step = step()
  local got = this_step ~= last_step
  last_step = this_step
  return got
end

-- Reset
function sinfonion.set_reset(reset_value)
  buffer[6] = (buffer[6] & ~0x60) | ((reset_value % 4) << 5)
end

function sinfonion.reset()
  return (buffer[6] & 0x60) >> 5
end

function sinfonion.got_next_reset()
  local this_reset = reset()
  local got = this_reset ~= last_reset
  last_reset = this_reset
  return got
end

local function handle_rx_irq(byte)
  last_interrupt = millis()
  if byte & 0x80 ~= 0 then
    wait_for_sync = false
    index = 1
    buffer[1] = byte
  elseif not wait_for_sync then
    index = index + 1
    buffer[index] = byte
  end
end

local function handle_tx_irq()
  last_interrupt = millis()
  local byte = buffer[index]
  index = (index % SYNC_BUFFER_SIZE) + 1
  last_sent_byte = byte
  return byte
end

local function dump()
  local values = {}
  for _, v in ipairs(buffer) do
    insert(values, format("%02x", v))
  end
  debug(" " .. table.concat(values, " "))
end

local function send_next()
  serial:write(string.char(buffer[index]))
  index = (index % SYNC_BUFFER_SIZE) + 1
  last_sent_byte = buffer[index]
end

function sinfonion.init()
  local serial_loop = metro.init()
  serial_loop.event = send_next
  serial_loop.time = 0.01
  serial_loop.count = -1
  serial_loop:start()
end

return sinfonion
