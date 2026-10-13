# Case-derived scenes

These scenes are authored in `scene-plans*.yaml` and validated by `case-scenes.schema.json` (Draft 7). Each step selects an exact successful semantic result from a named existing behaviour case. The adapter runs the actual application through that case's public grid, norns and MIDI inputs, waits for the independent observable oracle, then captures the native screen and grid. It never selects arbitrary observations as documentation.

The fixture is explicitly `behaviour-case`. Its public inputs come from the pinned case source, rather than from a second independently edited gesture recipe. Published authoring records the ordered public input trace, including waits, so a reviewer can inspect what caused each frame. Encoder deltas in these traces are native input units (two units per Driver detent). Polling waits differ between real time and controlled time; the original raw evidence preserves both. Change the source case or author a standalone v2 scene when changing the gesture sequence; editing a derived trace does not change the fixture.

Every step binds its semantic assertion index, exact asserted values, assertion hash, trace hash, native framebuffer hash and grid hash. The report pins the behaviour source files, the frozen application identity, authoring plan and adapter. Failed runs retain raw recipes, native observations, cleanup and a separate failure record; they are never published as success. All native sessions run under the whole-run `/tmp/mosaic-manual-native.lock` lock.

Scenes sharing the same case and output profile use one native session. Each scene keeps its own checkpoint occurrences and input-trace cursor. Child sessions created by the case inherit the same frozen application, preserving the existing public-input and acceptance path while isolating documentation edits. Constructors are restored when the case finishes.

From the fresh checkout:

```sh
MONOME_EMULATOR=/home/andy/projects/monome-emulator-ci-combined \\
python3 tools/manual_case_capture.py --clock-mode controlled-experimental \\
  --experimental-install /home/andy/projects/monome-runtime-candidates/final-qualification-controlled-01/installation.json

MONOME_EMULATOR=/home/andy/projects/monome-emulator-ci-combined \\
python3 tools/manual_case_capture.py --clock-mode real-time --publish
```

The default selects all authoring plan files. Repeat `--plans PATH` to select several families, or use `--profile base-midi` for the MIDI-only subset. The two modulation scenes require the pinned mod source root through `--mod-code-root`; `--mod-patches` uses the repository’s separately recorded patch fixtures. Use `--plans manual/scene-plans-extra.yaml --output reference-extra-scenes.json` for one family. Only a fully passing selected campaign is atomically published. Focused `--scene ID` runs are diagnostic and should not replace the full reference catalogue. The `complete_regression_run` flag stays false: documentation capture is not the exhaustive behaviour campaign.

A small number of original cases parse their final MIDI wire evidence after shutdown. These use an explicitly authored `capture_stage: before-finish` with `pre_finish_expect` header/field/menu assertions. The adapter independently checks that live UI, captures it immediately before the original close, then binds it only if the later exact MIDI assertion succeeds. The image illustrates the final live control state; it is not described as an image captured after that assertion. Late assertions are preserved in the final results file. There is no arbitrary terminal-frame fallback.

Each completed case saves its exact requested waits in `capture-trace.json` and its scene dictionaries in immutable `captured-scenes.json` before the next case begins. A later failure can therefore be repaired with focused case captures while preserving completed native identities and frame bindings. Original failure records are retained separately.

Authoring has two distinct paths. Edit `manual/scene-plans*.yaml` to choose case checkpoints and their titles/captions; edit the canonical behaviour case to change its existing public-input workflow, retaining its acceptance tests. The `manual/features/scenes-*.yaml` files are generated and pinned input-trace evidence. They are not independent editable gesture recipes. Before any case regeneration, the adapter compares their inputs with the associated captured publication and rejects drift, rather than silently overwriting an edited trace. Restore that derivative or use an independently authored v2 replay scene for a new workflow. Pilot and First Sound use the latter path and replay their authored YAML inputs.

Additional standalone documentation fixtures can export a `CASES` mapping from a file under `tools/`, passed through `--extra-cases tools/manual_reason_swing_cases.py`. The loader executes and pins the exact source bytes and preserves the canonical behaviour registry. `start-source-identity.json` and source-byte folders are written before the first native launch; failures retain the complete start receipt. Every completed case retains `captured-scenes.json` and its trace independently.
