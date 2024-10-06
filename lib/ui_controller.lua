local ui_controller = {}

local fn = include("mosaic/lib/functions")

channel_edit_page_ui_controller = include("mosaic/lib/pages/channel_edit_page/channel_edit_page_ui_controller")
velocity_edit_page_ui_controller = include("mosaic/lib/pages/velocity_edit_page/velocity_edit_page_ui_controller")
note_edit_page_ui_controller = include("mosaic/lib/pages/note_edit_page/note_edit_page_ui_controller")
trigger_edit_page_ui_controller = include("mosaic/lib/pages/trigger_edit_page/trigger_edit_page_ui_controller")
channel_sequencer_page_ui_controller = include("mosaic/lib/pages/channel_sequencer_page/channel_sequencer_page_ui_controller")

tooltip = include("mosaic/lib/ui_components/tooltip")
save_confirm = include("mosaic/lib/ui_components/save_confirm")

is_key1_down = false
is_key2_down = false
is_key3_down = false

function ui_controller.init()
  draw_handler:register_ui("tooltip", tooltip.draw)

  channel_edit_page_ui_controller.register_ui_draw_handlers()
  velocity_edit_page_ui_controller.register_ui_draw_handlers()
  note_edit_page_ui_controller.register_ui_draw_handlers()
  trigger_edit_page_ui_controller.register_ui_draw_handlers()
  channel_sequencer_page_ui_controller.register_ui_draw_handlers()

  channel_edit_page_ui_controller.init()
  channel_sequencer_page_ui_controller.init()
  note_edit_page_ui_controller.init()
  velocity_edit_page_ui_controller.init()
  trigger_edit_page_ui_controller.init()
end

function ui_controller.change_page(subpage_name)
  channel_edit_page_ui_controller.change_page(subpage_name)
  velocity_edit_page_ui_controller.change_page(subpage_name)
  note_edit_page_ui_controller.change_page(subpage_name)
  trigger_edit_page_ui_controller.change_page(subpage_name)
  channel_sequencer_page_ui_controller.change_page(subpage_name)
  fn.dirty_screen(true)
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
  draw_handler:handle_ui(program.get().selected_page)
end

function ui_controller.enc(n, d)
  if program.get().selected_page == 1 then
    channel_edit_page_ui_controller.enc(n, d)
  elseif program.get().selected_page == 2 then
    channel_sequencer_page_ui_controller.enc(n, d)
  elseif program.get().selected_page == 3 then
    trigger_edit_page_ui_controller.enc(n, d)
  elseif program.get().selected_page == 4 then
    note_edit_page_ui_controller.enc(n, d)
  elseif program.get().selected_page == 5 then
    velocity_edit_page_ui_controller.enc(n, d)
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

  channel_edit_page_ui_controller.key(n, z)
  -- velocity_edit_page_ui_controller.key(n, z)
  -- note_edit_page_ui_controller.key(n, z)
  -- trigger_edit_page_ui_controller.key(n, z)
  -- channel_sequencer_page_ui_controller.key(n, z)

end

function ui_controller.refresh()
  channel_edit_page_ui_controller.refresh()
  -- note_edit_page_ui_controller.refresh()
  -- trigger_edit_page_ui_controller.refresh()
  -- channel_sequencer_page_ui_controller.refresh()

end


return ui_controller
