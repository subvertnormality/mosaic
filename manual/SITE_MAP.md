# Manual architecture

The authored manual contains the complete feature inventory, a ten-chapter learning course, task guides, musical examples and a searchable control reference. Publication acceptance remains pending: authored coverage is not the same as verified course continuity or complete native capture coverage. Consult the current build report and evidence manifest for that distinction.

| Reader job | Destination | Content |
|---|---|---|
| Begin | `#learn` | Meet Mosaic → choose an output → first loop → phrase → Masks → second part → harmony → movement → arrangement → save and reload |
| Make a change | `#workflow` | Sound routing, rhythm, harmony, melody, pattern assignment, parameter variation, arrangement and different loop lengths |
| Look up | `#reference` | Pattern, Channel, Scale, Song, locks, projects, options, musical decisions and developer references; hierarchical feature links |
| Recall a control | `#quick` | Filter by editor, task or gesture; matching controls and their results link to the relevant feature |
| Make music | `#cookbook` | Numbered musical procedures and separately identified recordings |
| Recover | `#no-sound` | Diagnose transport, channel, pattern, masks and output in order |

## Course and reference contexts

The learning sequence is authored in `course.yaml` and compiled into the book. Each chapter states its goal, incoming state, numbered actions, expected result, recovery and outgoing state. Course pages use `#feature-id/course`; Previous and Next retain that context. A verified stage's captured result uses `#feature-id/course/scene-id/step-id`, retaining chapter position after reload or scene selection.

A course page presents its lesson once. Complete controls, independent examples, recipes and reference recordings remain available through its secondary reference link at `#feature-id`. Independent examples identify their starting state; changing examples does not imply that an earlier example's musical project continues.

## Captured-result interaction

Captured examples show the actual norns framebuffer and grid, rather than synthesising an instrument simulation. The next constituent action is identified. Pictured encoders, keys and pads navigate short captured action sequences in order, including held controls and releases; the result appears only after the required constituents. An encoder interaction selects the whole recorded turn, whose direction and detent count are stated.

View next result and Previous provide an accessible fallback and comparison. Long historical input bundles use explicit checkpoint navigation. A single arbitrary control does not enact a compound gesture, and no intermediate framebuffer is fabricated.

## Orientation and publication

Feature routes expose their active section, linked ancestors, local section links and neighbouring reference entries. Course routes add chapter position and chapter navigation. Search includes prose, controls, details, recipes and scene captions with matching excerpts. All feature routes and legacy aliases resolve through the compiled book; they do not fall back to README for unimplemented reference pages.

The YAML manual is the documentation authority. `README.md` provides an overview, and `cheat_sheet.html` is generated from the same manual data. Native acceptance remains inactive until the final qualification checks pass. Stable feature IDs, archived source identities, native captures and failure evidence remain preserved. The public preview must be rebuilt from the accepted source set before its status can be called complete.
