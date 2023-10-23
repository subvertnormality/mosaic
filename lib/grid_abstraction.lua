local grid_abstraction = {}

grid_abstraction.state = {}
grid_abstraction.screen_state = {}

function grid_abstraction.init()
  grid_abstraction.state = {}
  grid_abstraction.screen_state = {}
  for x = 1, 16 do
    grid_abstraction.state[x] = {}
    grid_abstraction.screen_state[x] = {}
    for y = 1, 8 do
      grid_abstraction.state[x][y] = 0
      grid_abstraction.screen_state[x][y] = 0
    end
  end
end

function grid_abstraction.led(x, y, brightness)
  if x < 1 or y < 1 or x > 16 or y > 8 then
    return
  end
  g:led(x, y, brightness)
  grid_abstraction.state[x][y] = brightness
end

function grid_abstraction.seq(x, y, brightness)
  if x < 1 or y < 1 or x > 16 or y > 8 then
    return
  end
  grid_abstraction.screen_state[x][y] = brightness
end

function grid_abstraction.get_state()
  return grid_abstraction.state
end

function grid_abstraction.get_screen_state()
  return grid_abstraction.screen_state
end

return grid_abstraction
