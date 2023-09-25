local custom_device_map = {

  {
     ["type"] = "midi", -- this is a midi device
     ["name"] = "Euro 1",
     ["id"] = "euro-1",
     ["unique"] = true,
     ["map_params_automatically"] = true, -- params will be mapped to channel param knobs automatically, from 1-4, otherwise user selects
     ["params"] = { -- up to 8 params
        {
           ["id"] = "flame_1",
           ["name"] = "Flame 1",
           ["channel"] = 15,
           ["cc_msb"] = 1, -- midi cc value
           ["cc_lsb"] = nil, -- not currently used but could be in the future
           ["cc_min_value"] = 0, -- bottom range of values
           ["cc_max_value"] = 127, -- top range of values
           ["nrpn_msb"] = 1, -- not currently used but could be in the future
           ["nrpn_lsb"] = 102, -- not currently used but could be in the future
           ["nrpn_min_value"] = 0, -- not currently used but could be in the future
           ["nrpn_max_value"] = 127, -- not currently used but could be in the future
           ["short_descriptor_1"] = "U16M", -- 4 caps letters
           ["short_descriptor_2"] = "1", -- 4 caps letters
        },
        {
           ["id"] = "flame_2",
           ["name"] = "Flame 2",
           ["channel"] = 15,
           ["cc_msb"] = 2, -- midi cc value
           ["cc_lsb"] = nil, -- not currently used but could be in the future
           ["cc_min_value"] = 0, -- bottom range of values
           ["cc_max_value"] = 127, -- top range of values
           ["nrpn_msb"] = 1, -- not currently used but could be in the future
           ["nrpn_lsb"] = 102, -- not currently used but could be in the future
           ["nrpn_min_value"] = 0, -- not currently used but could be in the future
           ["nrpn_max_value"] = 127, -- not currently used but could be in the future
           ["short_descriptor_1"] = "U16M", -- 4 caps letters
           ["short_descriptor_2"] = "2", -- 4 caps letters
        },
        {
           ["id"] = "flame_3",
           ["name"] = "Flame 3",
           ["channel"] = 15,
           ["cc_msb"] = 3, -- midi cc value
           ["cc_lsb"] = nil, -- not currently used but could be in the future
           ["cc_min_value"] = 0, -- bottom range of values
           ["cc_max_value"] = 127, -- top range of values
           ["nrpn_msb"] = 1, -- not currently used but could be in the future
           ["nrpn_lsb"] = 102, -- not currently used but could be in the future
           ["nrpn_min_value"] = 0, -- not currently used but could be in the future
           ["nrpn_max_value"] = 127, -- not currently used but could be in the future
           ["short_descriptor_1"] = "U16M", -- 4 caps letters
           ["short_descriptor_2"] = "3", -- 4 caps letters
        },
        {
           ["id"] = "flame_4",
           ["name"] = "Flame 4",
           ["channel"] = 15,
           ["cc_msb"] = 4, -- midi cc value
           ["cc_lsb"] = nil, -- not currently used but could be in the future
           ["cc_min_value"] = 0, -- bottom range of values
           ["cc_max_value"] = 127, -- top range of values
           ["nrpn_msb"] = 1, -- not currently used but could be in the future
           ["nrpn_lsb"] = 102, -- not currently used but could be in the future
           ["nrpn_min_value"] = 0, -- not currently used but could be in the future
           ["nrpn_max_value"] = 127, -- not currently used but could be in the future
           ["short_descriptor_1"] = "U16M", -- 4 caps letters
           ["short_descriptor_2"] = "4", -- 4 caps letters
        }
     },
     ["default_midi_channel"] = 11,
     ["default_midi_device"] = 1
  },
  {
     ["type"] = "midi", -- leave this as is
     ["name"] = "Euro 2",
     ["id"] = "euro-2",
     ["unique"] = true,
     ["fixed_note"] = nil, -- fixed midi note number that channel will always output, or nil
     ["map_params_automatically"] = true, -- if true, params will be mapped to channel param knobs automatically, from 1-8, otherwise user selects
     ["params"] = { -- up to 8 params
        {
           ["id"] = "flame_5",
           ["name"] = "Flame 5",
           ["channel"] = 15,
           ["cc_msb"] = 5, -- midi cc value
           ["cc_lsb"] = nil, -- not currently used but could be in the future
           ["cc_min_value"] = 0, -- bottom range of values
           ["cc_max_value"] = 127, -- top range of values
           ["nrpn_msb"] = 1, -- not currently used but could be in the future
           ["nrpn_lsb"] = 102, -- not currently used but could be in the future
           ["nrpn_min_value"] = 0, -- not currently used but could be in the future
           ["nrpn_max_value"] = 127, -- not currently used but could be in the future
           ["short_descriptor_1"] = "U16M", -- 4 caps letters
           ["short_descriptor_2"] = "5", -- 4 caps letters
        },
        {
           ["id"] = "flame_6",
           ["name"] = "Flame 6",
           ["channel"] = 15,
           ["cc_msb"] = 6, -- midi cc value
           ["cc_lsb"] = nil, -- not currently used but could be in the future
           ["cc_min_value"] = 0, -- bottom range of values
           ["cc_max_value"] = 127, -- top range of values
           ["nrpn_msb"] = 1, -- not currently used but could be in the future
           ["nrpn_lsb"] = 102, -- not currently used but could be in the future
           ["nrpn_min_value"] = 0, -- not currently used but could be in the future
           ["nrpn_max_value"] = 127, -- not currently used but could be in the future
           ["short_descriptor_1"] = "U16M", -- 4 caps letters
           ["short_descriptor_2"] = "6", -- 4 caps letters
        },
        {
           ["id"] = "flame_7",
           ["name"] = "Flame 7",
           ["channel"] = 15,
           ["cc_msb"] = 7, -- midi cc value
           ["cc_lsb"] = nil, -- not currently used but could be in the future
           ["cc_min_value"] = 0, -- bottom range of values
           ["cc_max_value"] = 127, -- top range of values
           ["nrpn_msb"] = 1, -- not currently used but could be in the future
           ["nrpn_lsb"] = 102, -- not currently used but could be in the future
           ["nrpn_min_value"] = 0, -- not currently used but could be in the future
           ["nrpn_max_value"] = 127, -- not currently used but could be in the future
           ["short_descriptor_1"] = "U16M", -- 4 caps letters
           ["short_descriptor_2"] = "7", -- 4 caps letters
        },
        {
           ["id"] = "flame_8",
           ["name"] = "Flame 8",
           ["channel"] = 15,
           ["cc_msb"] = 8, -- midi cc value
           ["cc_lsb"] = nil, -- not currently used but could be in the future
           ["cc_min_value"] = 0, -- bottom range of values
           ["cc_max_value"] = 127, -- top range of values
           ["nrpn_msb"] = 1, -- not currently used but could be in the future
           ["nrpn_lsb"] = 102, -- not currently used but could be in the future
           ["nrpn_min_value"] = 0, -- not currently used but could be in the future
           ["nrpn_max_value"] = 127, -- not currently used but could be in the future
           ["short_descriptor_1"] = "U16M", -- 4 caps letters
           ["short_descriptor_2"] = "8", -- 4 caps letters
        }
     },
     ["default_midi_channel"] = 12,
     ["default_midi_device"] = 1
  },
  {
     ["type"] = "midi", -- leave this as is
     ["name"] = "Euro 3",
     ["id"] = "euro-3",
     ["unique"] = true,
     ["fixed_note"] = nil, -- fixed midi note number that channel will always output, or nil
     ["map_params_automatically"] = true, -- if true, params will be mapped to channel param knobs automatically, from 1-8, otherwise user selects
     ["params"] = { -- up to 8 params
        {
           ["id"] = "flame_9",
           ["name"] = "Flame 9",
           ["channel"] = 15,
           ["cc_msb"] = 9, -- midi cc value
           ["cc_lsb"] = nil, -- not currently used but could be in the future
           ["cc_min_value"] = 0, -- bottom range of values
           ["cc_max_value"] = 127, -- top range of values
           ["nrpn_msb"] = 1, -- not currently used but could be in the future
           ["nrpn_lsb"] = 102, -- not currently used but could be in the future
           ["nrpn_min_value"] = 0, -- not currently used but could be in the future
           ["nrpn_max_value"] = 127, -- not currently used but could be in the future
           ["short_descriptor_1"] = "U16M", -- 4 caps letters
           ["short_descriptor_2"] = "9", -- 4 caps letters
        },
        {
           ["id"] = "flame_10",
           ["name"] = "Flame 10",
           ["channel"] = 15,
           ["cc_msb"] = 10, -- midi cc value
           ["cc_lsb"] = nil, -- not currently used but could be in the future
           ["cc_min_value"] = 0, -- bottom range of values
           ["cc_max_value"] = 127, -- top range of values
           ["nrpn_msb"] = 1, -- not currently used but could be in the future
           ["nrpn_lsb"] = 102, -- not currently used but could be in the future
           ["nrpn_min_value"] = 0, -- not currently used but could be in the future
           ["nrpn_max_value"] = 127, -- not currently used but could be in the future
           ["short_descriptor_1"] = "U16M", -- 4 caps letters
           ["short_descriptor_2"] = "10", -- 4 caps letters
        },
        {
           ["id"] = "flame_11",
           ["name"] = "Flame 11",
           ["channel"] = 15,
           ["cc_msb"] = 11, -- midi cc value
           ["cc_lsb"] = nil, -- not currently used but could be in the future
           ["cc_min_value"] = 0, -- bottom range of values
           ["cc_max_value"] = 127, -- top range of values
           ["nrpn_msb"] = 1, -- not currently used but could be in the future
           ["nrpn_lsb"] = 102, -- not currently used but could be in the future
           ["nrpn_min_value"] = 0, -- not currently used but could be in the future
           ["nrpn_max_value"] = 127, -- not currently used but could be in the future
           ["short_descriptor_1"] = "U16M", -- 4 caps letters
           ["short_descriptor_2"] = "11", -- 4 caps letters
        },
        {
           ["id"] = "flame_12",
           ["name"] = "Flame 12",
           ["channel"] = 15,
           ["cc_msb"] = 12, -- midi cc value
           ["cc_lsb"] = nil, -- not currently used but could be in the future
           ["cc_min_value"] = 0, -- bottom range of values
           ["cc_max_value"] = 127, -- top range of values
           ["nrpn_msb"] = 1, -- not currently used but could be in the future
           ["nrpn_lsb"] = 102, -- not currently used but could be in the future
           ["nrpn_min_value"] = 0, -- not currently used but could be in the future
           ["nrpn_max_value"] = 127, -- not currently used but could be in the future
           ["short_descriptor_1"] = "U16M", -- 4 caps letters
           ["short_descriptor_2"] = "12", -- 4 caps letters
        }
     },
     ["default_midi_channel"] = 13,
     ["default_midi_device"] = 1
  },
  {
     ["type"] = "midi", -- leave this as is
     ["name"] = "Euro 4",
     ["id"] = "euro-4",
     ["unique"] = true,
     ["fixed_note"] = nil, -- fixed midi note number that channel will always output, or nil
     ["map_params_automatically"] = true, -- if true, params will be mapped to channel param knobs automatically, from 1-8, otherwise user selects
     ["params"] = { -- up to 8 params
        {
           ["id"] = "flame_13",
           ["name"] = "Flame 13",
           ["channel"] = 15,
           ["cc_msb"] = 13, -- midi cc value
           ["cc_lsb"] = nil, -- not currently used but could be in the future
           ["cc_min_value"] = 0, -- bottom range of values
           ["cc_max_value"] = 127, -- top range of values
           ["nrpn_msb"] = 1, -- not currently used but could be in the future
           ["nrpn_lsb"] = 102, -- not currently used but could be in the future
           ["nrpn_min_value"] = 0, -- not currently used but could be in the future
           ["nrpn_max_value"] = 127, -- not currently used but could be in the future
           ["short_descriptor_1"] = "U16M", -- 4 caps letters
           ["short_descriptor_2"] = "13", -- 4 caps letters
        },
        {
           ["id"] = "flame_14",
           ["name"] = "Flame 14",
           ["channel"] = 15,
           ["cc_msb"] = 14, -- midi cc value
           ["cc_lsb"] = nil, -- not currently used but could be in the future
           ["cc_min_value"] = 0, -- bottom range of values
           ["cc_max_value"] = 127, -- top range of values
           ["nrpn_msb"] = 1, -- not currently used but could be in the future
           ["nrpn_lsb"] = 102, -- not currently used but could be in the future
           ["nrpn_min_value"] = 0, -- not currently used but could be in the future
           ["nrpn_max_value"] = 127, -- not currently used but could be in the future
           ["short_descriptor_1"] = "U16M", -- 4 caps letters
           ["short_descriptor_2"] = "14", -- 4 caps letters
        },
        {
           ["id"] = "flame_15",
           ["name"] = "Flame 15",
           ["channel"] = 15,
           ["cc_msb"] = 15, -- midi cc value
           ["cc_lsb"] = nil, -- not currently used but could be in the future
           ["cc_min_value"] = 0, -- bottom range of values
           ["cc_max_value"] = 127, -- top range of values
           ["nrpn_msb"] = 1, -- not currently used but could be in the future
           ["nrpn_lsb"] = 102, -- not currently used but could be in the future
           ["nrpn_min_value"] = 0, -- not currently used but could be in the future
           ["nrpn_max_value"] = 127, -- not currently used but could be in the future
           ["short_descriptor_1"] = "U16M", -- 4 caps letters
           ["short_descriptor_2"] = "15", -- 4 caps letters
        },
        {
           ["id"] = "flame_16",
           ["name"] = "Flame 16",
           ["channel"] = 15,
           ["cc_msb"] = 16, -- midi cc value
           ["cc_lsb"] = nil, -- not currently used but could be in the future
           ["cc_min_value"] = 0, -- bottom range of values
           ["cc_max_value"] = 127, -- top range of values
           ["nrpn_msb"] = 1, -- not currently used but could be in the future
           ["nrpn_lsb"] = 102, -- not currently used but could be in the future
           ["nrpn_min_value"] = 0, -- not currently used but could be in the future
           ["nrpn_max_value"] = 127, -- not currently used but could be in the future
           ["short_descriptor_1"] = "U16M", -- 4 caps letters
           ["short_descriptor_2"] = "16", -- 4 caps letters
        }
     },
     ["default_midi_channel"] = 14,
     ["default_midi_device"] = 1
  },
  {
     ["type"] = "midi", -- leave this as is
     ["name"] = "DRM BD",
     ["id"] = "drm-bd",
     ["unique"] = true,
     ["map_params_automatically"] = true, -- if true, params will be mapped to channel param knobs automatically, from 1-8, otherwise user selects
     ["params"] = { -- up to 8 params
        {
           ["id"] = "fixed_note",
           ["name"] = "Fixed Note",
           ["short_descriptor_1"] = "FIXD",
           ["short_descriptor_2"] = "NOTE",
           ["cc_min_value"] = -1,
           ["cc_max_value"] = 127,
           ["default"] = 0
        }
     },
     ["default_midi_channel"] = 15,
     ["default_midi_device"] = 1
  },
  {
     ["type"] = "midi", -- leave this as is
     ["name"] = "DRM Drum 1",
     ["id"] = "drm-drum1",
     ["unique"] = true,
     ["map_params_automatically"] = true, -- if true, params will be mapped to channel param knobs automatically, from 1-8, otherwise user selects
     ["params"] = { -- up to 8 params
        {
           ["id"] = "fixed_note",
           ["name"] = "Fixed Note",
           ["short_descriptor_1"] = "FIXD",
           ["short_descriptor_2"] = "NOTE",
           ["cc_min_value"] = -1,
           ["cc_max_value"] = 127,
           ["default"] = 2
        }
     },
     ["default_midi_channel"] = 15,
     ["default_midi_device"] = 1
  },
  {
     ["type"] = "midi", -- leave this as is
     ["name"] = "DRM Drum 2",
     ["id"] = "drm-drum2",
     ["unique"] = true,
     ["map_params_automatically"] = true, -- if true, params will be mapped to channel param knobs automatically, from 1-8, otherwise user selects
     ["params"] = { -- up to 8 params
        {
           ["id"] = "fixed_note",
           ["name"] = "Fixed Note",
           ["short_descriptor_1"] = "FIXD",
           ["short_descriptor_2"] = "NOTE",
           ["cc_min_value"] = -1,
           ["cc_max_value"] = 127,
           ["default"] = 4
        }
     },
     ["default_midi_channel"] = 15,
     ["default_midi_device"] = 1
  },
  {
     ["type"] = "midi", -- leave this as is
     ["name"] = "DRM Multi",
     ["id"] = "drm-multi",
     ["unique"] = true,
     ["map_params_automatically"] = true, -- if true, params will be mapped to channel param knobs automatically, from 1-8, otherwise user selects
     ["params"] = { -- up to 8 params
        {
           ["id"] = "fixed_note",
           ["name"] = "Fixed Note",
           ["short_descriptor_1"] = "FIXD",
           ["short_descriptor_2"] = "NOTE",
           ["cc_min_value"] = -1,
           ["cc_max_value"] = 127,
           ["default"] = 5
        }
     },
     ["default_midi_channel"] = 15,
     ["default_midi_device"] = 1
  },
  {
     ["type"] = "midi", -- leave this as is
     ["name"] = "DRM Snare",
     ["id"] = "drm-sd",
     ["unique"] = true,
     ["map_params_automatically"] = true, -- if true, params will be mapped to channel param knobs automatically, from 1-8, otherwise user selects
     ["params"] = { -- up to 8 params
        {
           ["id"] = "fixed_note",
           ["name"] = "Fixed Note",
           ["short_descriptor_1"] = "FIXD",
           ["short_descriptor_2"] = "NOTE",
           ["cc_min_value"] = -1,
           ["cc_max_value"] = 127,
           ["default"] = 7
        }
     },
     ["default_midi_channel"] = 15,
     ["default_midi_device"] = 1
  },
  {
     ["type"] = "midi", -- leave this as is
     ["name"] = "DRM HH 1",
     ["id"] = "drm-hh1",
     ["unique"] = true,
     ["map_params_automatically"] = true, -- if true, params will be mapped to channel param knobs automatically, from 1-8, otherwise user selects
     ["params"] = { -- up to 8 params
        {
           ["id"] = "fixed_note",
           ["name"] = "Fixed Note",
           ["short_descriptor_1"] = "FIXD",
           ["short_descriptor_2"] = "NOTE",
           ["cc_min_value"] = -1,
           ["cc_max_value"] = 127,
           ["default"] = 9
        }
     },
     ["default_midi_channel"] = 15,
     ["default_midi_device"] = 1
  },
  {
     ["type"] = "midi", -- leave this as is
     ["name"] = "DRM HH 2",
     ["id"] = "drm-hh2",
     ["unique"] = true,
     ["map_params_automatically"] = true, -- if true, params will be mapped to channel param knobs automatically, from 1-8, otherwise user selects
     ["params"] = { -- up to 8 params
        {
           ["id"] = "fixed_note",
           ["name"] = "Fixed Note",
           ["short_descriptor_1"] = "FIXD",
           ["short_descriptor_2"] = "NOTE",
           ["cc_min_value"] = -1,
           ["cc_max_value"] = 127,
           ["default"] = 12
        }
     },
     ["default_midi_channel"] = 15,
     ["default_midi_device"] = 1
  },
  {
     ["type"] = "midi", -- leave this as is
     ["name"] = "DRM Clap",
     ["id"] = "drm-clap",
     ["unique"] = true,
     ["map_params_automatically"] = true, -- if true, params will be mapped to channel param knobs automatically, from 1-8, otherwise user selects
     ["params"] = { -- up to 8 params
        {
           ["id"] = "fixed_note",
           ["name"] = "Fixed Note",
           ["short_descriptor_1"] = "FIXD",
           ["short_descriptor_2"] = "NOTE",
           ["cc_min_value"] = -1,
           ["cc_max_value"] = 127,
           ["default"] = 16
        }
     },
     ["default_midi_channel"] = 15,
     ["default_midi_device"] = 1
  },
  {
     ["id"] = "ex-braids",
     ["hide"] = false,
     ["unique"] = true,
     ["default_midi_channel"] = 16,
     ["default_midi_device"] = 1
  },
  {
     ["id"] = "digitakt",
     ["hide"] = true
  },
  {
     ["id"] = "op-1",
     ["hide"] = true
  }
}

return custom_device_map
