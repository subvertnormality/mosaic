local ui_controller = {}



channel_edit_page_ui_controller = include("mosaic/lib/pages/channel_edit_page/channel_edit_page_ui_controller")
scale_edit_page_ui_controller = include("mosaic/lib/pages/scale_edit_page/scale_edit_page_ui_controller")
velocity_edit_page_ui_controller = include("mosaic/lib/pages/velocity_edit_page/velocity_edit_page_ui_controller")
note_edit_page_ui_controller = include("mosaic/lib/pages/note_edit_page/note_edit_page_ui_controller")
trigger_edit_page_ui_controller = include("mosaic/lib/pages/trigger_edit_page/trigger_edit_page_ui_controller")
song_edit_page_ui_controller = include("mosaic/lib/pages/song_edit_page/song_edit_page_ui_controller")

tooltip = include("mosaic/lib/ui_components/tooltip")
save_confirm = include("mosaic/lib/ui_components/save_confirm")

is_key1_down = false
is_key2_down = false
is_key3_down = false

function ui_controller.init()
  draw:register_ui("tooltip", tooltip.draw)

  channel_edit_page_ui_controller.register_ui_draws()
  scale_edit_page_ui_controller.register_ui_draws()
  velocity_edit_page_ui_controller.register_ui_draws()
  note_edit_page_ui_controller.register_ui_draws()
  trigger_edit_page_ui_controller.register_ui_draws()
  song_edit_page_ui_controller.register_ui_draws()

  channel_edit_page_ui_controller.init()
  scale_edit_page_ui_controller.init()
  note_edit_page_ui_controller.init()
  velocity_edit_page_ui_controller.init()
  trigger_edit_page_ui_controller.init()
  song_edit_page_ui_controller.init()
end

function ui_controller.redraw()
  if not program then
    return
  end

  screen.font_size(8)
  screen.font_face(1)
  screen.level(10)
  screen.move(120, 9)
  screen.text("m")
  draw:handle_ui(program.get_selected_page())
end

function ui_controller.enc(n, d)
  if program.get_selected_page() == pages.pages.channel_edit_page then
    channel_edit_page_ui_controller.enc(n, d)
  elseif program.get_selected_page() == pages.pages.scale_edit_page then
    scale_edit_page_ui_controller.enc(n, d)
  elseif program.get_selected_page() == pages.pages.trigger_edit_page then
    trigger_edit_page_ui_controller.enc(n, d)
  elseif program.get_selected_page() == pages.pages.note_edit_page then
    note_edit_page_ui_controller.enc(n, d)
  elseif program.get_selected_page() == pages.pages.velocity_edit_page then
    velocity_edit_page_ui_controller.enc(n, d)
  elseif program.get_selected_page() == pages.pages.song_edit_page then
    song_edit_page_ui_controller.enc(n, d)
  end
end

function ui_controller.key(n, z)

  if n == 1 and z == 1 then
    is_key1_down = true
  elseif n == 1 and z == 0 then
    is_key1_down = false
  end

  if n == 2 and z == 1 then
    is_key2_down = true
  elseif n == 2 and z == 0 then
    is_key2_down = false
  end

  if n == 3 and z == 1 then
    is_key3_down = true
  elseif n == 3 and z == 0 then
    is_key3_down = false
  end

  if pages.pages.channel_edit_page == program.get_selected_page() then
    channel_edit_page_ui_controller.key(n, z)
  elseif pages.pages.scale_edit_page == program.get_selected_page() then
    scale_edit_page_ui_controller.key(n, z)
  elseif pages.pages.velocity_edit_page == program.get_selected_page() then
    -- velocity_edit_page_ui_controller.key(n, z)
  elseif pages.pages.note_edit_page == program.get_selected_page() then
    -- note_edit_page_ui_controller.key(n, z)
  elseif pages.pages.trigger_edit_page == program.get_selected_page() then
    -- trigger_edit_page_ui_controller.key(n, z)
  elseif pages.pages.song_edit_page == program.get_selected_page() then
    song_edit_page_ui_controller.key(n, z)
  end

end

function ui_controller.refresh()
  channel_edit_page_ui_controller.refresh()
  -- note_edit_page_ui_controller.refresh()
  -- trigger_edit_page_ui_controller.refresh()
  -- song_edit_page_ui_controller.refresh()

end


return ui_controller
