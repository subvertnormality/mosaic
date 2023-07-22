local channel_edit_page_ui = {}

local musicutil = require("musicutil")
local Pages = include("sinfcommand/lib/ui_components/Pages")
local Page = include("sinfcommand/lib/ui_components/Page")
local VerticalScrollSelector = include("sinfcommand/lib/ui_components/VerticalScrollSelector")

local pages = Pages:new()
quantizer_vertical_scroll_selector = VerticalScrollSelector:new(20, 20, "Quantizer", { 
  {name = "Chromatic", value = musicutil.generate_scale(0, "chromatic", 1)}, 
  {name = "Major", value = musicutil.generate_scale(0, "major", 1)},
  {name = "Harmonic Major", value = musicutil.generate_scale(0, "harmonic_major", 1)},
  {name = "Minor", value = musicutil.generate_scale(0, "minor", 1)}, 
  {name = "Harmonic Minor", value = musicutil.generate_scale(0, "harmonic_minor", 1)},
  {name = "Melodic Minor", value = musicutil.generate_scale(0, "melodic_minor", 1)},
  {name = "Dorian", value = musicutil.generate_scale(0, "dorian", 1)}, 
  {name = "Phrygian", value = musicutil.generate_scale(0, "phrygian", 1)}, 
  {name = "Lydian", value = musicutil.generate_scale(0, "lydian", 1)}, 
  {name = "Lydian Minor", value = musicutil.generate_scale(0, "lydian_minor", 1)},
  {name = "Mixolydian", value = musicutil.generate_scale(0, "mixolydian", 1)},
  {name = "Locrian", value = musicutil.generate_scale(0, "locrian", 1)}, 
  {name = "Whole Tone", value = musicutil.generate_scale(0, "whole_tone", 1)}, 
  {name = "Pentatonic Major", value = musicutil.generate_scale(0, "major_pentatonic", 1)}, 
  {name = "Pentatonic Minor", value = musicutil.generate_scale(0, "minor_pentatonic", 1)},
  {name = "Major Bebop", value = musicutil.generate_scale(0, "major_bebop", 1)},
  {name = "Altered Scale", value = musicutil.generate_scale(0, "altered_scale", 1)},
  {name = "Dorian Bebop", value = musicutil.generate_scale(0, "dorian_bebop", 1)},
  {name = "Mixolydian Bebop", value = musicutil.generate_scale(0, "mixolydian_bebop", 1)},
  {name = "Blues Scale", value = musicutil.generate_scale(0, "blues_scale", 1)},
  {name = "Diminished Whole Half", value = musicutil.generate_scale(0, "diminished_whole_half", 1)},
  {name = "Diminished Half Whole", value = musicutil.generate_scale(0, "diminished_half_whole", 1)},
  {name = "Neapolitan Major", value = musicutil.generate_scale(0, "neapolitan_major", 1)},
  {name = "Hungarian Major", value = musicutil.generate_scale(0, "hungarian_major", 1)},
  {name = "Harmonic Major", value = musicutil.generate_scale(0, "harmonic_major", 1)},
  {name = "Hungarian Minor", value = musicutil.generate_scale(0, "hungarian_minor", 1)},
  {name = "Neapolitan Minor", value = musicutil.generate_scale(0, "neapolitan_minor", 1)},
  {name = "Major Locrian", value = musicutil.generate_scale(0, "major_locrian", 1)},
  {name = "Leading Whole Tone", value = musicutil.generate_scale(0, "leading_whole_tone", 1)},
  {name = "Six Tone Symmetrical", value = musicutil.generate_scale(0, "six_tone_symmetrical", 1)},
  {name = "Balinese", value = musicutil.generate_scale(0, "balinese", 1)},
  {name = "Persian", value = musicutil.generate_scale(0, "persian", 1)},
  {name = "East Indian Purvi", value = musicutil.generate_scale(0, "east_indian_purvi", 1)},
  {name = "Oriental", value = musicutil.generate_scale(0, "oriental", 1)},
  {name = "Double Harmonic", value = musicutil.generate_scale(0, "double_harmonic", 1)},
  {name = "Enigmatic", value = musicutil.generate_scale(0, "enigmatic", 1)},
  {name = "Overtone", value = musicutil.generate_scale(0, "overtone", 1)},
  {name = "Eight Tone Spanish", value = musicutil.generate_scale(0, "eight_tone_spanish", 1)},
  {name = "Prometheus", value = musicutil.generate_scale(0, "prometheus", 1)},
  {name = "Gagaku Rittsu Sen Pou", value = musicutil.generate_scale(0, "gagaku_rittsu_sen_pou", 1)},
  {name = "In Sen Pou", value = musicutil.generate_scale(0, "in_sen_pou", 1)},
  {name = "Okinawa", value = musicutil.generate_scale(0, "okinawa", 1)},
})

local function quantizer_page_draw_func()
  quantizer_vertical_scroll_selector:draw()
end

function channel_edit_page_ui:change_page(subpage_name)
  pages:select_page(subpage_name)
end

function channel_edit_page_ui:register_ui_draw_handlers() 


  local quantizer_page = Page:new("quantizer_page", quantizer_page_draw_func)

  pages:add_page(quantizer_page)
  pages:select_page("quantizer_page")

  draw_handler:register_ui(
    "channel_edit_page",
    function()
      pages:draw()
    end
  )
end


return channel_edit_page_ui