I accepted and fixed both shared-helper findings from session 01a08a3c-b321-7a71-ad86-e6e546012cca1. Please inspect current source and the refreshed docs/testing/recording-trigless-validation.json.

1. `edit_value=-1` now expects an empty timestamp list and skips the immediate-emission assertion while retaining exact MIDI silence, stored Off replay, complete gate durations and paired release checks. M-REC-PARAM-006 passes controlled manifest e4ca7eff9cda4bcc85fcdbbcc8c9e795 and real manifest 3d906c527922458090708ef4f161722e.
2. `edit_value=0` now uses the physical saturation path's exact controlled offset of .76 seconds; ordinary one-detent input remains .61 seconds. M-REC-PARAM-005 passes controlled manifest 9b4cbd0d3cd34a5f83eace9a24bea4ee and real manifest a9cf96ab61e744ef957efed92b6a6128.
3. All five scoped cases were rerun in both clocks after the fix, producing ten new current-source-bound manifests listed in the validation JSON. A new source snapshot passes 530/530 Lua and 100/100 applicable Python unit/oracle tests; hashed logs and source hashes are linked in the JSON.

Confirm that the two helper regressions are resolved and the scoped REC-TRIGLESS slice is acceptable. Return ACCEPTED or CHANGES REQUIRED with concrete findings. Keep broader REC-PARAM-AUTOMATION combinations outside this verdict.
