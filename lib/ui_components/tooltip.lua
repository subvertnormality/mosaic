local tooltip = {}

tooltip.text = false
tooltip.metros = {}

function tooltip:draw()
  if tooltip.text then
    screen.move(0,60)
    screen.text(tooltip.text)
  end
end


  -- Define a local remove function for this metro
  local function remove_tip()
    tooltip.text = false
    fn.dirty_screen(true)
  end


function tooltip:show(text)
  -- Stop any existing metro and remove it from the table
  for i, m in ipairs(tooltip.metros) do
    m:stop()
    metro.free(i)
    table.remove(tooltip.metros, i)
  end
  
  tooltip.text = text

  -- Create a new metro
  local m = metro.init(remove_tip, 3, 1)

  -- Start the metro
  m:start()

  -- Add the metro to the metros table
  table.insert(tooltip.metros, m)
end

return tooltip
