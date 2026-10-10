-- PLAN.md Painting: an intervening ordinary source edit invalidates paint history.
-- Characterisation outside README, pure transaction semantics only.
package.path = './lib/?.lua;' .. package.path
local Journal = require('rhythm_doctor.paint_journal')
local target = {project_id='p', song_slot=1, pattern_id=1}
local journal = Journal.new(4)
assert(Journal.record(journal, target, {v=0}, {v=1}, 1, 0))
-- Ordinary editing produces revision 2 and a new value. Painting after it may
-- be undone, but a second undo must never leap over that ordinary edit.
assert(Journal.record(journal, target, {v=9}, {v=10}, 3, 2))
local undo = Journal.prepare_undo(journal, target, 3)
assert(undo.snapshot.v == 9)
assert(Journal.complete_undo(journal, undo, 4))
assert(Journal.prepare_undo(journal, target, 4).code == 'NO_UNDO',
       'new paint after ordinary edit retained stale older paint history')
local redo = Journal.prepare_redo(journal, target, 4)
assert(redo.snapshot.v == 10)
print('rhythm_doctor journal: intervening-edit transaction passed')

-- PLAN.md bounded session journal: the bound applies across source targets,
-- not independently to every pattern ever visited. Oldest target is evicted.
local bounded = Journal.new(2)
local targets = {}
for id=1,3 do
  targets[id] = {project_id='p', song_slot=1, pattern_id=id}
  assert(Journal.record(bounded, targets[id], {v=0}, {v=id}, id, 0))
end
assert(Journal.prepare_undo(bounded, targets[1], 1).code == 'NO_UNDO',
       'journal retained more entries than its global bound')
assert(Journal.prepare_undo(bounded, targets[2], 2).snapshot.v == 0)
assert(Journal.prepare_undo(bounded, targets[3], 3).snapshot.v == 0)
-- An evicted and recreated stream must not reuse a token generation.
local pending = Journal.prepare_undo(bounded, targets[2], 2)
assert(Journal.record(bounded, targets[1], {v=3}, {v=4}, 4, 3))
assert(Journal.record(bounded, targets[2], {v=4}, {v=5}, 5, 4))
local accepted, err = Journal.complete_undo(bounded, pending, 6)
assert(not accepted and err.code == 'STALE_JOURNAL', 'eviction reused pending token')
print('rhythm_doctor journal: global bound and token generation passed')
