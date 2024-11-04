local fade_button = {}
fade_button.__index = fade_button

function fade_button:new(x, y, min, max, button_type)
    local self = setmetatable({}, fade_button)
    self.x = x
    self.y = y
    self.min = min
    self.max = max
    self.button_type = button_type  -- "up", "down", or "center"
    self.value = min
    self.step_size = 1
    return self
end

function fade_button:draw()
    local brightness = 3
    
    if self.button_type == "up" or self.button_type == "down" then
        -- Calculate brightness based on value position
        local range = self.max - self.min
        local position = self.value - self.min
        
        if self.button_type == "down" then  -- Swapped this to match the direction
            position = range - position
        end
        
        brightness = math.max(4, 15 - position * 2) -- Fade from 15 to 4
    elseif self.button_type == "center" then
        local mid_point = math.floor((self.max - self.min) / 2) + self.min
        brightness = self.value == mid_point and 15 or 8
    end
    
    grid_abstraction.led(self.x, self.y, brightness)
end

function fade_button:set_value(val)
    self.value = math.max(self.min, math.min(val, self.max))
end

function fade_button:get_value()
    return self.value
end

function fade_button:press(x, y)
    if not self:is_this(x, y) then
        return false
    end
    
    if self.button_type == "down" and self.value < self.max then
        self.value = self.value + self.step_size
        return self.value
    elseif self.button_type == "up" and self.value > self.min then
        self.value = self.value - self.step_size
        return self.value
    elseif self.button_type == "center" then
        self.value = math.floor((self.max - self.min) / 2) + self.min
        return self.value
    end
    
    return false
end

function fade_button:is_this(x, y)
    return (self.x == x and self.y == y)
end

return fade_button