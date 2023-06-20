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
    return a[bit32.rshift(n, 3) + 1]
end

local function get_bit(a, k)
    local byte = get_byte(a, k)
    local bit_index = 7 - (k % 8)
    return bit32.band(byte, bit32.lshift(1, bit_index)) ~= 0
end

function drum_ops.tresillo(bank, pattern1, pattern2, len, step)
    if bank < 0 or bank > 4 then return 0 end
    if len < 8 then return 0 end
    if step < 0 then return 0 end
    if pattern1 >= _drum_ops_tables.drum_ops_pattern_len or pattern2 >= _drum_ops_tables.drum_ops_pattern_len then return 0 end

    local table1
    local table2

    if bank == 0 then
        table1 = _drum_ops_tables.table_t_r_e[pattern1 + 1]
        table2 = _drum_ops_tables.table_t_r_e[pattern2 + 1]
    elseif bank == 1 then
        table1 = _drum_ops_tables.table_dr_bd[pattern1 + 1]
        table2 = _drum_ops_tables.table_dr_bd[pattern2 + 1]
    elseif bank == 2 then
        table1 = _drum_ops_tables.table_dr_sd[pattern1 + 1]
        table2 = _drum_ops_tables.table_dr_sd[pattern2 + 1]
    elseif bank == 3 then
        table1 = _drum_ops_tables.table_dr_ch[pattern1 + 1]
        table2 = _drum_ops_tables.table_dr_ch[pattern2 + 1]
    elseif bank == 4 then
        table1 = _drum_ops_tables.table_dr_oh[pattern1 + 1]
        table2 = _drum_ops_tables.table_dr_oh[pattern2 + 1]
    end

    local multiplier = len / 8

    local three = 3 * multiplier
    local wrapped_step = wrap(step, 0, multiplier * 8 - 1)

    if wrapped_step <= three - 1 then
        return get_bit(table1, wrapped_step)
    elseif wrapped_step <= three * 2 - 1 then
        return get_bit(table1, wrapped_step - three)
    end

    return get_bit(table2, wrapped_step - (three * 2))
end

function drum_ops.drum(bank, pattern, step)
    if bank < 0 or bank > 4 then return 0 end
    if step < 0 then return 0 end
    if pattern >= _drum_ops_tables.drum_ops_pattern_len then return 0 end

    local table

    if bank == 0 then
        table = _drum_ops_tables.table_t_r_e[pattern + 1]
    elseif bank == 1 then
        table = _drum_ops_tables.table_dr_bd[pattern + 1]
    elseif bank == 2 then
        table = _drum_ops_tables.table_dr_sd[pattern + 1]
    elseif bank == 3 then
        table = _drum_ops_tables.table_dr_ch[pattern + 1]
    elseif bank == 4 then
        table = _drum_ops_tables.table_dr_oh[pattern + 1]
    end

    local wrapped_step = wrap(step, 0, 15)

    return get_bit(table, wrapped_step)
end


return drum_ops