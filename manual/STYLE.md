# Manual language

Use the procedural structure of the researched instrument manuals. Do not add a promotional voice or poetic descriptions of controls.

## Primary examples

- Elektron Digitakt OS 1.51 and Octatrack OS 1.40A: named controls, task-based operation sections, numbered sequences, and separate parameter descriptions.
- [Elektron Syntakt OS 1.30](https://elektron.se/wp-content/uploads/2024/10/Syntakt-User-Manual_ENG_OS1.30_241016.pdf), printed pp. 42–43, §9.10.1: numbered operations for entering parameter locks, followed by displayed and LED feedback, erase operations, limits and exceptions.
- [Polyend Tracker 1.7](https://polyend-website.fra1.digitaloceanspaces.com/wp-content/uploads/2023/08/01084159/Polyend-Tracker-Manual-1.7.0.pdf), printed pp. 6–9: define button and rotary-control notation before using it; distinguish individual controls from simultaneous combinations.
- [Polyend Play Manual Rev. 1](https://polyend-website.fra1.digitaloceanspaces.com/wp-content/uploads/2023/11/15093926/Polyend-Play-Manual-1v6b-1.pdf), printed p. 10 and p. 96 §6.6: consistent control/menu notation, numbered selection and adjustment instructions, and an explanation of displayed multi-selection feedback.
- Make Noise MATHS: place practical patch procedures after the control descriptions. Use this ordering for musical examples.
- monome norns/grid studies: introduce a small operation, describe its result, then extend it. Retain Mosaic's actual K1–K3, E1–E3 and grid vocabulary.

These are targeted section comparisons, not a claim that every page of every manual was reviewed. The text is newly written for Mosaic; the structure and control language follow these examples.

## Writing rules

1. Name a reference section after the actual control or parameter. Name a procedure after a literal task, such as “Set a step note” or “Clear masks”.
2. State what the feature changes in one or two sentences.
3. Give prerequisites before the procedure: editor, selected channel, output or playback state.
4. Number sequential operations. Start each operation with Press, Hold, Turn, Select, Set, Release or Enter.
5. Use the exact control and displayed parameter name. A simultaneous combination uses “Hold K1 and press K2”; a sequence uses separate operations.
6. State the observable result immediately after the relevant action: screen value, grid indication, emitted note or audible change.
7. Put ranges, defaults, precedence, interactions and exceptions after the basic operation. Keep their wording factual.
8. Write musical examples as settings and operations followed by the expected musical result. Avoid metaphors such as “give the melody a mind of its own” or “make a quiet step speak”.
9. Use numeric MIDI notes where displayed octave names differ between Mosaic controls. Explain Masks and Fixed Note conventions in the relevant reference.
10. Keep source and verification details in the evidence panel. Do not insert test-case names into an ordinary player's instructions.

## Example

Before: “Keep the pattern. Give the melody a mind of its own.”

After: “Masks override channel and step trig, note, velocity, length and chord values.”

Procedure:

1. Open the channel Masks task.
2. Select Note with E2.
3. Hold the grid step and turn E3 to the required note.
4. Release the step.

The step uses the selected note. Other steps retain the channel default or merged pattern notes.
