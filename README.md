# Patterning

Welcome to *Patterning*.

*Patterning* for monome norns manifests as a grid-centric, intentioned generative sequencer. Bridging the realms of modular, Elektron, and monome, it weaves intricate rhythms and melodic paths with finesse. Dive into a profound and singular tapestry of sketching and composition.

At a glance, as of v0.1 patterning gives you the following:

- 16 channels that can each output triggers, notes, note length, velocity and CC to a single midi device
- 16 patterns that can be combined and mutated in different permutation to change their properties in very musical ways
- Song mode with 90 sequencer patterns
- A pattern editor that allows quick creation of trigger patterns using a DrumOps port, includes euclidean, tresillo function, drum preset banks, and NE Numeric Repetitor
- 8 assignable trig locks per channel
- Midi device templates including labelled trig destinations
- Per channel tempo and swing
- Per channel pattern length
- Channel muting
- Scales with root note and degree setting
- Trig lockable octave and scale select

Requirements:

- Norns
- 128 grid
- Midi interface
- Midi instruments

## Core concepts

### Pattern

In patterning, the 'pattern' is a central pillar. Think of it as a sequence enriched with 64 trigs, 64 notes, 64 velocities, and timing linked to each trig. Even steps without trigs should be graced with note and velocity information. Each pattern spans 64 steps.

In the world of patterning, notes don't strictly adhere to a single scale. They echo their position within the chosen scale, measured by distance from the root. Take C major for instance: C is your starting point. One step up brings you to D, and one step down lands on B. Patterning ensures you remain within the bounds of your selected scale (though there are ways to flirt with notes outside of it, which we'll delve into later).

### Channel

The 'channel' is the second crucial component in patterning. Through a channel, you decide the musical device to play and the specifics of its sound. You select the channel's MIDI device, pick the MIDI output, choose the MIDI channel, and set up trig locks and their related destinations. Additionally, you can assign various patterns to one channel. Remember, a single pattern can be linked to multiple channels, and while each channel operates in monophonic mode, several can send signals to the same MIDI device.

When two patterns overlap in one channel and their trigs coincide, the outcome depends on the channel's 'merge mode'. There are several merge modes, each with its own characteristic. This feature encourages designing patterns that, when they overlap, produce intriguing results.

You can adjust the rhythm for each channel individually, allowing for different clock divisions and swings. Plus, if you're looking to mix up the rhythm, channels can be set to fewer than the standard 64 steps, opening the door to polyrhythmic experiments.

### Sequencer Pattern

The sequencer pattern stands as one of the foundational elements in Patterning. This entity encompasses all details from channels and patterns, ranging from trig locks and scale preferences to merge modes and octave choices for a 64-step sequence. Within a Patterning scene, you're provided with 90 sequencer pattern slots, which can be seamlessly linked to craft a song. All channels can have their sequencer patterns adjusted anywhere between 1 to 64 steps.

### Scale

Each sequencer pattern offers 16 scale slots. A single slot can house a root note, a scale variation (like Dorian or Major), and a degree setting. Scales can be fine-tuned in various ways: setting a default scale for a channel, designating scale trig locks for specific channels, or implementing global scale trig locks influencing all channels unless a particular channel-specific trig lock takes precedence. This flexibility paves the way for intricate chord progressions.

### Device

Think of a device as a representation of a MIDI device in your workspace. It's primarily defined by attributes like MIDI destinations, device name, and CC MIDI destinations. While there are some ready-made device templates to get you started, trig lock destinations can be customized either directly on the norns or through a configuration file.

## Pages

At its heart, Patterning comprises five distinct pages. Every page presents a grid interface complemented by a set of configurable options on the norns device. The design prioritizes the grid, urging users to initiate some basics via the norns—like scales and MIDI setups—and then dive deep into the grid for music creation.

### Menu

The grid's lower menu facilitates page selection using its initial five buttons, a feature maintained consistently across all pages. Additionally, on the right, there are functions sensitive to the current page context.
 
![The menu as shown on the pattern edit page](/designs/Images/menu.png)

From the left moving rightward, the buttons activate:

