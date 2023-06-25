local _drum_ops_tables = include('sinfcommand/lib/_drum_ops_tables')

drum_ops = {}

local function wrap(k, lower_bound, upper_bound)
    local range = upper_bound - lower_bound + 1
    local kx = ((k - lower_bound) % range)
    if kx < 0 then
        return upper_bound + 1 + kx
    else
        return lower_bound + kx
    end
end

local function get_byte(a, n)
    return a[bit32.rshift(n-1, 3) + 1]
end

local function get_bit(a, k)
    local byte = get_byte(a, k)
    local bit_index = 7 - ((k-1) % 8)
    return bit32.band(byte, bit32.lshift(1, bit_index)) ~= 0
end

function drum_ops.tresillo(bank, pattern1, pattern2, len, step)
    if bank < 1 or bank > 5 then return 1 end
    if len < 8 then return 1 end
    if step < 1 then return 1 end
    if pattern1 > _drum_ops_tables.drum_ops_pattern_len or pattern2 > _drum_ops_tables.drum_ops_pattern_len then return 1 end

    local table1
    local table2

    if bank == 1 then
        table1 = _drum_ops_tables.table_t_r_e[pattern1]
        table2 = _drum_ops_tables.table_t_r_e[pattern2]
    elseif bank == 2 then
        table1 = _drum_ops_tables.table_dr_bd[pattern1]
        table2 = _drum_ops_tables.table_dr_bd[pattern2]
    elseif bank == 3 then
        table1 = _drum_ops_tables.table_dr_sd[pattern1]
        table2 = _drum_ops_tables.table_dr_sd[pattern2]
    elseif bank == 4 then
        table1 = _drum_ops_tables.table_dr_ch[pattern1]
        table2 = _drum_ops_tables.table_dr_ch[pattern2]
    elseif bank == 5 then
        table1 = _drum_ops_tables.table_dr_oh[pattern1]
        table2 = _drum_ops_tables.table_dr_oh[pattern2]
    end

    local multiplier = math.floor(len / 8)

    local three = 3 * multiplier
    local wrapped_step = wrap(step, 1, multiplier * 8)

    if wrapped_step <= three then
        return get_bit(table1, wrapped_step)
    elseif wrapped_step <= three * 2 then
        return get_bit(table1, wrapped_step - three)
    end

    return get_bit(table2, wrapped_step - (three * 2))
end

function drum_ops.drum(bank, pattern, step)
    if bank < 1 or bank > 5 then return 1 end
    if step < 1 then return 1 end
    if pattern > _drum_ops_tables.drum_ops_pattern_len then return 1 end

    local table

    if bank == 1 then
        table = _drum_ops_tables.table_t_r_e[pattern]
    elseif bank == 2 then
        table = _drum_ops_tables.table_dr_bd[pattern]
    elseif bank == 3 then
        table = _drum_ops_tables.table_dr_sd[pattern]
    elseif bank == 4 then
        table = _drum_ops_tables.table_dr_ch[pattern]
    elseif bank == 5 then
        table = _drum_ops_tables.table_dr_oh[pattern]
    end

    local wrapped_step = wrap(step, 1, 16)
    print(get_bit(table, wrapped_step))
    return get_bit(table, wrapped_step)
end

function drum_ops.nr(prime, mask, factor, step)

    if prime < 1 then prime = 32 + prime end
    local rhythm = _drum_ops_tables.table_nr[prime] 
    if mask < 1 then mask = 4 + mask end
    if factor < 1 then factor = 17 + factor end
    if step < 1 then step = 16 + step end
    step = wrap(step, 1, 16)
    if mask == 1 then
        rhythm = bit32.band(rhythm, 0x0F0F)
    elseif mask == 2 then
        rhythm = bit32.band(rhythm, 0xF003)
    elseif mask == 3 then
        rhythm = bit32.band(rhythm, 0x1F0)
    end
    
    local modified = rhythm * factor
    
    local final = bit32.bor(bit32.band(modified, 0xFFFF), bit32.rshift(modified, 16))
    local bit_status = bit32.band(bit32.rshift(final, 16 - step), 1)
    
    return bit_status == 1
end

return drum_ops