Welcome to Mosaic, an intuitive XoX-style midi sequencer for Monome Norns and Grid. It melds the powerful features of the Elektron sequencer with innovative generative techniques, all within the Monome ecosystem, allowing you to craft complex rhythms and harmonies with ease. Whether you are sketching or composing, Mosaic provides a unique, deep musical experience.

- [Getting started](#mosaic)
  * [Install](#install)
  * [Setup](#setup)
    + [Hardware](#hardware)
    + [Device configuration](#device-configuration)
      - [Stock devices](#stock-devices)
      - [Custom devices](#custom-devices)
      - [Mods and software devices](#mods-and-software-devices)
  * [Typical workflow](#typical-workflow)
    + [Getting around Mosaic](#getting-around-mosaic)
      - [Grid menu navigation](#grid-menu-navigation)
      - [Norns menu navigation](#norns-menu-navigation)
      - [Sequencer start and stop](#sequencer-start-and-stop)
      - [Midi panic](#midi-panic)
    + [Sound design](#sound-design)
    + [Rhythm section design](#rhythm-section-design)
    + [Harmony design](#harmony-design)
    + [Harmony composition](#rhythm-and-harmony-composition)
      - [Adding patterns to channels](#adding-patterns-to-channels)
      - [Using merge modes](#using-merge-modes)
      - [Adding chords](#adding-chords)
    + [Melody composition](#melody-composition)
      - [Adding melodic notes over harmony and drums](#adding-melodic-notes-over-harmony-and-drums)
      - [Midi input](#midi-input)
    + [Modulation, movement and interest](#modulation-movement-and-interest)
    + [Song composition](#song-composition)
    + [Save and load](#save-and-load)
- [Dig deeper](#dig-deeper)
  * [UI interaction patterns](#ui-interaction-patterns)
  * [Pattern editor](#pattern-editor)
      - [Adding trigs](#adding-trigs)
      - [Adding notes](#adding-notes)
      - [Adding velocity](#adding-velocity)
  * [Channel editor](#channel-editor)
  * [Scale editor](#scale-editor)
  * [Devices](#devices)
    + [Midi sound sources](#midi-sound-sources)
    + [Norns sound sources with n.b.](#norns-sound-sources-with-n-b)
  * [Merge modes](#merge-modes)
    + [Trig merge modes](#trig-merge-modes)
    + [Note merge modes](#note-merge-modes)
    + [Velocity merge modes](#velocity-merge-modes)
    + [Length merge modes](#length-merge-modes)
  * [Song sequencer](#song-sequencer)
  * [Trig parameters](#trig-parameters)
    + [Sequencer params](#sequencer-params)
      - [Trig probability](#trig-probability)
      - [Fixed note](#fixed-note)
      - [Quantised fixed note](#quantised-fixed-note)
      - [Random note](#random-note)
      - [Random twos note](#random-twos-note)
      - [Chord strum](#chord-strum)
      - [Chord Velocity Modifier](#chord-velocity-modifier)
    + [Midi params](#trig-params)
  * [Trig locks](#trig-locks)
    + [Param locks](#param-locks)
    + [Scale locks](#scale-locks)
    + [Octave locks](#octave-locks)
  * [Options](#options)
    + [Elektron sync](#elektron-sync)
    + [Sinfonion connect](#sinfonion-connect)
- [Development](#development)
- [Device config template](#device-config-template)



# Getting started

## Install

To install, simply run `;install https://github.com/subvertnormality/mosaic` in maiden.

## Setup

### Hardware


_Mosaic_ operates with the Monome Norns and a 128 Grid at a minimum. While these two components allow you to create simple songs, incorporating external sound sources via a MIDI interface will vastly expand your sequencing capabilities. Devices with MIDI inputs are all supported, though those set up in _Mosaic_ using pre-existing or manually created configuration files are optimal. Crow, Just Friends, and Ansible are natively supported through [n.b.](https://github.com/sixolet/nb/). Additionally, you can utilize Norns to generate sounds by installing n.b. mods. A list of supported mods can be found in the [Norns sound sources with n.b.](#norns-sound-sources-with-n-b) section.

Using [Midi input](#midi-input) devices, while not essential, enhances the user experience. A MIDI keyboard simplifies melody creation, and a MIDI controller with encoders supporting relative bin offsets can improve the data input process.

For those using a ACL [Sinfonion](#sinfonion-connect), support is available through a straightforward hardware build. This setup allows synchronisation between Mosaic's quantization and the Sinfonion Eurorack module.



### Midi device configuration

#### Stock devices

TODO 

#### Custom devices

Tailor Mosaic to fit your studio setup by configuring it for your specific devices. If your device is not included in the standard configuration, create a .json file named after your device. Populate this file using a [device config template](#device-config-template) that matches your device’s MIDI specifications.

#### Mods and software devices

Mosaic can also use internal Norns sound sources and manage devices like Crow, Just Friends, and Ansible via i2c by installing [n.b.](https://github.com/sixolet/nb/) mods. These mods will appear in Mosaic's device list once installed and activated in the Norns settings menu. Ensure the n.b. mod is on the allow list to use with Mosaic. Supported mods include:

* [nb_ansible](https://github.com/sixolet/nb_ansible) for Ansible voices.
* [emplaitress](https://github.com/sixolet/emplaitress) offers four MI Plaits voices in parallel.
* [nb_jf](https://github.com/sixolet/nb_jf) accesses multiple voice modes from Just Friends, including individual mono voice (with slew), polysynth, kit, and unison modes.
* [nb_crow](https://github.com/sixolet/nb_crow) for Crow v/8 and envelope functions.

More mods are expected to be supported soon.

## Typical workflow

This section will guide you through Mosaic's functionality and basic operations, outlining a typical workflow for creating a song.

### Getting around Mosaic

#### Grid menu navigation

Navigation within Mosaic primarily occurs via the Grid. The lower left five buttons serve as the global menu buttons. From left to right, these buttons allow access to the "[Channel](#channel) page", "[Song sequencer](#song-sequence) page", "[Pattern](#pattern) editor", "[Notes](#adding-notes) page", and "[Velocity](#adding-velocity) page".

![The menu as shown on the pattern edit page](https://raw.githubusercontent.com/subvertnormality/mosaic/main/designs/Images/menu.png)


#### Norns menu navigation

Each grid page corresponds to several grouped pages displayed on the Norns screen. Settings in these pages are typically set once and require minimal adjustments. Navigation through these pages is accomplished by moving left and right with the [TODO: specify knob], and settings within pages can be adjusted by moving up and down with the [TODO: specify knob].

[TODO: image of Norns device with highlighted knobs]


#### Sequencer start and stop

To start the sequencer, press the global menu button of the currently selected page — the illuminated button — in the navigation section.

To stop the sequencer, hold down the global menu button of the currently selected page for around a second.

#### Midi panic

Should your MIDI output devices become unresponsive, you can clear all MIDI-on events by holding down the navigation button of the currently selected page while pressing a non-selected navigation button. This action will send a stop signal to all devices, on all channels, for all notes.


### Sound design

The initial stage of song creation involves setting up a few basic voices. These preliminary sound designs may evolve, but it's useful to have a basic foundation for developing the rhythmic, harmonic, and melodic aspects of your track.

Start by selecting the device for each element of your composition, whether it be an internal Norns player, an external drum machine or synthesizer, or components of a modular patch. Assign each device to a Mosaic [channel](#channel) as detailed in the [device](#device) section. Organising different instruments can be helpful; for instance, group drums on channels 1-6, harmonic and textural elements on channels 7-10, melodic elements on channels 11-14, and reserve channels 15 and 16 for modulation. Adapt these assignments to suit your specific musical style and needs.

With your devices assigned, you're ready to begin the rhythm and harmony design process.

### Rhythm section design

The rhythm of your track is crafted using the [Pattern editor](#pattern), accessible by pressing the third button in the global menu cluster located at the bottom left of your grid. A pattern in Mosaic is defined as a sequence composed of 64 trigs, notes, velocities, and duration data, spanning 64 steps.

The pattern editor provides multiple tools to create intricate rhythms. You can input trigs manually in an XOX style, or choose from predefined banks featuring bass, snare, and hi-hat patterns. For more complex needs, explore using Euclidean patterns or those from Noise Engineering's Numeric Repetitor. To add unique rhythmic variations, apply a tresillo modifier, which introduces a 3-3-2 repeating pattern. These rhythm types can be blended by selecting and "painting" them onto the grid. To learn more about this process, refer to the [adding trigs](#adding-trigs) section.

After establishing a pattern of trigs, assign [note](#adding-notes) and [velocity](#adding-velocity) data. These patterns will later be integrated and remixed to form your rhythm and harmony sections.


### Harmony design

_Mosaic_'s harmony tools enable you to compose your song's chordal progressions with ease. These progressions can dynamically modulate your patterns, allowing for the creation of complex harmonic sequences with minimal music theory knowledge.

Harmonic progressions can be applied globally — modulating all notes across all channels to the same key, degree, and scale rotation — or on a per-channel basis, affecting only the notes within that channel. This decoupling of patterns and notes from the active scale enables dynamic and experimental tonal modulations. For example, setting your global scale to change in a polyrhythmic pattern relative to your channel's note data can create captivating musical textures.

Each project supports 16 scale slots. Each slot includes a root note, a scale type (e.g., Dorian, Major), a degree, and a scale rotation. Access the scale editor by selecting the channel page using the far left global menu button, then pressing any of the scale buttons.

![Scale selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/channel_edit_scale_select.png)

When in the scale editor, a short press of the scale buttons selects one of the 16 scales; the currently selected scale is dimly lit on the grid. Use the Norns interface to adjust the root, scale, degree, and rotation for the selected scale.

A long press on a scale button selects it as the global scale, indicated by a brightly lit scale button. All patterns now default to this scale unless overridden by a global scale trig lock or channel scale trig lock.

Scale locks can be set to apply a scale globally or to a single channel, activating at a designated step and persisting until the end of the pattern. To set a scale lock, hold a step and press the desired scale slot button. On the scale page, this applies globally to all channels without an active channel scale trig lock; on a channel's page, it applies as a channel scale trig lock, affecting only that channel. Channel-specific scale locks override global scales and locks.

You can also adjust the rate of the global scale track and set its length independently of other channels, enabling chord progressions that extend beyond a single pattern. This feature offers substantial flexibility for crafting intricate chord progressions and varying patterns.

To return to the channel edit page, press any of the channel buttons at the top of the grid.

### Rhythm and harmony composition

At this point you will have a set of sound sources attached to a number of channels, a set of patterns with notes, trigs velocities and lengths, and a set of scales that work well together - possibly assigned as either a global scale or a set of trig locks on the global scale editor. Now it's time to do some composition. You can now use _Masaic_'s channel editor to lay out your harmonic and rhythem sections. First, select the channel page by pressing the far left global menu button, and select one of the 16 available channels using the channel select row at the top of _Mosaic_'s Grid UI.

![Channel selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/channel_edit_channel_select.png)

#### Adding patterns to channels

Experiment by assigning your various patterns to different channels. A single channel can accommodate multiple patterns, and likewise, a single pattern can be assigned to multiple channels. To assign patterns, use the pattern select row, located second from the top on Mosaic’s Grid UI.

![Pattern selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/channel_edit_pattern_select.png)

#### Using merge modes

When assigning multiple patterns to a single channel, you might notice that overlapping steps in different patterns can deactivate. This occurs because the default "skip" merge mode is active. [Merge modes](#merge-mode) control the behavior of these overlaps, allowing the same pattern to be used across multiple channels while ensuring they interact in harmonically meaningful ways. Experiment with different merge modes to explore various musical interactions.


### Melody composition

TODO

#### Adding melodic notes over harmony and drums

TODO

#### Adding chords

TODO

#### Midi input

TODO

### Modulation, movement and interest

TODO

#### Sequencer trig locks

TODO

### Song composition

TODO

### Save and load

TODO

## Dig deeper

TODO

### UI interaction patterns

### Pattern editor

TODO


#### Adding trigs

Trigs are added in the pattern editor.

![Trig editor with a complex trig pattern](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor.png)

With the top row, pick one of the 16 patterns available. In the image, you can see pattern 2 is selected.

![Pattern select buttons](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_pattern_select.png)

To set your rhythm, simply tap in steps using the sequencer. Bright steps symbolise a trig. To define its length, press and hold a trig, then choose its ending step. Steps with a subtle glow show the length. In a single pattern, one trig’s duration ends upon meeting another.

![Trig sequencer](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_sequencer.png)

Craft unique rhythms using a variety of built-in algorithms.

* button 1: The drum algorithm, drawing from a rich collection of classic drum patterns.
* button 2: The tresillo algorithm, utilising a 3/3/2 ratio for diverse rhythm variations. The tresillo multiplier can be set on the norns screen for more variations.
* button 3: Euclidian, a rhythm tool rooted in mathematical logic.
* button 4: NE Numeric Repetitor, another rhythm tool based on mathematical principles.

![Algorithm select](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_algorithms.png)

The grid is intuitive and adapts to your choices. Each algorithm brings its set of options, and pressing on a grid key typically displays its function on the norns screen.

The left side faders adjust algorithm values. Brightly lit ends refine values, while the dimmer ones adjust them broadly. The rightmost fader typically toggles between different algorithm banks.

![Algorithm controls](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_algorithm_controls.png)

To see your algorithm's impact, hit the prime button. This prepares a new pattern, and new steps are showcased as flashing bright steps on the sequencer. While these steps flash, they aren’t painted yet. Any step that would be painted over an existing active step will blink dimly. By painting the new pattern, you'll deactivate the faintly blinking steps. This approach lets you craft intricate sequences, grounded in rhythmic fundamentals, that don't get too busy. You can modify algorithm parameters whilst the pattern is primed.

If you haven’t painted the new pattern, the prime button continues to blink. Pressing it again paints your edits. Double-pressing the prime button without tweaking the algorithm or its parameters acts as an undo for the last action.

![Prime and print button](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_prime_and_print.png)

Opt out of a prepared pattern by using the cancel button.

![Cancel button](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_cancel.png)

While previewing a new pattern, use the move controls to shift its position. The first button shifts it left, the third to the right, and the centre button resets it. Remember to paint your changes.

![Left, centre, right buttons](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_left_right.png)

On the norns screen, you can see the selected channel's grid state on page 1. This is the merged version of the channel and is a useful context for editing your pattern. Use E2 to select channels.

![Channel grid viewer](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/UI/trig_edit_grid_viewer.png)

On page 2 you can select trig editor options. Currently this allows you to edit the tresillo multiplier in use. Experiment with different values to get wildly different results with the tresillo algorithm.

![Channel grid viewer](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/UI/trig_edit_options.png)

#### Adding notes

In _Mosaic_, notes aren't strictly bound to a single scale. Instead, they are valued by their position within the currently active scale, measured by distance from the root. Take C major for instance: C is your starting point. One step up brings you to D, and one step down lands on B. If you were to change the applied scale to E minor, the root of your pattern would now be E, one step up would output F sharp, one down would be D. 

You'll see in the [Harmony design](#harmony-design) section that it's possible to sequence scale and degree changes, and this affects the notes your patterns will play. When adding notes to patterns, consider that they represent the harmony of your song and map to what traditionally would be called the rhythm section. It is possible to create melodies using patterns, but it is difficult to do so in a deliberate way as your scale progressions will alter the tonality of your pattern. We'll learn about the recommended way to deliberate [melodies](#melody-composition) later. 

Select the note edtior by pressing the fourth key in the global menu button cluster on the grid. 

This space displays 16 steps at a glance. Active trigs appear as soft-glowing vertical bars while the root note lies in a subtle horizontal line. The notes you've actively chosen glow brightly. To pick a note for any of the 16 steps, just press. The gentle flicker on the top row indicates the currently chosen pattern. If you wish to explore a different pattern, press and hold on this top row.

Remember, each note you select links back to the root of the scale you're working within. The scale is applied to the channel, not the pattern. You must start to think about your patterns as being disconnected from each channel. This is why we say _Mosaic_ is an intentioned generative sequencer. Expect happy accidents. The channel grid viewer on the norns screen can help you here.

![Note select](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/note_editor_note_selector.png)

Switch between the four sets of 16 steps using the dedicated buttons.

![16 step selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/note_editor_16_selector.png)

Aim for higher pitches or dive deeper with the octave select buttons, expanding your melodic range.

![melodic range selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/note_editor_octave_selector.png)

Hint: Even if a step lacks a trig, don't hesitate to assign a note. This data might come in handy with different merge modes in play.

You can use the four by four button to toggle a mode that lets you more quickly enter repeating notes across the four note grid pages. In four by four mode, any entered note is automatically duplicated across all 4 screens.

![Four by four](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/note_editor_four_by_four.png)

On the norns screen, you'll find the channel grid visualiser. Use E2 to select the current channel.

#### Adding velocity

Now let's look at the velocity editor, which functions similarly to the note page. Access it by pressing the fifth button in the global menu cluster.

The velocity editor spans two vertical pages: the first displays velocities from 127 down to 67, while the second displays values between 58 and 0. Adjust these to fine-tune the dynamics of your sequence.

On the norns screen you can see the channel grid visualiser. Use E2 to select the current channel.


### Channel editor

TODO

### Scale editor

TODO

### Devices

TODO

#### Midi sound sources

TODO

#### Norns sound sources with n.b.

TODO

### Merge modes

To determine how your patterns interact and meld within the composition, you'll need to use the merge mode selector. This feature enables nuanced control over how overlapping patterns in the same channel behave, impacting trigs, notes, velocity, and length.

![Merge mode selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/channel_edit_merge_mode.png)

#### Trig merge modes

These modes define how trigs are activated when there are overlapping steps across selected patterns:

* All: Trigs will activate if they appear in any selected pattern.
* Skip: Trigs will activate only if they appear in exactly one selected pattern. If a trig appears in multiple patterns, it won't activate.
* Only: Trigs will activate only if they appear in more than one selected pattern, ignoring those that appear in just one.

#### Note merge modes

These modes determine how note values are handled when steps overlap:

* Average: The note value for overlapping steps is the average of those steps' values in each pattern, subsequently quantized.
* Higher: The highest note value from overlapping steps is used after calculating the average and adjusting by subtracting the lowest and adding the highest note value, followed by quantization.
* Lower: The lowest note value is used after calculating the average and subtracting the lowest note value from the average, followed by quantization.
* Pattern: To prioritize a specific pattern's note values during conflicts, hold the note merge button and select the desired pattern.

By default, notes will snap to the pentatonic version of the currently active scale to assist with avoiding unpleasent harmonic interactions. This can be disabled in _Mosaic_'s settings.

#### Velocity merge modes

These settings affect how velocity values are calculated for overlapping steps:

* Average: The velocity is the average of the velocities from overlapping steps in each pattern.
* Higher: The velocity is calculated by taking the average of each step's velocity, subtracting the lowest velocity, and adding the highest velocity.
* Lower: The velocity is calculated by taking the average of each step's velocity, subtracting the lowest velocity, and not adding the highest value back.
* Pattern: To use a specific pattern’s velocity values, hold the velocity merge button and press the pattern's select button.

#### Length Merge Modes

These modes dictate how the duration of notes is calculated for overlapping steps:

* Average: The length is the average of the lengths from overlapping steps in each pattern.
* Longer: The length is determined by taking the average length, subtracting the shortest length, and adding the longest length.
* Shorter: The length is calculated by subtracting the shortest length from the average of each step's length minus the shortest length.
* Pattern: To apply a specific pattern’s length values, hold the length merge button and press the pattern's select button.

### Song sequencer

TODO

### Trig parameters

Most devices in _Mosaic_ feature a set of trig params that alters either the quality of the sound or the trig in some way. Trig params are unique to a song pattern, allowing drastic transitions when moving from one section to another. Each channel can have up to 10 trig params asigned, and each trig param can be trig locked independently. Trig locking is a powerful sequencer device seen on Elektron synthesisers. Each step can be assigned a unique param value, allowing for endless sound variations. See the channel page section for details on how to assign and use trig params.

TODO: detail how to assign trig params

#### Sequencer params

All device types have a set of standard trig params that affect the sequencer rather than the quality of the sound. 

##### Trig Probability

This trig lock can be used to ensure trigs play only with a certain probability. When set to 100, the trig will always play. When set to 0, the trig will never play. At 50, the trig will play half the time. You can set this globally and per step.

##### Fixed note

Use this trig param to fix your channel to any midi note. The value represents a midi note number. The note is _not_ quantised. This is useful if you have a drum pattern and you don't want note data to affect the drum sound you're playing on a drum machine. This will override any quantised fixed note values or random note values.

##### Quantised fixed note

You can use this trig param to manually select a note in the currently selected scale at any step. The value represents note number, where 0 is the root and higher numbers represent notes in the quantised scale. This overrides the note data coming in from the patterns. This will override random note values.

##### Random note

This trig param introduces an element of random to your selected notes. A value of 0 will leave the note unchanged. A value of 1 will randomly give your existing note or the note one higher in the scale. A value of 2 will randomly give your existing note, the note one higher in your selected scale, or the note one lower. A value of 3 will randomly select notes -1, 0, 1 or 2. A value of 4 will randomly select notes -2, -1, 0, 1 or 2. And so on. Use trig locks to really spice things up. These can be combined with random two's note trig param. By default, random notes are quantised to the pentatonic version of the currently selected scale to reduce the chance of dissonant harmonic interactions. This can be disabled in _Mosaic_'s param settings.

##### Random twos note

Similar to random note, this trig param introduces an element of random to your selected notes. The difference here is that two's note restricts values to those divisible by two. A value of 0 will leave the note unchanged. A value of 1 will randomly give your existing note or the note two higher in the scale. A value of 2 will randomly give your existing note, the note two higher in your selected scale, or the note two lower. A value of 3 will randomly select notes -2, 0, 2 or 4. A value of 4 will randomly select notes -4, -2, 0, 2 or 4. And so on. Use trig locks to really spice things up. These can be combined with random note trig params. Again, random notes are quantised to the pentatonic version of the currently selected scale to reduce the chance of dissonant harmonic interactions. This can be disabled in _Mosaic_'s param settings.

##### Chord strum

The Chord Strum feature dynamically spaces chord notes using the selected clock division, ensuring they align rhythmically with the channel's settings. Notes are quantized to the current scale, adjusting in real-time if the scale changes mid-strum, guaranteeing each note stays harmonious and in tune, regardless of strum duration.

##### Chord Velocity Modifier

The Chord Velocity Modifier incrementally adjusts the velocity of successive notes in a chord, starting from the chord's root note. This adjustment can either increase or decrease the velocity, thereby creating a "swell" effect for rising intensity or a "fade" effect for a diminishing feel.

#### Midi params

TODO

### Trig locks

TODO

#### Param locks

TODO

#### Scale locks

TODO

#### Octave locks

TODO

### Options

TODO

#### Elektron sync

TODO

#### Sinfonion connect

TODO

## Development

TODO

## Device config template

If copying the below code, you must exclude all text appearing after "//"

```javascript
[{
  "params": [
    {
      "cc_msb": 7, // the midi cc number to send the command on.
      "name": "Level", // the name representing this param.
      "cc_max_value": 127, // the maximum value that can be sent over midi.
      "short_descriptor_1": "AMP", // the label that identifies the trigger param in _Mosaic_ at the top of the dial.
      "short_descriptor_2": "LVL", // the label that identifies the trigger param in _Mosaic_ at the bottom of the dial.
      "id": "level", // the unique ID of the param
      "off_value": -1, // the value that determines when the param is off, usually -1
      "cc_min_value": -1 //-- the lower value of the midi param, usually -1
    },
    { // here a specially sequencer param "fixed note" is used to lock the note to a certain midi note value, which is useful for some drum devices in combination with "maps_params_automatically".
      "short_descriptor_2": "NOTE",
      "name": "Fixed Note",
      "cc_max_value": 127,
      "default": 36, // the midi device will only send out the value 36, regardless of note assignment
      "cc_min_value": -1,
      "short_descriptor_1": "FIXD",
      "off_value": -1,
      "id": "fixed_note" -- this identifies the param as a special "fixed note" sequencer trig param
    }
  ],
  "type": "midi", // mandetory: leave as midi for custom devices.
  "unique": true, // mandetory: true if you only allow one instance of this device in use at one time, false allows multiple instances.
  "map_params_automatically": true, // mandetory: when true, the first 10 params are mapped and assigned on the device's channel trig parameters.
  "polyphonic": false, // mandetory: true if more than one note can be played at once on the device.
  "value": 8, // mandetory: arbitrary value, choose any number.
  "default_midi_device": 1, // optional: use this to set a default midi output device. When in use it will no longer be possible to change the output device in _Mosiac_.
  "default_midi_channel": 10, // optional: use this to set a default midi output channel. When in use it will no longer be possible to change the output channel in _Mosaic_.
  "name": "Your device", // mandetory: the name used to identify the device _Mosaic_.
  "id": "a-unique-id" // mandetory: the ID used to identify the device _Mosaic_. Must be unique.

}]
```