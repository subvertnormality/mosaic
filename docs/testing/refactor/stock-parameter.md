# Stock-parameter resolution boundary

This R06 slice moves stock parameter precedence into the explicit, lazy
`lib/musical_resolution/stock_parameter.lua` resolver. The existing
`step.process_stock_params(c, step, type)` facade still resolves the selected
song and channel and supplies the same lock and native parameter readers.

The resolver preserves numeric slot order, first-match shadowing, per-parameter
Off sentinels, Lua truthiness for zero and minus one, assigned-value precedence,
and the native fallback/default rule. Readers remain lazy so lookup count and
order, including conditional access to `p.default`, match the previous code.

Validation:

- all four direct resolver tests passed;
- all 262 selected step tests passed;
- the full 1,524-test Lua suite passed;
- behavior inventory and Lua syntax guards passed (6/6);
- controlled M-PARAM-015 passed (`722d59d0a167413792932ea74ffb0065`);
- controlled M-PARAM-016 passed (`5204bed42fff447b97b9cc199fcd3b42`);
- controlled M-PARAM-017 passed (`56096c73136c4623945854662b3cf94b`);
- real-time M-PARAM-017 passed (`1f7a1b774e2c45a980b05a6d7ec0510e`);
- controlled M-PARAM-018 passed (`3d096f9205a84360aeea22c01c6665fc`);
- Terra review found no semantic, ordering, coverage or scope issue.

The first attempted extraction made the native default dereference eager. The
existing step tests and M-PARAM cases failed before commit; the resolver now
retains the original short-circuit behavior and all of those checks pass.
