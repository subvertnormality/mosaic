local util = require("lib.util")

local create_default_config = {}

create_default_config.default_custom_device_map_content =
  [[
  local custom_midi_device_map = {

    -- { 
    --   ["type"] = "midi", -- leave this as is
    --   ["name"] = "Example",
    --   ["fixed_note"] = 60, -- fixed midi note number that channel will always output, or nil
    --   ["map_params_automatically"] = true, -- if true, params will be mapped to channel param knobs automatically, from 1-8, otherwise user selects
    --   ["polyphonic"] = true, -- allows the destination device to decide how to deal with overlapping notes
    --   ["params"] = { -- up to 8 params
    --     {
    --       ["id"] = "example",
    --       ["name"] = "Example",
    --       ["cc_msb"] = 93, -- midi cc value
    --       ["cc_lsb"] = nil, -- not currently used but could be in the future
    --       ["cc_min_value"] = 0, -- bottom range of values
    --       ["cc_max_value"] = 127, -- top range of values
    --       ["nrpn_msb"] = 1, -- not currently used but could be in the future
    --       ["nrpn_lsb"] = 102, -- not currently used but could be in the future
    --       ["nrpn_min_value"] = 0, -- not currently used but could be in the future
    --       ["nrpn_max_value"] = 127, -- not currently used but could be in the future
    --       ["short_descriptor_1"] = "EXMP", -- 4 caps letters 
    --       ["short_descriptor_2"] = "PARA", -- 4 caps letters
    --     },
    --     {
    --       ["id"] = "example",
    --       ["name"] = "Example",
    --       ["cc_msb"] = 93, -- midi cc value
    --       ["cc_lsb"] = nil, -- not currently used but could be in the future
    --       ["cc_min_value"] = 0, -- bottom range of values
    --       ["cc_max_value"] = 127, -- top range of values
    --       ["nrpn_msb"] = 1, -- not currently used but could be in the future
    --       ["nrpn_lsb"] = 102, -- not currently used but could be in the future
    --       ["nrpn_min_value"] = 0, -- not currently used but could be in the future
    --       ["nrpn_max_value"] = 127, -- not currently used but could be in the future
    --       ["short_descriptor_1"] = "EXMP", -- 4 caps letters 
    --       ["short_descriptor_2"] = "PARA", -- 4 caps letters
    --     } 
    --   }
  -- },

}

return custom_midi_device_map
]]

create_default_config.default_device_config_content =
  [[
local device_config = {
  ["show_devices"] = {
    "cc_device",
    "syntakt",
    "digitakt",
    "digitone",
    "op-1",
    "ex-braids",
    "ex-multi-sample",
    "ex-matrix-mixer",
    "drm-bd",
    "drm-drum1",
    "drm-drum2",
    "drm-multi",
    "drm-sd",
    "drm-hh1",
    "drm-hh2",
    "drm-clap",
    "nord_drum_2",
    "ex-plaits"
  }
}

return device_config
]]

function create_default_config.create_script(file_name, content)
  if not util.file_exists(norns.state.data .. "/" .. file_name) then
    local cmd = string.format("sudo echo '%s' > '%s'", content, norns.state.data .. "/" .. file_name)

    -- Execute the command and capture the result (though we're not really using the output)
    util.os_capture(cmd)

    -- Since we're not capturing errors from os_capture in this context, we'll assume success.
    print(file_name .. " created.")
  else
    print(file_name .. " already exists. Doing nothing.")
  end
end

return create_default_config
