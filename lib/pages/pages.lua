
local pages = {}

local PAGE_DEFINITIONS = {
  {
    id = "channel_edit_page",
    number = 2,
    name = "Channel Editor",
    grid_button = 3,
    controller = "channel_edit_page"
  },
  {
    id = "scale_edit_page",
    number = 3,
    name = "Scale Editor",
    grid_button = 4,
    controller = "scale_edit_page"
  },
  {
    id = "trigger_edit_page",
    number = 4,
    name = "Pattern Trig Editor",
    grid_button = 5,
    controller = "trigger_edit_page"
  },
  {
    id = "note_edit_page",
    number = 5,
    name = "Pattern Note Editor", 
    grid_button = 5,
    controller = "note_edit_page"
  },
  {
    id = "velocity_edit_page",
    number = 6,
    name = "Pattern Velocity Editor",
    grid_button = 5,
    controller = "velocity_edit_page"
  },
  {
    id = "song_edit_page",
    number = 7,
    name = "Song Editor",
    grid_button = 6,
    controller = "song_edit_page"
  }
}

-- Initialize pages enum
pages.pages = {}
for _, page in ipairs(PAGE_DEFINITIONS) do
  pages.pages[page.id] = page.number
end

-- Initialize page numbers to IDs mapping
pages.page_numbers_to_ids = {}
for _, page in ipairs(PAGE_DEFINITIONS) do
  pages.page_numbers_to_ids[page.number] = page.id
end

-- Initialize page names
pages.page_names = {"Recorder"} -- First page is special case
for _, page in ipairs(PAGE_DEFINITIONS) do
  pages.page_names[page.number] = page.name
end

-- Initialize grid menu mappings
pages.grid_menu_to_page_mappings = {}
pages.pages_to_grid_menu_button_mappings = {}
for _, page in ipairs(PAGE_DEFINITIONS) do
  pages.grid_menu_to_page_mappings[page.grid_button] = page.number
  pages.pages_to_grid_menu_button_mappings[page.id] = page.grid_button
end

function pages.initialise_page_controller_mappings()

  -- Initialize controller mappings
  pages.grid_menu_buttons_to_controller_mappings = {
    [1] = trigger_edit_page, -- recorder placeholder
    [2] = trigger_edit_page  -- blank
  }
  for _, page in ipairs(PAGE_DEFINITIONS) do
    pages.grid_menu_buttons_to_controller_mappings[page.grid_button] = _G[page.controller]
  end

  -- Initialize page to controller mappings
  pages.page_to_controller_mappings = {}
  for _, page in ipairs(PAGE_DEFINITIONS) do
    pages.page_to_controller_mappings[page.number] = _G[page.controller]
  end
end

return pages