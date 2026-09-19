-- Wire serialization owns receiver lookup, validation and ordered CC bytes.
-- Keep the owning module reference: NRPN honors replacement of its cc method.
local nrpn_codec = include("mosaic/lib/devices/nrpn_codec")
local output = {}

function output.new(m_midi)
  -- An NRPN is four CCs on the wire but one parameter to the receiver, so the
  -- listener hears it once, as an NRPN, and not as four CC writes.
  local inside_nrpn = false

  local function cc(cc_msb, cc_lsb, value, channel, device)
    local port = midi_devices[device]
    if port ~= nil then
      local status = 0xB0 + (channel or 1) - 1
      local cc_msb_value = cc_lsb and math.floor(value / 128) or value
      -- Every parameter write passes here, whoever produced it: a step, a
      -- slide, a live control, the lock lookahead itself. Reporting it from
      -- this one place is what lets the lookahead know when something else has
      -- changed what the receiver holds, without a hook in every caller.
      local listener = m_midi.parameter_write_listener
      if listener and not inside_nrpn then listener("cc", device, channel or 1, cc_msb) end
      -- A value too close after a delayed note waits for the gap between notes.
      local due = m_midi.parameter_deadline and m_midi.parameter_deadline(port, channel)
      if due then
        m_midi.hold_parameter(due, port, status, cc_msb, cc_msb_value, channel)
        if cc_lsb ~= nil then m_midi.hold_parameter(due, port, status, cc_lsb, value % 128, channel) end
        return
      end
      -- Send MSB
      if not m_midi.send_three(port, status, cc_msb, cc_msb_value) then
        m_midi.flush_output_batch()
        port:cc(cc_msb, cc_msb_value, channel)
      end

      -- Send LSB
      if cc_lsb ~= nil then
        if not m_midi.send_three(port, status, cc_lsb, value % 128) then
          m_midi.flush_output_batch()
          port:cc(cc_lsb, value % 128, channel)
        end
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
    local listener = m_midi.parameter_write_listener
    if listener and midi_devices[device] ~= nil then listener("nrpn", device, channel, nrpn_msb, nrpn_lsb) end
    inside_nrpn = true
    m_midi.cc(99, nil, nrpn_msb, channel, device)
    m_midi.cc(98, nil, nrpn_lsb, channel, device)
    m_midi.cc(6, nil, msb, channel, device)
    m_midi.cc(38, nil, lsb, channel, device)
    inside_nrpn = false
  end


  return cc, nrpn
end

return output
