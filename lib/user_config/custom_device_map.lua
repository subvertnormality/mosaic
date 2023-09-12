local custom_midi_device_map = {

    -- { 
    --   ["type"] = "midi", -- leave this as is
    --   ["name"] = "Example",
    --   ["fixed_note"] = 60, -- fixed midi note number that channel will always output, or nil
    --   ["map_params_automatically"] = true, -- if true, params will be mapped to channel param knobs automatically, from 1-8, otherwise user selects
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
