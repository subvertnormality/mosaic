local ui = {}



channel_edit_page_ui = include("mosaic/lib/pages/channel_edit_page/channel_edit_page_ui")
scale_edit_page_ui = include("mosaic/lib/pages/scale_edit_page/scale_edit_page_ui")
velocity_edit_page_ui = include("mosaic/lib/pages/velocity_edit_page/velocity_edit_page_ui")
note_edit_page_ui = include("mosaic/lib/pages/note_edit_page/note_edit_page_ui")
trigger_edit_page_ui = include("mosaic/lib/pages/trigger_edit_page/trigger_edit_page_ui")
song_edit_page_ui = include("mosaic/lib/pages/song_edit_page/song_edit_page_ui")

tooltip = include("mosaic/lib/ui_components/tooltip")
save_confirm = include("mosaic/lib/ui_components/save_confirm")
ui_live = include("mosaic/lib/ui_live")

is_key1_down = false
is_key2_down = false
is_key3_down = false

function ui.init()
  draw:register_ui("tooltip", tooltip.draw)

  channel_edit_page_ui.register_ui_draws()
  scale_edit_page_ui.register_ui_draws()
  velocity_edit_page_ui.register_ui_draws()
  note_edit_page_ui.register_ui_draws()
  trigger_edit_page_ui.register_ui_draws()
  song_edit_page_ui.register_ui_draws()

  channel_edit_page_ui.init()
  scale_edit_page_ui.init()
  note_edit_page_ui.init()
  velocity_edit_page_ui.init()
  trigger_edit_page_ui.init()
  song_edit_page_ui.init()

  -- The live UI wraps the page owners above; they keep their state and handlers.
  ui_live.install()
end

function ui.redraw()
  if not program then
    return
  end
  ui_live.redraw()
end

function ui.enc(n, d)
  ui_live.enc(n, d)
end

function ui.key(n, z)

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

  ui_live.key(n, z)

end

function ui.refresh()
  channel_edit_page_ui.refresh()
  -- note_edit_page_ui.refresh()
  -- trigger_edit_page_ui.refresh()
  -- song_edit_page_ui.refresh()

end


return ui
