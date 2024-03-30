local fn = include("mosaic/lib/functions")

local function parse_json(contents, depth)
    if depth > 100 then
        return false, "JSON structure too deep"
    end

    contents = fn.string_trim(contents)
    if contents == "" then
        return false, "Empty content"
    end

    -- Simple type checks
    if contents:sub(1, 1) ~= "{" and contents:sub(1, 1) ~= "[" then
        if is_string(contents) or is_number(contents) or is_boolean(contents) or is_null(contents) then
            return true
        else
            return false, "Invalid JSON value"
        end
    end

    -- Assume it's an object or array based on the first character
    local stack = {}
    local expectValue = false
    for i = 1, #contents do
        local char = contents:sub(i, i)
        if char == "{" or char == "[" then
            table.insert(stack, char)
        elseif char == "}" then
            if stack[#stack] ~= "{" then
                return false, "Mismatched closing brace"
            end
            table.remove(stack)
        elseif char == "]" then
            if stack[#stack] ~= "[" then
                return false, "Mismatched closing bracket"
            end
            table.remove(stack)
        end

        -- When the stack is empty, we've correctly closed all open objects/arrays
        if #stack == 0 then
            if i < #contents then
                return false, "Extra characters after closing the root object/array"
            end
            break
        end
    end

    if #stack > 0 then
        return false, "Unclosed object or array"
    end

    return true
end

-- Checks for basic JSON types
function is_number(str)
    return tonumber(str) ~= nil
end

function is_boolean(str)
    return str == "true" or str == "false"
end

function is_null(str)
    return str == "null"
end

function is_string(str)
    return str:sub(1, 1) == "\"" and str:sub(-1, -1) == "\"" -- Very simplistic check
end

function valid_json(contents)
    local valid, err = parse_json(contents, 0)
    if not valid then
        print("JSON validation error:", err)
        return false
    end
    return true
end

return valid_json