* Channel editor
* Song editor
* Trig editor (highlighted in this instance)
* Note editor
* Velocity editor

### Trig editor

Dive into the world of rhythmic design with the trig editor in _Patterning_. Using the DrumOp tools, you can craft intricate patterns and define the duration of each step.

![Trig editor with a complex trig pattern](/designs/Images/trig_editor.png)

With the top row, pick one of the 16 patterns available. In the image, you can see pattern 2 being selected.

![Pattern select buttons](/designs/Images/trig_editor_pattern_select.png)

To set your rhythm, simply tap in steps using the sequencer. Bright steps symbolize a trig. To define its length, press and hold a trig, then choose its ending step. Steps with a subtle glow show the length. Since patterns are monophonic, one trig’s duration ends upon meeting another.

![Trig sequencer](/designs/Images/trig_editor_sequencer.png)

Craft unique rhythms using a variety of built-in algorithms.

![Algorithm select](/designs/Images/trig_editor_algorithms.png)

* Button 1: The drum algorithm, drawing from a rich collection of classic drum patterns.
* Button 2: The tresillo algorithm, utilizing a 3/3/2 ratio for diverse rhythm variations.
* Button 3: Euclidian, a rhythm tool rooted in mathematical logic.
* Button 4: NE Numeric Repetitor, another rhythm tool based on mathematical principles.

The grid is intuitive and adapts to your choices. Each algorithm brings its set of options, and pressing on a grid key typically displays its function on the norns screen.

The left side faders adjust algorithm values. Brightly lit ends refine values, while the more subdued ones adjust them broadly. The rightmost fader typically toggles between different algorithm banks.

![Algorithm controls](/designs/Images/trig_editor_algorithm_controls.png)

To see your algorithm's impact, hit the prime button. This prepares a new pattern, and new steps are showcased as flashing bright steps on the sequencer. While these steps flash, they aren’t set. Any step that would be applied over an existing active step will blink dimly. By painting the new pattern, you'll deactivate the faintly blinking steps. This approach lets you craft intricate sequences grounded in rhythmic fundamentals.

If you haven’t set the new pattern, the prime button continues to blink. Pressing it again paints your edits. Here’s a tip: Double-pressing the prime button without tweaking the algorithm or its parameters acts as an undo for the last action.

![Prime and print button](/designs/Images/trig_editor_prime_and_print.png)

Opt out of a prepared pattern by using the cancel button.

![Cancel button](/designs/Images/trig_editor_cancel.png)

While previewing a new pattern, use the move controls to shift its position. The first button shifts it left, the third to the right, and the center button resets it. Remember to paint your changes.

![Left, centre, right buttons](/designs/Images/trig_editor_left_right.png)

### Note editor

Dive into the harmony and melody of your rhythmic creations with the note editor.

This space displays 16 steps at a glance. Envision the notes as a journey from the root: active trigs appear as soft-glowing vertical bars while the foundational root note lies in a subtle horizontal beam. The notes you've actively chosen gleam brightly. To pick a note for any of the 16 steps, just press. The gentle flicker on the top row indicates the currently chosen pattern. If you wish to explore a different pattern, press and hold on this top row.

Remember, each note you select links back to the root of the scale you're working within.

![Note select](/designs/Images/note_editor_note_selector.png)

Switch between the four sets of 16 steps using the dedicated buttons.

![16 step selector](/designs/Images/note_editor_16_selector.png)

Aim for higher pitches or dive deeper with the octave select buttons, expanding your melodic range.

![16 step selector](/designs/Images/note_editor_octave_selector.png)

Hint: Even if a step lacks a trig, don't hesitate to assign a note. This data might come in handy with different merge modes in play.

### Velocity editor

Venture into the velocity editor, a close kin of the note editor. It spans two vertical pages: the initial displays velocities from 127 down to 67, while the latter showcases values between 58 and 0. Adjust these to fine-tune the dynamics of your sequence.

### Channel editor

TODO

### Song editor

TODO


# Development

See https://trello.com/b/kMZ4qEhk/patterning for backlog. Please raise bugs and issues in Github.