-- Wire serialization owns receiver lookup, validation and ordered CC bytes.
-- Keep the owning module reference: NRPN honors replacement of its cc method.
local nrpn_codec = include("mosaic/lib/devices/nrpn_codec")
local output = {}

function output.new(m_midi)
  local function cc(cc_msb, cc_lsb, value, channel, device)
    if midi_devices[device] ~= nil then
      -- Send MSB
      local cc_msb_value = cc_lsb and math.floor(value / 128) or value
      midi_devices[device]:cc(cc_msb, cc_msb_value, channel)

      -- Send LSB
      if cc_lsb ~= nil then
        midi_devices[device]:cc(cc_lsb, value % 128, channel)
      end
    end
  end

  local function nrpn(nrpn_msb, nrpn_lsb, value, channel, device, mode)
    -- Validate the whole message before selecting a receiver parameter.
    local msb, lsb = nrpn_codec.encode(value, mode)
    for _,address in ipairs({nrpn_msb, nrpn_lsb}) do
      assert(type(address) == "number" and address % 1 == 0 and address >= 0 and address <= 127,
        "NRPN address must contain two 7-bit integers")
    end
    assert(nrpn_msb ~= nil and nrpn_lsb ~= nil, "NRPN address is required")
    assert(type(channel) == "number" and channel % 1 == 0 and channel >= 1 and channel <= 16,
      "NRPN channel must be from 1 to 16")
    m_midi.cc(99, nil, nrpn_msb, channel, device)
    m_midi.cc(98, nil, nrpn_lsb, channel, device)
    m_midi.cc(6, nil, msb, channel, device)
    m_midi.cc(38, nil, lsb, channel, device)
  end


  return cc, nrpn
end

return output
