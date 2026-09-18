-- Pure selection shared by playback and future read-only lock previews.
-- README Trig start/end and global pattern length: cap the channel range first.
local cursor = {}

function cursor.next(current, first_run, start_trig, end_trig, global_length)
  if end_trig - start_trig + 1 > global_length then
    end_trig = start_trig + global_length - 1
  end
  local selected = first_run and current or current + 1
  if selected < start_trig then selected = start_trig end
  local wrapped = selected > end_trig
  if wrapped then selected = start_trig end
  return selected, wrapped
end

return cursor
