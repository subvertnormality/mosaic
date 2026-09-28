-- Baseline capture for the Merge Shape v1 oracle. NOT part of the candidate
-- suite: capture.sh copies this file into a checkout of f908a553 as
-- lib/tests/lib/zz_merge_v1_baseline_capture_tests.lua and runs only
-- test_capture_merge_v1_baseline with that revision's own lib/tests harness.
-- Output goes to $MERGE_V1_CAPTURE_OUT; capture.sh adds provenance headers.

local scenario = dofile("./fixtures/merge_v1_baseline/scenario.lua")

function test_capture_merge_v1_baseline()
  local out = assert(os.getenv("MERGE_V1_CAPTURE_OUT"), "MERGE_V1_CAPTURE_OUT not set")
  for _, project in ipairs(scenario.projects) do
    project.build()
    local path = scenario.save(out, project.name .. ".v1")
    local observed = scenario.observe(path)
    local loaded = {}
    for number = 1, 17 do loaded[number] = program.get_song_pattern(1).channels[number].musical_merge or false end
    observed.loaded_merge = loaded
    local file = assert(io.open(out .. "/" .. project.name .. ".oracle.body", "w"))
    file:write("return ", scenario.serialize(observed), "\n")
    file:close()
  end
end
