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
